#!/usr/bin/env python3
"""Normalize lubricant and coolant rows from Ghana GSA's 2025 register.

The official PDF is a monthly decision register rather than a machine-readable
dataset.  The 16 relevant rows below are an audited transcription.  A pinned
PDF hash makes the transcription reproducible and forces a review when GSA
replaces the document at the same URL.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "ghana-gsa-certified-lubricant-products.jsonl"
REPORT = ROOT / "data" / "ghana-gsa-certified-lubricant-products-report.json"
SOURCE_ID = "GSA_GHANA_2025_CERTIFIED_LUBRICANT_PRODUCTS"
SOURCE_URL = "https://gsa.gov.gh/wp-content/uploads/2018/04/2025-CERTIFIED-LIST-JAN.-SEP.pdf"
LANDING_URL = "https://gsa.gov.gh/product-certification/"
SNAPSHOT_DATE = "2026-07-21"
EXPECTED_PDF_SHA256 = "8085170f9bdff86278d07c43b0375cd77727e6dde84f4320cc8403d7d7bd7bc2"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-data)"


# page_index is zero-based and matches PDF tooling. source_item_number is the
# number printed inside that month's table, so both coordinates are retained.
ROWS = [
    dict(page_index=8, item=98, holder="Yota Energy Ghana Ltd", source_product="Motor Oil 4T 15W-40 (Yota)", brand="Yota", product="Yota Motor Oil 4T 15W-40", family="M", sae=["15W-40"], api=[], standard="GS 826-2:2022", licence="GSA-PCM-L-A-2669-003", holder_licence="GSA-PCM-A-2669", issued="2025-01-28", expires="2026-01-27"),
    dict(page_index=73, item=78, holder="Rikpat Company Limited", source_product="Engine Lubricating Oil SAE 0W-20, API-SP (Seahorse Prime)", brand="Seahorse", product="Seahorse Prime Engine Oil SAE 0W-20 API SP", family="M", sae=["0W-20"], api=["SP"], standard="GS 816-2:2022", licence="GSA-PCM-L-A-2221-009", holder_licence="GSA-PCM-A-2221", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=73, item=79, holder="Rikpat Company Limited", source_product="Engine Lubricating Oil SAE 5W-40, API CK-4 (Seahorse Classic)", brand="Seahorse", product="Seahorse Classic Engine Oil SAE 5W-40 API CK-4", family="M", sae=["5W-40"], api=["CK-4"], standard="GS 826-2:2022", licence="GSA-PCM-L-A-2221-010", holder_licence="GSA-PCM-A-2221", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=73, item=80, holder="Rikpat Company Limited", source_product="Engine Lubricating Oil SAE 15W-40, API CI-4 (Seahorse Classic)", brand="Seahorse", product="Seahorse Classic Engine Oil SAE 15W-40 API CI-4", family="M", sae=["15W-40"], api=["CI-4"], standard="GS 826-2:2022", licence="GSA-PCM-L-A-2221-004", holder_licence="GSA-PCM-A-2221", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=73, item=81, holder="Rikpat Company Limited", source_product="Engine Lubricating Oil SAE 5W-30, API-SP (Seahorse Prime)", brand="Seahorse", product="Seahorse Prime Engine Oil SAE 5W-30 API SP", family="M", sae=["5W-30"], api=["SP"], standard="GS 816-2:2022", licence="GSA-PCM-L-A-2221-011", holder_licence="GSA-PCM-A-2221", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=73, item=82, holder="Rikpat Company Limited", source_product="Engine Lubricating Oil SAE 5W-20, API-SP (Seahorse Prime)", brand="Seahorse", product="Seahorse Prime Engine Oil SAE 5W-20 API SP", family="M", sae=["5W-20"], api=["SP"], standard="GS 816-2:2022", licence="GSA-PCM-L-A-2221-012", holder_licence="GSA-PCM-A-2221", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=74, item=83, holder="Rikpat Company Limited", source_product="Engine Lubricating Oil SAE 10W-40, API SN (Seahorse Classic)", brand="Seahorse", product="Seahorse Classic Engine Oil SAE 10W-40 API SN", family="M", sae=["10W-40"], api=["SN"], standard="GS 816-2:2022", licence="GSA-PCM-L-A-2221-013", holder_licence="GSA-PCM-A-2221", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=74, item=84, holder="Rikpat Company Limited", source_product="Motorcycle Engine Oil 20W50 (Seahorse Classic 4T)", brand="Seahorse", product="Seahorse Classic 4T Motorcycle Engine Oil SAE 20W-50", family="M", sae=["20W-50"], api=[], standard="GS 816-2:2022", licence="GSA-PCM-L-A-2221-014", holder_licence="GSA-PCM-A-2221", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=77, item=108, holder="Greenwich Industries Limited", source_product="Engine Lubricating Oil, 20W50 API SL/CF (Super Palco)", brand="Super Palco", product="Super Palco Engine Oil SAE 20W-50 API SL/CF", family="M", sae=["20W-50"], api=["SL", "CF"], standard="GS 816-2:2022", licence="GSA-PCM-L-A-1067-002", holder_licence="GSA-PCM-A-1067", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=77, item=109, holder="Greenwich Industries Limited", source_product="Engine Lubricating Oil, 4T Stroke Boss, 20W50, API SJ (Super Palco)", brand="Super Palco", product="Super Palco 4T Stroke Boss Engine Oil SAE 20W-50 API SJ", family="M", sae=["20W-50"], api=["SJ"], standard="GS 816-2:2022", licence="GSA-PCM-L-A-1067-010", holder_licence="GSA-PCM-A-1067", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=77, item=110, holder="Greenwich Industries Limited", source_product="Gear Oil, SAE-140 (Greenol)", brand="Greenol", product="Greenol Gear Oil SAE 140", family="T", sae=["140"], api=[], standard="GS 1027:2022", licence="GSA-PCM-L-A-1067-011", holder_licence="GSA-PCM-A-1067", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=77, item=111, holder="Greenwich Industries Limited", source_product="Gear Oil, EP-140, API GL-4 (Super Palco)", brand="Super Palco", product="Super Palco Gear Oil EP SAE 140 API GL-4", family="T", sae=["140"], api=["GL-4"], standard="GS 1027:2022", licence="GSA-PCM-L-A-1067-006", holder_licence="GSA-PCM-A-1067", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=77, item=112, holder="Greenwich Industries Limited", source_product="Engine Lubricating Oil Hitech 15W40, API CI-4/SL (Super Palco)", brand="Super Palco", product="Super Palco Hitech Engine Oil SAE 15W-40 API CI-4/SL", family="M", sae=["15W-40"], api=["CI-4", "SL"], standard="GS 807-2:2022", licence="GSA-PCM-L-A-1067-013", holder_licence="GSA-PCM-A-1067", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=77, item=113, holder="Greenwich Industries Limited", source_product="Engine Lubricating Oil PHD 15W40, API CF (Super Palco)", brand="Super Palco", product="Super Palco PHD Engine Oil SAE 15W-40 API CF", family="M", sae=["15W-40"], api=["CF"], standard="GS 816-2:2022", licence="GSA-PCM-L-A-1067-014", holder_licence="GSA-PCM-A-1067", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=78, item=114, holder="Greenwich Industries Limited", source_product="Engine Lubricating Oil, Diesel / Petrol Engine Oil, SAE-50, API SC/CC (Greenol)", brand="Greenol", product="Greenol Diesel / Petrol Engine Oil SAE 50 API SC/CC", family="M", sae=["50"], api=["SC", "CC"], standard="GS 826-1:2022", licence="GSA-PCM-L-A-1067-001", holder_licence="GSA-PCM-A-1067", issued="2025-07-30", expires="2026-07-29"),
    dict(page_index=108, item=59, holder="RP Auto Products Ventures", source_product="Autochem C Radiator Coolant", brand="Autochem C", product="Autochem C Radiator Coolant", family="TF", sae=[], api=[], standard="ASTM D3306:2021", licence="GSA-PCM-L-A-2675-001", holder_licence="GSA-PCM-A-2675", issued="2025-09-30", expires="2026-09-29"),
]


def fetch_pdf() -> bytes:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    if not payload.startswith(b"%PDF-"):
        raise RuntimeError("GSA source did not return a PDF")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_PDF_SHA256:
        raise RuntimeError(f"GSA PDF changed: expected {EXPECTED_PDF_SHA256}, got {digest}")
    return payload


def row_hash(row: dict) -> str:
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def normalize(row: dict) -> dict:
    lifecycle = (
        "certification_valid_as_of_catalog_snapshot"
        if date.fromisoformat(row["expires"]) >= date.fromisoformat(SNAPSHOT_DATE)
        else "certification_expired_before_catalog_snapshot"
    )
    technical = {
        "sae": row["sae"],
        "api": row["api"],
        "certified_standard": [row["standard"]],
    }
    if row["family"] == "TF":
        technical["coolant_standard"] = [row["standard"]]
    record_id = "GSA-GH-2025-" + hashlib.sha256(row["licence"].encode()).hexdigest()[:16].upper()
    return {
        "source_id": SOURCE_ID,
        "source_record_id": record_id,
        "source_url": SOURCE_URL,
        "source_landing_url": LANDING_URL,
        "source_pdf_page_index": row["page_index"],
        "source_item_number": row["item"],
        "source_product_field": row["source_product"],
        "source_facts_sha256": row_hash(row),
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "market": "Ghana",
        "manufacturer_or_certificate_holder": row["holder"],
        "brand": row["brand"],
        "product_name": row["product"],
        "family_code": row["family"],
        "technical": technical,
        "licence_number": row["licence"],
        "holder_licence_number": row["holder_licence"],
        "issued_at": row["issued"],
        "expires_at": row["expires"],
        "lifecycle_status": lifecycle,
        "evidence_status": "official_government_product_certification_registry",
        "source_quality_flags": [],
    }


def main() -> None:
    payload = fetch_pdf()
    records = sorted((normalize(row) for row in ROWS), key=lambda row: row["source_record_id"])
    if len(records) != 16 or len({row["licence_number"] for row in records}) != 16:
        raise RuntimeError("Curated GSA row set must contain 16 unique product licences")
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "status": "official_ghana_gsa_2025_product_certification_evidence_normalized",
        "source_url": SOURCE_URL,
        "source_pdf_sha256": hashlib.sha256(payload).hexdigest(),
        "source_pdf_pages": 112,
        "source_period": "January-September 2025",
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "audited_relevant_source_rows": len(ROWS),
        "normalized_products": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "rows_with_sae": sum(bool(row["technical"]["sae"]) for row in records),
        "rows_with_api": sum(bool(row["technical"]["api"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "method": "audited transcription pinned to the official PDF SHA-256; exact page index, item, licence, standard and dates retained",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
