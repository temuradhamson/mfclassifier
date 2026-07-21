#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Spain finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-spain-products.jsonl",
        report_path=ROOT / "data/fuchs-spain-products-report.json",
        source_url="https://www.fuchs.com/es/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/es/en/imprint/",
        source_id="FUCHS_SPAIN_PRODUCT_FINDER",
        record_prefix="FUCHS-ES",
        manufacturer="FUCHS LUBRICANTES, S.A.U.",
        market="ES",
        expected_embedded=1017,
        expected_products=938,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
