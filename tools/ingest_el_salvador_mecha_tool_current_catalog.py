#!/usr/bin/env python3
"""Build the current Mecha-Tool / Valgab El Salvador catalog evidence layer.

The official WordPress catalog contains 26 current product cards.  Linked
technical documents expand the cards to 67 page/grade occurrences.  Eight
duplicate Forza turbine-grade occurrences are collapsed across an English and
a Spanish card, leaving 59 product identities.  Two identities (Mecha Tool
Full Synthetic 0W-20 and 5W-30) are explicit candidates for the already
ingested current GM dexos1 Gen3 licence records; the other 57 are new
manufacturer-catalog identities.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_OUT = ROOT / "data/el-salvador-mecha-tool-current-products.jsonl"
REPORT_OUT = ROOT / "data/el-salvador-mecha-tool-current-catalog-report.json"

SNAPSHOT_DATE = "2026-07-24"
SOURCE_ID = "EL_SALVADOR_MECHA_TOOL_CURRENT_CATALOG"
HOME_URL = "https://mechatoolsv.com/"
CATALOG_URL = "https://mechatoolsv.com/catalogo-de-productos/"
API_URL = (
    "https://mechatoolsv.com/wp-json/wp/v2/"
    "product?per_page=100&_embed=1"
)
MEDIA_API = "https://mechatoolsv.com/wp-json/wp/v2/media/"
UA = "MFClassifier evidence catalog/1.0"

EXPECTED_PRODUCT_IDS = [
    776, 901, 1001, 1027, 1051, 1067, 1092, 1105, 1113, 1197, 1212,
    1228, 1250, 1266, 1372, 1387, 1400, 1410, 1426, 1442, 1458, 1652,
    1682, 1701, 1712, 1719,
]
EXPECTED_PAGE_FACTS_SHA256 = (
    "2d27e15fc0bb678bc8fd4cd9c819597aecf0dce80ea4a845925826424f5dbd55"
)
EXPECTED_IMAGE_FACTS_SHA256 = (
    "690f33fe3993a1604bc443cd98de4368b53e49a0ff18aaeccb01bc7ec4b16ff5"
)
EXPECTED_DOCUMENT_FACTS_SHA256 = (
    "58e53c10e3e4b80d2438ad995345460b77c8f5c863111def06abd70096e030fa"
)


def tech(
    *,
    sae_engine="",
    iso_vg="",
    source_grade="",
    api=(),
    api_gl=(),
    acea=(),
    ilsac=(),
    coolant_class="",
    performance=(),
):
    return {
        "sae_engine": sae_engine,
        "sae_gear": "",
        "iso_vg": iso_vg,
        "nlgi": "",
        "source_grade": source_grade,
        "api": list(api),
        "api_gl": list(api_gl),
        "acea": list(acea),
        "ilsac": list(ilsac),
        "jaso": [],
        "dot": "",
        "coolant_class": coolant_class,
        "performance": list(performance),
    }


def item(
    pages,
    brand,
    name,
    family,
    technical,
    *,
    packages=(),
    flags=(),
    existing_gm_source_record_id="",
):
    page_ids = [pages] if isinstance(pages, int) else list(pages)
    return {
        "source_page_ids": page_ids,
        "brand": brand,
        "product_name": name,
        "family_code": family,
        "technical": technical,
        "packages": list(packages),
        "source_quality_flags": list(flags),
        "existing_gm_source_record_id": existing_gm_source_record_id,
    }


P = []

# Automotive engine oils.
P.append(item(
    776,
    "MECHA-TOOL",
    "MECHA-TOOL Diesel Engine Oil 15W-40 CI-4 Plus/SN",
    "M",
    tech(
        sae_engine="15W-40",
        api=("CI-4 Plus", "SN"),
        performance=(
            "Cummins CES 20078 (source-reported)",
            "Detroit Diesel 93K215 (source-reported)",
            "Volvo VDS-3 (source-reported)",
            "Mack EO-N Premium Plus (source-reported)",
            "Renault VI RLD-2 (source-reported)",
            "Caterpillar ECF-2 (source prints EFC-2; retained as source issue)",
        ),
    ),
    packages=("12 quarts", "3 gallons", "5 gallons", "55 gallons"),
    flags=(
        "linked_detroit_renewal_document_names_ck_4_sn_not_the_ci_4_plus_sn_page_product",
        "ck_4_claim_not_promoted_to_this_product_identity",
        "source_prints_caterpillar_efc_2_not_silently_corrected_to_ecf_2",
    ),
))

P += [
    item(
        1051,
        "MECHA-TOOL",
        "MECHA-TOOL Full Synthetic Motor Oil 5W-20",
        "M",
        tech(sae_engine="5W-20", api=("SP",), ilsac=("GF-6A",)),
        packages=("12 quarts", "3 x 5 quarts", "55 gallons"),
    ),
    item(
        1067,
        "MECHA-TOOL",
        "MECHA TOOL FULL SYNTHETIC",
        "M",
        tech(
            sae_engine="5W-30",
            api=("SN",),
            ilsac=("GF-6",),
            performance=("GM dexos1 Gen2 (linked 2022 source document)",),
        ),
        packages=("12 quarts", "3 x 5 quarts", "55 gallons"),
        flags=(
            "current_gm_registry_gen3_supersedes_linked_2022_gen2_document_for_licence_status",
        ),
        existing_gm_source_record_id="D330AAEI170",
    ),
    item(
        1067,
        "MECHA-TOOL",
        "MECHA TOOL FULL SYNTHETIC",
        "M",
        tech(
            sae_engine="0W-20",
            api=("SN",),
            ilsac=("GF-6",),
            performance=("GM dexos1 Gen2 (source-reported in linked series TDS)",),
        ),
        packages=("12 quarts", "3 x 5 quarts", "55 gallons"),
        flags=(
            "linked_series_tds_grade_without_dedicated_current_product_card",
            "current_gm_registry_gen3_supersedes_linked_gen2_series_claim_for_licence_status",
        ),
        existing_gm_source_record_id="D330BAFL170",
    ),
    item(
        1652,
        "MECHA-TOOL",
        "MECHA-TOOL Full Synthetic Motor Oil 10W-30",
        "M",
        tech(sae_engine="10W-30", api=("SP",), ilsac=("GF-6A",)),
        packages=("12 quarts", "3 x 5 quarts", "55 gallons"),
        flags=("ambiguous_tds_dexos_table_layout_not_promoted_to_approval",),
    ),
]

# The generic semi-synthetic card and TDS explicitly publish three grades.
for grade in ("5W-20", "5W-30", "15W-40"):
    P.append(item(
        1712,
        "MECHA-TOOL",
        f"MECHA-TOOL Semi-Synthetic Motor Oil {grade}",
        "M",
        tech(
            sae_engine=grade,
            api=("SN",),
            ilsac=("GF-5",) if grade in {"5W-20", "5W-30"} else (),
        ),
        packages=("12 quarts", "3 x 5 quarts", "55 gallons"),
    ))
P += [
    item(
        1105,
        "MECHA-TOOL",
        "MECHA-TOOL Semi-Synthetic Motor Oil 10W-30",
        "M",
        tech(sae_engine="10W-30"),
        flags=(
            "current_card_and_image_grade_not_present_in_linked_tds_property_table",
            "linked_sds_lists_grade_but_does_not_prove_api_performance",
        ),
    ),
    item(
        1092,
        "MECHA-TOOL",
        "MECHA-TOOL Synthetic Blend Motor Oil 20W-50",
        "M",
        tech(sae_engine="20W-50"),
        flags=(
            "current_card_and_image_grade_not_present_in_linked_tds_property_table",
            "linked_sds_lists_grade_but_does_not_prove_api_performance",
        ),
    ),
    item(
        1682,
        "MECHA-TOOL",
        "MECHA-TOOL Diesel Engine Oil 20W-50 CI-4/SL",
        "M",
        tech(sae_engine="20W-50", api=("CI-4", "SL")),
        packages=("12 quarts", "3 gallons", "5 gallons", "55 gallons"),
    ),
    item(
        1719,
        "VALGAB",
        "VALGAB Diesel Engine Oil 10W-30 CK-4",
        "M",
        tech(sae_engine="10W-30", api=("CK-4",)),
        flags=("identity_supported_by_current_card_title_and_pinned_product_image",),
    ),
]

# Natural-gas engine oils and locomotive oil.
P.append(item(
    1212,
    "MECHA-TOOL",
    "MECHA-TOOL NGEO Low Ash SAE 40",
    "M",
    tech(sae_engine="40", api=("CF",), source_grade="Low Ash"),
    packages=("55 gallons",),
))
for page, series, source_grade in (
    (1400, "NGEO Medium Ash", "Medium Ash"),
    (1410, "NGEO Low Ash Improved Formula", "Low Ash Improved Formula"),
    (1426, "NGEO Medium Ash Improved Formula", "Medium Ash Improved Formula"),
):
    for grade in ("40", "15W-40"):
        P.append(item(
            page,
            "MECHA-TOOL",
            f"MECHA-TOOL {series} {grade}",
            "M",
            tech(
                sae_engine=grade,
                api=("CF",),
                source_grade=source_grade,
                performance=("Cummins L10 & M11 (source-reported)",),
            ),
            packages=("5 gallons", "55 gallons"),
        ))
for grade in ("40", "20W-40"):
    P.append(item(
        1387,
        "MECHA-TOOL",
        f"MECHA-TOOL Locomotive Motor Oil RR Zinc-Free {grade}",
        "M",
        tech(
            sae_engine=grade,
            source_grade="RR Zinc-Free",
            performance=(
                "LMOA Generation 6 & 7 (source-reported)",
                "General Electric / Electro-Motive Diesel use (source-reported)",
            ),
        ),
        packages=("5 gallons", "55 gallons"),
    ))

# Hydraulic fluids.
for grade in ("32", "46", "68", "100", "220"):
    P.append(item(
        1113,
        "MECHA-TOOL",
        f"MECHA-TOOL Hydraulic Fluid AW ISO {grade}",
        "H",
        tech(iso_vg=grade, source_grade=f"AW-{grade}"),
        packages=("3 gallons", "5 gallons", "55 gallons"),
        flags=(
            "tds_available_grade_list_controls_identity",
            "tds_property_table_contains_iso_22_but_omits_listed_iso_220_review_required",
        ),
    ))
for grade in ("32", "46", "68"):
    P.append(item(
        1250,
        "MECHA-TOOL",
        f"MECHA-TOOL AW 100% Synthetic Hydraulic Fluid ISO {grade}",
        "H",
        tech(
            iso_vg=grade,
            source_grade=f"AW-{grade} Full Synthetic",
            performance=(
                "DIN 51524 Part II (source-reported)",
                "Denison HF-0/HF-1/HF-2 (source prints Dennison)",
            ),
        ),
        packages=("5 gallons", "55 gallons"),
        flags=(
            "iso_68_tds_property_row_duplicates_iso_46_values_source_issue_retained",
        ) if grade == "68" else (),
    ))
for grade in ("100", "150", "220", "320", "460"):
    P.append(item(
        1442,
        "MECHA-TOOL",
        f"MECHA-TOOL TEMPSA AW Industrial Hydraulic Fluid ISO {grade}",
        "H",
        tech(
            iso_vg=grade,
            source_grade=f"AW-{grade}",
            performance=(
                "DIN 51524 Part II (source-reported)",
                "Denison HF-0/HF-1/HF-2 (source prints Dennison)",
            ),
        ),
        packages=("5 gallons", "55 gallons"),
    ))

# Turbine fluids. Pages 1228 and 1458 are language variants of the exact same
# Forza product-grade series and therefore become one identity per grade.
for grade in ("32", "46", "68", "100"):
    P.append(item(
        1197,
        "MECHA-TOOL",
        f"MECHA-TOOL TEMPSA Turbine Fluid ISO {grade}",
        "U",
        tech(
            iso_vg=grade,
            source_grade="TEMPSA Zinc-Free R&O/HL",
            performance=(
                "DIN 51524 Part 1 (source-reported)",
                "MIL-L-17672C (source-reported)",
                "AFNOR E48-600 HL (source-reported)",
            ),
        ),
        packages=("5 gallons", "55 gallons"),
    ))
for grade in ("32", "46", "68", "100", "150", "220", "320", "460"):
    P.append(item(
        (1228, 1458),
        "MECHA-TOOL",
        f"MECHA-TOOL FORZA Turbine Fluid ISO {grade}",
        "U",
        tech(
            iso_vg=grade,
            source_grade="FORZA Zinc-Free R&O/HL",
            performance=(
                "DIN 51524 Part 1 (source-reported)",
                "MIL-L-17672C (source-reported)",
                "AFNOR E48-600 HL (source-reported)",
            ),
        ),
        packages=("5 gallons", "55 gallons"),
        flags=("duplicate_english_and_spanish_product_cards_collapsed",),
    ))

# Industrial gear and cutting oils.
for grade in ("100", "150", "220", "320", "460"):
    P.append(item(
        1372,
        "MECHA-TOOL",
        f"MECHA-TOOL Gear Oil EP ISO {grade}",
        "I",
        tech(
            iso_vg=grade,
            source_grade=f"AGMA {dict(zip(('100','150','220','320','460'), ('3EP','4EP','5EP','6EP','7EP')))[grade]}",
            api_gl=("GL-4",),
            performance=("AGMA 9005-D94 (source-reported)",),
        ),
        packages=("5 gallons", "55 gallons"),
    ))
for grade in ("32", "46"):
    P.append(item(
        1266,
        "MECHA-TOOL",
        f"MECHA-TOOL Cutting Oil Series ISO {grade}",
        "S",
        tech(iso_vg=grade, source_grade="Active cutting oil"),
        packages=("5 gallons", "55 gallons"),
    ))

# Coolants, corrosion inhibitor and ATF.
P += [
    item(
        901,
        "MECHA-TOOL",
        "MECHA-TOOL Antifreeze/Coolant Green Concentrate",
        "TF",
        tech(
            coolant_class="Concentrate",
            source_grade="Green ethylene glycol low-silicate",
            performance=(
                "ASTM D3306 (source-reported)",
                "ASTM D4985 (source-reported)",
                "ASTM D6210 (source-reported)",
            ),
        ),
    ),
    item(
        901,
        "MECHA-TOOL",
        "MECHA-TOOL Antifreeze/Coolant Green 50/50",
        "TF",
        tech(
            coolant_class="50/50",
            source_grade="Green ethylene glycol low-silicate",
            performance=(
                "ASTM D4656 (source-reported)",
                "ASTM D5345 (source-reported)",
            ),
        ),
    ),
    item(
        1001,
        "MECHA-TOOL",
        "MECHA-TOOL Radiator Anti-Rust Green Ready to Use",
        "TF",
        tech(
            coolant_class="Ready to use; not antifreeze",
            source_grade="Green sodium-nitrate corrosion inhibitor",
            performance=("ASTM D1384-87 test method (source-reported)",),
        ),
        packages=("1 gallon", "5 gallons", "55 gallons"),
        flags=("tds_explicitly_states_product_is_not_antifreeze",),
    ),
    item(
        1027,
        "VALGAB",
        "VALGAB Heavy Duty Extended Life Antifreeze/Coolant Concentrate",
        "TF",
        tech(
            coolant_class="Concentrate",
            source_grade="Red/pink ethylene glycol, silicate-free",
            performance=(
                "ASTM D3306 (source-reported)",
                "ASTM D6210 (source-reported)",
                "TMC RP 329 (source-reported)",
            ),
        ),
        packages=("6 x 1 gallon", "55 gallons"),
    ),
    item(
        1027,
        "VALGAB",
        "VALGAB Heavy Duty Extended Life Antifreeze/Coolant 50/50",
        "TF",
        tech(
            coolant_class="50/50",
            source_grade="Red/pink ethylene glycol, silicate-free",
            performance=(
                "ASTM D3306 (source-reported)",
                "ASTM D6210 (source-reported)",
                "TMC RP 329 (source-reported)",
            ),
        ),
        packages=("6 x 1 gallon", "5 gallons", "55 gallons"),
    ),
    item(
        1701,
        "MECHA-TOOL",
        "MECHA-TOOL ATF Compatible with Dexron III",
        "TF",
        tech(
            source_grade="ATF Dexron III / Mercon compatible",
            performance=(
                "Dexron III compatible (source-reported recommendation, not current GM licence)",
                "Mercon compatible (source-reported recommendation)",
            ),
        ),
        flags=(
            "compatibility_recommendation_not_represented_as_oem_approval",
        ),
    ),
]


def quoted_url(url):
    return urllib.parse.quote(url, safe=":/?&=%")


def get(url):
    request = urllib.request.Request(
        quoted_url(url),
        headers={"User-Agent": UA},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def canonical_json_sha(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(payload)


def extract_pdf_urls(rendered_html):
    return [
        raw.strip()
        for raw in re.findall(
            r"""href=["']([^"']+)""",
            html.unescape(rendered_html),
            re.I,
        )
        if ".pdf" in raw.lower()
    ]


def main():
    rows = json.loads(get(API_URL))
    rows.sort(key=lambda row: row["id"])
    if [row["id"] for row in rows] != EXPECTED_PRODUCT_IDS:
        raise RuntimeError("Mecha-Tool current product-card denominator changed")

    page_facts = []
    page_by_id = {}
    image_facts = []
    document_facts = []
    image_by_page = {}
    documents_by_page = {}

    for row in rows:
        categories = sorted(
            (term["id"], term["slug"], term["name"])
            for group in row.get("_embedded", {}).get("wp:term", [])
            for term in group
            if term["taxonomy"] == "product_cat"
        )
        media = json.loads(get(MEDIA_API + str(row["featured_media"])))
        image_url = media["source_url"]
        pdf_urls = extract_pdf_urls(row["content"]["rendered"])
        page_fact = {
            "id": row["id"],
            "modified_gmt": row["modified_gmt"],
            "link": row["link"],
            "title": row["title"]["rendered"],
            "content": row["content"]["rendered"],
            "categories": categories,
            "featured_media": row["featured_media"],
            "image_url": image_url,
            "pdfs": sorted(pdf_urls),
        }
        page_facts.append(page_fact)
        page_by_id[row["id"]] = page_fact

        image_payload = get(image_url)
        image_fact = {
            "product_id": row["id"],
            "url": image_url,
            "sha256": sha256(image_payload),
            "bytes": len(image_payload),
        }
        image_facts.append(image_fact)
        image_by_page[row["id"]] = image_fact

        page_documents = []
        for url in pdf_urls:
            payload = get(url)
            fact = {
                "product_id": row["id"],
                "url": url,
                "sha256": sha256(payload),
                "bytes": len(payload),
            }
            document_facts.append(fact)
            page_documents.append(fact)
        documents_by_page[row["id"]] = page_documents

    if canonical_json_sha(page_facts) != EXPECTED_PAGE_FACTS_SHA256:
        raise RuntimeError("Mecha-Tool normalized current page facts changed")
    if canonical_json_sha(image_facts) != EXPECTED_IMAGE_FACTS_SHA256:
        raise RuntimeError("Mecha-Tool current product image payloads changed")
    if canonical_json_sha(document_facts) != EXPECTED_DOCUMENT_FACTS_SHA256:
        raise RuntimeError("Mecha-Tool linked document payloads changed")
    if len(image_facts) != 26 or len(document_facts) != 37:
        raise RuntimeError("Mecha-Tool evidence denominator drift")
    if len({fact["sha256"] for fact in document_facts}) != 33:
        raise RuntimeError("Mecha-Tool unique document payload denominator drift")

    if len(P) != 59:
        raise RuntimeError(f"Mecha-Tool identity denominator drift: {len(P)}")
    if sum(len(row["source_page_ids"]) for row in P) != 67:
        raise RuntimeError("Mecha-Tool expanded page/grade occurrence drift")
    if Counter(row["brand"] for row in P) != {
        "MECHA-TOOL": 56,
        "VALGAB": 3,
    }:
        raise RuntimeError("Mecha-Tool brand distribution drift")
    if Counter(row["family_code"] for row in P) != {
        "M": 21,
        "TF": 6,
        "H": 13,
        "U": 12,
        "S": 2,
        "I": 5,
    }:
        raise RuntimeError("Mecha-Tool family distribution drift")
    if sum(bool(row["existing_gm_source_record_id"]) for row in P) != 2:
        raise RuntimeError("Mecha-Tool existing-GM match denominator drift")

    products = []
    for index, source in enumerate(P, 1):
        source_record_id = f"MECHA-SV-{index:03d}"
        pages = [page_by_id[page_id] for page_id in source["source_page_ids"]]
        supporting_documents = []
        seen_document = set()
        for page_id in source["source_page_ids"]:
            for document in documents_by_page[page_id]:
                identity = (document["url"], document["sha256"])
                if identity not in seen_document:
                    supporting_documents.append(document)
                    seen_document.add(identity)
        row = {
            "source_id": SOURCE_ID,
            "source_record_id": source_record_id,
            "source_page_ids": source["source_page_ids"],
            "source_page_urls": [page["link"] for page in pages],
            "source_page_titles": [page["title"] for page in pages],
            "source_page_modified_gmt": [page["modified_gmt"] for page in pages],
            "source_categories": sorted({
                category[2]
                for page in pages
                for category in page["categories"]
            }),
            "source_images": [
                image_by_page[page_id] for page_id in source["source_page_ids"]
            ],
            "supporting_documents": supporting_documents,
            "market": "El Salvador",
            "manufacturer": "M & J Sunshine, Corporation",
            "brand": source["brand"],
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "technical": source["technical"],
            "packages": source["packages"],
            "existing_gm_source_record_id": source[
                "existing_gm_source_record_id"
            ],
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_current_official_brand_catalog",
            "evidence_status": (
                "official_current_brand_catalog_and_linked_technical_documents"
            ),
            "source_quality_flags": [
                "official_current_brand_product_card",
                "all_current_product_image_payloads_sha256_verified",
                "all_linked_pdf_payloads_sha256_verified",
                "source_reported_oem_and_standard_claims_not_independent_approvals",
                *source["source_quality_flags"],
            ],
        }
        products.append(row)

    source_facts_sha = canonical_json_sha([
        {
            "source_record_id": row["source_record_id"],
            "source_page_ids": row["source_page_ids"],
            "brand": row["brand"],
            "product_name": row["product_name"],
            "family_code": row["family_code"],
            "technical": row["technical"],
            "packages": row["packages"],
            "source_images": row["source_images"],
            "supporting_documents": row["supporting_documents"],
        }
        for row in products
    ])
    for row in products:
        row["source_facts_sha256"] = source_facts_sha

    output = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in products
    ).encode()
    PRODUCT_OUT.write_bytes(output)

    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "source_url": HOME_URL,
        "catalog_url": CATALOG_URL,
        "api_url": API_URL,
        "current_product_cards": len(rows),
        "current_card_categories": dict(sorted(Counter(
            category[2]
            for page in page_facts
            for category in page["categories"]
        ).items())),
        "expanded_page_grade_occurrences": 67,
        "duplicate_forza_language_page_grade_occurrences_collapsed": 8,
        "normalized_product_identities": len(products),
        "existing_gm_dexos_identity_match_candidates": 2,
        "new_manufacturer_catalog_identity_candidates": 57,
        "product_images_audited": len(image_facts),
        "product_image_bytes": sum(fact["bytes"] for fact in image_facts),
        "linked_pdf_references_audited": len(document_facts),
        "unique_linked_pdf_payloads": len({
            fact["sha256"] for fact in document_facts
        }),
        "linked_pdf_reference_bytes": sum(
            fact["bytes"] for fact in document_facts
        ),
        "page_facts_sha256": EXPECTED_PAGE_FACTS_SHA256,
        "image_facts_sha256": EXPECTED_IMAGE_FACTS_SHA256,
        "document_facts_sha256": EXPECTED_DOCUMENT_FACTS_SHA256,
        "source_facts_sha256": source_facts_sha,
        "normalized_output_sha256": sha256(output),
        "brands": dict(sorted(Counter(
            row["brand"] for row in products
        ).items())),
        "families": dict(sorted(Counter(
            row["family_code"] for row in products
        ).items())),
        "existing_gm_matches": [
            {
                "source_record_id": row["source_record_id"],
                "product_name": row["product_name"],
                "sae_engine": row["technical"]["sae_engine"],
                "gm_source_record_id": row[
                    "existing_gm_source_record_id"
                ],
            }
            for row in products
            if row["existing_gm_source_record_id"]
        ],
        "quality_note": (
            "The source denominator is the complete current WordPress product "
            "catalog. Product cards are expanded only by explicit current "
            "card, image or linked-TDS grades. Conflicting or mislinked "
            "documents are flagged rather than used to silently upgrade API, "
            "OEM approval, ISO VG or licence status."
        ),
    }
    REPORT_OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "cards": len(rows),
        "page_grade_occurrences": 67,
        "identities": len(products),
        "existing_gm_matches": 2,
        "new_identity_candidates": 57,
        "normalized_output_sha256": report["normalized_output_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
