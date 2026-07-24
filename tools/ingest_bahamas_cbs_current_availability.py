#!/usr/bin/env python3
"""Build the evidence-only current CBS Bahamas lubricant availability layer.

CBS returns HTTP 455 to command-line clients. The rows below are therefore
transcribed from the official category pages as rendered through a normal
browser and from the search-engine snapshot of those same official pages.
No access control is bypassed and no unavailable page/image hashes are
invented.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/bahamas-cbs-current-availability.jsonl"
REPORT = ROOT / "data/bahamas-cbs-current-catalog-report.json"
SNAPSHOT_DATE = "2026-07-24"
SOURCE_ID = "BAHAMAS_CBS_CURRENT_AVAILABILITY"

MOTOR_URL = "https://www.cbsbahamas.com/motor-oils--4"
GREASE_URL = "https://www.cbsbahamas.com/grease-and-lubricants--4"
FLUIDS_URL = "https://www.cbsbahamas.com/other-fluids-treatments-and-chemicals--4"


def p(brand: str, ref: str, sku: str, name: str, family: str, category: str,
      url: str, surface: str = "browser_rendered_official_category") -> dict:
    return {
        "brand": brand,
        "manufacturer_ref": ref,
        "item_sku": sku,
        "product_name": name,
        "family_code": family,
        "source_category": category,
        "source_card_url": url,
        "observation_surface": surface,
    }


PRODUCTS = [
    # The live official Motor Oils page reports 16 items.
    p("ITASCA", "702273", "9163528", "ITASCA Lawnmower & Utility 4-Cycle SAE 10W-30 Motor Oil, 1 Qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("PENNZOIL", "550035002", "0552869", "Pennzoil SAE 5W-20 Motor Oil, 1 Qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("ITASCA", "702275", "1868157", "ITASCA 702275 Outdoors 2-Cycle Engine Oil, 8 oz", "M", "Motor Oils", MOTOR_URL),
    p("COASTAL", "19301", "3651429", "Coastal SAE 30 Motor Oil, 1 Qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("VALVOLINE", "822344", "4001202", "Valvoline Daily Protection SAE 20W-50 Synthetic Blend Motor Oil, 1 Qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("BRIGGS & STRATTON", "100028", "4843967", "Briggs & Stratton Premium 4-Cycle SAE 30 Small Engine Oil, 18 oz Bottle", "M", "Motor Oils", MOTOR_URL),
    p("PENNZOIL", "550035261", "6224224", "Pennzoil Premium Outboard & Multi-Purpose 2-Cycle Engine Oil, 1 Qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("MARVEL MYSTERY OIL", "MM13", "6272371", "Marvel Mystery Oil Enhancer & Fuel Treatment, 32 oz Bottle", "U", "Motor Oils", MOTOR_URL),
    p("PENNZOIL", "550034991", "9223777", "Pennzoil SAE 30 Motor Oil, 1 Qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("PENNZOIL", "550035160", "9223900", "Pennzoil SAE 10W-40 Motor Oil, 1 Qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("SHELL", "550045144", "9224080", "Shell Rotella T4 Triple Protection 10W-30 Diesel Engine Oil, 1 Gal Bottle", "M", "Motor Oils", MOTOR_URL),
    p("PENNZOIL", "550035091/3609", "6208078", "Pennzoil Motor Oil, 5W-30, 1 qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("PENNZOIL", "550022757/5073655", "6209985", "Pennzoil TC-W3 Marine Premium Plus 2-Cycle Engine Oil, 1 gal", "M", "Motor Oils", MOTOR_URL),
    p("PENNZOIL", "550035052/3619", "9223793", "Pennzoil Motor Oil, 10W-30, 1 qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("CASTROL", "C178QW", "C178QW", "Castrol CRB Monograde SAE 40 Diesel Engine Oil, 1 Qt Bottle", "M", "Motor Oils", MOTOR_URL),
    p("QUAKER STATE", "12480", "9224320", "Quaker State Universal 2-Cycle Engine Oil, 8 oz Bottle", "M", "Motor Oils", MOTOR_URL),

    # Official Grease & Lubricants page. One grease gun is excluded as equipment.
    p("B’LASTER", "16-PB-DS", "7389091", "B’laster PB Powerful Penetrating Catalyst With ProStraw, 11 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("TRI-FLOW", "20005TF", "6475339", "Tri-Flow Superior Lubricant, 6 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("3-IN-ONE", "10038", "6368526", "3-IN-ONE Multi-Purpose Oil, 8 oz", "S", "Grease & Lubricants", GREASE_URL),
    p("PRIME GUARD", "GL14", "6798557", "Prime Guard Lithium Grease, 14 oz", "G", "Grease & Lubricants", GREASE_URL),
    p("FLUID FILM", "00207", "9573056", "FLUID FILM Rust & Corrosion Protection, Penetrant, & Lubricant, 11.75 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("LIQUID WRENCH", "L212", "6911101", "LIQUID WRENCH Lubricating Oil, 11 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("CRC", "05037", "6822050", "CRC White Lithium Grease, 10 oz Aerosol Can", "G", "Grease & Lubricants", GREASE_URL),
    p("WD-40", "300615", "6466007", "WD-40 Specialist White Lithium Grease Spray, 10 oz Aerosol Can", "G", "Grease & Lubricants", GREASE_URL),
    p("LUBRIMATIC", "11315", "6366702", "LubriMatic Multi-Purpose Lithium Grease, 14 oz Cartridge", "G", "Grease & Lubricants", GREASE_URL),
    p("WD-40", "490194", "5172697", "WD-40 Multi-Purpose Lubricant Spray With EZ-REACH Flexible Straw, 14.4 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("LIQUID WRENCH", "L711", "4291274", "LIQUID WRENCH Chain & Cable Lube, 11 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("LIQUID WRENCH", "L112", "2982395", "LIQUID WRENCH Penetrating Oil, 11 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("WD-40", "490057", "2076115", "WD-40 Multi-Purpose Lubricant Spray With Smart Straw, 12 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("STA-LUBE", "SL3144", "0716969", "Sta-Lube Moly-Graph Extreme Pressure Multi-Purpose Grease, 3 oz (3-Pack)", "G", "Grease & Lubricants", GREASE_URL),
    p("KEL", "57300", "6396170", "KEL Black Oil, 11.25 oz Aerosol Can", "S", "Grease & Lubricants", GREASE_URL),
    p("DANCO", "80360", "0522391", "Danco 80360 Waterproof Grease, 1/2 oz Tube", "G", "Grease & Lubricants", GREASE_URL),
    # Present in the recent official-page search snapshot while L112 appears in
    # the live browser render; retained as a transparent temporal union.
    p("MARVEL MYSTERY OIL", "MM12R", "6332928", "Marvel Mystery Oil MM12R Lubricant Oil, 16 oz Bottle", "S", "Grease & Lubricants", GREASE_URL, "recent_search_snapshot_of_official_category"),

    # 23-item Other Fluids page: 17 are in scope, but MM13 duplicates Motor Oils.
    p("GUNK", "M206", "6159339", "GUNK Belt Conditioner, 6 oz Aerosol Can", "U", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("HERRERO & SONS (HS)", "29.401", "29.401", "HS Engine Coolant Maximum Protection, 1 Gal Bottle", "C", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("GUMOUT", "5072866", "3422664", "Gumout 5072866 Starting Fluid, 11 oz Aerosol Can", "U", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("MOTOR MEDIC", "M3815", "9857285", "Motor Medic Thrust Starting Fluid, 11 oz Aerosol Can", "U", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("PENNZOIL", "550042065", "9223983", "Pennzoil Automatic Transmission Fluid, 32 oz Bottle", "TF", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("PRESTONE", "AF2100", "8559908", "Prestone 50/50 Prediluted Antifreeze/Coolant, 1 Gal Bottle", "C", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("PRESTONE", "AS-401", "6840029", "Prestone DOT 3 Synthetic Brake Fluid, 32 oz Bottle", "H", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("PRESTONE", "AS260", "6839948", "Prestone Power Steering Fluid, 12 oz Bottle", "H", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("SEA FOAM", "SF16", "2689792", "Sea Foam Motor Treatment, 16 oz Bottle", "U", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("SHELL", "9406706021", "1856210", "ShellZone Pre-Diluted 50/50 Antifreeze/Engine Coolant, 1 Gal Bottle", "C", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("MOTOR MEDIC", "M2713", "6560072", "Motor Medic Universal Power Steering Fluid With Stop Leak, 12 oz Bottle", "H", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("STP", "78380", "7137649", "STP Diesel Fuel Injector Treatment, 20 oz Bottle", "U", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("STP", "65148", "6315790", "STP Oil Treatment, 15 oz Bottle", "U", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("MOTOR MEDIC", "M3911", "9143819", "Motor Medic Liquid Fire Quick Starting Fluid, 7.2 oz Aerosol Can", "U", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("PENNZOIL", "550049545", "9223918", "Pennzoil ATF Type F Automatic Transmission Fluid, 1 Qt Bottle", "TF", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),
    p("RSC", "M3616", "6336440", "RSC M3616 Transmission Treatment, 12 oz Bottle", "TF", "Other Fluids, Treatments, & Chemicals", FLUIDS_URL),

    # Relevant cards found outside the three automotive-fluid child categories.
    p("CAMCO USA", "92006", "9381179", "Camco USA Xtreme Blue 92006 Windshield Washer Fluid, 1 gal", "U", "Auto Solvents & Cleaners", "https://www.cbsbahamas.com/prime-guard-xtreme-blue-92006-windshield-washer-fluid-1-gal--4"),
    p("GARDNER BENDER", "79-006N", "6748461", "Gardner Bender 79-006N Wire-Aide Wire-Pulling Lubricant, 1 Qt Bottle", "S", "Electrical Grease & Lubricants", "https://www.cbsbahamas.com/gardner-bender-79-006n-wire-aide-wire-pulling-lubricant-1-qt-bottle--1"),
]

EXCLUSIONS = [
    ("6366264", "LubriMatic 30-132 Mini Grease Gun Kit", "equipment"),
    ("6786107", "LubriMatic 30-200 Grease Gun", "equipment"),
    ("2258630", "GUNK Carburetor Parts Cleaner", "cleaner"),
    ("6711816", "CRC QD Contact Cleaner", "cleaner"),
    ("9490277", "GUNK Battery Terminal Cleaner & Protector", "cleaner"),
    ("5959739", "GUNK Battery Terminal Cleaner", "cleaner"),
    ("6290258", "Gumout Jet Spray Carb/Choke & Parts Cleaner", "cleaner"),
]


def technical(name: str) -> dict:
    upper = name.upper()
    sae = re.findall(r"(?<![A-Z0-9])(?:0W|5W|10W|15W|20W)-?(?:20|30|40|50)(?![A-Z0-9])|(?<![A-Z0-9])SAE\s+(?:30|40)(?![A-Z0-9])", upper)
    sae = [value.replace("SAE ", "") for value in sae]
    return {
        "sae_engine": sae[0] if sae else "",
        "sae_gear": "",
        "iso_vg": "",
        "nlgi": "2" if "EP NO 2" in upper else "",
        "api": ["SA"] if "COASTAL SAE 30" in upper else [],
        "api_gl": [],
        "acea": [],
        "ilsac": [],
        "jaso": [],
        "dot": "DOT 3" if "DOT 3" in upper else "",
        "coolant_class": "50/50 premix" if "50/50" in upper else "",
        "performance": (
            ["TC-W3"] if "TC-W3" in upper else []
        ),
    }


def main() -> None:
    assert len(PRODUCTS) == 51
    assert len({row["item_sku"] for row in PRODUCTS}) == 51
    assert Counter(row["source_category"] for row in PRODUCTS) == {
        "Motor Oils": 16,
        "Grease & Lubricants": 17,
        "Other Fluids, Treatments, & Chemicals": 16,
        "Auto Solvents & Cleaners": 1,
        "Electrical Grease & Lubricants": 1,
    }
    rows = []
    for index, source in enumerate(PRODUCTS, 1):
        row = {
            **source,
            "source_id": SOURCE_ID,
            "source_record_id": f"CBS-BS-{index:03d}",
            "source_url": "https://www.cbsbahamas.com/",
            "seller": "Commonwealth Building Supplies Ltd.",
            "market": "Bahamas",
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "observed_on_current_official_retailer_catalog",
            "scope_status": "bahamas_retail_availability_evidence",
            "technical": technical(source["product_name"]),
            "source_quality_flags": [
                "official_retailer_availability_not_manufacturer_master",
                "browser_observed_because_command_line_access_returns_http_455",
                "no_access_control_bypass",
                "no_page_or_image_hash_claimed",
                "technical_values_limited_to_explicit_card_text",
            ],
        }
        if source["observation_surface"].startswith("recent_search"):
            row["source_quality_flags"].append(
                "temporal_union_live_category_and_recent_official_page_snapshot"
            )
        rows.append(row)
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )
    OUT.write_text(payload, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": "https://www.cbsbahamas.com/",
        "snapshot_date": SNAPSHOT_DATE,
        "access_observation": "Direct command-line requests returned HTTP 455; official pages were observed through browser rendering and a recent search snapshot without bypassing access controls.",
        "official_category_reported_counts": {
            "Motor Oils": 16,
            "Grease & Lubricants": 17,
            "Other Fluids, Treatments, & Chemicals": 23,
        },
        "in_scope_unique_availability_cards": len(rows),
        "in_scope_by_category": dict(sorted(Counter(
            row["source_category"] for row in rows
        ).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "excluded_cards": [
            {"item_sku": sku, "product_name": name, "reason": reason}
            for sku, name, reason in EXCLUSIONS
        ],
        "duplicate_category_occurrences_collapsed": [
            {
                "item_sku": "6272371",
                "product_name": "Marvel Mystery Oil Enhancer & Fuel Treatment, 32 oz Bottle",
                "categories": ["Motor Oils", "Other Fluids, Treatments, & Chemicals"],
            }
        ],
        "temporal_category_union": {
            "reported_category_count": 17,
            "live_browser_only_card": "LIQUID WRENCH L112",
            "recent_official_page_snapshot_only_card": "Marvel Mystery Oil MM12R",
            "union_in_scope_cards_after_equipment_exclusion": 17,
        },
        "normalized_output_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "quality_note": "Evidence-only Bahamas retailer availability layer. It creates no manufacturer master identities until strict brand/ref/spec matching is completed.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "rows": len(rows),
        "sha256": report["normalized_output_sha256"],
    }))


if __name__ == "__main__":
    main()
