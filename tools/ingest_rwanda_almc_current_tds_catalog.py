#!/usr/bin/env python3
"""Normalize every TDS linked from the current ALMC Rwanda product page.

The official page has one Technical Data Sheets section with eleven PDFs.
Multi-grade tables are expanded into separate product-grade identities.  Only
factual names, specifications and typical properties are retained; source
contradictions and probable typos remain explicit.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/rwanda-almc-current-products.jsonl"
REPORT = ROOT / "data/rwanda-almc-current-report.json"
SOURCE_ID = "RWANDA_ALMC_CURRENT_COMPLETE_TDS_CATALOG"
LANDING_URL = "https://www.almc.rw/automotive-lubricants/"
SITEMAP_URL = "https://www.almc.rw/sitemap.xml"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class PdfLinksParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        href = dict(attrs).get("href")
        if href and href.casefold().split("?")[0].endswith(".pdf"):
            self.links.append(urljoin(LANDING_URL, href))


def product(name: str, family: str, tds: int, **specifications: object) -> dict:
    return {
        "product_name": name,
        "family_code": family,
        "tds": tds,
        "specifications": specifications,
    }


TDS = [
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Car-Engine-oil-Mineral-CF-4-SG-SAE-15W-40.pdf",
        "tokens": ["CF-4/SG", "15W/40", "MB 228.1"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Car-Engine-Oil-Mineral-API-SL-CF-SAE-20W-50.pdf",
        "tokens": ["API SL/CF", "20W/50", "VW 501.01/505.00"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Motorcycle-Engine-Oil-4T-Mineral.pdf",
        "tokens": ["Motorcycle Engine Oil 4T Mineral", "JASO MA 2", "20W/50"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Truck-engine-Oil-Mineral-SHPD-CI-4-SAE-15w-40.pdf",
        "tokens": ["SHPD CI-4", "15W/40", "Volvo VDS-3"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Truck-engine-oil-Mineral-CH-4-SL-SAE-15W-40.pdf",
        "tokens": ["CH-4/SL", "15W/40", "RENAULT RD"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Truck-Engine-Oil-Mineral-CF-SF.pdf",
        "tokens": ["API CF/SF", "SAE 40", "MIL-L-2104B"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Gear-Oil-Mineral-GL-5-Basic-SAE-80W90-and-85W140.pdf",
        "tokens": ["API GL-5", "80W/90", "85W/140"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Gear-Oil-Mineral-GL-4.pdf",
        "tokens": ["API GL-4", "80W/90", "85W/140"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/Hydraulic-Oil-HLP.pdf",
        "tokens": ["DIN 51524 part 2 HLP", "32 46 68"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/INDUSTRIAL_Gear_TWS_GB20.pdf",
        "tokens": ["DIN 51517-PART 3", "68 100 150 220 320 460 680"],
    },
    {
        "url": "https://d23n208rphwze8.cloudfront.net/media/GREASE_Lithium_EP_GB19.pdf",
        "tokens": ["Grease Lithium EP 1-2-3", "NLGI No", "GR0010002"],
    },
]


PRODUCTS = [
    product(
        "ALMC Car Engine Oil Mineral CF-4/SG SAE 15W-40", "M", 1,
        sae_engine="15W-40", api=["CF-4", "SG"], base_oil="mineral",
        oem_specifications=["MB 228.1", "VW 501.00", "VW 505.00", "Ford WSS-M2C153-C"],
        standards=["MIL-L-46152EC", "MIL-L-2104D"],
        operating_temperature_c={"min": -20, "max": 150},
        typical_properties={"density_20c_kg_l": 0.872, "kv40_cst": 107.3, "kv100_cst": 14.6, "ccs_minus20_cp_max": 7000, "viscosity_index": 130, "flash_point_c": 220, "pour_point_c": -27, "tbn_mg_koh_g": 8.5},
    ),
    product(
        "ALMC Car Engine Oil Mineral SL/CF SAE 20W-50", "M", 2,
        sae_engine="20W-50", api=["SL", "CF"], base_oil="mineral",
        oem_specifications=["VW 501.01", "VW 505.00", "MB 229.1"],
        operating_temperature_c={"min": -10, "max": 150},
        typical_properties={"density_20c_kg_l": 0.888, "kv40_cst": 157.3, "kv100_cst": 17.1, "ccs_minus15_cp_max": 9500, "viscosity_index": 125, "flash_point_c": 220, "pour_point_c": -18, "tbn_mg_koh_g": 6.1},
        source_quality_flags=["description_mentions_15w40_but_tds_type_and_property_table_only_publish_20w50"],
    ),
    product(
        "ALMC Motorcycle Engine Oil 4T Mineral SAE 20W-50", "M", 3,
        sae_engine="20W-50", api=["SL", "CF"], jaso=["MA2"],
        engine_cycle="4T", base_oil="mineral",
        operating_temperature_c={"min": 0, "max": 150},
        typical_properties={"density_20c_kg_l": 0.885, "kv40_cst": 173.0, "kv100_cst": 18.0, "ccs_minus15_cp_max": 9500, "viscosity_index": 125, "flash_point_c": 210, "pour_point_c": -5, "tbn_mg_koh_g": 5.0},
    ),
    product(
        "ALMC Truck Engine Oil Mineral SHPD CI-4 SAE 15W-40", "M", 4,
        sae_engine="15W-40", api=["CI-4", "CH-4", "SL"], base_oil="mineral",
        oem_specifications=["MB 228.3", "MB 228.1", "MB 229.1", "Volvo VDS-3", "MAN 3275", "MTU Type 2", "Cummins CES 20071", "Cummins CES 20072", "Cummins CES 20076", "Cummins CES 20077", "Cummins CES 20078", "Mack EO-M Plus", "Mack EO-N", "Caterpillar ECF-1-a", "Allison C4", "Renault RLD-2", "Renault RLD", "Detroit Diesel 93K215"],
        operating_temperature_c={"min": -30, "max": 150},
        typical_properties={"density_20c_kg_l": 0.884, "kv40_cst": 100.0, "kv100_cst": 14.0, "ccs_minus20_cp_max": 7000, "viscosity_index": 135, "flash_point_c": 220, "pour_point_c": -36, "tbn_mg_koh_g": 10.5},
    ),
    product(
        "ALMC Truck Engine Oil Mineral CH-4/SL SAE 15W-40", "M", 5,
        sae_engine="15W-40", api=["CH-4", "CG-4", "SL"], base_oil="mineral",
        oem_specifications=["MB 228.1", "MB 229.1", "Volvo VDS", "Renault RD", "MAN M271", "Mack EO-M", "Allison C4", "MTU Type 1", "DDC Oil Category 1", "ZF TE-ML 02C", "ZF TE-ML 03A", "ZF TE-ML 04B", "ZF TE-ML 04C", "ZF TE-ML 07C"],
        operating_temperature_c={"min": -30, "max": 150},
        typical_properties={"density_20c_kg_l": 0.882, "kv40_cst": 102.3, "kv100_cst": 13.7, "ccs_minus20_cp_max": 7000, "viscosity_index": 134, "flash_point_c": 210, "pour_point_c": -27, "tbn_mg_koh_g": 8.5},
    ),
    product(
        "ALMC Truck Engine Oil Mineral CF/SF SAE 40", "M", 6,
        sae_engine="40", api=["CF", "SF"], base_oil="mineral",
        standards=["MIL-L-46152B", "MIL-L-2104B"],
        operating_temperature_c={"min": 0, "max": 150},
        typical_properties={"density_20c_kg_l": 0.887, "kv40_cst": 143.0, "kv100_cst": 14.5, "viscosity_index": 95, "flash_point_c": 220, "pour_point_c": -15, "tbn_mg_koh_g": 10.5},
    ),
]

for tds, api_gl, grade, properties in [
    (7, "GL-5", "80W-90", (0.909, 197.3, 17.1, 92, 210, -15, -5)),
    (7, "GL-5", "85W-140", (0.917, 352.3, 24.2, 88, 210, -8, 0)),
    (8, "GL-4", "80W-90", (902, 146.0, 14.3, 100, 215, -27, -25)),
    (8, "GL-4", "85W-140", (908, 430.0, 29.0, 100, 215, -18, -16)),
]:
    density_key = "density_20c_kg_l" if tds == 7 else "density_15c_kg_m3"
    PRODUCTS.append(product(
        f"ALMC Gear Oil Mineral {api_gl} Basic SAE {grade}", "T", tds,
        sae_gear=grade, api_gl=[api_gl], base_oil="mineral",
        standards=["MIL-L-2105D"],
        operating_temperature_c={"min": properties[6], "max": 150},
        typical_properties={density_key: properties[0], "kv40_cst": properties[1], "kv100_cst": properties[2], "viscosity_index": properties[3], "flash_point_c": properties[4], "pour_point_c": properties[5]},
    ))

for grade, properties in {
    "32": (0.872, 32, 2.3, 95, 200, -24, -20),
    "46": (0.876, 46, 6.7, 95, 200, -24, -20),
    "68": (0.879, 68, 8.6, 95, 210, -18, -10),
}.items():
    flags = ["hydraulic_iso_vg32_kv100_published_as_2_3_suspected_source_typo_retained"] if grade == "32" else []
    PRODUCTS.append(product(
        f"ALMC Hydraulic Oil HLP ISO VG {grade}", "H", 9,
        iso_vg=grade, hydraulic_class=["HLP"], base_oil="mineral",
        standards=["DIN 51524-2 HLP"],
        operating_temperature_c={"min": properties[6], "max": 150},
        typical_properties={"density_15c_kg_l": properties[0], "kv40_cst": properties[1], "kv100_cst": properties[2], "viscosity_index": properties[3], "flash_point_c": properties[4], "pour_point_c": properties[5]},
        source_quality_flags=flags,
    ))

for grade, properties in {
    "68": (0.875, 8.6, 95, -27, 210, -20),
    "100": (0.885, 11.2, 95, -24, 220, -20),
    "150": (0.889, 14.6, 95, -24, 220, -20),
    "220": (0.895, 18.8, 95, -24, 230, -20),
    "320": (0.898, 24.0, 95, -18, 240, -15),
    "460": (0.907, 31.0, 95, -15, 250, -10),
    "680": (0.900, 39.0, 95, -15, 250, -10),
}.items():
    PRODUCTS.append(product(
        f"ALMC Industrial Gear Oil TWS ISO VG {grade}", "I", 10,
        iso_vg=grade, industrial_gear_class=["CLP"], base_oil="mineral",
        standards=["DIN 51517-3 CLP", "ISO 12925-1", "ANSI/AGMA 9005-E02", "US Steel 224", "David Brown S1.53.101"],
        source_reported_performance=["Timken OK Load 75 lb", "FZG load stage 12"],
        operating_temperature_c={"min": properties[5], "max": 150},
        typical_properties={"density_15c_kg_l": properties[0], "kv40_cst": int(grade), "kv100_cst": properties[1], "viscosity_index": properties[2], "pour_point_c": properties[3], "flash_point_c": properties[4]},
    ))

for nlgi, reference, penetration in [
    ("1", "GR0010002", "310-340"),
    ("2", "GR0020002", "265-295"),
    ("3", "GR0030003", "220-250"),
]:
    PRODUCTS.append(product(
        f"ALMC Grease Lithium EP NLGI {nlgi}", "G", 11,
        nlgi=nlgi, thickener="lithium 12-hydroxystearate",
        grease_type="EP multipurpose", base_oil="mineral",
        manufacturer_reference=reference,
        operating_temperature_c={"min": -20, "max": 130},
        typical_properties={"worked_penetration_01mm": penetration, "base_oil_kv40_cst": "135-165", "dropping_point_c": 180, "rust_test_max": 1, "roll_stability_penetration_change_pct_max": 25, "four_ball_weld_load_kg": 200},
        source_quality_flags=["landing_page_title_claims_ep_0_1_2_3_but_tds_only_publishes_nlgi_1_2_3"],
    ))


def main() -> None:
    landing_payload = fetch(LANDING_URL)
    sitemap_payload = fetch(SITEMAP_URL)
    parser = PdfLinksParser()
    parser.feed(landing_payload.decode(errors="replace"))
    discovered = list(dict.fromkeys(parser.links))
    expected = [row["url"] for row in TDS]
    if discovered != expected:
        raise RuntimeError(f"TDS denominator changed: {discovered!r}")
    sitemap_text = sitemap_payload.decode(errors="replace")
    if "automotive-lubricants" not in sitemap_text:
        raise RuntimeError("Official sitemap no longer lists the product page")

    pdf_evidence: dict[int, dict] = {}
    for index, source in enumerate(TDS, 1):
        payload = fetch(source["url"])
        reader = PdfReader(io.BytesIO(payload))
        text = clean(" ".join((page.extract_text() or "") for page in reader.pages))
        for token in source["tokens"]:
            if clean(token).casefold() not in text.casefold():
                raise RuntimeError(f"TDS {index} missing token {token!r}")
        pdf_evidence[index] = {
            "source_pdf_sha256": hashlib.sha256(payload).hexdigest(),
            "source_facts_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source_pdf_pages": len(reader.pages),
        }

    records = []
    for index, source in enumerate(PRODUCTS, 1):
        evidence = pdf_evidence[source["tds"]]
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"ALMC-RW-{index:03d}",
            "source_url": TDS[source["tds"] - 1]["url"],
            "listing_url": LANDING_URL,
            **evidence,
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Rwanda",
            "manufacturer": "Africa Lubricants Manufacturing Company Ltd.",
            "brand": "ALMC",
            "brand_scope": "manufacturer_catalog_label; company also offers private-label manufacturing",
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "lifecycle_status": "current_official_catalog",
            "evidence_status": "current_local_manufacturer_complete_tds_catalog",
            "specifications": source["specifications"],
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    quality_flags = Counter(
        flag for row in records
        for flag in row["specifications"].get("source_quality_flags", [])
    )
    report = {
        "schema_version": 1,
        "status": "current_local_manufacturer_complete_tds_catalog_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "landing_pages": 1,
        "sitemap_product_pages": 1,
        "tds_documents": len(TDS),
        "tds_pages": sum(row["source_pdf_pages"] for row in pdf_evidence.values()),
        "product_grade_identities": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "quality_flags": dict(sorted(quality_flags.items())),
        "landing_tds_links_sha256": hashlib.sha256(
            ("\n".join(discovered) + "\n").encode()
        ).hexdigest(),
        "sitemap_locations_sha256": hashlib.sha256(
            (
                "\n".join(sorted(set(re.findall(r"<loc>([^<]+)</loc>", sitemap_text))))
                + "\n"
            ).encode()
        ).hexdigest(),
        "pdf_sha256": {
            str(index): row["source_pdf_sha256"]
            for index, row in sorted(pdf_evidence.items())
        },
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "denominator_note": "All 11 TDS links on the sole product page listed in the official sitemap are included and expanded into 23 explicitly published grades.",
        "availability_note": "The manufacturer page publishes no packages, prices, stock quantities or order actions; no offers are created.",
        "brand_note": "ALMC is retained as the manufacturer-catalog label, not asserted as the package brand; the same company explicitly offers private-label manufacturing.",
        "publication_scope": "Factual product names, grades, specifications, typical properties, evidence URLs and hashes only; descriptions, benefits, contacts, imagery and source PDFs are excluded.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
