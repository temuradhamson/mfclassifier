#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Poland finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-poland-products.jsonl",
        report_path=ROOT / "data/fuchs-poland-products-report.json",
        source_url="https://www.fuchs.com/pl/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/pl/en/imprint/",
        source_id="FUCHS_POLAND_PRODUCT_FINDER",
        record_prefix="FUCHS-PL",
        manufacturer="FUCHS OIL CORPORATION (PL) SP. Z O.O.",
        market="PL",
        expected_embedded=776,
        expected_products=690,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
