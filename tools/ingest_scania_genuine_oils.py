#!/usr/bin/env python3
"""Normalize the current Scania Middle East genuine engine-oil page."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "scania-genuine-oils.jsonl"
REPORT = ROOT / "data" / "scania-genuine-oils-report.json"
SOURCE_ID = "SCANIA_GENUINE_ENGINE_OILS"
SOURCE_URL = "https://www.scania.com/ae/en/home/services/repair-and-maintenance/scania-oil.html"
TERMS_URL = "https://www.scania.com/ae/en/home/admin/misc/legal.html"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"


PRODUCTS = [
    {
        "product_name": "Scania Oil E7 15W-40",
        "specifications": {
            "sae_engine": "15W-40",
            "acea": ["E7"],
            "scania_oil_designation": "E7",
            "temperature_min_c": -15,
            "temperature_max_c": 30,
            "drain_interval_source_reported": "Normal",
            "engine_emission_stages_source_reported": ["Euro I", "Euro II", "Euro III", "Euro IV", "Euro V"],
            "source_exclusion": "Not suitable for Euro VI engines or engines with after-treatment systems",
        },
    },
    {
        "product_name": "Scania Oil BEO-2",
        "specifications": {
            "scania_oil_designation": "BEO-2",
            "temperature_min_c": -25,
            "temperature_max_c": 30,
            "drain_interval_source_reported": "Extended",
            "fuel_and_engine_source_reported": "Scania ED95 bioethanol engine",
        },
    },
    {
        "product_name": "Scania Oil LDF-3 10W-40",
        "specifications": {
            "sae_engine": "10W-40",
            "scania_oil_designation": "LDF-3",
            "temperature_min_c": -25,
            "temperature_max_c": 30,
            "drain_interval_source_reported": "Extended",
            "engine_emission_stages_source_reported": ["Euro I", "Euro II", "Euro III", "Euro IV", "Euro V", "Euro VI"],
        },
    },
    {
        "product_name": "Scania Oil LDF-4",
        "specifications": {
            "scania_oil_designation": "LDF-4",
            "temperature_min_c": -30,
            "temperature_max_c": 30,
            "drain_interval_source_reported": "Extended",
            "engine_emission_stages_source_reported": ["Euro I", "Euro II", "Euro III", "Euro IV", "Euro V", "Euro VI"],
            "fuel_and_engine_source_reported": "Scania Euro VI, CNG and LNG engines",
            "source_quality_note": "No SAE grade is stated on the regional source page; none is inferred.",
        },
    },
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def visible_text(payload: bytes) -> str:
    value = re.sub(
        r"<script\b.*?</script>|<style\b.*?</style>",
        " ",
        payload.decode(errors="replace"),
        flags=re.I | re.S,
    )
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> None:
    source_payload = fetch(SOURCE_URL)
    terms_payload = fetch(TERMS_URL)
    source_text = visible_text(source_payload)
    terms_text = visible_text(terms_payload)

    for product in PRODUCTS:
        assert normalize(product["product_name"]) in normalize(source_text), product["product_name"]
    for fact in (
        "ACEA E7-quality oil",
        "ED95 bioethanol engine",
        "Temperature range",
        "-15 to +30 degrees",
        "-25 to +30 degrees",
        "-30 to +30 degrees",
        "Valid for CNG and LNG engines",
    ):
        assert normalize(fact) in normalize(source_text), fact
    for term in (
        "Creative Commons 3.0 license",
        "not for purposes of commercialization of the contents as such",
        "reference is made to Scania",
    ):
        assert normalize(term) in normalize(terms_text), term

    rows = []
    for index, product in enumerate(PRODUCTS, 1):
        rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"SCANIA-OIL-{index:03d}",
            "brand": "Scania",
            "manufacturer": "Scania CV AB",
            "product_name": product["product_name"],
            "family_code": "M",
            "market": "MIDDLE_EAST_GULF_REGION",
            "source_url": SOURCE_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_current_regional_page_status_not_individually_dated",
            "specifications": product["specifications"],
        })

    assert len(rows) == len({(row["brand"], row["product_name"], row["family_code"]) for row in rows}) == 4
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "terms_url": TERMS_URL,
        "source_page_sha256": hashlib.sha256(source_payload).hexdigest(),
        "terms_page_sha256": hashlib.sha256(terms_payload).hexdigest(),
        "normalized_products": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "rows_with_sae": sum(bool(row["specifications"].get("sae_engine")) for row in rows),
        "rows_with_acea": sum(bool(row["specifications"].get("acea")) for row in rows),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Factual product and technical fields with Scania attribution; marketing prose, images, logos and page design are excluded. Noncommercial use only under the source terms.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
