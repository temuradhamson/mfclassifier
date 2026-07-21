#!/usr/bin/env python3
"""Normalize lubricant rows from the Green Choice Philippines licence checker."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "green-choice-philippines-lubricants.jsonl"
REPORT = ROOT / "data" / "green-choice-philippines-lubricants-report.json"
SOURCE_PAGE_URL = "https://pcepsdi.org.ph/check-gcp-seal/"
SOURCE_AJAX_URL = "https://pcepsdi.org.ph/wp-admin/admin-ajax.php"
PROGRAM_URL = "https://pcepsdi.org.ph/programme/green-choice-philippines/"
CRITERIA_URL = "https://pcepsdi.org.ph/programme/green-choice-philippines/gcp-criteria/"
USER_AGENT = "MFClassifierResearch/1.0 (national-ecolabel-public-register research)"
TABLES = {11: "active", 12: "expired", 13: "ongoing_renewal"}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.cell = ""
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.in_cell = True
            self.cell = ""

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"}:
            self.row.append(clean(self.cell))
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)


def fetch_page_and_nonce() -> tuple[bytes, str]:
    request = urllib.request.Request(SOURCE_PAGE_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read()
    match = re.search(rb'var front_end_data = .*?"nonce":"([a-f0-9]+)"', raw, re.S)
    assert match, "public table nonce missing"
    return raw, match.group(1).decode()


def fetch_table(table_id: int, nonce: str) -> tuple[bytes, list[list[str]]]:
    payload = urllib.parse.urlencode({
        "action": "gswpts_sheet_fetch",
        "id": str(table_id),
        "nonce": nonce,
    }).encode()
    request = urllib.request.Request(
        SOURCE_AJAX_URL,
        data=payload,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read()
    document = json.loads(raw)
    assert document["success"] is True
    parser = TableParser()
    parser.feed(document["data"]["output"])
    assert parser.rows[0] == [
        "Sector/Industry", "License No.", "Company Name", "Product/Brands", "GCP Criteria",
    ]
    return raw, parser.rows[1:]


def technical(product_name: str) -> dict:
    reported = re.findall(r"\b(?:SAE\s*)?([0-9S]{1,2}W[- ]?\d{2,3})\b", product_name, re.I)
    reported = [value.upper().replace(" ", "-") for value in reported]
    valid = [value for value in reported if re.fullmatch(r"(?:0|5|10|15|20|25)W-?\d{2,3}", value)]
    return {
        "sae_source_reported": reported,
        "sae_validated": valid,
        "source_quality_flags": ["nonstandard_sae_notation_retained_verbatim"] if set(reported) - set(valid) else [],
    }


def main() -> None:
    source_page_raw, nonce = fetch_page_and_nonce()
    table_rows: dict[str, list[list[str]]] = {}
    table_hashes = {}
    for table_id, status in TABLES.items():
        raw, rows = fetch_table(table_id, nonce)
        table_rows[status] = rows
        table_hashes[status] = hashlib.sha256(raw).hexdigest()

    # Counts make upstream spreadsheet changes explicit rather than silently
    # accepting a materially different register shape.
    assert {status: len(rows) for status, rows in table_rows.items()} == {
        "active": 34, "expired": 35, "ongoing_renewal": 7,
    }

    candidates = []
    for status, rows in table_rows.items():
        for source_row_number, row in enumerate(rows, 1):
            sector, licence, company, product_name, criterion = row
            if criterion == "GCP 2008032 Automotive Engine Oil":
                candidates.append((status, source_row_number, sector, licence, company, product_name, criterion))

    assert len(candidates) == 3
    assert {row[0] for row in candidates} == {"expired"}
    assert {row[3] for row in candidates} == {"000009", "000010", "000011"}

    records = []
    for status, row_number, sector, licence, company, product_name, criterion in candidates:
        records.append({
            "source_id": "GREEN_CHOICE_PHILIPPINES_ENGINE_OILS",
            "source_record_id": f"GCP-{licence}",
            "source_url": SOURCE_PAGE_URL,
            "source_ajax_url": SOURCE_AJAX_URL,
            "program_url": PROGRAM_URL,
            "criteria_url": CRITERIA_URL,
            "snapshot_date": date.today().isoformat(),
            "market": "Philippines",
            "manufacturer": company,
            "product_name": product_name,
            "certificate_number": licence,
            "official_sector": sector,
            "official_criterion": criterion,
            "official_criterion_code": "GCP 2008032",
            "lifecycle_status": "ecolabel_certificate_expired",
            "source_table_status": status,
            "source_row_number": row_number,
            "family_code": "M",
            "classification_basis": "official_GCP_2008032_automotive_engine_oil_criterion",
            "technical": technical(product_name),
        })

    records.sort(key=lambda row: row["certificate_number"])
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "official_national_ecolabel_historical_engine_oils_normalized",
        "snapshot_date": date.today().isoformat(),
        "source_page_url": SOURCE_PAGE_URL,
        "source_ajax_url": SOURCE_AJAX_URL,
        "program_url": PROGRAM_URL,
        "criteria_url": CRITERIA_URL,
        "source_table_rows": {status: len(rows) for status, rows in table_rows.items()},
        "source_table_response_sha256": table_hashes,
        "source_page_sha256": hashlib.sha256(source_page_raw).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "normalized_products": len(records),
        "manufacturers": len({row["manufacturer"] for row in records}),
        "lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "source_quality_flags": dict(sorted(Counter(flag for row in records for flag in row["technical"]["source_quality_flags"]).items())),
        "rights_note": "The national Green Choice Philippines programme publishes the licence checker as its public verification register. Only factual licence, holder, product, criterion and lifecycle fields are normalized with attribution; page design, logos, addresses and narrative content are omitted.",
        "lifecycle_note": "All three lubricant records occur only in the official Expired table. They are historical product evidence and must not be represented as currently certified or currently marketed products.",
        "quality_note": "The source spelling 'SW-40' is retained verbatim and flagged as non-standard. It is not silently corrected to a guessed SAE grade.",
        "grain_note": "One row is one published GCP licence number and named automotive engine-oil product.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "normalized_products": len(records),
        "source_table_rows": report["source_table_rows"],
        "lifecycle_statuses": report["lifecycle_statuses"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
