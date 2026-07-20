#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Germany finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-germany-products.jsonl",
        report_path=ROOT / "data/fuchs-germany-products-report.json",
        source_url="https://www.fuchs.com/de/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/de/en/imprint/",
        source_id="FUCHS_GERMANY_PRODUCT_FINDER",
        record_prefix="FUCHS-DE",
        manufacturer="FUCHS LUBRICANTS GERMANY GMBH",
        market="DE",
        expected_embedded=1464,
        expected_products=1464,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
