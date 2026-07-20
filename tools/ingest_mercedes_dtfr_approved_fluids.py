#!/usr/bin/env python3
"""Download and normalize the public Mercedes-Benz Trucks DTFR approval registry."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "mercedes-dtfr-approved-fluids.jsonl"
REPORT = ROOT / "data" / "mercedes-dtfr-approved-fluids-report.json"
SOURCE_URL = "https://bevo.mercedes-benz-trucks.com/api/v1/all/"
LANDING_URL = "https://bevo.mercedes-benz-trucks.com/"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"

INCLUDED_CATEGORIES = {
    "E-Antriebssysteme",
    "Achsenöl",
    "Getriebeöl",
    "H Getriebeöl",
    "Motoröl",
    "Korrosions- / Frostschutzmittel",
    "Bremsflüssigkeit",
    "Hydrauliköl",
    "edAC-Öl",
    "Fett",
    "Kompressoröl",
    "Lenkgetriebeöl",
}

# Overview sheets repeat examples from unrelated families. The four other sheets
# explicitly say Daimler Truck does not issue approvals and point to another OEM.
EXCLUDED_NON_APPROVAL_SHEETS = {
    "DTFR 15A100",
    "DTFR 31A100",
    "DTFR 12C100",
    "DTFR 12C110",
    "DTFR 13E100",
    "DTFR 15E100",
}

VISCOSITY_FIELDS = {
    "type30": "SAE 30",
    "type40": "SAE 40",
    "type50": "SAE 50",
    "type80": "SAE 80",
    "type90": "SAE 90",
    "type0W": "SAE 0W",
    "type0W20": "0W-20",
    "type0W30": "0W-30",
    "type0W40": "0W-40",
    "type5W20": "5W-20",
    "type5W30": "5W-30",
    "type5W40": "5W-40",
    "type5W50": "5W-50",
    "type10W": "SAE 10W",
    "type10W30": "10W-30",
    "type10W40": "10W-40",
    "type10W60": "10W-60",
    "type15W40": "15W-40",
    "type20W20": "20W-20",
    "type20W50": "20W-50",
    "type75W": "SAE 75W",
    "type75W80": "75W-80",
    "type75W85": "75W-85",
    "type75W90": "75W-90",
    "type80W": "SAE 80W",
    "type80W90": "80W-90",
    "type80W85": "80W-85",
    "type85W90": "85W-90",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def family_for(sheet_number: str, category: str) -> str:
    if category == "Motoröl":
        return "M"
    if category == "Hydrauliköl":
        return "H"
    if category == "Fett":
        return "G"
    if category == "Kompressoröl":
        return "C"
    if category in {"Korrosions- / Frostschutzmittel", "Bremsflüssigkeit"}:
        return "TF"
    if category == "edAC-Öl" or sheet_number == "DTFR 10D100":
        return "S"
    return "T"


def published_at(value: str) -> str:
    return datetime.strptime(value, "%d.%m.%y, %H:%M").isoformat()


def main() -> None:
    payload = fetch(SOURCE_URL)
    source = json.loads(payload)
    sheets = [
        sheet for sheet in source
        if sheet.get("category") in INCLUDED_CATEGORIES
        and sheet.get("productCollection")
        and sheet["sheetNumber"] not in EXCLUDED_NON_APPROVAL_SHEETS
    ]
    occurrences = []
    sheet_metadata = []
    for sheet in sheets:
        historical = "historical" in (sheet.get("titleEn") or "").casefold()
        products = [
            product for product in sheet["productCollection"]
            if product.get("productId") and product.get("description") and product.get("productName")
        ]
        sheet_metadata.append({
            "sheet_number": sheet["sheetNumber"],
            "category": sheet["category"],
            "title_en": sheet.get("titleEn") or "",
            "published_at": published_at(sheet["publishDate"]),
            "historical": historical,
            "products": len(products),
        })
        for product in products:
            occurrences.append({
                "product_id": product["productId"],
                "product_name": product["productName"].strip(),
                "company": product["description"].strip(),
                "sheet_number": sheet["sheetNumber"],
                "category": sheet["category"],
                "title_en": sheet.get("titleEn") or "",
                "published_at": published_at(sheet["publishDate"]),
                "historical": historical,
                "sae_grades": [grade for field, grade in VISCOSITY_FIELDS.items() if product.get(field)],
            })

    grouped = defaultdict(list)
    for row in occurrences:
        grouped[row["product_id"]].append(row)
    products = []
    for product_id, group in sorted(grouped.items()):
        identities = {(row["company"], row["product_name"]) for row in group}
        assert len(identities) == 1, (product_id, identities)
        first = group[0]
        products.append({
            "source_id": "MERCEDES_DTFR_APPROVED_FLUIDS",
            "source_record_id": f"MB-DTFR-{product_id}",
            "dtfr_product_id": product_id,
            "company": first["company"],
            "product_name": first["product_name"],
            "family_code": family_for(first["sheet_number"], first["category"]),
            "approval_occurrences": sorted(group, key=lambda row: row["sheet_number"]),
            "dtfr_sheets": sorted({row["sheet_number"] for row in group}),
            "sae_grades": sorted({grade for row in group for grade in row["sae_grades"]}),
            "historical_only": all(row["historical"] for row in group),
            "landing_url": LANDING_URL,
            "source_url": SOURCE_URL,
            "snapshot_date": SNAPSHOT_DATE,
        })

    assert len(sheets) == 63
    assert len(occurrences) == 2102
    assert len(products) == 1892
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in products),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": "MERCEDES_DTFR_APPROVED_FLUIDS",
        "landing_url": LANDING_URL,
        "source_url": SOURCE_URL,
        "source_response_sha256": hashlib.sha256(payload).hexdigest(),
        "sheets": len(sheets),
        "approval_occurrences": len(occurrences),
        "products": len(products),
        "current_products": sum(not row["historical_only"] for row in products),
        "historical_only_products": sum(row["historical_only"] for row in products),
        "companies": len({row["company"] for row in products}),
        "families": {
            family: sum(row["family_code"] == family for row in products)
            for family in sorted({row["family_code"] for row in products})
        },
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "source_sheets": sheet_metadata,
        "excluded_non_approval_sheets": sorted(EXCLUDED_NON_APPROVAL_SHEETS),
        "publication_scope": "Derived factual approval records with attribution; page design, PDFs and explanatory text are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "source_sheets"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
