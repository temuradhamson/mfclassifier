#!/usr/bin/env python3
"""Normalize market evidence from every MOGAS country shop listed on its site.

Six country Store APIs expose the same 39-card catalog; Rwanda exposes five
local package/grade cards.  This layer links market observations to the already
normalized MOGAS identities and never duplicates the canonical products.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PRODUCTS = ROOT / "data/burundi-mogas-current-products.jsonl"
OUT = ROOT / "data/mogas-global-market-shop-observations.jsonl"
REPORT = ROOT / "data/mogas-global-market-shop-report.json"
SOURCE_ID = "MOGAS_GLOBAL_OFFICIAL_COUNTRY_SHOP_APIS"
HOME_URL = "https://mogasoil.com/"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"
MARKETS = {
    "burundi": "Burundi",
    "drc": "Democratic Republic of the Congo",
    "kenya": "Kenya",
    "rwanda": "Rwanda",
    "tanzania": "Tanzania",
    "uae": "United Arab Emirates",
    "uganda": "Uganda",
}
FULL_MARKETS = {"burundi", "drc", "kenya", "tanzania", "uae", "uganda"}
LPG_NAMES = {"6kg Cylinder", "13kg Cylinder", "45kg Cylinder"}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def fetch_json(url: str) -> list[dict]:
    return json.loads(fetch(url))


def normalized_attributes(row: dict) -> dict[str, list[str]]:
    return {
        attribute["name"]: sorted(term["name"] for term in attribute["terms"])
        for attribute in row.get("attributes", [])
    }


def target_rows_for_rwanda(row: dict, base_rows: list[dict]) -> list[str]:
    name = html.unescape(row["name"]).casefold()
    if "hydrax z 68" in name:
        return [
            base["source_record_id"] for base in base_rows
            if base["source_card_id"] == 146
            and base["specifications"].get("iso_vg") == "68"
        ]
    if "grease mp3" in name:
        return [
            base["source_record_id"] for base in base_rows
            if base["source_card_id"] == 186
            and base["specifications"].get("nlgi") == "3"
        ]
    if name == "mogas hydrax z series":
        published = {
            term["name"].removeprefix("Z")
            for attribute in row["attributes"]
            if attribute["name"].casefold() == "grade"
            for term in attribute["terms"]
        }
        return [
            base["source_record_id"] for base in base_rows
            if base["source_card_id"] == 146
            and base["specifications"].get("iso_vg") in published
        ]
    if name == "mogas dynatrans":
        return [
            base["source_record_id"] for base in base_rows
            if base["source_card_id"] == 135
        ]
    raise RuntimeError(f"Unmapped Rwanda product: {row['name']!r}")


def main() -> None:
    home_payload = fetch(HOME_URL)
    home_text = home_payload.decode(errors="replace")
    discovered = {
        match.group(1).casefold()
        for match in re.finditer(
            r"https?://mogasoil\.com/([^/\"'#?]+)/?", home_text, re.I
        )
        if match.group(1).casefold() in MARKETS
    }
    if discovered != set(MARKETS):
        raise RuntimeError(f"MOGAS market denominator changed: {discovered}")

    base_rows = [
        json.loads(line)
        for line in BASE_PRODUCTS.read_text(encoding="utf-8").splitlines()
        if line
    ]
    base_by_card: dict[int, list[str]] = {}
    for row in base_rows:
        base_by_card.setdefault(row["source_card_id"], []).append(
            row["source_record_id"]
        )

    baseline_names: set[str] | None = None
    observations = []
    api_hashes = {}
    for slug, market in MARKETS.items():
        api_url = (
            f"https://mogasoil.com/{slug}/wp-json/wc/store/v1/"
            "products?per_page=100"
        )
        payload = fetch(api_url)
        source_rows = json.loads(payload)
        api_hashes[slug] = hashlib.sha256(payload).hexdigest()
        expected_count = 39 if slug in FULL_MARKETS else 5
        if len(source_rows) != expected_count:
            raise RuntimeError(f"{slug} API count changed: {len(source_rows)}")

        relevant = [
            row for row in source_rows
            if html.unescape(row["name"]) not in LPG_NAMES
        ]
        if slug in FULL_MARKETS:
            names = {html.unescape(row["name"]) for row in relevant}
            if baseline_names is None:
                baseline_names = names
            elif names != baseline_names:
                raise RuntimeError(f"{slug} full-catalog name set changed")
            burundi_name_to_card = {
                html.unescape(row["name"]): row["id"]
                for row in (
                    source_rows if slug == "burundi" else fetch_json(
                        "https://mogasoil.com/burundi/wp-json/wc/store/v1/"
                        "products?per_page=100"
                    )
                )
            }

        for row in relevant:
            if slug in FULL_MARKETS:
                card_id = burundi_name_to_card[html.unescape(row["name"])]
                targets = sorted(base_by_card[card_id])
            else:
                card_id = None
                targets = sorted(target_rows_for_rwanda(row, base_rows))
            prices = row["prices"]
            currency_status = (
                "local_currency_plausible_pending_variant_level_offer_audit"
                if slug in {"uganda", "rwanda"}
                else "configured_currency_conflicted_excluded_from_analytics"
            )
            observations.append({
                "source_id": SOURCE_ID,
                "source_record_id": f"MOGAS-MARKET-{slug.upper()}-{row['id']}",
                "snapshot_date": SNAPSHOT_DATE,
                "market": market,
                "market_slug": slug,
                "source_product_id": row["id"],
                "source_product_name": html.unescape(row["name"]),
                "source_url": row["permalink"],
                "api_url": api_url,
                "reference_burundi_card_id": card_id,
                "target_burundi_source_record_ids": targets,
                "source_categories": sorted(
                    category["name"] for category in row["categories"]
                ),
                "source_attributes": normalized_attributes(row),
                "source_price_minor_units": prices["price"],
                "source_regular_price_minor_units": prices["regular_price"],
                "source_sale_price_minor_units": prices["sale_price"],
                "source_price_range": prices["price_range"],
                "source_currency_code": prices["currency_code"],
                "source_currency_symbol": prices["currency_symbol"],
                "source_currency_minor_unit": prices["currency_minor_unit"],
                "currency_evidence_status": currency_status,
                "source_is_in_stock": row["is_in_stock"],
                "source_is_purchasable": row["is_purchasable"],
                "source_has_options": row["has_options"],
                "source_variation_count": len(row["variations"]),
                "lifecycle_status": "current_official_country_shop_observation",
                "evidence_status": "official_manufacturer_country_shop_api",
                "source_quality_flags": [
                    "market_observation_linked_to_existing_mogas_identity",
                    "no_cross_market_product_duplication",
                    "price_not_promoted_to_offer_until_variant_and_currency_audit",
                ] + (
                    []
                    if slug in {"uganda", "rwanda"}
                    else ["configured_currency_conflicted_excluded_from_analytics"]
                ),
            })

    observations.sort(key=lambda row: row["source_record_id"])
    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in observations
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "all_officially_listed_mogas_country_shop_apis_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "official_markets": len(MARKETS),
        "market_names": list(MARKETS.values()),
        "full_catalog_markets": len(FULL_MARKETS),
        "full_catalog_api_cards_per_market": 39,
        "full_catalog_relevant_cards_per_market": 36,
        "rwanda_api_cards": 5,
        "market_card_observations": len(observations),
        "product_identity_links": sum(
            len(row["target_burundi_source_record_ids"])
            for row in observations
        ),
        "observations_by_market": dict(sorted(Counter(
            row["market"] for row in observations
        ).items())),
        "currency_codes_by_market": {
            market: sorted({
                row["source_currency_code"]
                for row in observations if row["market"] == market
            })
            for market in MARKETS.values()
        },
        "configured_currency_conflict_observations": sum(
            row["currency_evidence_status"].startswith("configured")
            for row in observations
        ),
        "local_currency_pending_offer_audit_observations": sum(
            row["currency_evidence_status"].startswith("local")
            for row in observations
        ),
        "home_market_links_sha256": hashlib.sha256(
            ("\n".join(sorted(discovered)) + "\n").encode()
        ).hexdigest(),
        "api_payload_sha256": dict(sorted(api_hashes.items())),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "deduplication_note": "Market cards link to the 45 normalized MOGAS identities created from the complete Burundi-section technical catalog; no country copy creates a new canonical product.",
        "price_note": "UGX and RWF observations remain pending variant-level offer normalization. All other configured currencies are retained as raw evidence and excluded from analytics.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
