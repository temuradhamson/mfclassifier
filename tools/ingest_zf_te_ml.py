#!/usr/bin/env python3
"""Download and normalize official ZF TE-ML approved lubricant lists."""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "zf-te-ml-approved-products.jsonl"
REPORT = ROOT / "data" / "zf-te-ml-approved-products-report.json"
URL = "https://aftermarket.zf.com/lubricants/en/2026-07-01_en.zip"
LIST_DATE = "2026-07-01"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"
ROW_RE = re.compile(r"^\s*(.*?/[A-Z]{2})(.*?)(ZF\d{6})\s*$")
HEADER_RE = re.compile(r"Manufacturer\s*\((\d+[A-Z]*)\).*Trade name")


def clean(value: str) -> str:
    value = re.sub(r"\s*\(\*\)\s*", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def company_and_country(manufacturer_raw: str) -> tuple[str, str]:
    country_match = re.search(r"/([A-Z]{2})$", manufacturer_raw)
    country = country_match.group(1) if country_match else ""
    parts = [part.strip() for part in manufacturer_raw.split(",")]
    if len(parts) == 1:
        return manufacturer_raw, country
    last_location = parts[-1].split("/", 1)[0].strip()
    remove = 2 if len(parts) >= 3 and re.fullmatch(r"[A-Z]{2,3}", last_location) else 1
    company = ", ".join(parts[:-remove]).strip()
    return company or manufacturer_raw, country


def family_for(name: str, classes: list[str]) -> str:
    value = name.casefold()
    if any(token in value for token in ["grease", "fett", "graisse"]):
        return "G"
    if any(token in value for token in ["hydraulic", "hydraulik", "hydrofluid", "hydro "]):
        return "H"
    if any(token in value for token in ["engine oil", "motor oil"]):
        return "M"
    if any(token in value for token in ["coolant", "antifreeze", "brake fluid"]):
        return "TF"
    return "T"


def download() -> bytes:
    request = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def main() -> None:
    archive = download()
    by_approval: dict[str, dict] = {}
    occurrences = []
    pdf_reports = []
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        pdf_names = sorted(name for name in zf.namelist() if name.lower().endswith(".pdf"))
        assert len(pdf_names) == 28
        for pdf_name in pdf_names:
            payload = zf.read(pdf_name)
            sheet_match = re.search(r"TE-ML\s+(\d+)", pdf_name, re.I)
            assert sheet_match, pdf_name
            sheet = sheet_match.group(1)
            reader = PdfReader(io.BytesIO(payload))
            pdf_rows = 0
            for page_number, page in enumerate(reader.pages, 1):
                lubricant_class = ""
                layout = page.extract_text(extraction_mode="layout") or ""
                for line in layout.splitlines():
                    header = HEADER_RE.search(line)
                    if header:
                        lubricant_class = header.group(1)
                    match = ROW_RE.match(line)
                    if not match:
                        continue
                    assert lubricant_class, (pdf_name, page_number, line)
                    manufacturer_raw = clean(match.group(1))
                    product_name = clean(match.group(2))
                    approval_number = match.group(3)
                    company, country = company_and_country(manufacturer_raw)
                    occurrence = {
                        "te_ml_sheet": f"TE-ML {sheet}",
                        "lubricant_class": lubricant_class,
                        "page": page_number,
                    }
                    occurrences.append({"approval_number": approval_number, **occurrence})
                    pdf_rows += 1
                    if approval_number not in by_approval:
                        by_approval[approval_number] = {
                            "approval_number": approval_number,
                            "manufacturer": company,
                            "manufacturer_raw": manufacturer_raw,
                            "manufacturer_country": country,
                            "product_names": set(),
                            "approval_occurrences": [],
                        }
                    row = by_approval[approval_number]
                    assert row["manufacturer"] == company, approval_number
                    row["product_names"].add(product_name)
                    row["approval_occurrences"].append(occurrence)
            pdf_reports.append({
                "file": pdf_name,
                "source_sha256": hashlib.sha256(payload).hexdigest(),
                "pages": len(reader.pages),
                "approval_occurrences": pdf_rows,
            })

    products = []
    name_collisions = 0
    for approval_number, row in by_approval.items():
        names = sorted(row.pop("product_names"), key=lambda value: (-len(value), value))
        occurrences_for_product = sorted(
            {tuple(item.values()) for item in row["approval_occurrences"]}
        )
        approval_occurrences = [
            {"te_ml_sheet": item[0], "lubricant_class": item[1], "page": item[2]}
            for item in occurrences_for_product
        ]
        lubricant_classes = sorted({item["lubricant_class"] for item in approval_occurrences})
        if len(names) > 1:
            name_collisions += 1
        products.append({
            **row,
            "product_name": names[0],
            "product_name_aliases": names[1:],
            "approval_occurrences": approval_occurrences,
            "te_ml_sheets": sorted({item["te_ml_sheet"] for item in approval_occurrences}),
            "lubricant_classes": lubricant_classes,
            "family_code": family_for(names[0], lubricant_classes),
            "source_id": "ZF_TE_ML",
            "source_url": URL,
            "source_record_id": approval_number,
            "list_date": LIST_DATE,
            "snapshot_date": SNAPSHOT_DATE,
        })
    products.sort(key=lambda row: row["approval_number"])
    assert len(products) == len({row["approval_number"] for row in products}) == 1498
    assert len(occurrences) == 4919
    assert name_collisions == 2
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in products), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "list_date": LIST_DATE,
        "source_id": "ZF_TE_ML",
        "source_url": URL,
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "pdfs": len(pdf_reports),
        "approval_occurrences": len(occurrences),
        "unique_approval_numbers": len(products),
        "manufacturers": len({row["manufacturer"] for row in products}),
        "source_name_collisions": name_collisions,
        "families": dict(sorted((family, sum(row["family_code"] == family for row in products)) for family in {row["family_code"] for row in products})),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "source_files": pdf_reports,
        "publication_scope": "Derived factual approval records with attribution; ZF PDF design and full text are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "source_files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
