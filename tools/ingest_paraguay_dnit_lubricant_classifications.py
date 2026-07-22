#!/usr/bin/env python3
"""Normalize lubricant product rulings from Paraguay DNIT's public register."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "paraguay-dnit-lubricant-classifications.jsonl"
REPORT = ROOT / "data" / "paraguay-dnit-lubricant-classifications-report.json"
SOURCE_ID = "PARAGUAY_DNIT_LUBRICANT_TARIFF_CLASSIFICATION_RULINGS"
SOURCE_URL = "https://www.dnit.gov.py/web/portal-institucional/dictamenes-de-clasificacion"
SNAPSHOT_DATE = "2026-07-22"
EXPECTED_SOURCE_ROWS = 627
EXPECTED_NORMALIZED_SOURCE_SHA256 = "9f8c1a975a77552d1af539c415a6a2cc390b9b98e7c321a9454dcee108ef0cb3"

PRODUCTS = {
    645: ("M", "Shell", "Shell Helix HX7 SP 10W-30", ["10W-30"], ["SP"], []),
    644: ("M", "Shell", "Shell Helix HX7 SN 10W-40", ["10W-40"], ["SN"], []),
    643: ("T", "Shell", "Shell Spirax S5 ATF X", [], [], ["Allison C-4", "Aisin JWS 3309", "JASO 1-A", "JASO 2A-02", "Ford MERCON V", "GM DEXRON", "GM DEXRON II", "GM DEXRON III", "Toyota T-III", "Toyota T-IV"]),
    642: ("T", "Shell", "Shell Spirax S5 DCT X", [], [], ["VW G 052 182", "BMW 83 22 0 440 214", "BMW 83 22 2 146 578", "Ford WSS-MC936-A", "Mercedes-Benz 236.24"]),
    640: ("S", "Mundial Prime", "Mundial Prime MP1 Desengripante-Lubricante", [], [], []),
    608: ("S", "TEKORO", "TEKORO TE-60 Desengripante-Lubricante", [], [], []),
    589: ("T", "Valvoline", "Valvoline MaxLife ATF 884646", [], [], ["DEXRON VI", "MERCON V", "MERCON LV", "DEX/MERC"]),
    577: ("S", "BASTON", "BASTON M500 LUB", [], [], []),
    370: ("M", "Mobil", "Mobil Super 3000 X5 5W-40", ["5W-40"], [], []),
    369: ("M", "Mobil", "Mobil Super 2000 5W-30", ["5W-30"], [], []),
    368: ("M", "Mobil", "Mobil Super 3000 X1 5W-40", ["5W-40"], [], []),
    367: ("M", "Mobil", "Mobil Super 3000 XE 5W-30", ["5W-30"], [], []),
    366: ("M", "Mobil", "Mobil Super 2000 X3 10W-40", ["10W-40"], [], []),
    365: ("M", "Mobil", "Mobil Delvac XHP Extra 10W-40", ["10W-40"], [], []),
    364: ("M", "Mobil", "Mobil Super 2000 X1 15W-40", ["15W-40"], [], []),
    362: ("M", "Mobil", "Mobil Super Motor 4T MX 15W-50", ["15W-50"], [], []),
    361: ("M", "Mobil", "Mobil Super Motor 4T MX 10W-30", ["10W-30"], [], []),
    360: ("M", "Mobil", "Mobil Super Motor 4T MX 10W-40", ["10W-40"], [], []),
    250: ("M", "Brand not stated (DNIT source)", "Aceite lubricante multigrado de uso automotriz", [], [], []),
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_html() -> str:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "MFClassifierResearch/1.0 (public-government-rulings)"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read().decode("utf-8")


def source_rows(page: str) -> list[dict]:
    marker = "const data ="
    start = page.index(marker) + len(marker)
    end = page.index("];", start) + 1
    rows = json.loads(re.sub(r",\s*}", "}", page[start:end]))
    normalized = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(normalized).hexdigest()
    if len(rows) != EXPECTED_SOURCE_ROWS or len({row["id"] for row in rows}) != EXPECTED_SOURCE_ROWS:
        raise RuntimeError("DNIT source row count or IDs changed")
    if digest != EXPECTED_NORMALIZED_SOURCE_SHA256:
        raise RuntimeError(f"DNIT normalized source changed: expected {EXPECTED_NORMALIZED_SOURCE_SHA256}, got {digest}")
    return rows


def normalize(row: dict) -> dict:
    family, brand, product, sae, api, performance = PRODUCTS[row["id"]]
    facts = {key: clean(row.get(key)) for key in ("fecha", "dictamen", "mercaderia", "descripcion", "clasificacion", "legal", "nro_res")}
    return {
        "source_id": SOURCE_ID,
        "source_record_id": f"DNIT-PY-RULING-{row['id']}",
        "source_url": SOURCE_URL,
        "source_numeric_id": row["id"],
        "source_resolution": clean(row.get("nro_res")),
        "source_ruling": clean(row["dictamen"]),
        "source_product_field": clean(row["mercaderia"]),
        "source_description": clean(row["descripcion"]),
        "source_legal_basis": clean(row["legal"]),
        "source_facts_sha256": hashlib.sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "market": "Paraguay",
        "manufacturer_or_certificate_holder": "",
        "brand": brand,
        "product_name": product,
        "family_code": family,
        "technical": {"sae": sae, "api": api, "performance_source_reported": performance},
        "ruling_date": datetime.strptime(row["fecha"], "%Y-%m-%d").date().isoformat(),
        "tariff_code": clean(row["clasificacion"]),
        "lifecycle_status": "historical_tariff_classification_ruling_current_market_status_unverified",
        "evidence_status": "official_government_product_tariff_classification_ruling",
        "source_quality_flags": [
            "ruling_proves_product_identity_composition_and_tariff_classification_not_current_market_availability",
            "performance_values_retained_only_when_explicit_in_official_description",
        ],
    }


def main() -> None:
    rows = source_rows(fetch_html())
    by_id = {row["id"]: row for row in rows}
    if set(PRODUCTS) - set(by_id):
        raise RuntimeError("Expected DNIT lubricant ruling disappeared")
    selected_by_tariff = {
        row["id"] for row in rows
        if re.fullmatch(r"(?:2710|3403|3819|3820)\.\d+(?:\.\d+)*", clean(row["clasificacion"]))
    }
    if selected_by_tariff != set(PRODUCTS):
        raise RuntimeError(f"DNIT lubricant tariff selection drifted: {sorted(selected_by_tariff ^ set(PRODUCTS))}")
    records = [normalize(by_id[item]) for item in sorted(PRODUCTS)]
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "status": "official_paraguay_dnit_lubricant_tariff_rulings_normalized",
        "source_url": SOURCE_URL,
        "normalized_source_sha256": EXPECTED_NORMALIZED_SOURCE_SHA256,
        "source_rows_audited": len(rows),
        "normalized_products": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "brands": dict(sorted(Counter(row["brand"] for row in records).items())),
        "rows_with_sae": sum(bool(row["technical"]["sae"]) for row in records),
        "rows_with_api": sum(bool(row["technical"]["api"]) for row in records),
        "rows_with_explicit_performance": sum(bool(row["technical"]["performance_source_reported"]) for row in records),
        "ruling_date_min": min(row["ruling_date"] for row in records),
        "ruling_date_max": max(row["ruling_date"] for row in records),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "method": "all 627 embedded official rulings audited by lubricant tariff headings 2710/3403/3819/3820; exact product, description, ruling and NCM retained",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
