#!/usr/bin/env python3
"""Normalize named motor oils in Panama ACODECO's January 2020 price survey.

The two-page official consumer-price table contains 45 brand/grade rows and
several generic fluid rows.  Only the named motor-oil rows become product
observations.  Prices are historical retail observations in balboas, not
evidence of current availability, quality, API licensing or manufacturer
approval.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/panama-acodeco-2020-lubricant-price-survey.jsonl"
REPORT = ROOT / "data/panama-acodeco-2020-lubricant-price-survey-report.json"
SOURCE_ID = "PANAMA_ACODECO_2020_LUBRICANT_PRICE_SURVEY"
SOURCE_URL = (
    "https://tableroquejas.acodeco.gob.pa/uploads/pdf/estadisticas/"
    "LubricantesAutoRepuesto_Ene2020.02_07_2020_10_49_02_a.m..pdf"
)
SOURCE_SHA256 = "052ce0cd74d9bf1892f90bdcfcd508bfb8810f16c4a83f4513ede5112a80b6a3"
SURVEY_DATE = "2020-01"
SNAPSHOT_DATE = "2026-07-23"
UA = "MFClassifier evidence catalog/1.0"


# grade, source product/brand label, standardized brand, variant, observed prices.
ROWS = [
    ("10W-30", "Golden Supreme", "Golden Supreme", "", [2.95]),
    ("10W-30", "Abro", "ABRO", "", [4.50]),
    ("10W-30", "Amalie", "AMALIE", "", [4.50, 4.35, 3.55, 4.25, 3.75, 3.97]),
    ("10W-30", "Avenoil", "AVENOIL", "", [3.75]),
    ("10W-30", "Castrol", "Castrol", "", [5.00, 5.30, 5.25, 4.75, 4.75]),
    ("10W-30", "Castrol Semi Sintético", "Castrol", "Semi Sintético", [7.65]),
    ("10W-30", "Castrol Magnatec Sintético", "Castrol", "Magnatec Sintético", [8.50]),
    ("10W-30", "Champion Full sintético", "Champion", "Full sintético", [7.50]),
    ("10W-30", "Havoline semi sintético", "Havoline", "semi sintético", [4.25]),
    ("10W-30", "Mobil", "Mobil", "", [4.99]),
    ("10W-30", "Mobil semi sintético", "Mobil", "semi sintético", [5.25]),
    ("10W-30", "Mobil 1 full sintético", "Mobil 1", "full sintético", [13.99]),
    ("10W-30", "Penzoil", "Pennzoil", "", [5.00]),
    ("10W-30", "Shell Helix", "Shell Helix", "", [5.50, 5.55, 5.00, 5.14]),
    ("10W-30", "Shevron semisintético", "Chevron", "semisintético", [4.25]),
    ("10W-30", "Total", "Total", "", [4.85, 4.85]),
    ("10W-30", "Valvoline", "Valvoline", "", [4.50]),
    ("10W-30", "Valvoline semisintético", "Valvoline", "semisintético", [7.00]),
    ("10W-30", "Venoco semisintético", "Venoco", "semisintético", [3.50]),
    ("15W-40", "Golden Supreme", "Golden Supreme", "", [2.95]),
    ("15W-40", "Abro", "ABRO", "", [5.50]),
    ("15W-40", "Amalie", "AMALIE", "", [4.35, 4.55, 3.90, 4.30, 4.99]),
    ("15W-40", "Amalie Sintetico", "AMALIE", "Sintético", [4.95]),
    ("15W-40", "Avenoil", "AVENOIL", "", [3.75]),
    ("15W-40", "Castrol", "Castrol", "", [5.80, 5.90, 6.50, 5.95, 7.55]),
    ("15W-40", "Citgo", "CITGO", "", [5.85]),
    ("15W-40", "mobil Delvac", "Mobil Delvac", "", [5.85]),
    ("15W-40", "Qualiguard", "Qualiguard", "", [3.00]),
    ("15W-40", "Shell Helix", "Shell Helix", "", [5.60, 5.40, 5.51]),
    ("15W-40", "Motul", "MOTUL", "", [5.40]),
    ("15W-40", "Total", "Total", "", [5.60]),
    ("20W-50", "Golden Supreme", "Golden Supreme", "", [2.95]),
    ("20W-50", "Abro", "ABRO", "", [4.50]),
    ("20W-50", "Amalie", "AMALIE", "", [4.60, 4.55, 3.55, 4.25, 3.97]),
    ("20W-50", "Amalie semi sintético", "AMALIE", "semi sintético", [4.95]),
    ("20W-50", "Avenoil", "AVENOIL", "", [3.75]),
    ("20W-50", "Citgo", "CITGO", "", [4.50]),
    ("20W-50", "Castrol", "Castrol", "", [5.25, 5.10, 4.45, 4.75, 5.00, 5.99]),
    ("20W-50", "Mobil", "Mobil", "", [4.55]),
    ("20W-50", "Penzoil", "Pennzoil", "", [4.65, 5.00]),
    ("20W-50", "Shell Helix", "Shell Helix", "", [5.60, 5.55, 5.00, 5.14]),
    ("20W-50", "Total", "Total", "", [5.35, 4.85]),
    ("20W-50", "Valvoline", "Valvoline", "", [3.75, 4.50]),
    ("40", "Sae 40 mobil", "Mobil", "", [4.99]),
    ("50", "Sae 50 Avenoil", "AVENOIL", "", [1.50]),
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def main() -> None:
    payload = fetch(SOURCE_URL)
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != SOURCE_SHA256:
        raise RuntimeError(f"ACODECO survey payload changed: {actual_sha}")
    records = []
    for number, (sae, source_label, brand, variant, prices) in enumerate(ROWS, start=1):
        product_name = " ".join(value for value in (brand, variant, sae) if value)
        flags = []
        if source_label == "Penzoil":
            flags.append("source_brand_spelling_penzoil_standardized_to_pennzoil")
        if source_label.startswith("Shevron"):
            flags.append("source_brand_spelling_shevron_standardized_to_chevron")
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"ACODECO-2020-{number:03d}-{normalize(source_label)}-{normalize(sae)}",
            "manufacturer": "",
            "brand": brand,
            "product_name": product_name,
            "source_product_label": source_label,
            "family_code": "M",
            "market": "Panama",
            "lifecycle_status": "historical_retail_price_observation_current_status_unverified",
            "survey_date": SURVEY_DATE,
            "package": "1/4 gallon",
            "currency": "PAB",
            "observed_prices": prices,
            "observed_price_min": min(prices),
            "observed_price_max": max(prices),
            "technical": {
                "sae_engine": sae,
                "sae_gear": "",
                "api": [],
                "api_gl": [],
                "acea": [],
                "ilsac": [],
                "iso_vg": "",
                "nlgi": "",
                "source_grade": "",
                "performance": [],
            },
            "source_url": SOURCE_URL,
            "source_pdf_sha256": actual_sha,
            "snapshot_date": SNAPSHOT_DATE,
            "flags": flags,
        })
    assert len(records) == 45
    assert len({row["source_record_id"] for row in records}) == 45
    assert Counter(row["technical"]["sae_engine"] for row in records) == {
        "10W-30": 19, "15W-40": 12, "20W-50": 12, "40": 1, "50": 1,
    }
    assert sum(len(row["observed_prices"]) for row in records) == 83

    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                for row in records),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_pdf_sha256": actual_sha,
        "survey_date": SURVEY_DATE,
        "pdf_pages": 2,
        "named_product_grade_rows": len(records),
        "sae_distribution": dict(sorted(Counter(
            row["technical"]["sae_engine"] for row in records
        ).items())),
        "brands": len({row["brand"] for row in records}),
        "retail_price_observations": sum(len(row["observed_prices"]) for row in records),
        "generic_rows_report_only": [
            "outboard motor oil",
            "ATF",
            "coolant",
            "tube grease",
            "battery fluid",
            "brake fluid",
            "power steering fluid",
            "diesel treatment",
            "gasoline treatment",
        ],
        "lifecycle_note": (
            "A January 2020 retail price observation proves a historical "
            "brand/grade occurrence. It does not prove current availability, "
            "API licensing, product quality or manufacturer approval."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
