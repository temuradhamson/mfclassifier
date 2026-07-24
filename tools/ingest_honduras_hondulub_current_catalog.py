#!/usr/bin/env python3
"""Build the current Hondureña de Lubricantes catalog evidence layer.

The current homepage publishes eleven factual product tables as images.  The
tables contain 110 printed rows; explicit multi-grade rows expand to 120
identity hints after three exact package-only duplicate rows are collapsed.
Thirty-one OIL STAR product-grade identities enter canonical product truth.
Other global brands remain Honduras availability occurrences pending their
manufacturer-level identity passes.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_OUT = ROOT / "data/honduras-hondulub-current-oil-star-products.jsonl"
AVAILABILITY_OUT = ROOT / "data/honduras-hondulub-current-availability.jsonl"
REPORT_OUT = ROOT / "data/honduras-hondulub-current-catalog-report.json"

SNAPSHOT_DATE = "2026-07-24"
SOURCE_ID = "HONDURAS_HONDULUB_CURRENT_PRODUCT_TABLES"
HOME_URL = "https://hondulub.com/"
IMAGE_BASE = "https://hondulub.com/wp-content/uploads/2023/09/"
UA = "MFClassifier evidence catalog/1.0"

IMAGE_SHA256 = {
    1: "91ea314ed97878a61cb2fb95a1e0cbd06ba098ae6eed2b6f7e8d9fe76a40605c",
    2: "05f29bfb3595c15565aa5e7119899020ecde304b06e9f15c8a2828e86370564a",
    3: "0fb73e879ac9896381898a369ad08e2761218bf1331d8436478de1777ad3151d",
    4: "6c2130cbb4179c8c0f68d71da7dfdba0eb87d16909d7d98dd4d1bb6c8b222e5a",
    5: "2ab6d10d3a10dcf3f6d9274e2c7b7b20ccfa54824be5cc4e75ec50f299e8ff3d",
    6: "29c487a995d4f2193b0bddc229f864b7fc0818d0d96bd334883c4d720cd07696",
    7: "275e78442988e2526790394c17974175c3c671e89efbe5675b6d38c4c8510e3d",
    8: "ac35550c3869a9cd51c5a0580406b82394469216027ec20cec24dc66fbb55ce6",
    9: "d9f771018910207a6753da8e3fbf805a02ad13b62d6b6d10872756f8fec6b6f3",
    10: "7a95bd241a303a474d2be9dd517cb804db24dbfcb11bc9dc8e225a7911234fb1",
    11: "c46c2294234c942e40fe1b4b8aaa8dc21ee970e3a80d419fc6c80aabe11064fb",
}


def tech(*, sae_engine="", sae_gear="", iso_vg="", source_grade="",
         api=(), api_gl=(), acea=(), jaso=(), dot="", coolant_class="",
         performance=()):
    return {
        "sae_engine": sae_engine,
        "sae_gear": sae_gear,
        "iso_vg": iso_vg,
        "nlgi": "",
        "source_grade": source_grade,
        "api": list(api),
        "api_gl": list(api_gl),
        "acea": list(acea),
        "ilsac": [],
        "jaso": list(jaso),
        "dot": dot,
        "coolant_class": coolant_class,
        "performance": list(performance),
    }


def item(image, brand, name, family, packages, technical=None, *,
         scope="global_product_honduras_availability", flags=()):
    return {
        "image": image,
        "brand": brand,
        "name": name,
        "family_code": family,
        "packages": list(packages),
        "technical": technical or tech(),
        "scope_status": scope,
        "flags": list(flags),
    }


OIL = "canonical_oil_star_product"
REPORT_ONLY = "report_only_generic_series"
EXCLUDED = "excluded_non_product_equipment"

P = []

# Image 1 — gasoline/diesel, gas and two-cycle engine oils.
P += [
    item(1, "OIL STAR", "OIL STAR 15W-40 Semi-Synthetic CK-4/SN", "M", ("55 Gal", "5 Gal"), tech(sae_engine="15W-40", api=("CK-4", "SN")), scope=OIL),
    item(1, "OIL STAR", "OIL STAR MG 15W-40 Mineral CJ-4/SN", "M", ("55 Gal", "5 Gal"), tech(sae_engine="15W-40", api=("CJ-4", "SN")), scope=OIL),
    item(1, "OIL STAR", "OIL STAR 15W-50 Semi-Synthetic CF/SN", "M", ("55 Gal", "5 Gal"), tech(sae_engine="15W-50", api=("CF", "SN")), scope=OIL),
    item(1, "OIL STAR", "OIL STAR Super 10W-30 Semi-Synthetic CK-4/SN", "M", ("55 Gal", "5 Gal"), tech(sae_engine="10W-30", api=("CK-4", "SN")), scope=OIL),
    item(1, "OIL STAR", "OIL STAR Super 10W-30 Mineral SN/GF-5", "M", ("55 Gal", "5 Gal"), tech(sae_engine="10W-30", api=("SN",), performance=("ILSAC GF-5",)), scope=OIL),
    item(1, "OIL STAR", "OIL STAR Super 20W-50 Mineral CF/SP", "M", ("55 Gal", "5 Gal"), tech(sae_engine="20W-50", api=("CF", "SP")), scope=OIL),
    item(1, "OIL STAR", "OIL STAR Super SAE 40W Mineral CF-4", "M", ("55 Gal", "5 Gal"), tech(source_grade="SAE 40W", api=("CF-4",)), scope=OIL, flags=("source_nonstandard_sae_40w_retained_without_mapping_to_sae_40",)),
    item(1, "OIL STAR", "OIL STAR Super SAE 50W Mineral CF-4", "M", ("55 Gal", "5 Gal"), tech(source_grade="SAE 50W", api=("CF-4",)), scope=OIL, flags=("source_nonstandard_sae_50w_retained_without_mapping_to_sae_50",)),
    item(1, "Phillips 66", "Phillips 66 Guardol Fleet EC EO 15W-40 Mineral CK-4/SN", "M", ("55 Gal", "5 Gal", "12 cuartos", "3 galones"), tech(sae_engine="15W-40", api=("CK-4", "SN")), flags=("duplicate_table_package_row_collapsed",)),
    item(1, "Phillips 66", "Phillips 66 Power-D Engine Oil 15W-40 Mineral CI-4 Plus", "M", ("3 galones",), tech(sae_engine="15W-40", api=("CI-4 Plus",))),
    item(1, "Phillips 66", "Phillips 66 Guardol ECT TI 10W-30 Semi-Synthetic CK-4", "M", ("12 cuartos", "3 galones"), tech(sae_engine="10W-30", api=("CK-4",)), flags=("source_product_token_ti_retained_verbatim",)),
    item(1, "Phillips 66", "Phillips 66 Shield Choice 10W-30 Semi-Synthetic SN Plus", "M", ("12 cuartos",), tech(sae_engine="10W-30", api=("SN Plus",))),
    item(1, "Phillips 66", "Phillips 66 Shield Classic 20W-50 Mineral SN Plus", "M", ("12 cuartos", "3 galones"), tech(sae_engine="20W-50", api=("SN Plus",))),
    item(1, "Phillips 66", "Phillips 66 Shield Valor 0W-20 Full Synthetic", "M", ("12 cuartos",), tech(sae_engine="0W-20", api=("SN Plus",), performance=("GM dexos1 Gen 2 (source-reported)",))),
    item(1, "Phillips 66", "Phillips 66 Shield Valor 5W-20 Full Synthetic", "M", ("12 cuartos",), tech(sae_engine="5W-20", api=("SN Plus",), performance=("GM dexos1 Gen 2 (source-reported)",))),
    item(1, "Phillips 66", "Phillips 66 Shield Choice 5W-20 Semi-Synthetic SN Plus", "M", ("12 cuartos",), tech(sae_engine="5W-20", api=("SN Plus",))),
    item(1, "Phillips 66", "Phillips 66 Shield Valor 5W-30 Full Synthetic", "M", ("12 cuartos",), tech(sae_engine="5W-30", api=("SN Plus",), performance=("GM dexos1 Gen 3 (source-reported)",))),
    item(1, "Phillips 66", "Phillips 66 Shield Choice 5W-30 Semi-Synthetic SP", "M", ("12 cuartos",), tech(sae_engine="5W-30", api=("SP",))),
    item(1, "Phillips 66", "Phillips 66 Shield Euro-Tech 5W-40 Full Synthetic SN", "M", ("12 cuartos",), tech(sae_engine="5W-40", api=("SN",), acea=("A3/B4-16",))),
    item(1, "Phillips 66", "Phillips 66 4T 20W-50 Mineral SL", "M", ("12 cuartos",), tech(sae_engine="20W-50", api=("SL",), jaso=("MA",))),
    item(1, "TEK STAR", "TEK STAR 0W-20 Full Synthetic", "M", ("55 Gal", "5 Gal"), tech(sae_engine="0W-20", performance=("GM dexos1 Gen 2 (source-reported)",))),
    item(1, "TEK STAR", "TEK STAR 5W-20 Semi-Synthetic SN Plus", "M", ("55 Gal", "5 Gal", "12 cuartos"), tech(sae_engine="5W-20", api=("SN Plus",)), flags=("duplicate_table_package_row_collapsed",)),
    item(1, "TEK STAR", "TEK STAR 10W-30 Semi-Synthetic SN Plus", "M", ("55 Gal", "5 Gal", "12 cuartos"), tech(sae_engine="10W-30", api=("SN Plus",)), flags=("duplicate_table_package_row_collapsed",)),
    item(1, "TEK STAR", "TEK STAR Auto 10W-40 CF/SN", "M", ("55 Gal", "5 Gal"), tech(sae_engine="10W-40", api=("CF", "SN"))),
    item(1, "TEK STAR", "TEK STAR 25W-60 Mineral CH-4/SG", "M", ("55 Gal", "5 Gal"), tech(sae_engine="25W-60", api=("CH-4", "SG"))),
    item(1, "TEK STAR", "TEK STAR SAE 30 ND", "M", ("55 Gal", "5 Gal"), tech(sae_engine="30", source_grade="ND (no detergente)")),
    item(1, "TEK STAR", "TEK STAR LE 15W-40 Semi-Synthetic CK-4/SN Plus", "M", ("12 cuartos",), tech(sae_engine="15W-40", api=("CK-4", "SN Plus"))),
    item(1, "TEK STAR", "TEK STAR High Performance MG 15W-40 CI-4 Plus", "M", ("12 cuartos",), tech(sae_engine="15W-40", api=("CI-4 Plus",))),
    item(1, "TEK STAR", "TEK STAR High Performance 10W-30 SM", "M", ("12 cuartos",), tech(sae_engine="10W-30", api=("SM",))),
    item(1, "TEK STAR", "TEK STAR 20W-50 Semi-Synthetic SN Plus", "M", ("12 cuartos",), tech(sae_engine="20W-50", api=("SN Plus",))),
    item(1, "TEK STAR", "TEK STAR High Performance 20W-50 SM", "M", ("12 cuartos",), tech(sae_engine="20W-50", api=("SM",))),
    item(1, "TEK STAR", "TEK STAR 5W-30 Full Synthetic", "M", ("12 cuartos",), tech(sae_engine="5W-30", api=("SN Plus",), performance=("GM dexos1 Gen 2 (source-reported)",))),
    item(1, "TEK STAR", "TEK STAR 5W-30 Semi-Synthetic SN Plus", "M", ("12 cuartos",), tech(sae_engine="5W-30", api=("SN Plus",))),
    item(1, "TEK STAR", "TEK STAR Potenza 4T 20W-50 Semi-Synthetic SN Plus", "M", ("12 cuartos",), tech(sae_engine="20W-50", api=("SN Plus",), jaso=("MA2",))),
    item(1, "TEK STAR", "TEK STAR 20W-50 Gas Semi-Synthetic SN", "M", ("55 Gal", "5 Gal"), tech(sae_engine="20W-50", api=("SN",))),
    item(1, "TEK STAR", "TEK STAR 5W-30 Gas Semi-Synthetic SN Plus", "M", ("55 Gal", "5 Gal"), tech(sae_engine="5W-30", api=("SN Plus",))),
    item(1, "TEK STAR", "TEK STAR Nautica 2-Cycle TC-W3", "M", ("12 cuartos",), tech(performance=("NMMA TC-W3 (source-reported)",))),
]

# Image 2 — marine and stationary-generator oils.
P += [
    item(2, "TEK STAR", "TEK STAR Marine 13 TBN SAE 40W", "M", ("55 Gal",), tech(source_grade="13 TBN SAE 40W"), flags=("source_nonstandard_sae_40w_retained_without_mapping_to_sae_40",)),
    item(2, "TEK STAR", "TEK STAR Marine 40 TBN SAE 30W", "M", ("55 Gal",), tech(source_grade="40 TBN SAE 30W"), flags=("source_nonstandard_sae_30w_retained_without_mapping_to_sae_30",)),
    item(2, "TEK STAR", "TEK STAR Marine 40 TBN SAE 40W", "M", ("55 Gal",), tech(source_grade="40 TBN SAE 40W"), flags=("source_nonstandard_sae_40w_retained_without_mapping_to_sae_40",)),
    item(2, "TEK STAR", "TEK STAR Marine Diesel Cylinder Lubricant 70 TBN SAE 50W", "M", ("55 Gal",), tech(source_grade="70 TBN SAE 50W"), flags=("source_nonstandard_sae_50w_retained_without_mapping_to_sae_50",)),
]

# Image 3 — gear oils and transmission fluids.
P += [
    item(3, "OIL STAR", "OIL STAR Universal Gear HD 85W-140 GL-5", "T", ("55 Gal", "5 Gal"), tech(sae_gear="85W-140", api_gl=("GL-5",)), scope=OIL),
    item(3, "OIL STAR", "OIL STAR Universal Gear HD 80W-90 GL-5", "T", ("55 Gal", "5 Gal"), tech(sae_gear="80W-90", api_gl=("GL-5",)), scope=OIL),
    item(3, "TEK STAR", "TEK STAR Gear Lube 75W-90 Full Synthetic", "T", ("55 Gal", "5 Gal"), tech(sae_gear="75W-90")),
    item(3, "OIL STAR", "OIL STAR Drive Train Fluid SAE 10W TO-4", "TF", ("55 Gal", "5 Gal"), tech(sae_engine="10W", performance=("Caterpillar TO-4",)), scope=OIL),
    item(3, "OIL STAR", "OIL STAR Drive Train Fluid SAE 50W TO-4", "TF", ("55 Gal", "5 Gal"), tech(source_grade="SAE 50W", performance=("Caterpillar TO-4",)), scope=OIL, flags=("source_nonstandard_sae_50w_retained_without_mapping_to_sae_50",)),
    item(3, "OIL STAR", "OIL STAR SAE 50W Synthetic", "TF", ("55 Gal", "5 Gal"), tech(source_grade="SAE 50W"), scope=OIL, flags=("source_nonstandard_sae_50w_retained_without_mapping_to_sae_50",)),
    item(3, "OIL STAR", "OIL STAR MP ATF MD-3", "TF", ("55 Gal", "5 Gal"), tech(source_grade="MD-3"), scope=OIL),
    item(3, "OIL STAR", "OIL STAR JD-20 MP Tractor Fluid", "TF", ("55 Gal", "5 Gal"), tech(source_grade="JD-20"), scope=OIL),
    item(3, "Phillips 66", "Phillips 66 VersaTrans CVT Plus Fluid Full Synthetic", "TF", ("12 cuartos",), tech(source_grade="CVT Plus")),
    item(3, "Phillips 66", "Phillips 66 VersaTrans LV ATF Full Synthetic", "TF", ("55 Gal", "12 cuartos"), tech(source_grade="LV ATF")),
    item(3, "Phillips 66", "Phillips 66 VersaTrans ATF Semi-Synthetic", "TF", ("12 cuartos",), tech(source_grade="ATF")),
    item(3, "TEK STAR", "TEK STAR MP ATF MD-3", "TF", ("12 cuartos",), tech(source_grade="MD-3")),
]

# Image 4 — industrial gear compounds.  Numeric EP grades are not silently
# interpreted as ISO VG because the table does not print the ISO designation.
for grade in ("68", "100", "150", "220", "320", "460", "680"):
    P.append(item(4, "OIL STAR", f"OIL STAR Gear Compound EP {grade}", "I", ("55 Gal", "5 Gal"), tech(source_grade=f"EP {grade}"), scope=OIL))
for grade in ("150", "220", "680"):
    P.append(item(4, "TEK STAR", f"TEK STAR Gear Compound Synthetic EP {grade}", "I", ("55 Gal", "5 Gal"), tech(source_grade=f"Synthetic EP {grade}")))

# Image 5 — hydraulic oils plus one engine-oil row printed in that section.
for grade in ("32", "46", "68"):
    for tier in ("Regular", "Premium"):
        P.append(item(5, "OIL STAR", f"OIL STAR Hydraulic AW ISO {grade} {tier}", "H", ("55 Gal", "5 Gal"), tech(iso_vg=grade, source_grade=f"AW {grade} {tier}"), scope=OIL))
P.append(item(5, "OIL STAR", "OIL STAR Super SAE 30W CF/CF-2", "M", ("55 Gal", "5 Gal"), tech(source_grade="SAE 30W", api=("CF", "CF-2")), scope=OIL, flags=("source_nonstandard_sae_30w_retained_without_mapping_to_sae_30", "engine_oil_printed_under_hydraulic_section_classified_by_explicit_api_claim")))

# Image 6 — food-grade lubricants.
for grade in ("220", "320", "460"):
    P.append(item(6, "TEK STAR", f"TEK STAR Gear Compound EP {grade} Food Grade H1", "I", ("55 Gal",), tech(source_grade=f"EP {grade}", performance=("NSF H1 (source-reported)",))))
for grade in ("220", "320", "460"):
    P.append(item(6, "TEK STAR", f"TEK STAR Gear EP {grade} Food Grade H1 Synthetic", "I", ("55 Gal",), tech(source_grade=f"Synthetic EP {grade}", performance=("NSF H1 (source-reported)",))))
P += [
    item(6, "TEK STAR", "TEK STAR Hydraulic Food Grade H1 ISO 68", "H", ("55 Gal",), tech(iso_vg="68", performance=("NSF H1 (source-reported)",))),
    item(6, "TEK STAR", "TEK STAR Hydraulic Food Grade H1 ISO 68 Synthetic", "H", ("55 Gal",), tech(iso_vg="68", performance=("NSF H1 (source-reported)",))),
    item(6, "TEK STAR", "TEK STAR Food Grade H1 Full Synthetic Grease EP #2", "G", ("5 Gal",), tech(source_grade="EP #2", performance=("NSF H1 (source-reported)",)), flags=("ep_2_source_label_not_silently_interpreted_as_nlgi_2",)),
    item(6, "TEK STAR", "TEK STAR White Technical Food Grade H1 Mineral", "I", ("55 Gal",), tech(source_grade="White Technical Mineral", performance=("NSF H1 (source-reported)",))),
    item(6, "TEK STAR", "TEK STAR food-grade H1 lubricant assortment", "I", ("55 Gal", "5 Gal"), tech(performance=("NSF H1 (source-reported)",)), scope=REPORT_ONLY, flags=("generic_assortment_without_product_or_grade",)),
]
for grade in ("32", "46", "68"):
    P.append(item(6, "Phillips 66", f"Phillips 66 Hydraulic Food Grade H1 ISO {grade}", "H", ("55 Gal",), tech(iso_vg=grade, performance=("NSF H1 (source-reported)",))))
P.append(item(6, "Phillips 66", "Phillips 66 Food Grade H1 Grease assortment", "G", ("Tubo 14 oz.",), tech(performance=("NSF H1 (source-reported)",)), scope=REPORT_ONLY, flags=("generic_grease_description_without_product_series_or_grade",)))

# Image 7 — special-purpose oils.
P += [
    item(7, "OIL STAR", "OIL STAR Rock Drill ISO 100", "I", ("55 Gal", "5 Gal"), tech(iso_vg="100"), scope=OIL),
]
for grade in ("32", "68", "220"):
    P.append(item(7, "TEK STAR", f"TEK STAR R&O ISO {grade}", "I", ("55 Gal", "5 Gal"), tech(iso_vg=grade, source_grade="R&O")))
P += [
    item(7, "TEK STAR", "TEK STAR Multipurpose Circulating & Bearing Oil ISO 460", "I", ("55 Gal", "5 Gal"), tech(iso_vg="460")),
    item(7, "TEK STAR", "TEK STAR Biodegradable Hydraulic ISO 68", "H", ("55 Gal", "5 Gal"), tech(iso_vg="68")),
    item(7, "TEK STAR", "TEK STAR Refrigeration WF ISO 32", "C", ("55 Gal", "5 Gal"), tech(iso_vg="32", source_grade="WF")),
    item(7, "TEK STAR", "TEK STAR Refrigeration WF ISO 68", "C", ("55 Gal", "5 Gal"), tech(iso_vg="68", source_grade="WF")),
    item(7, "TEK STAR", "TEK STAR Soluble Cutting Oil BT", "S", ("55 Gal", "5 Gal"), tech(source_grade="BT")),
    item(7, "TEK STAR", "TEK STAR AX Inhibited Transformer Oil", "E", ("55 Gal",), tech(source_grade="AX Inhibited")),
    item(7, "TEK STAR", "TEK STAR Utility Oil HVI 22", "I", ("55 Gal",), tech(source_grade="HVI 22", performance=("Máquina de coser tipo R22",))),
    item(7, "TEK STAR", "TEK STAR Utility Oil HVI 32", "I", ("55 Gal",), tech(source_grade="HVI 32", performance=("Máquina de coser tipo R32",))),
    item(7, "TEK STAR", "TEK STAR Turbine Oil T32", "U", ("55 Gal",), tech(source_grade="T32")),
    item(7, "TEK STAR", "TEK STAR Turbine Oil T46", "U", ("55 Gal",), tech(source_grade="T46")),
    item(7, "TEK STAR", "TEK STAR Heat Transfer Oil 32", "I", ("55 Gal",), tech(source_grade="32")),
    item(7, "TEK STAR", "TEK STAR Heat Transfer Oil 46", "I", ("55 Gal",), tech(source_grade="46")),
    item(7, "TEK STAR", "TEK STAR Low Ash SAE 40W Natural Gas Engine Oil", "M", ("55 Gal",), tech(source_grade="Low Ash SAE 40W"), flags=("source_nonstandard_sae_40w_retained_without_mapping_to_sae_40",)),
    item(7, "TEK STAR", "TEK STAR 75 S Spray Oil", "I", ("6100 galones",), tech(source_grade="75 S", performance=("Aceite agrícola",))),
    item(7, "TEK STAR", "TEK STAR compressor-oil assortment", "C", ("55 Gal", "5 Gal"), scope=REPORT_ONLY, flags=("generic_assortment_without_product_or_grade",)),
    item(7, "Ultrachem", "Ultrachem RF2A Ammonia Compressor Oil R717", "C", ("55 Gal",), tech(source_grade="RF2A", performance=("Ammonia compressor R717",))),
    item(7, "Phillips 66", "Phillips 66 Refrigerant Compressor Oil assortment", "C", ("55 Gal",), scope=REPORT_ONLY, flags=("generic_assortment_without_product_or_grade",)),
]

# Image 8 — greases and one non-product automatic lubricator.
P += [
    item(8, "OIL STAR", "OIL STAR Red Ultra HD Grease EP #2", "G", ("400 lbs", "120 lbs", "35 lbs"), tech(source_grade="EP #2", performance=("Multipurpose lithium complex",)), scope=OIL, flags=("ep_2_source_label_not_silently_interpreted_as_nlgi_2",)),
    item(8, "Phillips 66", "Phillips 66 Multiplex 220 Red Grease EP #2", "G", ("Tubo 14 oz.",), tech(source_grade="EP #2", performance=("Multipurpose lithium complex",)), flags=("ep_2_source_label_not_silently_interpreted_as_nlgi_2",)),
    item(8, "TEK STAR", "TEK STAR Heavy Duty Moly 3% Grease EP #2", "G", ("120 lbs", "35 lbs"), tech(source_grade="3% Moly EP #2", performance=("Graphited black lithium complex",)), flags=("ep_2_source_label_not_silently_interpreted_as_nlgi_2",)),
    item(8, "Phillips 66", "Phillips 66 Megaplex XD3 Grease EP #2", "G", ("Tubo 14 oz.",), tech(source_grade="EP #2", performance=("Graphited black grease",)), flags=("ep_2_source_label_not_silently_interpreted_as_nlgi_2",)),
    item(8, "Phillips 66", "Phillips 66 Automatic Lubricator", "G", ("60 cc", "125 cc"), scope=EXCLUDED, flags=("automatic_lubricator_is_equipment_not_lubricant_product",)),
]

# Images 9–11 — coolants, brake fluids and power-steering fluids.
P += [
    item(9, "Shell", "Shell Rotella ELC Nitrite Free Extended Life Red 50/50 Coolant", "TF", ("55 Gal", "6 Galones"), tech(coolant_class="50/50", source_grade="Nitrite Free ELC Red")),
    item(9, "Shell", "Shell Zone Green 50/50 Coolant", "TF", ("6 Galones",), tech(coolant_class="50/50", source_grade="Green")),
    item(9, "Shell", "Shell Zone Green Concentrate Coolant", "TF", ("6 Galones",), tech(coolant_class="Concentrate", source_grade="Green concentrate")),
    item(9, "TEK STAR", "TEK STAR HD ELC Extended Life Red 50/50 Coolant", "TF", ("55 Gal",), tech(coolant_class="50/50", source_grade="HD ELC Red")),
    item(9, "TEK STAR", "TEK STAR Conventional Green 50/50 Coolant", "TF", ("55 Gal",), tech(coolant_class="50/50", source_grade="Conventional Green")),
    item(10, "Pyroil", "Pyroil Synthetic Brake Fluid DOT 4", "TF", ("12/12 oz", "6/32 oz"), tech(dot="DOT 4")),
    item(10, "Pyroil", "Pyroil Synthetic Brake Fluid DOT 3", "TF", ("12/12 oz", "12/32 oz"), tech(dot="DOT 3")),
    item(11, "Pyroil", "Pyroil Power Steering Fluid", "TF", ("12/12 oz", "12/32 oz"), tech(source_grade="Power Steering Fluid")),
    item(11, "Pyroil", "Pyroil Power Steering Fluid Honda", "TF", ("12/12 oz",), tech(source_grade="Honda")),
]


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def main():
    homepage = get(HOME_URL)
    image_facts = {}
    for image_number, expected_sha in IMAGE_SHA256.items():
        url = f"{IMAGE_BASE}{image_number}-1.png"
        if url.encode() not in homepage:
            raise RuntimeError(f"current homepage no longer embeds table image {url}")
        payload = get(url)
        actual_sha = sha256(payload)
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"Hondulub table image {image_number} changed: {actual_sha}"
            )
        image_facts[str(image_number)] = {
            "url": url,
            "sha256": actual_sha,
            "bytes": len(payload),
        }

    if len(P) != 120:
        raise RuntimeError(f"Hondulub normalized identity denominator drift: {len(P)}")
    status_counts = Counter(row["scope_status"] for row in P)
    if status_counts != {
        OIL: 31,
        "global_product_honduras_availability": 84,
        REPORT_ONLY: 4,
        EXCLUDED: 1,
    }:
        raise RuntimeError(f"Hondulub scope matrix drift: {status_counts}")

    availability_rows = []
    canonical_rows = []
    counters = Counter()
    for source_index, source in enumerate(P, 1):
        counters[source["image"]] += 1
        source_record_id = (
            f"HONDULUB-HN-{source['image']:02d}-{counters[source['image']]:03d}"
        )
        image = image_facts[str(source["image"])]
        row = {
            "source_id": SOURCE_ID,
            "source_record_id": source_record_id,
            "source_table_image": source["image"],
            "market": "Honduras",
            "seller": "Hondureña de Lubricantes S.R.L. de C.V.",
            "brand": source["brand"],
            "product_name": source["name"],
            "product_identity_hint": normalize(
                f"{source['brand']} {source['name']} {source['family_code']}"
            ),
            "family_code": source["family_code"],
            "technical": source["technical"],
            "packages": source["packages"],
            "scope_status": source["scope_status"],
            "source_url": HOME_URL,
            "source_image_url": image["url"],
            "source_image_sha256": image["sha256"],
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_current_official_distributor_homepage",
            "source_quality_flags": [
                "official_current_distributor_product_table",
                "table_image_payload_sha256_verified",
                "source_reported_performance_claims_not_independent_approvals",
                *source["flags"],
            ],
        }
        availability_rows.append(row)
        if source["scope_status"] != OIL:
            continue
        canonical_rows.append({
            **row,
            "manufacturer": "",
            "evidence_status": "official_exclusive_distributor_current_product_table",
            "brand_owner_and_distributor": (
                "Hondureña de Lubricantes S.R.L. de C.V. / "
                "OIL STAR (source states products are manufactured in the USA)"
            ),
        })

    canonical_facts = [
        {
            "source_record_id": row["source_record_id"],
            "product_name": row["product_name"],
            "technical": row["technical"],
            "packages": row["packages"],
            "source_image_sha256": row["source_image_sha256"],
        }
        for row in canonical_rows
    ]
    source_facts_sha = sha256(
        json.dumps(canonical_facts, ensure_ascii=False, sort_keys=True).encode()
    )
    for row in canonical_rows:
        row["source_facts_sha256"] = source_facts_sha

    canonical_bytes = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in canonical_rows
    ).encode()
    availability_bytes = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in availability_rows
    ).encode()
    PRODUCT_OUT.write_bytes(canonical_bytes)
    AVAILABILITY_OUT.write_bytes(availability_bytes)

    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "source_url": HOME_URL,
        "homepage_sha256": sha256(homepage),
        "current_table_images": len(IMAGE_SHA256),
        "current_table_image_bytes": sum(
            image["bytes"] for image in image_facts.values()
        ),
        "source_printed_product_rows": 110,
        "normalized_identity_hints_after_expansion_and_package_grouping": len(P),
        "in_scope_product_grade_occurrences": status_counts[OIL]
        + status_counts["global_product_honduras_availability"],
        "canonical_oil_star_product_rows": len(canonical_rows),
        "global_brand_honduras_availability_occurrences": status_counts[
            "global_product_honduras_availability"
        ],
        "report_only_generic_series": status_counts[REPORT_ONLY],
        "excluded_non_product_equipment": status_counts[EXCLUDED],
        "scope_status_counts": dict(sorted(status_counts.items())),
        "brands": dict(sorted(Counter(row["brand"] for row in P).items())),
        "families_in_scope": dict(sorted(Counter(
            row["family_code"] for row in P
            if row["scope_status"] in {
                OIL, "global_product_honduras_availability"
            }
        ).items())),
        "canonical_oil_star_families": dict(sorted(Counter(
            row["family_code"] for row in canonical_rows
        ).items())),
        "source_image_facts": image_facts,
        "source_facts_sha256": source_facts_sha,
        "normalized_product_output_sha256": sha256(canonical_bytes),
        "availability_output_sha256": sha256(availability_bytes),
        "identity_policy": (
            "OIL STAR is the exclusive-distributor portfolio and is the only "
            "new canonical layer. TEK STAR, Phillips 66, Shell, Pyroil and "
            "Ultrachem remain Honduras availability occurrences until their "
            "global identity passes prevent cross-country duplication."
        ),
        "quality_note": (
            "Explicit multi-grade rows are expanded. Package duplicates are "
            "collapsed. Nonstandard source grades such as SAE 40W/50W and EP "
            "#2 remain source labels; no SAE monograde, ISO VG, NLGI, licence "
            "or independent OEM approval is invented."
        ),
    }
    REPORT_OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "identity_hints": len(P),
        "in_scope": report["in_scope_product_grade_occurrences"],
        "canonical_oil_star": len(canonical_rows),
        "availability_only": report[
            "global_brand_honduras_availability_occurrences"
        ],
        "canonical_sha256": report["normalized_product_output_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
