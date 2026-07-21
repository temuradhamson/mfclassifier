#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS Turkey finder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = ingest_catalog(
        out=ROOT / "data/fuchs-turkey-products.jsonl",
        report_path=ROOT / "data/fuchs-turkey-products-report.json",
        source_url="https://www.fuchs.com/tr/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/tr/en/company/policies-and-approvals/terms-conditions-and-policies/",
        source_id="FUCHS_TURKEY_PRODUCT_FINDER",
        record_prefix="FUCHS-TR",
        manufacturer="OPET FUCHS MADENI YAĞ SAN. TIC. A.Ş.",
        market="TR",
        expected_embedded=632,
        expected_products=583,
        rights_review="The official Turkey site provides no general website-use imprint. Publication is conservatively limited to attributed factual identity, classification, specification, UID/URL and hash fields; marketing descriptions and page layout are excluded.",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
