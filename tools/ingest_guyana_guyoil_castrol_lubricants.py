#!/usr/bin/env python3
"""Build GUYOIL's explicitly identified current lubricant products.

GUYOIL is Guyana's state-owned petroleum distributor and the country's sole
authorized Castrol distributor.  Its current official product page names five
broader series whose portfolio grades are not printed; those series remain
report-only.  Only eleven explicit product/grade identities are normalized.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/guyana-guyoil-current-lubricants.jsonl"
REPORT = ROOT / "data/guyana-guyoil-current-lubricants-report.json"
SOURCE_ID = "GUYANA_GUYOIL_CURRENT_CASTROL_LUBRICANT_CATALOG"
PAGE_URL = "https://guyoil.gy/fuel-products/"
API_URL = "https://guyoil.gy/wp-json/wp/v2/pages?slug=fuel-products&context=view"
SNAPSHOT_DATE = "2026-07-23"
UA = "MFClassifier evidence catalog/1.0"


PRODUCTS = [
    {"name": "Castrol CRB 15W-40", "family_code": "M", "line": "heavy_duty_engine",
     "sae_engine": "15W-40"},
    {"name": "Castrol Diesel 40", "family_code": "M", "line": "heavy_duty_engine",
     "sae_engine": "40", "packages": ["quart", "gallon", "5 gallon", "55 gallon"]},
    {"name": "Castrol Diesel 50", "family_code": "M", "line": "heavy_duty_engine",
     "sae_engine": "50", "packages": ["quart", "gallon", "5 gallon", "55 gallon"]},
    {"name": "Castrol HD 40", "family_code": "M", "line": "gasoline_engine",
     "sae_engine": "40", "packages": ["quart", "gallon"]},
    {"name": "Castrol HD 50", "family_code": "M", "line": "gasoline_engine",
     "sae_engine": "50", "packages": ["quart", "gallon"]},
    {"name": "Castrol SOB", "family_code": "M", "line": "marine_two_stroke",
     "application": "outboard engine fuel-mixture lubricant"},
    {"name": "Castrol GO 2T", "family_code": "M", "line": "two_stroke",
     "application": "air-cooled small-engine fuel-mixture lubricant"},
    {"name": "Castrol AXLE Limited Slip", "family_code": "T", "line": "automotive_gear"},
    {"name": "Castrol Hypoy", "family_code": "T", "line": "automotive_gear",
     "source_name_spelling": "Hypoy"},
    {"name": "Castrol Axle GL", "family_code": "T", "line": "automotive_gear"},
    {"name": "Castrol EP Gear Oil", "family_code": "T", "line": "automotive_gear"},
]

SERIES_WITHOUT_PUBLISHED_GRADES = ["Castrol Edge", "Castrol Magnatec", "Castrol GTX", "Castrol Actevo"]


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def main() -> None:
    api_bytes = get(API_URL)
    pages = json.loads(api_bytes)
    if len(pages) != 1 or pages[0]["id"] != 1817:
        raise RuntimeError("GUYOIL fuel-products page identity changed")
    page = pages[0]
    rendered = page["content"]["rendered"]
    rendered_text = clean(rendered)

    required_tokens = [
        "CRB 15W40", "DIESEL 40", "DIESEL 50", "HD 40", "HD 50",
        "CASTROL SOB", "GO 2T", "AXLE Limited Slip", "Hypoy", "Axle GL", "EP Gear Oil",
    ]
    missing = [token for token in required_tokens if token.casefold() not in rendered_text.casefold()]
    if missing:
        raise RuntimeError(f"Explicit GUYOIL product identities disappeared: {missing}")
    if not all(series.casefold() in rendered_text.casefold() for series in SERIES_WITHOUT_PUBLISHED_GRADES):
        raise RuntimeError("GUYOIL report-only series set changed")

    page_facts = {
        "page_id": page["id"],
        "modified": page["modified"],
        "link": page["link"],
        "explicit_products": PRODUCTS,
        "series_without_published_grades": SERIES_WITHOUT_PUBLISHED_GRADES,
    }
    page_facts_sha = sha256(json.dumps(page_facts, ensure_ascii=False, sort_keys=True).encode())
    rows = []
    for index, product in enumerate(PRODUCTS, 1):
        rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"GUYOIL-GY-{index:02d}",
            "market": "Guyana",
            "manufacturer": "Castrol",
            "distributor": "The Guyana Oil Company Limited (GUYOIL)",
            "brand": "Castrol",
            "product_name": product["name"],
            "source_name_spelling": product.get("source_name_spelling", product["name"]),
            "product_line": product["line"],
            "family_code": product["family_code"],
            "technical": {
                "sae_engine": product.get("sae_engine", ""),
                "sae_gear": "",
                "api": [],
                "api_gl": [],
                "application": product.get("application", ""),
                "packages_source_reported": product.get("packages", []),
            },
            "lifecycle_status": "listed_on_current_official_state_distributor_page",
            "evidence_status": "official_state_owned_distributor_product_catalog",
            "snapshot_date": SNAPSHOT_DATE,
            "source_url": PAGE_URL,
            "source_page_id": page["id"],
            "source_page_modified": page["modified"],
            "source_page_api_sha256": sha256(api_bytes),
            "source_page_facts_sha256": page_facts_sha,
            "source_quality_flags": [
                "explicit_product_identity_only",
                "series_without_published_grade_excluded_from_canonical_products",
                "distributor_listing_not_independent_performance_approval",
                "marketing_prose_excluded",
            ],
        })

    if len(rows) != 11:
        raise RuntimeError(f"GUYOIL audit matrix drift: {len(rows)} rows")
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "source_page_id": page["id"],
        "source_page_modified": page["modified"],
        "source_page_api_sha256": sha256(api_bytes),
        "source_page_facts_sha256": page_facts_sha,
        "normalized_products": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "rows_with_sae": sum(bool(row["technical"]["sae_engine"]) for row in rows),
        "rows_with_source_packages": sum(bool(row["technical"]["packages_source_reported"]) for row in rows),
        "series_without_published_grades_report_only": SERIES_WITHOUT_PUBLISHED_GRADES,
        "normalized_output_sha256": sha256(OUT.read_bytes()),
        "audit_boundary": (
            "Only explicit product/grade identities are normalized. Edge, Magnatec, GTX and Actevo "
            "are named as series but have no printed portfolio grades and therefore remain report-only."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
