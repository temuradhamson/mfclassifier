#!/usr/bin/env python3
"""Capture current official Lubex statements about MAG 1 presence in Haiti."""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/haiti-lubex-mag1-current-presence.jsonl"
REPORT = ROOT / "data/haiti-lubex-mag1-current-presence-report.json"
SOURCE_ID = "HAITI_LUBEX_MAG1_CURRENT_DISTRIBUTOR_PRESENCE"
HOME_URL = "https://www.lubex.net/"
PRODUCT_URL = (
    "https://www.lubex.net/market-sectors/automotive-chemicals/"
)


def fetch(url: str) -> bytes:
    result = subprocess.run(
        [
            "curl",
            "-LsS",
            "--fail",
            "--max-time",
            "60",
            url,
        ],
        check=True,
        capture_output=True,
    )
    return result.stdout


def visible_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="replace")
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(
        r"\s+",
        " ",
        html.unescape(text).replace("\xa0", " "),
    ).strip()


def main() -> None:
    home_payload = fetch(HOME_URL)
    product_payload = fetch(PRODUCT_URL)
    home_text = visible_text(home_payload)
    product_text = visible_text(product_payload)
    required_home = (
        "We are the exclusive authorized distributor of MAG1 "
        "lubricants products in Haiti."
    )
    required_product = "Exclusive MAG1 Product Distributor in Haiti"
    assert required_home.casefold() in home_text.casefold()
    assert required_product.casefold() in product_text.casefold()
    evidence_projection = {
        "market": "Haiti",
        "brand": "MAG 1",
        "distributor": "Lubex S.A.",
        "authorized_distributor_statement": True,
        "exclusive_distributor_statement": True,
        "home_url": HOME_URL,
        "product_url": PRODUCT_URL,
    }
    projection_json = json.dumps(
        evidence_projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    row = {
        "source_id": SOURCE_ID,
        "source_record_id": "LUBEX-MAG1-HAITI",
        **evidence_projection,
        "snapshot_date": str(date.today()),
        "http_statuses": {HOME_URL: 200, PRODUCT_URL: 200},
        "evidence_projection_sha256": hashlib.sha256(
            projection_json.encode("utf-8")
        ).hexdigest(),
        "evidence_scope": (
            "authorized_brand_distributor_presence_only"
        ),
        "product_scope_status": (
            "no_local_sku_stock_or_full_global_range_inference_permitted"
        ),
        "source_quality_flags": [
            "official_distributor_first_party_statement",
            "brand_presence_not_product_availability",
            "marketing_text_not_redistributed",
        ],
    }
    rendered = json.dumps(
        row,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"
    OUT.write_text(rendered, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": HOME_URL,
        "source_product_url": PRODUCT_URL,
        "snapshot_date": str(date.today()),
        "evidence_rows": 1,
        "normalized_output_sha256": hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "First-party Lubex evidence confirms MAG 1 distributor/brand "
            "presence in Haiti only. It does not prove any specific SKU, "
            "stock state or the complete global MAG 1 range in Haiti."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
