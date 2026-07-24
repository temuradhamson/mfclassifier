#!/usr/bin/env python3
"""Normalize TAPPCO Sudan's complete public WordPress product-post catalog."""

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
OUT = ROOT / "data/sudan-tappco-products.jsonl"
REPORT = ROOT / "data/sudan-tappco-report.json"
SOURCE_ID = "SUDAN_TAPPCO_COMPLETE_PRODUCT_POST_CATALOG"
BASE_URL = "https://tappco-lubes.com/"
API_URL = BASE_URL + "wp-json/wp/v2/"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"
EXCLUDED_POST_IDS = {
    511: "WordPress theme demonstration post",
    692: "Company information, not a product",
}
CATEGORY_NAMES = {
    72: "Marine and Two stroke",
    73: "Industrial",
    74: "Grease",
    76: "Gear and Transmission",
    78: "Auxiliary",
    79: "Motor oils",
    80: "Diesel oils",
}

# Manually reviewed product/grade identities from the public card titles and
# correctly linked TAPPCO TDS documents. A grade found only in a mismatched TDS
# is deliberately excluded.
PRODUCTS = {
    1482: ("LITHIUM GREASE MP", "G", "nlgi", ["3"], {}),
    1274: (
        "Antifreeze LL", "TF", "", [""],
        {"performance": [
            "ASTM D3306", "ASTM D4985", "SAE J1034", "BS 6580:2010",
            "AFNOR NF R15-601", "JIS K 2234", "NATO S 759",
        ]},
    ),
    1273: (
        "UNIVERSAL BRAKE FLUID", "TF", "dot", ["DOT 4"],
        {"performance": ["FMVSS 116", "SAE J1703", "ISO 4925", "JIS K 2233 Class 4"]},
    ),
    1272: (
        "OPTIMA DIESEL", "M", "sae_engine", ["30", "40", "50"],
        {"api": ["CH-4", "SJ"], "acea": ["A3", "B3", "B4", "E2"]},
    ),
    # The live card links to the OPTIMA DIESEL PDF, not an OPTIMA VIMAX TDS.
    1270: ("OPTIMA VIMAX", "M", "sae_engine", ["20W-50"], {}),
    1266: (
        "SUPER OPTIMA", "M", "sae_engine", ["15W-40"],
        {
            "api": ["CI-4", "SL"],
            "acea": ["A3", "B3", "B4", "E5", "E6", "E7"],
            "performance": [
                "MB 229.1", "MB 228.3", "Mack EO-M Plus", "MAN M 3275",
                "Volvo VDS-2", "Volvo VDS-3", "Renault RVI RLD-2",
                "MTU Type 2", "CAT ECF-1",
                "Cummins 20071/72/76/77/78",
            ],
        },
    ),
    1264: (
        "PPX MOTOR OIL", "M", "sae_engine", ["50"],
        {
            "api": ["SL"], "acea": ["A3", "B3", "B4"],
            "performance": ["VW 505", "MB 228.1", "MAN 271", "Volvo VDS"],
        },
    ),
    # The live card links to the PPX MOTOR 50 PDF, not a TEENA TDS.
    1265: ("TEENA MOTOR", "M", "sae_engine", ["20W-50"], {}),
    1260: (
        "ATF DEXRON III", "T", "", [""],
        {"performance": [
            "General Motors DEXRON III(H)", "Allison C-4",
            "Allison TES-389", "Ford MERCON",
        ]},
    ),
    1256: (
        "GEAR OIL GL-5", "T", "sae_gear",
        ["90", "140", "250", "80W-90", "85W-140"],
        {"api_gl": ["GL-5"], "performance": ["MIL-L-2105D"]},
    ),
    1251: (
        "HARVEST UTTO", "T", "sae_gear", ["10W-30", "15W-40"],
        {
            "api_gl": ["GL-4"],
            "performance": [
                "John Deere J20A/B/C/D", "Massey Ferguson M1145/M1143/M1141/M1135",
                "Case MAT 3525", "Allison C-4/C-3", "Caterpillar TO-2",
            ],
        },
    ),
    1257: (
        "TRANSMISSION TO-4", "T", "sae_gear", ["10W", "30", "50"],
        {"performance": [
            "Caterpillar TO-4", "Allison C-4", "Komatsu Micro-Clutch",
            "ZF TE-ML 01", "ZF TE-ML 03",
        ]},
    ),
    1253: ("LITHIUM COMPLEX EP", "G", "nlgi", ["2"], {}),
    1248: (
        "LITHIUM GREASE EP", "G", "nlgi", ["000", "00", "0", "1", "2", "3"], {}
    ),
    1249: (
        "CYCLONE COMPRESSOR HT", "C", "iso_vg", ["32", "46", "68", "100", "150"],
        {"performance": ["DIN 51506 VD-L"]},
    ),
    1245: (
        "Cyclone PAO", "C", "iso_vg", ["32", "46", "68", "100", "150"],
        {
            "performance": [
                "DIN 51506 VDL", "DIN 51524-3 HVLP", "AFNOR NF E 48-603 HM",
            ],
        },
    ),
    1244: (
        "CYCLONE TURBINE OIL", "I", "iso_vg", ["22", "32", "68", "100", "150"],
        {
            "performance": [
                "Denison HF-1", "DIN 51524-1", "US Steel 126",
                "MIL-L-17672C", "AFNOR E-48600 HL",
            ],
        },
    ),
    1243: ("HEAT TRANSFER OIL", "I", "iso_vg", ["22", "32", "46"], {}),
    1240: (
        "HYDRAULIC HVI OIL", "H", "iso_vg", ["15", "22", "32", "46", "68", "100"],
        {
            "performance": [
                "DIN 51524-3 HVLP", "DIN 51517-3", "ISO 6743-4 HV",
                "Sperry Vickers M-2950-S", "Sperry Vickers I-286-S",
            ],
        },
    ),
    1238: (
        "HYDRAULIC OIL", "H", "sae_engine", ["10W"],
        {"performance": ["DIN 51524-2 HLP", "ISO 6743-4 HM"]},
    ),
    1237: (
        "HYDRAULIC OIL", "H", "source_grade", ["37"],
        {"performance": ["DIN 51524-2 HLP", "ISO 6743-4 HM"]},
    ),
    1232: (
        "HYDRAULIC OIL", "H", "iso_vg", ["32", "46", "68", "100"],
        {"performance": ["DIN 51524-2 HLP", "ISO 6743-4 HM"]},
    ),
    1231: ("INDUSTRIAL GEAR OIL", "I", "", [""], {}),
    1233: ("MEDIC WHITE OIL", "S", "", [""], {}),
    1229: ("REFRIDGE OIL", "C", "iso_vg", ["68"], {}),
    1227: ("Rockdrill", "I", "iso_vg", ["100", "150", "220", "320"], {}),
    1225: ("SPRAYABLE GEAR LUBE", "G", "nlgi", ["0"], {}),
    # The live SYNGEAR card links to the SPRAYABLE Gear Lube PDF.
    1223: ("SYNGEAR PAO", "I", "", [""], {}),
    1221: (
        "TRANSFORMER OIL", "I", "", [""],
        {"performance": [
            "IEC 60296:2003 Class I/II", "ASTM D3487 Type I",
            "AS 1767-1975", "BS 148:98 Class I/II",
        ]},
    ),
    1219: (
        "Ultra Hi-Load", "H", "iso_vg", ["32"],
        {
            "performance": [
                "DIN 51524-2", "DIN 51517-3", "ISO 6743-4",
                "Sperry Vickers I-286-S", "Sperry Vickers M-2950-S",
            ],
        },
    ),
    1217: (
        "MARINE TWO STROKE", "M", "", [""],
        {"api": ["TD"], "performance": ["NMMA TC-W3"]},
    ),
    1215: (
        "MARINE ULTRA", "M", "sae_engine", ["30", "40"],
        {"api": ["CF"], "performance": ["Caterpillar Series 3", "MIL-L-2104C"]},
    ),
    1213: (
        "TWO STROKE OIL TC", "M", "", [""],
        {"api": ["TC"], "jaso": ["FB"], "performance": ["TSC-3", "GLOBAL ISO-L-EGB"]},
    ),
}
MISMATCHED_TDS_POSTS = {
    1270: "linked PDF identifies OPTIMA DIESEL, not OPTIMA VIMAX",
    1265: "linked PDF identifies PPX MOTOR OIL SAE 50, not TEENA MOTOR",
    1223: "linked PDF identifies SPRAYABLE Gear Lube, not SYNGEAR PAO",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


class FactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.pdf_urls: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if href and href.lower().split("?", 1)[0].endswith(".pdf"):
            self.pdf_urls.append(href.replace("http://", "https://", 1))


def clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def main() -> None:
    posts_payload = fetch(
        API_URL
        + "posts?per_page=100&_fields=id,slug,link,date,modified,title,"
        + "content,categories"
    )
    all_posts = json.loads(posts_payload)
    if len(all_posts) != 35:
        raise RuntimeError(f"TAPPCO post denominator changed: {len(all_posts)}")
    excluded = {
        row["id"]: EXCLUDED_POST_IDS[row["id"]]
        for row in all_posts if row["id"] in EXCLUDED_POST_IDS
    }
    posts = [row for row in all_posts if row["id"] not in EXCLUDED_POST_IDS]
    if len(posts) != 33 or set(PRODUCTS) != {row["id"] for row in posts}:
        raise RuntimeError("TAPPCO reviewed 33-product post set changed")

    categories = json.loads(fetch(API_URL + "categories?per_page=100"))
    category_names = {row["id"]: clean_title(row["name"]) for row in categories}
    for category_id, expected_name in CATEGORY_NAMES.items():
        if category_names.get(category_id) != expected_name:
            raise RuntimeError(f"TAPPCO category changed: {category_id}")

    records = []
    post_facts = []
    pdf_observations = []
    for post in sorted(posts, key=lambda row: row["id"]):
        post_id = post["id"]
        base_name, family, grade_field, grades, common_specs = PRODUCTS[post_id]
        parser = FactParser()
        parser.feed(post["content"]["rendered"])
        description = re.sub(
            r"\s+", " ", html.unescape(" ".join(parser.text))
        ).strip()
        pdf_rows = []
        for pdf_url in sorted(set(parser.pdf_urls)):
            payload = fetch(pdf_url)
            pdf_row = {
                "url": pdf_url,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
            pdf_rows.append(pdf_row)
            pdf_observations.append(pdf_row)
        if post_id in MISMATCHED_TDS_POSTS and not pdf_rows:
            raise RuntimeError(f"Expected mismatched TAPPCO TDS missing: {post_id}")
        category = CATEGORY_NAMES[post["categories"][0]]
        source_title = clean_title(post["title"]["rendered"])
        source_flags = [
            "live_public_manufacturer_product_post",
            "card_modified_2020_or_2022_current_availability_unverified",
            "source_reported_specifications_not_independent_approvals",
        ]
        if not pdf_rows:
            source_flags.append("no_tds_link_on_live_product_card")
        if post_id in MISMATCHED_TDS_POSTS:
            source_flags.extend([
                "linked_tds_product_identity_mismatch",
                "mismatched_tds_technical_fields_not_assigned_to_product",
            ])
        for grade_index, grade in enumerate(grades, 1):
            specifications = {
                **common_specs,
                "source_grade": grade,
                "source_post_id": post_id,
                "source_category": category,
                "source_post_modified": post["modified"],
                "source_description_sha256": hashlib.sha256(
                    description.encode()
                ).hexdigest(),
                "source_tds_urls": [row["url"] for row in pdf_rows],
                "source_tds_sha256": [row["sha256"] for row in pdf_rows],
                "source_quality_flags": source_flags,
            }
            if grade_field:
                specifications[grade_field] = grade
            grade_suffix = f" {grade}" if grade else ""
            facts = {
                "post_id": post_id,
                "source_title": source_title,
                "base_name": base_name,
                "grade_field": grade_field,
                "grade": grade,
                "family": family,
                "category": category,
                "modified": post["modified"],
                "description_sha256": specifications[
                    "source_description_sha256"
                ],
                "pdf_rows": pdf_rows,
                "specifications": common_specs,
            }
            records.append({
                "source_id": SOURCE_ID,
                "source_record_id": (
                    f"TAPPCO-SD-{post_id}-{grade_index:02d}"
                ),
                "source_url": post["link"],
                "snapshot_date": SNAPSHOT_DATE,
                "market": "Sudan",
                "manufacturer": "TAPPCO Lubricants",
                "brand": "TAPPCO",
                "product_name": f"TAPPCO {base_name}{grade_suffix}",
                "source_product_name": source_title,
                "family_code": family,
                "evidence_status": "official_manufacturer_product_post_and_tds",
                "lifecycle_status": (
                    "live_product_post_historical_card_current_availability_unverified"
                ),
                "specifications": specifications,
                "source_facts_sha256": hashlib.sha256(
                    json.dumps(
                        facts, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest(),
            })
        post_facts.append({
            "post_id": post_id,
            "source_title": source_title,
            "category": category,
            "date": post["date"],
            "modified": post["modified"],
            "description_sha256": hashlib.sha256(description.encode()).hexdigest(),
            "pdf_rows": pdf_rows,
            "identity_rows": len(grades),
        })

    if len(records) != 73:
        raise RuntimeError(f"TAPPCO identity denominator changed: {len(records)}")
    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    category_counts = Counter(
        CATEGORY_NAMES[row["categories"][0]] for row in posts
    )
    family_counts = Counter(row["family_code"] for row in records)
    grade_counts = Counter(
        next(
            (
                field for field in (
                    "sae_engine", "sae_gear", "iso_vg", "nlgi", "dot",
                    "source_grade",
                )
                if field in row["specifications"]
            ),
            "ungraded",
        )
        for row in records
    )
    unique_pdf_hashes = {row["sha256"] for row in pdf_observations}
    report = {
        "schema_version": 1,
        "status": "live_complete_public_manufacturer_product_post_catalog",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "wordpress_all_posts": len(all_posts),
        "excluded_non_product_posts": excluded,
        "product_posts": len(posts),
        "category_counts": dict(sorted(category_counts.items())),
        "identity_rows": len(records),
        "family_identity_counts": dict(sorted(family_counts.items())),
        "grade_field_counts": dict(sorted(grade_counts.items())),
        "posts_without_tds": sum(
            not row["pdf_rows"] for row in post_facts
        ),
        "pdf_link_observations": len(pdf_observations),
        "unique_pdf_payloads": len(unique_pdf_hashes),
        "mismatched_tds_posts": MISMATCHED_TDS_POSTS,
        "mismatched_tds_count": len(MISMATCHED_TDS_POSTS),
        "post_facts": post_facts,
        "normalized_output_sha256": hashlib.sha256(
            output_text.encode()
        ).hexdigest(),
        "publication_scope": (
            "Factual product names, grades, category membership, source-reported "
            "standards and evidence hashes only; descriptions, TDS files, artwork "
            "and contacts are not redistributed."
        ),
        "denominator_note": (
            "The WordPress posts endpoint publishes 35 posts. Two are explicit "
            "non-product posts; all remaining 33 product posts in seven technical "
            "categories are included and expand to 73 reviewed product-grade "
            "identities. The WooCommerce product endpoint contains theme-demo "
            "apparel and is not a lubricant catalog."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "product_posts": len(posts),
        "identity_rows": len(records),
        "pdf_link_observations": len(pdf_observations),
        "unique_pdf_payloads": len(unique_pdf_hashes),
        "output_sha256": report["normalized_output_sha256"],
    }))


if __name__ == "__main__":
    main()
