#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Brazil finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-brazil-products.jsonl",
        report_path=ROOT / "data/fuchs-brazil-products-report.json",
        source_url="https://www.fuchs.com/br/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/br/en/imprint/",
        source_id="FUCHS_BRAZIL_PRODUCT_FINDER",
        record_prefix="FUCHS-BR",
        manufacturer="FUCHS LUBRIFICANTES DO BRASIL LTDA",
        market="BR",
        expected_embedded=213,
        expected_products=182,
        snapshot_date="2026-07-21",
        rights_review="The official imprint permits use, copying and distribution for informational purposes within an organisation when the copyright notice is retained, and prohibits commercial use. Only attributed factual fields are republished; marketing descriptions are excluded and represented only by SHA-256 evidence hashes.",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
