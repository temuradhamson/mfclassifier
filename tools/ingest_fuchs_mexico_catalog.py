#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Mexico finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-mexico-products.jsonl",
        report_path=ROOT / "data/fuchs-mexico-products-report.json",
        source_url="https://www.fuchs.com/mx/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/mx/en/imprint/",
        source_id="FUCHS_MEXICO_PRODUCT_FINDER",
        record_prefix="FUCHS-MX",
        manufacturer="LUBRICANTES FUCHS DE MEXICO SA DE CV",
        market="MX",
        expected_embedded=364,
        expected_products=314,
        rights_review="The official imprint permits informational organizational use when the copyright notice is retained and prohibits commercial use. Only attributed factual fields are republished; marketing descriptions are excluded and represented only by SHA-256 evidence hashes.",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
