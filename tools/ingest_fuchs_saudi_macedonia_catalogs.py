#!/usr/bin/env python3
"""Normalize official FUCHS product finders for Saudi Arabia and Macedonia."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]
RIGHTS_REVIEW = (
    "The official imprint expressly permits use, copying and distribution for "
    "informational purposes within an organisation when the complete copyright "
    "notice is retained, and prohibits commercial use. Only attributed factual "
    "fields are republished; marketing descriptions are excluded and represented "
    "only by SHA-256 evidence hashes."
)
CATALOGS = [
    ("saudi-arabia", "sa", "SA", "Alhamrani-Fuchs Petroleum Saudi Arabia Limited", 376, 360),
    ("macedonia", "mk", "MK", "FUCHS MAK DOOEL", 1075, 948),
]


def main() -> None:
    reports = []
    for slug, country_path, market, manufacturer, embedded, products in CATALOGS:
        reports.append(ingest_catalog(
            out=ROOT / f"data/fuchs-{slug}-products.jsonl",
            report_path=ROOT / f"data/fuchs-{slug}-products-report.json",
            source_url=f"https://www.fuchs.com/{country_path}/en/products/service-links/product-finder/",
            imprint_url=f"https://www.fuchs.com/{country_path}/en/imprint/",
            source_id=f"FUCHS_{slug.upper().replace('-', '_')}_PRODUCT_FINDER",
            record_prefix=f"FUCHS-{market}",
            manufacturer=manufacturer,
            market=market,
            expected_embedded=embedded,
            expected_products=products,
            snapshot_date="2026-07-21",
            rights_review=RIGHTS_REVIEW,
        ))
    print(json.dumps({
        "sources": len(reports),
        "products": sum(row["products"] for row in reports),
        "reports": reports,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
