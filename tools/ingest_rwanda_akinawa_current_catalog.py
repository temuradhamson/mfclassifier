#!/usr/bin/env python3
"""Normalize the complete current Akinawa catalog published by Leadway Rwanda.

Leadway identifies itself as the exclusive Rwanda distributor and its public
Store API exposes ten cards.  Several card titles conflict materially with the
body copy; agreed fields may enter strict keys, while disputed API/JASO/marine
classes remain source-reported only.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/rwanda-akinawa-current-products.jsonl"
REPORT = ROOT / "data/rwanda-akinawa-current-report.json"
SOURCE_ID = "RWANDA_LEADWAY_AKINAWA_CURRENT_COMPLETE_CATALOG"
API_URL = "https://leadwaydistribution.com/wp-json/wc/store/v1/products?per_page=100"
LANDING_URL = "https://leadwaydistribution.com/products/"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if value:
            self.parts.append(value)


def clean_html(value: str) -> str:
    parser = VisibleText()
    parser.feed(value)
    return " | ".join(parser.parts)


def product(card_id: int, name: str, family: str, **specifications: object) -> dict:
    return {
        "card_id": card_id,
        "product_name": name,
        "family_code": family,
        "specifications": specifications,
    }


PRODUCTS = [
    product(
        524, "Akinawa Premium Heavy Duty Grease MP2", "G",
        nlgi="2", grease_type="multipurpose heavy-duty",
        source_reported_grade="MP-2",
    ),
    product(
        522, "Akinawa CVT Fluid FE", "T",
        cvt_specifications=["CVT FE"], base_oil="synthetic",
    ),
    product(
        497, "Akinawa ATF WS", "T",
        atf_specifications=["ATF WS"],
        source_reported_base_oil_values=[
            "Synthetic Blended in title", "Fully synthetic in body",
        ],
        source_quality_flags=[
            "title_synthetic_blended_conflicts_with_body_fully_synthetic",
        ],
    ),
    product(
        496, "Akinawa Gear Oil GL-5 SAE 75W-90 LSD", "T",
        sae_gear="75W-90", api_gl=["GL-5"], differential_type="LSD",
        base_oil="synthetic",
    ),
    product(
        464, "Akinawa Diesel SAE 10W-40", "M",
        sae_engine="10W-40", base_oil="synthetic blend",
        source_reported_api_values=[
            "CI-4 in product title", "SN/CF in body application",
        ],
        source_reported_product_line_values=[
            "Akinawa Diesel in title", "Platinum 5 in body",
        ],
        source_quality_flags=[
            "title_ci4_conflicts_with_body_sn_cf_not_promoted_to_strict_api",
            "title_product_line_conflicts_with_body_platinum5",
        ],
    ),
    product(
        463, "Akinawa Gold LL SAE 5W-40", "M",
        sae_engine="5W-40", base_oil="synthetic",
        source_reported_api_values=[
            "SN/CF in title", "SP in body application",
        ],
        source_reported_ilsac_values=["GF-6A in body application"],
        source_quality_flags=[
            "title_sn_cf_conflicts_with_body_sp_not_promoted_to_strict_api",
        ],
    ),
    product(
        462, "Akinawa Gold SAE 5W-30", "M",
        sae_engine="5W-30", base_oil="synthetic",
        source_reported_api_values=["SN in title", "SP in body application"],
        source_reported_ilsac_values=[
            "GF-5 in title", "GF-6A in body application",
        ],
        source_quality_flags=[
            "title_sn_gf5_conflicts_with_body_sp_gf6a_not_promoted_to_strict_performance",
        ],
    ),
    product(
        367, "Akinawa 4-Stroke SAE 20W-50", "M",
        sae_engine="20W-50",
        source_reported_motorcycle_performance=["MA2 in title"],
        source_reported_api_values=["SN/CF in passenger-car body application"],
        source_reported_base_oil_values=[
            "Semi-synthetic in body", "Refined paraffinic base oils in body",
        ],
        source_quality_flags=[
            "motorcycle_ma2_title_conflicts_with_passenger_car_sn_cf_body_not_promoted_to_strict_performance",
        ],
    ),
    product(
        355, "Akinawa Marine 2T Outboard", "M",
        source_reported_marine_performance=["TC-W3 in title"],
        source_reported_body_identity=[
            "Titanium1 SAE 0W-30 hybrid passenger-car oil",
            "API SP", "ILSAC GF-6A",
        ],
        source_quality_flags=[
            "marine_2t_tcw3_title_conflicts_with_hybrid_0w30_sp_gf6a_body_no_strict_key",
        ],
    ),
    product(
        340, "Akinawa Gold Hybrid SAE 0W-20", "M",
        sae_engine="0W-20", base_oil="synthetic",
        source_reported_api_values=["SN in title", "SP in body application"],
        source_reported_ilsac_values=["GF-6A in body application"],
        source_quality_flags=[
            "title_sn_conflicts_with_body_sp_not_promoted_to_strict_api",
        ],
    ),
]


def main() -> None:
    api_payload = fetch(API_URL)
    source_rows = json.loads(api_payload)
    landing_payload = fetch(LANDING_URL)
    landing_text = clean_html(landing_payload.decode(errors="replace"))
    if len(source_rows) != 10:
        raise RuntimeError(f"Akinawa card denominator changed: {len(source_rows)}")
    if "exclusive distributor" not in landing_text.casefold():
        raise RuntimeError("Leadway exclusivity statement not found")
    expected = {row["card_id"] for row in PRODUCTS}
    if {row["id"] for row in source_rows} != expected:
        raise RuntimeError("Akinawa Store API identities changed")

    by_id = {row["id"]: row for row in source_rows}
    records = []
    for index, source in enumerate(PRODUCTS, 1):
        card = by_id[source["card_id"]]
        card_facts = {
            "id": card["id"],
            "name": html.unescape(card["name"]),
            "permalink": card["permalink"],
            "categories": sorted(
                category["name"] for category in card["categories"]
            ),
            "description_text": clean_html(card["description"]),
            "price_minor_units": card["prices"]["price"],
            "currency_code": card["prices"]["currency_code"],
            "currency_minor_unit": card["prices"]["currency_minor_unit"],
            "is_in_stock": card["is_in_stock"],
            "is_purchasable": card["is_purchasable"],
        }
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"AKINAWA-RW-{index:03d}",
            "source_product_id": source["card_id"],
            "source_url": card["permalink"],
            "listing_url": LANDING_URL,
            "source_card_facts_sha256": hashlib.sha256(
                json.dumps(card_facts, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Rwanda",
            "manufacturer": "",
            "manufacturer_status": "not_published_by_current_distributor_catalog",
            "distributor": "Leadway Distribution",
            "brand": "AKINAWA",
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "lifecycle_status": "current_exclusive_distributor_catalog",
            "evidence_status": "current_exclusive_country_distributor_complete_store_api",
            "specifications": source["specifications"] | {
                "source_category": card_facts["categories"],
                "source_price_minor_units": card_facts["price_minor_units"],
                "source_currency_code": card_facts["currency_code"],
                "source_currency_minor_unit": card_facts["currency_minor_unit"],
                "source_is_in_stock": card_facts["is_in_stock"],
                "source_is_purchasable": card_facts["is_purchasable"],
                "source_quality_flags": sorted(set(
                    source["specifications"].get("source_quality_flags", [])
                    + [
                        "zero_price_and_not_purchasable_no_offer_created",
                        "marketing_description_not_redistributed",
                    ]
                )),
            },
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    quality_flags = Counter(
        flag for row in records
        for flag in row["specifications"]["source_quality_flags"]
        if flag not in {
            "zero_price_and_not_purchasable_no_offer_created",
            "marketing_description_not_redistributed",
        }
    )
    unambiguous_source_spec_rows = sum(
        bool(
            row["specifications"].get("nlgi")
            or row["specifications"].get("cvt_specifications")
            or row["specifications"].get("atf_specifications")
            or (
                row["specifications"].get("sae_gear")
                and row["specifications"].get("api_gl")
            )
        )
        for row in records
    )
    report = {
        "schema_version": 1,
        "status": "current_exclusive_distributor_complete_catalog_conflicts_explicit",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "api_cards": len(source_rows),
        "product_identities": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "unambiguous_source_spec_rows": unambiguous_source_spec_rows,
        "expected_current_classifier_professional_key_complete_rows": 3,
        "conflict_limited_rows": len(records) - unambiguous_source_spec_rows,
        "quality_flags": dict(sorted(quality_flags.items())),
        "cards_source_reported_in_stock": sum(
            row["specifications"]["source_is_in_stock"] is True
            for row in records
        ),
        "cards_source_reported_purchasable": sum(
            row["specifications"]["source_is_purchasable"] is True
            for row in records
        ),
        "source_reported_price_minor_units": dict(sorted(Counter(
            row["specifications"]["source_price_minor_units"]
            for row in records
        ).items())),
        "api_normalized_card_names_sha256": hashlib.sha256(
            (
                "\n".join(sorted(html.unescape(row["name"]) for row in source_rows))
                + "\n"
            ).encode()
        ).hexdigest(),
        "landing_product_names_sha256": hashlib.sha256(
            (
                "\n".join(sorted(row["product_name"] for row in records))
                + "\n"
            ).encode()
        ).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "denominator_note": "All ten cards in the public Leadway Store API are included.",
        "offer_note": "All cards report zero price and are not purchasable; stock badges remain source evidence and no offers are created.",
        "conflict_note": "Only fields agreed by title and body enter strict professional keys. Conflicting API/JASO/TC-W3 and product-line statements remain source-reported.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
