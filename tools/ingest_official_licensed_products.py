#!/usr/bin/env python3
"""Fetch factual product rows from official public licensing registries."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "official-licensed-products.jsonl"
REPORT = ROOT / "data" / "official-licensed-products-report.json"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"

SOURCES = [
    ("NMMA_TCW3", "https://www.nmma.org/certification/oil/tc-w3", 3),
    ("NMMA_FCW", "https://www.nmma.org/certification/oil/fc-w", 3),
    ("NMMA_FCW_CAT", "https://www.nmma.org/certification/oil/fc-wcat", 3),
    ("GM_DEXOS1_GEN3", "https://www.gmdexos.com/brands/dexos1_3/index.html", 5),
    ("GM_DEXOS2", "https://www.gmdexos.com/brands/dexos2/index.html", 5),
    ("GM_DEXOSD", "https://www.gmdexos.com/brands/dexosd/index.html", 5),
    ("GM_DEXOSR", "https://www.gmdexos.com/brands/dexosr/index.html", 5),
    ("NLGI_CERTIFIED", "https://www.nlgi.org/about-us/high-performance-multiuse-grease/", 8),
]
EU_ECOLABEL_URL = "https://apps.data.env.service.ec.europa.eu/dataquery/v2/ecolabel/products?group_id__eq=57&limit=1000"


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
            self.row.append(" ".join(self.cell.split()))
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def source_row_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]


def normalized_rows_sha256(rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_nmma(source_id: str, url: str, rows: list[list[str]]) -> list[dict]:
    specification = {
        "NMMA_TCW3": "NMMA TC-W3",
        "NMMA_FCW": "NMMA FC-W",
        "NMMA_FCW_CAT": "NMMA FC-W(CAT)",
    }[source_id]
    result = []
    for row_number, row in enumerate(rows, 1):
        if len(row) != 3 or row[0] == "Number" or not re.match(r"^(?:RL|FB)", row[0]):
            continue
        license_number, product_name, company = row
        result.append({
            "source_id": source_id,
            "source_url": url,
            "source_row_number": row_number,
            "source_record_id": license_number,
            "manufacturer": company,
            "product_name": product_name,
            "family_code": "M",
            "category": "Морские моторные масла",
            "specification": specification,
            "viscosity": "",
            "license_number": license_number,
            "certification_tags": [],
            "snapshot_date": SNAPSHOT_DATE,
        })
    return result


def parse_dexos(source_id: str, url: str, rows: list[list[str]]) -> list[dict]:
    result = []
    for row_number, row in enumerate(rows, 1):
        if len(row) != 5 or row[0] == "Brand Name" or not row[4]:
            continue
        product_name, supplier, specification, viscosity, license_number = row
        result.append({
            "source_id": source_id,
            "source_url": url,
            "source_row_number": row_number,
            "source_record_id": license_number,
            "manufacturer": supplier,
            "product_name": product_name,
            "family_code": "M",
            "category": "Лицензированные моторные масла GM dexos",
            "specification": specification.replace("™", ""),
            "viscosity": viscosity,
            "license_number": license_number,
            "certification_tags": [],
            "snapshot_date": SNAPSHOT_DATE,
        })
    return result


def parse_nlgi(source_id: str, url: str, rows: list[list[str]]) -> list[dict]:
    result = []
    for row_number, row in enumerate(rows, 1):
        if len(row) != 8 or row[0] == "Supplier":
            continue
        supplier, product_name, certification, core, cr, wr, hl, lt = row
        if certification not in {"HPM", "GC-LB", "GC", "LB"}:
            continue
        tags = [name for name, value in zip(["CORE", "CR", "WR", "HL", "LT"], [core, cr, wr, hl, lt]) if value]
        record_id = source_row_id(supplier, product_name, certification, *tags)
        result.append({
            "source_id": source_id,
            "source_url": url,
            "source_row_number": row_number,
            "source_record_id": record_id,
            "manufacturer": supplier,
            "product_name": product_name,
            "family_code": "G",
            "category": "Сертифицированные пластичные смазки NLGI",
            "specification": f"NLGI {certification}",
            "viscosity": "",
            "license_number": "",
            "certification_tags": tags,
            "snapshot_date": SNAPSHOT_DATE,
        })
    return result


def ecolabel_family(name: str) -> str:
    value = name.casefold()
    if any(token in value for token in ["grease", "fett", "graisse", "grasa"]):
        return "G"
    if any(token in value for token in ["hydraulic", "hydraulik", "hydraulique", "hidrául"]):
        return "H"
    if any(token in value for token in ["gear oil", "getriebe", "transmission"]):
        return "T"
    if any(token in value for token in ["coolant", "antifreeze", "kühl"]):
        return "TF"
    return "S"


def parse_eu_ecolabel(payload: bytes) -> list[dict]:
    raw = json.loads(payload)
    assert raw["meta"]["count"] == raw["meta"]["total"]
    result = []
    for row_number, row in enumerate(raw["data"], 1):
        item_id = str(int(row["item_id"]))
        family_code = ecolabel_family(row["product_name"])
        result.append({
            "source_id": "EU_ECOLABEL_LUBRICANTS",
            "source_url": EU_ECOLABEL_URL,
            "source_row_number": row_number,
            "source_record_id": item_id,
            "manufacturer": row["licence_holder"],
            "product_name": row["product_name"],
            "family_code": family_code,
            "category": "Смазочные материалы с EU Ecolabel",
            "specification": "EU Ecolabel Lubricants 2018/1702/EU",
            "viscosity": "",
            "license_number": row["licence_number"],
            "certification_tags": [],
            "external_codes": {"GTIN": row.get("ean13") or ""},
            "available_in": row.get("available_in") or "",
            "expiration_date": row.get("expiration_date") or "",
            "snapshot_date": SNAPSHOT_DATE,
        })
    return result


def main() -> None:
    products = []
    source_reports = []
    for source_id, url, expected_columns in SOURCES:
        payload = fetch(url)
        parser = TableParser()
        parser.feed(payload.decode("utf-8", "ignore"))
        if source_id.startswith("NMMA_"):
            parsed = parse_nmma(source_id, url, parser.rows)
        elif source_id.startswith("GM_"):
            parsed = parse_dexos(source_id, url, parser.rows)
        else:
            parsed = parse_nlgi(source_id, url, parser.rows)
        assert parsed, source_id
        assert all(len(row) == expected_columns for row in parser.rows if len(row) == expected_columns)
        products.extend(parsed)
        source_reports.append({
            "source_id": source_id,
            "source_url": url,
            "source_sha256": normalized_rows_sha256(parsed),
            "hash_basis": "normalized_extracted_factual_rows",
            "rows": len(parsed),
        })

    eu_payload = fetch(EU_ECOLABEL_URL)
    eu_products = parse_eu_ecolabel(eu_payload)
    products.extend(eu_products)
    source_reports.append({
        "source_id": "EU_ECOLABEL_LUBRICANTS",
        "source_url": EU_ECOLABEL_URL,
        "source_sha256": normalized_rows_sha256(eu_products),
        "hash_basis": "normalized_extracted_factual_rows",
        "rows": len(eu_products),
    })

    identity = [(row["source_id"], row["source_record_id"], row["product_name"]) for row in products]
    assert len(identity) == len(set(identity))
    registry_ids = [(row["source_id"], row["source_record_id"]) for row in products]
    products.sort(key=lambda row: (row["source_id"], row["source_record_id"]))
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in products), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "rows": len(products),
        "manufacturers": len({row["manufacturer"] for row in products}),
        "unique_product_records": len(set(identity)),
        "unique_registry_ids": len(set(registry_ids)),
        "registry_id_collisions": len(registry_ids) - len(set(registry_ids)),
        "sources": source_reports,
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
