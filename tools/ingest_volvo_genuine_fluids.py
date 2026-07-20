#!/usr/bin/env python3
"""Normalize current Volvo Trucks and Volvo CE genuine lubricants and coolants."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "volvo-genuine-fluids.jsonl"
REPORT = ROOT / "data" / "volvo-genuine-fluids-report.json"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"

PAGES = {
    "ce_lubricants": "https://www.volvoce.com/asia/en-as/parts/maintenance-parts/lubricants/",
    "ce_grease": "https://www.volvoce.com/asia/en-as/parts/maintenance-parts/grease/",
    "ce_coolants": "https://www.volvoce.com/asia/en-as/parts/maintenance-parts/coolants/",
    "ce_ho103": "https://www.volvoce.com/asia/en-as/parts/maintenance-parts/common-hydraulic-oil/",
    "trucks_us_sds": "https://www.volvotrucks.us/parts-and-services/parts/material-safety-data-sheets/",
}


def product(name: str, family: str, page: str, market: str, **specifications) -> dict:
    return {
        "brand": "Volvo",
        "manufacturer": "Volvo Group",
        "product_name": name,
        "family_code": family,
        "source_page": page,
        "market": market,
        "specifications": specifications,
    }


PRODUCTS = [
    product("Volvo Hydraulic Oil 98608 Super", "H", "ce_lubricants", "ASIA_VOLVO_CE", application="hydraulic systems"),
    product("Volvo Hydraulic Oil 98609 Extra", "H", "ce_lubricants", "ASIA_VOLVO_CE", application="hydraulic systems"),
    product("Volvo Hydraulic Oil 98620 Ultra", "H", "ce_lubricants", "ASIA_VOLVO_CE", application="excavator hydraulic systems"),
    product("Volvo Hydraulic Oil 98610 Biodegradable", "H", "ce_lubricants", "ASIA_VOLVO_CE", application="hydraulic systems", biodegradable=True),
    product("Volvo Hydraulic Oil 98611 HO103", "H", "ce_ho103", "GLOBAL_VOLVO_CE", application="hydraulic systems", extended_drain_hours=3000),
    product("Volvo Automatic Transmission Fluid 97341 AT101", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="automatic transmissions", volvo_standard="97341"),
    product("Volvo Automatic Transmission Fluid 97342 AT102", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="automatic transmissions", volvo_standard="97342"),
    product("Volvo Transmission Oil 10W", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="transmissions", sae_gear="SAE 10W"),
    product("Volvo Transmission Oil 30", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="transmissions", sae_gear="SAE 30"),
    product("Volvo Axle Oil 97321 80W-90", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="axles", sae_gear="80W-90", volvo_standard="97321"),
    product("Volvo Axle Oil 97321 85W-140", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="axles", sae_gear="85W-140", volvo_standard="97321"),
    product("Volvo Axle Oil 97317 75W-80 GO102", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="axles", sae_gear="75W-80", volvo_standard="97317", volvo_product_class="GO102"),
    product("Volvo Axle Oil Limited Slip 85W-90 GL-5", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="limited-slip axles", sae_gear="85W-90", api_gl="GL-5"),
    product("Volvo Synthetic Axle Oil 97312 75W-90", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="axles", sae_gear="75W-90", volvo_standard="97312"),
    product("Volvo Wet Brake Oil 97303 WB101", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="wet brakes and reduction gears", volvo_standard="97303", volvo_product_class="WB101"),
    product("Volvo Wet Brake Oil 97304 WB102", "T", "ce_lubricants", "ASIA_VOLVO_CE", application="wet brakes and reduction gears", volvo_standard="97304", volvo_product_class="WB102"),
    product("Volvo Multipurpose Grease 97718 GR101", "G", "ce_grease", "ASIA_VOLVO_CE", application="general use", thickener="lithium", nlgi="2", temperature_min_c=-20, temperature_max_c=130, volvo_standard="1277,18", volvo_product_class="GR101"),
    product("Volvo Resistant Grease 97720 GR102", "G", "ce_grease", "ASIA_VOLVO_CE", application="general use and wet operating environments", thickener="lithium complex", nlgi="2", temperature_min_c=-20, temperature_max_c=140, volvo_standard="1277,2", volvo_product_class="GR102"),
    product("Volvo Extreme Grease 97765 GR103", "G", "ce_grease", "ASIA_VOLVO_CE", application="heavy duty", thickener="lithium complex with molybdenum disulfide", nlgi="2", temperature_min_c=-10, temperature_max_c=140, volvo_standard="1277,65", volvo_product_class="GR103"),
    product("Volvo High Temperature Grease", "G", "ce_grease", "ASIA_VOLVO_CE", application="paver systems", thickener="polyurea", nlgi="1", temperature_max_c=200),
    product("Volvo Breaker Paste", "G", "ce_grease", "ASIA_VOLVO_CE", application="hydraulic breakers", thickener="aluminium complex", nlgi="2", temperature_min_c=-20, temperature_max_c=1100),
    product("Volvo Coolant VCS", "TF", "ce_coolants", "ASIA_VOLVO_CE", application="engine cooling systems", coolant_chemistry="OAT", color="yellow", product_form="concentrate_or_premix_unspecified"),
    product("Volvo Coolant", "TF", "ce_coolants", "ASIA_VOLVO_CE", application="engine cooling systems", coolant_chemistry="hybrid organic/inorganic", color="green", product_form="concentrate_or_premix_unspecified"),
    product("Volvo Engine Oil VDS-5 5W-30", "M", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="heavy-duty diesel engines", sae_engine="5W-30", volvo_standard="VDS-5", packages=["5 gallon pail", "55 gallon drum"], part_numbers=["MVB V5W30PAIL", "MVB V5W30DRUM"]),
    product("Volvo Engine Oil VDS-4.5 10W-30", "M", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="heavy-duty diesel engines", sae_engine="10W-30", volvo_standard="VDS-4.5", packages=["1 gallon bottle", "55 gallon drum", "bulk"], part_numbers=["MVB V10W30JUG", "MVB V10W30DRUM", "MVB V10W30BULK"]),
    product("Volvo Engine Oil VDS-4.5 15W-40", "M", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="heavy-duty diesel engines", sae_engine="15W-40", volvo_standard="VDS-4.5", packages=["1 gallon bottle", "55 gallon drum", "bulk"], part_numbers=["MVB V15W40JUG", "MVB V15W40DRUM", "MVB V15W40BULK"]),
    product("Volvo Extended Life NF Premixed 50/50 Coolant", "TF", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="engine cooling systems", product_form="premix 50/50", packages=["1 gallon bottle", "55 gallon drum"], part_numbers=["MVB VNF5050JUG", "MVB VNF5050DRUM"]),
    product("Volvo VCS2 50/50 Premixed Coolant", "TF", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="engine cooling systems", product_form="premix 50/50", packages=["1 gallon bottle", "55 gallon drum", "275 gallon tote", "bulk"], part_numbers=["MVBVVCS25050JUG", "MVBVVCS25050DRUM", "MVBVVCS25050TOTE", "MVBVVCS25050BULK"]),
    product("Volvo VCS2 Concentrate Coolant", "TF", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="engine cooling systems", product_form="concentrate", packages=["1 gallon bottle", "55 gallon drum"], part_numbers=["MVBVVCS2CONJUG", "MVBVVCS2CONDRUM"]),
    product("Volvo I-Shift Transmission Fluid 75W-80", "T", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="I-Shift transmissions", sae_gear="75W-80", packages=["1 gallon bottle", "5 gallon pail"], part_numbers=["MVB VISHIFT75W80JUG", "MVB VISHIFT75W80PAIL"]),
    product("Volvo I-Shift Transmission Fluid 75W-90", "T", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="I-Shift transmissions", sae_gear="75W-90", packages=["1 gallon bottle"], part_numbers=["MVB VISHIFT75W90JUG"]),
    product("Volvo Grease Seal Conditioner Timing Gear Plate", "G", "trucks_us_sds", "US_CA_VOLVO_TRUCKS", application="timing gear plate seal conditioning", packages=["tube"], part_numbers=["24533210"]),
]

EXCLUDED_SERIES = ["Volvo Engine Oil VDS-3", "Volvo Engine Oil VDS-4", "Volvo Engine Oil VDS-4.5"]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def visible_text(payload: bytes) -> str:
    value = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", payload.decode(errors="replace"), flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def source_name_candidates(product_name: str) -> list[str]:
    """Volvo CE headings omit the brand although the canonical name keeps it."""
    candidates = [product_name]
    if product_name.casefold().startswith("volvo "):
        candidates.append(product_name[6:])
    return candidates


def main() -> None:
    pages = {}
    for page_id, url in PAGES.items():
        payload = fetch(url)
        pages[page_id] = {"url": url, "payload": payload, "text": visible_text(payload)}
    for row in PRODUCTS:
        source_text = normalized(pages[row["source_page"]]["text"])
        assert any(normalized(candidate) in source_text for candidate in source_name_candidates(row["product_name"])), row["product_name"]
    for series in EXCLUDED_SERIES:
        assert normalized(series) in normalized(pages["ce_lubricants"]["text"]), series

    records = []
    for index, row in enumerate(PRODUCTS, 1):
        records.append({
            "source_id": "VOLVO_GENUINE_FLUIDS",
            "source_record_id": f"VOLVO-GENUINE-{index:03d}",
            **row,
            "source_url": PAGES[row["source_page"]],
            "snapshot_date": SNAPSHOT_DATE,
        })
    assert len(records) == 32
    assert len({(row["brand"], row["product_name"], row["market"]) for row in records}) == len(records)
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": "VOLVO_GENUINE_FLUIDS",
        "landing_urls": list(PAGES.values()),
        "source_pages": [
            {"page_id": page_id, "source_url": data["url"], "source_sha256": hashlib.sha256(data["payload"]).hexdigest()}
            for page_id, data in pages.items()
        ],
        "products": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "excluded_ungraded_engine_oil_series": EXCLUDED_SERIES,
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Derived factual product and technical fields with attribution; page design and marketing prose are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
