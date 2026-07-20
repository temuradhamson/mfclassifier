#!/usr/bin/env python3
"""Download and normalize current Driventic (formerly Voith DIWA) oil lists."""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

import pdfplumber
from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "driventic-diwa-approved-oils.jsonl"
REPORT = ROOT / "data" / "driventic-diwa-approved-oils-report.json"
LANDING_URL = "https://www.driventic.com/products/bus/diwa-automatic-transmission"
API = "https://www.driventic.com/api/canto/share?key=OAPC5U8N9T&pn={}"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"
TABLE_SETTINGS = {"vertical_strategy": "text", "horizontal_strategy": "lines", "intersection_tolerance": 5}
LISTS = [
    {"publication_number": "DR1026", "interval_km": 60000, "list_date": "2022-01-17", "products": 135},
    {"publication_number": "DR1025", "interval_km": 120000, "list_date": "2022-01-17", "products": 70},
    {"publication_number": "DR1024", "interval_km": 180000, "list_date": "2025-03-06", "products": 20},
    {"publication_number": "DR1023", "interval_km": 240000, "list_date": "2025-08-20", "products": 1},
]


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\x03", " ")).strip()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def rotated_page(payload: bytes, page_index: int) -> io.BytesIO:
    page = PdfReader(io.BytesIO(payload)).pages[page_index]
    page.rotate(90)
    writer = PdfWriter()
    writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output


def has_approval_mark(row: list[str | None]) -> bool:
    return any(clean(cell).casefold() == "x" for cell in row[2:])


def parse_default_tables(payload: bytes) -> list[dict]:
    """Parse the 60k and 180k layouts, whose ruled tables retain both identity columns."""
    rows = []
    page_count = len(PdfReader(io.BytesIO(payload)).pages)
    for page_index in range(page_count):
        with pdfplumber.open(rotated_page(payload, page_index)) as pdf:
            tables = [table for table in pdf.pages[0].extract_tables() if len(table) > 20 and len(table[0]) >= 8]
        if not tables:
            continue
        supplier = ""
        flags_pending = False
        supplier_continues_current = False
        for row in max(tables, key=len):
            source_supplier = clean(row[0])
            product_name = clean(row[1])
            marked = has_approval_mark(row)
            if source_supplier and not product_name:
                if marked:
                    supplier = source_supplier
                    flags_pending = True
                    supplier_continues_current = False
                elif rows and rows[-1]["page"] == page_index + 1:
                    if source_supplier.startswith("(") or rows[-1].get("_explicit_supplier"):
                        rows[-1]["marketer_brand"] = clean(rows[-1]["marketer_brand"] + " " + source_supplier)
                    else:
                        rows[-1]["marketer_brand"] = source_supplier
                    supplier = rows[-1]["marketer_brand"]
                    supplier_continues_current = True
                continue
            if not source_supplier and not product_name and marked:
                flags_pending = True
                supplier_continues_current = False
                continue
            if not product_name:
                continue
            if source_supplier:
                supplier = source_supplier
            if supplier_continues_current and not source_supplier and not marked and not flags_pending:
                rows[-1]["product_name"] = clean(rows[-1]["product_name"] + " " + product_name)
            else:
                rows.append({
                    "marketer_brand": supplier,
                    "product_name": product_name,
                    "page": page_index + 1,
                    "_explicit_supplier": bool(source_supplier),
                })
            flags_pending = False
            supplier_continues_current = False
    for row in rows:
        row.pop("_explicit_supplier", None)
    return rows


def parse_120k(payload: bytes) -> list[dict]:
    """Parse the 120k list; its final page has a different PDF table boundary."""
    rows = []
    page_count = len(PdfReader(io.BytesIO(payload)).pages)
    for page_index in range(page_count):
        with pdfplumber.open(rotated_page(payload, page_index)) as pdf:
            page = pdf.pages[0]
            tables = [
                table for table in page.extract_tables(TABLE_SETTINGS)
                if len(table) > 20 and len(table[0]) >= 12
            ]
            page_text = (page.extract_text() or "").replace("\x03", " ")
        if tables:
            supplier = ""
            for row in max(tables, key=len):
                source_supplier = clean(row[0])
                product_name = clean(row[1])
                if source_supplier:
                    supplier = source_supplier
                if product_name and has_approval_mark(row):
                    rows.append({"marketer_brand": supplier, "product_name": product_name, "page": page_index + 1})
            continue
        if "Producer/Oil supplier" not in page_text:
            continue
        supplier = ""
        started = False
        for line in page_text.splitlines():
            if "Producer/Oil supplier" in line:
                started = True
                continue
            if not started:
                continue
            match = re.match(r"^(.*?)(?:\s{2,}x(?:\s+x|\s*)*)$", line.rstrip())
            if not match:
                continue
            parts = [part.strip() for part in re.split(r"\s{2,}", match.group(1).rstrip()) if part.strip()]
            if len(parts) >= 2:
                supplier, product_name = parts[0], " ".join(parts[1:])
            elif len(parts) == 1 and line.startswith(" "):
                product_name = parts[0]
            else:
                continue
            rows.append({"marketer_brand": supplier, "product_name": product_name, "page": page_index + 1})
    return rows


def parse_240k(payload: bytes) -> list[dict]:
    text = " ".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(payload)).pages)
    compact = re.sub(r"\s+", "", text)
    assert all(token in compact for token in ["Driventics.r.l.", "DLiquid", "RED", "Supreme"])
    return [{"marketer_brand": "Driventic s.r.l.", "product_name": "D Liquid RED Supreme", "page": 5}]


def main() -> None:
    occurrences = []
    files = []
    parsers = {60000: parse_default_tables, 120000: parse_120k, 180000: parse_default_tables, 240000: parse_240k}
    for source in LISTS:
        publication_number = source["publication_number"]
        metadata_url = API.format(publication_number)
        metadata_payload = fetch(metadata_url)
        metadata = json.loads(metadata_payload)
        assert metadata["success"] is True and metadata["error"] is None
        english = [item for item in metadata["data"] if item["lang"] == "English"]
        assert len(english) == 1
        source_file = english[0]
        payload = fetch(source_file["url"])
        reader = PdfReader(io.BytesIO(payload))
        rows = parsers[source["interval_km"]](payload)
        assert len(rows) == source["products"], (publication_number, len(rows))
        for row in rows:
            assert row["marketer_brand"] and row["product_name"]
            occurrences.append({
                **row,
                "publication_number": publication_number,
                "oil_change_interval_km": source["interval_km"],
                "list_date": source["list_date"],
                "source_url": source_file["url"],
            })
        files.append({
            **source,
            "metadata_url": metadata_url,
            "metadata_sha256": hashlib.sha256(metadata_payload).hexdigest(),
            "file_name": source_file["name"],
            "source_url": source_file["url"],
            "source_sha256": hashlib.sha256(payload).hexdigest(),
            "pages": len(reader.pages),
        })

    grouped = defaultdict(list)
    for row in occurrences:
        grouped[(normalized(row["marketer_brand"]), normalized(row["product_name"]))].append(row)
    products = []
    for index, (_, group) in enumerate(sorted(grouped.items()), 1):
        first = group[0]
        products.append({
            "source_id": "DRIVENTIC_DIWA_APPROVED_OILS",
            "source_record_id": f"DRIVENTIC-DIWA-{index:04d}",
            "marketer_brand": first["marketer_brand"],
            "product_name": first["product_name"],
            "family_code": "T",
            "approval_occurrences": sorted(group, key=lambda row: (row["oil_change_interval_km"], row["page"])),
            "oil_change_intervals_km": sorted({row["oil_change_interval_km"] for row in group}),
            "list_dates": sorted({row["list_date"] for row in group}),
            "landing_url": LANDING_URL,
            "snapshot_date": SNAPSHOT_DATE,
        })
    assert len(occurrences) == 226
    assert len(products) == 226
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in products),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": "DRIVENTIC_DIWA_APPROVED_OILS",
        "landing_url": LANDING_URL,
        "lists": len(files),
        "approval_occurrences": len(occurrences),
        "products": len(products),
        "marketers_brands": len({row["marketer_brand"] for row in products}),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "source_files": files,
        "publication_scope": "Derived factual approval records with attribution; Driventic PDF design and full text are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "source_files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
