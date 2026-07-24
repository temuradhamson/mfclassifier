#!/usr/bin/env python3
"""Normalize the complete current MTCC Maldives Castrol listing.

MTCC's public robots policy permits reference use and prohibits AI training,
but Cloudflare returns 403 to direct automated page/API retrieval from this
research environment. The official listing is nevertheless exposed in current
search indexes with an explicit denominator of 15 and an official page that
shows all 15 names. We retain only those factual identities and grades that are
part of the product names. Detail prose is excluded because at least one live
card (High Temperature Grease) is visibly populated with Transmax ATF prose.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "maldives-mtcc-current-castrol-products.jsonl"
REPORT = ROOT / "data" / "maldives-mtcc-current-castrol-report.json"
SOURCE_ID = "MALDIVES_MTCC_COMPLETE_CURRENT_CASTROL_LISTING"
SNAPSHOT_DATE = "2026-07-24"
ROBOTS_URL = "https://mtcc.mv/robots.txt"
PRODUCTS_URL = "https://mtcc.mv/castrol-lubricants/"
CATEGORY_URL = "https://mtcc.mv/brand/castrol-lubricants/"
CASTROL_DISTRIBUTOR_URL = (
    "https://www.castrol.com/en/global/corporate/about-castrol/distributors.html"
)


def item(name: str, family: str, **technical: object) -> dict:
    return {"product_name": name, "family_code": family, "technical": technical}


# Snapshot audited against the current official listing. The category index
# explicitly reports "Showing 1–12 of 15 results"; the official Castrol landing
# page exposes all names below.
PRODUCTS = [
    item("Castrol Aircol 299", "C"),
    item("Castrol Aircol SN 100", "C", iso_vg="100"),
    item("Castrol Alpha SP 220", "I", iso_vg="220"),
    item("Castrol High Temperature Grease", "G"),
    item("Castrol Hyspin AWH-M 15", "H", iso_vg="15"),
    item("Castrol Hyspin AWH-M 32", "H", iso_vg="32"),
    item("Castrol Hyspin AWH-M 46", "H", iso_vg="46"),
    item("Castrol Hyspin AWH-M 68", "H", iso_vg="68"),
    item("Castrol MHP 1-40", "M", source_variant="1-40"),
    item("Castrol Radicool", "TF"),
    item("Castrol Transmax", "T"),
    item("Castrol Spheerol EPL 2", "G", source_variant="2"),
    item("Castrol Spheerol SX 2", "G", source_variant="2"),
    item("Castrol Vecton 15W-40", "M", sae_engine="15W-40"),
    item("Castrol TLX", "M"),
]


def fetch_robots() -> bytes:
    request = urllib.request.Request(
        ROBOTS_URL,
        headers={"User-Agent": "mfclassifier-source-review/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> None:
    robots = fetch_robots()
    robots_text = robots.decode("utf-8-sig")
    required = [
        "Content-Signal: search=yes,ai-train=no,use=reference",
        "User-agent: *",
        "Allow: /",
        "User-agent: GPTBot",
        "Disallow: /",
    ]
    if not all(value in robots_text for value in required):
        raise RuntimeError("MTCC robots/content-signal policy changed")

    rows = []
    for index, source in enumerate(PRODUCTS, 1):
        technical = {
            "sae_engine": source["technical"].get("sae_engine", ""),
            "sae_gear": "",
            "iso_vg": source["technical"].get("iso_vg", ""),
            "nlgi": "",
            "api": [],
            "api_gl": [],
            "acea": [],
            "ilsac": [],
            "jaso": [],
        }
        if "source_variant" in source["technical"]:
            technical["source_variant"] = source["technical"]["source_variant"]
        facts = {
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "technical": technical,
            "market": "Maldives",
            "brand": "Castrol",
        }
        rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"MTCC-MV-{index:03d}",
            "source_url": PRODUCTS_URL,
            "source_category_url": CATEGORY_URL,
            "official_brand_distributor_url": CASTROL_DISTRIBUTOR_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Maldives",
            "manufacturer": "Castrol",
            "brand": "Castrol",
            "local_distributor": "Maldives Transport & Contracting Company Plc",
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "lifecycle_status": "listed_on_current_official_country_catalog",
            "evidence_status": (
                "official_country_distributor_complete_current_indexed_listing"
            ),
            "technical": technical,
            "source_facts_sha256": hashlib.sha256(
                json.dumps(
                    facts,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            "source_quality_flags": [
                "direct_page_and_wordpress_api_cloudflare_403_from_research_environment",
                "current_official_search_index_snapshot_requires_periodic_manual_denominator_review",
                "detail_prose_excluded_due_observed_high_temperature_grease_card_containing_transmax_atf_prose",
                *(
                    ["numeric_product_name_variant_not_promoted_to_strict_grade"]
                    if "source_variant" in technical else []
                ),
            ],
        })

    if len(rows) != 15 or len({
        row["product_name"].casefold() for row in rows
    }) != 15:
        raise RuntimeError("MTCC Castrol denominator/identity set changed")
    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "complete_current_official_indexed_listing_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "owner": "Maldives Transport & Contracting Company Plc",
        "market": "Maldives",
        "products_url": PRODUCTS_URL,
        "category_url": CATEGORY_URL,
        "robots_url": ROBOTS_URL,
        "official_brand_distributor_url": CASTROL_DISTRIBUTOR_URL,
        "robots_sha256": hashlib.sha256(robots).hexdigest(),
        "robots_content_signal": {
            "search": "yes",
            "ai_train": "no",
            "use": "reference",
        },
        "category_reported_total_results": 15,
        "category_reported_first_page_range": "1–12",
        "normalized_product_rows": len(rows),
        "families": dict(sorted(Counter(
            row["family_code"] for row in rows
        ).items())),
        "rows_with_sae": sum(
            bool(row["technical"]["sae_engine"]) for row in rows
        ),
        "rows_with_iso_vg": sum(
            bool(row["technical"]["iso_vg"]) for row in rows
        ),
        "rows_with_strict_nlgi": 0,
        "offers_created": 0,
        "normalized_output_sha256": hashlib.sha256(
            output_text.encode()
        ).hexdigest(),
        "access_note": (
            "Cloudflare returns HTTP 403 to direct page/API retrieval from the "
            "research environment. The current official pages remain visible "
            "through search indexes; this snapshot is therefore explicitly "
            "versioned and requires periodic manual denominator review."
        ),
        "quality_note": (
            "The live High Temperature Grease detail result contains Transmax "
            "ATF prose. No MTCC detail prose, claimed standards, temperatures "
            "or description-derived grades are imported."
        ),
        "grain_note": (
            "One row per one of the 15 explicitly listed current product names. "
            "Only SAE/ISO VG tokens intrinsic to a name are promoted to strict "
            "technical keys; other numerals remain source variants."
        ),
        "publication_scope": (
            "Reference-use factual product identities, explicit name grades, "
            "market/distributor attribution, URLs and hashes only; no prose, "
            "images, contacts, page layout or training use."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
