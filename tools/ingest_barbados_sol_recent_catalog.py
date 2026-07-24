#!/usr/bin/env python3
"""Normalize the official Sol Barbados Mobil ecommerce catalog.

The storefront is intermittently available to browser clients while direct
command-line requests currently return 404 for several category routes.
This is therefore an attributed browser-observed availability layer. Package
cards are collapsed only when the Mobil product identity is explicit.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/barbados-sol-recent-availability.jsonl"
REPORT = ROOT / "data/barbados-sol-recent-catalog-report.json"
SOURCE_ID = "BARBADOS_SOL_RECENT_ECOMMERCE_CATALOG"
SNAPSHOT_DATE = "2026-07-24"
BASE = "https://barbados.solpetroleum.com"


def row(name: str, family: str, category: str, cards: list[tuple[str, str]],
        statuses: list[str], technical: dict | None = None) -> dict:
    return {
        "brand": "MOBIL",
        "product_name": name,
        "family_code": family,
        "source_category": category,
        "source_category_url": f"{BASE}/{category}",
        "listing_cards": [
            {"source_card_title": title, "product_code": code}
            for title, code in cards
        ],
        "source_statuses_observed": statuses,
        "technical": {
            "sae_engine": "",
            "sae_gear": "",
            "iso_vg": "",
            "nlgi": "",
            "api": [],
            "api_gl": [],
            "acea": [],
            "ilsac": [],
            "oem_or_industry": [],
            **(technical or {}),
        },
    }


PRODUCTS = [
    # Gasoline engine oils: 10 listing cards collapse to eight identities.
    row("Mobil 1 10W-30", "M", "gasoline-engine-oils",
        [("M-110W-30CASE 6x1 QT CARTON (207)", "M-110W-30CASE207")],
        ["in_stock"], {"sae_engine": "10W-30"}),
    row("Mobil Special 10W-30", "M", "gasoline-engine-oils", [
        ("M-SPECIAL10W-30CASE 6x1 QT CARTON (207)", "M-SPECIAL10W-30CASE207"),
        ("M-SPECIAL10W-30DRUM 55 AG DRUM (241)", "M-SPECIAL10W-30DRUM241"),
    ], ["in_stock", "not_available"], {
        "sae_engine": "10W-30", "api": ["SN", "SM", "SL", "SJ"],
        "ilsac": ["GF-5"], "oem_or_industry": ["GM 6094M"],
    }),
    row("Mobil Special 10W-40", "M", "gasoline-engine-oils",
        [("M-SPECIAL10W-40CASE 6x1 QT CARTON (207)", "M-SPECIAL10W-40CASE207_Group")],
        ["configurable"], {"sae_engine": "10W-40"}),
    row("M-SPECIAL10W40 SYNTH", "M", "gasoline-engine-oils",
        [("M-SPECIAL10W40 SYNTH DRUM 55 AG DRUM (241)", "M-SPECIAL10W40SYNDRUM241")],
        ["not_available"], {"sae_engine": "10W-40"}),
    row("Mobil Special 20W-50", "M", "gasoline-engine-oils",
        [("M-SPECIAL20W-50CASE 6x1 QT CARTON (207)", "M-SPECIAL20W-50CASE207_Group")],
        ["configurable", "in_stock"], {
            "sae_engine": "20W-50", "api": ["SN", "SM", "SL", "SJ"],
        }),
    row("Mobil Super 10W-30", "M", "gasoline-engine-oils",
        [("M-SUPER10W-30CASE 3 X 5 QT (304)", "M-SUPER10W-30CASE304")],
        ["in_stock"], {"sae_engine": "10W-30"}),
    row("Mobil Super 10W-40", "M", "gasoline-engine-oils",
        [("M-SUPER10W-40CASE 3 X 5 QT (304)", "M-SUPER10W-40CASE304")],
        ["in_stock"], {"sae_engine": "10W-40"}),
    row("Mobil 1 5W-30", "M", "gasoline-engine-oils", [
        ("M15W-30CASE 6x1 QT CARTON (207)", "M15W-30CASE207"),
        ("M15W-30STDRUM 55 AG DRUM (241)", "M15W-30STDRUM241"),
    ], ["in_stock", "not_available"], {"sae_engine": "5W-30"}),

    # Diesel and marine engine oils.
    row("Mobil 1 Turbo Diesel Truck 5W-40", "M", "diesel-engine-oils",
        [("M-1TDTRUCK5W40CASE 6x1 QT CARTON (207)", "M-1TDTRUCK5W40CASE207")],
        ["in_stock", "not_available"], {
            "sae_engine": "5W-40",
            "api": ["CK-4", "CJ-4", "CI-4 PLUS", "CI-4", "CH-4", "CG-4", "SN", "SM", "SL"],
            "acea": ["E7", "E9"], "oem_or_industry": ["Caterpillar ECF-3"],
        }),
    row("Mobilgard 412", "M", "diesel-engine-oils",
        [("M-GARD412DRUM 55 AG DRUM (241)", "M-GARD412STDRUM241")],
        ["in_stock"]),
    row("Mobilgard M440", "M", "diesel-engine-oils",
        [("M-GARDM440DRUM 55 AG DRUM (241)", "M-GARDM440DRUM241")],
        ["in_stock"]),
    row("Mobil Delvac 1240", "M", "diesel-engine-oils",
        [("Mobil Delvac 1240", "M-DELVAC1240CASE207_Group")],
        ["configurable", "in_stock"], {
            "sae_engine": "40", "api": ["CF-2", "CF", "SF"],
        }),
    row("Mobil Delvac 1250", "M", "diesel-engine-oils",
        [("Mobil Delvac 1250", "M-DELVAC1250CASE207_Group")],
        ["configurable"], {"sae_engine": "50"}),
    row("Mobil Delvac MX F2 15W-40", "M", "diesel-engine-oils",
        [("Mobil Delvac MX F2", "M-DELVACMXF215W-40CASE207_Group")],
        ["configurable"], {
            "sae_engine": "15W-40", "api": ["CI-4 PLUS"],
        }),

    # Automotive and industrial gear oils.
    row("Mobilgear 600 XP 220", "I", "gear-oils",
        [("M-GEAR600XP220PAIL 38LB PAIL 5 AG(721)", "M-GEAR600XP220PAIL721_Group")],
        ["configurable"], {"iso_vg": "220"}),
    row("Mobilgear 600 XP 320", "I", "gear-oils",
        [("M-GEAR600XP320PAIL 38LB PAIL 5 AG(721)", "M-GEAR600XP320PAIL721_Group")],
        ["configurable"], {"iso_vg": "320"}),
    row("Mobilgear 600 XP 680", "I", "gear-oils",
        [("M-GEAR600XP680DRUM 400LB DRUM 53 AG(711)", "M-GEAR600XP680DRUM711")],
        ["in_stock"], {"iso_vg": "680"}),
    row("Mobilube HD 80W-90", "T", "gear-oils",
        [("M-LUBEHD+80W90CASE 12x1 QT CARTON (205)", "M-LUBEHD+80W90CASE205_Group")],
        ["configurable", "in_stock"], {"sae_gear": "80W-90", "api_gl": ["GL-5"]}),
    row("Mobilube HD 85W-140", "T", "gear-oils",
        [("M-LUBEHD+85W140CASE 12x1 QT CARTON (205)", "M-LUBEHD+85W140CASE205")],
        ["in_stock"], {"sae_gear": "85W-140", "api_gl": ["GL-5"]}),
    row("Mobil 1 Syn Gear Lube LS 75W-90", "T", "gear-oils",
        [("M1SYNGLLS75W-90CASE 12x1 QT CARTON (205)", "M1SYNGLLS75W-90CASE205")],
        ["in_stock"], {"sae_gear": "75W-90", "api_gl": ["GL-5"]}),

    # Greases.
    row("Mobilgrease XHP 222", "G", "greases",
        [("M-GREASEXHP222PAIL 16 KG PAIL (323)", "M-GREASEXHP222PAIL323_Group")],
        ["configurable", "in_stock"], {
            "nlgi": "2", "oem_or_industry": ["DIN 51825 KP 2 N-20", "Fives Cincinnati P-64"],
        }),
    row("Mobilgrease XHP 223", "G", "greases",
        [("M-GREASEXHP223PAIL 18 KG PAIL (328)", "M-GREASEXHP223PAIL328")],
        ["not_available"], {"nlgi": "3"}),

    # Industrial oils.
    row("Mobil Rarus 427", "C", "air-compressor-oils",
        [("M-RARUS427STDRUM 55 AG DRUM (241)", "M-RARUS427STDRUM241")],
        ["in_stock"], {
            "iso_vg": "100", "oem_or_industry": ["DIN 51506 VDL"],
        }),
    row("Mobil SHC Rarus 46", "C", "air-compressor-oils",
        [("M-SHCRARUS46PAIL 5 AG PAIL (221)", "M-SHCRARUS46PAIL221")],
        ["not_available"], {"iso_vg": "46"}),
    row("Mobil DTE Oil Heavy Medium", "I", "circulating-oils",
        [("M-DTEHVYMEDPAIL 5 AG PAIL (221)", "M-DTEHVYMEDPAIL221_Group")],
        ["configurable", "in_stock"], {
            "oem_or_industry": ["DIN 51515-1", "JIS K-2213 Type 2"],
        }),
    row("Mobil DTE Oil BB", "I", "circulating-oils",
        [("M-DTEOILBBDRUM 55 AG DRUM (241)", "M-DTEOILBBDRUM241")],
        ["in_stock"]),
    row("Mobil DTE hydraulic oil group", "H", "hydraulic-oils",
        [("Mobil DTE", "M-DTE24PAIL221_Group")],
        ["configurable"]),
    row("Nuto H 46", "H", "hydraulic-oils",
        [("NUTOH46PAIL 5 AG PAIL (221)", "NUTOH46PAIL221_Group")],
        ["configurable", "in_stock"], {
            "iso_vg": "46",
            "oem_or_industry": ["Denison HF-0", "DIN 51524-2", "ISO L-HM"],
        }),
    row("Nuto H 68", "H", "hydraulic-oils",
        [("NUTOH68PAIL 5 AG PAIL (221)", "NUTOH68PAIL221_Group")],
        ["configurable"], {"iso_vg": "68"}),

    # Transmission oils: two ATF D/M package cards collapse to one identity.
    row("Mobil Automatic Transmission Fluid D/M", "T", "transmission-oils", [
        ("M-ATFD / MPAIL 5 AG PAIL (221)", "M-ATFD/MPAIL221"),
        ("Mobil Automatic Transmission Fluid D / M", "M-ATFD/MCASE207"),
    ], ["in_stock"]),
    row("Mobil Dexron-VI ATF", "T", "transmission-oils",
        [("M-DEXRONVIATFCASE 6x1 QT CARTON (207)", "M-DEXRONVIATFCASE207")],
        ["in_stock"]),
    row("Mobiltrans HD 10W", "T", "transmission-oils",
        [("M-TRANSHD10WDRUM 55 AG DRUM (241)", "M-TRANSHD10WDRUM241")],
        ["in_stock"], {"sae_engine": "10W"}),

    # Listed in the official all-products search while its category route is
    # intermittently unavailable.
    row("Mobil Jet Oil 254", "U", "turbine-oils",
        [("M-JET254STDRUM 55 AG DRUM (241)", "M-JET254STDRUM241")],
        ["in_stock", "not_available"], {
            "oem_or_industry": ["MIL-PRF-23699-HTS", "PRI-QPL-AS5780/HPC"],
        }),
]


def main() -> None:
    assert len(PRODUCTS) == 33
    assert sum(len(item["listing_cards"]) for item in PRODUCTS) == 36
    assert len({
        card["product_code"]
        for item in PRODUCTS
        for card in item["listing_cards"]
    }) == 36
    rows = []
    for index, item in enumerate(PRODUCTS, 1):
        rows.append({
            **item,
            "source_id": SOURCE_ID,
            "source_record_id": f"SOL-BB-{index:03d}",
            "source_url": BASE + "/products-search",
            "seller": "Sol Barbados Ltd.",
            "market": "Barbados",
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_recent_official_ecommerce_catalog",
            "scope_status": "global_mobil_identity_barbados_availability",
            "source_quality_flags": [
                "official_country_ecommerce_availability_not_manufacturer_master",
                "package_only_cards_collapsed_when_product_identity_explicit",
                "intermittent_browser_access_and_command_line_404_recorded",
                "conflicting_availability_statuses_preserved",
                "no_page_or_image_hash_claimed",
                "source_reported_specifications_not_independent_approvals",
            ],
        })
    payload = "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
        for item in rows
    )
    OUT.write_text(payload, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": BASE,
        "snapshot_date": SNAPSHOT_DATE,
        "normalized_product_identities": len(rows),
        "listing_card_occurrences": sum(
            len(item["listing_cards"]) for item in rows
        ),
        "package_only_occurrences_collapsed": 3,
        "identities_by_category": dict(sorted(Counter(
            item["source_category"] for item in rows
        ).items())),
        "families": dict(sorted(Counter(
            item["family_code"] for item in rows
        ).items())),
        "identities_with_conflicting_status_observations": sum(
            {"in_stock", "not_available"}.issubset(
                set(item["source_statuses_observed"])
            )
            for item in rows
        ),
        "empty_or_intermittently_unavailable_category_routes": [
            "industrial-gear-oils",
            "outboard-motorcycle-oils",
            "turbine-oils",
        ],
        "normalized_output_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "quality_note": "Barbados availability evidence for global Mobil identities. No country-specific manufacturer master products are created before strict matching.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "identities": len(rows),
        "listing_cards": report["listing_card_occurrences"],
        "sha256": report["normalized_output_sha256"],
    }))


if __name__ == "__main__":
    main()
