#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Italy finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-italy-products.jsonl",
        report_path=ROOT / "data/fuchs-italy-products-report.json",
        source_url="https://www.fuchs.com/it/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/it/en/imprint/",
        source_id="FUCHS_ITALY_PRODUCT_FINDER",
        record_prefix="FUCHS-IT",
        manufacturer="FUCHS LUBRIFICANTI S.P.A.",
        market="IT",
        expected_embedded=1174,
        expected_products=1007,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
