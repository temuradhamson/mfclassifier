#!/usr/bin/env python3
"""Capture NP ULTRA's current first-party export-market statement.

This layer proves brand/channel presence only. It must not replicate the
already integrated NP ULTRA product-grade catalog into every export market.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/np-ultra-current-export-presence.jsonl"
REPORT = ROOT / "data/np-ultra-current-export-presence-report.json"
SOURCE_ID = "NP_ULTRA_CURRENT_EXPORT_MARKET_PRESENCE"
SOURCE_URL = "https://www.np.co.tt/ultra-lubricants/"
SOURCE_PAGE_MODIFIED_GMT = "2025-07-07T09:25:58"
SOURCE_LABELS = (
    "Anguilla",
    "Antigua",
    "Barbados",
    "Grenada",
    "Guyana",
    "Montserrat",
    "St. Lucia",
    "St. Kitts and Nevis",
    "St. Vincent",
    "Jamaica",
    "St. Maarten",
    "Suriname",
    "Tortola",
    "Grenada",
)
MARKET_NORMALIZATION = {
    "Anguilla": "Anguilla",
    "Antigua": "Antigua and Barbuda",
    "Barbados": "Barbados",
    "Grenada": "Grenada",
    "Guyana": "Guyana",
    "Montserrat": "Montserrat",
    "St. Lucia": "Saint Lucia",
    "St. Kitts and Nevis": "Saint Kitts and Nevis",
    "St. Vincent": "Saint Vincent and the Grenadines",
    "Jamaica": "Jamaica",
    "St. Maarten": "Sint Maarten (Dutch part)",
    "Suriname": "Suriname",
    "Tortola": "British Virgin Islands",
}


def fetch(url: str) -> bytes:
    result = subprocess.run(
        [
            "curl", "-LsS", "--fail", "--max-time", "60",
            "-A", "Mozilla/5.0 (compatible; catalog-research/1.0)", url,
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


def slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")


def render(rows: list[dict]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )


def main() -> None:
    text = visible_text(fetch(SOURCE_URL))
    statement = (
        "Export: NPMC products, except fuels, can be found in territories "
        "such as Anguilla, Antigua, Barbados, Grenada, Guyana, Montserrat, "
        "St. Lucia, St. Kitts and Nevis, St. Vincent, Jamaica, St. Maarten, "
        "Suriname, Tortola and Grenada."
    )
    assert statement in text
    assert "249 Stock Keeping Units (SKUs)" in text
    assert "Over 50 different lubricants manufactured" in text

    occurrences = Counter(SOURCE_LABELS)
    rows = []
    for source_label in dict.fromkeys(SOURCE_LABELS):
        market = MARKET_NORMALIZATION[source_label]
        flags = [
            "official_first_party_export_market_statement",
            "brand_presence_not_product_availability",
            "no_local_sku_stock_or_full_range_inference_permitted",
            "no_marketing_text_or_images_redistributed",
        ]
        if occurrences[source_label] > 1:
            flags.append("source_market_label_repeated_verbatim")
        if source_label != market:
            flags.append("source_market_label_normalized")
        rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": "NP-ULTRA-EXPORT-" + slug(market),
            "market": market,
            "source_market_label": source_label,
            "source_occurrences": occurrences[source_label],
            "brand": "NP ULTRA",
            "manufacturer": (
                "Trinidad & Tobago National Petroleum Marketing Company Limited"
            ),
            "source_url": SOURCE_URL,
            "source_page_modified_gmt": SOURCE_PAGE_MODIFIED_GMT,
            "snapshot_date": str(date.today()),
            "evidence_scope": "export_market_brand_presence_only",
            "product_scope_status": (
                "existing_np_ultra_product_catalog_not_replicated_by_market"
            ),
            "source_quality_flags": flags,
        })

    rendered = render(rows)
    OUT.write_text(rendered, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_page_modified_gmt": SOURCE_PAGE_MODIFIED_GMT,
        "snapshot_date": str(date.today()),
        "source_market_occurrences": len(SOURCE_LABELS),
        "unique_market_rows": len(rows),
        "repeated_source_labels": {
            key: count for key, count in occurrences.items() if count > 1
        },
        "markets": [row["market"] for row in rows],
        "normalized_output_sha256": hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "The official page identifies export territories for NPMC "
            "non-fuel products. Rows prove NP ULTRA market presence only; "
            "they do not assert local availability of any specific SKU."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
