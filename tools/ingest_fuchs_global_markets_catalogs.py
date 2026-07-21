#!/usr/bin/env python3
"""Normalize official FUCHS product finders from additional global markets."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]
RIGHTS_REVIEW = (
    "The official imprint permits use, copying and distribution for informational "
    "purposes within an organisation when the copyright notice is retained, and "
    "prohibits commercial use. Only attributed factual fields are republished; "
    "marketing descriptions are excluded and represented only by SHA-256 evidence hashes."
)
CATALOGS = [
    ("korea", "kr", "KR", "FUCHS LUBRICANTS (KOREA) LTD.", 249, 221),
    ("uae", "ae", "AE", "FUCHS OIL MIDDLE EAST LTD.", 1073, 965),
    ("argentina", "ar", "AR", "FUCHS ARGENTINA S.A.", 35, 5),
    ("chile", "cl", "CL", "FUCHS LUBRICANTS SpA", 549, 496),
    ("ukraine", "ua", "UA", "FUCHS MASTYLA UKRAINA LLC", 918, 842),
    ("slovakia", "sk", "SK", "FUCHS OIL CORP. (SK), spol. s r. o.", 1074, 966),
    ("slovenia", "si", "SI", "FUCHS MAZIVA LSL D.O.O.", 1, 1),
    ("croatia", "hr", "HR", "FUCHS MAZIVA D.O.O.", 1082, 975),
]


def main() -> None:
    reports = []
    for slug, country_path, market, manufacturer, embedded, products in CATALOGS:
        reports.append(ingest_catalog(
            out=ROOT / f"data/fuchs-{slug}-products.jsonl",
            report_path=ROOT / f"data/fuchs-{slug}-products-report.json",
            source_url=f"https://www.fuchs.com/{country_path}/en/products/service-links/product-finder/",
            imprint_url=f"https://www.fuchs.com/{country_path}/en/imprint/",
            source_id=f"FUCHS_{slug.upper()}_PRODUCT_FINDER",
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
