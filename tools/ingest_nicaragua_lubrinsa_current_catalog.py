#!/usr/bin/env python3
"""Audit Lubrinsa's current Nicaragua catalog without creating geo-duplicates.

Lubrinsa's WooCommerce API exposes a complete 55-card denominator.  Most
in-scope cards are Nicaragua availability occurrences for global Repsol
products, not new product truth.  They are therefore retained in a separate
availability layer.  Four AUTO-branded local automotive fluids visible in the
official product-card artwork are emitted as canonical product candidates.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_OUT = ROOT / "data/nicaragua-lubrinsa-current-local-fluids.jsonl"
AVAILABILITY_OUT = ROOT / "data/nicaragua-lubrinsa-current-availability.jsonl"
REPORT_OUT = ROOT / "data/nicaragua-lubrinsa-current-catalog-report.json"

SNAPSHOT_DATE = "2026-07-23"
SOURCE_ID = "NICARAGUA_LUBRINSA_CURRENT_CATALOG"
STORE_API = "https://www.lubrinsa.com/wp-json/wc/store/v1/products?per_page=100"
HOME_URL = "https://www.lubrinsa.com/"
RTCA_URL = (
    "https://www.ine.gob.ni/DGE/digesto/2021/"
    "NTON_14_008-04_RTCA_75.01.15.04._Aceite_lubricantes.pdf"
)
UA = "MFClassifier evidence catalog/1.0"

EXPECTED_PRODUCT_IDS = {
    4504, 4506, 4508, 4515, 4518, 4520, 4523, 4526, 4528, 4530, 4532,
    4534, 4536, 4538, 4540, 4542, 4544, 4546, 4548, 4550, 4552, 4554,
    4556, 4558, 4560, 4562, 4564, 4566, 4568, 4570, 4572, 4574, 4576,
    4578, 4580, 4582, 4584, 4586, 4588, 4590, 4592, 4594, 4596, 4598,
    4600, 4602, 4604, 4606, 4608, 4610, 4612, 4657, 4711, 4713, 4716,
}

LOCAL_PRODUCTS = {
    4610: {
        "product_name": "AUTO Coolant Green 32 oz",
        "source_grade": "green",
        "package": "32 oz",
    },
    4608: {
        "product_name": "AUTO Coolant Red 32 oz",
        "source_grade": "red",
        "package": "32 oz",
    },
    4606: {
        "product_name": "AUTO Power Steering Fluid",
        "source_grade": "",
        "package": "",
    },
    4604: {
        "product_name": "AUTO Power Brake Brake Fluid",
        "source_grade": "",
        "package": "",
    },
}

AUTO_EXCLUSIONS = {
    4612: "vehicle_care_vinyl_dressing_outside_catalog_scope",
    4602: "glass_cleaner_outside_catalog_scope",
    4600: "gasoline_injector_cleaner_outside_catalog_scope",
    4598: "diesel_injector_cleaner_outside_catalog_scope",
    4596: "vehicle_wax_outside_catalog_scope",
    4594: "generic_distilled_water_not_product_grade_identity",
    4592: "battery_electrolyte_activator_insufficient_product_grade_facts",
    4590: "upholstery_dressing_outside_catalog_scope",
    4588: "tire_dressing_outside_catalog_scope",
}

REPSOL_EXCLUSIONS = {
    4528: "cleaner_polish_outside_catalog_scope",
}

# Only package duplicates are grouped here.  Similar-looking names or grades
# remain separate unless the seller cards explicitly identify the same
# product line and viscosity.
DUPLICATE_IDENTITY_GROUPS = {
    4580: "REPSOL Navigator HQ GL-5 85W-140",
    4578: "REPSOL Navigator HQ GL-5 85W-140",
    4576: "REPSOL Navigator HQ GL-5 85W-140",
    4574: "REPSOL Giant 7530 15W-40 THPD",
    4572: "REPSOL Giant 7530 15W-40 THPD",
    4566: "REPSOL Giant 5510 15W-40",
    4564: "REPSOL Giant 5510 15W-40",
    4560: "REPSOL Giant 3020 25W-60",
    4558: "REPSOL Giant 3020 25W-60",
    4657: "REPSOL Giant 3010 25W-50",
    4556: "REPSOL Giant 3010 25W-50",
    4518: "REPSOL Leader Super 20W-50",
    4515: "REPSOL Leader Super 20W-50",
}


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def identity_hint(product: dict, brand: str) -> str:
    product_id = product["id"]
    if product_id in DUPLICATE_IDENTITY_GROUPS:
        return DUPLICATE_IDENTITY_GROUPS[product_id]
    name = compact_space(product["name"])
    return f"{brand} seller-card {product_id}: {name}"


def scope_status(product_id: int, categories: set[str]) -> tuple[str, str]:
    if product_id in LOCAL_PRODUCTS:
        return "canonical_local_product", ""
    if product_id in AUTO_EXCLUSIONS:
        return "report_only_excluded", AUTO_EXCLUSIONS[product_id]
    if product_id in REPSOL_EXCLUSIONS:
        return "report_only_excluded", REPSOL_EXCLUSIONS[product_id]
    if "repsol" in categories:
        return "global_product_nicaragua_availability", ""
    raise RuntimeError(f"unclassified Lubrinsa product {product_id}")


def main() -> None:
    api_payload = get(STORE_API)
    products = json.loads(api_payload)
    if len(products) != 55:
        raise RuntimeError(f"Lubrinsa catalog denominator changed: {len(products)}")
    ids = {product["id"] for product in products}
    if ids != EXPECTED_PRODUCT_IDS:
        raise RuntimeError(
            "Lubrinsa product ID set changed: "
            f"added={sorted(ids - EXPECTED_PRODUCT_IDS)} "
            f"removed={sorted(EXPECTED_PRODUCT_IDS - ids)}"
        )

    availability_rows = []
    image_facts = {}
    local_rows = []
    for product in sorted(products, key=lambda item: item["id"]):
        categories = {item["slug"] for item in product["categories"]}
        image = product["images"][0]
        image_payload = get(image["src"])
        image_sha = sha256(image_payload)
        image_facts[str(product["id"])] = {
            "url": image["src"],
            "sha256": image_sha,
            "bytes": len(image_payload),
        }
        brand = "Repsol" if "repsol" in categories else "AUTO"
        status, exclusion_reason = scope_status(product["id"], categories)
        row = {
            "source_id": SOURCE_ID,
            "source_record_id": f"LUBRINSA-NI-{product['id']}",
            "source_product_id": product["id"],
            "market": "Nicaragua",
            "seller": "Lubrinsa",
            "brand": brand,
            "source_product_name": compact_space(product["name"]),
            "identity_group_hint": identity_hint(product, brand),
            "scope_status": status,
            "exclusion_reason": exclusion_reason,
            "categories": sorted(categories),
            "source_url": product["permalink"],
            "source_image_url": image["src"],
            "source_image_sha256": image_sha,
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_current_official_distributor_catalog",
        }
        availability_rows.append(row)

        if product["id"] not in LOCAL_PRODUCTS:
            continue
        local = LOCAL_PRODUCTS[product["id"]]
        local_rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": row["source_record_id"],
            "source_product_id": product["id"],
            "market": "Nicaragua",
            "manufacturer": "",
            "brand": "AUTO",
            "product_name": local["product_name"],
            "source_product_name": row["source_product_name"],
            "family_code": "TF",
            "technical": {
                "sae_engine": "",
                "sae_gear": "",
                "api": [],
                "api_gl": [],
                "acea": [],
                "ilsac": [],
                "iso_vg": "",
                "nlgi": "",
                "source_grade": local["source_grade"],
                "performance": [],
            },
            "source_package": local["package"],
            "lifecycle_status": "listed_on_current_official_nicaraguan_distributor_catalog",
            "evidence_status": "official_local_distributor_product_card_artwork",
            "snapshot_date": SNAPSHOT_DATE,
            "source_url": row["source_url"],
            "source_image_url": row["source_image_url"],
            "source_image_sha256": row["source_image_sha256"],
            "source_quality_flags": [
                "AUTO_brand_read_from_official_product_card_artwork",
                "image_payload_sha256_verified",
                "no_unpublished_dot_coolant_or_oem_standard_inferred",
                "seller_listing_not_independent_performance_approval",
            ],
        })

    availability_bytes = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in availability_rows
    ).encode()
    product_facts = [
        {
            "source_record_id": row["source_record_id"],
            "product_name": row["product_name"],
            "source_image_sha256": row["source_image_sha256"],
        }
        for row in local_rows
    ]
    source_facts_sha = sha256(
        json.dumps(product_facts, ensure_ascii=False, sort_keys=True).encode()
    )
    for row in local_rows:
        row["source_facts_sha256"] = source_facts_sha
    product_bytes = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in local_rows
    ).encode()

    PRODUCT_OUT.write_bytes(product_bytes)
    AVAILABILITY_OUT.write_bytes(availability_bytes)

    status_counts = Counter(row["scope_status"] for row in availability_rows)
    category_counts = Counter(
        category for row in availability_rows for category in row["categories"]
    )
    grouped = defaultdict(list)
    for row in availability_rows:
        if row["scope_status"] != "report_only_excluded":
            grouped[row["identity_group_hint"]].append(row["source_product_id"])
    multi_offer_groups = {
        key: ids for key, ids in sorted(grouped.items()) if len(ids) > 1
    }
    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "store_api_url": STORE_API,
        "home_url": HOME_URL,
        "store_api_sha256": sha256(api_payload),
        "current_seller_cards": len(availability_rows),
        "current_repsol_seller_cards": sum(
            row["brand"] == "Repsol" for row in availability_rows
        ),
        "current_auto_seller_cards": sum(
            row["brand"] == "AUTO" for row in availability_rows
        ),
        "scope_status_counts": dict(sorted(status_counts.items())),
        "current_in_scope_availability_occurrences": sum(
            row["scope_status"] != "report_only_excluded"
            for row in availability_rows
        ),
        "current_in_scope_identity_hints_after_package_grouping": len(grouped),
        "repsol_identity_hints_after_package_grouping": len({
            row["identity_group_hint"]
            for row in availability_rows
            if row["brand"] == "Repsol"
            and row["scope_status"] != "report_only_excluded"
        }),
        "canonical_local_product_rows": len(local_rows),
        "multi_offer_identity_groups": multi_offer_groups,
        "category_occurrences": dict(sorted(category_counts.items())),
        "image_payloads_audited": len(image_facts),
        "image_bytes_audited": sum(item["bytes"] for item in image_facts.values()),
        "image_facts": image_facts,
        "source_facts_sha256": source_facts_sha,
        "normalized_product_output_sha256": sha256(product_bytes),
        "availability_output_sha256": sha256(availability_bytes),
        "regulatory_context": {
            "official_rtca_url": RTCA_URL,
            "finding": (
                "RTCA 75.01.15.04 requires each manufacturer or importer to "
                "register a quality profile with classification and viscosity "
                "grade, but no public product-level register was located in "
                "this audit."
            ),
        },
        "identity_policy": (
            "Repsol cards are retained as Nicaragua availability occurrences "
            "for a later global Repsol identity pass. They do not create "
            "country-specific canonical duplicates."
        ),
        "quality_note": (
            "AUTO product-card artwork proves labels and current seller "
            "presence only. No DOT class, coolant chemistry, OEM approval or "
            "manufacturer identity is inferred where the source does not "
            "publish it."
        ),
    }
    REPORT_OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "seller_cards": len(availability_rows),
        "in_scope_occurrences": report["current_in_scope_availability_occurrences"],
        "identity_hints": len(grouped),
        "canonical_local_rows": len(local_rows),
        "product_sha256": report["normalized_product_output_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
