#!/usr/bin/env python3
"""Normalize the lubricant guide currently linked by PETROMOC Mozambique.

The official landing page still links this 2011-era guide.  It is therefore
valuable product evidence, but every record is deliberately labelled as a
legacy catalog row rather than a current market offer.  Only factual names,
grades, specifications and typical-property values are retained.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/mozambique-petromoc-legacy-products.jsonl"
REPORT = ROOT / "data/mozambique-petromoc-legacy-report.json"
SOURCE_ID = "MOZAMBIQUE_PETROMOC_OFFICIALLY_LINKED_LEGACY_CATALOG"
LANDING_URL = "https://www.petromoc.co.mz/product-service/lubrificantes/"
PDF_URL = (
    "https://www.petromoc.co.mz/wp-content/uploads/2021/12/"
    "BROCHURA-DE-LUBRIFICANTES-PORTUGUES-.pdf"
)
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def product(name: str, family: str, page: int, **specifications: object) -> dict:
    return {
        "product_name": name,
        "family_code": family,
        "source_page": page,
        "specifications": specifications,
    }


PRODUCTS = [
    product(
        "Petromoc Leão B SAE 15W-40",
        "M",
        3,
        sae_engine="15W-40",
        api=["CJ-4", "SL"],
        acea=["E5"],
        oem_specifications=[
            "Mercedes-Benz 228.3", "MAN M 3275", "Volkswagen 501.01",
            "Volkswagen 505.00", "Volvo VDS-3", "Renault VI RLD",
            "Mack EO-M", "Caterpillar TO-2", "Allison C-4",
        ],
        typical_properties={"kv40_cst": 106, "kv100_cst": 14.5, "viscosity_index": 140, "flash_point_c": 225, "pour_or_freezing_point_c": -30},
    ),
    product("Petromoc Chita SAE 15W-50", "M", 4, sae_engine="15W-50", api=["SJ", "CF"], acea=["A3-96", "B3-96"], oem_specifications=["Volkswagen 501.01", "Volkswagen 505.00", "MB 229.1"], base_oil="synthetic", typical_properties={"kv40_cst": 143, "kv100_cst": 18.5, "viscosity_index": 146, "flash_point_c": 225, "pour_or_freezing_point_c": -33}),
    product("Petromoc Chita SAE 20W-50", "M", 5, sae_engine="20W-50", api=["SM", "CF"], acea=["A3-98", "B3-96", "B4-98"], oem_specifications=["Volkswagen 502.00", "Volkswagen 505.00", "MB 229.3"], base_oil="synthetic", typical_properties={"kv40_cst": 83.7, "kv100_cst": 13.8, "viscosity_index": 169, "flash_point_c": 225, "pour_or_freezing_point_c": -33}),
    product("Petromoc Leão Sintético SAE 10W-40", "M", 6, sae_engine="10W-40", api=["CF"], acea=["E4"], oem_specifications=["Mercedes-Benz 228.5", "MAN M 3275", "Volvo VDS-2", "Renault VI RXD"], typical_properties={"kv40_cst": 93.7, "kv100_cst": 14.5, "viscosity_index": 157, "flash_point_c": 232, "pour_or_freezing_point_c": -33}),
]

for grade, properties in {
    "30": (100, 12, 100, 220, -18),
    "40": (155, 15.5, 100, 230, -10),
    "50": (220, 20, 100, 240, -10),
}.items():
    PRODUCTS.append(product(
        f"Petromoc Rino SAE {grade}", "M", 7, sae_engine=grade,
        api=["CF", "CD", "SF"],
        oem_specifications=["MAN 270", "MIL-L-2104 E", "MIL-L-46152 B/C", "Mercedes-Benz 227.0", "Caterpillar TO-2", "Allison C-4"],
        typical_properties=dict(zip(("kv40_cst", "kv100_cst", "viscosity_index", "flash_point_c", "pour_or_freezing_point_c"), properties)),
    ))

PRODUCTS.extend([
    product("Petromoc Rino SAE 10W", "M", 8, sae_engine="10W", api=["CF", "CD", "SF"], oem_specifications=["MIL-L-2104 E", "MIL-L-46152 B/C", "Caterpillar TO-2", "Allison C-4"], application="engine oil also specified for hydraulic systems and torque converters", typical_properties={"kv40_cst": 32, "kv100_cst": 6, "viscosity_index": 125, "flash_point_c": 200, "pour_or_freezing_point_c": -25}),
])

for grade, properties in {"30": (100, 12, 105, 220, -18), "40": (150, 15.5, 100, 230, -10)}.items():
    PRODUCTS.append(product(
        f"Petromoc TTE/HD S2 SAE {grade}", "M", 9,
        sae_engine=grade, api=["CC"], oem_specifications=["MIL-L-2104 B"],
        typical_properties=dict(zip(("kv40_cst", "kv100_cst", "viscosity_index", "flash_point_c", "pour_or_freezing_point_c"), properties)),
    ))

PRODUCTS.extend([
    product("Petromoc Búfalo-Agri SAE 20W-50", "T", 10, sae_engine="20W-50", api=["CD"], api_gl=["GL-4"], hydraulic_class=["ISO HV 68/100"], oem_specifications=["Allison C-4", "Massey Ferguson M 1135", "Massey Ferguson M 1139", "John Deere J 20A", "Ford M2C 159B", "MIL-L-2104C", "MIL-L-46152"], application="STOU agricultural engine, transmission, hydraulic and wet-brake fluid", typical_properties={"kv40_cst": 116, "kv100_cst": 13, "viscosity_index": 105, "flash_point_c": 200, "pour_or_freezing_point_c": -21}),
    product("Petromoc Pala-Pala 2T", "M", 11, engine_cycle="2T", api=["TA", "TSC-3"], jaso=["FB"], standards=["ISO-L-EGB"], typical_properties={"kv40_cst": 70, "kv100_cst": 9.5, "viscosity_index": 112, "flash_point_c": 97, "pour_or_freezing_point_c": -12}),
    product("Petromoc Golfinho Outboard", "M", 12, engine_cycle="2T", marine_specifications=["NMMA TC-WII", "NMMA TC-W3"], certification_number="3-12140", typical_properties={"kv40_cst": 35, "kv100_cst": 6.2, "viscosity_index": 128, "flash_point_pensky_martens_c": 58, "pour_or_freezing_point_c": -39}),
])

for grade, properties in {"30": (100, 12, 95, 248, -21), "40": (155, 15.5, 95, 255, -12)}.items():
    PRODUCTS.append(product(
        f"Petromoc Marine 2000 SAE {grade}", "M", 13,
        sae_engine=grade, api=["CD"], oem_specifications=["Caterpillar TO-2"],
        typical_properties=dict(zip(("kv40_cst", "kv100_cst", "viscosity_index", "flash_point_c", "pour_or_freezing_point_c"), properties)) | {"tbn_mg_koh_g": 20},
    ))

PRODUCTS.append(product(
    "Petromoc Marine HD 4015 SAE 40", "M", 14, sae_engine="40", api=["CF"],
    standards=["CCMC D5", "MIL-L-2104E", "French Navy STM 7251A", "NATO O-278"],
    oem_specifications=["Caterpillar TO-2", "MB 228.2"],
    source_reported_approvals=["Baudouin", "Poyaud"],
    typical_properties={"kv40_cst": 145, "kv100_cst": 14.2, "flash_point_c": 230, "pour_or_freezing_point_c": -12, "tbn_mg_koh_g": 14},
))

for grade, properties in {"80W-90": (140, 15, 95, 180, -27), "85W-140": (345, 25, 95, 228, -15)}.items():
    PRODUCTS.append(product(
        f"Petromoc Hipo EP SAE {grade}", "T", 16, sae_gear=grade,
        api_gl=["GL-5"], standards=["MIL-L-2105 D"], oem_specifications=["ZF TE-ML 01", "ZF TE-ML 05", "ZF TE-ML 07"],
        typical_properties=dict(zip(("kv40_cst", "kv100_cst", "viscosity_index", "flash_point_c", "pour_or_freezing_point_c"), properties)),
    ))

PRODUCTS.extend([
    product("Petromoc Elefante", "T", 17, api_gl=["GL-4"], source_reported_sae="80W-85W", oem_specifications=["ZF TE-ML 02 P2", "MAN 341 Type N", "Mercedes-Benz 235.1"], source_quality_flags=["nonstandard_sae_range_retained_verbatim_not_promoted_to_strict_key"], typical_properties={"kv40_cst": 105, "kv100_cst": 11.5, "viscosity_index": 96, "flash_point_c": 224, "pour_or_freezing_point_c": -24}),
    product("Petromoc Zebra ATF Dexron IID", "T", 18, atf_specifications=["GM Dexron IID"], oem_specifications=["BMW Group 23-30", "BMW Group 24-30", "Caterpillar TO-2", "Voith G 607", "ZF TE-ML 04D", "ZF TE-ML 09B", "ZF TE-ML 11A", "ZF TE-ML 17C"], license_number="D-20356", color="red", typical_properties={"kv40_cst": 36.8, "kv100_cst": 7.2, "viscosity_index": 163, "brookfield_viscosity_minus40_mpa_s": 47500, "flash_point_c": 210, "pour_or_freezing_point_c": -44}),
    product("Petromoc Zebra ATF DX III", "T", 19, atf_specifications=["GM Dexron III", "Allison C-4"], oem_specifications=["BMW Group 23-30", "BMW Group 24-30", "Caterpillar TO-2", "Voith G 607", "ZF TE-ML 04D", "ZF TE-ML 09B", "ZF TE-ML 11A", "ZF TE-ML 17C"], color="red", typical_properties={"kv40_cst": 40, "kv100_cst": 7.5, "viscosity_index": 157, "brookfield_viscosity_minus40_mpa_s": 47500, "flash_point_c": 210, "pour_or_freezing_point_c": -44}),
    product("Petromoc Coelho DOT 4", "TF", 21, brake_fluid_class="DOT 4", standards=["SAE J1703", "FMVSS 116 DOT 4", "ISO 4925"], product_form="synthetic brake and clutch fluid", typical_properties={"dry_boiling_point_c_min": 230, "wet_boiling_point_c_min": 155, "flash_point_pensky_martens_c": 125}),
    product("Petromoc Antifreeze Blue", "C", 22, coolant_color="blue", coolant_chemistry="monoethylene glycol aqueous solution with corrosion inhibitors", product_form="concentrate / source dilution guidance", standards=["SABS 1251"], oem_specifications=["Mercedes-Benz Sheet 325.0", "MAN 324", "MTU MTL 5048", "Porsche TL 774C", "SAAB 6901 599", "Volkswagen TL 774C", "Skoda TL 774C", "SEAT TL 774C"], source_reported_freezing_point_c=-30),
    product("Petromoc SMO/2 NLGI 2", "G", 24, nlgi="2", thickener="lithium soap", grease_type="EP multipurpose", standards=["ISO 6743-9 L-XBCEB 2", "DIN 51502 KP2K-25"], source_reported_approvals=["Mercedes-Benz 267.0"], operating_temperature_c={"min": -20, "max": 140}, typical_properties={"worked_penetration_01mm": 280, "dropping_point_c": 185}),
    product("Petromoc GL/Premium 3 NLGI 3", "G", 25, nlgi="3", thickener="lithium/calcium soap", grease_type="multipurpose", standards=["ISO 6743-9 L-XBCEA 3", "DIN 51502 K3K-20"], operating_temperature_c={"min": -20, "max": 120}, typical_properties={"base_oil_kv40_cst": 120, "dropping_point_c_min": 185, "worked_penetration_01mm": "220-250"}),
    product("Petromoc GL/2 NLGI 2", "G", 26, nlgi="2", thickener="lithium/calcium soap", solid_lubricant="molybdenum disulfide", grease_type="EP multipurpose", standards=["ISO 6743-9 L-XBCEB 2", "DIN 51502 MPF2K-25"], operating_temperature_c={"min": -25, "max": 130}, typical_properties={"base_oil_kv40_cst": 150, "dropping_point_c_min": 190, "worked_penetration_01mm": "265-295"}),
])

for grade, properties in {
    "22": (862, 22, 4.4, 105, 200, -30),
    "32": (870, 32, 5.4, 102, 210, -27),
    "46": (877, 46, 6.8, 106, 230, -24),
    "68": (884, 68, 8.7, 100, 240, -21),
    "100": (886, 100, 11.4, 100, 250, -18),
    "150": (890, 150, 15, 100, 260, -15),
}.items():
    PRODUCTS.append(product(
        f"Petromoc SHO ISO VG {grade}", "H", 29, iso_vg=grade,
        standards=["AFNOR NFE 48-603 HM", "ISO 6743-4 HM", "DIN 51524 HLP"],
        oem_specifications=["Vickers M-2950-S", "Vickers I-286-S", "Cincinnati P68/P69/P70", "Hägglunds Denison HF-0/HF-2"],
        typical_properties=dict(zip(("density_15c_kg_m3", "kv40_cst", "kv100_cst", "viscosity_index", "flash_point_c", "pour_or_freezing_point_c"), properties)),
    ))

for grade, properties in {
    "15": (858, 14.7, 3.7, 151, 174, -42),
    "32": (870, 32.3, 6.5, 160, 208, -39),
    "46": (874, 46.0, 8.4, 161, 215, -39),
    "68": (882, 67.5, 11.2, 161, 220, -36),
}.items():
    PRODUCTS.append(product(
        f"Petromoc SHO B ISO VG {grade}", "H", 30, iso_vg=grade,
        standards=["AFNOR NFE 48-603 HV", "DIN 51524-3 HVLP", "ISO 6743-4 HV"],
        oem_specifications=["Cincinnati Milacron P68/P69/P70", "Vickers M-2950-S", "Vickers I-286"],
        typical_properties=dict(zip(("density_15c_kg_m3", "kv40_cst", "kv100_cst", "viscosity_index", "flash_point_c", "pour_or_freezing_point_c"), properties)),
    ))

for grade, properties in {
    "68": (885, 8.8, 100, 240, -21), "100": (893, 11, 100, 250, -21),
    "150": (895, 15, 100, 255, -18), "220": (896, 19, 96, 255, -12),
    "320": (901, 24.5, 96, 255, -12), "460": (906, 31, 96, 260, -9),
    "680": (912, 36.7, 89, 260, -9), "1000": (920, 48.4, 92, 270, -9),
    "1500": (919, 64.3, 95, 270, -9), "2200": (919, 95.1, 103, 280, -9),
}.items():
    PRODUCTS.append(product(
        f"Petromoc Transgear EP ISO VG {grade}", "I", 32, iso_vg=grade,
        standards=["DIN 51517-3", "ISO 6743-6 CKD", "AGMA 9005-D94"],
        oem_specifications=["Cincinnati Milacron", "David Brown"],
        typical_properties={"density_15c_kg_m3": properties[0], "kv40_cst": int(grade), "kv100_cst": properties[1], "viscosity_index": properties[2], "flash_point_c": properties[3], "pour_or_freezing_point_c": properties[4]},
    ))

for grade, properties in {"46": (883, 97, 215, -9), "68": (881, 100, 255, -24), "100": (884, 98, 270, -24), "150": (885, 101, 280, -24)}.items():
    PRODUCTS.append(product(
        f"Petromoc Compressor Oil ISO VG {grade}", "I", 33, iso_vg=grade,
        standards=["DIN 51506 VDL", "ISO 6743-3A DAC"],
        typical_properties={"density_15c_kg_m3": properties[0], "kv40_cst": int(grade), "viscosity_index": properties[1], "flash_point_c": properties[2], "pour_or_freezing_point_c": properties[3]},
    ))

for grade, properties in {"32": (0.890, 180, -39), "46": (0.890, 185, -30)}.items():
    PRODUCTS.append(product(
        f"Petromoc IM ISO VG {grade}", "I", 34, iso_vg=grade,
        application="refrigeration compressors using CFC, HCFC or NH3 refrigerants",
        typical_properties={"density_15c_kg_dm3": properties[0], "kv40_cst": int(grade), "flash_point_c": properties[1], "pour_or_freezing_point_c": properties[2]},
    ))

for grade, properties in {"32": (870, 5.4, 102, 210, -9), "46": (877, 6.8, 100, 230, -9), "68": (884, 8.7, 100, 240, -9), "100": (886, 11.4, 100, 250, -9)}.items():
    PRODUCTS.append(product(
        f"Petromoc Turbinoil ISO VG {grade}", "I", 36, iso_vg=grade,
        standards=["DIN 51515-1", "JIS K 2213 Type 2", "BS 489", "ISO 6743-5 TSA/TSE/RGA/TGB/TGE"],
        source_reported_approvals=["GEC Alsthom", "ABB", "Siemens", "Skoda", "Nuovo Pignone"],
        typical_properties={"density_15c_kg_m3": properties[0], "kv40_cst": int(grade), "kv100_cst": properties[1], "viscosity_index": properties[2], "flash_point_c": properties[3], "pour_or_freezing_point_c": properties[4]},
    ))

PRODUCTS.append(product(
    "Petromoc STO Transformer Oil", "E", 37,
    standards=["BS 148/98 Class 1", "IEC 60296:2003"],
    base_oil="highly refined wax-free naphthenic insulating oil",
    application="high-voltage transformers, switchgear and electrical equipment",
    source_quality_flags=["source_uses_ice_where_iec_is_probable_retained_as_published_in_raw_evidence"],
    typical_properties={"density_20c_kg_dm3": "0.875-0.88", "kv40_cst": 9.24, "kv100_cst": "2.36-3.0", "flash_point_c": 145, "pour_point_c": -50, "breakdown_voltage_kv": ">60"},
))

for grade, properties in {"10W": (878, 28, 5, 110, 220, -38), "30": (895, 105, 12, 102, 260, -35), "50": (905, 255, 20, 90, 265, -18)}.items():
    PRODUCTS.append(product(
        f"Petromoc Hipo AC SAE {grade}", "T", 39, sae_gear=grade,
        oem_specifications=["Caterpillar TO-4", "Allison C-4"],
        application="off-highway powershift transmissions, final drives and hydraulic systems",
        typical_properties=dict(zip(("density_15c_kg_m3", "kv40_cst", "kv100_cst", "viscosity_index", "flash_point_c", "pour_or_freezing_point_c"), properties)),
    ))


PAGE_TOKENS = {
    3: ["LEÃO B", "API CJ-4/SL"],
    7: ["RINO", "SAE 30", "SAE 50"],
    13: ["MARINE 2000", "Grau SAE 30", "Grau SAE 40"],
    19: ["ZEBRA ATF DX III", "ALLISON C-4"],
    22: ["ANTIFREEZE", "Mercedes Benz. Sheet 325.0"],
    29: ["SHO", "22 32 46 68 100 150"],
    32: ["TRANSGEAR EP", "68 100 150 220 320 460 680 1000 1500 2200"],
    39: ["HIPO AC", "10W 30 50"],
}


def main() -> None:
    landing_payload = fetch(LANDING_URL)
    landing_text = clean(re.sub(r"<[^>]+>", " ", landing_payload.decode(errors="replace")))
    if "Brochura de lubrificantes" not in landing_text:
        raise RuntimeError("PETROMOC official landing page no longer exposes the lubricant brochure")

    pdf_payload = fetch(PDF_URL)
    reader = PdfReader(io.BytesIO(pdf_payload))
    if len(reader.pages) != 39:
        raise RuntimeError(f"Expected 39 PETROMOC brochure pages, found {len(reader.pages)}")
    page_text = {number: clean(reader.pages[number - 1].extract_text() or "") for number in range(1, 40)}
    for page, tokens in PAGE_TOKENS.items():
        for token in tokens:
            if token.casefold() not in page_text[page].casefold():
                raise RuntimeError(f"Missing expected token on page {page}: {token}")

    records = []
    for index, source in enumerate(PRODUCTS, 1):
        page = source["source_page"]
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"PETROMOC-MZ-{index:03d}",
            "source_url": LANDING_URL,
            "technical_document_url": PDF_URL,
            "technical_document_sha256": hashlib.sha256(pdf_payload).hexdigest(),
            "source_page": page,
            "source_page_text_sha256": hashlib.sha256(page_text[page].encode()).hexdigest(),
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Mozambique",
            "manufacturer": "Petróleos de Moçambique, S.A.",
            "brand": "PETROMOC",
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "lifecycle_status": "officially_linked_legacy_catalog",
            "evidence_status": "official_state_owned_supplier_legacy_technical_catalog",
            "specifications": source["specifications"],
        })

    if len(records) != 60:
        raise RuntimeError(f"Expected 60 product-grade rows, found {len(records)}")
    if len({row["product_name"].casefold() for row in records}) != len(records):
        raise RuntimeError("Duplicate normalized PETROMOC product names")

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "officially_linked_legacy_state_owned_supplier_catalog_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_url": LANDING_URL,
        "technical_document_url": PDF_URL,
        "landing_page_sha256": hashlib.sha256(landing_payload).hexdigest(),
        "technical_document_sha256": hashlib.sha256(pdf_payload).hexdigest(),
        "technical_document_pages": len(reader.pages),
        "source_product_sheets": len({row["source_page"] for row in records}),
        "normalized_product_grade_rows": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "quality_flags": dict(sorted(Counter(
            flag for row in records
            for flag in row["specifications"].get("source_quality_flags", [])
        ).items())),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "lifecycle_note": "The 2026 official PETROMOC page links the brochure, but the brochure artwork identifies it as a 2011-era guide. Rows are historical evidence, not current availability.",
        "grain_note": "One row per explicitly published product-grade variant; multi-grade technical tables are expanded and package variants are not invented.",
        "publication_scope": "Factual product names, technical classifications, typical values, evidence URLs and hashes only; brochure prose, artwork and layout are excluded.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
