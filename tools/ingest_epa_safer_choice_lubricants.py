#!/usr/bin/env python3
"""Extract explicitly named lubricants from the US EPA Safer Choice dataset."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "epa-safer-choice-lubricants.jsonl"
REPORT = ROOT / "data" / "epa-safer-choice-lubricants-report.json"
SOURCE_URL = "https://data.epa.gov/efservice/t_safer_choice_and_design_for_the_environment/CSV"
SOURCE_PAGE_URL = "https://www.epa.gov/enviro/download-additional-envirofacts-datasets"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (official-open-government-data)"


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


def fetch() -> bytes:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError("EPA Safer Choice returned an empty CSV")
    return payload


def main() -> None:
    payload = fetch()
    text = payload.decode("utf-8-sig")
    source_rows = list(csv.DictReader(io.StringIO(text)))
    required = {
        "program", "category", "sector", "upcs", "gtins", "mpns",
        "product_name", "company_name", "partner_since",
        "company_in_good_standing", "product_url",
    }
    if not source_rows or not required.issubset(source_rows[0]):
        raise RuntimeError("Unexpected EPA Safer Choice CSV schema")

    # An explicit product-name test keeps degreasers, grease-trap cleaners and
    # unrelated products outside the professional lubricant catalog.
    scoped = [
        row for row in source_rows
        if re.search(r"\blubricants?\b", clean(row["product_name"]), re.IGNORECASE)
    ]
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in scoped:
        grouped[(normalize(row["company_name"]), normalize(row["product_name"]))].append(row)

    records = []
    for key, rows in sorted(grouped.items()):
        first = rows[0]
        identity = "|".join(key)
        codes = {
            field: sorted({clean(row[field]) for row in rows if clean(row[field])})
            for field in ("upcs", "gtins", "mpns")
        }
        source_record_id = "EPA-SC-" + hashlib.sha256(identity.encode()).hexdigest()[:16].upper()
        records.append({
            "source_id": "EPA_SAFER_CHOICE_LUBRICANTS",
            "source_record_id": source_record_id,
            "source_url": SOURCE_URL,
            "source_page_url": SOURCE_PAGE_URL,
            "product_url": clean(first["product_url"]),
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "manufacturer": clean(first["company_name"]),
            "brand": clean(first["company_name"]),
            "product_name": clean(first["product_name"]),
            "family_code": "S",
            "classification_basis": "explicit_lubricant_product_name_in_official_safer_choice_dataset",
            "program": clean(first["program"]),
            "categories": sorted({clean(row["category"]) for row in rows if clean(row["category"])}),
            "sectors": sorted({clean(row["sector"]) for row in rows if clean(row["sector"])}),
            "partner_since": clean(first["partner_since"]),
            "company_in_good_standing": clean(first["company_in_good_standing"]).casefold() == "true",
            "upcs": codes["upcs"],
            "gtins": codes["gtins"],
            "mpns": codes["mpns"],
            "source_occurrence_count": len(rows),
            "lifecycle_status": "listed_in_current_safer_choice_dataset",
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_open_government_safer_choice_lubricants_normalized",
        "source_id": "EPA_SAFER_CHOICE_LUBRICANTS",
        "source_url": SOURCE_URL,
        "source_page_url": SOURCE_PAGE_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "source_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "source_csv_rows": len(source_rows),
        "explicit_lubricant_name_occurrences": len(scoped),
        "normalized_products": len(records),
        "duplicate_identifier_occurrences_merged": len(scoped) - len(records),
        "manufacturers": len({row["manufacturer"] for row in records}),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "scope_rule": "Product name contains the standalone word lubricant or lubricants; degreasers and grease-trap cleaners are excluded.",
        "excluded_fields": ["city", "state"],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
