#!/usr/bin/env python3
"""Normalize public TISI manufacturing licences for two-stroke engine oil.

The Thai Industrial Standards Institute publishes a current searchable licence
report for compulsory standards.  TIS 1040-2541 search results identify a
licence holder and certified product scope, not a marketed brand, grade or SKU.
This importer deliberately preserves that conservative grain.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "tisi-two-stroke-oil-licences.jsonl"
REPORT = ROOT / "data" / "tisi-two-stroke-oil-licences-report.json"
SOURCE_ID = "TISI_TWO_STROKE_OIL_LICENCES"
STANDARD = "TIS 1040-2541"
STANDARD_NUMBER = "1040-2541"
STANDARD_TITLE_EN = "Two-stroke gasoline engine lubricating oil"
SOURCE_URL = (
    "https://appdb.tisi.go.th/tis_dev/p4_license_report/"
    "p4license_report.php?data=tis&txt_tis=1040-2541"
)
DATASET_URL = "https://www.data.go.th/dataset/tis_hav_lic_total"
STANDARD_URL = "https://a.tisi.go.th/t/?n=1040-2541"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-data)"


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def plain(fragment: str) -> str:
    return clean(re.sub(r"<[^>]+>", " ", fragment))


def buddhist_date(value: str) -> str:
    day, month, year = map(int, clean(value).split("-"))
    if year < 2400:
        raise RuntimeError(f"Expected a Thai Buddhist year, received {value!r}")
    return date(year - 543, month, day).isoformat()


def fetch() -> bytes:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError("TISI returned an empty response")
    return payload


def parse_rows(payload: bytes) -> list[dict]:
    text = payload.decode("utf-8", errors="replace")
    table = re.search(r'<table[^>]+id="table1".*?</table>', text, re.I | re.S)
    if not table:
        raise RuntimeError("TISI licence table is missing")
    rows = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(0), re.I | re.S)[1:]:
        cells = [plain(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.I | re.S)]
        if not cells or not any(cells):
            continue
        if len(cells) != 7:
            raise RuntimeError(f"Unexpected TISI result row: {cells!r}")
        permit, permit_type, issued, standard_scope, holder, _document, _details = cells
        if not all([permit, permit_type, issued, standard_scope, holder]):
            raise RuntimeError(f"Incomplete TISI result row: {cells!r}")
        if permit_type != "ทำ":
            raise RuntimeError(f"Unexpected TISI permit type: {permit_type!r}")
        if not standard_scope.startswith(f"{STANDARD_NUMBER} :"):
            raise RuntimeError(f"Unexpected TISI standard scope: {standard_scope!r}")
        rows.append({
            "permit_number": permit,
            "permit_type_source_reported": permit_type,
            "permit_type": "manufacturing",
            "issued_at": buddhist_date(issued),
            "issued_at_source_reported": issued,
            "standard_scope_source_reported": standard_scope,
            "licence_holder": holder,
        })
    if len(rows) != 10:
        raise RuntimeError(f"Expected 10 TISI licences in the current snapshot, received {len(rows)}")
    if len({row["permit_number"] for row in rows}) != len(rows):
        raise RuntimeError("TISI result contains a duplicate permit number")
    return rows


def main() -> None:
    payload = fetch()
    source_rows = parse_rows(payload)
    records = []
    for row in sorted(source_rows, key=lambda item: item["permit_number"]):
        source_facts = {key: row[key] for key in sorted(row)}
        record_id = hashlib.sha256(row["permit_number"].encode("utf-8")).hexdigest()[:20]
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"TISI-{record_id}",
            "source_url": SOURCE_URL,
            "dataset_url": DATASET_URL,
            "standard_url": STANDARD_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Thailand",
            "permit_number": row["permit_number"],
            "permit_type": row["permit_type"],
            "permit_type_source_reported": row["permit_type_source_reported"],
            "manufacturer": row["licence_holder"],
            "brand": row["licence_holder"],
            "product_name": f"{row['licence_holder']} — {STANDARD} certified holder scope",
            "product_name_basis": "source_reported_certified_holder_scope_not_individual_brand_grade_or_sku",
            "certified_product_scope": STANDARD_TITLE_EN,
            "certified_product_scope_source_reported": row["standard_scope_source_reported"],
            "family_code": "M",
            "technical": {
                "certified_standard": [STANDARD],
                "sae": [],
                "api": [],
            },
            "issued_at": row["issued_at"],
            "issued_at_source_reported": row["issued_at_source_reported"],
            "lifecycle_status": "published_in_current_tisi_licence_search_current_validity_not_independently_stated",
            "source_quality_flags": [
                "licence_covers_holder_scope_not_individual_commercial_product",
                "no_source_reported_brand_sae_or_api_grade",
                "current_validity_not_independently_stated",
            ],
            "source_facts_sha256": hashlib.sha256(
                json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "evidence_status": "official_government_product_certification_holder_scope",
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records
    )
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_thailand_two_stroke_oil_manufacturing_licences_normalized",
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "dataset_url": DATASET_URL,
        "standard_url": STANDARD_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "standard": STANDARD,
        "source_occurrences": len(source_rows),
        "normalized_licence_holder_scopes": len(records),
        "unique_licence_holders": len({row["manufacturer"] for row in records}),
        "permit_types": dict(sorted(Counter(row["permit_type"] for row in records).items())),
        "issue_year_range": [min(row["issued_at"] for row in records)[:4], max(row["issued_at"] for row in records)[:4]],
        "families": {"M": len(records)},
        "source_response_sha256": hashlib.sha256(payload).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "grain_note": "One row is one TISI manufacturing licence + exact licence holder + TIS 1040-2541 certified scope. It is not a marketed brand, grade or SKU.",
        "technical_note": "TIS 1040-2541 is retained as certification evidence. No SAE or API value is inferred because the public result does not publish one.",
        "lifecycle_note": "The row appears in the current public licence search, but the result does not explicitly state a current-validity flag or expiry date.",
        "rights_note": "The official data.go.th dataset page publishes the source under Creative Commons Attribution; source and dataset URLs are retained for attribution.",
        "privacy_note": "Only company-level licence facts are retained; no addresses, tax identifiers, contacts or personal data are collected.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
