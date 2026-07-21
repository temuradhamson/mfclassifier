#!/usr/bin/env python3
"""Normalize historical product-grade approvals from Mack service bulletin 175-61-08."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "mack-2014-approved-oils.jsonl"
REPORT = ROOT / "data" / "mack-2014-approved-oils-report.json"
SOURCE_ID = "MACK_2014_APPROVED_OILS"
SOURCE_URL = "https://sv.macktrucks.com/media/files/body-builder/pv776-89149448.pdf"
SNAPSHOT_DATE = "2026-07-21"
DOCUMENT_DATE = "2014-04"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"


SECTIONS = []
for page in range(3, 16):
    SECTIONS.append((page, 0, 1, "EO-O Premium Plus", "M", ["Mack EO-O Premium Plus", "Volvo VDS-4", "Volvo VDS-3", "Volvo VDS-2", "Mack EO-N Premium Plus", "API CJ-4"]))
for page in range(16, 18):
    SECTIONS.append((page, 0, 1, "EO-N Premium Plus", "M", ["Mack EO-N Premium Plus"]))
SECTIONS.extend([
    (18, 2, 2, "mDRIVE extended drain", "T", ["Mack mDRIVE", "Volvo transmission oils 97318/97319 source-section scope"]),
    (18, 3, 2, "mDRIVE regular drain", "T", ["Mack mDRIVE", "Volvo transmission oils 97307/97315 source-section scope"]),
    (19, 0, 1, "mDRIVE regular drain", "T", ["Mack mDRIVE", "Volvo transmission oils 97307/97315 source-section scope"]),
])
for page in range(19, 22):
    SECTIONS.append((page, 2 if page == 19 else 0, 1, "TO-A Plus", "T", ["Mack TO-A Plus"]))
for page in range(22, 27):
    SECTIONS.append((page, 1 if page == 22 else 0, 1, "GO-J", "T", ["Mack GO-J"]))
for page in range(27, 30):
    SECTIONS.append((page, 0, 1, "GO-J Plus", "T", ["Mack GO-J Plus"]))


GRADE_PATTERN = re.compile(
    r"(?<!\d)((?:0|5|10|15)W[-–]?\d{2}|(?:75|80|85)W[-–]?\d{2,3}|SAE\s*50)(?!\d)",
    re.I,
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
        if response.headers.get("Content-Encoding", "").casefold() == "gzip" or payload[:2] == b"\x1f\x8b":
            payload = gzip.decompress(payload)
        return payload


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\u00ad", "")).strip()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def normalize_grade(value: str) -> str:
    value = value.upper().replace("–", "-").replace(" ", "")
    return "SAE 50" if value == "SAE50" else value


def main() -> None:
    payload = fetch(SOURCE_URL)
    cache_pdf = ROOT / ".cache" / "mack-2014-approved-oils.pdf"
    cache_pdf.parent.mkdir(parents=True, exist_ok=True)
    cache_pdf.write_bytes(payload)

    parsed = []
    last_supplier: dict[str, str] = {}
    with pdfplumber.open(cache_pdf) as pdf:
        assert len(pdf.pages) == 29
        document_text = " ".join((page.extract_text() or "") for page in pdf.pages[:3])
        assert "4.2014" in document_text and "mackeoopremiumplusapprovedengineoils" in normalized(document_text)
        for page_number, table_index, first_data_row, section, family, approvals in SECTIONS:
            tables = pdf.pages[page_number - 1].extract_tables({"text_x_tolerance": 1})
            table = tables[table_index]
            for table_row_number, cells in enumerate(table[first_data_row:], first_data_row):
                supplier, product_name_source, viscosity_source = [clean(value) for value in cells[:3]]
                if supplier.startswith("Regular drains:"):
                    continue
                if supplier:
                    last_supplier[section] = supplier
                else:
                    supplier = last_supplier.get(section, "")
                flags = []
                if not viscosity_source and GRADE_PATTERN.search(product_name_source):
                    viscosity_source = normalize_grade(GRADE_PATTERN.search(product_name_source).group(1))
                    flags.append("viscosity_inferred_from_product_name_due_empty_table_cell")
                grades = [normalize_grade(value) for value in GRADE_PATTERN.findall(viscosity_source)]
                assert supplier and product_name_source and grades, (page_number, cells)
                if len(grades) > 1:
                    flags.append("source_multi_grade_approval_row_split")
                for grade in grades:
                    source_grade_match = GRADE_PATTERN.search(product_name_source)
                    if source_grade_match and normalized(source_grade_match.group(1)) == normalized(grade):
                        product_name = GRADE_PATTERN.sub(grade, product_name_source, count=1)
                    else:
                        product_name = f"{product_name_source} {grade}"
                    parsed.append({
                        "section": section,
                        "family_code": family,
                        "supplier": supplier,
                        "product_name_source": product_name_source,
                        "product_name": product_name,
                        "viscosity_source": viscosity_source,
                        "grade": grade,
                        "approvals_source_section_scope": approvals,
                        "source_occurrence": {"page": page_number, "table_row": table_row_number, "section": section},
                        "source_quality_flags": flags,
                    })

    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in parsed:
        grouped[(normalized(row["supplier"]), normalized(row["product_name"]), normalized(row["grade"]), row["family_code"])].append(row)

    records = []
    for key, occurrences in sorted(grouped.items()):
        row = occurrences[0]
        flags = {flag for value in occurrences for flag in value["source_quality_flags"]}
        sections = sorted({value["section"] for value in occurrences})
        source_identity_keys = {
            (value["section"], normalized(value["supplier"]), normalized(value["product_name_source"]), normalized(value["grade"]))
            for value in occurrences
        }
        if len(occurrences) > len(source_identity_keys):
            flags.add("source_duplicate_approval_row_merged")
        if len(sections) > 1:
            flags.add("cross_section_same_product_identity_merged")
        if len({normalized(value["product_name_source"]) for value in occurrences}) > 1:
            flags.add("source_name_grade_notation_variants_merged")
        record_hash = hashlib.sha256("|".join(key).encode()).hexdigest()[:20]
        approvals = sorted({
            approval for value in occurrences
            for approval in value["approvals_source_section_scope"]
        })
        specifications = {
            "sae_engine" if row["family_code"] == "M" else "sae_gear": row["grade"],
            "mack_approval_sections": sections,
            "oem_approvals_source_section_scope": approvals,
            "viscosity_source_reported": sorted({value["viscosity_source"] for value in occurrences}),
        }
        if "EO-O Premium Plus" in sections:
            specifications["api"] = ["CJ-4"]
            specifications["volvo_standards"] = ["VDS-4", "VDS-3", "VDS-2"]
            specifications["mack_standards"] = ["EO-O Premium Plus", "EO-N Premium Plus"]
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"MACK-2014-{record_hash}",
            "brand": row["supplier"],
            "manufacturer": row["supplier"],
            "product_name": row["product_name"],
            "product_name_source": row["product_name_source"],
            "family_code": row["family_code"],
            "market": "GLOBAL_MACK_HISTORICAL_BULLETIN",
            "source_url": SOURCE_URL,
            "source_document": "Mack Service Bulletin 175-61-08, PV776-89149448",
            "source_document_date": DOCUMENT_DATE,
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "historical_approval_as_published_2014_04_current_status_unverified",
            "specifications": specifications,
            "source_occurrences": [value["source_occurrence"] for value in occurrences],
            "source_quality_flags": sorted(flags),
        })

    assert len(parsed) == 806
    section_identity_keys = {
        (row["section"], normalized(row["supplier"]), normalized(row["product_name_source"]), normalized(row["grade"]))
        for row in parsed
    }
    assert len(section_identity_keys) == 805
    assert len(records) == 803
    assert sum(len(row["source_occurrences"]) for row in records) == 806
    assert len({row["source_record_id"] for row in records}) == len(records)
    assert Counter(row["section"] for row in parsed if (
        row["section"], normalized(row["supplier"]), normalized(row["product_name_source"]), normalized(row["grade"])
    ) in section_identity_keys) == {
        "EO-O Premium Plus": 435,
        "EO-N Premium Plus": 45,
        "mDRIVE extended drain": 6,
        "mDRIVE regular drain": 18,
        "TO-A Plus": 80,
        "GO-J": 128,
        "GO-J Plus": 94,
    }

    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "document_date": DOCUMENT_DATE,
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_pdf_sha256": hashlib.sha256(payload).hexdigest(),
        "pdf_pages": 29,
        "approval_occurrences": len(parsed),
        "source_section_product_grade_rows": len(section_identity_keys),
        "normalized_products": len(records),
        "duplicate_source_occurrences_merged": len(parsed) - len(section_identity_keys),
        "cross_section_or_notation_identity_merges": len(section_identity_keys) - len(records),
        "sections": dict(sorted(Counter(row["section"] for row in parsed).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "source_quality_flags": dict(sorted(Counter(flag for row in records for flag in row["source_quality_flags"]).items())),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Attributed derived factual approval rows only; bulletin prose, layout, artwork and images are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
