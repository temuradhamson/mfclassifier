#!/usr/bin/env python3
"""Build ANCAP Uruguay's 2024–2026 lubricant and specialties catalog.

The official catalog is a compact spread-based PDF.  Its 56 commercial product
families are represented below as an audited matrix and expanded only where the
source explicitly publishes multiple SAE, ISO VG, NLGI or proprietary grades.
Marketing prose and inferred approvals are deliberately excluded.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/uruguay-ancap-current-lubricants.jsonl"
REPORT = ROOT / "data/uruguay-ancap-current-lubricants-report.json"
SOURCE_ID = "URUGUAY_ANCAP_CURRENT_LUBRICANT_CATALOG"
CATALOG_PAGE_URL = "https://www.ancap.com.uy/5990/4/catalogo-lubricantes.html"
CATALOG_URL = (
    "https://www.ancap.com.uy/innovaportal/file/5990/1/"
    "catalogo-productos-ancap---lubricantes-y-especialidades-2024---2026-v5.pdf"
)
SNAPSHOT_DATE = "2026-07-23"
EXPECTED_CATALOG_SHA256 = "a48cfd55716f8653ccd3f0bb34dc0d07a43eddf319b902c3a87aa40c151cd2a7"
UA = "MFClassifier evidence catalog/1.0"


def p(
    name: str,
    family: str,
    line: str,
    grades: list[dict] | None = None,
    *,
    page: str = "",
    **technical: object,
) -> dict:
    return {
        "name": name,
        "family_code": family,
        "product_line": line,
        "grades": grades or [{}],
        "page": page,
        "technical": technical,
    }


PRODUCTS = [
    # Passenger-car and heavy-duty engine oils.
    p("SYNTH MILENIUM", "M", "automotive_engine", [{"sae_engine": "5W-30"}],
      api=["SP"], ilsac=["GF-6A"], performance=["API SP Resource Conserving", "GM dexos1 Gen3"]),
    p("SYNTH", "M", "automotive_engine", [{"sae_engine": "5W-40"}],
      api=["SN", "CF"], acea=["A3/B4-21"]),
    p("SUPER-A MAX", "M", "automotive_engine", [{"sae_engine": "10W-40"}],
      api=["SN", "CF"], acea=["A3/B4-21"],
      performance=["MB 229.3", "VW 501.01", "VW 505.00", "PSA B71 2300"]),
    p("SUPER-A", "M", "automotive_engine", [{"sae_engine": "20W-50"}],
      api=["SL", "CF"], acea=["A3/B3-16"]),
    p("LUBAN PLUS", "M", "automotive_engine",
      [{"sae_engine": "30"}, {"sae_engine": "40"}], api=["SF", "CF"]),
    p("ANCAP RACING", "M", "automotive_engine", [{"sae_engine": "10W-60"}],
      page="https://www.ancap.com.uy/21049/1/ancap-racing-10w60.html",
      api=["SP"], acea=["A3/B4-21"], performance=["FIAT 9.55535-H3"]),
    p("TURBO SYNTH", "M", "heavy_duty_engine", [{"sae_engine": "10W-40"}],
      api=["CK-4"], acea=["E8-22"], jaso=["DH-2"]),
    p("SYNTH DISEL PRO", "M", "heavy_duty_engine", [{"sae_engine": "5W-30"}],
      api=["SN", "CF"], acea=["C3-21"],
      performance=["GM dexos2", "MB 229.31", "MB 229.51", "MB 226.5",
                   "VW 502.00", "VW 505.00", "Renault RN0700", "Renault RN0710"]),
    p("TURBODISEL", "M", "heavy_duty_engine", [{"sae_engine": "15W-40"}],
      api=["CI-4", "SL"], acea=["E7-16"],
      performance=["DTFR 15B110", "MAN M 3275", "Volvo VDS-3", "MTU Type 2.0",
                   "Mack EO-M Plus", "Mack EO-N", "Cummins CES 20077",
                   "Cummins CES 20078", "Caterpillar ECF-1-a", "Caterpillar ECF-2"]),
    p("SUPERDISEL PLUS", "M", "heavy_duty_engine", [{"sae_engine": "15W-40"}],
      api=["CH-4", "SJ"], acea=["E7-22"]),
    p("SUPERDISEL", "M", "heavy_duty_engine",
      [{"sae_engine": grade} for grade in ("10W", "30", "40", "50")],
      api=["CF", "SF"]),

    # Automotive gears, transmissions and tractor fluids.
    p("TRANSMILUB GL-3", "T", "automotive_gear", [{"sae_gear": "80W-90"}],
      page="https://www.ancap.com.uy/8282/4/transmilub-gl-3.html", api_gl=["GL-3"]),
    p("TRANSMILUB GL-4", "T", "automotive_gear",
      [{"sae_gear": "80W"}, {"sae_gear": "80W-90"}],
      page="https://www.ancap.com.uy/1661/4/transmilub-gl-4.html", api_gl=["GL-4"]),
    p("LUBRIDIF PRO", "T", "automotive_gear", [{"sae_gear": "80W-90"}],
      page="https://www.ancap.com.uy/1658/5/lubridif--pro-80w90.html",
      api_gl=["GL-5"], performance=["DTFR 12B110"]),
    p("LUBRICAMBIO LS", "T", "automotive_gear",
      [{"sae_gear": "80W-90"}, {"sae_gear": "85W-140"}], api_gl=["GL-5"]),
    p("LUBRICAMBIO DC", "T", "automotive_gear",
      [{"sae_gear": "90"}, {"sae_gear": "140"}],
      page="https://www.ancap.com.uy/1655/4/lubricambio-dc.html", api_gl=["GL-1"]),
    p("LUBRICAMBIO EP", "T", "automotive_gear",
      [{"sae_gear": "80W-90"}, {"sae_gear": "85W-140"}],
      page="https://www.ancap.com.uy/1656/4/lubricambio-ep.html",
      api_gl=["GL-5", "MT-1"]),
    p("TRACTODINA", "T", "tractor_transmission", [{"sae_gear": "10W-30"}],
      api_gl=["GL-4"], performance=["UTTO", "THF"]),
    p("CVT TRACTODINA PLUS", "T", "tractor_transmission",
      performance=["Case New Holland MAT 3540"]),
    p("FLUDINA", "T", "automatic_transmission",
      atf=["GM Dexron III H", "Ford Mercon", "Allison C-4", "Allison TES-389"],
      jaso=["M315-2013 1A"]),
    p("LUBRIC TO-4", "T", "powertrain",
      [{"sae_gear": grade} for grade in ("10W", "30", "50")],
      performance=["Caterpillar TO-4", "Allison C-4", "Allison C-3", "Allison C-2", "Komatsu"]),

    # Coolants and brake fluid.
    p("GLICOL 100% CONCENTRADO", "TF", "coolant",
      coolant_type="ethylene glycol concentrate",
      performance=["ASTM D6210", "ASTM D4985", "ASTM D3306", "TMC RP 329", "SAE J1034"]),
    p("LÍQUIDO REFRIGERANTE GLICOL AL 50%", "TF", "coolant",
      coolant_type="ethylene glycol 50% premix",
      performance=["ASTM D6210", "ASTM D4985", "ASTM D3306", "ASTM D5345",
                   "TMC RP 329", "SAE J1034"]),
    p("LÍQUIDO PARA FRENOS DOT 4", "TF", "brake_fluid",
      brake_fluid_class=["DOT 4"],
      performance=["FMVSS 116", "SAE J1704", "SAE J1703", "ISO 4925 Class 3", "ISO 4925 Class 4"]),

    # Motorcycle, nautical and garden oils.
    p("MOTO PLUS 4T", "M", "motorcycle", [{"sae_engine": "5W-40"}],
      api=["SN"], jaso=["MA2"]),
    p("MOTO SUPER 4T", "M", "motorcycle", [{"sae_engine": "10W-40"}],
      api=["SN"], jaso=["MA2"]),
    p("MOTOLUB 4T", "M", "motorcycle", [{"sae_engine": "20W-50"}],
      api=["SL"], jaso=["MA2"]),
    p("LUBRICICLO 2T", "M", "two_stroke", api=["TC+"], jaso=["FD"], performance=["ISO-L-EGD"]),
    p("LUBRIMOTO 2T", "M", "two_stroke", api=["TC+"], jaso=["FB"]),
    p("NÁUTICO 4T", "M", "marine_recreational", [{"sae_engine": "10W-40"}],
      api=["SJ"], nmma=["FC-W"]),
    p("NÁUTICO 2T", "M", "marine_recreational", nmma=["TC-W3", "TC-WII", "TC-W"]),
    p("JARDÍN 4T", "M", "garden", [{"sae_engine": "10W-30"}]),
    p("JARDÍN 2T", "M", "garden"),

    # Greases.
    p("MULTILUB-A", "G", "grease", [{"nlgi": "2"}, {"nlgi": "3"}]),
    p("MULTILUB-B", "G", "grease", [{"nlgi": "2"}]),
    p("MULTILUB-EP", "G", "grease", [{"nlgi": "2"}]),
    p("PERDURALUB-L", "G", "grease", [{"nlgi": "2"}]),
    p("MULTILUB SPEED 2", "G", "grease", [{"nlgi": "2"}]),
    p("ANCAPLEX EP", "G", "grease", [{"nlgi": "2"}]),

    # Industrial oils.
    p("TRELUB AD", "H", "hydraulic",
      [{"iso_vg": grade} for grade in ("15", "32", "46", "68", "100", "150", "220", "320")],
      din=["DIN 51524-2"],
      performance=["AFNOR NF E 48-603 HM", "Denison HF-0", "Denison HF-1", "Denison HF-2",
                   "Eaton Vickers M-2950-S", "Cincinnati P-68", "Cincinnati P-69", "Cincinnati P-70"]),
    p("TRELUB H68", "H", "hydraulic", [{"iso_vg": "68"}], din=["DIN 51524-2"]),
    p("HIDRANCAP HVI", "H", "hydraulic",
      [{"iso_vg": grade} for grade in ("15", "32", "46", "68")],
      din=["DIN 51524-3 HVLP"], performance=["AFNOR NF E 48-603 HV", "ISO 6743-4 HV"]),
    p("LUBRITEX", "I", "industrial", [{"iso_vg": "68"}, {"iso_vg": "100"}]),
    p("LUBRICANTE BV", "I", "vacuum_pump",
      din=["DIN 51506 VDL", "DIN 51515-1"],
      performance=["AIST 120", "Fives P-54", "ISO 6743-3A DAH"]),
    p("CELUB EP", "I", "industrial_gear",
      [{"iso_vg": grade} for grade in ("68", "100", "150", "220", "320", "680")],
      din=["DIN 51517-3"],
      performance=["AGMA 9005-E02", "AIST 224", "David Brown S1.53.101", "ISO 12925-1 CKC/CKD"]),
    p("ENGRALUB SINT", "I", "industrial_gear", [{"iso_vg": "220"}],
      din=["DIN 51517-3 CLP"],
      performance=["U.S. Steel 224", "AGMA 9005-E02", "Flender micropitting"]),
    p("DIELECTROL-X", "E", "transformer_oil",
      performance=["IEC 60296 Ed. 4", "ASTM D1275 Method B", "DIN 51353", "IEC 62535"]),
    p("INCOLUB", "I", "food_grade_white_oil",
      performance=["NSF H1", "NSF H2", "NSF 3H", "FDA"]),
    p("APROL", "I", "process_oil"),
    p("CILINDROLUB", "I", "steam_cylinder", [{"viscosity_source_reported": "C460"}]),
    p("TURBOLUB", "U", "turbine",
      [{"iso_vg": grade} for grade in ("32", "46", "68")],
      din=["DIN 51506 VDL", "DIN 51515 Part I/II"],
      performance=["Fives P-38", "Fives P-55", "Siemens", "General Electric"]),
    p("VISCODIS", "I", "circulating", [{"iso_vg": "100"}], api=["SA"]),

    # Metalworking and commercial marine engine oils.
    p("ANTICORROSIVO S", "I", "metalworking"),
    p("HERCOLUB", "I", "metalworking"),
    p("SOLUBLE 11", "I", "metalworking"),
    p("ANCAP MARINO", "M", "commercial_marine",
      [{"marine_grade_source_reported": grade} for grade in ("3012", "3015", "4015", "4020")],
      performance=["MIL-L-2104B", "MIL-L-2104C", "Series 3", "Caterpillar 1G-2", "MWM B"]),
]


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def grade_label(grade: dict) -> str:
    if grade.get("sae_engine"):
        return f"SAE {grade['sae_engine']}"
    if grade.get("sae_gear"):
        return f"SAE {grade['sae_gear']}"
    if grade.get("iso_vg"):
        return f"ISO VG {grade['iso_vg']}"
    if grade.get("nlgi"):
        return f"NLGI {grade['nlgi']}"
    return grade.get("viscosity_source_reported") or grade.get("marine_grade_source_reported") or ""


def main() -> None:
    catalog_bytes = get(CATALOG_URL)
    catalog_sha = sha256(catalog_bytes)
    if catalog_sha != EXPECTED_CATALOG_SHA256:
        raise RuntimeError(f"ANCAP catalog changed: expected {EXPECTED_CATALOG_SHA256}, got {catalog_sha}")
    if not catalog_bytes.startswith(b"%PDF"):
        raise RuntimeError("ANCAP catalog response is not a PDF")

    rows = []
    for product_index, product in enumerate(PRODUCTS, 1):
        for grade_index, grade in enumerate(product["grades"], 1):
            technical = {
                "sae_engine": grade.get("sae_engine", ""),
                "sae_gear": grade.get("sae_gear", ""),
                "iso_vg": grade.get("iso_vg", ""),
                "nlgi": grade.get("nlgi", ""),
                "viscosity_source_reported": grade.get("viscosity_source_reported", ""),
                "marine_grade_source_reported": grade.get("marine_grade_source_reported", ""),
                "api": product["technical"].get("api", []),
                "api_gl": product["technical"].get("api_gl", []),
                "acea": product["technical"].get("acea", []),
                "ilsac": product["technical"].get("ilsac", []),
                "jaso": product["technical"].get("jaso", []),
                "nmma": product["technical"].get("nmma", []),
                "atf": product["technical"].get("atf", []),
                "brake_fluid_class": product["technical"].get("brake_fluid_class", []),
                "din": product["technical"].get("din", []),
                "performance": product["technical"].get("performance", []),
                "coolant_type": product["technical"].get("coolant_type", ""),
            }
            label = grade_label(grade)
            name = product["name"] if len(product["grades"]) == 1 else f"{product['name']} — {label}"
            rows.append({
                "source_id": SOURCE_ID,
                "source_record_id": f"ANCAP-UY-{product_index:02d}-{grade_index:02d}",
                "market": "Uruguay",
                "manufacturer": "Administración Nacional de Combustibles, Alcohol y Pórtland (ANCAP)",
                "brand": "ANCAP",
                "product_name": name,
                "product_name_source": product["name"],
                "product_line": product["product_line"],
                "family_code": product["family_code"],
                "technical": technical,
                "lifecycle_status": "current_official_catalog_2024_2026",
                "evidence_status": "official_state_owned_manufacturer_product_catalog",
                "snapshot_date": SNAPSHOT_DATE,
                "source_url": product["page"] or CATALOG_PAGE_URL,
                "catalog_page_url": CATALOG_PAGE_URL,
                "catalog_url": CATALOG_URL,
                "catalog_sha256": catalog_sha,
                "source_quality_flags": [
                    "official_product_identity_and_specifications",
                    "multi_grade_families_expanded_only_on_explicit_source_grades",
                    "catalog_presence_not_independent_performance_approval",
                    "proprietary_marine_and_cylinder_grades_not_reinterpreted",
                    "marketing_prose_excluded",
                ],
            })

    if len(PRODUCTS) != 56 or len(rows) != 88:
        raise RuntimeError(f"ANCAP audit matrix drift: {len(PRODUCTS)} families, {len(rows)} variants")

    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "catalog_product_families": len(PRODUCTS),
        "normalized_product_variants": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "product_lines": dict(sorted(Counter(row["product_line"] for row in rows).items())),
        "catalog_url": CATALOG_URL,
        "catalog_sha256": catalog_sha,
        "normalized_output_sha256": sha256(OUT.read_bytes()),
        "audit_boundary": (
            "The official 2024–2026 ANCAP catalog is the identity and specification source. "
            "Multiple grades are expanded only when explicitly published; approvals are "
            "source-reported claims and not independently certified by this dataset."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
