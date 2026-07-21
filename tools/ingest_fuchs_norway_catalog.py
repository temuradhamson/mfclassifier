#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Norway finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-norway-products.jsonl",
        report_path=ROOT / "data/fuchs-norway-products-report.json",
        source_url="https://www.fuchs.com/no/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/no/en/imprint/",
        source_id="FUCHS_NORWAY_PRODUCT_FINDER",
        record_prefix="FUCHS-NO",
        manufacturer="FUCHS LUBRICANTS NORWAY AS",
        market="NO",
        expected_embedded=650,
        expected_products=649,
        snapshot_date="2026-07-21",
        rights_review="The official imprint permits use, copying and distribution for informational purposes within an organisation when the copyright notice is retained, and prohibits commercial use. Only attributed factual fields are republished; marketing descriptions are excluded and represented only by SHA-256 evidence hashes.",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
