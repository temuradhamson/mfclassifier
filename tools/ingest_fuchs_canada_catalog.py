#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Canada finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-canada-products.jsonl",
        report_path=ROOT / "data/fuchs-canada-products-report.json",
        source_url="https://www.fuchs.com/ca/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/ca/en/imprint/",
        source_id="FUCHS_CANADA_PRODUCT_FINDER",
        record_prefix="FUCHS-CA",
        manufacturer="FUCHS LUBRICANTS CANADA LTD.",
        market="CA",
        expected_embedded=323,
        expected_products=289,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
