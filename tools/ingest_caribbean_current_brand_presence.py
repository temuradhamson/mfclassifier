#!/usr/bin/env python3
"""Capture current first-party Caribbean Shell and Total brand presence.

The two layers prove distribution/retail brand presence only. They never
expand a manufacturer's global range into country-level SKU availability.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VADD_OUT = ROOT / "data/antigua-vadd-shell-current-presence.jsonl"
VADD_REPORT = ROOT / "data/antigua-vadd-shell-current-presence-report.json"
RUBIS_OUT = ROOT / "data/rubis-caribbean-total-current-presence.jsonl"
RUBIS_REPORT = ROOT / "data/rubis-caribbean-total-current-presence-report.json"
VADD_SOURCE_ID = "ANTIGUA_VADD_SHELL_CURRENT_DISTRIBUTOR_PRESENCE"
RUBIS_SOURCE_ID = "RUBIS_CARIBBEAN_TOTAL_CURRENT_RETAIL_PRESENCE"
VADD_URL = "https://vaderrick.com/"
RUBIS_URL = "https://www.rubis-caribbean.com/total-lubricants/"
RUBIS_MARKETS = (
    "Antigua and Barbuda",
    "Barbados",
    "Grenada",
    "Guyana",
    "Saint Lucia",
    "Saint Vincent and the Grenadines",
)


def fetch(url: str) -> bytes:
    result = subprocess.run(
        ["curl", "-LsS", "--fail", "--max-time", "60", url],
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


def render(rows: list[dict]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )


def write_report(
    path: Path,
    source_id: str,
    source_url: str,
    rows: list[dict],
    rendered: str,
    note: str,
) -> None:
    report = {
        "source_id": source_id,
        "source_url": source_url,
        "snapshot_date": str(date.today()),
        "evidence_rows": len(rows),
        "markets": [row["market"] for row in rows],
        "normalized_output_sha256": hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": note,
    }
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def main() -> None:
    vadd_payload = fetch(VADD_URL)
    rubis_payload = fetch(RUBIS_URL)
    vadd_text = visible_text(vadd_payload)
    rubis_text = visible_text(rubis_payload)
    assert (
        "We are your authorized agent for Shell Engine Oils and Lubricants"
        in vadd_text
    )
    rubis_statement = (
        "Total Lubricants are sold exclusively at all RUBIS Service Stations "
        "throughout Antigua, Barbados, Grenada, Guyana, St Lucia and St Vincent."
    )
    assert rubis_statement in rubis_text

    common_flags = [
        "official_first_party_distribution_statement",
        "brand_presence_not_product_availability",
        "no_marketing_text_or_images_redistributed",
    ]
    vadd_rows = [{
        "source_id": VADD_SOURCE_ID,
        "source_record_id": "VADD-SHELL-ANTIGUA-BARBUDA",
        "market": "Antigua and Barbuda",
        "brand": "SHELL",
        "distributor": "V.A. Derrick Distributors",
        "source_url": VADD_URL,
        "snapshot_date": str(date.today()),
        "evidence_scope": "authorized_brand_agent_presence_only",
        "product_scope_status": (
            "no_local_sku_stock_or_full_global_range_inference_permitted"
        ),
        "source_quality_flags": common_flags,
    }]
    rubis_rows = [
        {
            "source_id": RUBIS_SOURCE_ID,
            "source_record_id": (
                "RUBIS-TOTAL-"
                + re.sub(r"[^A-Z0-9]+", "-", market.upper()).strip("-")
            ),
            "market": market,
            "brand": "TOTALENERGIES",
            "source_brand_label": "Total Lubricants",
            "retail_channel": "RUBIS Service Stations",
            "source_url": RUBIS_URL,
            "source_page_modified": "2025-04-07T14:49:24+00:00",
            "snapshot_date": str(date.today()),
            "evidence_scope": "exclusive_retail_brand_presence_only",
            "product_scope_status": (
                "no_local_sku_stock_or_full_global_range_inference_permitted"
            ),
            "source_quality_flags": common_flags,
        }
        for market in RUBIS_MARKETS
    ]
    vadd_rendered = render(vadd_rows)
    rubis_rendered = render(rubis_rows)
    VADD_OUT.write_text(vadd_rendered, encoding="utf-8")
    RUBIS_OUT.write_text(rubis_rendered, encoding="utf-8")
    write_report(
        VADD_REPORT,
        VADD_SOURCE_ID,
        VADD_URL,
        vadd_rows,
        vadd_rendered,
        (
            "V.A. Derrick's first-party statement confirms authorised Shell "
            "agent presence in Antigua and Barbuda only; no SKU inference."
        ),
    )
    write_report(
        RUBIS_REPORT,
        RUBIS_SOURCE_ID,
        RUBIS_URL,
        rubis_rows,
        rubis_rendered,
        (
            "RUBIS explicitly names six Total Lubricants retail markets. "
            "The rows prove brand/channel presence, not local SKU or stock."
        ),
    )


if __name__ == "__main__":
    main()
