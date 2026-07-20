#!/usr/bin/env python3
"""Normalize named lubricants and fluids in MAN's current service recommendation."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "man-service-products.jsonl"
REPORT = ROOT / "data" / "man-service-products-report.json"
SNAPSHOT_DATE = "2026-07-20"
DOCUMENT_DATE = "2026-04"
PDF_URL = "https://public.man.eu/media/service/asp/media/en/927247.pdf?filename=Maintenance+and+service+product+recommendations+for+trucks"
COOLANT_PAGE_URL = "https://public.man.eu/portal/asp/en/partsnequip/contentnav_copy_67/3_136/article_page_703"
COOLANT_API_URL = "https://public.man.eu/content/service/asp/en/partsnequip/contentnav_copy_67/3_136/article_page_703"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"


def product(brand: str, name: str, family: str, pages: list[int], application: str, **specifications) -> dict:
    return {
        "brand": brand,
        "manufacturer": brand,
        "product_name": name,
        "family_code": family,
        "source_pages": pages,
        "application": application,
        "specifications": specifications,
    }


PRODUCTS = [
    product("MAN", "Paragon MAN 3977 5W-20", "M", [24], "diesel engines", sae_engine="5W-20", man_standard="MAN 3977"),
    product("MAN", "Excellence MAN 3677 5W-30", "M", [24], "diesel engines", sae_engine="5W-30", man_standard="MAN 3677"),
    product("MAN", "Flexor MAN 341 Z5 75W-80", "T", [24], "manual gearboxes", sae_gear="75W-80", man_standard="MAN 341 Z5"),
    product("MAN", "Nexus MAN 342 S1 75W-90", "T", [25], "driven axles and transfer cases", sae_gear="75W-90", man_standard="MAN 342 S1"),
    product("Chevron", "Cetus PAO 46", "C", [33], "electric air compressor", iso_vg="46", base_oil="PAO"),
    product("MAN", "MAN Genuine anti-corrosion and anti-freeze liquid", "TF", [34], "engine cooling systems", man_standard="MAN 324 Si-OAT", vw_standard="VW TL 774-G", temperature_min_c=-37),
    product("BP", "Energol HLP-HM 15", "H", [44], "mechanical cab tilt mechanism", iso_vg="15", temperature_min_c=-25, temperature_max_c=80),
    product("Gulf", "Harmony HVI Plus 15", "H", [44], "mechanical cab tilt mechanism", iso_vg="15", temperature_min_c=-25, temperature_max_c=80),
    product("TotalEnergies", "ELFMATIC G2", "T", [44], "mechanical cab tilt mechanism", temperature_min_c=-25, temperature_max_c=80),
    product("Chevron", "Rando HDZ 15", "H", [44], "mechanical cab tilt mechanism", iso_vg="15", temperature_min_c=-30, temperature_max_c=80),
    product("Mobil", "Univis HVI 26", "H", [44], "mechanical cab tilt mechanism", temperature_min_c=-30, temperature_max_c=80),
    product("Shell", "Tellus S2 V 15", "H", [44], "mechanical cab tilt mechanism", iso_vg="15", temperature_min_c=-30, temperature_max_c=80),
    product("Chevron", "Hydraulic Oil 5606A", "H", [44], "electric cab tilt mechanism", temperature_min_c=-40, temperature_max_c=80),
    product("Shell", "AeroShell Fluid 41", "H", [44], "electric cab tilt mechanism", temperature_min_c=-40, temperature_max_c=80),
    product("MAHLE", "PAG Oil SP-A2", "C", [48], "air-conditioning refrigerant compressor", iso_vg="46"),
    product("Sanden", "SP 10 PAG Oil", "C", [48], "air-conditioning refrigerant compressor"),
    product("TCCI", "PAG 46", "C", [48], "air-conditioning refrigerant compressor", iso_vg="46"),
    product("WD-40", "WD-40 Multi-Use Product", "S", [49], "trailer coupling contact surfaces", function="creep oil with corrosion protection"),
    product("Castrol", "Olista Longtime 3 EP", "G", [49, 50], "trailer coupling and gearbox input shaft", nlgi="3"),
    product("FUCHS", "Renocal FN 745/94", "G", [49], "vehicle door lock lubrication"),
    product("Castrol", "Optitemp TT1 Spray", "G", [49], "vehicle door lock lubrication", nlgi="1/2"),
    product("FUCHS", "Renolit LX-PEP 1/2", "G", [49], "slide and propshaft joint grease nipples", nlgi="1/2"),
    product("Shell", "Retinax LX2", "G", [49], "slide and propshaft joint grease nipples", nlgi="2"),
    product("Shell", "Gadus S3 V220C 2", "G", [49], "slide and propshaft joint grease nipples", nlgi="2"),
    product("FUCHS", "Service Free 2 GWB", "G", [49], "slide and propshaft joint grease nipples", nlgi="2"),
    product("FUCHS", "Renolit LX-NHU 2", "G", [50], "low-maintenance brake camshaft", nlgi="2", man_standard="MAN 284 Li-H 2"),
    product("FUCHS", "Renolit W2", "G", [50], "low-temperature periodic lubrication", nlgi="2", temperature_min_c=-50),
    product("TC", "High-Temperature Lubricant 13-047", "G", [51], "brake shoe pins, rollers, nozzle holders and exhaust mounting bolts", temperature_max_c=200),
    product("Castrol", "Molub-Alloy Paste MP 3", "G", [51], "constant-velocity shafts"),
    product("FUCHS", "Renolit LX-OTP 2", "G", [51], "steering knuckle bearing", nlgi="2"),
    product("JOST", "JHS 2020 B", "G", [51], "integrated fifth-wheel lubrication system"),
    product("HOLLAND", "RECOLUBE BIOPOWER SKX 023", "G", [51], "integrated fifth-wheel lubrication system"),
]


SOURCE_NAME_OVERRIDES = {
    "WD-40 Multi-Use Product": "WD-40",
    "High-Temperature Lubricant 13-047": "TC high-temperature",
    "RECOLUBE BIOPOWER SKX 023": "HOLLAND RECOLUBE",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> None:
    pdf_payload = fetch(PDF_URL)
    coolant_payload = fetch(COOLANT_API_URL)
    reader = PdfReader(BytesIO(pdf_payload))
    assert len(reader.pages) == 150
    page_text = {page: reader.pages[page - 1].extract_text(extraction_mode="layout") or "" for page in range(1, 151)}
    assert "issuedapril2026" in normalized(page_text[24])
    coolant_data = json.loads(coolant_payload)
    coolant_text = " ".join(
        str(value)
        for item in coolant_data.get("content", [])
        for value in [item.get("headline", ""), item.get("text", "")]
    )
    normalized_coolant = normalized(coolant_text)
    assert all(fragment in normalized_coolant for fragment in ["man324sioat", "vwtl774g", "37c"])

    records = []
    for index, row in enumerate(PRODUCTS, 1):
        fragment = SOURCE_NAME_OVERRIDES.get(row["product_name"], row["product_name"])
        combined = " ".join(page_text[page] for page in row["source_pages"])
        assert normalized(fragment) in normalized(combined), (row["product_name"], row["source_pages"])
        if row["product_name"] == "High-Temperature Lubricant 13-047":
            assert "13047" in normalized(combined)
        if row["product_name"] == "RECOLUBE BIOPOWER SKX 023":
            assert "biopowerskx023" in normalized(combined)
        records.append({
            "source_id": "MAN_CURRENT_SERVICE_PRODUCTS",
            "source_record_id": f"MAN-SERVICE-{index:03d}",
            **row,
            "market": "MAN_TRUCKS_GLOBAL_EN",
            "recommendation_status": "recommended_or_specified_by_MAN",
            "document_date": DOCUMENT_DATE,
            "source_url": PDF_URL,
            "snapshot_date": SNAPSHOT_DATE,
        })

    assert len(records) == 32
    assert len({(row["brand"], row["product_name"], row["family_code"]) for row in records}) == len(records)
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "document_date": DOCUMENT_DATE,
        "source_id": "MAN_CURRENT_SERVICE_PRODUCTS",
        "source_url": PDF_URL,
        "secondary_source_url": COOLANT_PAGE_URL,
        "pdf_pages": len(reader.pages),
        "pdf_sha256": hashlib.sha256(pdf_payload).hexdigest(),
        "secondary_source_sha256": hashlib.sha256(coolant_payload).hexdigest(),
        "products": len(records),
        "brands": len({row["brand"] for row in records}),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "recommendation_occurrences": sum(len(row["source_pages"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "excluded_non_product_standards_and_ungraded_series": [
            "MAN 248", "MAN 283 Li-P 2", "MAN 284 Li-H 2", "MAN 339 L1/L3",
            "MAN 3703", "generic ISO VG hydraulic grades", "Chevron Ultra-Duty Greases EP series",
        ],
        "evidence_note": "Current MAN vehicle service recommendations are evidence of OEM recommendation/application, not a claim that every row has a formal approval letter.",
        "publication_scope": "Derived factual product and technical fields with attribution; PDF layout and prose are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
