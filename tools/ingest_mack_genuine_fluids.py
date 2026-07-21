#!/usr/bin/env python3
"""Normalize current official Mack lubricants, coolants and technical fluids."""

from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "mack-genuine-fluids.jsonl"
REPORT = ROOT / "data" / "mack-genuine-fluids-report.json"
SOURCE_ID = "MACK_GENUINE_FLUIDS"
SDS_URL = "https://bahamas.macktrucks.com/parts-and-services/parts/mack-parts/material-safety-data-sheets"
OVERVIEW_URL = "https://www.macktrucks.com/parts-and-services/parts/mack-parts/engine/"
MANUAL_URL = "https://www.macktrucks.com/media/documents/mack-hd-sec-1-oil-filter-final.pdf"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"


def product(name: str, family: str, packages: list[tuple[str, str]], **specifications) -> dict:
    return {
        "product_name": name,
        "family_code": family,
        "packages": [
            {"package_name": package_name, "part_number": part_number}
            for package_name, part_number in packages
        ],
        "specifications": specifications,
    }


PRODUCTS = [
    product("Mack Engine Oil EOS-5 5W-30", "M", [("5 Gallon Pail", "9853-M5W30PAIL"), ("55 Gallon Drum", "9853-M5W30DRUM")], application="heavy-duty diesel engines", sae_engine="5W-30", mack_standard="EOS-5", api=["FA-4"]),
    product("Mack Engine Oil EOS-4.5 10W-30", "M", [("1 Gallon Bottle", "9853-M10W30JUG"), ("55 Gallon Drum", "9853-M10W30DRUM"), ("Bulk", "9853-M10W30BULK")], application="heavy-duty diesel engines", sae_engine="10W-30", mack_standard="EOS-4.5", api=["CK-4"]),
    product("Mack Engine Oil EOS-4.5 15W-40", "M", [("1 Gallon Bottle", "9853-M15W40JUG"), ("5 Gallon Pail", "9853-M15W40PAIL"), ("55 Gallon Drum", "9853-M15W40DRUM"), ("Bulk", "9853-M15W40BULK")], application="heavy-duty diesel engines", sae_engine="15W-40", mack_standard="EOS-4.5", api=["CK-4"]),
    product("Mack Grease 97718", "G", [("14 Oz Tube", "9853-M97718TUBE"), ("Keg 50 kg O/H Steel Black", "9853-M97718KEG")], application="multipurpose chassis and bearing lubrication", mack_standard="97718", thickener="lithium soap", base_oil="mineral oil"),
    product("Mack Gear Oil GO-J 80W-90", "T", [("5 Gallon Pail", "9853-MGOJ80W90PAIL"), ("16 Gallon Keg", "9853-MGOJ80W90KEG"), ("55 Gallon Drum", "9853-MGOJ80W90DRUM")], application="axles and gears", sae_gear="80W-90", mack_product_class="GO-J"),
    product("Mack Gear Oil GO-J 85W-140", "T", [("5 Gallon Pail", "9853-MGOJ85W140PAIL"), ("16 Gallon Keg", "9853-MGOJ85W140KEG")], application="axles and gears", sae_gear="85W-140", mack_product_class="GO-J"),
    product("Mack Synthetic Gear Oil GO-J Plus", "T", [("1 Gallon Bottle", "9853-MGOJPLUSJUG"), ("16 Gallon Keg", "9853-MGOJPLUSKEG"), ("55 Gallon Drum", "9853-MGOJPLUSDRUM")], application="axles and gears", mack_product_class="GO-J Plus"),
    product("Mack Hydraulic Oil Premium 32", "H", [("5 Gallon Pail", "9853-MHYDRAULIC32PAIL")], application="hydraulic systems", iso_vg="32"),
    product("Mack Extended Life NF Premixed 50/50 Coolant", "TF", [("1 Gallon Bottle", "9854-MNF5050JUG")], application="engine cooling systems", product_form="premix 50/50"),
    product("Mack VCS2 Premixed 50/50 Coolant", "TF", [("1 Gallon Bottle", "9854-MVCS25050JUG"), ("55 Gallon Drum", "9854-MVCS25050DRUM"), ("275 Gallon Tote", "9854-MVCS25050TOTE"), ("Bulk", "9854-MVCS25050BULK")], application="engine cooling systems", product_form="premix 50/50", coolant_chemistry="POAT", mack_product_class="VCS2"),
    product("Mack VCS2 Concentrate Coolant", "TF", [("1 Gallon Bottle", "9854-MVCS2CONJUG"), ("55 Gallon Drum", "9854-MVCS2CONDRUM")], application="engine cooling systems", product_form="concentrate", coolant_chemistry="POAT", mack_product_class="VCS2"),
    product("Mack mDRIVE Transmission Fluid 75W-80", "T", [("1 Gallon Bottle", "9853-M m DRIVE75W80JUG"), ("5 Gallon Pail", "9853-M m DRIVE75W80PAIL")], application="mDRIVE automated manual transmissions", sae_gear="75W-80", mack_standards=["97307", "97318"]),
    product("Mack mDRIVE Transmission Fluid 75W-90", "T", [("1 Gallon Bottle", "9853-M m DRIVE75W90JUG")], application="mDRIVE automated manual transmissions", sae_gear="75W-90", mack_standards=["97315", "37319"]),
    product("Mack Synthetic ATF A295", "T", [("1 Gallon Bottle", "9853-MATFA295JUG")], application="automatic transmissions", mack_product_class="A295"),
    product("Grease Seal Conditioner Timing Gear Plate", "G", [("Tube", "24533210")], application="timing gear plate seal conditioning"),
]


PRODUCT_SHEET_PART_NUMBERS = {
    "Mack Engine Oil EOS-5 5W-30": ["9853-M5W30PAIL", "9853-M5W30DRUM"],
    "Mack Engine Oil EOS-4.5 10W-30": ["9853-M10W30JUG", "9853-M10W30DRUM", "9853-M10W30BULK"],
    "Mack Engine Oil EOS-4.5 15W-40": ["9853-M15W40JUG", "9853-M15W40PAIL", "9853-M15W40DRUM", "9853-M15W40BULK"],
    "Mack Grease 97718": ["MVBM97718TUBE", "MVBM97718KEG"],
    "Mack Hydraulic Oil Premium 32": ["MVBMHYDRAULIC32PAIL"],
    "Mack mDRIVE Transmission Fluid 75W-80": ["MVBMMDRIVE75W80JUG", "MVBMMDRIVE75W80PAIL"],
    "Mack mDRIVE Transmission Fluid 75W-90": ["MVBMMDRIVE75W90JUG"],
}

PRODUCT_SHEET_URLS = {
    "Mack Engine Oil EOS-5 5W-30": "https://www.macktrucks.com/media/files/parts-and-service/engine/pv960-m-051321-pure-mack-eos-5-engine-oil.pdf",
    "Mack Engine Oil EOS-4.5 10W-30": "https://www.macktrucks.com/media/files/parts-and-service/engine/2021/pv960-m-111821-pure-mack-vds-45-engine-oil.pdf",
    "Mack Engine Oil EOS-4.5 15W-40": "https://www.macktrucks.com/media/files/parts-and-service/engine/2021/pv960-m-111821-pure-mack-vds-45-engine-oil.pdf",
    "Mack Grease 97718": "https://www.macktrucks.com/media/files/parts-and-service/engine/2022/pure-mack-grease-product-sheet.pdf",
    "Mack Hydraulic Oil Premium 32": "https://www.macktrucks.com/media/files/parts-and-service/engine/2022/mack-premium-hydraulic-oil-product-sheet.pdf",
    "Mack mDRIVE Transmission Fluid 75W-80": "https://www.macktrucks.com/media/files/parts-and-service/engine/2022/75w-80-mdrive-transmission-fluid-1.pdf",
    "Mack mDRIVE Transmission Fluid 75W-90": "https://www.macktrucks.com/media/files/parts-and-service/engine/2022/75w-90-mdrive-transmission-fluid-1.pdf",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
        if response.headers.get("Content-Encoding", "").casefold() == "gzip" or payload[:2] == b"\x1f\x8b":
            payload = gzip.decompress(payload)
        return payload


def visible_text(payload: bytes) -> str:
    value = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", payload.decode(errors="replace"), flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def english_sds_links(payload: bytes) -> dict[str, str]:
    page = payload.decode(errors="replace")
    blocks = re.findall(r"<div>\s*<div><strong>(.*?)</strong>(.*?)</div>\s*</div>\s*<div>(.*?)(?=<div>\s*<div><strong>|</div>\s*</main>)", page, flags=re.I | re.S)
    links = {}
    for strong, tail, body in blocks:
        name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", strong + tail))).strip()
        match = re.search(r'href=["\']([^"\']+)["\'][^>]*>English', body, flags=re.I | re.S)
        if match:
            links[name] = urllib.parse.urljoin(SDS_URL, html.unescape(match.group(1)))
    return links


def main() -> None:
    sds_payload = fetch(SDS_URL)
    overview_payload = fetch(OVERVIEW_URL)
    manual_payload = fetch(MANUAL_URL)
    product_sheet_payloads = {
        url: fetch(url) for url in sorted(set(PRODUCT_SHEET_URLS.values()))
    }
    sds_text = visible_text(sds_payload)
    overview_text = visible_text(overview_payload)
    sds_links = english_sds_links(sds_payload)

    for row in PRODUCTS:
        assert normalized(row["product_name"]) in normalized(sds_text), row["product_name"]
        for package in row["packages"]:
            assert normalized(package["part_number"]) in normalized(sds_text), package["part_number"]
    for evidence in ["97307, 97318", "97315, 37319", "VCS2 Coolant", "POAT"]:
        assert normalized(evidence) in normalized(overview_text), evidence

    records = []
    for index, row in enumerate(PRODUCTS, 1):
        quality_flags = []
        if row["product_name"].startswith("Mack mDRIVE"):
            quality_flags.append("source_part_number_contains_embedded_formatting_spaces_retained_verbatim")
        if row["product_name"] == "Mack mDRIVE Transmission Fluid 75W-90":
            quality_flags.append("source_mack_standard_37319_retained_verbatim_not_silently_corrected")
        if row["product_name"] in {"Mack Grease 97718", "Mack Hydraulic Oil Premium 32"}:
            quality_flags.append("source_sds_link_target_name_mismatch_not_used_as_technical_evidence")
        sheet_numbers = PRODUCT_SHEET_PART_NUMBERS.get(row["product_name"], [])
        sds_numbers = [package["part_number"] for package in row["packages"]]
        if set(sheet_numbers) - set(sds_numbers):
            quality_flags.append("official_regional_part_number_variants_preserved_separately")
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"MACK-GENUINE-{index:03d}",
            "brand": "Mack",
            "manufacturer": "Mack Trucks, Inc. / Volvo Group",
            **row,
            "market": "BAHAMAS_EN_MACK",
            "source_url": SDS_URL,
            "product_overview_url": OVERVIEW_URL,
            "engine_oil_standard_evidence_url": MANUAL_URL,
            "safety_document_url_source_reported": sds_links.get(row["product_name"], ""),
            "product_sheet_part_numbers": sheet_numbers,
            "product_sheet_url": PRODUCT_SHEET_URLS.get(row["product_name"], ""),
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_current_official_catalog_page",
            "source_quality_flags": quality_flags,
        })

    package_occurrences = sum(len(row["packages"]) for row in records)
    sds_part_numbers = {package["part_number"] for row in records for package in row["packages"]}
    product_sheet_part_numbers = {number for row in records for number in row["product_sheet_part_numbers"]}
    assert len(records) == 15
    assert package_occurrences == 32
    assert len(sds_part_numbers) == 32
    assert len(sds_part_numbers | product_sheet_part_numbers) == 38
    assert len({row["source_record_id"] for row in records}) == len(records)

    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "landing_urls": [SDS_URL, OVERVIEW_URL, MANUAL_URL],
        "source_pages": [
            {"source_url": SDS_URL, "source_sha256": hashlib.sha256(sds_payload).hexdigest()},
            {"source_url": OVERVIEW_URL, "source_sha256": hashlib.sha256(overview_payload).hexdigest()},
            {"source_url": MANUAL_URL, "source_sha256": hashlib.sha256(manual_payload).hexdigest()},
        ] + [
            {"source_url": url, "source_sha256": hashlib.sha256(payload).hexdigest()}
            for url, payload in sorted(product_sheet_payloads.items())
        ],
        "products": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "package_occurrences": package_occurrences,
        "sds_catalog_part_numbers": len(sds_part_numbers),
        "unique_part_numbers_all_official_pages": len(sds_part_numbers | product_sheet_part_numbers),
        "source_quality_flags": dict(sorted(Counter(
            flag for row in records for flag in row["source_quality_flags"]
        ).items())),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Derived factual product, grade, standard, package and part-number fields with attribution; page design, images and marketing prose are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
