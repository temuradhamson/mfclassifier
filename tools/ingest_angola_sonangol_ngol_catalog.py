#!/usr/bin/env python3
"""Build reviewed product-grade facts from Sonangol's official NGOL catalog.

The official 44-page PDF is publicly indexed but returns HTTP 403 to direct
non-browser downloads as of the snapshot.  Facts below are a page-by-page
transcription of non-expressive product, grade and specification fields.  The
official PDF remains the primary source; an indexed 44-page reading copy was
used only to verify page completeness and is not redistributed.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/angola-sonangol-ngol-products.jsonl"
REPORT = ROOT / "data/angola-sonangol-ngol-report.json"
SNAPSHOT_DATE = "2026-07-24"
SOURCE_ID = "ANGOLA_SONANGOL_NGOL_OFFICIAL_44_PAGE_CATALOG"
SOURCE_URL = (
    "https://observatoriom-dc.sonangol.co.ao/wp-content/uploads/"
    "2024/06/Catalogo_NGol-3.pdf"
)


def item(
    name: str,
    family: str,
    page: int,
    field: str = "source_grade",
    grades: tuple[str, ...] = ("catalog product",),
    *,
    api: tuple[str, ...] = (),
    api_gl: tuple[str, ...] = (),
    acea: tuple[str, ...] = (),
    jaso: tuple[str, ...] = (),
    standards: tuple[str, ...] = (),
    extras: tuple[dict, ...] | None = None,
) -> dict:
    assert extras is None or len(extras) == len(grades)
    return {
        "name": name,
        "family": family,
        "page": page,
        "field": field,
        "grades": grades,
        "api": api,
        "api_gl": api_gl,
        "acea": acea,
        "jaso": jaso,
        "standards": standards,
        "extras": extras or tuple({} for _ in grades),
    }


PRODUCTS = [
    item("NGOL RALLY", "M", 6, "sae_engine", ("5W-40",), api=("SM", "CF"), acea=("A3/B3-04", "A3/B4-04"), standards=("MB 229.5", "VW 502.00/505.00", "BMW LL-01", "Porsche-02", "Opel B 040 2098", "GM-LL-B-025")),
    item("NGOL SPEED", "M", 6, "sae_engine", ("10W-40",), api=("SL", "CF"), acea=("A3/B3-04",), standards=("VW 501.01/505.00", "MB 229.1")),
    item("NGOL HEAVY DIESEL", "M", 7, "sae_engine", ("5W-30",), api=("CI-4",), acea=("EA-99-3", "E7-04", "E5-02"), standards=("Cummins CES 20071/20072/20076/20077", "MB 228.5", "MTU MTL Type 3", "Scania LDF", "Renault RXD", "Volvo VDS-2/VDS-3", "Mack EOM-Plus", "MAN M 3277")),
    item("NGOL SUPER 15W50", "M", 7, "sae_engine", ("15W-50",), api=("SL", "CF"), acea=("A3/B3-04", "A3/B4-04"), standards=("MB 229.1", "VW 501.01/505.00")),
    item("NGOL MG", "M", 8, "sae_engine", ("30", "40"), api=("SF", "CF")),
    item("NGOL MULTIDIESEL", "M", 8, "sae_engine", ("15W-40",), api=("CI-4", "SL"), acea=("E7-07", "E5-02", "E3", "B3", "A3"), standards=("MAN 3275", "MB 228.3/229.1", "Cummins 20071/72/76/77/78", "Caterpillar ECF-2/ECF-1-a", "ZF TE-ML 07C", "Mack EO-M Plus", "Volvo VDS/VDS-3", "Renault RLD/RLD-2", "MTU Type 2")),
    item("NGOL ARIANE", "M", 9, "sae_engine", ("15W-40",), api=("CF-4", "SJ"), acea=("A3",), standards=("MB 229.1", "VW 501.01/505.05")),
    item("NGOL DIESEL", "M", 9, "sae_engine", ("30", "40", "50"), api=("CF", "SF"), acea=("E1",), standards=("MB 227.0", "Allison C-4")),
    item("NGOL LUBSYNT 4", "T", 10, "sae_gear", ("80W-90",), api_gl=("GL-4",), standards=("MIL-L-2105", "Ford ESD-M2C-175 A", "Opel B 040 1043")),
    item("NGOL LUBSYNT 5", "T", 10, "sae_gear", ("75W-90",), api_gl=("GL-5",), standards=("API MT-1", "SAE J2360", "MIL-PRF-2105 E", "Mack GO-J", "Scania STO 1:0")),
    item("NGOL LUBE HD", "T", 11, "sae_gear", ("80W-90", "85W-140"), api_gl=("GL-5",), standards=("MIL-L-2105D", "MAN 342 N")),
    item("NGOL LUBOIL", "T", 11, "sae_gear", ("80W", "90", "80W-90", "85W-140"), api_gl=("GL-4",)),
    item("NGOL BLOCOIL", "T", 12, "sae_gear", ("80W-90", "85W-140"), api_gl=("GL-5",), standards=("MIL-L-2105 B", "ZF TE-ML 05")),
    item("NGOL TRANSFLUID DII", "T", 12, grades=("DEXRON IID",), standards=("GM DEXRON IID", "Allison C-4", "MB 236.6"), extras=({"sae_source_reported": "10W"},)),
    item("NGOL TRANSFLUID DIII", "T", 13, grades=("DEXRON IIIG",), standards=("DEXRON IIIG", "Allison C-4", "Mercon", "Voith G 607", "ZF TE-ML 14", "MB 236.9"), extras=({"sae_source_reported": "10W"},)),
    item("NGOL TRANSTATIC", "T", 13, "sae_gear", ("10W", "30", "50", "60"), api=("CF", "CF-2"), standards=("CAT TO-4", "Allison C-4", "Komatsu Micro-Clutch", "ZF TE-ML 01/03")),
    item("NGOL DIESEL 10W", "T", 14, "sae_gear", ("10W",), api=("CF", "CD", "SF"), acea=("E1",), standards=("MB 227.0", "Allison C-4", "Caterpillar TO-2")),
    item("NGOL MIX 2T", "M", 14, grades=("two-stroke",), api=("TC",), jaso=("FC",), standards=("ISO GD",)),
    item("NGOL OUTBOARD SUPER", "M", 14, grades=("outboard two-stroke",), standards=("NMMA TC-3W",)),
    item("NGOL AGRO 20W40", "T", 15, "sae_gear", ("20W-40",), api=("CF-4", "CD", "CE", "SF", "SE"), api_gl=("GL-4",), acea=("E2",), standards=("Massey Ferguson CMS M1139/M1144/M1143/M1135", "Allison C-4", "MB 227.1", "ZF TE-ML 06B/06C", "Ford M2C 159 B/C", "New Holland MAT 3525/3526")),
    item("NGOL TRANSFLUID 807 S", "T", 15, grades=("UTTO",), api_gl=("GL-4",), standards=("ZF TE-ML 06B/07B", "Ford M2C 134D", "Case New Holland MAT 3525/3526", "John Deere J20C", "Massey Ferguson CMS M1143/M1135")),
    item("NGOL MAX VEDANTE DE RADIADOR", "TF", 20, grades=("radiator sealant",)),
    item("NGOL MAX ANTIFERRUGEM", "TF", 20, grades=("cooling-system emulsifiable corrosion inhibitor",)),
    item("NGOL MAX MULTIUSOS", "S", 20, grades=("multipurpose penetrating lubricant",)),
    item("NGOL FLUIDO DE TRAVÕES", "TF", 21, "dot", ("DOT 4",), standards=("SAE J1703", "FMVSS 116", "ISO 4925")),
    item("NGOL RADIADOR +", "TF", 21, grades=("ethylene-glycol coolant concentrate",)),
    item("NGOL CLEANOIL", "S", 21, grades=("flushing oil",)),
    item("NGOL CIRCULANTE", "H", 26, "iso_vg", ("150", "220", "320"), standards=("DIN 51524-2", "Denison HF-0/HF-1/HF-2", "Vickers M-2950-S/I-286-S", "US Steel 127/136")),
    item("NGOL HIDRO", "H", 26, "iso_vg", ("10", "15", "22", "32", "46", "68", "100"), standards=("DIN 51524-2", "Denison HF-0/HF-1/HF-2", "Vickers M-2950-S/I-286-S", "US Steel 127/136")),
    item("NGOL HIDROEX", "H", 27, "iso_vg", ("10", "15", "22", "32", "46", "68", "100"), standards=("DIN 51524-3", "Parker Hannifin France HF-0", "Vickers M-2950-S/I-286-S", "AFNOR E48-603", "GM LS-2/LH-03/LH-04/LH-06")),
    item("NGOL TURBO", "I", 27, "iso_vg", ("32", "46", "68", "100"), standards=("DIN 51515-1 L-TD", "DIN 51517-1/2", "ISO 6743-5", "ISO 8068", "Denison HF-0", "MIL-L-17672D", "AGMA 250.04 R&O")),
    item("NGOL ÁRTICO", "C", 28, "iso_vg", ("46", "68", "100"), standards=("refrigerants R12/R22/R502/R402a/R402b",)),
    item("NGOL COMPRESSOR", "C", 28, "iso_vg", ("32", "46", "68", "100", "150"), standards=("DIN 51506 VDL", "ISO/DP 6521 DAB/DAG")),
    item("NGOL GRENA", "I", 29, "iso_vg", ("68", "100", "150", "220", "320", "460", "680", "1500"), standards=("David Brown S1.53.101 E", "AGMA 9005-E02", "DIN 51517-3")),
    item("NGOL BERTA SV", "I", 29, grades=("open-gear black oil",)),
    item("NGOL TERM 32", "I", 30, "iso_vg", ("32",)),
    item("NGOL DIELÉCTRICO II", "I", 30, grades=("transformer insulating oil",), standards=("IEC 296:1982 Class II", "BS 148:1998 Class II", "ASTM D3487 Type I")),
    item("NGOL CYL G 460", "I", 30, grades=("compound steam-cylinder oil",)),
    item("NGOL CYL 1000", "I", 31, grades=("steam-cylinder oil",)),
    item("NGOL CORTE 37", "S", 31, grades=("neat cutting oil",)),
    item("NGOL CORTE S 33 R", "S", 31, grades=("soluble cutting oil",)),
    item("NGOL MARTEL", "I", 32, "iso_vg", ("100", "150"), standards=("David Brown S1.53.101 E", "AGMA 9005-E02", "DIN 51517-3")),
    item("NGOL TURBOGÁS", "M", 32, "sae_engine", ("40",), api=("CD",), standards=("Caterpillar", "Waukesha Co-Generation", "MWM-Deutz", "MAN MDE10/95")),
    item("NGOL LOCODIESEL", "M", 33, "sae_engine", ("40", "20W-40"), standards=("GE Generation IV/V Long Life LMOA",)),
    item("NGOL MAR 153/154", "M", 36, "sae_engine", ("30", "40"), api=("CF",), extras=({"base_number": "15"}, {"base_number": "15"})),
    item("NGOL MAR 303/304", "M", 36, "sae_engine", ("30", "40"), api=("CF",), extras=({"base_number": "30"}, {"base_number": "30"})),
    item("NGOL MAR 403/404", "M", 37, "sae_engine", ("30", "40"), api=("CF",), extras=({"base_number": "40"}, {"base_number": "40"})),
    item("NGOL MAR 405/705", "M", 37, "sae_engine", ("50", "50"), api=("CF",), extras=({"base_number": "40", "source_product_code": "405"}, {"base_number": "70", "source_product_code": "705"})),
    item("NGOL MAR D 30", "M", 37, "sae_engine", ("30",), api=("CD",), standards=("MIL-L-2104C",)),
    item("NGOL MULTIMAX 2", "G", 40, "nlgi", ("2",), extras=({"thickener": "lithium"},)),
    item("NGOL MULTIMAX SUPER", "G", 40, "nlgi", ("2",), extras=({"thickener": "lithium", "solid_lubricant": "molybdenum disulfide"},)),
    item("NGOL BENTOMAX", "G", 40, "nlgi", ("1",), extras=({"thickener": "non-metallic", "solid_lubricant": "molybdenum disulfide"},)),
    item("NGOL CALCIMAX", "G", 41, "nlgi", ("00", "0", "1", "2", "3"), extras=tuple({"thickener": "calcium complex"} for _ in range(5))),
    item("NGOL GRAFIMAX", "G", 41, "nlgi", ("3",), extras=({"thickener": "calcium", "solid_lubricant": "graphite"},)),
    item("NGOL LITIMAX EP", "G", 41, "nlgi", ("2", "3"), extras=({"thickener": "lithium"}, {"thickener": "lithium"})),
]

EXCLUDED_CAR_CARE = [
    "NGOL MAX TOPCYCL D",
    "NGOL MAX TOPCYCL G",
    "NGOL MAX BRILHO",
    "NGOL MAX PROTECTOR DE BATERIA",
    "NGOL MAX REPARADOR DE CORREIAS",
    "NGOL MAX SHAMPOO",
    "NGOL MAX LIMPA TABLIER",
    "NGOL MAX LIMPA JANTES",
    "NGOL MAX TAPA FUROS",
]


def main() -> None:
    assert len(PRODUCTS) == 55
    assert len(EXCLUDED_CAR_CARE) == 9
    records = []
    sequence = 0
    for product in PRODUCTS:
        for grade, extra in zip(product["grades"], product["extras"]):
            sequence += 1
            specs = {
                product["field"]: grade,
                "api": list(product["api"]),
                "api_gl": list(product["api_gl"]),
                "acea": list(product["acea"]),
                "jaso": list(product["jaso"]),
                "standards_and_approvals_source_reported": list(
                    product["standards"]
                ),
                "source_grade": grade,
                "source_printed_page": product["page"],
                "source_quality_flags": [
                    "official_44_page_national_manufacturer_catalog",
                    "page_by_page_indexed_pdf_fact_transcription",
                    "official_pdf_direct_download_http_403_at_snapshot",
                    "source_reported_specifications_not_independent_approvals",
                    "current_product_availability_unverified",
                    "no_price_stock_or_offer_inferred",
                ],
                **extra,
            }
            suffix = grade
            if extra.get("source_product_code"):
                suffix = extra["source_product_code"] + " SAE " + grade
            elif product["field"] == "sae_engine":
                suffix = "SAE " + grade
            elif product["field"] == "sae_gear":
                suffix = "SAE " + grade
            elif product["field"] == "iso_vg":
                suffix = "ISO VG " + grade
            elif product["field"] == "nlgi":
                suffix = "NLGI " + grade
            elif product["field"] == "dot":
                suffix = grade
            facts = {
                "name": product["name"],
                "family": product["family"],
                "page": product["page"],
                "field": product["field"],
                "grade": grade,
                "extra": extra,
                "api": product["api"],
                "api_gl": product["api_gl"],
                "acea": product["acea"],
                "jaso": product["jaso"],
                "standards": product["standards"],
            }
            records.append({
                "brand": "NGOL",
                "evidence_status": "official_national_manufacturer_catalog",
                "existing_target_source_id": "",
                "existing_target_source_record_id": "",
                "family_code": product["family"],
                "lifecycle_status": "official_catalog_current_status_unverified",
                "manufacturer": "Sonangol Distribuição e Comercialização",
                "market": "Angola",
                "product_name": f"{product['name']} {suffix}",
                "snapshot_date": SNAPSHOT_DATE,
                "source_facts_sha256": hashlib.sha256(
                    json.dumps(
                        facts, ensure_ascii=False, sort_keys=True
                    ).encode()
                ).hexdigest(),
                "source_id": SOURCE_ID,
                "source_product_name": product["name"],
                "source_record_id": f"NGOL-AO-{sequence:03d}",
                "source_url": SOURCE_URL,
                "specifications": specs,
            })
    assert len(records) == 107
    family_counts = dict(sorted(Counter(
        row["family_code"] for row in records
    ).items()))
    grade_counts = dict(sorted(Counter(
        next(
            key for key in (
                "sae_engine", "sae_gear", "iso_vg", "nlgi", "dot",
                "source_grade",
            )
            if key in row["specifications"]
        )
        for row in records
    ).items()))
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(payload, encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "status": "ok",
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "official_pdf_pages": 44,
        "catalog_product_series": len(PRODUCTS) + len(EXCLUDED_CAR_CARE),
        "target_scope_series": len(PRODUCTS),
        "excluded_non_lubricant_car_care_series": EXCLUDED_CAR_CARE,
        "identity_rows": len(records),
        "family_identity_counts": family_counts,
        "grade_field_counts": grade_counts,
        "official_pdf_direct_download_status": "HTTP 403",
        "official_pdf_sha256": None,
        "official_pdf_sha256_note": (
            "Unavailable because the official host blocks direct retrieval; "
            "the PDF URL, page number and normalized source-fact hash are kept."
        ),
        "normalized_output_sha256": hashlib.sha256(
            payload.encode()
        ).hexdigest(),
        "offers_created": 0,
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "series": len(PRODUCTS),
        "identity_rows": len(records),
        "family_counts": family_counts,
        "output_sha256": report["normalized_output_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
