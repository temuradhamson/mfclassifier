#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Sweden finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-sweden-products.jsonl",
        report_path=ROOT / "data/fuchs-sweden-products-report.json",
        source_url="https://www.fuchs.com/se/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/se/en/imprint/",
        source_id="FUCHS_SWEDEN_PRODUCT_FINDER",
        record_prefix="FUCHS-SE",
        manufacturer="FUCHS LUBRICANTS SWEDEN AB",
        market="SE",
        expected_embedded=675,
        expected_products=675,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
