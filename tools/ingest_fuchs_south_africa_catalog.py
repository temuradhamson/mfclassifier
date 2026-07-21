#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS South Africa finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-south-africa-products.jsonl",
        report_path=ROOT / "data/fuchs-south-africa-products-report.json",
        source_url="https://www.fuchs.com/za/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/za/en/imprint/",
        source_id="FUCHS_SOUTH_AFRICA_PRODUCT_FINDER",
        record_prefix="FUCHS-ZA",
        manufacturer="FUCHS LUBRICANTS SOUTH AFRICA",
        market="ZA",
        expected_embedded=864,
        expected_products=756,
        rights_review="The official imprint permits informational organizational use when the copyright notice is retained and prohibits commercial use. Only attributed factual fields are republished; marketing descriptions are excluded and represented only by SHA-256 evidence hashes.",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
