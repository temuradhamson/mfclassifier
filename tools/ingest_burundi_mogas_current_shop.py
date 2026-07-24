#!/usr/bin/env python3
"""Normalize the complete MOGAS Burundi-section WooCommerce catalog.

The public Store API exposes 39 cards.  Three LPG cylinder cards are excluded;
the remaining 36 lubricant/fluid cards expand to 45 explicit grade identities.
The section URL/title says Burundi, while the footer says Uganda, and the API
reports implausible USD prices.  Those facts are retained as conflicted source
evidence and deliberately not converted into analytical offer prices.
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
OUT = ROOT / "data/burundi-mogas-current-products.jsonl"
REPORT = ROOT / "data/burundi-mogas-current-report.json"
SOURCE_ID = "BURUNDI_MOGAS_CURRENT_COMPLETE_SHOP_API"
API_URL = "https://mogasoil.com/burundi/wp-json/wc/store/v1/products?per_page=100"
SHOP_URL = "https://mogasoil.com/burundi/shop/"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"
EXCLUDED_IDS = {75, 76, 77}


def fetch_json(url: str) -> list[dict]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


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


def spec(**values: object) -> dict:
    return values


def variant(card_id: int, name: str, family: str, **specifications: object) -> dict:
    return {
        "card_id": card_id,
        "product_name": name,
        "family_code": family,
        "specifications": specifications,
    }


PRODUCTS = [
    variant(124, "MOGAS 2T Motor Oil", "M", engine_cycle="2T", jaso=["FB"], standards=["ISO-L-EGB"], base_oil="mineral"),
    variant(144, "MOGAS Agritrak SAE 20W-40 STOU", "T", sae_engine="20W-40", sae_gear="80W", api=["CF-4", "SF"], api_gl=["GL-4"], acea=["E2"], application="STOU engine, transmission, hydraulic and wet-brake fluid", standards=["MIL-L-2104D"], oem_specifications=["MB 227.1", "MB 228.1", "John Deere J27A", "John Deere JDM J27", "Ford M2C159-B", "Massey Ferguson CMS M1145", "Massey Ferguson CMS M1144", "Massey Ferguson CMS M1139", "Caterpillar TO-2", "Allison C4", "ZF TE-ML 07B", "Massey Ferguson MF 1135", "Ford M2C-143-D", "John Deere JDQ9E", "JI Case MS1120", "JI Case MS1210", "JI Case MS1207"]),
    variant(145, "MOGAS Agritrak UTTO SAE 80W", "T", sae_gear="80W", api_gl=["GL-4"], application="UTTO transmission, hydraulic and wet-brake fluid", oem_specifications=["Eaton Vickers 35VQ25", "Ford M2C41B", "Ford M2C48-B/C", "Ford M2C86-B/C", "Ford M2C134D", "Massey Ferguson M1129A", "Massey Ferguson M1127A/B", "Massey Ferguson M1110", "Massey Ferguson M1135", "Massey Ferguson M1141", "Massey Ferguson M1143", "Massey Ferguson M1145", "John Deere J14A/B/C", "John Deere J20C", "John Deere J20D", "John Deere J21A", "Allison C-3", "Allison C-4", "Caterpillar TO-2", "Denison HF-0/HF-1/HF-2", "Kubota UDT"]),
    variant(134, "MOGAS ATF II D", "T", atf_specifications=["GM Dexron IID"], color="red", oem_specifications=["Volvo 97335", "ZF TE-ML 05", "ZF TE-ML 09", "Caterpillar TO-2", "Allison C-4", "Denison"]),
    variant(165, "MOGAS Brake Fluid DOT 4", "TF", brake_fluid_class="DOT 4", standards=["FMVSS 116 DOT 4", "SAE J1704", "ISO 4925"], source_reported_compatibility=["DOT 3"]),
    variant(173, "MOGAS Cutting Oil", "I", product_form="chlorine-free soluble cutting oil", standards=["ISO-L-MAA"], source_reported_dilution="1:10 minimum to 1:40 maximum"),
    variant(95, "MOGAS Duramax Extra SAE 25W-50", "M", sae_engine="25W-50", api=["CF", "SF"]),
    variant(88, "MOGAS Duramax XHD SAE 15W-40", "M", sae_engine="15W-40", api=["CH-4", "SJ"], acea=["E7-12"], oem_specifications=["MB 228.3", "Volvo VDS-3", "Mack EO-N", "Mack EO-M Plus", "MAN M 3275", "Renault RLD-2", "Cummins CES 20076", "Cummins CES 20077", "Caterpillar ECF-1-a", "MTU Type 2", "Detroit Diesel DDC 93K215"]),
    variant(87, "MOGAS Duramax XL SYN SAE 10W-40", "M", sae_engine="10W-40", api=["CI-4"], acea=["E7"], base_oil="synthetic", standards=["Global DHD-1"], oem_specifications=["Mack EO-M Plus", "Cummins CES 20077", "Cummins CES 20078", "Caterpillar ECF-1", "Scania LDF-2", "Renault RLD-2", "MB-Approval 228.3", "Volvo VDS-3", "MAN M 3275", "MTU Type 2"]),
    variant(103, "MOGAS Frontia X SAE 20W-50", "M", sae_engine="20W-50", api=["SJ", "CF"]),
    variant(143, "MOGAS Hitrans TO-4", "T", api=["CF"], api_gl=["GL-3"], transmission_specifications=["Caterpillar TO-4", "Allison C4"], oem_specifications=["Komatsu KES 07.868.1", "ZF TE-ML 03"], source_quality_flags=["product_range_publishes_no_sae_grade"]),
    variant(161, "MOGAS Hydrax T 540", "H", hydraulic_class=["H-540"], standards=["NATO H-540", "TL-9150-35/5"], source_quality_flags=["product_page_publishes_no_iso_vg_grade"]),
    variant(160, "MOGAS Hydrax ZFR", "H", hydraulic_class=["HLP", "HM"], zinc_free=True, standards=["DIN 51524-2 HLP", "AFNOR NFE 48-603 HM", "ISO 11158 HM"], oem_specifications=["Denison HF-0", "Denison HF-1", "Denison HF-2", "Eaton Vickers M-2950-S", "Eaton Vickers I-286-S"], source_quality_flags=["product_page_publishes_no_iso_vg_grade"]),
    variant(164, "MOGAS Marina 2T", "M", engine_cycle="2T", marine_specifications=["NMMA TC-WII"], color="blue"),
    variant(162, "MOGAS Marina XHP 1240 SAE 40", "M", sae_engine="40", api=["CG-4"], acea=["E3"], marine_tbn_mg_koh_g=12, oem_specifications=["MTU Type II"]),
    variant(133, "MOGAS Power 2T Synthetic Motor Oil", "M", engine_cycle="2T", base_oil="synthetic", product_form="low-smoke scooter oil", source_quality_flags=["product_page_publishes_no_api_jaso_or_iso_performance_class"]),
    variant(176, "MOGAS Powersaw Chain and Bar Oil", "I", application="chain saw, external gear and chain lubricant", source_quality_flags=["product_page_publishes_no_iso_vg_grade"]),
    variant(177, "MOGAS Prottex Grease EP NLGI 00", "G", nlgi="00", thickener="lithium", grease_type="EP semi-fluid multipurpose", standards=["ISO 6743-9 L-XCBEB 00", "DIN 51502 GP00G-30"]),
    variant(179, "MOGAS Prottex Grease HDX NLGI 2", "G", nlgi="2", thickener="lithium complex", solid_lubricant="3% molybdenum disulfide", grease_type="EP heavy-duty", oem_specifications=["Mack MG-C", "Caterpillar MPGM"], operating_temperature_c={"min": -20, "max": 150}),
    variant(187, "MOGAS Prottex Grease OGH NLGI 0", "G", nlgi="0", thickener="calcium sulphonate complex", grease_type="EP water-resistant high-temperature", standards=["ISO 6743-9 L-XBFHB 0", "DIN 51502 OGPF0R-20"], operating_temperature_c={"min": -20, "max": 180}, source_quality_flags=["application_text_erroneously_names_prottex_wr_retained_as_source_conflict"]),
    variant(189, "MOGAS Prottex Grease WR NLGI 2", "G", nlgi="2", thickener="lithium-calcium mixed soap", grease_type="EP water-resistant multipurpose", standards=["ASTM D4950 LB"], operating_temperature_c={"min": -20, "max": 130}, source_reported_peak_temperature_c=140),
    variant(174, "MOGAS Radiator Coolant 50:50", "C", coolant_chemistry="virgin ethylene glycol", dilution="premix 50:50", standards=["ASTM D4985", "ASTM D3306", "ASTM D5345", "ASTM D4656", "ASTM D6210", "SAE J1941", "SAE J1034"], oem_specifications=["Case MS1710", "Detroit Diesel 7SE298", "Cummins 90T8-4", "Cummins 3666132", "Freightliner 48-22880", "Ford New Holland 9-86", "GM 1825M", "GM 1899M", "GSA A-A-870", "DOD A-A-52624", "John Deere 8650-5"]),
    variant(175, "MOGAS Radiator Coolant Concentrate 100", "C", coolant_chemistry="monoethylene glycol low-silicate NAP-free", dilution="concentrate", standards=["SAE J1034", "ASTM D4985"], oem_specifications=["GM 1899M", "GM 6038M", "Chrysler MS 7170", "John Deere H24B1/24C1", "Cummins 90T8-4", "Ford ESE-M97B44-A", "Detroit Diesel"]),
    variant(123, "MOGAS Sentry 4T SAE 20W-50", "M", sae_engine="20W-50", api=["SL"], jaso=["MA2"], engine_cycle="4T"),
    variant(102, "MOGAS Sentry FL SYN SAE 5W-40", "M", sae_engine="5W-40", api=["SN", "CF"], acea=["A3/B3", "A3/B4"], base_oil="synthetic", oem_specifications=["MB-Approval 229.3", "Porsche A40", "Renault RN0700", "Renault RN0710", "VW 502 00", "VW 505 00"]),
    variant(122, "MOGAS Sentry G SAE 20W-50", "M", sae_engine="20W-50", source_reported_api_values=["SG/CF in application text", "SG/CD in specification line"], source_quality_flags=["api_secondary_class_conflict_cf_vs_cd_not_promoted_to_strict_key"]),
    variant(117, "MOGAS Sentry HD SAE 40", "M", sae_engine="40", api=["SF", "CD"]),
    variant(78, "MOGAS Turbofleet SAE 15W-40", "M", sae_engine="15W-40", api=["CI-4", "CH-4", "CG-4", "CF-4", "CF", "SL"], acea=["E3", "E5", "E7", "B2", "A3"], oem_specifications=["MB-Approval 228.3", "MAN M3275", "Volvo VDS-3", "MB 229.1", "Cummins CES 20071", "Cummins CES 20072", "Cummins CES 20076", "Cummins CES 20077", "Cummins CES 20078", "Renault RLD-2", "MTU Type 2", "Mack EO-M Plus", "ZF TE-ML 07C"]),
]

for grade in ["80W-90", "85W-140"]:
    PRODUCTS.append(variant(135, f"MOGAS Dynatrans EP SAE {grade}", "T", sae_gear=grade, api_gl=["GL-5"], standards=["MIL-L-2105D"]))
for grade in ["32", "46", "68"]:
    PRODUCTS.append(variant(146, f"MOGAS Hydrax Z ISO VG {grade}", "H", iso_vg=grade, hydraulic_class=["HLP"], base_oil="mineral", standards=["DIN 51524-2"], oem_specifications=["Denison HF-0", "US Steel 127", "US Steel 136", "Eaton Vickers M-2950-S", "Eaton Vickers I-286-S", "AFNOR NFE 48-691", f"Cincinnati P-{'68' if grade == '32' else '69' if grade == '46' else '70'}"]))
for grade in ["30", "40"]:
    PRODUCTS.append(variant(163, f"MOGAS Marina XHP 40{grade} SAE {grade}", "M", sae_engine=grade, api=["CG-4"], acea=["E3-96"], marine_bn_mg_koh_g=40, oem_specifications=["MTU Type II"]))
for card_id, base_name, grades, shared in [
    (178, "MOGAS Prottex Grease EP", ["2", "3"], spec(thickener="lithium", grease_type="EP multipurpose", standards=["ISO 6743-9 L-XBCEB"], operating_temperature_c={"min": -20, "max": 130})),
    (184, "MOGAS Prottex Grease HT", ["2", "3"], spec(thickener="bentonite clay", grease_type="high-temperature", standards=["US Steel 372", "IPSS 1-09-008", "ISO 6743-9 L-XAEEA"], operating_temperature_c={"min": 120, "max": 220})),
    (185, "MOGAS Prottex Grease JB", ["1", "2"], spec(thickener="inorganic non-soap", solid_lubricant="molybdenum disulfide", standards=["US Steel 372", "IPSS 1-09-008", "ISO 6743-9"], operating_temperature_c={"min": 10, "max": 250})),
    (186, "MOGAS Prottex Grease MP", ["2", "3"], spec(thickener="lithium", grease_type="multipurpose", standards=["ISO 6743-9 L-XBCEA"], operating_temperature_c={"min": -20, "max": 130})),
    (188, "MOGAS Prottex Grease WBX", ["2", "3"], spec(thickener="lithium complex", grease_type="EP multipurpose", standards=["ASTM D4950 GC-LB", "ISO 6743-9 L-XBEHB"], operating_temperature_c={"min": -30, "max": 160})),
]:
    for grade in grades:
        PRODUCTS.append(variant(card_id, f"{base_name} NLGI {grade}", "G", nlgi=grade, **shared))


def normalized_card_facts(row: dict) -> dict:
    prices = row["prices"]
    return {
        "id": row["id"],
        "name": html.unescape(row["name"]),
        "permalink": row["permalink"],
        "categories": sorted(category["name"] for category in row["categories"]),
        "attributes": {
            attribute["name"]: sorted(term["name"] for term in attribute["terms"])
            for attribute in row.get("attributes", [])
        },
        "description_text": clean_html(row.get("description", "")),
        "price_minor_units": prices.get("price"),
        "regular_price_minor_units": prices.get("regular_price"),
        "sale_price_minor_units": prices.get("sale_price"),
        "currency_code": prices.get("currency_code"),
        "currency_symbol": prices.get("currency_symbol"),
        "currency_minor_unit": prices.get("currency_minor_unit"),
        "has_options": row.get("has_options", False),
        "is_in_stock": row.get("is_in_stock"),
        "is_purchasable": row.get("is_purchasable"),
        "add_to_cart": row.get("add_to_cart", {}),
    }


def main() -> None:
    source_rows = fetch_json(API_URL)
    if len(source_rows) != 39 or {row["id"] for row in source_rows} != (
        {row["card_id"] for row in PRODUCTS} | EXCLUDED_IDS
    ):
        raise RuntimeError("MOGAS Burundi shop denominator changed")
    excluded = [row for row in source_rows if row["id"] in EXCLUDED_IDS]
    if {html.unescape(row["name"]) for row in excluded} != {
        "6kg Cylinder", "13kg Cylinder", "45kg Cylinder",
    }:
        raise RuntimeError("Expected LPG cylinder exclusions changed")

    cards = {
        row["id"]: normalized_card_facts(row)
        for row in source_rows if row["id"] not in EXCLUDED_IDS
    }
    if len(cards) != 36:
        raise RuntimeError("Relevant card denominator changed")
    records = []
    occurrences = Counter()
    for index, source in enumerate(sorted(PRODUCTS, key=lambda row: (row["card_id"], row["product_name"])), 1):
        card = cards[source["card_id"]]
        occurrences[source["card_id"]] += 1
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"MOGAS-BI-{index:03d}",
            "source_card_id": source["card_id"],
            "source_url": card["permalink"],
            "listing_url": SHOP_URL,
            "source_card_facts_sha256": hashlib.sha256(
                json.dumps(card, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Burundi",
            "market_evidence_status": "official_burundi_section_url_and_title_but_uganda_footer_conflict",
            "manufacturer": "MOGAS Group",
            "brand": "MOGAS",
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "lifecycle_status": "current_shop_listing_country_and_currency_conflicted",
            "evidence_status": "official_manufacturer_burundi_section_complete_shop_api",
            "specifications": source["specifications"] | {
                "source_category": card["categories"],
                "source_attributes": card["attributes"],
                "source_price_minor_units": card["price_minor_units"],
                "source_regular_price_minor_units": card["regular_price_minor_units"],
                "source_sale_price_minor_units": card["sale_price_minor_units"],
                "source_currency_code": card["currency_code"],
                "source_currency_symbol": card["currency_symbol"],
                "source_currency_minor_unit": card["currency_minor_unit"],
                "source_is_in_stock": card["is_in_stock"],
                "source_is_purchasable": card["is_purchasable"],
                "source_add_to_cart": card["add_to_cart"],
                "source_quality_flags": sorted(set(
                    source["specifications"].get("source_quality_flags", [])
                    + [
                        "burundi_section_footer_publishes_uganda_contact",
                        "woocommerce_reports_usd_but_price_scale_and_country_context_make_currency_unreliable",
                        "source_price_excluded_from_analytical_offer_layer",
                        "order_action_present_but_grade_specific_stock_not_verified",
                    ]
                )),
            },
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "current_complete_shop_api_country_currency_conflicts_explicit",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "api_cards": len(source_rows),
        "excluded_non_lubricant_lpg_cylinders": len(excluded),
        "relevant_shop_cards": len(cards),
        "product_grade_identities": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "cards_expanded_to_multiple_grades": sum(count > 1 for count in occurrences.values()),
        "cards_with_order_action": sum(bool(card["add_to_cart"]) for card in cards.values()),
        "cards_source_reported_in_stock": sum(card["is_in_stock"] is True for card in cards.values()),
        "cards_source_reported_purchasable": sum(card["is_purchasable"] is True for card in cards.values()),
        "source_reported_currency_codes": dict(sorted(Counter(card["currency_code"] for card in cards.values()).items())),
        "api_normalized_facts_sha256": hashlib.sha256(
            json.dumps(cards, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "denominator_note": "All 39 Store API cards are accounted for: 36 lubricant/fluid cards normalized and three LPG cylinder cards excluded.",
        "offer_note": "Orderability and raw configured prices remain in source specifications, but no analytical offers are created because the Burundi section has a Uganda footer and the WooCommerce USD configuration is implausible for the published amounts.",
        "publication_scope": "Factual product names, variants, specifications, shop state, evidence URLs and hashes only; descriptions, reviews, contacts and images are excluded.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
