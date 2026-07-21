#!/usr/bin/env python3
"""Ingest factual hydraulic-fluid ratings from Parker Denison's public list."""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "parker-denison-fluid-ratings.jsonl"
REPORT = ROOT / "data" / "parker-denison-fluid-ratings-report.json"
SOURCE_ID = "PARKER_DENISON_CURRENT_FLUID_RATINGS"
SOURCE_PAGE = "https://discover.parker.com/hydraulic-fluid-evaluation-process"
PDF_URL = (
    "https://images.solutions.parker.com/Web/Parker/"
    "%7B07ef2fe8-ccb4-406e-bff7-d48dd318ca71%7D_MSG30-0004_Parker-Denison_fluid_ratings.pdf"
)
SNAPSHOT_DATE = "2026-07-21"
REVIEW_DATE = "2026-04-14"
EXPECTED_PDF_SHA256 = "a32d4aa248adc30eae63b00b3433272f0d9e37e19a22ff5c7aad66d68294ebc1"


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def fetch() -> bytes:
    request = urllib.request.Request(
        PDF_URL,
        headers={"User-Agent": "MFClassifierResearch/1.0 (official-OEM-fluid-ratings)"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def classification(raw: str) -> tuple[list[str], list[str]]:
    compact = raw.replace(" ", "")
    flags = []
    if compact in {"HF01", "HF02"}:
        flags.append(f"source_{compact.casefold()}_superscript_footnote_normalized_to_hf0")
        compact = "HF0"
    values = []
    for value in re.findall(r"HF[0-6](?:[a-e])?", compact, re.I):
        normalized = value.upper()[:-1] + value[-1].lower() if value[-1].isalpha() else value.upper()
        if normalized not in values:
            values.append(normalized)
    return values, flags


def lifecycle(validity: str) -> tuple[str, list[str]]:
    match = re.fullmatch(r"(\d{4})-(\d{2})", validity)
    if not match or not 1 <= int(match.group(2)) <= 12:
        return "source_validity_value_invalid_review_required", ["source_invalid_validity_month_retained_verbatim"]
    if validity < SNAPSHOT_DATE[:7]:
        return "published_rating_expired_by_validity_month_as_of_snapshot", []
    return "published_rating_not_expired_by_validity_month_as_of_snapshot", []


def main() -> None:
    payload = fetch()
    pdf_sha256 = hashlib.sha256(payload).hexdigest()
    assert pdf_sha256 == EXPECTED_PDF_SHA256
    records = []
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        assert len(pdf.pages) == 8
        assert "Review Date: 4/14/2026" in (pdf.pages[0].extract_text() or "")
        for page_number in range(2, 8):
            tables = pdf.pages[page_number - 1].extract_tables()
            assert len(tables) == 1
            table = tables[0]
            assert clean(table[0][0]).casefold() == "manufacturer"
            assert clean(table[0][1]).casefold() in {"commercial name", "commercial name"}
            for source_table_row, row in enumerate(table[1:], 2):
                if len(row) != 11:
                    raise AssertionError((page_number, source_table_row, len(row)))
                manufacturer, product_name = clean(row[0]), clean(row[1])
                if not manufacturer and not product_name:
                    continue
                assert manufacturer and product_name
                grade_marks = {str(grade): clean(row[index]) for grade, index in ((32, 2), (46, 3), (68, 4))}
                assert all(not mark or re.fullmatch(r"X[23]?", mark) for mark in grade_marks.values())
                approved_iso_vg = [grade for grade, mark in grade_marks.items() if mark]
                class_raw = clean(row[9])
                classes, class_flags = classification(class_raw)
                assert classes
                validity = clean(row[10])
                lifecycle_status, validity_flags = lifecycle(validity)
                quality_flags = class_flags + validity_flags
                identity = "|".join((manufacturer.casefold(), product_name.casefold(), class_raw.casefold(), validity))
                source_record_id = "PARKER-DENISON-" + hashlib.sha256(identity.encode()).hexdigest()[:20].upper()
                records.append({
                    "source_id": SOURCE_ID,
                    "source_record_id": source_record_id,
                    "manufacturer": manufacturer,
                    "brand": manufacturer,
                    "product_name": product_name,
                    "family_code": "H",
                    "market": "GLOBAL_PARKER_DENISON",
                    "specifications": {
                        "parker_denison_hf_classification_source_reported": class_raw,
                        "parker_denison_hf_classes": classes,
                        "approved_iso_vg": approved_iso_vg,
                        "iso_vg_rating_marks_source_reported": grade_marks,
                        "ashless": clean(row[5]) == "X",
                        "zinc_free": clean(row[6]) == "X",
                        "iso_6743_hm": clean(row[7]) == "X",
                        "iso_6743_hv": clean(row[8]) == "X",
                        "rating_procedures": ["TP-30532", "TP-30533"],
                    },
                    "rating_validity_until_source_reported": validity,
                    "rating_list_review_date": REVIEW_DATE,
                    "lifecycle_status": lifecycle_status,
                    "source_page": page_number,
                    "source_table_row": source_table_row,
                    "source_url": SOURCE_PAGE,
                    "source_document_url": PDF_URL,
                    "snapshot_date": SNAPSHOT_DATE,
                    "source_quality_flags": quality_flags,
                })

    records.sort(key=lambda row: (
        row["manufacturer"].casefold(), row["product_name"].casefold(),
        row["rating_validity_until_source_reported"], row["source_record_id"],
    ))
    assert len(records) == 217
    assert len({row["source_record_id"] for row in records}) == len(records)
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_url": SOURCE_PAGE,
        "source_document_url": PDF_URL,
        "source_document_sha256": pdf_sha256,
        "source_document_pages": 8,
        "rating_list_review_date": REVIEW_DATE,
        "normalized_rating_rows": len(records),
        "manufacturers": len({row["manufacturer"] for row in records}),
        "rows_by_lifecycle": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "rows_by_hf_class": dict(sorted(Counter(
            value for row in records for value in row["specifications"]["parker_denison_hf_classes"]
        ).items())),
        "rows_by_iso_vg": dict(sorted(Counter(
            value for row in records for value in row["specifications"]["approved_iso_vg"]
        ).items())),
        "source_quality_flags": dict(sorted(Counter(
            flag for row in records for flag in row["source_quality_flags"]
        ).items())),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Attributed non-expressive rating facts only: manufacturer, commercial name, ISO VG rating columns, HM/HV, ashless/zinc-free, HF classification, validity and source coordinates. Narrative text and document layout are not republished.",
        "lifecycle_note": "Validity is evaluated only at published month granularity. A malformed source month remains verbatim and is not repaired by inference.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
