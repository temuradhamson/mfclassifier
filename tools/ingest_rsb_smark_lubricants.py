#!/usr/bin/env python3
"""Normalize lubricant products from Rwanda RSB's public S-Mark directory."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "rsb-smark-lubricant-products.jsonl"
REPORT = ROOT / "data" / "rsb-smark-lubricant-products-report.json"
CACHE = ROOT / ".cache" / "rsb-smark"
HTML_CACHE = CACHE / "products-with-s-marks-2026-07-21.html"
SOURCE_ID = "RSB_SMARK_LUBRICANT_PRODUCTS"
SOURCE_URL = "https://www.rsb.gov.rw/certifications/directories/products-with-s-marks-1"
SOURCE_CONTEXT_URL = "https://www.rsb.gov.rw/certifications/product-certification"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-directory)"


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "td":
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td":
            self.row.append(clean("".join(self.cell_parts)))
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = []


def fetch_html() -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    if HTML_CACHE.exists():
        return HTML_CACHE.read_bytes()
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    error = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read()
            if len(body) < 400_000 or b"Products with S-Marks" not in body:
                raise RuntimeError("unexpected RSB directory response")
            HTML_CACHE.write_bytes(body)
            return body
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            error = exc
            time.sleep(min(10, attempt + 1))
    raise RuntimeError(f"Failed to fetch RSB directory: {error}")


def source_rows(source_html: bytes) -> list[dict]:
    parser = TableParser()
    parser.feed(source_html.decode("utf-8", errors="replace"))
    rows = []
    for cells in parser.rows:
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        rows.append({
            "source_number": int(cells[0]),
            "manufacturer": cells[1],
            "product_name": cells[2],
            "licence_number": cells[3],
            "standard": cells[4],
            "source_status": cells[5],
            "expiry_raw": cells[6],
        })
    numbers = [row["source_number"] for row in rows]
    missing = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
    if len(rows) != 1843 or numbers != sorted(set(numbers)) or numbers[-1] != 1846 or missing != [1764, 1765, 1766]:
        raise RuntimeError(f"Unexpected RSB extraction: rows={len(rows)} last={numbers[-1]} missing={missing}")
    return rows


def in_scope(row: dict) -> bool:
    value = f" {normalize(row['product_name'])} "
    standard = normalize(row["standard"])
    professional_name = any(token in value for token in (
        " lubricant ", " engine oil ", " motor oil ", " hydraulic oil ",
        " gear oil ", " grease ", " coolant ", " brake fluid ",
        " transmission fluid ", " antifreeze ", " cutting oil ",
        " compressor oil ", " turbine oil ", " transformer oil ",
    ))
    professional_standard = bool(re.search(r"\b(?:rs\s+)?(?:eas\s+159|234\s+1)\b", standard))
    exclusions = ("edible", "cooking", "hair oil", "body oil", "chilli oil")
    return (professional_name or professional_standard) and not any(token in value for token in exclusions)


def family_for(product_name: str) -> tuple[str, str]:
    value = f" {normalize(product_name)} "
    if " engine oil " in value or " motor oil " in value:
        return "M", "explicit_engine_oil_product_name"
    if " food grade lubricant " in value:
        return "S", "explicit_food_grade_lubricant_product_name"
    if " grease " in value:
        return "G", "explicit_grease_product_name"
    if " hydraulic " in value:
        return "H", "explicit_hydraulic_product_name"
    if any(token in value for token in (" gear oil ", " transmission fluid ")):
        return "T", "explicit_transmission_or_gear_product_name"
    if any(token in value for token in (" coolant ", " brake fluid ", " antifreeze ")):
        return "TF", "explicit_technical_fluid_product_name"
    return "S", "explicit_lubricant_product_name"


def brand_for(product_name: str, manufacturer: str) -> tuple[str, str]:
    for brand in ("RYMAX", "STABEX", "MOTRAX", "TINTEC"):
        if re.search(rf"\b{brand}\b", product_name, re.I):
            return brand, "brand_token_in_source_product_brand_name"
    return manufacturer, "manufacturer_fallback_no_distinct_brand_token"


def expiry_date(value: str) -> str:
    value = clean(value).removesuffix(" 00:00:00")
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unexpected RSB expiry date: {value}")


def technical(product_name: str) -> dict:
    upper = clean(product_name).upper().replace("–", "-").replace("—", "-")
    sae = {f"{a}W-{b}" for a, b in re.findall(r"(?<!\d)(0|5|10|15|20|25)\s*W\s*[- ]?\s*([2345]0)(?!\d)", upper)}
    sae_monograde = {f"SAE {value}" for value in re.findall(r"\bSAE\s*(20|30|40|50|60)\b", upper)}
    api = set()
    for value in re.findall(r"\bAPI\s*([SC][A-Z](?:\s*[- ]?\s*4)?|SP|SN|SM|SL|SJ|SH|SG|SF|SE|SD)\b", upper):
        value = re.sub(r"^(C[A-Z])\s*[- ]?\s*4$", r"\1-4", value)
        api.add(value)
    return {
        "sae": sorted(sae),
        "sae_monograde": sorted(sae_monograde),
        "api": sorted(api),
        "api_gl": [],
        "iso_vg": [],
        "nlgi": [],
    }


def main() -> None:
    source_html = fetch_html()
    directory_rows = source_rows(source_html)
    scope_rows = [row for row in directory_rows if in_scope(row)]
    records = []
    for row in scope_rows:
        family, basis = family_for(row["product_name"])
        brand, brand_basis = brand_for(row["product_name"], row["manufacturer"])
        identity = "|".join((normalize(row["manufacturer"]), normalize(row["product_name"]), normalize(row["licence_number"])))
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": "RSB-SMARK-" + hashlib.sha256(identity.encode()).hexdigest()[:16].upper(),
            "source_url": SOURCE_URL,
            "source_context_url": SOURCE_CONTEXT_URL,
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "market": "RW",
            "certification_authority": "Rwanda Standards Board (RSB)",
            "manufacturer": row["manufacturer"],
            "brand": brand,
            "brand_basis": brand_basis,
            "product_name": row["product_name"],
            "family_code": family,
            "classification_basis": basis,
            "licence_number": row["licence_number"],
            "standard": row["standard"],
            "source_status": row["source_status"],
            "expiry_date": expiry_date(row["expiry_raw"]),
            "lifecycle_status": "source_reported_valid" if row["source_status"].casefold() == "valid" else "source_reported_" + normalize(row["source_status"]).replace(" ", "_"),
            "source_number": row["source_number"],
            "technical": technical(row["product_name"]),
        })
    records.sort(key=lambda row: (normalize(row["manufacturer"]), normalize(row["product_name"]), row["licence_number"]))
    if len(records) != 9 or len({row["source_record_id"] for row in records}) != len(records):
        raise RuntimeError(f"Unexpected RSB lubricant scope: {len(records)}")
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_public_government_product_certification_directory_normalized",
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_context_url": SOURCE_CONTEXT_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "source_html_sha256": hashlib.sha256(source_html).hexdigest(),
        "source_directory_rows": len(directory_rows),
        "source_last_serial_number": directory_rows[-1]["source_number"],
        "source_missing_serial_numbers": [1764, 1765, 1766],
        "lubricant_scope_rows": len(scope_rows),
        "normalized_products": len(records),
        "manufacturers": len({row["manufacturer"] for row in records}),
        "brands": len({row["brand"] for row in records}),
        "lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "technical_coverage": dict(sorted(Counter(key for row in records for key, values in row["technical"].items() if values).items())),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "rights_note": "Public S-Mark certification facts only. Location, telephone and email are excluded; Rwanda Standard body text and certification-mark artwork are not republished.",
        "excluded_fields": ["location", "telephone", "email", "contacts", "standard_body_text", "certification_mark_artwork"],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
