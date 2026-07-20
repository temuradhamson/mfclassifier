#!/usr/bin/env python3
"""Download and normalize the public Mercedes-Benz BeVo approval registry."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "mercedes-bevo-approved-fluids.jsonl"
REPORT = ROOT / "data" / "mercedes-bevo-approved-fluids-report.json"
LANDING_URL = "https://operatingfluids.mercedes-benz.com/"
API_ROOT = "https://operatingfluids.mercedes-benz.com/api/v1/categorySheetNumbers/"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"

CATEGORY_QUERIES = [
    "Motoröl",
    "Bremsflüssigkeit",
    "Getriebeöl",
    "Fett",
    "Hydrauliköl",
    "Konservierungsmittel",
    "Kompressoröl",
    "Lenkgetriebeöl",
    "Frostschutz",
    "Kältemittel",
    "Scheibenwaschmittel-Konzentrat",
    "NOx-Reduktionsmittel",
]

FAMILY_BY_CATEGORY = {
    "Motoröl": "M",
    "Getriebeöl": "T",
    "Lenkgetriebeöl": "T",
    "Fett": "G",
    "Hydrauliköl": "H",
    "Kompressoröl": "C",
    "Korrosions- / Frostschutzmittel": "TF",
    "Bremsflüssigkeit": "TF",
    "Scheibenwaschmittel-Konzentрат": "TF",
}

VISCOSITY_FIELDS = {
    "type30": "SAE 30", "type40": "SAE 40", "type50": "SAE 50",
    "type80": "SAE 80", "type90": "SAE 90", "type0W": "SAE 0W",
    "type0W20": "0W-20", "type0W30": "0W-30", "type0W40": "0W-40",
    "type5W20": "5W-20", "type5W30": "5W-30", "type5W40": "5W-40",
    "type5W50": "5W-50", "type10W": "SAE 10W", "type10W30": "10W-30",
    "type10W40": "10W-40", "type10W60": "10W-60", "type15W40": "15W-40",
    "type20W20": "20W-20", "type20W50": "20W-50", "type75W": "SAE 75W",
    "type75W80": "75W-80", "type75W85": "75W-85", "type75W90": "75W-90",
    "type80W": "SAE 80W", "type80W90": "80W-90", "type80W85": "80W-85",
    "type85W90": "85W-90",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я]+", " ", value).strip()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def main() -> None:
    sheets_by_number = {}
    responses = []
    for category in CATEGORY_QUERIES:
        url = API_ROOT + urllib.parse.quote(category, safe="")
        payload = fetch(url)
        responses.append((category, payload))
        for sheet in json.loads(payload):
            existing = sheets_by_number.get(sheet["sheetNumber"])
            if existing:
                assert existing == sheet, sheet["sheetNumber"]
            sheets_by_number[sheet["sheetNumber"]] = sheet

    occurrences = []
    sheet_metadata = []
    for sheet_number, sheet in sorted(sheets_by_number.items()):
        historical = "histor" in (sheet.get("titleEn") or "").casefold()
        products = [
            product for product in sheet.get("products") or []
            if product.get("id") and product.get("productName") and product.get("description")
        ]
        sheet_metadata.append({
            "sheet_number": sheet_number,
            "category": sheet["category"],
            "title_en": sheet.get("titleEn") or "",
            "published_at": sheet["publishDate"],
            "historical": historical,
            "products": len(products),
            "source_url": f"https://operatingfluids.mercedes-benz.com/sheet/{sheet_number}/en",
        })
        for product in products:
            occurrences.append({
                "approval_record_uuid": product["id"],
                "bevo_product_id": product.get("productId") or "",
                "company": product["description"].strip(),
                "product_name": product["productName"].strip(),
                "sheet_number": sheet_number,
                "category": sheet["category"],
                "title_en": sheet.get("titleEn") or "",
                "published_at": sheet["publishDate"],
                "historical": historical,
                "sae_grades": [grade for field, grade in VISCOSITY_FIELDS.items() if product.get(field)],
                "source_url": f"https://operatingfluids.mercedes-benz.com/sheet/{sheet_number}/en",
            })

    grouped = defaultdict(list)
    for row in occurrences:
        grouped[(normalize(row["company"]), normalize(row["product_name"]))].append(row)
    products = []
    for key, group in sorted(grouped.items()):
        families = {FAMILY_BY_CATEGORY.get(row["category"], "S") for row in group}
        assert len(families) == 1, (key, families)
        first = group[0]
        identity_hash = hashlib.sha256("|".join(key).encode()).hexdigest()[:20]
        products.append({
            "source_id": "MERCEDES_BENZ_BEVO_APPROVED_FLUIDS",
            "source_record_id": f"MB-BEVO-{identity_hash}",
            "company": first["company"],
            "product_name": first["product_name"],
            "family_code": next(iter(families)),
            "approval_occurrences": sorted(group, key=lambda row: (row["sheet_number"], row["approval_record_uuid"])),
            "approval_record_uuids": sorted({row["approval_record_uuid"] for row in group}),
            "bevo_product_ids": sorted({row["bevo_product_id"] for row in group if row["bevo_product_id"]}),
            "bevo_sheets": sorted({row["sheet_number"] for row in group}),
            "sae_grades": sorted({grade for row in group for grade in row["sae_grades"]}),
            "historical_only": all(row["historical"] for row in group),
            "landing_url": LANDING_URL,
            "snapshot_date": SNAPSHOT_DATE,
        })

    product_id_identities = defaultdict(set)
    for row in occurrences:
        if row["bevo_product_id"]:
            product_id_identities[row["bevo_product_id"]].add(
                (normalize(row["company"]), normalize(row["product_name"]))
            )
    product_id_collisions = {
        product_id: len(identities)
        for product_id, identities in product_id_identities.items() if len(identities) > 1
    }

    assert len(sheets_by_number) == 130
    assert len([sheet for sheet in sheets_by_number.values() if sheet.get("products")]) == 92
    assert len(occurrences) == 2461
    assert len(products) == 1913
    assert product_id_collisions == {"FDKAI7": 2}
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in products),
        encoding="utf-8",
    )
    response_digest = hashlib.sha256()
    for category, payload in responses:
        response_digest.update(category.encode())
        response_digest.update(b"\0")
        response_digest.update(payload)
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": "MERCEDES_BENZ_BEVO_APPROVED_FLUIDS",
        "landing_url": LANDING_URL,
        "category_api_response_sha256": response_digest.hexdigest(),
        "sheets_inspected": len(sheets_by_number),
        "product_sheets": len([sheet for sheet in sheets_by_number.values() if sheet.get("products")]),
        "approval_occurrences": len(occurrences),
        "products": len(products),
        "current_products": sum(not row["historical_only"] for row in products),
        "historical_only_products": sum(row["historical_only"] for row in products),
        "companies": len({row["company"] for row in products}),
        "families": dict(sorted(Counter(row["family_code"] for row in products).items())),
        "bevo_product_id_collisions": product_id_collisions,
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "source_sheets": sheet_metadata,
        "publication_scope": "Derived factual approval records with attribution; page design and explanatory text are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "source_sheets"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
