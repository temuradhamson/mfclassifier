#!/usr/bin/env python3
"""Normalize product-grade facts from IMCA's December 2025 Mobil catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/dominican-republic-imca-mobil-2025-products.jsonl"
REPORT = ROOT / "data/dominican-republic-imca-mobil-2025-report.json"
SOURCE_ID = "DOMINICAN_REPUBLIC_IMCA_MOBIL_2025_CATALOG"
SOURCE_URL = (
    "https://lubricantesmobil.imcadom.com/wp-content/uploads/2025/12/"
    "0008982IMCARD_Catalogo-Completo.pdf"
)
SOURCE_PDF_SHA256 = (
    "9e7c730837583042997e2a9c32ba9f4424bc53a025e2d8bc4bf6f4535aad50ab"
)
SOURCE_PDF_BYTES = 15_201_268


def product(
    name: str,
    page: int,
    family: str,
    category: str,
    *,
    sae_engine: str = "",
    sae_gear: str = "",
    api: tuple[str, ...] = (),
    api_gl: tuple[str, ...] = (),
    acea: tuple[str, ...] = (),
    jaso: tuple[str, ...] = (),
    performance: tuple[str, ...] = (),
) -> dict:
    return {
        "brand": "MOBIL",
        "product_name": name,
        "family_code": family,
        "source_category": category,
        "source_page": page,
        "technical": {
            "sae_engine": sae_engine,
            "sae_gear": sae_gear,
            "api": list(api),
            "api_gl": list(api_gl),
            "acea": list(acea),
            "jaso": list(jaso),
            "performance": list(performance),
        },
    }


P = product
PRODUCTS = [
    P("Mobil 1 0W-16", 3, "M", "passenger_car_engine_oil", sae_engine="0W-16",
      api=("SN", "SN PLUS", "SP"), performance=("API SP Resource Conserving",)),
    P("Mobil 1 0W-20", 3, "M", "passenger_car_engine_oil", sae_engine="0W-20",
      api=("SJ", "SL", "SM", "SN", "SN PLUS", "SP"),
      performance=("API SN Resource Conserving", "API SN PLUS Resource Conserving", "API SP Resource Conserving")),
    P("Mobil 1 0W-40", 3, "M", "passenger_car_engine_oil", sae_engine="0W-40",
      api=("CF", "SJ", "SL", "SM", "SN")),
    P("Mobil 1 5W-20", 3, "M", "passenger_car_engine_oil", sae_engine="5W-20",
      api=("CF", "SJ", "SL", "SM", "SN", "SN PLUS", "SP"),
      performance=("API SP Resource Conserving",)),
    P("Mobil 1 5W-50", 3, "M", "passenger_car_engine_oil", sae_engine="5W-50",
      api=("CF", "SJ", "SL", "SM", "SN", "SN PLUS", "SP")),
    P("Mobil 1 10W-30", 3, "M", "passenger_car_engine_oil", sae_engine="10W-30",
      api=("SJ", "SL", "SM", "SN", "SN PLUS", "SP"),
      performance=("API SP Resource Conserving",)),
    P("Mobil 1 ESP Formula 0W-30", 4, "M", "passenger_car_engine_oil",
      sae_engine="0W-30", api=("SL", "SN", "SN PLUS", "SP"), acea=("C3",)),
    P("Mobil 1 ESP Formula 5W-30", 4, "M", "passenger_car_engine_oil",
      sae_engine="5W-30", api=("SJ", "SL", "SM", "SN", "SN PLUS", "SP"),
      acea=("C2", "C3")),
    P("Mobil 1 Turbo Diesel Truck 5W-40", 5, "M", "heavy_duty_engine_oil",
      sae_engine="5W-40",
      api=("CG-4", "CH-4", "CI-4", "CI-4 PLUS", "CJ-4", "CK-4", "SL", "SM", "SN")),
    *[
        P(f"Mobil Full Synthetic {grade}", 6, "M", "passenger_car_engine_oil",
          sae_engine=grade, api=("SJ", "SL", "SM", "SN", "SP"),
          performance=("API SN Resource Conserving", "API SP Resource Conserving"))
        for grade in ("0W-20", "5W-20", "5W-30")
    ],
    *[
        P(f"Mobil Super {grade}", 7, "M", "passenger_car_engine_oil",
          sae_engine=grade, api=("SJ", "SL", "SM", "SN"))
        for grade in ("5W-20", "5W-30", "10W-30")
    ],
    P("Mobil Super 10W-40", 7, "M", "passenger_car_engine_oil",
      sae_engine="10W-40", api=("SJ", "SL", "SM")),
    *[
        P(f"Mobil Special {grade}", 8, "M", "passenger_car_engine_oil",
          sae_engine=grade, api=("SJ", "SL", "SM", "SN", "SN PLUS", "SP"))
        for grade in ("5W-20", "5W-30", "10W-30", "20W-50")
    ],
    *[
        P(f"Mobil Special Monograde {grade}", 9, "M", "passenger_car_engine_oil",
          sae_engine=grade, api=("SL",))
        for grade in ("40", "50")
    ],
    P("Mobil Delvac 1 ESP 5W-40", 10, "M", "heavy_duty_engine_oil",
      sae_engine="5W-40",
      api=("CG-4", "CF-4", "CF", "CI-4 PLUS", "CI-4", "CH-4", "CK-4", "SL", "SJ")),
    P("Mobil Delvac Extreme 10W-30", 11, "M", "heavy_duty_engine_oil",
      sae_engine="10W-30", api=("CH-4", "CI-4", "CI-4 PLUS", "CJ-4", "CK-4"),
      acea=("E7", "E11"), jaso=("DH-2",)),
    P("Mobil Delvac Extreme 15W-40", 11, "M", "heavy_duty_engine_oil",
      sae_engine="15W-40",
      api=("CH-4", "CI-4", "CI-4 PLUS", "CJ-4", "CK-4", "SL", "SM"),
      acea=("E7", "E11"), jaso=("DH-2",)),
    P("Mobil Delvac 1300 Super 15W-40", 12, "M", "heavy_duty_engine_oil",
      sae_engine="15W-40",
      api=("CH-4", "CI-4", "CI-4 PLUS", "CJ-4", "CK-4", "SN"),
      acea=("E7", "E11"), jaso=("DH-2",)),
    P("Mobil Delvac MX F2 15W-40", 13, "M", "heavy_duty_engine_oil",
      sae_engine="15W-40",
      api=("CF", "CF-4", "CG-4", "CH-4", "CI-4", "CI-4 PLUS", "SJ", "SL"),
      acea=("E7",)),
    P("Mobil Delvac Legend 15W-40", 14, "M", "heavy_duty_engine_oil",
      sae_engine="15W-40", api=("CH-4", "SJ")),
    P("Mobil Delvac Legend 20W-50", 14, "M", "heavy_duty_engine_oil",
      sae_engine="20W-50", api=("CH-4",)),
    P("Mobil Delvac 1220", 15, "M", "heavy_duty_engine_oil",
      sae_engine="20", api=("CF", "SF")),
    *[
        P(name, 15, "M", "heavy_duty_engine_oil", sae_engine=grade,
          api=("CF-2", "CF", "SF"))
        for name, grade in (
            ("Mobil Delvac 1230", "30"),
            ("Mobil Delvac 1240", "40"),
            ("Mobil Delvac 1250", "50"),
        )
    ],
    P("Mobil 1 Synthetic Gear Lubricant LS 75W-90", 16, "T",
      "automotive_gear_oil", sae_gear="75W-90", api_gl=("GL-5",)),
    P("Mobil Delvac Modern Axle Oil 80W-90", 17, "T",
      "automotive_gear_oil", sae_gear="80W-90", api_gl=("GL-5",)),
    P("Mobil Delvac Modern Axle Oil 85W-140", 17, "T",
      "automotive_gear_oil", sae_gear="85W-140", api_gl=("GL-5",)),
    P("Mobil 1 Synthetic ATF", 18, "T", "automatic_transmission_fluid",
      performance=("Allison C-4", "Ford MERCON", "Ford MERCON V", "GM DEXRON",
                   "GM DEXRON II", "GM DEXRON IID", "GM DEXRON IIE",
                   "GM DEXRON IIIG", "GM DEXRON IIIH", "JASO 1-A", "Volvo 97340")),
    P("Mobil CVTF Multi-Vehicle", 19, "T", "continuously_variable_transmission_fluid",
      performance=("Audi", "BMW", "Jeep", "Chrysler", "Mini Cooper", "Renault",
                   "Volvo", "VW", "Honda", "Hyundai", "Lexus", "Mazda",
                   "Mitsubishi", "Nissan", "Subaru", "Suzuki", "Toyota")),
    P("Mobil ATF 3309", 20, "T", "automatic_transmission_fluid",
      performance=("AUDI G-055-025-A2", "GM 9986195", "TOYOTA T-IV", "Ford WSS-M2C924-A")),
    P("Mobil ATF D/M", 21, "T", "automatic_transmission_fluid",
      performance=("Allison C-4", "Ford MERCON", "GM DEXRON IIIH")),
    *[
        P(f"Mobil 1 Racing 4T {grade}", 22, "M", "motorcycle_engine_oil",
          sae_engine=grade, api=("SH",), jaso=("MA 2011", "MA2 2011"))
        for grade in ("10W-40", "15W-50")
    ],
    P("Mobil 1 V-Twin 20W-50", 23, "M", "motorcycle_engine_oil",
      sae_engine="20W-50", api=("SJ", "SH", "SG", "CF")),
    P("Mobil Super Moto 4T 20W-50", 24, "M", "motorcycle_engine_oil",
      sae_engine="20W-50", api=("SL",)),
    P("Mobil Super Moto 4T 10W-40", 25, "M", "motorcycle_engine_oil",
      sae_engine="10W-40", api=("SL",), jaso=("MA", "MA2")),
    P("Mobil Super Moto 4T 15W-50", 26, "M", "motorcycle_engine_oil",
      sae_engine="15W-50", api=("SL",), jaso=("MA", "MA2")),
    P("Mobil Super Moto Scooter MX 10W-40", 27, "M", "scooter_engine_oil",
      sae_engine="10W-40", api=("SL",), jaso=("MB",)),
    P("Mobil Outboard Plus", 28, "M", "two_stroke_marine_engine_oil",
      api=("TC",), performance=("NMMA TC-W", "NMMA TC-WII", "NMMA TC-W3")),
    P("Mobil Delvac Extended Life Coolant", 29, "TF", "engine_coolant",
      performance=("ASTM D6210", "Detroit Fluids 93K217", "MTU 5048",
                   "ASTM D7583", "John Deere H24A1", "John Deere H24C1",
                   "Navistar CEMS-B1 Type IIIa")),
    P("Mobil Heavy Duty SCA Pre-charged 50/50", 30, "TF", "engine_coolant",
      performance=("Chrysler MS7170", "ASTM D3306", "ASTM D4340", "ASTM D4985",
                   "ASTM D6210", "Cummins 90T8-4", "GM 1825M", "GM 1899M",
                   "Ford", "Caterpillar", "Detroit Diesel 7SE298",
                   "Freightliner 48-22880", "John Deere", "Mack Truck", "Volvo", "MTU")),
    P("Mobil Permazone 50/50 Antifreeze", 31, "TF", "engine_coolant",
      performance=("ASTM D3306", "ASTM D4340", "ASTM D4985", "ASTM D6210",
                   "ABNT NBR 13705", "Caterpillar CAT ELC EC-1",
                   "Chrysler MS7170", "Ford", "MTU MTL 5048")),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf",
        type=Path,
        help="Optional downloaded official PDF for byte-size and SHA verification.",
    )
    args = parser.parse_args()
    if args.pdf:
        payload = args.pdf.read_bytes()
        assert len(payload) == SOURCE_PDF_BYTES
        assert hashlib.sha256(payload).hexdigest() == SOURCE_PDF_SHA256

    assert len(PRODUCTS) == 51
    assert len({
        (item["product_name"], item["source_page"])
        for item in PRODUCTS
    }) == len(PRODUCTS)
    rows = []
    for index, item in enumerate(PRODUCTS, 1):
        rows.append({
            **item,
            "source_id": SOURCE_ID,
            "source_record_id": f"IMCA-MOBIL-2025-{index:03d}",
            "source_url": SOURCE_URL,
            "source_pdf_sha256": SOURCE_PDF_SHA256,
            "source_pdf_creation_date": "2025-12-09",
            "source_pdf_pages": 32,
            "market": "Dominican Republic",
            "snapshot_date": str(date.today()),
            "lifecycle_status": "listed_in_official_december_2025_country_catalog",
            "scope_status": "global_mobil_identity_dominican_republic_availability",
            "source_quality_flags": [
                "official_authorized_distributor_catalog",
                "product_grade_split_only_when_catalog_table_explicit",
                "source_reported_specifications_not_independent_approvals",
                "no_unprinted_grade_or_specification_inference",
            ],
        })

    rendered = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )
    OUT.write_text(rendered, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_pdf_sha256": SOURCE_PDF_SHA256,
        "source_pdf_bytes": SOURCE_PDF_BYTES,
        "source_pdf_creation_date": "2025-12-09",
        "source_pdf_pages": 32,
        "snapshot_date": str(date.today()),
        "product_grade_rows": len(rows),
        "source_pages_with_products": 29,
        "families": dict(sorted(Counter(
            row["family_code"] for row in rows
        ).items())),
        "categories": dict(sorted(Counter(
            row["source_category"] for row in rows
        ).items())),
        "normalized_output_sha256": hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "Dominican Republic availability evidence for global Mobil "
            "identities; no country-specific manufacturer masters are created "
            "before strict matching."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
