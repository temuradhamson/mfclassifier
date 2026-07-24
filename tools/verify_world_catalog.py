#!/usr/bin/env python3
"""Verify reproducibility, provenance and quality gates for the world catalog seed."""

from __future__ import annotations

import ast
import hashlib
import gzip
import json
import lzma
import sqlite3
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def stream_sha256(stream) -> bytes:
    """Hash a file-like object without materializing large artifacts in RAM."""
    digest = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
    return digest.digest()


def sqlite_catalog_projection_sha256(path: Path) -> str:
    """Hash only the AIChilon catalog projection, not its mutable operations data."""
    queries = [
        ("brands", "SELECT id, code, name FROM brands ORDER BY id"),
        (
            "products",
            "SELECT id, brand_id, category, name, is_active, archive_type, archive_reason "
            "FROM products ORDER BY id",
        ),
        (
            "product_packages",
            "SELECT id, product_id, package_name, unit, quantity_per_package, is_active, "
            "weight_kg, density_kg_per_l, archive_type, archive_reason "
            "FROM product_packages ORDER BY id",
        ),
    ]
    digest = hashlib.sha256()
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        for label, query in queries:
            digest.update(f"{label}\n".encode())
            for row in db.execute(query):
                payload = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                digest.update(f"{payload}\n".encode())
    finally:
        db.close()
    return digest.hexdigest()


def main() -> None:
    report = json.loads((ROOT / "data/world-catalog-report.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "data/global-source-policy.json").read_text(encoding="utf-8"))
    policy_by_id = {source["source_id"]: source for source in policy["sources"]}
    jaso_report = json.loads((ROOT / "data/jaso-filed-oils-report.json").read_text(encoding="utf-8"))
    licensed_report = json.loads((ROOT / "data/official-licensed-products-report.json").read_text(encoding="utf-8"))
    biopreferred_report = json.loads((ROOT / "data/usda-biopreferred-products-report.json").read_text(encoding="utf-8"))
    zf_report = json.loads((ROOT / "data/zf-te-ml-approved-products-report.json").read_text(encoding="utf-8"))
    allison_report = json.loads((ROOT / "data/allison-approved-fluids-report.json").read_text(encoding="utf-8"))
    driventic_report = json.loads((ROOT / "data/driventic-diwa-approved-oils-report.json").read_text(encoding="utf-8"))
    mercedes_report = json.loads((ROOT / "data/mercedes-dtfr-approved-fluids-report.json").read_text(encoding="utf-8"))
    mercedes_bevo_report = json.loads((ROOT / "data/mercedes-bevo-approved-fluids-report.json").read_text(encoding="utf-8"))
    volvo_report = json.loads((ROOT / "data/volvo-genuine-fluids-report.json").read_text(encoding="utf-8"))
    mack_report = json.loads((ROOT / "data/mack-genuine-fluids-report.json").read_text(encoding="utf-8"))
    mack_rows = [json.loads(line) for line in (ROOT / "data/mack-genuine-fluids.jsonl").read_text(encoding="utf-8").splitlines() if line]
    mack_2014_report = json.loads((ROOT / "data/mack-2014-approved-oils-report.json").read_text(encoding="utf-8"))
    mack_2014_rows = [json.loads(line) for line in (ROOT / "data/mack-2014-approved-oils.jsonl").read_text(encoding="utf-8").splitlines() if line]
    cummins_valvoline_report = json.loads((ROOT / "data/cummins-valvoline-2022-products-report.json").read_text(encoding="utf-8"))
    cummins_valvoline_rows = [json.loads(line) for line in (ROOT / "data/cummins-valvoline-2022-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    taiwan_cpc_report = json.loads((ROOT / "data/taiwan-cpc-lubricant-products-report.json").read_text(encoding="utf-8"))
    taiwan_cpc_rows = [json.loads(line) for line in (ROOT / "data/taiwan-cpc-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    volvo_websds_report = json.loads((ROOT / "data/volvo-group-websds-lubricant-products-report.json").read_text(encoding="utf-8"))
    volvo_websds_rows = [json.loads(line) for line in (ROOT / "data/volvo-group-websds-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    parker_denison_report = json.loads((ROOT / "data/parker-denison-fluid-ratings-report.json").read_text(encoding="utf-8"))
    parker_denison_rows = [json.loads(line) for line in (ROOT / "data/parker-denison-fluid-ratings.jsonl").read_text(encoding="utf-8").splitlines() if line]
    scania_report = json.loads((ROOT / "data/scania-genuine-oils-report.json").read_text(encoding="utf-8"))
    scania_rows = [json.loads(line) for line in (ROOT / "data/scania-genuine-oils.jsonl").read_text(encoding="utf-8").splitlines() if line]
    brava_report = json.loads((ROOT / "data/brava-official-products-report.json").read_text(encoding="utf-8"))
    brava_rows = [json.loads(line) for line in (ROOT / "data/brava-official-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ceypetco_report = json.loads((ROOT / "data/ceypetco-lubricant-products-report.json").read_text(encoding="utf-8"))
    ceypetco_rows = [json.loads(line) for line in (ROOT / "data/ceypetco-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    pso_report = json.loads((ROOT / "data/pso-official-lubricant-products-report.json").read_text(encoding="utf-8"))
    pso_rows = [json.loads(line) for line in (ROOT / "data/pso-official-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    chevron_us_report = json.loads((ROOT / "data/chevron-us-current-products-report.json").read_text(encoding="utf-8"))
    chevron_us_rows = [json.loads(line) for line in (ROOT / "data/chevron-us-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    pertamina_report = json.loads((ROOT / "data/pertamina-official-lubricant-products-report.json").read_text(encoding="utf-8"))
    pertamina_rows = [json.loads(line) for line in (ROOT / "data/pertamina-official-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    man_report = json.loads((ROOT / "data/man-service-products-report.json").read_text(encoding="utf-8"))
    fuchs_report = json.loads((ROOT / "data/fuchs-india-products-report.json").read_text(encoding="utf-8"))
    fuchs_rows = [json.loads(line) for line in (ROOT / "data/fuchs-india-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_us_report = json.loads((ROOT / "data/fuchs-us-products-report.json").read_text(encoding="utf-8"))
    fuchs_us_rows = [json.loads(line) for line in (ROOT / "data/fuchs-us-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_germany_report = json.loads((ROOT / "data/fuchs-germany-products-report.json").read_text(encoding="utf-8"))
    fuchs_germany_rows = [json.loads(line) for line in (ROOT / "data/fuchs-germany-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_poland_report = json.loads((ROOT / "data/fuchs-poland-products-report.json").read_text(encoding="utf-8"))
    fuchs_poland_rows = [json.loads(line) for line in (ROOT / "data/fuchs-poland-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_italy_report = json.loads((ROOT / "data/fuchs-italy-products-report.json").read_text(encoding="utf-8"))
    fuchs_italy_rows = [json.loads(line) for line in (ROOT / "data/fuchs-italy-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_sweden_report = json.loads((ROOT / "data/fuchs-sweden-products-report.json").read_text(encoding="utf-8"))
    fuchs_sweden_rows = [json.loads(line) for line in (ROOT / "data/fuchs-sweden-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_spain_report = json.loads((ROOT / "data/fuchs-spain-products-report.json").read_text(encoding="utf-8"))
    fuchs_spain_rows = [json.loads(line) for line in (ROOT / "data/fuchs-spain-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_france_report = json.loads((ROOT / "data/fuchs-france-products-report.json").read_text(encoding="utf-8"))
    fuchs_france_rows = [json.loads(line) for line in (ROOT / "data/fuchs-france-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_turkey_report = json.loads((ROOT / "data/fuchs-turkey-products-report.json").read_text(encoding="utf-8"))
    fuchs_turkey_rows = [json.loads(line) for line in (ROOT / "data/fuchs-turkey-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_canada_report = json.loads((ROOT / "data/fuchs-canada-products-report.json").read_text(encoding="utf-8"))
    fuchs_canada_rows = [json.loads(line) for line in (ROOT / "data/fuchs-canada-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_china_report = json.loads((ROOT / "data/fuchs-china-products-report.json").read_text(encoding="utf-8"))
    fuchs_china_rows = [json.loads(line) for line in (ROOT / "data/fuchs-china-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_czech_report = json.loads((ROOT / "data/fuchs-czech-products-report.json").read_text(encoding="utf-8"))
    fuchs_czech_rows = [json.loads(line) for line in (ROOT / "data/fuchs-czech-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_mexico_report = json.loads((ROOT / "data/fuchs-mexico-products-report.json").read_text(encoding="utf-8"))
    fuchs_mexico_rows = [json.loads(line) for line in (ROOT / "data/fuchs-mexico-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_south_africa_report = json.loads((ROOT / "data/fuchs-south-africa-products-report.json").read_text(encoding="utf-8"))
    fuchs_south_africa_rows = [json.loads(line) for line in (ROOT / "data/fuchs-south-africa-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_brazil_report = json.loads((ROOT / "data/fuchs-brazil-products-report.json").read_text(encoding="utf-8"))
    fuchs_brazil_rows = [json.loads(line) for line in (ROOT / "data/fuchs-brazil-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_norway_report = json.loads((ROOT / "data/fuchs-norway-products-report.json").read_text(encoding="utf-8"))
    fuchs_norway_rows = [json.loads(line) for line in (ROOT / "data/fuchs-norway-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    fuchs_hungary_report = json.loads((ROOT / "data/fuchs-hungary-products-report.json").read_text(encoding="utf-8"))
    fuchs_hungary_rows = [json.loads(line) for line in (ROOT / "data/fuchs-hungary-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    additional_fuchs_specs = {
        "denmark": ("FUCHS_DENMARK_PRODUCT_FINDER", 641, 640, 1, 0, 0, 20, 628, 12, 638, 1, {"C": 35, "E": 1, "G": 137, "H": 66, "I": 65, "M": 66, "S": 47, "T": 93, "TF": 122, "U": 8}),
        "finland": ("FUCHS_FINLAND_PRODUCT_FINDER", 639, 599, 38, 0, 2, 5, 577, 22, 581, 0, {"C": 33, "E": 2, "G": 133, "H": 63, "I": 37, "M": 79, "S": 33, "T": 85, "TF": 128, "U": 6}),
        "portugal": ("FUCHS_PORTUGAL_PRODUCT_FINDER", 529, 484, 42, 2, 1, 2, 452, 32, 460, 10, {"C": 19, "E": 1, "G": 137, "H": 35, "I": 30, "M": 79, "S": 54, "T": 66, "TF": 62, "U": 1}),
        "romania": ("FUCHS_ROMANIA_PRODUCT_FINDER", 794, 691, 91, 1, 11, 1, 689, 2, 690, 1, {"C": 19, "E": 3, "G": 176, "H": 42, "I": 29, "M": 76, "S": 56, "T": 85, "TF": 204, "U": 1}),
        "austria": ("FUCHS_AUSTRIA_PRODUCT_FINDER", 1057, 952, 94, 6, 5, 0, 951, 1, 952, 0, {"C": 23, "E": 3, "G": 237, "H": 54, "I": 53, "M": 78, "S": 75, "T": 95, "TF": 333, "U": 1}),
        "greece": ("FUCHS_GREECE_PRODUCT_FINDER", 1074, 966, 97, 6, 5, 0, 965, 1, 966, 0, {"C": 23, "E": 3, "G": 237, "H": 55, "I": 57, "M": 84, "S": 75, "T": 96, "TF": 335, "U": 1}),
        "switzerland": ("FUCHS_SWITZERLAND_PRODUCT_FINDER", 1466, 1464, 0, 2, 0, 234, 1458, 6, 1458, 1, {"C": 66, "G": 317, "H": 174, "I": 42, "M": 103, "S": 139, "T": 146, "TF": 471, "U": 6}),
        "korea": ("FUCHS_KOREA_PRODUCT_FINDER", 249, 221, 28, 0, 0, 0, 181, 40, 181, 0, {"G": 12, "H": 11, "I": 3, "M": 67, "S": 16, "T": 34, "TF": 78}),
        "uae": ("FUCHS_UAE_PRODUCT_FINDER", 1073, 965, 97, 6, 5, 0, 963, 2, 964, 0, {"C": 23, "E": 3, "G": 237, "H": 55, "I": 57, "M": 83, "S": 75, "T": 96, "TF": 335, "U": 1}),
        "argentina": ("FUCHS_ARGENTINA_PRODUCT_FINDER", 35, 5, 30, 0, 0, 0, 5, 0, 5, 0, {"G": 4, "TF": 1}),
        "chile": ("FUCHS_CHILE_PRODUCT_FINDER", 549, 496, 49, 4, 0, 0, 493, 3, 494, 0, {"C": 16, "E": 3, "G": 173, "H": 72, "I": 34, "M": 30, "S": 31, "T": 72, "TF": 64, "U": 1}),
        "ukraine": ("FUCHS_UKRAINE_PRODUCT_FINDER", 918, 842, 65, 6, 4, 0, 835, 7, 841, 0, {"C": 15, "E": 3, "G": 204, "H": 31, "I": 49, "M": 88, "S": 72, "T": 92, "TF": 288}),
        "slovakia": ("FUCHS_SLOVAKIA_PRODUCT_FINDER", 1074, 966, 97, 6, 5, 0, 965, 1, 966, 0, {"C": 23, "E": 3, "G": 237, "H": 55, "I": 57, "M": 84, "S": 75, "T": 96, "TF": 335, "U": 1}),
        "slovenia": ("FUCHS_SLOVENIA_PRODUCT_FINDER", 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, {"M": 1}),
        "croatia": ("FUCHS_CROATIA_PRODUCT_FINDER", 1082, 975, 96, 6, 5, 0, 967, 8, 971, 0, {"C": 23, "E": 3, "G": 238, "H": 52, "I": 57, "M": 89, "S": 74, "T": 103, "TF": 335, "U": 1}),
        "saudi-arabia": ("FUCHS_SAUDI_ARABIA_PRODUCT_FINDER", 376, 360, 13, 0, 1, 1, 251, 109, 254, 1, {"C": 19, "E": 4, "G": 86, "H": 35, "I": 23, "M": 53, "S": 33, "T": 63, "TF": 42, "U": 2}),
        "macedonia": ("FUCHS_MACEDONIA_PRODUCT_FINDER", 1075, 948, 97, 6, 24, 0, 947, 1, 948, 0, {"C": 23, "E": 3, "G": 236, "H": 55, "I": 57, "M": 77, "S": 75, "T": 95, "TF": 326, "U": 1}),
    }
    additional_fuchs = {
        slug: {
            "report": json.loads((ROOT / f"data/fuchs-{slug}-products-report.json").read_text(encoding="utf-8")),
            "rows": [json.loads(line) for line in (ROOT / f"data/fuchs-{slug}-products.jsonl").read_text(encoding="utf-8").splitlines() if line],
        }
        for slug in additional_fuchs_specs
    }
    liqui_moly_report = json.loads((ROOT / "data/liqui-moly-2020-products-report.json").read_text(encoding="utf-8"))
    liqui_moly_rows = [json.loads(line) for line in (ROOT / "data/liqui-moly-2020-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    liqui_moly_current_report = json.loads((ROOT / "data/liqui-moly-current-products-report.json").read_text(encoding="utf-8"))
    liqui_moly_current_rows = [json.loads(line) for line in (ROOT / "data/liqui-moly-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    liqui_moly_lifecycle_rows = [json.loads(line) for line in (ROOT / "data/liqui-moly-2020-2026-lifecycle.jsonl").read_text(encoding="utf-8").splitlines() if line]
    anp_report = json.loads((ROOT / "data/anp-brazil-lubricant-products-report.json").read_text(encoding="utf-8"))
    anp_rows = [json.loads(line) for line in (ROOT / "data/anp-brazil-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    anp_monitoring_report = json.loads((ROOT / "data/anp-brazil-monitoring-report.json").read_text(encoding="utf-8"))
    anp_monitoring_rows = [json.loads(line) for line in (ROOT / "data/anp-brazil-monitoring-observations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    anp_monitoring_pdf_report = json.loads((ROOT / "data/anp-brazil-monitoring-pdf-report.json").read_text(encoding="utf-8"))
    anp_monitoring_pdf_rows = [json.loads(line) for line in (ROOT / "data/anp-brazil-monitoring-pdf-observations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    anp_monitoring_pdf_exception_report = json.loads((ROOT / "data/anp-brazil-monitoring-pdf-exceptions-report.json").read_text(encoding="utf-8"))
    anp_monitoring_pdf_exception_rows = [json.loads(line) for line in (ROOT / "data/anp-brazil-monitoring-pdf-exceptions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    indonesia_report = json.loads((ROOT / "data/indonesia-npt-lubricant-products-report.json").read_text(encoding="utf-8"))
    indonesia_rows = [json.loads(line) for line in (ROOT / "data/indonesia-npt-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    thailand_doeb_report = json.loads((ROOT / "data/thailand-doeb-lubricant-products-report.json").read_text(encoding="utf-8"))
    thailand_doeb_rows = [json.loads(line) for line in (ROOT / "data/thailand-doeb-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    dla_report = json.loads((ROOT / "data/dla-qpd-lubricant-products-report.json").read_text(encoding="utf-8"))
    dla_rows = [json.loads(line) for line in (ROOT / "data/dla-qpd-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    blue_angel_report = json.loads((ROOT / "data/blue-angel-de-uz-178-products-report.json").read_text(encoding="utf-8"))
    blue_angel_rows = [json.loads(line) for line in (ROOT / "data/blue-angel-de-uz-178-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    austrian_uz14_report = json.loads((ROOT / "data/austrian-ecolabel-uz14-products-report.json").read_text(encoding="utf-8"))
    austrian_uz14_rows = [json.loads(line) for line in (ROOT / "data/austrian-ecolabel-uz14-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    korea_ecolabel_report = json.loads((ROOT / "data/korea-ecolabel-el611-lubricants-report.json").read_text(encoding="utf-8"))
    korea_ecolabel_rows = [json.loads(line) for line in (ROOT / "data/korea-ecolabel-el611-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    korea_el509_report = json.loads((ROOT / "data/korea-ecolabel-el509-washer-fluids-report.json").read_text(encoding="utf-8"))
    korea_el509_rows = [json.loads(line) for line in (ROOT / "data/korea-ecolabel-el509-washer-fluids.jsonl").read_text(encoding="utf-8").splitlines() if line]
    green_choice_philippines_report = json.loads((ROOT / "data/green-choice-philippines-lubricants-report.json").read_text(encoding="utf-8"))
    green_choice_philippines_rows = [json.loads(line) for line in (ROOT / "data/green-choice-philippines-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    uae_moiat_report = json.loads((ROOT / "data/uae-moiat-conformity-products-report.json").read_text(encoding="utf-8"))
    uae_moiat_rows = [json.loads(line) for line in (ROOT / "data/uae-moiat-conformity-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    eaeu_conformity_report = json.loads((ROOT / "data/eaeu-conformity-lubricant-products-report.json").read_text(encoding="utf-8"))
    eaeu_conformity_rows = [json.loads(line) for line in (ROOT / "data/eaeu-conformity-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    epa_safer_choice_report = json.loads((ROOT / "data/epa-safer-choice-lubricants-report.json").read_text(encoding="utf-8"))
    epa_safer_choice_rows = [json.loads(line) for line in (ROOT / "data/epa-safer-choice-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    epa_chemexpo_report = json.loads((ROOT / "data/epa-chemexpo-lubricants-report.json").read_text(encoding="utf-8"))
    epa_chemexpo_rows = [json.loads(line) for line in (ROOT / "data/epa-chemexpo-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    psqca_report = json.loads((ROOT / "data/psqca-engine-oil-licences-report.json").read_text(encoding="utf-8"))
    psqca_rows = [json.loads(line) for line in (ROOT / "data/psqca-engine-oil-licences.jsonl").read_text(encoding="utf-8").splitlines() if line]
    tisi_report = json.loads((ROOT / "data/tisi-two-stroke-oil-licences-report.json").read_text(encoding="utf-8"))
    tisi_rows = [json.loads(line) for line in (ROOT / "data/tisi-two-stroke-oil-licences.jsonl").read_text(encoding="utf-8").splitlines() if line]
    samr_china_report = json.loads((ROOT / "data/samr-china-2025-nonconforming-fluids-report.json").read_text(encoding="utf-8"))
    samr_china_rows = [json.loads(line) for line in (ROOT / "data/samr-china-2025-nonconforming-fluids.jsonl").read_text(encoding="utf-8").splitlines() if line]
    samr_china_2023_report = json.loads((ROOT / "data/samr-china-2023-nonconforming-fluids-report.json").read_text(encoding="utf-8"))
    samr_china_2023_rows = [json.loads(line) for line in (ROOT / "data/samr-china-2023-nonconforming-fluids.jsonl").read_text(encoding="utf-8").splitlines() if line]
    samr_china_2024_report = json.loads((ROOT / "data/samr-china-2024-nonconforming-fuel-additives-report.json").read_text(encoding="utf-8"))
    samr_china_2024_rows = [json.loads(line) for line in (ROOT / "data/samr-china-2024-nonconforming-fuel-additives.jsonl").read_text(encoding="utf-8").splitlines() if line]
    shenzhen_china_2021_report = json.loads((ROOT / "data/shenzhen-2021-nonconforming-automotive-fluids-report.json").read_text(encoding="utf-8"))
    shenzhen_china_2021_rows = [json.loads(line) for line in (ROOT / "data/shenzhen-2021-nonconforming-automotive-fluids.jsonl").read_text(encoding="utf-8").splitlines() if line]
    shenzhen_china_2020_report = json.loads((ROOT / "data/shenzhen-2020-automotive-fluid-inspection-report.json").read_text(encoding="utf-8"))
    shenzhen_china_2020_rows = [json.loads(line) for line in (ROOT / "data/shenzhen-2020-automotive-fluid-inspection.jsonl").read_text(encoding="utf-8").splitlines() if line]
    shenzhen_china_2019_report = json.loads((ROOT / "data/shenzhen-2019-automotive-fluid-inspection-report.json").read_text(encoding="utf-8"))
    shenzhen_china_2019_rows = [json.loads(line) for line in (ROOT / "data/shenzhen-2019-automotive-fluid-inspection.jsonl").read_text(encoding="utf-8").splitlines() if line]
    shenzhen_china_2025_report = json.loads((ROOT / "data/shenzhen-2025-automotive-fluid-inspection-report.json").read_text(encoding="utf-8"))
    shenzhen_china_2025_rows = [json.loads(line) for line in (ROOT / "data/shenzhen-2025-automotive-fluid-inspection.jsonl").read_text(encoding="utf-8").splitlines() if line]
    shanghai_china_report = json.loads((ROOT / "data/shanghai-2023-2025-lubricant-inspections-report.json").read_text(encoding="utf-8"))
    shanghai_china_rows = [json.loads(line) for line in (ROOT / "data/shanghai-2023-2025-lubricant-inspections.jsonl").read_text(encoding="utf-8").splitlines() if line]
    beijing_china_report = json.loads((ROOT / "data/beijing-2018-automotive-fluid-inspections-report.json").read_text(encoding="utf-8"))
    beijing_china_rows = [json.loads(line) for line in (ROOT / "data/beijing-2018-automotive-fluid-inspections.jsonl").read_text(encoding="utf-8").splitlines() if line]
    shenzhen_china_2016_2017_report = json.loads((ROOT / "data/shenzhen-2016-2017-lubricant-inspections-report.json").read_text(encoding="utf-8"))
    shenzhen_china_2016_2017_rows = [json.loads(line) for line in (ROOT / "data/shenzhen-2016-2017-lubricant-inspections.jsonl").read_text(encoding="utf-8").splitlines() if line]
    qingdao_china_report = json.loads((ROOT / "data/qingdao-2021-2025-automotive-fluid-inspections-report.json").read_text(encoding="utf-8"))
    qingdao_china_rows = [json.loads(line) for line in (ROOT / "data/qingdao-2021-2025-automotive-fluid-inspections.jsonl").read_text(encoding="utf-8").splitlines() if line]
    jilin_china_report = json.loads((ROOT / "data/jilin-2024-2025-automotive-fluid-inspections-report.json").read_text(encoding="utf-8"))
    jilin_china_rows = [json.loads(line) for line in (ROOT / "data/jilin-2024-2025-automotive-fluid-inspections.jsonl").read_text(encoding="utf-8").splitlines() if line]
    wuxi_china_report = json.loads((ROOT / "data/wuxi-2024-lubricant-inspection-report.json").read_text(encoding="utf-8"))
    wuxi_china_rows = [json.loads(line) for line in (ROOT / "data/wuxi-2024-lubricant-inspection.jsonl").read_text(encoding="utf-8").splitlines() if line]
    yantai_china_report = json.loads((ROOT / "data/yantai-2025-gasoline-detergent-inspection-report.json").read_text(encoding="utf-8"))
    yantai_china_rows = [json.loads(line) for line in (ROOT / "data/yantai-2025-gasoline-detergent-inspection.jsonl").read_text(encoding="utf-8").splitlines() if line]
    offline_quality_audit = json.loads((ROOT / "data/world-catalog-offline-quality-audit.json").read_text(encoding="utf-8"))
    duplicate_triage = json.loads((ROOT / "data/world-catalog-duplicate-triage.json").read_text(encoding="utf-8"))
    philippines_bps_report = json.loads((ROOT / "data/philippines-bps-brake-fluid-products-report.json").read_text(encoding="utf-8"))
    philippines_bps_rows = [json.loads(line) for line in (ROOT / "data/philippines-bps-brake-fluid-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ghana_gsa_report = json.loads((ROOT / "data/ghana-gsa-certified-lubricant-products-report.json").read_text(encoding="utf-8"))
    ghana_gsa_rows = [json.loads(line) for line in (ROOT / "data/ghana-gsa-certified-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ecuador_inen_report = json.loads((ROOT / "data/ecuador-inen-certified-lubricants-report.json").read_text(encoding="utf-8"))
    ecuador_inen_rows = [json.loads(line) for line in (ROOT / "data/ecuador-inen-certified-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ecuador_inen_current_report = json.loads((ROOT / "data/ecuador-inen-current-certified-lubricants-report.json").read_text(encoding="utf-8"))
    ecuador_inen_current_rows = [json.loads(line) for line in (ROOT / "data/ecuador-inen-current-certified-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    peru_sunat_report = json.loads((ROOT / "data/peru-sunat-noncontrolled-lubricants-report.json").read_text(encoding="utf-8"))
    peru_sunat_rows = [json.loads(line) for line in (ROOT / "data/peru-sunat-noncontrolled-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    paraguay_dnit_report = json.loads((ROOT / "data/paraguay-dnit-lubricant-classifications-report.json").read_text(encoding="utf-8"))
    paraguay_dnit_rows = [json.loads(line) for line in (ROOT / "data/paraguay-dnit-lubricant-classifications.jsonl").read_text(encoding="utf-8").splitlines() if line]
    guatemala_siges_report = json.loads((ROOT / "data/guatemala-siges-lubricant-nomenclature-report.json").read_text(encoding="utf-8"))
    guatemala_siges_rows = [json.loads(line) for line in (ROOT / "data/guatemala-siges-lubricant-nomenclature.jsonl").read_text(encoding="utf-8").splitlines() if line]
    costa_rica_health_report = json.loads((ROOT / "data/costa-rica-health-registered-lubricants-report.json").read_text(encoding="utf-8"))
    costa_rica_health_rows = [json.loads(line) for line in (ROOT / "data/costa-rica-health-registered-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    bolivia_ypfb_report = json.loads((ROOT / "data/bolivia-ypfb-current-lubricants-report.json").read_text(encoding="utf-8"))
    bolivia_ypfb_rows = [json.loads(line) for line in (ROOT / "data/bolivia-ypfb-current-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    mozambique_petromoc_report = json.loads((ROOT / "data/mozambique-petromoc-legacy-report.json").read_text(encoding="utf-8"))
    mozambique_petromoc_rows = [json.loads(line) for line in (ROOT / "data/mozambique-petromoc-legacy-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    uganda_mpower_report = json.loads((ROOT / "data/uganda-mpower-current-report.json").read_text(encoding="utf-8"))
    uganda_mpower_rows = [json.loads(line) for line in (ROOT / "data/uganda-mpower-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rwanda_almc_report = json.loads((ROOT / "data/rwanda-almc-current-report.json").read_text(encoding="utf-8"))
    rwanda_almc_rows = [json.loads(line) for line in (ROOT / "data/rwanda-almc-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    burundi_mogas_report = json.loads((ROOT / "data/burundi-mogas-current-report.json").read_text(encoding="utf-8"))
    burundi_mogas_rows = [json.loads(line) for line in (ROOT / "data/burundi-mogas-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    mogas_global_market_report = json.loads((ROOT / "data/mogas-global-market-shop-report.json").read_text(encoding="utf-8"))
    mogas_global_market_rows = [json.loads(line) for line in (ROOT / "data/mogas-global-market-shop-observations.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rwanda_akinawa_report = json.loads((ROOT / "data/rwanda-akinawa-current-report.json").read_text(encoding="utf-8"))
    rwanda_akinawa_rows = [json.loads(line) for line in (ROOT / "data/rwanda-akinawa-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rwanda_rymax_report = json.loads((ROOT / "data/rwanda-rymax-current-report.json").read_text(encoding="utf-8"))
    rwanda_rymax_rows = [json.loads(line) for line in (ROOT / "data/rwanda-rymax-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    afal_east_africa_report = json.loads((ROOT / "data/afal-east-africa-featured-products-report.json").read_text(encoding="utf-8"))
    afal_east_africa_rows = [json.loads(line) for line in (ROOT / "data/afal-east-africa-featured-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    south_sudan_taam_report = json.loads((ROOT / "data/south-sudan-taam-pakelo-report.json").read_text(encoding="utf-8"))
    south_sudan_taam_rows = [json.loads(line) for line in (ROOT / "data/south-sudan-taam-pakelo-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    sudan_tappco_report = json.loads((ROOT / "data/sudan-tappco-report.json").read_text(encoding="utf-8"))
    sudan_tappco_rows = [json.loads(line) for line in (ROOT / "data/sudan-tappco-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ethiopia_noc_report = json.loads((ROOT / "data/ethiopia-noc-caltex-report.json").read_text(encoding="utf-8"))
    ethiopia_noc_rows = [json.loads(line) for line in (ROOT / "data/ethiopia-noc-caltex-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    scope_global_report = json.loads((ROOT / "data/scope-global-report.json").read_text(encoding="utf-8"))
    scope_global_rows = [json.loads(line) for line in (ROOT / "data/scope-global-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    angola_ngol_report = json.loads((ROOT / "data/angola-sonangol-ngol-report.json").read_text(encoding="utf-8"))
    angola_ngol_rows = [json.loads(line) for line in (ROOT / "data/angola-sonangol-ngol-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    madagascar_galana_report = json.loads((ROOT / "data/madagascar-galana-mobil-report.json").read_text(encoding="utf-8"))
    madagascar_galana_rows = [json.loads(line) for line in (ROOT / "data/madagascar-galana-mobil-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    comoros_sch_report = json.loads((ROOT / "data/comoros-sch-lubricant-scope-review.json").read_text(encoding="utf-8"))
    uruguay_ancap_report = json.loads((ROOT / "data/uruguay-ancap-current-lubricants-report.json").read_text(encoding="utf-8"))
    uruguay_ancap_rows = [json.loads(line) for line in (ROOT / "data/uruguay-ancap-current-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    colombia_terpel_report = json.loads((ROOT / "data/colombia-terpel-current-lubricants-report.json").read_text(encoding="utf-8"))
    colombia_terpel_rows = [json.loads(line) for line in (ROOT / "data/colombia-terpel-current-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    guyana_guyoil_report = json.loads((ROOT / "data/guyana-guyoil-current-lubricants-report.json").read_text(encoding="utf-8"))
    guyana_guyoil_rows = [json.loads(line) for line in (ROOT / "data/guyana-guyoil-current-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    suriname_powerfull_report = json.loads((ROOT / "data/suriname-powerfull-current-lubricants-report.json").read_text(encoding="utf-8"))
    suriname_powerfull_rows = [json.loads(line) for line in (ROOT / "data/suriname-powerfull-current-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    trinidad_tobago_np_ultra_report = json.loads((ROOT / "data/trinidad-tobago-np-ultra-current-lubricants-report.json").read_text(encoding="utf-8"))
    trinidad_tobago_np_ultra_rows = [json.loads(line) for line in (ROOT / "data/trinidad-tobago-np-ultra-current-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    venezuela_pdv_report = json.loads((ROOT / "data/venezuela-pdv-current-lubricants-report.json").read_text(encoding="utf-8"))
    venezuela_pdv_rows = [json.loads(line) for line in (ROOT / "data/venezuela-pdv-current-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    jamaica_futroil_tek_report = json.loads((ROOT / "data/jamaica-futroil-tek-current-lubricants-report.json").read_text(encoding="utf-8"))
    jamaica_futroil_tek_rows = [json.loads(line) for line in (ROOT / "data/jamaica-futroil-tek-current-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    cuba_cubalub_2007_report = json.loads((ROOT / "data/cuba-cubalub-2007-official-products-report.json").read_text(encoding="utf-8"))
    cuba_cubalub_2007_rows = [json.loads(line) for line in (ROOT / "data/cuba-cubalub-2007-official-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    panama_acodeco_2020_report = json.loads((ROOT / "data/panama-acodeco-2020-lubricant-price-survey-report.json").read_text(encoding="utf-8"))
    panama_acodeco_2020_rows = [json.loads(line) for line in (ROOT / "data/panama-acodeco-2020-lubricant-price-survey.jsonl").read_text(encoding="utf-8").splitlines() if line]
    nicaragua_lubrinsa_report = json.loads((ROOT / "data/nicaragua-lubrinsa-current-catalog-report.json").read_text(encoding="utf-8"))
    nicaragua_lubrinsa_rows = [json.loads(line) for line in (ROOT / "data/nicaragua-lubrinsa-current-local-fluids.jsonl").read_text(encoding="utf-8").splitlines() if line]
    nicaragua_lubrinsa_availability_rows = [json.loads(line) for line in (ROOT / "data/nicaragua-lubrinsa-current-availability.jsonl").read_text(encoding="utf-8").splitlines() if line]
    honduras_hondulub_report = json.loads((ROOT / "data/honduras-hondulub-current-catalog-report.json").read_text(encoding="utf-8"))
    honduras_hondulub_rows = [json.loads(line) for line in (ROOT / "data/honduras-hondulub-current-oil-star-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    honduras_hondulub_availability_rows = [json.loads(line) for line in (ROOT / "data/honduras-hondulub-current-availability.jsonl").read_text(encoding="utf-8").splitlines() if line]
    el_salvador_mecha_tool_report = json.loads((ROOT / "data/el-salvador-mecha-tool-current-catalog-report.json").read_text(encoding="utf-8"))
    el_salvador_mecha_tool_rows = [json.loads(line) for line in (ROOT / "data/el-salvador-mecha-tool-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    belize_ilb_report = json.loads((ROOT / "data/belize-ilb-current-catalog-report.json").read_text(encoding="utf-8"))
    belize_ilb_rows = [json.loads(line) for line in (ROOT / "data/belize-ilb-current-availability.jsonl").read_text(encoding="utf-8").splitlines() if line]
    belize_rymax_catalog_report = json.loads((ROOT / "data/belize-rymax-current-catalog-report.json").read_text(encoding="utf-8"))
    belize_rymax_assets_report = json.loads((ROOT / "data/belize-rymax-current-assets-report.json").read_text(encoding="utf-8"))
    belize_rymax_products_report = json.loads((ROOT / "data/belize-rymax-current-products-report.json").read_text(encoding="utf-8"))
    belize_rymax_rows = [json.loads(line) for line in (ROOT / "data/belize-rymax-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    bahamas_cbs_report = json.loads((ROOT / "data/bahamas-cbs-current-catalog-report.json").read_text(encoding="utf-8"))
    bahamas_cbs_rows = [json.loads(line) for line in (ROOT / "data/bahamas-cbs-current-availability.jsonl").read_text(encoding="utf-8").splitlines() if line]
    barbados_sol_report = json.loads((ROOT / "data/barbados-sol-recent-catalog-report.json").read_text(encoding="utf-8"))
    barbados_sol_rows = [json.loads(line) for line in (ROOT / "data/barbados-sol-recent-availability.jsonl").read_text(encoding="utf-8").splitlines() if line]
    shell_global_distributors_report = json.loads((ROOT / "data/shell-global-current-distributors-report.json").read_text(encoding="utf-8"))
    shell_global_distributor_rows = [json.loads(line) for line in (ROOT / "data/shell-global-current-distributors.jsonl").read_text(encoding="utf-8").splitlines() if line]
    castrol_global_distributors_report = json.loads((ROOT / "data/castrol-global-current-distributors-report.json").read_text(encoding="utf-8"))
    castrol_global_distributor_rows = [json.loads(line) for line in (ROOT / "data/castrol-global-current-distributors.jsonl").read_text(encoding="utf-8").splitlines() if line]
    dominican_imca_mobil_report = json.loads((ROOT / "data/dominican-republic-imca-mobil-2025-report.json").read_text(encoding="utf-8"))
    dominican_imca_mobil_rows = [json.loads(line) for line in (ROOT / "data/dominican-republic-imca-mobil-2025-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    dominican_imca_mobil_web_report = json.loads((ROOT / "data/dominican-republic-imca-mobil-web-report.json").read_text(encoding="utf-8"))
    dominican_imca_mobil_web_rows = [json.loads(line) for line in (ROOT / "data/dominican-republic-imca-mobil-web-pages.jsonl").read_text(encoding="utf-8").splitlines() if line]
    mag1_current_report = json.loads((ROOT / "data/mag1-current-official-catalog-report.json").read_text(encoding="utf-8"))
    mag1_current_rows = [json.loads(line) for line in (ROOT / "data/mag1-current-official-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    mag1_current_exclusions = [json.loads(line) for line in (ROOT / "data/mag1-current-official-exclusions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    haiti_lubex_mag1_report = json.loads((ROOT / "data/haiti-lubex-mag1-current-presence-report.json").read_text(encoding="utf-8"))
    haiti_lubex_mag1_rows = [json.loads(line) for line in (ROOT / "data/haiti-lubex-mag1-current-presence.jsonl").read_text(encoding="utf-8").splitlines() if line]
    antigua_vadd_shell_report = json.loads((ROOT / "data/antigua-vadd-shell-current-presence-report.json").read_text(encoding="utf-8"))
    antigua_vadd_shell_rows = [json.loads(line) for line in (ROOT / "data/antigua-vadd-shell-current-presence.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rubis_caribbean_total_report = json.loads((ROOT / "data/rubis-caribbean-total-current-presence-report.json").read_text(encoding="utf-8"))
    rubis_caribbean_total_rows = [json.loads(line) for line in (ROOT / "data/rubis-caribbean-total-current-presence.jsonl").read_text(encoding="utf-8").splitlines() if line]
    grenada_sol_report = json.loads((ROOT / "data/grenada-sol-current-catalog-report.json").read_text(encoding="utf-8"))
    grenada_sol_sku_rows = [json.loads(line) for line in (ROOT / "data/grenada-sol-current-skus.jsonl").read_text(encoding="utf-8").splitlines() if line]
    grenada_sol_product_rows = [json.loads(line) for line in (ROOT / "data/grenada-sol-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    np_ultra_export_presence_report = json.loads((ROOT / "data/np-ultra-current-export-presence-report.json").read_text(encoding="utf-8"))
    np_ultra_export_presence_rows = [json.loads(line) for line in (ROOT / "data/np-ultra-current-export-presence.jsonl").read_text(encoding="utf-8").splitlines() if line]
    cayman_ace_report = json.loads((ROOT / "data/cayman-ace-current-automotive-report.json").read_text(encoding="utf-8"))
    cayman_ace_sku_rows = [json.loads(line) for line in (ROOT / "data/cayman-ace-current-automotive-fluids.jsonl").read_text(encoding="utf-8").splitlines() if line]
    cayman_ace_product_rows = [json.loads(line) for line in (ROOT / "data/cayman-ace-current-automotive-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    cayman_ace_exclusions = [json.loads(line) for line in (ROOT / "data/cayman-ace-current-automotive-exclusions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    zambia_gearpros_report = json.loads((ROOT / "data/zambia-gearpros-current-report.json").read_text(encoding="utf-8"))
    zambia_gearpros_sku_rows = [json.loads(line) for line in (ROOT / "data/zambia-gearpros-current-skus.jsonl").read_text(encoding="utf-8").splitlines() if line]
    zambia_gearpros_product_rows = [json.loads(line) for line in (ROOT / "data/zambia-gearpros-current-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    kebs_smark_report = json.loads((ROOT / "data/kebs-smark-lubricant-products-report.json").read_text(encoding="utf-8"))
    kebs_smark_rows = [json.loads(line) for line in (ROOT / "data/kebs-smark-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    east_africa_report = json.loads((ROOT / "data/east-africa-certified-lubricant-products-report.json").read_text(encoding="utf-8"))
    east_africa_rows = [json.loads(line) for line in (ROOT / "data/east-africa-certified-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    son_mancap_report = json.loads((ROOT / "data/son-mancap-chemical-lubricant-products-report.json").read_text(encoding="utf-8"))
    son_mancap_rows = [json.loads(line) for line in (ROOT / "data/son-mancap-chemical-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rsb_smark_report = json.loads((ROOT / "data/rsb-smark-lubricant-products-report.json").read_text(encoding="utf-8"))
    rsb_smark_rows = [json.loads(line) for line in (ROOT / "data/rsb-smark-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    jsonl_gz_path = ROOT / "data/world-catalog-products.jsonl.gz"
    jsonl_rows = 0
    jsonl_product_ids = set()
    jsonl_canonical_key_hashes = set()
    with gzip.open(jsonl_gz_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            jsonl_rows += 1
            assert row["product_name_normalized"]
            assert row["canonical_key"].split("|", 1)[0]
            assert row["product_id"] not in jsonl_product_ids
            jsonl_product_ids.add(row["product_id"])
            canonical_key_hash = hashlib.sha256(row["canonical_key"].encode()).digest()
            assert canonical_key_hash not in jsonl_canonical_key_hashes
            jsonl_canonical_key_hashes.add(canonical_key_hash)
    local_jsonl_path = ROOT / "data/world-catalog-products.jsonl"
    if local_jsonl_path.exists():
        with local_jsonl_path.open("rb") as plain, gzip.open(jsonl_gz_path, "rb") as packed:
            assert stream_sha256(plain) == stream_sha256(packed)
    assert report["status"] == "seed_only_world_catalog_incomplete"
    assert report["confirmed_world_total"] is None
    assert jsonl_rows == report["canonical_rows"]
    assert len(jsonl_product_ids) == jsonl_rows
    assert len(jsonl_canonical_key_hashes) == jsonl_rows
    del jsonl_product_ids, jsonl_canonical_key_hashes
    assert report["normalized_input_sha256"] == hashlib.sha256((ROOT / "data/catalog-v3.json").read_bytes()).hexdigest()

    for source in policy["sources"]:
        if source.get("source_locator") and source.get("source_sha256"):
            source_path = ROOT / source["source_locator"]
            if source.get("source_hash_scope") == "sqlite_catalog_projection_v1":
                actual = sqlite_catalog_projection_sha256(source_path)
            else:
                actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
            assert actual == source["source_sha256"], source["source_id"]
        if not source["bulk_ingest_allowed"]:
            assert source["source_id"] in report["bulk_sources_blocked"]

    db = sqlite3.connect(ROOT / "data/world-catalog.sqlite3")
    with (ROOT / "data/world-catalog.sqlite3").open("rb") as plain, lzma.open(ROOT / "data/world-catalog.sqlite3.xz", "rb") as packed:
        assert stream_sha256(plain) == stream_sha256(packed)
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert db.execute("SELECT count(*) FROM products").fetchone()[0] == jsonl_rows
    assert jsonl_rows == (
        101505
        + report["anp_brazil_monitoring_historical_identities_added"]
        + report["qingdao_china_products_added"]
        + report["jilin_china_products_added"]
        + report["wuxi_china_products_added"]
        + report["yantai_china_products_added"]
        + report["ecuador_inen_current_source_rows"]
        + report["ecuador_inen_announcement_products_added"]
        + report["peru_sunat_noncontrolled_source_rows"]
        + report["paraguay_dnit_lubricant_source_rows"]
        + report["guatemala_siges_lubricant_source_rows"]
        + report["costa_rica_health_lubricant_source_rows"]
        + report["bolivia_ypfb_lubricant_source_rows"]
        + report["mozambique_petromoc_legacy_source_rows"]
        + report["uganda_mpower_current_source_rows"]
        + report["rwanda_almc_current_source_rows"]
        + report["burundi_mogas_current_source_rows"]
        + report["rwanda_akinawa_current_source_rows"]
        + report["rwanda_rymax_products_added"]
        + report["afal_east_africa_featured_source_rows"]
        + report["south_sudan_taam_pakelo_products_added"]
        + report["sudan_tappco_products_added"]
        + report["ethiopia_noc_caltex_products_added"]
        + report["scope_global_products_added"]
        + report["angola_sonangol_ngol_products_added"]
        + report["madagascar_galana_mobil_products_added"]
        + report["chevron_us_current_products_added"]
        + len(uruguay_ancap_rows)
        + len(colombia_terpel_rows)
        + len(guyana_guyoil_rows)
        + len(suriname_powerfull_rows)
        + len(trinidad_tobago_np_ultra_rows)
        + len(venezuela_pdv_rows)
        + len(jamaica_futroil_tek_rows)
        + len(cuba_cubalub_2007_rows)
        + len(panama_acodeco_2020_rows)
        + len(nicaragua_lubrinsa_rows)
        + len(honduras_hondulub_rows)
        + el_salvador_mecha_tool_report[
            "new_manufacturer_catalog_identity_candidates"
        ]
        + len(belize_rymax_rows)
        + report["dominican_imca_mobil_products_added"]
        + report["mag1_current_products_added"]
        + report["grenada_sol_products_added"]
        + report["cayman_ace_products_added"]
        + report["zambia_gearpros_products_added"]
        - report["gm_dual_standard_license_rows_merged"]
        - report["fuchs_exact_payload_identity_rows_matched"]
        - report["fuchs_exact_content_identity_rows_matched"]
        - report["fuchs_unique_description_identity_rows_matched"]
        - report["fuchs_exact_technical_identity_rows_matched"]
    )
    assert report["jaso_source_rows"] == jaso_report["rows"] == 3630
    assert report["jaso_unique_oil_codes"] == jaso_report["unique_oil_codes"] == 3629
    assert report["official_filed_registry_rows"] == 3629
    assert report["official_licensed_source_rows"] == licensed_report["rows"] == 3037
    assert report["official_licensed_registry_rows"] == 3030
    assert report["official_licensed_canonical_records_before_global_deduplication"] == 3030
    assert report["gm_dual_standard_license_rows_merged"] == 7
    assert report["gm_license_code_name_collisions_retained"] == 1
    for source in licensed_report["sources"]:
        assert db.execute(
            "SELECT count(*) FROM product_sources WHERE source_id=?", (source["source_id"],)
        ).fetchone()[0] == source["rows"]
    assert report["blue_angel_source_rows"] == blue_angel_report["normalized_products"] == len(blue_angel_rows) == 148
    assert report["blue_angel_products_matched_to_existing"] == 21
    assert report["blue_angel_products_added"] == report["official_ecolabel_product_registry_rows"] == 127
    assert report["austrian_ecolabel_uz14_source_rows"] == austrian_uz14_report["normalized_products"] == len(austrian_uz14_rows) == 11
    assert report["austrian_ecolabel_uz14_products_matched_to_existing"] == 10
    assert report["austrian_ecolabel_uz14_cross_family_evidence_matches"] == 3
    assert report["austrian_ecolabel_uz14_products_added"] == 1
    assert report["scania_genuine_source_rows"] == scania_report["normalized_products"] == len(scania_rows) == 4
    assert scania_report["families"] == {"M": 4}
    assert scania_report["rows_with_sae"] == 2
    assert scania_report["rows_with_acea"] == 1
    assert report["scania_genuine_input_sha256"] == scania_report["normalized_output_sha256"]
    assert policy_by_id["SCANIA_GENUINE_ENGINE_OILS"]["source_sha256"] == scania_report["normalized_output_sha256"]
    assert policy_by_id["SCANIA_GENUINE_ENGINE_OILS"]["observed_count"] == 4
    assert all(row["family_code"] == "M" for row in scania_rows)
    assert all(row["lifecycle_status"] == "listed_on_current_regional_page_status_not_individually_dated" for row in scania_rows)
    assert all(not ({"description", "image", "logo", "marketing_text"} & set(row)) for row in scania_rows)
    ldf4 = next(row for row in scania_rows if row["product_name"] == "Scania Oil LDF-4")
    assert not ldf4["specifications"].get("sae_engine")
    assert report["brava_official_source_rows"] == brava_report["normalized_product_grade_rows"] == len(brava_rows) == 69
    assert brava_report["source_product_pages"] == 30
    assert brava_report["families"] == {"H": 5, "I": 2, "M": 42, "T": 13, "TF": 4, "U": 3}
    assert brava_report["rows_with_sae"] == 48
    assert brava_report["rows_with_iso_vg"] == 7
    assert brava_report["package_occurrences"] == 94
    assert brava_report["unique_part_numbers"] == 93
    assert brava_report["colliding_part_numbers"] == {
        "BRA-119-D": ["Brava Aurum 5W-20", "Brava Ignis 5W-20"],
    }
    assert brava_report["source_quality_flags"] == {
        "nonstandard_acea_class_source_reported_verbatim": 1,
        "source_part_number_cross_product_collision": 2,
        "source_part_number_placeholder_excluded": 2,
        "vague_additional_specifications_not_enumerated": 1,
    }
    assert report["brava_official_input_sha256"] == brava_report["normalized_output_sha256"]
    assert policy_by_id["BRAVA_LUBRICANTS_OFFICIAL_CATALOG"]["source_sha256"] == brava_report["normalized_output_sha256"]
    assert policy_by_id["BRAVA_LUBRICANTS_OFFICIAL_CATALOG"]["observed_count"] == 69
    assert len({row["source_record_id"] for row in brava_rows}) == 69
    assert len({row["product_name"] for row in brava_rows}) == 69
    assert all(row["manufacturer"] == "Olein Refinery Corp." for row in brava_rows)
    assert all(not ({"description", "image", "logo", "marketing_text"} & set(row)) for row in brava_rows)
    assert sum("nonstandard_acea_class_source_reported_verbatim" in row["source_quality_flags"] for row in brava_rows) == 1
    assert report["pso_official_source_rows"] == pso_report["normalized_product_grade_rows"] == len(pso_rows) == 124
    assert report["pso_official_products_matched_to_existing"] == 1
    assert report["pso_official_products_added"] == 123
    assert report["pso_official_input_sha256"] == pso_report["output_sha256"]
    assert policy_by_id["PAKISTAN_STATE_OIL_OFFICIAL_CATALOG"]["source_sha256"] == pso_report["output_sha256"]
    assert policy_by_id["PAKISTAN_STATE_OIL_OFFICIAL_CATALOG"]["observed_count"] == 124
    assert pso_report["source_product_series_pages"] == pso_report["source_pds_documents"] == 43
    assert pso_report["grade_evidence"] == {
        "current_product_page_only_not_observed_in_linked_pds": 2,
        "linked_current_product_data_sheet": 122,
    }
    assert pso_report["families"] == {"C": 8, "E": 1, "G": 9, "H": 14, "I": 33, "M": 25, "S": 10, "T": 17, "TF": 3, "U": 4}
    assert all(row["publication_restriction"] == "noncommercial_informational_use_with_attribution" for row in pso_rows)
    assert all(not ({"description", "marketing_text", "document_text", "artwork", "image"} & set(row)) for row in pso_rows)
    assert report["pertamina_official_source_rows"] == pertamina_report["normalized_product_grade_rows"] == len(pertamina_rows) == 250
    assert report["pertamina_official_products_exact_matched_to_existing"] == 77
    assert report["pertamina_official_products_blank_npt_fallback_matched"] == 11
    assert report["pertamina_official_products_added"] == 162
    assert report["pertamina_official_ambiguous_rows_added_separately"] == 8
    assert len(report["pertamina_official_cross_family_corrections"]) == 6
    assert report["pertamina_official_input_sha256"] == pertamina_report["output_sha256"]
    assert policy_by_id["PERTAMINA_LUBRICANTS_OFFICIAL_CATALOG"]["source_sha256"] == pertamina_report["output_sha256"]
    assert policy_by_id["PERTAMINA_LUBRICANTS_OFFICIAL_CATALOG"]["observed_count"] == 250
    assert pertamina_report["source_industrial_cards"] == pertamina_report["source_industrial_pds_documents"] == 104
    assert pertamina_report["industrial_product_grade_occurrences"] == 231
    assert pertamina_report["source_automotive_cards"] == 22
    assert pertamina_report["automotive_product_occurrences_retained"] == 21
    assert pertamina_report["source_product_occurrences_retained"] == 252
    assert pertamina_report["within_source_repeat_occurrences_merged"] == 2
    assert pertamina_report["families"] == {"C": 21, "E": 2, "G": 14, "H": 34, "I": 43, "M": 79, "S": 2, "T": 38, "TF": 8, "U": 9}
    assert pertamina_report["grade_kinds"] == {"iso_vg": 114, "nlgi": 13, "sae_engine": 84, "sae_gear": 6, "source_variant": 6, "ungraded": 27}
    assert sum("linked_pds_title_conflicts_with_current_product_card" in row["source_quality_flags"] for row in pertamina_rows) == 1
    assert all(not ({"description", "marketing_text", "document_text", "artwork", "image"} & set(row)) for row in pertamina_rows)
    assert report["mack_genuine_source_rows"] == mack_report["products"] == len(mack_rows) == 15
    assert report["mack_genuine_input_sha256"] == mack_report["normalized_output_sha256"]
    assert policy_by_id["MACK_GENUINE_FLUIDS"]["source_sha256"] == mack_report["normalized_output_sha256"]
    assert policy_by_id["MACK_GENUINE_FLUIDS"]["observed_count"] == 15
    assert mack_report["families"] == {"G": 2, "H": 1, "M": 3, "T": 6, "TF": 3}
    assert mack_report["package_occurrences"] == 32
    assert mack_report["sds_catalog_part_numbers"] == 32
    assert mack_report["unique_part_numbers_all_official_pages"] == 38
    assert sum("source_sds_link_target_name_mismatch_not_used_as_technical_evidence" in row["source_quality_flags"] for row in mack_rows) == 2
    assert sum("source_part_number_contains_embedded_formatting_spaces_retained_verbatim" in row["source_quality_flags"] for row in mack_rows) == 2
    assert sum("source_mack_standard_37319_retained_verbatim_not_silently_corrected" in row["source_quality_flags"] for row in mack_rows) == 1
    assert mack_report["source_quality_flags"] == {
        "official_regional_part_number_variants_preserved_separately": 4,
        "source_mack_standard_37319_retained_verbatim_not_silently_corrected": 1,
        "source_part_number_contains_embedded_formatting_spaces_retained_verbatim": 2,
        "source_sds_link_target_name_mismatch_not_used_as_technical_evidence": 2,
    }
    assert all(not ({"description", "image", "logo", "marketing_text"} & set(row)) for row in mack_rows)
    assert report["mack_2014_approved_source_rows"] == mack_2014_report["normalized_products"] == len(mack_2014_rows) == 803
    assert report["mack_2014_approved_input_sha256"] == mack_2014_report["normalized_output_sha256"]
    assert policy_by_id["MACK_2014_APPROVED_OILS"]["source_sha256"] == mack_2014_report["normalized_output_sha256"]
    assert policy_by_id["MACK_2014_APPROVED_OILS"]["observed_count"] == 803
    assert mack_2014_report["document_date"] == "2014-04"
    assert mack_2014_report["pdf_pages"] == 29
    assert mack_2014_report["approval_occurrences"] == 806
    assert mack_2014_report["source_section_product_grade_rows"] == 805
    assert mack_2014_report["duplicate_source_occurrences_merged"] == 1
    assert mack_2014_report["cross_section_or_notation_identity_merges"] == 2
    assert mack_2014_report["families"] == {"M": 479, "T": 324}
    assert mack_2014_report["source_quality_flags"] == {
        "cross_section_same_product_identity_merged": 1,
        "source_duplicate_approval_row_merged": 1,
        "source_multi_grade_approval_row_split": 2,
        "source_name_grade_notation_variants_merged": 1,
        "viscosity_inferred_from_product_name_due_empty_table_cell": 1,
    }
    assert report["cummins_valvoline_2022_source_rows"] == cummins_valvoline_report["normalized_products"] == len(cummins_valvoline_rows) == 166
    assert report["cummins_valvoline_2022_input_sha256"] == cummins_valvoline_report["normalized_output_sha256"]
    assert policy_by_id["CUMMINS_VALVOLINE_EU_2022_CATALOG"]["source_sha256"] == cummins_valvoline_report["normalized_output_sha256"]
    assert policy_by_id["CUMMINS_VALVOLINE_EU_2022_CATALOG"]["observed_count"] == 166
    assert policy_by_id["CUMMINS_CURRENT_OIL_REGISTRATION_LIST"]["bulk_ingest_allowed"] is False
    assert cummins_valvoline_report["source_pdf_sha256"] == "aad161c366c35e74fcd331771bb4d6194470e26099f970f878b2d96d2b3cc401"
    assert cummins_valvoline_report["families"] == {"C": 8, "G": 33, "H": 33, "I": 26, "M": 30, "S": 3, "T": 19, "TF": 6, "U": 8}
    assert cummins_valvoline_report["package_offer_occurrences"] == 510
    assert cummins_valvoline_report["unique_article_numbers"] == 502
    assert cummins_valvoline_report["cross_product_colliding_article_numbers"] == 8
    assert all(row["lifecycle_status"] == "historical_catalog_as_published_2022_04_current_status_unverified" for row in cummins_valvoline_rows)
    assert all(not ({"description", "image", "logo", "marketing_text"} & set(row)) for row in cummins_valvoline_rows)
    assert report["taiwan_cpc_source_rows"] == taiwan_cpc_report["current_product_cards"] == len(taiwan_cpc_rows) == 224
    assert report["taiwan_cpc_input_sha256"] == taiwan_cpc_report["normalized_output_sha256"]
    assert policy_by_id["TAIWAN_CPC_CURRENT_LUBRICANT_CATALOG"]["source_sha256"] == taiwan_cpc_report["normalized_output_sha256"]
    assert policy_by_id["TAIWAN_CPC_CURRENT_LUBRICANT_CATALOG"]["observed_count"] == 224
    assert taiwan_cpc_report["families"] == {"C": 9, "E": 1, "G": 21, "H": 15, "I": 71, "M": 76, "S": 11, "T": 11, "TF": 4, "U": 5}
    assert report["taiwan_cpc_structured_package_offers"] == taiwan_cpc_report["structured_package_offers"] == 478
    assert taiwan_cpc_report["products_with_structured_package_offers"] == 224
    assert taiwan_cpc_report["rows_with_iso_vg"] == 50
    assert taiwan_cpc_report["rows_with_nlgi"] == 21
    assert taiwan_cpc_report["source_quality_flags"] == {"source_multigrade_table_not_safely_aligned_to_listing_title": 27}
    assert len({row["manufacturer_product_code"] for row in taiwan_cpc_rows}) == 224
    assert all(row["lifecycle_status"] == "listed_on_current_official_product_sheet_directory" for row in taiwan_cpc_rows)
    assert all(row["packages"] for row in taiwan_cpc_rows)
    assert all(not ({"description", "image", "logo", "marketing_text"} & set(row)) for row in taiwan_cpc_rows)
    assert report["volvo_websds_source_rows"] == volvo_websds_report["normalized_product_part_identities"] == len(volvo_websds_rows) == 144
    assert report["volvo_websds_unique_part_numbers"] == volvo_websds_report["unique_part_numbers"] == 394
    assert report["volvo_websds_input_sha256"] == volvo_websds_report["normalized_output_sha256"]
    assert policy_by_id["VOLVO_GROUP_WEBSDS_CHANGE_ARCHIVE"]["source_sha256"] == volvo_websds_report["normalized_output_sha256"]
    assert policy_by_id["VOLVO_GROUP_WEBSDS_CHANGE_ARCHIVE"]["observed_count"] == 144
    assert volvo_websds_report["source_documents"] == 50
    assert volvo_websds_report["source_document_formats"] == {"pdf": 49, "xlsx": 1}
    assert volvo_websds_report["source_table_rows"] == 833
    assert volvo_websds_report["lubricant_scope_occurrences"] == 537
    assert volvo_websds_report["brands"] == {"Renault Trucks": 28, "Volvo": 116}
    assert volvo_websds_report["families"] == {"C": 6, "G": 24, "H": 13, "I": 7, "M": 13, "T": 61, "TF": 20}
    assert sum(len(row["source_occurrences"]) for row in volvo_websds_rows) == 537
    assert all(row["lifecycle_status"] == "official_sds_change_observation_2023_09_to_2026_06_current_availability_unverified" for row in volvo_websds_rows)
    assert all(not ({"description", "hazard_text", "image", "logo", "marketing_text"} & set(row)) for row in volvo_websds_rows)
    assert policy_by_id["REPSOL_LUBRICANTS_PRODUCT_CATALOG"]["bulk_ingest_allowed"] is False
    assert policy_by_id["REPSOL_LUBRICANTS_PRODUCT_CATALOG"]["observed_count"] == 0
    assert policy_by_id["MEXICO_CONUEE_CERTIFIED_PRODUCTS_LUBRICANT_SCOPE_REVIEW"]["observed_count"] == 0
    assert report["parker_denison_source_rows"] == parker_denison_report["normalized_rating_rows"] == len(parker_denison_rows) == 217
    assert report["parker_denison_input_sha256"] == parker_denison_report["normalized_output_sha256"]
    assert policy_by_id["PARKER_DENISON_CURRENT_FLUID_RATINGS"]["source_sha256"] == parker_denison_report["normalized_output_sha256"]
    assert policy_by_id["PARKER_DENISON_CURRENT_FLUID_RATINGS"]["observed_count"] == 217
    assert parker_denison_report["source_document_sha256"] == "a32d4aa248adc30eae63b00b3433272f0d9e37e19a22ff5c7aad66d68294ebc1"
    assert parker_denison_report["source_document_pages"] == 8
    assert parker_denison_report["rating_list_review_date"] == "2026-04-14"
    assert parker_denison_report["manufacturers"] == 104
    assert parker_denison_report["rows_by_lifecycle"] == {
        "published_rating_expired_by_validity_month_as_of_snapshot": 11,
        "published_rating_not_expired_by_validity_month_as_of_snapshot": 205,
        "source_validity_value_invalid_review_required": 1,
    }
    assert parker_denison_report["rows_by_iso_vg"] == {"32": 197, "46": 216, "68": 194}
    assert all(row["family_code"] == "H" for row in parker_denison_rows)
    assert all(row["specifications"]["approved_iso_vg"] for row in parker_denison_rows)
    assert all(not ({"description", "image", "logo", "marketing_text", "narrative"} & set(row)) for row in parker_denison_rows)
    assert policy_by_id["EATON_APPROVED_LUBRICANTS_TCMT0020"]["bulk_ingest_allowed"] is False
    assert sum(len(row["source_occurrences"]) for row in mack_2014_rows) == 806
    assert all(row["lifecycle_status"] == "historical_approval_as_published_2014_04_current_status_unverified" for row in mack_2014_rows)
    assert report["korea_ecolabel_source_rows"] == korea_ecolabel_report["normalized_products"] == len(korea_ecolabel_rows) == 20
    assert report["korea_ecolabel_products_matched_to_existing"] == 0
    assert report["korea_ecolabel_products_added"] == 20
    assert report["korea_ecolabel_el509_source_rows"] == korea_el509_report["normalized_products"] == len(korea_el509_rows) == 9
    assert report["korea_ecolabel_el509_products_matched_to_existing"] == 0
    assert report["korea_ecolabel_el509_products_added"] == 9
    assert report["green_choice_philippines_source_rows"] == green_choice_philippines_report["normalized_products"] == len(green_choice_philippines_rows) == 3
    assert report["green_choice_philippines_expired_rows"] == 3
    assert report["official_government_ecolabel_registry_rows"] == 33
    assert green_choice_philippines_report["source_table_rows"] == {"active": 34, "expired": 35, "ongoing_renewal": 7}
    assert green_choice_philippines_report["source_quality_flags"] == {"nonstandard_sae_notation_retained_verbatim": 1}
    assert all(row["lifecycle_status"] == "ecolabel_certificate_expired" for row in green_choice_philippines_rows)
    assert policy_by_id["GREEN_CHOICE_PHILIPPINES_ENGINE_OILS"]["source_sha256"] == green_choice_philippines_report["normalized_output_sha256"]
    assert policy_by_id["GREEN_CHOICE_PHILIPPINES_ENGINE_OILS"]["observed_count"] == 3
    assert report["uae_moiat_source_rows"] == uae_moiat_report["normalized_products"] == len(uae_moiat_rows) == 1840
    assert report["eaeu_conformity_source_rows"] == eaeu_conformity_report["deduplicated_product_rows"] == len(eaeu_conformity_rows) == 38444
    assert report["eaeu_conformity_explicit_brand_rows"] == eaeu_conformity_report["explicit_brand_rows"] == 2943
    assert report["eaeu_conformity_manufacturer_holder_fallback_rows"] == eaeu_conformity_report["manufacturer_holder_fallback_rows"] == 35501
    assert report["official_government_product_conformity_registry_rows"] == 40284
    assert eaeu_conformity_report["status"] == "official_eaeu_open_data_product_evidence_normalized"
    assert eaeu_conformity_report["crawl_strategy"] == "codes"
    assert eaeu_conformity_report["search_terms"] == []
    assert eaeu_conformity_report["unique_conformity_documents"] == 81076
    assert eaeu_conformity_report["candidate_occurrences"] == 51768
    assert eaeu_conformity_report["duplicate_certificate_occurrences_merged"] == 13324
    assert eaeu_conformity_report["query_truncated_terms"] == []
    assert eaeu_conformity_report["families"] == {"C": 1246, "E": 119, "G": 6780, "H": 2899, "I": 1117, "M": 13119, "S": 2466, "T": 6443, "TF": 3883, "U": 372}
    assert eaeu_conformity_report["normalized_output_sha256"] == hashlib.sha256((ROOT / "data/eaeu-conformity-lubricant-products.jsonl").read_bytes()).hexdigest()
    assert policy_by_id["EAEU_CONFORMITY_LUBRICANT_PRODUCTS"]["source_sha256"] == eaeu_conformity_report["normalized_output_sha256"]
    assert policy_by_id["EAEU_CONFORMITY_LUBRICANT_PRODUCTS"]["observed_count"] == len(eaeu_conformity_rows)
    assert len({row["source_record_id"] for row in eaeu_conformity_rows}) == len(eaeu_conformity_rows)
    assert all(row["source_url"].startswith("https://tech.eaeunion.org/tech/registers/35-1/ru/registryList/conformityDocs/view/") for row in eaeu_conformity_rows)
    assert report["epa_safer_choice_source_rows"] == epa_safer_choice_report["normalized_products"] == len(epa_safer_choice_rows) == 2
    assert report["epa_chemexpo_source_rows"] == epa_chemexpo_report["normalized_products"] == len(epa_chemexpo_rows)
    assert report["epa_chemexpo_source_product_occurrences"] == epa_chemexpo_report["kept_product_occurrences"]
    assert report["epa_chemexpo_products_added"] + report["epa_chemexpo_products_matched_to_existing"] == len(epa_chemexpo_rows)
    assert report["official_government_compiled_product_database_rows"] == report["epa_chemexpo_products_added"]
    assert report["psqca_engine_oil_source_rows"] == psqca_report["normalized_licence_brand_scopes"] == len(psqca_rows) == 14
    assert report["official_government_product_certification_brand_scope_rows"] == 14
    assert report["tisi_two_stroke_oil_source_rows"] == tisi_report["normalized_licence_holder_scopes"] == len(tisi_rows) == 10
    assert report["official_government_product_certification_holder_scope_rows"] == 10
    assert report["samr_china_2025_source_rows"] == samr_china_report["normalized_product_observations"] == len(samr_china_rows) == 25
    assert report["samr_china_2023_source_rows"] == samr_china_2023_report["normalized_product_observations"] == len(samr_china_2023_rows) == 126
    assert report["samr_china_2023_products_matched_to_existing"] == 1
    assert report["samr_china_2023_products_added"] == 125
    assert report["samr_china_2024_source_rows"] == samr_china_2024_report["normalized_product_observations"] == len(samr_china_2024_rows) == 23
    assert report["shenzhen_china_2021_source_rows"] == shenzhen_china_2021_report["normalized_product_observations"] == len(shenzhen_china_2021_rows) == 12
    assert report["shenzhen_china_2021_products_matched_to_existing"] == 1
    assert report["shenzhen_china_2021_products_added"] == 11
    assert report["shenzhen_china_2020_source_rows"] == shenzhen_china_2020_report["source_rows"] == len(shenzhen_china_2020_rows) == 106
    assert report["shenzhen_china_2020_products_matched_to_existing"] == 1
    assert report["shenzhen_china_2020_duplicate_occurrences_merged"] == 4
    assert report["shenzhen_china_2020_products_added"] == 101
    assert report["shenzhen_china_2019_source_rows"] == shenzhen_china_2019_report["source_rows"] == len(shenzhen_china_2019_rows) == 60
    assert report["shenzhen_china_2019_products_matched_to_existing"] == 10
    assert report["shenzhen_china_2019_duplicate_occurrences_merged"] == 1
    assert report["shenzhen_china_2019_products_added"] == 49
    assert report["shenzhen_china_2025_source_rows"] == shenzhen_china_2025_report["source_automotive_rows"] == len(shenzhen_china_2025_rows) == 100
    assert report["shenzhen_china_2025_products_matched_to_existing"] == 0
    assert report["shenzhen_china_2025_duplicate_occurrences_merged"] == 2
    assert report["shenzhen_china_2025_products_added"] == 98
    assert report["shanghai_china_2023_2025_source_rows"] == shanghai_china_report["source_observations"] == len(shanghai_china_rows) == 390
    assert report["shanghai_china_products_matched_to_existing"] == 57
    assert report["shanghai_china_products_added"] == 333
    assert report["beijing_china_2018_source_rows"] == beijing_china_report["source_observations"] == len(beijing_china_rows) == 294
    assert report["beijing_china_products_matched_to_existing"] == 87
    assert report["beijing_china_products_added"] == 207
    assert report["shenzhen_china_2016_2017_source_rows"] == shenzhen_china_2016_2017_report["source_observations"] == len(shenzhen_china_2016_2017_rows) == 140
    assert report["shenzhen_china_2016_2017_products_matched_to_existing"] == 7
    assert report["shenzhen_china_2016_2017_products_added"] == 133
    assert report["qingdao_china_2021_2025_source_rows"] == qingdao_china_report["retained_product_observations"] == len(qingdao_china_rows) == 262
    assert report["qingdao_china_products_matched_to_existing"] == 11
    assert report["qingdao_china_duplicate_occurrences_merged"] == 42
    assert report["qingdao_china_products_added"] == 209
    assert report["qingdao_china_products_matched_to_existing"] + report["qingdao_china_duplicate_occurrences_merged"] + report["qingdao_china_products_added"] == 262
    assert report["jilin_china_2024_2025_source_rows"] == jilin_china_report["retained_product_observations"] == len(jilin_china_rows) == 404
    assert report["jilin_china_products_matched_to_existing"] == 38
    assert report["jilin_china_duplicate_occurrences_merged"] == 42
    assert report["jilin_china_products_added"] == 324
    assert report["jilin_china_products_matched_to_existing"] + report["jilin_china_duplicate_occurrences_merged"] + report["jilin_china_products_added"] == 404
    assert report["wuxi_china_2024_source_rows"] == wuxi_china_report["retained_product_observations"] == len(wuxi_china_rows) == 10
    assert report["wuxi_china_products_matched_to_existing"] == 2
    assert report["wuxi_china_duplicate_occurrences_merged"] == 0
    assert report["wuxi_china_products_added"] == 8
    assert report["wuxi_china_products_matched_to_existing"] + report["wuxi_china_duplicate_occurrences_merged"] + report["wuxi_china_products_added"] == 10
    assert report["yantai_china_2025_source_rows"] == yantai_china_report["retained_product_observations"] == len(yantai_china_rows) == 15
    assert report["yantai_china_products_matched_to_existing"] == 0
    assert report["yantai_china_duplicate_occurrences_merged"] == 5
    assert report["yantai_china_products_added"] == 10
    assert report["yantai_china_products_matched_to_existing"] + report["yantai_china_duplicate_occurrences_merged"] + report["yantai_china_products_added"] == 15
    assert report["samr_china_source_observations"] == 174
    assert report["china_government_inspection_source_observations"] == 1967
    assert report["official_government_nonconforming_product_inspection_observation_rows"] == 261
    assert report["official_government_conforming_product_inspection_observation_rows"] == 1395
    assert report["philippines_bps_brake_fluid_source_rows"] == philippines_bps_report["normalized_products_or_brand_grade_scopes"] == len(philippines_bps_rows) == 123
    assert report["philippines_bps_ps_brake_fluid_rows"] == philippines_bps_report["rows_by_source"]["PHILIPPINES_BPS_PS_BRAKE_FLUID_LICENCES"] == 89
    assert report["philippines_bps_icc_brake_fluid_rows"] == philippines_bps_report["rows_by_source"]["PHILIPPINES_BPS_ICC_BRAKE_FLUID_CERTIFICATES"] == 34
    assert report["ghana_gsa_certified_source_rows"] == ghana_gsa_report["normalized_products"] == len(ghana_gsa_rows) == 16
    assert report["kebs_smark_source_rows"] == kebs_smark_report["normalized_products"] == len(kebs_smark_rows) == 750
    assert report["east_africa_certified_source_rows"] == east_africa_report["normalized_products"] == len(east_africa_rows) == 229
    assert report["east_africa_certified_source_rows_by_source"] == east_africa_report["normalized_products_by_source"] == {
        "TBS_CERTIFIED_LUBRICANT_PRODUCTS": 183,
        "UNBS_CERTIFIED_LUBRICANT_PRODUCTS": 46,
    }
    assert report["son_mancap_source_rows"] == son_mancap_report["normalized_products"] == len(son_mancap_rows) == 608
    assert report["rsb_smark_source_rows"] == rsb_smark_report["normalized_products"] == len(rsb_smark_rows) == 9
    assert report["official_government_product_certification_registry_rows"] == 1612
    assert report["usda_biopreferred_source_rows"] == biopreferred_report["rows"] == 892
    assert report["official_government_program_rows"] == 894
    assert report["anp_brazil_source_rows"] == anp_report["normalized_product_grade_rows"] == len(anp_rows) == 12664
    assert report["indonesia_npt_source_rows"] == indonesia_report["published_product_rows"] == len(indonesia_rows) == 12626
    assert report["indonesia_npt_rows_with_registration_value"] == indonesia_report["rows_with_registration_value"] == 12575
    assert report["indonesia_npt_rows_with_source_data_issue"] == indonesia_report["rows_with_source_placeholder_no_registration_number"] == 51
    assert indonesia_report["unique_registration_numbers"] == 12565
    assert indonesia_report["registration_number_collisions"] == 10
    assert report["thailand_doeb_normalized_products"] == thailand_doeb_report["normalized_products"] == len(thailand_doeb_rows) == 5486
    assert report["thailand_doeb_source_occurrences"] == thailand_doeb_report["published_source_rows"] == 6213
    assert thailand_doeb_report["duplicate_registration_occurrences_merged"] == 727
    assert report["thailand_doeb_unique_registration_numbers"] == thailand_doeb_report["unique_registration_numbers"] == 6210
    assert report["thailand_doeb_registration_collision_products"] == thailand_doeb_report["registration_number_collision_products"] == 6
    assert thailand_doeb_report["registration_number_collision_source_rows"] == 6
    assert report["thailand_doeb_published_end_date_not_expired_products"] == thailand_doeb_report["lifecycle_assessments"]["not_expired_by_published_end_date_as_of_catalog_snapshot"] == 1492
    assert report["official_government_regulatory_registry_rows"] == 30725
    assert report["official_government_registry_source_data_issue_rows"] == 51
    assert report["dla_qpd_source_rows"] == dla_report["normalized_products"] == len(dla_rows) == 536
    assert report["official_government_qualified_product_registry_rows"] == 536
    assert report["dla_qpd_source_rows_by_source"] == dla_report["normalized_products_by_source"] == {
        "DLA_QPD_FSC_6850_LUBRICANT_SCOPE": 25,
        "DLA_QPD_FSC_8030_LUBRICANT_SCOPE": 80,
        "DLA_QPD_FSC_9150": 431,
    }
    assert dla_report["active_qpls_in_scope"] == 65
    assert dla_report["qpls_by_fsc"] == {"6850_lubricant_scope": 6, "8030_lubricant_scope": 3, "9150": 56}
    assert len(dla_report["fsc_6850_excluded_active_qpls"]) == 18
    assert not ({q.removeprefix("QPL-") for q in dla_report["fsc_6850_excluded_active_qpls"]} & {"6529", "8188", "AS8660", "25017", "29608", "32490"})
    assert len(dla_report["fsc_8030_excluded_search_qpls"]) == 10
    assert dla_report["government_designations"] == 139
    assert dla_report["published_manufacturer_product_occurrences"] == 570
    assert dla_report["plant_rows_without_product_designation_excluded"] == 861
    assert report["zf_te_ml_source_rows"] == zf_report["unique_approval_numbers"] == 1498
    assert report["official_oem_approval_rows"] == 6495
    assert report["official_manufacturer_catalog_rows"] == 6142
    assert report["official_oem_service_recommendation_rows"] == 30
    assert report["allison_source_rows"] == allison_report["products"] == 104
    assert report["driventic_diwa_source_rows"] == driventic_report["products"] == 226
    assert report["mercedes_dtfr_source_rows"] == mercedes_report["products"] == 1892
    assert report["mercedes_bevo_source_rows"] == mercedes_bevo_report["products"] == 1913
    assert report["mercedes_bevo_products_matched_to_existing"] == 158
    assert report["mercedes_bevo_products_added"] == 1755
    assert report["volvo_genuine_source_rows"] == volvo_report["products"] == 32
    assert report["ceypetco_source_rows"] == ceypetco_report["normalized_product_grade_rows"] == len(ceypetco_rows) == 47
    assert report["man_service_source_rows"] == man_report["products"] == 32
    assert report["man_service_products_matched_to_existing"] == 2
    assert report["man_service_products_added"] == 30
    assert report["fuchs_india_source_rows"] == fuchs_report["products"] == 1007
    assert report["fuchs_india_products_matched_to_existing"] == 22
    assert report["fuchs_india_products_added"] == 985
    assert report["fuchs_us_source_rows"] == fuchs_us_report["products"] == 623
    assert report["fuchs_us_products_matched_to_existing"] == 128
    assert report["fuchs_us_products_added"] == 495
    assert report["fuchs_cross_market_exact_name_family_rows"] == 118
    assert report["fuchs_cross_market_family_conflict_rows"] == 4
    assert report["fuchs_germany_source_rows"] == fuchs_germany_report["products"] == 1464
    assert report["fuchs_germany_products_matched_to_existing"] == 447
    assert report["fuchs_germany_products_added"] == 1017
    assert report["fuchs_germany_cross_market_exact_name_family_rows"] == 441
    assert report["fuchs_germany_cross_market_family_conflict_rows"] == 79
    assert report["fuchs_poland_source_rows"] == fuchs_poland_report["products"] == 690
    assert report["fuchs_poland_products_matched_to_existing"] == 544
    assert report["fuchs_poland_products_added"] == 146
    assert report["fuchs_poland_cross_market_exact_name_family_rows"] == 560
    assert report["fuchs_poland_cross_market_family_conflict_rows"] == 59
    assert report["fuchs_italy_source_rows"] == fuchs_italy_report["products"] == 1007
    assert report["fuchs_italy_products_matched_to_existing"] == 648
    assert report["fuchs_italy_products_added"] == 359
    assert report["fuchs_italy_cross_market_exact_name_family_rows"] == 657
    assert report["fuchs_italy_cross_market_family_conflict_rows"] == 28
    assert report["fuchs_sweden_source_rows"] == fuchs_sweden_report["products"] == 675
    assert report["fuchs_sweden_products_matched_to_existing"] == 360
    assert report["fuchs_sweden_products_added"] == 315
    assert report["fuchs_sweden_cross_market_exact_name_family_rows"] == 379
    assert report["fuchs_sweden_cross_market_family_conflict_rows"] == 17
    assert report["fuchs_spain_source_rows"] == fuchs_spain_report["products"] == 938
    assert report["fuchs_spain_products_matched_to_existing"] == 729
    assert report["fuchs_spain_products_added"] == 209
    assert report["fuchs_spain_cross_market_exact_name_family_rows"] == 743
    assert report["fuchs_spain_cross_market_family_conflict_rows"] == 19
    assert report["fuchs_france_source_rows"] == fuchs_france_report["products"] == 705
    assert report["fuchs_france_products_matched_to_existing"] == 506
    assert report["fuchs_france_products_added"] == 199
    assert report["fuchs_france_cross_market_exact_name_family_rows"] == 532
    assert report["fuchs_france_cross_market_family_conflict_rows"] == 12
    assert report["fuchs_turkey_source_rows"] == fuchs_turkey_report["products"] == 583
    assert report["fuchs_turkey_products_matched_to_existing"] == 422
    assert report["fuchs_turkey_products_added"] == 161
    assert report["fuchs_turkey_cross_market_exact_name_family_rows"] == 423
    assert report["fuchs_turkey_cross_market_family_conflict_rows"] == 5
    assert report["fuchs_canada_source_rows"] == fuchs_canada_report["products"] == 289
    assert report["fuchs_canada_products_matched_to_existing"] == 138
    assert report["fuchs_canada_products_added"] == 151
    assert report["fuchs_canada_cross_market_exact_name_family_rows"] == 152
    assert report["fuchs_canada_cross_market_family_conflict_rows"] == 5
    assert report["fuchs_china_source_rows"] == fuchs_china_report["products"] == 278
    assert report["fuchs_china_products_matched_to_existing"] == 204
    assert report["fuchs_china_products_added"] == 74
    assert report["fuchs_china_cross_market_exact_name_family_rows"] == 202
    assert report["fuchs_china_cross_market_family_conflict_rows"] == 0
    assert report["fuchs_czech_source_rows"] == fuchs_czech_report["products"] == 1146
    assert report["fuchs_czech_products_matched_to_existing"] == 1041
    assert report["fuchs_czech_products_added"] == 105
    assert report["fuchs_czech_cross_market_exact_name_family_rows"] == 1063
    assert report["fuchs_czech_cross_market_family_conflict_rows"] == 19
    assert report["fuchs_mexico_source_rows"] == fuchs_mexico_report["products"] == 314
    assert report["fuchs_mexico_products_matched_to_existing"] == 252
    assert report["fuchs_mexico_products_added"] == 62
    assert report["fuchs_mexico_cross_market_exact_name_family_rows"] == 258
    assert report["fuchs_mexico_cross_market_family_conflict_rows"] == 3
    assert report["fuchs_south_africa_source_rows"] == fuchs_south_africa_report["products"] == 756
    assert report["fuchs_south_africa_products_matched_to_existing"] == 720
    assert report["fuchs_south_africa_products_added"] == 36
    assert report["fuchs_south_africa_cross_market_exact_name_family_rows"] == 725
    assert report["fuchs_south_africa_cross_market_family_conflict_rows"] == 2
    assert report["fuchs_brazil_source_rows"] == fuchs_brazil_report["products"] == 182
    assert report["fuchs_brazil_products_matched_to_existing"] == 180
    assert report["fuchs_brazil_products_added"] == 2
    assert report["fuchs_brazil_cross_market_exact_name_family_rows"] == 182
    assert report["fuchs_brazil_cross_market_family_conflict_rows"] == 0
    assert report["fuchs_norway_source_rows"] == fuchs_norway_report["products"] == 649
    assert report["fuchs_norway_products_matched_to_existing"] == 622
    assert report["fuchs_norway_products_added"] == 27
    assert report["fuchs_norway_cross_market_exact_name_family_rows"] == 630
    assert report["fuchs_norway_cross_market_family_conflict_rows"] == 15
    assert report["fuchs_hungary_source_rows"] == fuchs_hungary_report["products"] == 506
    assert report["fuchs_hungary_products_matched_to_existing"] == 354
    assert report["fuchs_hungary_products_added"] == 152
    assert report["fuchs_hungary_cross_market_exact_name_family_rows"] == 369
    assert report["fuchs_hungary_cross_market_family_conflict_rows"] == 15
    for slug, spec in additional_fuchs_specs.items():
        _, _, products, _, _, _, _, matched, added, exact, conflicts, _ = spec
        assert report[f"fuchs_{slug}_source_rows"] == products
        assert report[f"fuchs_{slug}_products_matched_to_existing"] == matched
        assert report[f"fuchs_{slug}_products_added"] == added
        assert report[f"fuchs_{slug}_cross_market_exact_name_family_rows"] == exact
        assert report[f"fuchs_{slug}_cross_market_family_conflict_rows"] == conflicts
    assert report["liqui_moly_2020_source_rows"] == liqui_moly_report["products"] == 419
    assert report["liqui_moly_2020_products_matched_to_existing"] == 13
    assert report["liqui_moly_2020_products_added"] == 406
    assert report["liqui_moly_current_source_rows"] == liqui_moly_current_report["lubricant_and_technical_fluid_products"] == len(liqui_moly_current_rows) == 447
    assert report["liqui_moly_current_products_matched_to_2020"] == 295
    assert report["liqui_moly_current_products_added"] == 152
    assert report["liqui_moly_current_article_skus"] == liqui_moly_current_report["unique_article_skus"] == 985
    assert report["duplicate_decisions"]["review_cross_source_identity"] == 597
    assert report["duplicate_decisions"]["keep_separate_specification_conflict"] == 11205
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND (a.source_id LIKE 'BEIJING_CHINA_%' OR b.source_id LIKE 'BEIJING_CHINA_%')
    """).fetchone()[0] == 16
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_professional_signature_conflict'
          AND (a.source_id LIKE 'BEIJING_CHINA_%' OR b.source_id LIKE 'BEIJING_CHINA_%')
    """).fetchone()[0] == 43
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_specification_conflict'
          AND (a.source_id LIKE 'BEIJING_CHINA_%' OR b.source_id LIKE 'BEIJING_CHINA_%')
    """).fetchone()[0] == 18
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND (a.source_id LIKE 'QINGDAO_CHINA_%' OR b.source_id LIKE 'QINGDAO_CHINA_%')
    """).fetchone()[0] == 21
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_professional_signature_conflict'
          AND (a.source_id LIKE 'QINGDAO_CHINA_%' OR b.source_id LIKE 'QINGDAO_CHINA_%')
    """).fetchone()[0] == 14
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_specification_conflict'
          AND (a.source_id LIKE 'QINGDAO_CHINA_%' OR b.source_id LIKE 'QINGDAO_CHINA_%')
    """).fetchone()[0] == 4
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND (a.source_id LIKE 'JILIN_CHINA_%' OR b.source_id LIKE 'JILIN_CHINA_%')
    """).fetchone()[0] == 35
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_professional_signature_conflict'
          AND (a.source_id LIKE 'JILIN_CHINA_%' OR b.source_id LIKE 'JILIN_CHINA_%')
    """).fetchone()[0] == 28
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_specification_conflict'
          AND (a.source_id LIKE 'JILIN_CHINA_%' OR b.source_id LIKE 'JILIN_CHINA_%')
    """).fetchone()[0] == 15
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND (a.source_id IN ('SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION', 'SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION')
               OR b.source_id IN ('SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION', 'SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION'))
    """).fetchone()[0] == 19
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_professional_signature_conflict'
          AND (a.source_id IN ('SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION', 'SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION')
               OR b.source_id IN ('SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION', 'SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION'))
    """).fetchone()[0] == 19
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_specification_conflict'
          AND (a.source_id IN ('SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION', 'SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION')
               OR b.source_id IN ('SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION', 'SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION'))
    """).fetchone()[0] == 9
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_specification_conflict'
          AND a.source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'
          AND b.source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'
    """).fetchone()[0] == 14
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_specification_conflict'
          AND a.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'
          AND b.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'
    """).fetchone()[0] == 5
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND (a.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION')
    """).fetchone()[0] == 16
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_professional_signature_conflict'
          AND (a.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION')
    """).fetchone()[0] == 8
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND (a.source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION')
    """).fetchone()[0] == 0
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_professional_signature_conflict'
          AND (a.source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION')
    """).fetchone()[0] == 1
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND (a.source_id='VOLVO_GROUP_WEBSDS_CHANGE_ARCHIVE'
               OR b.source_id='VOLVO_GROUP_WEBSDS_CHANGE_ARCHIVE')
    """).fetchone()[0] == 10
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND a.source_id='PHILIPPINES_BPS_ICC_BRAKE_FLUID_CERTIFICATES'
          AND b.source_id='PHILIPPINES_BPS_PS_BRAKE_FLUID_LICENCES'
          AND a.brand='Würth'
          AND b.brand='WÜRTH'
    """).fetchone()[0] == 2
    assert report["duplicate_decisions"]["keep_separate_blue_angel_family_conflict"] == 34
    assert report["duplicate_decisions"]["review_brand_alias_identity"] == 2
    assert report["duplicate_decisions"]["review_liqui_moly_multi_registry_identity"] == 49
    assert report["duplicate_decisions"]["review_liqui_moly_current_multiple_historical_candidates"] == 4
    assert report["fuchs_exact_payload_identity_rows_matched"] == 43
    assert report["fuchs_exact_payload_identity_rows_matched_by_source"] == {
        "FUCHS_DENMARK_PRODUCT_FINDER": 2,
        "FUCHS_FINLAND_PRODUCT_FINDER": 5,
        "FUCHS_NORWAY_PRODUCT_FINDER": 12,
        "FUCHS_SWITZERLAND_PRODUCT_FINDER": 24,
    }
    assert report["fuchs_unique_content_hashes"] == 2600
    assert report["fuchs_exact_content_identity_rows_matched"] == 179
    assert report["fuchs_exact_content_identity_rows_matched_by_source"] == {
        "FUCHS_AUSTRIA_PRODUCT_FINDER": 14,
        "FUCHS_BRAZIL_PRODUCT_FINDER": 4,
        "FUCHS_CHILE_PRODUCT_FINDER": 9,
        "FUCHS_CHINA_PRODUCT_FINDER": 4,
        "FUCHS_CROATIA_PRODUCT_FINDER": 13,
        "FUCHS_CZECH_PRODUCT_FINDER": 4,
        "FUCHS_DENMARK_PRODUCT_FINDER": 6,
        "FUCHS_FINLAND_PRODUCT_FINDER": 10,
        "FUCHS_FRANCE_PRODUCT_FINDER": 3,
        "FUCHS_GREECE_PRODUCT_FINDER": 14,
        "FUCHS_HUNGARY_PRODUCT_FINDER": 1,
        "FUCHS_ITALY_PRODUCT_FINDER": 4,
        "FUCHS_KOREA_PRODUCT_FINDER": 7,
        "FUCHS_MACEDONIA_PRODUCT_FINDER": 13,
        "FUCHS_PORTUGAL_PRODUCT_FINDER": 5,
        "FUCHS_ROMANIA_PRODUCT_FINDER": 10,
        "FUCHS_SAUDI_ARABIA_PRODUCT_FINDER": 3,
        "FUCHS_SLOVAKIA_PRODUCT_FINDER": 14,
        "FUCHS_SOUTH_AFRICA_PRODUCT_FINDER": 4,
        "FUCHS_SPAIN_PRODUCT_FINDER": 5,
        "FUCHS_SWEDEN_PRODUCT_FINDER": 2,
        "FUCHS_TURKEY_PRODUCT_FINDER": 8,
        "FUCHS_UAE_PRODUCT_FINDER": 14,
        "FUCHS_UKRAINE_PRODUCT_FINDER": 8,
    }
    assert report["fuchs_unique_description_hashes"] == 2432
    assert report["fuchs_unique_description_identity_rows_matched"] == 28
    assert report["fuchs_unique_description_identity_rows_matched_by_source"] == {
        "FUCHS_CHINA_PRODUCT_FINDER": 2,
        "FUCHS_CZECH_PRODUCT_FINDER": 2,
        "FUCHS_DENMARK_PRODUCT_FINDER": 3,
        "FUCHS_FINLAND_PRODUCT_FINDER": 1,
        "FUCHS_FRANCE_PRODUCT_FINDER": 2,
        "FUCHS_ITALY_PRODUCT_FINDER": 6,
        "FUCHS_NORWAY_PRODUCT_FINDER": 1,
        "FUCHS_PORTUGAL_PRODUCT_FINDER": 4,
        "FUCHS_SAUDI_ARABIA_PRODUCT_FINDER": 1,
        "FUCHS_SOUTH_AFRICA_PRODUCT_FINDER": 4,
        "FUCHS_UKRAINE_PRODUCT_FINDER": 2,
    }
    assert report["fuchs_unique_technical_hashes"] == 352
    assert report["fuchs_exact_technical_identity_rows_matched"] == 33
    assert report["fuchs_exact_technical_identity_rows_matched_by_source"] == {
        "FUCHS_DENMARK_PRODUCT_FINDER": 4,
        "FUCHS_FINLAND_PRODUCT_FINDER": 7,
        "FUCHS_FRANCE_PRODUCT_FINDER": 2,
        "FUCHS_HUNGARY_PRODUCT_FINDER": 1,
        "FUCHS_ITALY_PRODUCT_FINDER": 1,
        "FUCHS_MEXICO_PRODUCT_FINDER": 1,
        "FUCHS_NORWAY_PRODUCT_FINDER": 5,
        "FUCHS_POLAND_PRODUCT_FINDER": 4,
        "FUCHS_SPAIN_PRODUCT_FINDER": 5,
        "FUCHS_UKRAINE_PRODUCT_FINDER": 1,
        "FUCHS_US_PRODUCT_FINDER": 2,
    }
    assert report["duplicate_decisions"]["review_fuchs_multi_registry_identity"] == 1929
    assert report["duplicate_decisions"]["keep_separate_fuchs_market_family_conflict"] == 482
    assert report["duplicate_decisions"]["keep_separate_professional_signature_conflict"] == 730
    assert report["duplicate_decision_pair_rows_collapsed"] == {
        "keep_separate_professional_signature_conflict + keep_separate_professional_signature_conflict": 11,
        "review_cross_source_identity + review_fuchs_multi_registry_identity": 1196,
        "review_cross_source_identity + review_liqui_moly_current_multiple_historical_candidates": 2,
    }
    assert report["duplicate_review_conflicts_resolved"] == {
        "brake_fluid_hzy_source_reported": 2,
        "coolant_class": 4,
        "coolant_class_source_reported": 7,
        "coolant_freezing_point_source_reported": 7,
        "iso_vg": 20,
        "jaso_family_detail": 3,
        "sae_engine": 658,
        "sae_gear": 48,
    }
    assert report["duplicate_decision_self_pairs_dropped"] == {
        "merged": 1, "review_fuchs_multi_registry_identity": 281,
    }
    assert report["canonical_input_rows_collapsed"] == 1
    assert db.execute("SELECT count(*) FROM duplicate_decisions WHERE product_id_a=product_id_b").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM duplicate_decisions").fetchone()[0] == 15032
    assert db.execute("""
        SELECT count(*) FROM (
            SELECT 1 FROM duplicate_decisions
            GROUP BY min(product_id_a, product_id_b), max(product_id_a, product_id_b)
            HAVING count(*) > 1
        )
    """).fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM duplicate_decisions WHERE reason LIKE '% | %'").fetchone()[0] == 1198
    assert report["aichilon_products_matched_to_existing"] == 255
    assert report["aichilon_products_added"] == 60
    assert report["aichilon_rows_excluded"] == 2
    assert db.execute("SELECT count(*) FROM product_offers").fetchone()[0] == report["offers"] == 5191
    assert db.execute("SELECT count(*) FROM product_offers WHERE lifecycle_status IN ('active', 'listed_current_catalog')").fetchone()[0] == report["active_offers"] == 3115
    assert db.execute("SELECT input_rows FROM ingest_runs WHERE run_id=?", (report["run_id"],)).fetchone()[0] == report["input_rows"] == 118700
    assert db.execute("SELECT canonical_rows FROM ingest_runs WHERE run_id=?", (report["run_id"],)).fetchone()[0] == report["canonical_rows"] == 118699
    assert report["quality_issues"]["professional_key_incomplete"] == 79480
    assert dict(db.execute("""
        SELECT p.family_code, count(*) FROM quality_issues q
        JOIN products p USING(product_id)
        WHERE q.issue_code='professional_key_incomplete'
        GROUP BY p.family_code
    """)) == {
        "C": 2300, "E": 151, "G": 12528, "H": 5285, "I": 3903,
        "M": 23721, "S": 12183, "T": 11982, "TF": 6783, "U": 644,
    }
    assert offline_quality_audit["compressed_database_sha256"] == hashlib.sha256((ROOT / "data/world-catalog.sqlite3.xz").read_bytes()).hexdigest()
    assert offline_quality_audit["input_rows_before_canonicalization"] == report["input_rows"]
    assert offline_quality_audit["canonical_products"] == report["canonical_rows"]
    assert offline_quality_audit["active_offers"] == report["active_offers"]
    assert offline_quality_audit["canonical_key_duplicates"] == 0
    assert offline_quality_audit["products_with_at_least_one_source_link"] == report["canonical_rows"]
    assert sum(row["products"] for row in offline_quality_audit["family_coverage"]) == report["canonical_rows"]
    assert duplicate_triage["compressed_database_sha256"] == hashlib.sha256((ROOT / "data/world-catalog.sqlite3.xz").read_bytes()).hexdigest()
    assert duplicate_triage["canonical_products"] == report["canonical_rows"]
    assert duplicate_triage["review_pairs"] == 2581
    assert duplicate_triage["distinct_products_in_review"] == 1306
    assert duplicate_triage["self_pairs_remaining"] == 0
    assert duplicate_triage["already_applied_safe_merges"] == {
        "canonical_input_rows_collapsed": 1,
        "gm_dual_standard_same_license_manufacturer_name_family_viscosity": 7,
    }
    assert duplicate_triage["retained_source_code_collisions"] == {
        "gm_same_license_different_product_names": 1,
    }
    assert duplicate_triage["resolved_keep_separate_pairs"] == {
        "explicit_professional_signature_conflict": 730,
        "conflicting_fields": report["duplicate_review_conflicts_resolved"],
    }
    assert duplicate_triage["duplicate_decision_rows_collapsed"] == {
        "by_decision_combination": report["duplicate_decision_pair_rows_collapsed"],
        "total_extra_rows_removed": 1209,
    }
    assert duplicate_triage["triage_status_counts"] == {
        "compatible_partial_specification_review": 1206,
        "complete_exact_signature_candidate": 470,
        "insufficient_comparable_evidence": 905,
    }
    assert db.execute("SELECT count(*) FROM product_offers WHERE lifecycle_status='listed_current_catalog'").fetchone()[0] == report["current_catalog_listed_offers"] == 1660
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_filed_registry'").fetchone()[0] == 3629
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_licensed_registry'").fetchone()[0] == 3030
    assert db.execute("SELECT count(*) FROM specifications WHERE spec_type='gm_license_occurrences'").fetchone()[0] == 1705
    assert db.execute("SELECT count(DISTINCT product_id) FROM specifications WHERE spec_type='gm_license_occurrences'").fetchone()[0] == 1698
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_ecolabel_product_registry'").fetchone()[0] == 127
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_ecolabel_registry'").fetchone()[0] == 33
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_product_conformity_registry'").fetchone()[0] == 40284
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_product_certification_registry'").fetchone()[0] == 1612
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_program_catalog'").fetchone()[0] == 894
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_regulatory_registry'").fetchone()[0] == 30725
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_registry_source_data_issue'").fetchone()[0] == 51
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_qualified_product_registry'").fetchone()[0] == 536
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_oem_approval_registry'").fetchone()[0] == 6495
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_manufacturer_product_catalog'").fetchone()[0] == 6142
    assert db.execute("SELECT count(*) FROM specifications WHERE spec_type='fuchs_payload_identity_sha256'").fetchone()[0] == 21032
    assert db.execute("SELECT count(DISTINCT spec_value) FROM specifications WHERE spec_type='fuchs_payload_identity_sha256'").fetchone()[0] == 19691
    assert db.execute("SELECT count(*) FROM specifications WHERE spec_type='fuchs_content_identity_sha256'").fetchone()[0] == 9076
    assert db.execute("SELECT count(DISTINCT spec_value) FROM specifications WHERE spec_type='fuchs_content_identity_sha256'").fetchone()[0] == 8597
    assert db.execute("SELECT count(*) FROM specifications WHERE spec_type='fuchs_technical_identity_sha256'").fetchone()[0] == 1211
    assert db.execute("SELECT count(DISTINCT spec_value) FROM specifications WHERE spec_type='fuchs_technical_identity_sha256'").fetchone()[0] == 1143
    assert db.execute("SELECT count(*) FROM products WHERE source_id='BRAVA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 69
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='BRAVA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 69
    assert db.execute("SELECT count(*) FROM products WHERE source_id='PAKISTAN_STATE_OIL_OFFICIAL_CATALOG'").fetchone()[0] == 123
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='PAKISTAN_STATE_OIL_OFFICIAL_CATALOG'").fetchone()[0] == 124
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='PAKISTAN_STATE_OIL_OFFICIAL_CATALOG'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code LIKE 'pso_%'").fetchone()[0] == 8
    assert db.execute("""
        SELECT count(*) FROM products p
        JOIN product_sources s ON s.product_id=p.product_id
        WHERE p.source_id='MERCEDES_DTFR_APPROVED_FLUIDS'
          AND p.product_name_raw='PSO DEO 8000'
          AND s.source_id='PAKISTAN_STATE_OIL_OFFICIAL_CATALOG'
          AND EXISTS (
              SELECT 1 FROM specifications sp
              WHERE sp.product_id=p.product_id
                AND sp.spec_type='pso_technical_document_url'
          )
    """).fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM products WHERE source_id='PERTAMINA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 162
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='PERTAMINA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 250
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='PERTAMINA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='pertamina_linked_pds_title_conflicts_with_current_product_card'").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='pertamina_current_official_family_corrects_prior_registry_family'").fetchone()[0] == 6
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='BRAVA_PART_NUMBER'").fetchone()[0] == 94
    assert db.execute("SELECT count(DISTINCT code_value) FROM external_codes WHERE code_system='BRAVA_PART_NUMBER'").fetchone()[0] == 93
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='BRAVA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 94
    assert db.execute("SELECT count(*) FROM products WHERE source_id='MACK_GENUINE_FLUIDS'").fetchone()[0] == 15
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='MACK_GENUINE_FLUIDS'").fetchone()[0] == 15
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='MACK_PART_NUMBER'").fetchone()[0] == 38
    assert db.execute("SELECT count(DISTINCT code_value) FROM external_codes WHERE code_system='MACK_PART_NUMBER'").fetchone()[0] == 38
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='MACK_GENUINE_FLUIDS'").fetchone()[0] == 32
    eos5_key = db.execute("SELECT canonical_key FROM products WHERE source_id='MACK_GENUINE_FLUIDS' AND product_name_raw='Mack Engine Oil EOS-5 5W-30'").fetchone()[0]
    mdrive_7580_key = db.execute("SELECT canonical_key FROM products WHERE source_id='MACK_GENUINE_FLUIDS' AND product_name_raw='Mack mDRIVE Transmission Fluid 75W-80'").fetchone()[0]
    mdrive_7590_key = db.execute("SELECT canonical_key FROM products WHERE source_id='MACK_GENUINE_FLUIDS' AND product_name_raw='Mack mDRIVE Transmission Fluid 75W-90'").fetchone()[0]
    assert "mack_professional_performance:api fa 4 mack eos 5" in eos5_key
    assert "mack_professional_performance:mack 97307 97318" in mdrive_7580_key
    assert "mack_professional_performance:mack 97315" in mdrive_7590_key
    assert "37319" not in mdrive_7590_key
    assert db.execute("SELECT count(*) FROM products WHERE source_id='MACK_2014_APPROVED_OILS'").fetchone()[0] == 803
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='MACK_2014_APPROVED_OILS'").fetchone()[0] == 803
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='MACK_2014_APPROVED_OILS'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM products WHERE source_id='MACK_2014_APPROVED_OILS' AND lifecycle_status='historical_approval_as_published_2014_04_current_status_unverified'").fetchone()[0] == 803
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code LIKE 'mack_2014_%'").fetchone()[0] == 6
    assert db.execute("SELECT count(*) FROM products WHERE source_id='CUMMINS_VALVOLINE_EU_2022_CATALOG'").fetchone()[0] == 166
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='CUMMINS_VALVOLINE_EU_2022_CATALOG'").fetchone()[0] == 166
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='CUMMINS_VALVOLINE_EU_2022_CATALOG'").fetchone()[0] == 510
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='VALVOLINE_ARTICLE_NUMBER'").fetchone()[0] == 510
    assert db.execute("SELECT count(DISTINCT code_value) FROM external_codes WHERE code_system='VALVOLINE_ARTICLE_NUMBER'").fetchone()[0] == 502
    assert db.execute("SELECT count(*) FROM products WHERE source_id='CUMMINS_VALVOLINE_EU_2022_CATALOG' AND lifecycle_status='historical_catalog_as_published_2022_04_current_status_unverified'").fetchone()[0] == 166
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code LIKE 'cummins_valvoline_2022_%'").fetchone()[0] == 9
    assert db.execute("SELECT count(*) FROM products WHERE source_id='TAIWAN_CPC_CURRENT_LUBRICANT_CATALOG'").fetchone()[0] == 224
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='TAIWAN_CPC_CURRENT_LUBRICANT_CATALOG'").fetchone()[0] == 224
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='CPC_TAIWAN_PRODUCT_CODE'").fetchone()[0] == 224
    assert db.execute("SELECT count(DISTINCT code_value) FROM external_codes WHERE code_system='CPC_TAIWAN_PRODUCT_CODE'").fetchone()[0] == 224
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='TAIWAN_CPC_CURRENT_LUBRICANT_CATALOG'").fetchone()[0] == 478
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='TAIWAN_CPC_CURRENT_LUBRICANT_CATALOG' AND lifecycle_status='listed_current_catalog'").fetchone()[0] == 478
    assert db.execute("SELECT count(*) FROM products WHERE source_id='TAIWAN_CPC_CURRENT_LUBRICANT_CATALOG' AND lifecycle_status='listed_on_current_official_product_sheet_directory'").fetchone()[0] == 224
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='source_multigrade_table_not_safely_aligned_to_listing_title'").fetchone()[0] == 27
    assert db.execute("SELECT count(*) FROM products WHERE source_id='VOLVO_GROUP_WEBSDS_CHANGE_ARCHIVE'").fetchone()[0] == 144
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_manufacturer_sds_change_observation'").fetchone()[0] == 144
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='VOLVO_GROUP_WEBSDS_CHANGE_ARCHIVE'").fetchone()[0] == 144
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='VOLVO_GROUP_WEBSDS_PART_NUMBER'").fetchone()[0] == 394
    assert db.execute("SELECT count(DISTINCT code_value) FROM external_codes WHERE code_system='VOLVO_GROUP_WEBSDS_PART_NUMBER'").fetchone()[0] == 394
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='VOLVO_GROUP_WEBSDS_CHANGE_ARCHIVE'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM products WHERE source_id='PARKER_DENISON_CURRENT_FLUID_RATINGS'").fetchone()[0] == 217
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='PARKER_DENISON_CURRENT_FLUID_RATINGS'").fetchone()[0] == 217
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='PARKER_DENISON_CURRENT_FLUID_RATINGS'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='parker_denison_source_invalid_validity_month'").fetchone()[0] == 1
    assert db.execute("""
        SELECT count(*) FROM products p
        JOIN product_sources s ON s.product_id=p.product_id
        WHERE p.source_id='PARKER_DENISON_CURRENT_FLUID_RATINGS'
          AND s.source_id='FUCHS_US_PRODUCT_FINDER'
    """).fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_oem_service_recommendation'").fetchone()[0] == 30
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='ALLISON_APPROVAL_NUMBER'").fetchone()[0] == 119
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='MERCEDES_DTFR_PRODUCT_ID'").fetchone()[0] == 1892
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='MERCEDES_BEVO_PRODUCT_ID'").fetchone()[0] == 1914
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='BLUE_ANGEL_PRODUCT_PAGE'").fetchone()[0] == 149
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='AUSTRIAN_ECOLABEL_UZ14_CERTIFICATE'").fetchone()[0] == 11
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='KOREA_ECOLABEL_CERTIFICATE'").fetchone()[0] == 29
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='VOLVO_PART_NUMBER'").fetchone()[0] == 20
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='VOLVO_GENUINE_FLUIDS'").fetchone()[0] == 32
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='CEYPETCO_OFFICIAL_LUBRICANT_CATALOG'").fetchone()[0] == 47
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='MAN_CURRENT_SERVICE_PRODUCTS'").fetchone()[0] == 32
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_INDIA_PRODUCT_FINDER'").fetchone()[0] == 1007
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_US_PRODUCT_FINDER'").fetchone()[0] == 623
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_GERMANY_PRODUCT_FINDER'").fetchone()[0] == 1464
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_POLAND_PRODUCT_FINDER'").fetchone()[0] == 690
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_ITALY_PRODUCT_FINDER'").fetchone()[0] == 1007
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_SWEDEN_PRODUCT_FINDER'").fetchone()[0] == 675
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_SPAIN_PRODUCT_FINDER'").fetchone()[0] == 938
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_FRANCE_PRODUCT_FINDER'").fetchone()[0] == 705
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_TURKEY_PRODUCT_FINDER'").fetchone()[0] == 583
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_CANADA_PRODUCT_FINDER'").fetchone()[0] == 289
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_CHINA_PRODUCT_FINDER'").fetchone()[0] == 278
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_CZECH_PRODUCT_FINDER'").fetchone()[0] == 1146
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_MEXICO_PRODUCT_FINDER'").fetchone()[0] == 314
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_SOUTH_AFRICA_PRODUCT_FINDER'").fetchone()[0] == 756
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_BRAZIL_PRODUCT_FINDER'").fetchone()[0] == 182
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_NORWAY_PRODUCT_FINDER'").fetchone()[0] == 649
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_HUNGARY_PRODUCT_FINDER'").fetchone()[0] == 506
    for source_id, _, products, *_ in additional_fuchs_specs.values():
        assert db.execute("SELECT count(*) FROM product_sources WHERE source_id=?", (source_id,)).fetchone()[0] == products
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='LIQUI_MOLY_2020_PRODUCT_CATALOG'").fetchone()[0] == 419
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='LIQUI_MOLY_CURRENT_OPENAPI'").fetchone()[0] == 447
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='LIQUI_MOLY_PART_NUMBER'").fetchone()[0] == 1482
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='LIQUI_MOLY_MASTER_SKU'").fetchone()[0] == 447
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='LIQUI_MOLY_ARTICLE_SKU'").fetchone()[0] == 985
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='ANP_BRAZIL_REGISTRATION_NUMBER'").fetchone()[0] == 12664 + report["anp_brazil_monitoring_registered_historical_identities_added"]
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='ANP_BRAZIL_LUBRICANT_MONITORING_HISTORY'").fetchone()[0] == 12048
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='ANP_BRAZIL_LUBRICANT_MONITORING_PDF_HISTORY'").fetchone()[0] == 1552
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='ANP_BRAZIL_LUBRICANT_MONITORING_PDF_EXCEPTIONS'").fetchone()[0] == (
        len(anp_monitoring_pdf_exception_rows)
        + report["anp_brazil_monitoring_historical_identities_added_by_primary_source"].get(
            "ANP_BRAZIL_LUBRICANT_MONITORING_PDF_EXCEPTIONS", 0
        )
    )
    assert len(anp_monitoring_rows) == 11026
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='INDONESIA_NPT_REGISTRATION_NUMBER'").fetchone()[0] == 12575
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='INDONESIA_NPT_LUBRICANT_REGISTRY'").fetchone()[0] == 12626
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='source_registration_number_missing'").fetchone()[0] == 51
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='THAILAND_DOEB_LUBRICANT_REGISTRY'").fetchone()[0] == 5486
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='THAILAND_DOEB_REGISTRATION_NUMBER'").fetchone()[0] == 6213
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='thailand_doeb_registration_number_collision'").fetchone()[0] == 6
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='thailand_doeb_nonstandard_sae_notation'").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='DLA_QPD_FSC_9150'").fetchone()[0] == 431
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='DLA_QPD_FSC_6850_LUBRICANT_SCOPE'").fetchone()[0] == 25
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='DLA_QPD_FSC_8030_LUBRICANT_SCOPE'").fetchone()[0] == 80
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='BLUE_ANGEL_DE_UZ_178'").fetchone()[0] == 148
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='AUSTRIAN_ECOLABEL_UZ14_LUBRICANTS'").fetchone()[0] == 11
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='KOREA_ECOLABEL_EL611'").fetchone()[0] == 20
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='KOREA_ECOLABEL_EL509'").fetchone()[0] == 9
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='UAE_MOIAT_PRODUCT_CONFORMITY'").fetchone()[0] == 1840
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='EAEU_CONFORMITY_LUBRICANT_PRODUCTS'").fetchone()[0] == 38444
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='EPA_SAFER_CHOICE_LUBRICANTS'").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM external_codes WHERE source_id='EPA_SAFER_CHOICE_LUBRICANTS'").fetchone()[0] == 12
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='EPA_CHEMEXPO_CPDAT_LUBRICANTS'").fetchone()[0] == len(epa_chemexpo_rows)
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='EPA_CHEMEXPO_PRODUCT_ID'").fetchone()[0] == epa_chemexpo_report["kept_product_occurrences"]
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='PSQCA_ENGINE_OIL_CM_LICENCES'").fetchone()[0] == 14
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='PSQCA_CM_LICENCE'").fetchone()[0] == 14
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='TISI_TWO_STROKE_OIL_LICENCES'").fetchone()[0] == 10
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='TISI_MANUFACTURING_LICENCE'").fetchone()[0] == 10
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='SAMR_CHINA_2025_NONCONFORMING_FLUIDS'").fetchone()[0] == 25
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='SAMR_CHINA_2025_NONCONFORMING_FLUIDS'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='SAMR_CHINA_2023_NONCONFORMING_FLUIDS'").fetchone()[0] == 126
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SAMR_CHINA_2023_NONCONFORMING_FLUIDS'").fetchone()[0] == 125
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='SAMR_CHINA_2023_NONCONFORMING_FLUIDS'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='SAMR_CHINA_2024_NONCONFORMING_FUEL_ADDITIVES'").fetchone()[0] == 23
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SAMR_CHINA_2024_NONCONFORMING_FUEL_ADDITIVES'").fetchone()[0] == 23
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='SAMR_CHINA_2024_NONCONFORMING_FUEL_ADDITIVES'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS'").fetchone()[0] == 12
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS'").fetchone()[0] == 11
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 106
    assert db.execute("SELECT count(DISTINCT product_id) FROM product_sources WHERE source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 102
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 101
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION' AND evidence_status='official_government_conforming_product_inspection_observation'").fetchone()[0] == 90
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION' AND evidence_status='official_government_nonconforming_product_inspection_observation'").fetchone()[0] == 11
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 60
    assert db.execute("SELECT count(DISTINCT product_id) FROM product_sources WHERE source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 58
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 49
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION' AND evidence_status='official_government_conforming_product_inspection_observation'").fetchone()[0] == 42
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION' AND evidence_status='official_government_nonconforming_product_inspection_observation'").fetchone()[0] == 7
    assert db.execute("""
        SELECT count(*) FROM product_sources ps JOIN products p ON p.product_id=ps.product_id
        WHERE p.product_name_raw='奥迪原装刹车液'
          AND ps.source_id IN ('SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION', 'SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION')
    """).fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 100
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 98
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION' AND evidence_status='official_government_conforming_product_inspection_observation'").fetchone()[0] == 97
    assert db.execute("SELECT count(*) FROM products WHERE source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION' AND evidence_status='official_government_nonconforming_product_inspection_observation'").fetchone()[0] == 1
    assert db.execute("""
        SELECT count(*) FROM (
            SELECT product_id FROM product_sources
            WHERE source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'
            GROUP BY product_id HAVING count(*)=2
        )
    """).fetchone()[0] == 2
    assert db.execute("""
        SELECT count(*) FROM (
            SELECT s.product_id FROM specifications s
            JOIN products p ON p.product_id=s.product_id
            WHERE p.source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'
              AND s.spec_type='samr_inspection_occurrences'
            GROUP BY s.product_id HAVING count(*)=2
        )
    """).fetchone()[0] == 4
    shenzhen_history_product = db.execute("""
        SELECT p.product_id, p.source_id FROM product_sources ps
        JOIN products p ON p.product_id=ps.product_id
        WHERE ps.source_record_id='SZ-CN-2021-002'
    """).fetchone()
    assert shenzhen_history_product[1] == "SAMR_CHINA_2023_NONCONFORMING_FLUIDS"
    assert db.execute("""
        SELECT count(*) FROM specifications
        WHERE product_id=? AND spec_type='samr_inspection_occurrences'
    """, (shenzhen_history_product[0],)).fetchone()[0] == 3
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='review_cross_source_identity'
          AND (a.source_id LIKE 'SAMR_CHINA_%' OR b.source_id LIKE 'SAMR_CHINA_%'
               OR a.source_id='SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS'
               OR b.source_id='SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS'
               OR a.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'
               OR a.source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'
               OR a.source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION')
    """).fetchone()[0] == 20
    assert db.execute("""
        SELECT count(*) FROM duplicate_decisions d
        JOIN products a ON a.product_id=d.product_id_a
        JOIN products b ON b.product_id=d.product_id_b
        WHERE d.decision='keep_separate_professional_signature_conflict'
          AND (a.source_id LIKE 'SAMR_CHINA_%' OR b.source_id LIKE 'SAMR_CHINA_%'
               OR a.source_id='SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS'
               OR b.source_id='SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS'
               OR a.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION'
               OR a.source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION'
               OR a.source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION'
               OR b.source_id='SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION')
    """).fetchone()[0] == 15
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='PHILIPPINES_BPS_PS_BRAKE_FLUID_LICENCES'").fetchone()[0] == 89
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='PHILIPPINES_BPS_ICC_BRAKE_FLUID_CERTIFICATES'").fetchone()[0] == 34
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='PHILIPPINES_BPS_PS_LICENCE'").fetchone()[0] == 89
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='PHILIPPINES_BPS_ICC_CERTIFICATE'").fetchone()[0] == 68
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='GSA_GHANA_2025_CERTIFIED_LUBRICANT_PRODUCTS'").fetchone()[0] == 16
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='GHANA_GSA_PRODUCT_LICENCE'").fetchone()[0] == 16
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='GSA_GHANA_2025_CERTIFIED_LUBRICANT_PRODUCTS'").fetchone()[0] == 0
    assert db.execute("""
        SELECT count(*) FROM certificates c JOIN products p ON p.product_id=c.product_id
        WHERE p.source_id LIKE 'PHILIPPINES_BPS_%'
    """).fetchone()[0] == 123
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id LIKE 'PHILIPPINES_BPS_%'").fetchone()[0] == 0
    assert db.execute("""
        SELECT count(*) FROM products p
        WHERE p.source_id LIKE 'PHILIPPINES_BPS_%'
          AND NOT EXISTS (
              SELECT 1 FROM specifications s
              WHERE s.product_id=p.product_id AND s.spec_type='coolant_class'
          )
    """).fetchone()[0] == 4
    assert db.execute("""
        SELECT count(*) FROM specifications s JOIN products p ON p.product_id=s.product_id
        WHERE p.source_id LIKE 'PHILIPPINES_BPS_%'
          AND s.spec_type='coolant_class' AND s.spec_value='ENV6'
    """).fetchone()[0] == 1
    assert db.execute("""
        SELECT count(*) FROM certificates c
        JOIN products p ON p.product_id=c.product_id
        WHERE p.source_id='PSQCA_ENGINE_OIL_CM_LICENCES'
    """).fetchone()[0] == 14
    assert db.execute("""
        SELECT count(*) FROM certificates c
        JOIN products p ON p.product_id=c.product_id
        WHERE p.source_id='TISI_TWO_STROKE_OIL_LICENCES'
    """).fetchone()[0] == 10
    assert db.execute("""
        SELECT count(*) FROM products
        WHERE source_id='TISI_TWO_STROKE_OIL_LICENCES'
          AND (json_extract(profile_match_basis_json, '$.sae') IS NOT NULL
               OR json_extract(profile_match_basis_json, '$.api') IS NOT NULL)
    """).fetchone()[0] == 0
    assert db.execute("""
        SELECT count(*) FROM products
        WHERE source_id='PSQCA_ENGINE_OIL_CM_LICENCES'
          AND (json_extract(profile_match_basis_json, '$.sae') IS NOT NULL
               OR json_extract(profile_match_basis_json, '$.api') IS NOT NULL)
    """).fetchone()[0] == 0
    assert db.execute("""
        SELECT count(*)
        FROM product_sources ps
        JOIN products p ON p.product_id = ps.product_id
        WHERE ps.source_id='EPA_CHEMEXPO_CPDAT_LUBRICANTS'
          AND ps.source_record_id='EPA-CHEMEXPO-22FC008D410855F6'
          AND p.source_id='KEBS_SMARK_LUBRICANT_PRODUCTS'
    """).fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='KEBS_SMARK_LUBRICANT_PRODUCTS'").fetchone()[0] == 750
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='KEBS_SMARK_PERMIT'").fetchone()[0] == 775
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='UNBS_CERTIFIED_LUBRICANT_PRODUCTS'").fetchone()[0] == 46
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='TBS_CERTIFIED_LUBRICANT_PRODUCTS'").fetchone()[0] == 183
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='SON_MANCAP_CHEMICAL_LUBRICANT_PRODUCTS'").fetchone()[0] == 608
    assert db.execute("SELECT count(*) FROM external_codes WHERE source_id='SON_MANCAP_CHEMICAL_LUBRICANT_PRODUCTS'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='RSB_SMARK_LUBRICANT_PRODUCTS'").fetchone()[0] == 9
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='RSB_SMARK_LICENCE'").fetchone()[0] == 9
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='UNBS_QMARK_PERMIT'").fetchone()[0] == 47
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='TBS_STANDARDS_MARK_LICENSE'").fetchone()[0] == 182
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='DLA_QPL_NUMBER'").fetchone()[0] == 537
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='dla_qpd_lifecycle_restriction'").fetchone()[0] == 96
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='FUCHS_PRODUCT_UID'").fetchone()[0] == 23587
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='JASO_OIL_CODE'").fetchone()[0] == 3629
    assert db.execute("SELECT count(*) FROM sources WHERE bulk_ingest_allowed=0").fetchone()[0] == len(report["bulk_sources_blocked"])
    motor_enkt = db.execute("""
        SELECT count(*) FROM products p
        JOIN external_codes c USING(product_id)
        WHERE p.family_code='M' AND c.code_system='ENKT' AND c.code_value NOT LIKE '19.20.29.110%'
    """).fetchone()[0]
    flagged_motor_enkt = db.execute("""
        SELECT count(*) FROM products p
        JOIN quality_issues q USING(product_id)
        WHERE p.family_code='M' AND q.issue_code='classification_family_conflict' AND q.field='ENKT'
    """).fetchone()[0]
    assert motor_enkt == flagged_motor_enkt == 107
    policy_by_id = {source["source_id"]: source for source in policy["sources"]}
    for source in jaso_report["sources"]:
        assert policy_by_id[source["source_id"]]["source_sha256"] == source["source_sha256"]
        assert policy_by_id[source["source_id"]]["observed_count"] == source["rows"]
    for source in licensed_report["sources"]:
        assert policy_by_id[source["source_id"]]["source_sha256"] == source["source_sha256"]
        assert policy_by_id[source["source_id"]]["observed_count"] == source["rows"]
    assert policy_by_id["usda-biopreferred"]["source_sha256"] == biopreferred_report["normalized_output_sha256"]
    assert policy_by_id["usda-biopreferred"]["observed_count"] == biopreferred_report["rows"]
    assert policy_by_id["BLUE_ANGEL_DE_UZ_178"]["source_sha256"] == blue_angel_report["normalized_output_sha256"]
    assert policy_by_id["BLUE_ANGEL_DE_UZ_178"]["observed_count"] == blue_angel_report["normalized_products"]
    assert blue_angel_report["export_rows"] == blue_angel_report["official_product_cards"] == 149
    assert blue_angel_report["duplicate_export_occurrences_merged"] == 1
    assert blue_angel_report["category_occurrences"] == 159
    assert blue_angel_report["families"] == {"G": 7, "H": 33, "I": 86, "S": 19, "T": 3}
    assert all(not ({"address", "phone", "email", "image", "description"} & set(row)) for row in blue_angel_rows)
    assert policy_by_id["AUSTRIAN_ECOLABEL_UZ14_LUBRICANTS"]["source_sha256"] == austrian_uz14_report["normalized_output_sha256"]
    assert policy_by_id["AUSTRIAN_ECOLABEL_UZ14_LUBRICANTS"]["observed_count"] == austrian_uz14_report["normalized_products"]
    assert austrian_uz14_report["licensees"] == 5
    assert austrian_uz14_report["products_by_family"] == {"H": 4, "I": 7}
    assert len({row["source_record_id"] for row in austrian_uz14_rows}) == 11
    assert all(row["lifecycle_status"] == "listed_in_current_uz14_directory_status_not_individually_dated" for row in austrian_uz14_rows)
    assert all(not ({"address", "postal_code", "phone", "email", "description", "image", "logo"} & set(row)) for row in austrian_uz14_rows)
    assert policy_by_id["KOREA_ECOLABEL_EL611"]["source_sha256"] == korea_ecolabel_report["normalized_output_sha256"]
    assert policy_by_id["KOREA_ECOLABEL_EL611"]["observed_count"] == korea_ecolabel_report["normalized_products"]
    assert korea_ecolabel_report["source_csv_rows_observed"] == 240695
    assert korea_ecolabel_report["portal_metadata_rows_reported"] == 99602
    assert korea_ecolabel_report["source_EL611_rows"] == 21
    assert korea_ecolabel_report["duplicate_package_occurrences_merged"] == 1
    assert korea_ecolabel_report["manufacturers"] == 6
    assert korea_ecolabel_report["families"] == {"H": 18, "I": 2}
    assert all(not ({"business_registration_number", "headquarters_location", "factory_location", "factory_id"} & set(row)) for row in korea_ecolabel_rows)
    assert policy_by_id["KOREA_ECOLABEL_EL509"]["source_sha256"] == korea_el509_report["normalized_output_sha256"]
    assert policy_by_id["KOREA_ECOLABEL_EL509"]["observed_count"] == korea_el509_report["normalized_products"]
    assert korea_el509_report["source_csv_rows_observed"] == 240695
    assert korea_el509_report["portal_metadata_rows_reported"] == 99602
    assert korea_el509_report["source_EL509_rows"] == 11
    assert korea_el509_report["duplicate_model_package_occurrences_merged"] == 2
    assert korea_el509_report["manufacturers"] == 2
    assert korea_el509_report["families"] == {"TF": 9}
    assert all(not ({"business_registration_number", "headquarters_location", "factory_location", "factory_id"} & set(row)) for row in korea_el509_rows)
    assert policy_by_id["UAE_MOIAT_PRODUCT_CONFORMITY"]["source_sha256"] == uae_moiat_report["normalized_output_sha256"]
    assert policy_by_id["UAE_MOIAT_PRODUCT_CONFORMITY"]["observed_count"] == uae_moiat_report["normalized_products"]
    assert uae_moiat_report["certificate_cards"] == 1236
    assert uae_moiat_report["product_certificate_occurrences"] == 3176
    assert uae_moiat_report["cross_certificate_occurrences_merged"] == 1336
    assert uae_moiat_report["families"] == {"M": 1561, "S": 183, "T": 49, "TF": 47}
    assert sum(uae_moiat_report["listing_pages_by_product_type"].values()) == 131
    assert len(uae_moiat_report["certificates_without_product_rows"]) == 177
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in uae_moiat_rows)
    assert policy_by_id["EPA_SAFER_CHOICE_LUBRICANTS"]["source_sha256"] == epa_safer_choice_report["normalized_output_sha256"]
    assert policy_by_id["EPA_SAFER_CHOICE_LUBRICANTS"]["observed_count"] == epa_safer_choice_report["normalized_products"]
    assert epa_safer_choice_report["source_csv_rows"] == 4786
    assert epa_safer_choice_report["explicit_lubricant_name_occurrences"] == 12
    assert epa_safer_choice_report["duplicate_identifier_occurrences_merged"] == 10
    assert epa_safer_choice_report["families"] == {"S": 2}
    assert all(not ({"city", "state", "address", "phone", "email"} & set(row)) for row in epa_safer_choice_rows)
    assert policy_by_id["EPA_CHEMEXPO_CPDAT_LUBRICANTS"]["source_sha256"] == epa_chemexpo_report["normalized_output_sha256"]
    assert policy_by_id["EPA_CHEMEXPO_CPDAT_LUBRICANTS"]["observed_count"] == epa_chemexpo_report["normalized_products"]
    assert epa_chemexpo_report["source_category_product_occurrences"] == 10342
    assert epa_chemexpo_report["kept_product_occurrences"] == 7450
    assert epa_chemexpo_report["excluded_product_occurrences"] == 2892
    assert len(epa_chemexpo_rows) == 5915
    assert report["epa_chemexpo_products_matched_to_existing"] == 275
    assert report["epa_chemexpo_products_added"] == 5640
    assert epa_chemexpo_report["kept_product_occurrences"] + epa_chemexpo_report["excluded_product_occurrences"] == 10342
    assert epa_chemexpo_report["within_source_occurrences_merged"] == epa_chemexpo_report["kept_product_occurrences"] - len(epa_chemexpo_rows)
    assert epa_chemexpo_report["licence"] == "CC0"
    assert epa_chemexpo_report["cpdat_release"] == "4.1 (May 2025)"
    assert epa_chemexpo_report["categories"]["380"] == {
        "general_category": "Industrial products",
        "product_family": "mold release agents",
        "product_type": "",
        "scope_rule": "filtered_mold_release",
        "source_products": 323,
        "kept_occurrences": 233,
        "excluded_occurrences": 90,
        "api_page_sha256": [
            "fa0675c78d57a6bace8a6c49f7b71765f43855fb72d1ec92842d3e719d4ede1e",
            "eedf25b591ab980878aa06347a33e9aaec1e0c9bdbe7e386bd41cd6d682a4f4b",
            "5b0d63c63b649ef1ba351e6519aa3a7399b8dc30b28af082113257554526bc92",
            "807385575db32c9a2ae5cfd96b089dbbec8547cd25a9c8adb4a73cac3cd33b4b",
        ],
    }
    assert epa_chemexpo_report["exclusions"]["puc_380_strict_mold_release_name_or_reviewed_assignment_filter"] == 90
    assert len({row["source_record_id"] for row in epa_chemexpo_rows}) == len(epa_chemexpo_rows)
    chemexpo_product_ids = [product_id for row in epa_chemexpo_rows for product_id in row["source_product_ids"]]
    assert len(chemexpo_product_ids) == len(set(chemexpo_product_ids)) == epa_chemexpo_report["kept_product_occurrences"]
    assert all(row["lifecycle_status"] == "historical_or_current_status_not_reported" for row in epa_chemexpo_rows)
    assert all(row["source_product_urls"] == [f"https://comptox.epa.gov/chemexpo/product/{value}/" for value in row["source_product_ids"]] for row in epa_chemexpo_rows)
    assert all(not ({"address", "phone", "email", "source_document_text", "chemical_composition"} & set(row)) for row in epa_chemexpo_rows)
    assert policy_by_id["PSQCA_ENGINE_OIL_CM_LICENCES"]["source_sha256"] == psqca_report["normalized_output_sha256"]
    assert policy_by_id["PSQCA_ENGINE_OIL_CM_LICENCES"]["observed_count"] == 14
    assert psqca_report["source_occurrences"] == psqca_report["normalized_licence_brand_scopes"] == 14
    assert psqca_report["lifecycle_statuses"] == {"certification_expired": 13, "certification_valid_as_of_source_query": 1}
    assert psqca_report["families"] == {"M": 14}
    assert len({row["licence_number"] for row in psqca_rows}) == 14
    assert all(row["technical"]["sae"] == row["technical"]["api"] == [] for row in psqca_rows)
    assert all(row["product_name_basis"] == "source_reported_certified_brand_scope_not_individual_grade" for row in psqca_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in psqca_rows)
    assert report["tisi_two_stroke_oil_input_sha256"] == tisi_report["normalized_output_sha256"]
    assert policy_by_id["TISI_TWO_STROKE_OIL_LICENCES"]["source_sha256"] == tisi_report["normalized_output_sha256"]
    assert policy_by_id["TISI_TWO_STROKE_OIL_LICENCES"]["observed_count"] == 10
    assert tisi_report["source_occurrences"] == tisi_report["normalized_licence_holder_scopes"] == 10
    assert tisi_report["unique_licence_holders"] == 9
    assert tisi_report["permit_types"] == {"manufacturing": 10}
    assert tisi_report["issue_year_range"] == ["2005", "2022"]
    assert tisi_report["families"] == {"M": 10}
    assert len({row["permit_number"] for row in tisi_rows}) == 10
    assert all(row["family_code"] == "M" for row in tisi_rows)
    assert all(row["technical"]["sae"] == row["technical"]["api"] == [] for row in tisi_rows)
    assert all(row["product_name_basis"] == "source_reported_certified_holder_scope_not_individual_brand_grade_or_sku" for row in tisi_rows)
    assert all(row["lifecycle_status"] == "published_in_current_tisi_licence_search_current_validity_not_independently_stated" for row in tisi_rows)
    assert all(not ({"address", "tax_id", "phone", "email", "contact_person"} & set(row)) for row in tisi_rows)
    assert report["samr_china_2025_input_sha256"] == samr_china_report["normalized_output_sha256"]
    assert policy_by_id["SAMR_CHINA_2025_NONCONFORMING_FLUIDS"]["source_sha256"] == samr_china_report["normalized_output_sha256"]
    assert policy_by_id["SAMR_CHINA_2025_NONCONFORMING_FLUIDS"]["observed_count"] == 25
    assert samr_china_report["source_xlsx_sha256"] == "0042e67b52973d78660f2c137f912cac2ceb785ff56132467f5eb24248c0f801"
    assert samr_china_report["source_relevant_rows"] == 28
    assert samr_china_report["excluded_counterfeit_rows_without_producer"] == 3
    assert {row["source_row"] for row in samr_china_report["excluded_source_rows"]} == {11, 29, 36}
    assert samr_china_report["rows_by_source_product_kind"] == {"发动机润滑油": 6, "机动车辆制动液": 9, "车用尿素水溶液": 10}
    assert samr_china_report["families"] == {"M": 6, "TF": 19}
    assert samr_china_report["rows_with_api"] == samr_china_report["rows_with_sae"] == 6
    assert samr_china_report["rows_with_dot"] == 5
    assert samr_china_report["rows_with_hzy"] == 9
    assert len({row["source_record_id"] for row in samr_china_rows}) == 25
    assert all(row["inspection_outcome"] == "nonconforming" for row in samr_china_rows)
    assert all(row["lifecycle_status"] == "official_2025_national_inspection_nonconforming_current_market_status_unverified" for row in samr_china_rows)
    assert all(row["manufacturer"] and row["source_note"] != "假冒" for row in samr_china_rows)
    assert all(not ({"retailer", "seller", "platform", "testing_laboratory", "producer_location", "address", "phone", "email"} & set(row)) for row in samr_china_rows)
    assert report["samr_china_2023_input_sha256"] == samr_china_2023_report["normalized_output_sha256"]
    assert policy_by_id["SAMR_CHINA_2023_NONCONFORMING_FLUIDS"]["source_sha256"] == samr_china_2023_report["normalized_output_sha256"]
    assert policy_by_id["SAMR_CHINA_2023_NONCONFORMING_FLUIDS"]["observed_count"] == 126
    assert samr_china_2023_report["source_xlsx_sha256"] == "6eff7f988cba8b51e04ac3e7735affa790431cb9e51aec21eb9087928d38d45b"
    assert samr_china_2023_report["source_relevant_rows"] == 136
    assert samr_china_2023_report["excluded_suspected_counterfeit_rows"] == 10
    assert {row["source_row"] for row in samr_china_2023_report["excluded_source_rows"]} == {2, 6, 9, 72, 85, 103, 122, 124, 138, 158}
    assert samr_china_2023_report["rows_by_source_product_kind"] == {"机动车发动机冷却液": 6, "机动车发动机润滑油": 15, "机动车辆制动液": 13, "汽车风窗玻璃清洗液": 8, "车用尿素水溶液": 44, "车用汽油清净剂": 40}
    assert samr_china_2023_report["families"] == {"M": 15, "S": 40, "TF": 71}
    assert samr_china_2023_report["rows_with_api"] == samr_china_2023_report["rows_with_sae"] == 15
    assert samr_china_2023_report["rows_with_dot"] == 8
    assert samr_china_2023_report["rows_with_hzy"] == 13
    assert samr_china_2023_report["rows_with_coolant_class"] == 6
    assert samr_china_2023_report["rows_with_washer_class"] == 8
    assert samr_china_2023_report["rows_with_aus32"] == 4
    assert samr_china_2023_report["retest_confirmed_nonconforming_rows"] == 17
    assert all(row["inspection_outcome"] == "nonconforming" for row in samr_china_2023_rows)
    assert all("涉嫌假冒" not in row["source_note"] for row in samr_china_2023_rows)
    assert all(not ({"retailer", "seller", "testing_laboratory", "producer_location", "address", "phone", "email"} & set(row)) for row in samr_china_2023_rows)
    assert report["samr_china_2024_input_sha256"] == samr_china_2024_report["normalized_output_sha256"]
    assert policy_by_id["SAMR_CHINA_2024_NONCONFORMING_FUEL_ADDITIVES"]["source_sha256"] == samr_china_2024_report["normalized_output_sha256"]
    assert policy_by_id["SAMR_CHINA_2024_NONCONFORMING_FUEL_ADDITIVES"]["observed_count"] == 23
    assert samr_china_2024_report["source_xlsx_sha256"] == "a5c76c5d5834f1d33512e4177b79cc0601f13c4ee0fefa2a8e8c45db8caf1ca5"
    assert samr_china_2024_report["families"] == {"S": 23}
    assert samr_china_2024_report["retest_confirmed_nonconforming_rows"] == 9
    assert all(row["inspection_outcome"] == "nonconforming" and row["family_code"] == "S" for row in samr_china_2024_rows)
    assert report["shenzhen_china_2021_input_sha256"] == shenzhen_china_2021_report["normalized_output_sha256"]
    assert policy_by_id["SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS"]["source_sha256"] == shenzhen_china_2021_report["normalized_output_sha256"]
    assert policy_by_id["SHENZHEN_CHINA_2021_NONCONFORMING_AUTOMOTIVE_FLUIDS"]["observed_count"] == 12
    assert shenzhen_china_2021_report["source_xlsx_sha256"] == "73a011b46ee94611f487c89791bf9cf01c7a2a978c59c495f46bd95dd7f414bd"
    assert shenzhen_china_2021_report["source_rows"] == 13 and shenzhen_china_2021_report["excluded_diesel_fuel_rows"] == 1
    assert shenzhen_china_2021_report["families"] == {"M": 6, "S": 1, "TF": 5}
    assert shenzhen_china_2021_report["rows_with_api"] == shenzhen_china_2021_report["rows_with_sae"] == 5
    assert shenzhen_china_2021_report["rows_with_coolant_class"] == 2
    assert shenzhen_china_2021_report["rows_with_washer_class"] == 1
    assert shenzhen_china_2021_report["retest_confirmed_nonconforming_rows"] == 3
    assert all(row["inspection_outcome"] == "nonconforming" for row in shenzhen_china_2021_rows)
    assert all(not ({"retailer", "seller", "testing_laboratory", "producer_location", "address", "phone", "email"} & set(row)) for row in shenzhen_china_2021_rows)
    assert report["shenzhen_china_2020_input_sha256"] == shenzhen_china_2020_report["normalized_output_sha256"]
    assert policy_by_id["SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION"]["source_sha256"] == shenzhen_china_2020_report["normalized_output_sha256"]
    assert policy_by_id["SHENZHEN_CHINA_2020_AUTOMOTIVE_FLUID_INSPECTION"]["observed_count"] == 106
    assert shenzhen_china_2020_report["source_xlsx_sha256"] == {
        "conforming": "6eb62911fd9b0e6a8c4e89cd33f2b5e0463ec174812277b04219967a5d2d94eb",
        "nonconforming": "9dda9aa6d8b4b295e559b63a7dc6b3e2a1a3c47484bd40d1e8a9ea9c81eb6a83",
    }
    assert shenzhen_china_2020_report["outcomes"] == {"conforming": 95, "nonconforming": 11}
    assert shenzhen_china_2020_report["source_product_types"] == {
        "机动车制动液": 22, "机动车发动机冷却液": 25, "机动车发动机润滑油": 26,
        "车用尿素溶液": 20, "车用汽油清净剂": 13,
    }
    assert shenzhen_china_2020_report["families_before_identity_merging"] == {"M": 26, "S": 13, "TF": 67}
    assert shenzhen_china_2020_report["rows_with_api"] == 24
    assert shenzhen_china_2020_report["rows_with_sae"] == 26
    assert shenzhen_china_2020_report["rows_with_acea"] == 2
    assert shenzhen_china_2020_report["rows_with_ilsac"] == 2
    assert shenzhen_china_2020_report["rows_with_brake_class"] == 20
    assert shenzhen_china_2020_report["rows_with_coolant_class_or_freezing_point"] == 11
    assert shenzhen_china_2020_report["rows_with_aus32"] == 9
    assert shenzhen_china_2020_report["counterfeit_source_notes"] == 1
    assert {row["source_record_id"] for row in shenzhen_china_2020_rows if "source_reported_counterfeit_trademark_product" in row["source_quality_flags"]} == {"SZ-CN-2020-NC-010"}
    assert all(not ({"retailer", "seller", "testing_laboratory", "producer_location", "address", "phone", "email"} & set(row)) for row in shenzhen_china_2020_rows)
    assert report["shenzhen_china_2019_input_sha256"] == shenzhen_china_2019_report["normalized_output_sha256"]
    assert policy_by_id["SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION"]["source_sha256"] == shenzhen_china_2019_report["normalized_output_sha256"]
    assert policy_by_id["SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION"]["observed_count"] == 60
    assert shenzhen_china_2019_report["source_xls_sha256"] == {
        "conforming": "838dec55b34970ddbd4e6ccdcd7654f2551940c0104d676c5a631bd0cbb8b81e",
        "nonconforming": "cae0176f84915f288d929ef9e2bfd372475b96ff0670519bc6d154eb283ed846",
    }
    assert shenzhen_china_2019_report["outcomes"] == {"conforming": 51, "nonconforming": 9}
    assert shenzhen_china_2019_report["source_product_types"] == {
        "机动车制动液": 20, "车用尿素溶液": 20, "车用燃油添加剂": 20,
    }
    assert shenzhen_china_2019_report["outcomes_by_product_type"] == {
        "机动车制动液": {"conforming": 18, "nonconforming": 2},
        "车用尿素溶液": {"conforming": 16, "nonconforming": 4},
        "车用燃油添加剂": {"conforming": 17, "nonconforming": 3},
    }
    assert shenzhen_china_2019_report["families_before_identity_merging"] == {"S": 20, "TF": 40}
    assert shenzhen_china_2019_report["rows_with_brake_class"] == 19
    assert shenzhen_china_2019_report["rows_with_aus32"] == 3
    assert shenzhen_china_2019_report["rows_with_atypical_aus30"] == 1
    shenzhen_2019_by_id = {row["source_record_id"]: row for row in shenzhen_china_2019_rows}
    assert shenzhen_2019_by_id["SZ-CN-2019-C-036"]["technical"]["urea_class_source_reported"] == ["AUS 30"]
    assert "source_reported_atypical_aus30_not_normalized_to_aus32" in shenzhen_2019_by_id["SZ-CN-2019-C-036"]["source_quality_flags"]
    assert shenzhen_2019_by_id["SZ-CN-2019-C-046"]["brand"] == "可兰素 智蓝1号"
    assert len(shenzhen_2019_by_id["SZ-CN-2019-NC-001"]["nonconforming_items"]) == 5
    assert len(shenzhen_2019_by_id["SZ-CN-2019-NC-004"]["nonconforming_items"]) == 2
    assert all(row["inspection_standards_scope_source_reported"] for row in shenzhen_china_2019_rows)
    assert all(not ({"retailer", "seller", "testing_laboratory", "producer_location", "address", "phone", "email"} & set(row)) for row in shenzhen_china_2019_rows)
    assert report["shenzhen_china_2025_input_sha256"] == shenzhen_china_2025_report["normalized_output_sha256"]
    assert policy_by_id["SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION"]["source_sha256"] == shenzhen_china_2025_report["normalized_output_sha256"]
    assert policy_by_id["SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION"]["observed_count"] == 100
    assert shenzhen_china_2025_report["source_pdf_sha256"] == "6cb5b14209ad9717d4d790175889d5b19bb5917016f2449e6317d821a12a1905"
    assert shenzhen_china_2025_report["source_pdf_pages"] == 5
    assert shenzhen_china_2025_report["source_all_rows"] == 246
    assert shenzhen_china_2025_report["outcomes"] == {"conforming": 99, "nonconforming": 1}
    assert shenzhen_china_2025_report["source_product_types"] == {"冷却液": 11, "制动液": 6, "润滑油": 56, "燃油添加剂": 9, "玻璃水": 9, "车用尿素溶液": 9}
    assert shenzhen_china_2025_report["families_before_identity_merging"] == {"M": 55, "S": 10, "TF": 35}
    assert shenzhen_china_2025_report["rows_with_api"] == 47
    assert shenzhen_china_2025_report["rows_with_sae"] == 55
    assert shenzhen_china_2025_report["rows_with_acea"] == 7
    assert shenzhen_china_2025_report["rows_with_ilsac"] == 3
    assert shenzhen_china_2025_report["rows_with_brake_class"] == 6
    assert shenzhen_china_2025_report["rows_with_coolant_class"] == 11
    assert shenzhen_china_2025_report["rows_with_washer_class"] == 9
    assert shenzhen_china_2025_report["rows_with_aus32"] == 2
    assert {row["source_record_id"] for row in shenzhen_china_2025_rows if row["inspection_outcome"] == "nonconforming"} == {"SZ-CN-2025-235"}
    assert all(not ({"retailer", "seller", "testing_laboratory", "producer_location", "address", "phone", "email"} & set(row)) for row in shenzhen_china_2025_rows)
    assert report["shanghai_china_2023_2025_input_sha256"] == shanghai_china_report["normalized_output_sha256"]
    assert shanghai_china_report["source_observations"] == 390
    assert shanghai_china_report["outcomes"] == {"conforming": 376, "nonconforming": 14}
    assert shanghai_china_report["families"] == {"H": 170, "I": 13, "M": 30, "T": 177}
    assert shanghai_china_report["rows_with_sae"] == 30
    assert shanghai_china_report["rows_with_api"] == 30
    assert shanghai_china_report["rows_with_api_gl"] == 131
    assert shanghai_china_report["rows_with_iso_vg"] == 158
    assert shanghai_china_report["rows_with_china_lubricant_class"] == 159
    assert sum(shanghai_china_report["source_counts"].values()) == 390
    for source_id, count in shanghai_china_report["source_counts"].items():
        assert policy_by_id[source_id]["source_sha256"] == shanghai_china_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == count
    assert all(row["market"] == "China / Shanghai" for row in shanghai_china_rows)
    assert all(not ({"retailer", "seller", "sampled_seller", "shopping_centre", "platform", "certification_agency", "address", "phone", "email"} & set(row)) for row in shanghai_china_rows)
    shanghai_link_counts = dict(db.execute(
        "SELECT source_id, count(*) FROM product_sources "
        "WHERE source_id LIKE 'SHANGHAI_CHINA_%' GROUP BY source_id"
    ))
    assert shanghai_link_counts == shanghai_china_report["source_counts"]
    assert sum(shanghai_link_counts.values()) == 390
    assert report["beijing_china_2018_input_sha256"] == beijing_china_report["normalized_output_sha256"]
    assert beijing_china_report["source_observations"] == 294
    assert beijing_china_report["source_counts"] == {
        "BEIJING_CHINA_2018_AUTOMOTIVE_FLUID_INSPECTION_1": 147,
        "BEIJING_CHINA_2018_AUTOMOTIVE_FLUID_INSPECTION_2": 147,
    }
    assert beijing_china_report["source_product_types"] == {
        "发动机冷却液": 40, "机动车制动液": 5, "柴油机油、汽油机油": 162,
        "车用尿素溶液": 69, "车用汽油清净剂": 18,
    }
    assert beijing_china_report["outcomes"] == {"conforming": 283, "nonconforming": 11}
    assert beijing_china_report["families"] == {"M": 162, "S": 18, "TF": 114}
    assert beijing_china_report["rows_with_sae"] == 161
    assert beijing_china_report["rows_with_api"] == 155
    assert beijing_china_report["rows_with_ilsac"] == 5
    assert beijing_china_report["rows_with_acea"] == 2
    assert beijing_china_report["rows_with_jaso"] == 2
    assert beijing_china_report["rows_with_coolant_class"] == 1
    assert beijing_china_report["rows_with_coolant_freezing_point"] == 40
    assert beijing_china_report["rows_with_brake_class"] == 5
    assert beijing_china_report["rows_with_explicit_aus32"] == 5
    assert len({row["source_record_id"] for row in beijing_china_rows}) == 294
    assert sum(row["inspection_outcome"] == "nonconforming" for row in beijing_china_rows) == 11
    assert sum("source_note_reports_follow_up_reinspection_conforming" in row["source_quality_flags"] for row in beijing_china_rows) == 8
    assert not any(row["inspection_retest_confirmed_nonconforming"] for row in beijing_china_rows)
    assert all(row["market"] == "China / Beijing" for row in beijing_china_rows)
    assert all(not ({"retailer", "seller", "sampled_seller", "address", "phone", "email"} & set(row)) for row in beijing_china_rows)
    for source_id, count in beijing_china_report["source_counts"].items():
        assert policy_by_id[source_id]["source_sha256"] == beijing_china_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == count
    beijing_link_counts = dict(db.execute(
        "SELECT source_id, count(*) FROM product_sources "
        "WHERE source_id LIKE 'BEIJING_CHINA_%' GROUP BY source_id"
    ))
    assert beijing_link_counts == beijing_china_report["source_counts"]
    assert sum(beijing_link_counts.values()) == 294
    assert report["shenzhen_china_2016_2017_input_sha256"] == shenzhen_china_2016_2017_report["normalized_output_sha256"]
    assert shenzhen_china_2016_2017_report["source_observations"] == len(shenzhen_china_2016_2017_rows) == 140
    assert shenzhen_china_2016_2017_report["source_counts"] == {
        "SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION": 80,
        "SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION": 60,
    }
    assert shenzhen_china_2016_2017_report["outcomes"] == {"conforming": 129, "nonconforming": 11}
    assert shenzhen_china_2016_2017_report["outcomes_by_source"] == {
        "SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION": {"conforming": 72, "nonconforming": 8},
        "SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION": {"conforming": 57, "nonconforming": 3},
    }
    assert shenzhen_china_2016_2017_report["families"] == {"M": 140}
    assert shenzhen_china_2016_2017_report["rows_with_sae"] == 137
    assert shenzhen_china_2016_2017_report["rows_with_api"] == 96
    assert shenzhen_china_2016_2017_report["rows_with_acea"] == 4
    assert shenzhen_china_2016_2017_report["rows_with_ilsac"] == 7
    assert shenzhen_china_2016_2017_report["rows_with_oem_approval"] == 2
    assert len({row["source_record_id"] for row in shenzhen_china_2016_2017_rows}) == 140
    assert all(row["family_code"] == "M" and row["market"] == "China / Shenzhen" for row in shenzhen_china_2016_2017_rows)
    assert all(not ({"retailer", "seller", "sampled_seller", "inspected_enterprise", "address", "phone", "email"} & set(row)) for row in shenzhen_china_2016_2017_rows)
    for source_id, count in shenzhen_china_2016_2017_report["source_counts"].items():
        assert policy_by_id[source_id]["source_sha256"] == shenzhen_china_2016_2017_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == count
    shenzhen_china_2016_2017_link_counts = dict(db.execute(
        "SELECT source_id, count(*) FROM product_sources "
        "WHERE source_id IN ('SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION', "
        "'SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION') GROUP BY source_id"
    ))
    assert shenzhen_china_2016_2017_link_counts == shenzhen_china_2016_2017_report["source_counts"]
    assert sum(shenzhen_china_2016_2017_link_counts.values()) == 140
    assert db.execute(
        "SELECT count(DISTINCT product_id) FROM product_sources "
        "WHERE source_record_id IN ('SZ-CN-2016-C-042', 'SZ-CN-2017-NC-001')"
    ).fetchone()[0] == 1
    mixed_outcome_product_id = db.execute(
        "SELECT product_id FROM product_sources WHERE source_record_id='SZ-CN-2016-C-042'"
    ).fetchone()[0]
    mixed_outcome_occurrences = [
        ast.literal_eval(row[0])
        for row in db.execute(
            "SELECT spec_value FROM specifications WHERE product_id=? "
            "AND spec_type='samr_inspection_occurrences'",
            (mixed_outcome_product_id,),
        )
    ]
    assert Counter(row["inspection_outcome"] for row in mixed_outcome_occurrences) == {
        "conforming": 1, "nonconforming": 1,
    }
    assert db.execute(
        "SELECT count(*) FROM specifications WHERE spec_type='oem_approval_source_reported' "
        "AND spec_value IN ('WSS-M2C915BA', 'WSS-M2C929 BA')"
    ).fetchone()[0] == 2
    assert report["qingdao_china_2021_2025_input_sha256"] == qingdao_china_report["normalized_output_sha256"]
    assert qingdao_china_report["source_workbooks"] == 18
    assert qingdao_china_report["source_all_rows"] == 268
    assert qingdao_china_report["retained_product_observations"] == 262
    assert qingdao_china_report["excluded_motor_fuel_rows"] == 6
    assert qingdao_china_report["outcomes"] == {"conforming": 261, "nonconforming": 1}
    assert qingdao_china_report["families"] == {"H": 8, "M": 40, "S": 6, "T": 9, "TF": 199}
    assert qingdao_china_report["rows_with_api"] == 40
    assert qingdao_china_report["rows_with_sae"] == 49
    assert qingdao_china_report["rows_with_api_gl"] == 9
    assert qingdao_china_report["rows_with_iso_vg"] == 8
    assert qingdao_china_report["rows_with_china_lubricant_class"] == 7
    assert qingdao_china_report["rows_with_brake_class"] == 42
    assert qingdao_china_report["rows_with_coolant_class"] == 24
    assert qingdao_china_report["rows_with_coolant_freezing_point"] == 30
    assert qingdao_china_report["rows_with_washer_class"] == 14
    assert qingdao_china_report["rows_with_washer_freezing_point"] == 18
    assert qingdao_china_report["rows_with_aus32"] == 106
    assert len({row["source_record_id"] for row in qingdao_china_rows}) == 262
    assert {row["source_record_id"] for row in qingdao_china_rows if row["inspection_outcome"] == "nonconforming"} == {
        "QD-CN-2025_SPECIAL6-787636233154-001"
    }
    assert all(row["market"] == "China / Qingdao" for row in qingdao_china_rows)
    assert all(not ({
        "retailer", "seller", "sampled_seller", "inspected_enterprise", "inspected_unit",
        "unified_social_credit_code", "address", "district", "laboratory", "phone", "email",
    } & set(row)) for row in qingdao_china_rows)
    assert {item["source_xls_sha256"] for item in qingdao_china_report["source_files"]} == {
        "8ad7db962d9a237277c6e1512b0ed8ecee5c56a6f54478080cdbc82fc33a53b7",
        "4f65c28e38843cf41688f9ce5fbc7a377712c96acb2d7064bbb62a66239975a8",
        "86ae45b7c16c86ef82dacdb6316f06bfca35dbf97d6bfd4c7de39fad174248cb",
        "c509b5570105e87063dc1280147afe5da8f984ceeed991773b09a564cf7a1952",
        "5f4e96580c76da5816edfcb6e869b4af32088b8d2e76dd74b809e9dd8b1e2ab7",
        "b579f8c74d9614bd4d0b7f03320ab7e5f52ad480723f3b6d727cbe8ac0cabc08",
        "6b0ea8977cd276769f47b705a31904985d1a6e0cd1183255b7e1cd722be2113f",
        "9944e5c1630109bd20d64cd918cef67e5dd3df864848cdd44c4d0a61968eadc1",
        "80a396cced87f97e242235a65ebb9f5bc3045116fbdc702f9d85b3d4384422ed",
        "d2f0e3ae0df1446c74247732c1283428c1792e8dbf8835be16a5ab4c2a438fb7",
        "af6f0c667365b59efa1be7e649f57d8f17c1246e77ec2a8862233dbdc08a00dc",
        "a7078dbd4893cb04cdfb95725f8321342cf6f62df2a5a69a4c9734c9a7b3afda",
        "22e2bbd650b27ef1aa118460414cf2b928277a975a966120cb96ac0bd43a5a5d",
        "f4085d082f4861b907be24917f82e8fec4f20e8f105149e660f839d590e77395",
        "adfb6a102ce55d9dfe09237440a4ffeb5a8ff481288d2975b189562d5260fff1",
        "2a87656f2054750c6e196ffc8d393d5937e94899908364d97bbe4e82150277ff",
        "91e409157ec73527a49ef64833dfb170f31a476113a72ec5033f76a05379d2e9",
        "c6efdabd90f0e9adc6919718c4c711c0c7c85af12e0583b57a844221cd81bf79",
    }
    for source_id, count in qingdao_china_report["source_counts"].items():
        assert policy_by_id[source_id]["source_sha256"] == qingdao_china_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == count
    qingdao_link_counts = dict(db.execute(
        "SELECT source_id, count(*) FROM product_sources "
        "WHERE source_id LIKE 'QINGDAO_CHINA_%' GROUP BY source_id"
    ))
    assert qingdao_link_counts == qingdao_china_report["source_counts"]
    assert sum(qingdao_link_counts.values()) == 262
    assert db.execute(
        "SELECT count(DISTINCT product_id) FROM product_sources WHERE source_id LIKE 'QINGDAO_CHINA_%'"
    ).fetchone()[0] == 213
    assert db.execute(
        "SELECT count(DISTINCT product_id) FROM product_sources WHERE source_record_id IN "
        "('SAMR-CN-2023-074', 'QD-CN-2023-557282227031-004', "
        "'QD-CN-2024-511444161658-010', 'QD-CN-2025_DAILY2-505998188416-040')"
    ).fetchone()[0] == 1
    qingdao_longitudinal_product_id = db.execute(
        "SELECT product_id FROM product_sources WHERE source_record_id='SAMR-CN-2023-074'"
    ).fetchone()[0]
    qingdao_longitudinal_occurrences = [
        ast.literal_eval(row[0])
        for row in db.execute(
            "SELECT spec_value FROM specifications WHERE product_id=? "
            "AND spec_type='samr_inspection_occurrences'",
            (qingdao_longitudinal_product_id,),
        )
    ]
    assert Counter(row["inspection_outcome"] for row in qingdao_longitudinal_occurrences) == {
        "conforming": 6, "nonconforming": 1,
    }
    assert report["jilin_china_2024_2025_input_sha256"] == jilin_china_report["normalized_output_sha256"]
    assert jilin_china_report["source_all_rows"] == 415
    assert jilin_china_report["retained_product_observations"] == 404
    assert jilin_china_report["excluded_motor_fuel_rows"] == 11
    assert jilin_china_report["outcomes"] == {"conforming": 379, "nonconforming": 25}
    assert jilin_china_report["suspected_counterfeit"] == 3
    assert jilin_china_report["families"] == {"M": 70, "S": 46, "TF": 288}
    assert jilin_china_report["rows_with_api"] == 70
    assert jilin_china_report["rows_with_sae"] == 70
    assert jilin_china_report["rows_with_acea"] == 1
    assert jilin_china_report["rows_with_ilsac"] == 1
    assert jilin_china_report["rows_with_brake_class"] == 71
    assert jilin_china_report["rows_with_coolant_class"] == 69
    assert jilin_china_report["rows_with_coolant_freezing_point"] == 69
    assert jilin_china_report["rows_with_washer_class"] == 70
    assert jilin_china_report["rows_with_washer_freezing_point"] == 7
    assert jilin_china_report["rows_with_aus32"] == 74
    assert jilin_china_report["unavailable_historical_source"]["status_at_snapshot"] == "official_attachment_http_404_not_ingested"
    assert {item["source_pdf_sha256"] for item in jilin_china_report["source_files"]} == {
        "095535608bce0826e046264dc79be24c2f7c7d1429d252dd850f18aae6a35461",
        "e437192cab367b60ed0b2b58812e1eaebda2df643e41812a7c4eb45998368c3d",
    }
    assert len({row["source_record_id"] for row in jilin_china_rows}) == 404
    assert sum(row["inspection_suspected_counterfeit"] for row in jilin_china_rows) == 3
    assert all(row["market"] == "China / Jilin" for row in jilin_china_rows)
    assert all(not ({
        "retailer", "seller", "sampled_seller", "inspected_enterprise", "inspected_unit",
        "unified_social_credit_code", "address", "district", "laboratory", "phone", "email",
    } & set(row)) for row in jilin_china_rows)
    for source_id, count in jilin_china_report["source_counts"].items():
        assert policy_by_id[source_id]["source_sha256"] == jilin_china_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == count
    jilin_link_counts = dict(db.execute(
        "SELECT source_id, count(*) FROM product_sources "
        "WHERE source_id LIKE 'JILIN_CHINA_%' GROUP BY source_id"
    ))
    assert jilin_link_counts == jilin_china_report["source_counts"]
    assert sum(jilin_link_counts.values()) == 404
    assert wuxi_china_report["source_xls_sha256"] == "d9d6b453523985b306e6fe5a84cffd5355bd03445e796226113a2febcbe3a9fa"
    assert wuxi_china_report["source_rows"] == 10
    assert wuxi_china_report["families"] == {"H": 2, "M": 8}
    assert wuxi_china_report["outcomes"] == {"conforming": 10}
    assert wuxi_china_report["rows_with_api"] == 7
    assert wuxi_china_report["rows_with_sae"] == 8
    assert wuxi_china_report["rows_with_china_lubricant_class"] == 2
    assert wuxi_china_report["rows_with_iso_vg"] == 2
    assert len({row["source_record_id"] for row in wuxi_china_rows}) == 10
    assert all(row["market"] == "China / Wuxi" for row in wuxi_china_rows)
    assert all(not ({
        "retailer", "seller", "sampled_seller", "inspected_enterprise", "inspected_unit",
        "manufacturer_address", "address", "district", "laboratory", "phone", "email",
    } & set(row)) for row in wuxi_china_rows)
    assert policy_by_id["WUXI_CHINA_2024_LUBRICANT_INSPECTION"]["source_sha256"] == wuxi_china_report["normalized_output_sha256"]
    assert policy_by_id["WUXI_CHINA_2024_LUBRICANT_INSPECTION"]["observed_count"] == 10
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='WUXI_CHINA_2024_LUBRICANT_INSPECTION'"
    ).fetchone()[0] == 10
    assert yantai_china_report["source_html_sha256"] == "b87f4e6ff53c591878ea114f219b63b0a350c1a0ecd4be734ffe238d87000eb0"
    assert yantai_china_report["source_all_product_rows"] == 350
    assert yantai_china_report["excluded_out_of_scope_rows"] == 335
    assert yantai_china_report["families"] == {"S": 15}
    assert yantai_china_report["outcomes"] == {"conforming": 15}
    assert yantai_china_report["distinct_nominal_producers"] == 10
    assert len({row["source_record_id"] for row in yantai_china_rows}) == 15
    assert all(row["market"] == "China / Yantai" and row["family_code"] == "S" for row in yantai_china_rows)
    assert all(not ({
        "retailer", "seller", "sampled_seller", "inspected_enterprise", "inspected_unit",
        "social_credit_code", "unified_social_credit_code", "address", "laboratory", "phone", "email",
    } & set(row)) for row in yantai_china_rows)
    assert policy_by_id["YANTAI_CHINA_2025_GASOLINE_DETERGENT_INSPECTION"]["source_sha256"] == yantai_china_report["normalized_output_sha256"]
    assert policy_by_id["YANTAI_CHINA_2025_GASOLINE_DETERGENT_INSPECTION"]["observed_count"] == 15
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='YANTAI_CHINA_2025_GASOLINE_DETERGENT_INSPECTION'"
    ).fetchone()[0] == 15
    assert db.execute("""
        SELECT count(*) FROM products
        WHERE source_id='SAMR_CHINA_2025_NONCONFORMING_FLUIDS'
          AND lifecycle_status='official_2025_national_inspection_nonconforming_current_market_status_unverified'
    """).fetchone()[0] == 25
    assert db.execute("""
        SELECT count(DISTINCT p.product_id)
        FROM products p JOIN specifications s ON s.product_id=p.product_id
        WHERE p.source_id='SAMR_CHINA_2025_NONCONFORMING_FLUIDS'
          AND p.family_code='M' AND s.spec_type='sae_engine'
    """).fetchone()[0] == 6
    assert db.execute("""
        SELECT count(DISTINCT p.product_id)
        FROM products p JOIN specifications s ON s.product_id=p.product_id
        WHERE p.source_id='SAMR_CHINA_2025_NONCONFORMING_FLUIDS'
          AND p.family_code='M' AND s.spec_type='api'
    """).fetchone()[0] == 6
    assert philippines_bps_report["source_reports"]["PHILIPPINES_BPS_PS_BRAKE_FLUID_LICENCES"] == {
        "source_rows": 3558,
        "relevant_source_rows": 13,
        "normalized_rows": 89,
    }
    assert philippines_bps_report["source_reports"]["PHILIPPINES_BPS_ICC_BRAKE_FLUID_CERTIFICATES"] == {
        "source_rows": 19461,
        "relevant_source_rows": 114,
        "false_positive_rows_excluded": 1,
        "expanded_grade_occurrences": 129,
        "normalized_rows": 34,
    }
    assert philippines_bps_report["brake_fluid_classes"] == {"DOT 3": 62, "DOT 4": 56, "ENV6": 1}
    assert philippines_bps_report["source_quality_flags"] == {
        "brake_fluid_class_not_reported": 4,
        "source_brand_name_and_model_type_fields_conflict": 1,
        "source_product_category_typo_retained": 2,
        "source_reports_env6_without_dot_class": 1,
        "source_standard_inconsistent_with_brake_fluid_category": 3,
        "source_type_appears_to_contain_tyre_size": 2,
    }
    assert len({row["source_record_id"] for row in philippines_bps_rows}) == 123
    assert sum(not row["technical"]["brake_fluid_class"] for row in philippines_bps_rows) == 4
    assert all(row["family_code"] == "TF" for row in philippines_bps_rows)
    assert all(not ({"region", "address", "phone", "email", "contact_person"} & set(row)) for row in philippines_bps_rows)
    for source_id, expected in (("PHILIPPINES_BPS_PS_BRAKE_FLUID_LICENCES", 89), ("PHILIPPINES_BPS_ICC_BRAKE_FLUID_CERTIFICATES", 34)):
        assert policy_by_id[source_id]["source_sha256"] == philippines_bps_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == expected
    assert ghana_gsa_report["source_pdf_sha256"] == "8085170f9bdff86278d07c43b0375cd77727e6dde84f4320cc8403d7d7bd7bc2"
    assert ghana_gsa_report["families"] == {"M": 13, "T": 2, "TF": 1}
    assert ghana_gsa_report["lifecycle_statuses"] == {
        "certification_expired_before_catalog_snapshot": 1,
        "certification_valid_as_of_catalog_snapshot": 15,
    }
    assert ghana_gsa_report["rows_with_sae"] == 15
    assert ghana_gsa_report["rows_with_api"] == 12
    assert len({row["licence_number"] for row in ghana_gsa_rows}) == 16
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in ghana_gsa_rows)
    assert policy_by_id["GSA_GHANA_2025_CERTIFIED_LUBRICANT_PRODUCTS"]["source_sha256"] == ghana_gsa_report["normalized_output_sha256"]
    assert policy_by_id["GSA_GHANA_2025_CERTIFIED_LUBRICANT_PRODUCTS"]["observed_count"] == 16
    assert ecuador_inen_report["audited_all_product_rows"] == 155
    assert ecuador_inen_report["normalized_products"] == len(ecuador_inen_rows) == 30
    assert ecuador_inen_report["families"] == {"M": 25, "T": 5}
    assert ecuador_inen_report["rows_with_sae"] == 30
    assert ecuador_inen_report["rows_with_api"] == 25
    assert ecuador_inen_report["rows_with_jaso"] == 1
    assert len({row["source_record_id"] for row in ecuador_inen_rows}) == 30
    assert all(row["market"] == "Ecuador" for row in ecuador_inen_rows)
    assert all(not ({"address", "city", "phone", "email", "contact_person"} & set(row)) for row in ecuador_inen_rows)
    for post in ecuador_inen_report["posts"].values():
        source_id = post["source_id"]
        assert policy_by_id[source_id]["source_sha256"] == ecuador_inen_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == post["relevant_rows"]
        assert db.execute(
            "SELECT count(*) FROM product_sources WHERE source_id=?", (source_id,)
        ).fetchone()[0] == post["relevant_rows"]
    assert db.execute(
        "SELECT count(*) FROM products WHERE evidence_status='official_government_product_certification_announcement'"
    ).fetchone()[0] == 11
    assert ecuador_inen_current_report["source_pdf_sha256"] == "42bac24e08c30af8966cce6025a24e7ba2ce84487c712afba2d303c9a8111c26"
    assert ecuador_inen_current_report["source_pdf_pages"] == 81
    assert ecuador_inen_current_report["audited_all_certificate_rows"] == 1763
    assert ecuador_inen_current_report["normalized_products"] == len(ecuador_inen_current_rows) == 410
    assert ecuador_inen_current_report["families"] == {"I": 2, "M": 288, "T": 120}
    assert ecuador_inen_current_report["certified_standards"] == {
        "NTE INEN 2027:2024": 156,
        "NTE INEN 2028:2021": 119,
        "NTE INEN 2029:2018": 2,
        "NTE INEN 2030:2024": 133,
    }
    assert ecuador_inen_current_report["rows_with_sae"] == 408
    assert ecuador_inen_current_report["rows_with_api"] == 288
    assert ecuador_inen_current_report["rows_with_api_gl"] == 120
    assert ecuador_inen_current_report["rows_with_jaso"] == 14
    assert ecuador_inen_current_report["rows_with_ilsac"] == 3
    assert ecuador_inen_current_report["rows_with_acea"] == 1
    assert ecuador_inen_current_report["valid_at_snapshot"] == 410
    assert ecuador_inen_current_report["source_standard_family_conflicts"] == 1
    assert ecuador_inen_current_report["announcement_rows_exactly_matched_to_current"] == 19
    assert ecuador_inen_current_report["announcement_rows_not_in_current_registry"] == 11
    assert len({row["certificate_number"] for row in ecuador_inen_current_rows}) == 410
    assert all(not ({"geographic_location", "address", "city", "phone", "email", "contact_person"} & set(row)) for row in ecuador_inen_current_rows)
    assert policy_by_id["ECUADOR_INEN_2026_07_CURRENT_CERTIFIED_LUBRICANTS"]["source_sha256"] == ecuador_inen_current_report["normalized_output_sha256"]
    assert policy_by_id["ECUADOR_INEN_2026_07_CURRENT_CERTIFIED_LUBRICANTS"]["observed_count"] == 410
    assert db.execute(
        "SELECT count(*) FROM products WHERE evidence_status='official_government_current_product_certification_registry'"
    ).fetchone()[0] == 410
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='ECUADOR_INEN_2026_07_CURRENT_CERTIFIED_LUBRICANTS'"
    ).fetchone()[0] == 410
    assert peru_sunat_report["source_pdf_sha256"] == "f8e154f1b352853fcc95aabebf4543b71905eef8e097742cc87b7b93c4e61ce8"
    assert peru_sunat_report["source_pdf_pages"] == 302
    assert peru_sunat_report["audited_all_product_rows"] == 4518
    assert peru_sunat_report["broad_candidate_rows_reviewed"] == 176
    assert peru_sunat_report["relevant_source_occurrences"] == 95
    assert peru_sunat_report["duplicate_source_occurrences_collapsed"] == 8
    assert peru_sunat_report["normalized_product_identities"] == len(peru_sunat_rows) == 87
    assert peru_sunat_report["families"] == {"G": 20, "H": 1, "I": 2, "S": 51, "TF": 13}
    assert peru_sunat_report["source_table_extraction_anomalies"] == 1
    assert all(row["source_evaluation"] == "NO CONTROLADO" for row in peru_sunat_rows)
    assert all(not (row["manufacturer_or_certificate_holder"] or ({"address", "phone", "email", "contact_person"} & set(row))) for row in peru_sunat_rows)
    assert policy_by_id["PERU_SUNAT_2025_NONCONTROLLED_LUBRICANT_PRODUCTS"]["source_sha256"] == peru_sunat_report["normalized_output_sha256"]
    assert policy_by_id["PERU_SUNAT_2025_NONCONTROLLED_LUBRICANT_PRODUCTS"]["observed_count"] == 87
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='PERU_SUNAT_2025_NONCONTROLLED_LUBRICANT_PRODUCTS'"
    ).fetchone()[0] == 87
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='PERU_SUNAT_2025_NONCONTROLLED_LUBRICANT_PRODUCTS'"
    ).fetchone()[0] == 87
    assert paraguay_dnit_report["normalized_source_sha256"] == "9f8c1a975a77552d1af539c415a6a2cc390b9b98e7c321a9454dcee108ef0cb3"
    assert paraguay_dnit_report["source_rows_audited"] == 627
    assert paraguay_dnit_report["normalized_products"] == len(paraguay_dnit_rows) == 19
    assert paraguay_dnit_report["families"] == {"M": 13, "S": 3, "T": 3}
    assert paraguay_dnit_report["brands"] == {
        "BASTON": 1, "Brand not stated (DNIT source)": 1, "Mobil": 10,
        "Mundial Prime": 1, "Shell": 4, "TEKORO": 1, "Valvoline": 1,
    }
    assert paraguay_dnit_report["rows_with_sae"] == 12
    assert paraguay_dnit_report["rows_with_api"] == 2
    assert paraguay_dnit_report["rows_with_explicit_performance"] == 3
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in paraguay_dnit_rows)
    assert policy_by_id["PARAGUAY_DNIT_LUBRICANT_TARIFF_CLASSIFICATION_RULINGS"]["source_sha256"] == paraguay_dnit_report["normalized_output_sha256"]
    assert policy_by_id["PARAGUAY_DNIT_LUBRICANT_TARIFF_CLASSIFICATION_RULINGS"]["observed_count"] == 19
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='PARAGUAY_DNIT_LUBRICANT_TARIFF_CLASSIFICATION_RULINGS'"
    ).fetchone()[0] == 19
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='PARAGUAY_DNIT_LUBRICANT_TARIFF_CLASSIFICATION_RULINGS'"
    ).fetchone()[0] == 19
    assert guatemala_siges_report["source_catalog_total_rows"] == 206416
    assert guatemala_siges_report["source_catalog_updated_at"] == "13/07/2026 11:41"
    assert guatemala_siges_report["search_union_rows"] == 2973
    assert guatemala_siges_report["selected_source_presentations"] == 752
    assert guatemala_siges_report["normalized_item_identities"] == len(guatemala_siges_rows) == 279
    assert guatemala_siges_report["families"] == {"C": 7, "G": 57, "H": 38, "I": 16, "M": 54, "S": 58, "T": 43, "TF": 6}
    assert guatemala_siges_report["selected_raw_sha256"] == "174380b63cef99959bb3c0132c763816b1ebc96bf3b197dc0cde900a0ff1568a"
    assert all(row["brand"] == "Brand not stated (SIGES source)" for row in guatemala_siges_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in guatemala_siges_rows)
    assert policy_by_id["GUATEMALA_SIGES_LUBRICANT_ITEM_NOMENCLATURE"]["source_sha256"] == guatemala_siges_report["normalized_output_sha256"]
    assert policy_by_id["GUATEMALA_SIGES_LUBRICANT_ITEM_NOMENCLATURE"]["observed_count"] == 279
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='GUATEMALA_SIGES_LUBRICANT_ITEM_NOMENCLATURE'"
    ).fetchone()[0] == 279
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='GUATEMALA_SIGES_LUBRICANT_ITEM_NOMENCLATURE'"
    ).fetchone()[0] == 279
    assert costa_rica_health_report["audited_total_rows"] == 106372
    assert costa_rica_health_report["audited_source_rows"] == {"after_2007": 62532, "before_2007": 43840}
    assert costa_rica_health_report["retained_source_rows"] == {"after_2007": 6176, "before_2007": 3735}
    assert costa_rica_health_report["normalized_products"] == len(costa_rica_health_rows) == 9911
    assert costa_rica_health_report["families"] == {"C": 214, "G": 1450, "H": 543, "I": 340, "M": 1195, "S": 5143, "T": 854, "TF": 172}
    assert costa_rica_health_report["source_workbook_sha256"] == {
        "after_2007": "ab5d966547dc81c6d485090411bf6ee7156ccb4414565a4305f880246f3c758e",
        "before_2007": "5cc6ca26fa8baaebc416e324ac91aef146cb7837d0d25d0df4ec3385d74f7b6f",
    }
    assert all(not ({"REP_LEGAL", "CIA_USO_REG", "address", "phone", "email", "contact_person"} & set(row)) for row in costa_rica_health_rows)
    assert policy_by_id["COSTA_RICA_HEALTH_HISTORICAL_CHEMICAL_PRODUCT_REGISTRATIONS"]["source_sha256"] == costa_rica_health_report["normalized_output_sha256"]
    assert policy_by_id["COSTA_RICA_HEALTH_HISTORICAL_CHEMICAL_PRODUCT_REGISTRATIONS"]["observed_count"] == 9911
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='COSTA_RICA_HEALTH_HISTORICAL_CHEMICAL_PRODUCT_REGISTRATIONS'"
    ).fetchone()[0] == 9911
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='COSTA_RICA_HEALTH_HISTORICAL_CHEMICAL_PRODUCT_REGISTRATIONS'"
    ).fetchone()[0] == 9911
    assert bolivia_ypfb_report["wp_total_pages"] == 74
    assert bolivia_ypfb_report["selected_product_pages"] == 27
    assert bolivia_ypfb_report["normalized_product_variants"] == len(bolivia_ypfb_rows) == 47
    assert bolivia_ypfb_report["automotive_variants"] == 13
    assert bolivia_ypfb_report["industrial_variants"] == 34
    assert bolivia_ypfb_report["families"] == {"G": 5, "H": 10, "I": 7, "M": 12, "T": 9, "TF": 4}
    assert bolivia_ypfb_report["catalog_sha256"] == "1e97a275d2efc7e5f73bd607a5e9d3c521ab4b47652709ea493c2f41f97451fb"
    assert all(row["manufacturer"] == "YPFB Refinación S.A." for row in bolivia_ypfb_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in bolivia_ypfb_rows)
    assert policy_by_id["BOLIVIA_YPFB_CURRENT_LUBRICANT_CATALOG"]["source_sha256"] == bolivia_ypfb_report["normalized_output_sha256"]
    assert policy_by_id["BOLIVIA_YPFB_CURRENT_LUBRICANT_CATALOG"]["observed_count"] == 47
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='BOLIVIA_YPFB_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 47
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='BOLIVIA_YPFB_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 47
    assert mozambique_petromoc_report[
        "normalized_product_grade_rows"
    ] == len(mozambique_petromoc_rows) == report[
        "mozambique_petromoc_legacy_source_rows"
    ] == 60
    assert mozambique_petromoc_report["technical_document_pages"] == 39
    assert mozambique_petromoc_report["source_product_sheets"] == 29
    assert mozambique_petromoc_report["families"] == {
        "C": 1, "E": 1, "G": 3, "H": 10,
        "I": 20, "M": 15, "T": 9, "TF": 1,
    }
    assert mozambique_petromoc_report[
        "technical_document_sha256"
    ] == "145f5ff42aae8fded1a543795ad8aa163dc86a5c79188c0246ed84a40b67890d"
    assert mozambique_petromoc_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/mozambique-petromoc-legacy-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["lifecycle_status"] == "officially_linked_legacy_catalog"
        for row in mozambique_petromoc_rows
    )
    assert all(
        row["market"] == "Mozambique"
        and row["brand"] == "PETROMOC"
        for row in mozambique_petromoc_rows
    )
    assert all(
        not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in mozambique_petromoc_rows
    )
    assert policy_by_id[
        "MOZAMBIQUE_PETROMOC_OFFICIALLY_LINKED_LEGACY_CATALOG"
    ]["source_sha256"] == mozambique_petromoc_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "MOZAMBIQUE_PETROMOC_OFFICIALLY_LINKED_LEGACY_CATALOG"
    ]["observed_count"] == 60
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='MOZAMBIQUE_PETROMOC_OFFICIALLY_LINKED_LEGACY_CATALOG'"
    ).fetchone()[0] == 60
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='MOZAMBIQUE_PETROMOC_OFFICIALLY_LINKED_LEGACY_CATALOG'"
    ).fetchone()[0] == 60
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='MOZAMBIQUE_PETROMOC_OFFICIALLY_LINKED_LEGACY_CATALOG'"
    ).fetchone()[0] == 0
    assert uganda_mpower_report[
        "detail_pages"
    ] == len(uganda_mpower_rows) == report[
        "uganda_mpower_current_source_rows"
    ] == 16
    assert uganda_mpower_report["listing_pages"] == 2
    assert uganda_mpower_report["brands"] == {"GOLDSTAR": 5, "LUBEX": 11}
    assert uganda_mpower_report["families"] == {
        "G": 1, "H": 1, "M": 9, "T": 5,
    }
    assert uganda_mpower_report["package_occurrences"] == 33
    assert uganda_mpower_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/uganda-mpower-current-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["lifecycle_status"] == "current_official_catalog"
        and row["market"] == "Uganda"
        for row in uganda_mpower_rows
    )
    assert all(
        not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in uganda_mpower_rows
    )
    assert policy_by_id[
        "UGANDA_MPOWER_CURRENT_COMPLETE_PRODUCT_PAGES"
    ]["source_sha256"] == uganda_mpower_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "UGANDA_MPOWER_CURRENT_COMPLETE_PRODUCT_PAGES"
    ]["observed_count"] == 16
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='UGANDA_MPOWER_CURRENT_COMPLETE_PRODUCT_PAGES'"
    ).fetchone()[0] == 16
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='UGANDA_MPOWER_CURRENT_COMPLETE_PRODUCT_PAGES'"
    ).fetchone()[0] == 16
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='UGANDA_MPOWER_CURRENT_COMPLETE_PRODUCT_PAGES'"
    ).fetchone()[0] == 0
    assert rwanda_almc_report[
        "product_grade_identities"
    ] == len(rwanda_almc_rows) == report[
        "rwanda_almc_current_source_rows"
    ] == 23
    assert rwanda_almc_report["tds_documents"] == 11
    assert rwanda_almc_report["tds_pages"] == 13
    assert rwanda_almc_report["families"] == {
        "G": 3, "H": 3, "I": 7, "M": 6, "T": 4,
    }
    assert rwanda_almc_report["quality_flags"] == {
        "description_mentions_15w40_but_tds_type_and_property_table_only_publish_20w50": 1,
        "hydraulic_iso_vg32_kv100_published_as_2_3_suspected_source_typo_retained": 1,
        "landing_page_title_claims_ep_0_1_2_3_but_tds_only_publishes_nlgi_1_2_3": 3,
    }
    assert rwanda_almc_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/rwanda-almc-current-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["lifecycle_status"] == "current_official_catalog"
        and row["market"] == "Rwanda"
        and row["brand"] == "ALMC"
        for row in rwanda_almc_rows
    )
    assert all(
        not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in rwanda_almc_rows
    )
    assert policy_by_id[
        "RWANDA_ALMC_CURRENT_COMPLETE_TDS_CATALOG"
    ]["source_sha256"] == rwanda_almc_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "RWANDA_ALMC_CURRENT_COMPLETE_TDS_CATALOG"
    ]["observed_count"] == 23
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='RWANDA_ALMC_CURRENT_COMPLETE_TDS_CATALOG'"
    ).fetchone()[0] == 23
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='RWANDA_ALMC_CURRENT_COMPLETE_TDS_CATALOG'"
    ).fetchone()[0] == 23
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='RWANDA_ALMC_CURRENT_COMPLETE_TDS_CATALOG'"
    ).fetchone()[0] == 0
    assert burundi_mogas_report["api_cards"] == 39
    assert burundi_mogas_report["excluded_non_lubricant_lpg_cylinders"] == 3
    assert burundi_mogas_report["relevant_shop_cards"] == 36
    assert burundi_mogas_report[
        "product_grade_identities"
    ] == len(burundi_mogas_rows) == report[
        "burundi_mogas_current_source_rows"
    ] == 45
    assert burundi_mogas_report["families"] == {
        "C": 2, "G": 14, "H": 5, "I": 2, "M": 15, "T": 6, "TF": 1,
    }
    assert burundi_mogas_report["cards_expanded_to_multiple_grades"] == 8
    assert burundi_mogas_report["cards_with_order_action"] == 36
    assert burundi_mogas_report["cards_source_reported_in_stock"] == 36
    assert burundi_mogas_report["cards_source_reported_purchasable"] == 36
    assert burundi_mogas_report["source_reported_currency_codes"] == {
        "USD": 36,
    }
    assert burundi_mogas_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/burundi-mogas-current-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["lifecycle_status"]
        == "current_shop_listing_country_and_currency_conflicted"
        and row["market"] == "Burundi"
        and row["brand"] == "MOGAS"
        and row["market_evidence_status"].endswith(
            "uganda_footer_conflict"
        )
        for row in burundi_mogas_rows
    )
    assert all(
        row["specifications"]["source_currency_code"] == "USD"
        and "source_price_excluded_from_analytical_offer_layer"
        in row["specifications"]["source_quality_flags"]
        for row in burundi_mogas_rows
    )
    assert all(
        not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in burundi_mogas_rows
    )
    assert policy_by_id[
        "BURUNDI_MOGAS_CURRENT_COMPLETE_SHOP_API"
    ]["source_sha256"] == burundi_mogas_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "BURUNDI_MOGAS_CURRENT_COMPLETE_SHOP_API"
    ]["observed_count"] == 45
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='BURUNDI_MOGAS_CURRENT_COMPLETE_SHOP_API'"
    ).fetchone()[0] == 45
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='BURUNDI_MOGAS_CURRENT_COMPLETE_SHOP_API'"
    ).fetchone()[0] == 45
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='BURUNDI_MOGAS_CURRENT_COMPLETE_SHOP_API'"
    ).fetchone()[0] == 0
    assert mogas_global_market_report["official_markets"] == 7
    assert mogas_global_market_report["full_catalog_markets"] == 6
    assert mogas_global_market_report[
        "full_catalog_api_cards_per_market"
    ] == 39
    assert mogas_global_market_report[
        "full_catalog_relevant_cards_per_market"
    ] == 36
    assert mogas_global_market_report["rwanda_api_cards"] == 5
    assert mogas_global_market_report[
        "market_card_observations"
    ] == len(mogas_global_market_rows) == report[
        "mogas_global_market_shop_observations"
    ] == 221
    assert mogas_global_market_report[
        "product_identity_links"
    ] == report[
        "mogas_global_market_product_identity_links"
    ] == 277
    assert mogas_global_market_report["observations_by_market"] == {
        "Burundi": 36,
        "Democratic Republic of the Congo": 36,
        "Kenya": 36,
        "Rwanda": 5,
        "Tanzania": 36,
        "Uganda": 36,
        "United Arab Emirates": 36,
    }
    assert mogas_global_market_report[
        "configured_currency_conflict_observations"
    ] == 180
    assert mogas_global_market_report[
        "local_currency_pending_offer_audit_observations"
    ] == 41
    assert mogas_global_market_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (
            ROOT / "data/mogas-global-market-shop-observations.jsonl"
        ).read_bytes()
    ).hexdigest()
    assert all(
        row["target_burundi_source_record_ids"]
        and row["source_is_in_stock"] is True
        and row["source_is_purchasable"] is True
        for row in mogas_global_market_rows
    )
    assert policy_by_id[
        "MOGAS_GLOBAL_OFFICIAL_COUNTRY_SHOP_APIS"
    ]["source_sha256"] == mogas_global_market_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "MOGAS_GLOBAL_OFFICIAL_COUNTRY_SHOP_APIS"
    ]["observed_count"] == 221
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='MOGAS_GLOBAL_OFFICIAL_COUNTRY_SHOP_APIS'"
    ).fetchone()[0] == 277
    assert db.execute(
        "SELECT count(DISTINCT product_id) FROM product_sources "
        "WHERE source_id='MOGAS_GLOBAL_OFFICIAL_COUNTRY_SHOP_APIS'"
    ).fetchone()[0] == 45
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='MOGAS_GLOBAL_OFFICIAL_COUNTRY_SHOP_APIS'"
    ).fetchone()[0] == 0
    assert rwanda_akinawa_report[
        "api_cards"
    ] == rwanda_akinawa_report[
        "product_identities"
    ] == len(rwanda_akinawa_rows) == report[
        "rwanda_akinawa_current_source_rows"
    ] == 10
    assert rwanda_akinawa_report["families"] == {
        "G": 1, "M": 6, "T": 3,
    }
    assert rwanda_akinawa_report["unambiguous_source_spec_rows"] == 4
    assert rwanda_akinawa_report[
        "expected_current_classifier_professional_key_complete_rows"
    ] == 3
    assert rwanda_akinawa_report["conflict_limited_rows"] == 6
    assert len(rwanda_akinawa_report["quality_flags"]) == 8
    assert rwanda_akinawa_report["cards_source_reported_in_stock"] == 10
    assert rwanda_akinawa_report["cards_source_reported_purchasable"] == 0
    assert rwanda_akinawa_report[
        "source_reported_price_minor_units"
    ] == {"0": 10}
    assert rwanda_akinawa_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/rwanda-akinawa-current-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["market"] == "Rwanda"
        and row["brand"] == "AKINAWA"
        and row["manufacturer"] == ""
        and row["specifications"]["source_is_purchasable"] is False
        for row in rwanda_akinawa_rows
    )
    assert policy_by_id[
        "RWANDA_LEADWAY_AKINAWA_CURRENT_COMPLETE_CATALOG"
    ]["source_sha256"] == rwanda_akinawa_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "RWANDA_LEADWAY_AKINAWA_CURRENT_COMPLETE_CATALOG"
    ]["observed_count"] == 10
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='RWANDA_LEADWAY_AKINAWA_CURRENT_COMPLETE_CATALOG'"
    ).fetchone()[0] == 10
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='RWANDA_LEADWAY_AKINAWA_CURRENT_COMPLETE_CATALOG'"
    ).fetchone()[0] == 10
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='RWANDA_LEADWAY_AKINAWA_CURRENT_COMPLETE_CATALOG'"
    ).fetchone()[0] == 0
    assert rwanda_rymax_report[
        "unique_product_pages"
    ] == len(rwanda_rymax_rows) == report[
        "rwanda_rymax_current_source_rows"
    ] == 68
    assert rwanda_rymax_report["listing_pages"] == 6
    assert rwanda_rymax_report["listing_card_occurrences"] == 81
    assert rwanda_rymax_report["duplicate_listing_occurrences"] == 13
    assert rwanda_rymax_report["families"] == {
        "C": 2, "E": 1, "G": 6, "H": 6, "I": 9,
        "M": 19, "T": 20, "TF": 1, "U": 4,
    }
    assert rwanda_rymax_report["products_with_approvals"] == 59
    assert rwanda_rymax_report["products_with_documents"] == 67
    assert rwanda_rymax_report["technical_documents"] == 123
    assert rwanda_rymax_report["document_types"] == {
        "SDS": 56, "TDS": 67,
    }
    assert rwanda_rymax_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/rwanda-rymax-current-products.jsonl").read_bytes()
    ).hexdigest()
    assert report["rwanda_rymax_products_matched_to_existing"] == 52
    assert report["rwanda_rymax_products_added"] == 16
    assert all(
        row["market"] == "Rwanda"
        and row["brand"] == "RYMAX"
        and row["manufacturer"] == "Rymax Lubricants"
        and not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in rwanda_rymax_rows
    )
    assert policy_by_id[
        "RWANDA_RYMAX_CURRENT_COMPLETE_PAGINATED_CATALOG"
    ]["source_sha256"] == rwanda_rymax_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "RWANDA_RYMAX_CURRENT_COMPLETE_PAGINATED_CATALOG"
    ]["observed_count"] == 68
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='RWANDA_RYMAX_CURRENT_COMPLETE_PAGINATED_CATALOG'"
    ).fetchone()[0] == 16
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='RWANDA_RYMAX_CURRENT_COMPLETE_PAGINATED_CATALOG'"
    ).fetchone()[0] == 68
    assert db.execute(
        "SELECT count(DISTINCT product_id) FROM product_sources "
        "WHERE source_id='RWANDA_RYMAX_CURRENT_COMPLETE_PAGINATED_CATALOG'"
    ).fetchone()[0] == 68
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='RWANDA_RYMAX_CURRENT_COMPLETE_PAGINATED_CATALOG'"
    ).fetchone()[0] == 0
    assert afal_east_africa_report[
        "featured_product_cards"
    ] == len(afal_east_africa_rows) == report[
        "afal_east_africa_featured_source_rows"
    ] == 6
    assert afal_east_africa_report["families"] == {"M": 6}
    assert afal_east_africa_report["brands"] == {
        "DELO": 3, "HAVOLINE": 3,
    }
    assert len(afal_east_africa_report["visible_distributor_markets"]) == 5
    assert len(afal_east_africa_report["structured_metadata_markets"]) == 6
    assert "South Sudan" not in afal_east_africa_report[
        "visible_distributor_markets"
    ]
    assert "South Sudan" in afal_east_africa_report[
        "structured_metadata_markets"
    ]
    assert afal_east_africa_report["images_hashed"] == 6
    assert afal_east_africa_report["offers_created"] == 0
    assert afal_east_africa_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/afal-east-africa-featured-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["market"] == "East Africa regional"
        and row["family_code"] == "M"
        and row["manufacturer"] == "Chevron Lubricants"
        and row["specifications"]["sae_engine"]
        and not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in afal_east_africa_rows
    )
    assert policy_by_id[
        "AFAL_CALTEX_EAST_AFRICA_FEATURED_PRODUCTS"
    ]["source_sha256"] == afal_east_africa_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "AFAL_CALTEX_EAST_AFRICA_FEATURED_PRODUCTS"
    ]["observed_count"] == 6
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='AFAL_CALTEX_EAST_AFRICA_FEATURED_PRODUCTS'"
    ).fetchone()[0] == 6
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='AFAL_CALTEX_EAST_AFRICA_FEATURED_PRODUCTS'"
    ).fetchone()[0] == 6
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='AFAL_CALTEX_EAST_AFRICA_FEATURED_PRODUCTS'"
    ).fetchone()[0] == 0
    assert south_sudan_taam_report[
        "category_pages"
    ] == 10
    assert south_sudan_taam_report["product_occurrences"] == 216
    assert south_sudan_taam_report[
        "duplicate_category_occurrences"
    ] == 41
    assert south_sudan_taam_report[
        "unique_product_codes"
    ] == len(south_sudan_taam_rows) == report[
        "south_sudan_taam_pakelo_source_rows"
    ] == 175
    assert south_sudan_taam_report["product_code_collisions"] == 0
    assert south_sudan_taam_report[
        "exact_existing_zf_identity_matches"
    ] == report[
        "south_sudan_taam_pakelo_products_matched_to_existing"
    ] == 2
    assert south_sudan_taam_report[
        "new_distributor_catalog_identities"
    ] == report[
        "south_sudan_taam_pakelo_products_added"
    ] == 173
    assert south_sudan_taam_report["families"] == {
        "C": 27, "G": 23, "H": 29, "I": 23, "M": 33,
        "S": 10, "T": 10, "TF": 20,
    }
    assert south_sudan_taam_report["records_with_sae"] == 32
    assert south_sudan_taam_report["records_with_iso_vg"] == 78
    assert south_sudan_taam_report["records_with_nlgi"] == 19
    assert south_sudan_taam_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/south-sudan-taam-pakelo-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["market"] == "South Sudan"
        and row["brand"] == "PAKELO"
        and row["specifications"]["product_code"]
        and not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in south_sudan_taam_rows
    )
    assert policy_by_id[
        "SOUTH_SUDAN_TAAM_PAKELO_COMPLETE_CATEGORY_CATALOG"
    ]["source_sha256"] == south_sudan_taam_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "SOUTH_SUDAN_TAAM_PAKELO_COMPLETE_CATEGORY_CATALOG"
    ]["observed_count"] == 175
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='SOUTH_SUDAN_TAAM_PAKELO_COMPLETE_CATEGORY_CATALOG'"
    ).fetchone()[0] == 173
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='SOUTH_SUDAN_TAAM_PAKELO_COMPLETE_CATEGORY_CATALOG'"
    ).fetchone()[0] == 175
    assert db.execute(
        "SELECT count(DISTINCT product_id) FROM product_sources "
        "WHERE source_id='SOUTH_SUDAN_TAAM_PAKELO_COMPLETE_CATEGORY_CATALOG'"
    ).fetchone()[0] == 175
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='SOUTH_SUDAN_TAAM_PAKELO_COMPLETE_CATEGORY_CATALOG'"
    ).fetchone()[0] == 0
    assert sudan_tappco_report["wordpress_all_posts"] == 35
    assert len(sudan_tappco_report["excluded_non_product_posts"]) == 2
    assert sudan_tappco_report["product_posts"] == 33
    assert sudan_tappco_report["category_counts"] == {
        "Auxiliary": 2, "Diesel oils": 3, "Gear and Transmission": 4,
        "Grease": 3, "Industrial": 16, "Marine and Two stroke": 3,
        "Motor oils": 2,
    }
    assert sudan_tappco_report["identity_rows"] == len(
        sudan_tappco_rows
    ) == report["sudan_tappco_source_rows"] == report[
        "sudan_tappco_products_added"
    ] == 73
    assert sudan_tappco_report["family_identity_counts"] == {
        "C": 11, "G": 9, "H": 13, "I": 15, "M": 11,
        "S": 1, "T": 11, "TF": 2,
    }
    assert sudan_tappco_report["grade_field_counts"] == {
        "dot": 1, "iso_vg": 34, "nlgi": 9, "sae_engine": 10,
        "sae_gear": 10, "source_grade": 9,
    }
    assert sudan_tappco_report["posts_without_tds"] == 3
    assert sudan_tappco_report["pdf_link_observations"] == 30
    assert sudan_tappco_report["unique_pdf_payloads"] == 27
    assert sudan_tappco_report["mismatched_tds_count"] == 3
    assert sudan_tappco_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/sudan-tappco-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["market"] == "Sudan"
        and row["brand"] == "TAPPCO"
        and not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in sudan_tappco_rows
    )
    assert all(
        "mismatched_tds_technical_fields_not_assigned_to_product"
        in row["specifications"]["source_quality_flags"]
        for row in sudan_tappco_rows
        if row["specifications"]["source_post_id"] in {1270, 1265, 1223}
    )
    assert policy_by_id[
        "SUDAN_TAPPCO_COMPLETE_PRODUCT_POST_CATALOG"
    ]["source_sha256"] == sudan_tappco_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "SUDAN_TAPPCO_COMPLETE_PRODUCT_POST_CATALOG"
    ]["observed_count"] == 73
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='SUDAN_TAPPCO_COMPLETE_PRODUCT_POST_CATALOG'"
    ).fetchone()[0] == 73
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='SUDAN_TAPPCO_COMPLETE_PRODUCT_POST_CATALOG'"
    ).fetchone()[0] == 73
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='SUDAN_TAPPCO_COMPLETE_PRODUCT_POST_CATALOG'"
    ).fetchone()[0] == 0
    assert ethiopia_noc_report["lubricant_link_occurrences"] == 23
    assert ethiopia_noc_report["reviewed_product_series"] == 15
    assert ethiopia_noc_report["identity_rows"] == len(
        ethiopia_noc_rows
    ) == report["ethiopia_noc_caltex_source_rows"] == 35
    assert ethiopia_noc_report["family_identity_counts"] == {
        "G": 3, "H": 13, "M": 7, "T": 12,
    }
    assert ethiopia_noc_report["resolved_pdf_observations"] == 22
    assert ethiopia_noc_report["unique_resolved_pdf_payloads"] == 21
    assert ethiopia_noc_report["broken_official_pdf_links"] == 1
    assert ethiopia_noc_report["mismatched_tds_count"] == 3
    assert ethiopia_noc_report[
        "exact_existing_identity_matches"
    ] == report[
        "ethiopia_noc_caltex_products_matched_to_existing"
    ] == 3
    assert ethiopia_noc_report[
        "new_archive_identities"
    ] == report["ethiopia_noc_caltex_products_added"] == 32
    assert ethiopia_noc_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/ethiopia-noc-caltex-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["market"] == "Ethiopia"
        and row["brand"] == "CALTEX"
        and not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in ethiopia_noc_rows
    )
    assert all(
        "mismatched_tds_technical_fields_not_assigned_to_product"
        in row["specifications"]["source_quality_flags"]
        for row in ethiopia_noc_rows
        if row["specifications"]["source_series"]
        in {"starplex", "molytex", "multifak"}
    )
    assert policy_by_id[
        "ETHIOPIA_NOC_CALTEX_RECOVERABLE_OFFICIAL_ARCHIVE"
    ]["source_sha256"] == ethiopia_noc_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "ETHIOPIA_NOC_CALTEX_RECOVERABLE_OFFICIAL_ARCHIVE"
    ]["observed_count"] == 35
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='ETHIOPIA_NOC_CALTEX_RECOVERABLE_OFFICIAL_ARCHIVE'"
    ).fetchone()[0] == 32
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='ETHIOPIA_NOC_CALTEX_RECOVERABLE_OFFICIAL_ARCHIVE'"
    ).fetchone()[0] == 35
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='ETHIOPIA_NOC_CALTEX_RECOVERABLE_OFFICIAL_ARCHIVE'"
    ).fetchone()[0] == 0
    assert scope_global_report["product_endpoint_rows"] == 62
    assert scope_global_report["nonempty_product_categories"] == 12
    assert scope_global_report["category_occurrences"] == 66
    assert scope_global_report["multi_category_products"] == 4
    assert scope_global_report["identity_rows"] == len(
        scope_global_rows
    ) == report["scope_global_source_rows"] == 200
    assert scope_global_report["family_identity_counts"] == {
        "C": 7, "G": 14, "H": 10, "I": 30, "M": 110,
        "S": 3, "T": 20, "TF": 6,
    }
    assert scope_global_report["grade_field_counts"] == {
        "dot": 4, "iso_vg": 47, "nlgi": 14, "sae_engine": 109,
        "sae_gear": 14, "source_grade": 12,
    }
    assert scope_global_report["linked_document_observations"] == 61
    assert scope_global_report["unique_linked_document_urls"] == 19
    assert scope_global_report["unique_linked_document_payloads"] == 19
    assert scope_global_report[
        "exact_existing_identity_matches"
    ] == report["scope_global_products_matched_to_existing"] == 1
    assert scope_global_report[
        "new_manufacturer_catalog_identities"
    ] == report["scope_global_products_added"] == 199
    assert scope_global_report[
        "catalog_map_market_presence_observation"
    ] == "Somalia"
    assert scope_global_report["somalia_sku_availability_inferred"] is False
    assert scope_global_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/scope-global-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["market"] == "Global manufacturer catalog"
        and row["brand"] == "SCOPE"
        and "somalia_named_on_manufacturer_catalog_map_but_no_sku_availability_inferred"
        in row["specifications"]["source_quality_flags"]
        and not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in scope_global_rows
    )
    assert policy_by_id[
        "SCOPE_GLOBAL_COMPLETE_LIVE_PRODUCT_CATALOG"
    ]["source_sha256"] == scope_global_report["normalized_output_sha256"]
    assert policy_by_id[
        "SCOPE_GLOBAL_COMPLETE_LIVE_PRODUCT_CATALOG"
    ]["observed_count"] == 200
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='SCOPE_GLOBAL_COMPLETE_LIVE_PRODUCT_CATALOG'"
    ).fetchone()[0] == 199
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='SCOPE_GLOBAL_COMPLETE_LIVE_PRODUCT_CATALOG'"
    ).fetchone()[0] == 200
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='SCOPE_GLOBAL_COMPLETE_LIVE_PRODUCT_CATALOG'"
    ).fetchone()[0] == 0
    assert angola_ngol_report["official_pdf_pages"] == 44
    assert angola_ngol_report["catalog_product_series"] == 64
    assert angola_ngol_report["target_scope_series"] == 55
    assert len(
        angola_ngol_report["excluded_non_lubricant_car_care_series"]
    ) == 9
    assert angola_ngol_report["identity_rows"] == len(
        angola_ngol_rows
    ) == report["angola_sonangol_ngol_source_rows"] == report[
        "angola_sonangol_ngol_products_added"
    ] == 107
    assert angola_ngol_report["family_identity_counts"] == {
        "C": 8, "G": 11, "H": 17, "I": 19, "M": 25,
        "S": 4, "T": 19, "TF": 4,
    }
    assert angola_ngol_report["grade_field_counts"] == {
        "dot": 1, "iso_vg": 40, "nlgi": 11, "sae_engine": 23,
        "sae_gear": 16, "source_grade": 16,
    }
    assert angola_ngol_report[
        "official_pdf_direct_download_status"
    ] == "HTTP 403"
    assert angola_ngol_report["official_pdf_sha256"] is None
    assert angola_ngol_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/angola-sonangol-ngol-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["market"] == "Angola"
        and row["brand"] == "NGOL"
        and "official_pdf_direct_download_http_403_at_snapshot"
        in row["specifications"]["source_quality_flags"]
        and not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in angola_ngol_rows
    )
    assert policy_by_id[
        "ANGOLA_SONANGOL_NGOL_OFFICIAL_44_PAGE_CATALOG"
    ]["source_sha256"] == angola_ngol_report["normalized_output_sha256"]
    assert policy_by_id[
        "ANGOLA_SONANGOL_NGOL_OFFICIAL_44_PAGE_CATALOG"
    ]["observed_count"] == 107
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='ANGOLA_SONANGOL_NGOL_OFFICIAL_44_PAGE_CATALOG'"
    ).fetchone()[0] == 107
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='ANGOLA_SONANGOL_NGOL_OFFICIAL_44_PAGE_CATALOG'"
    ).fetchone()[0] == 107
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='ANGOLA_SONANGOL_NGOL_OFFICIAL_44_PAGE_CATALOG'"
    ).fetchone()[0] == 0
    assert madagascar_galana_report["endpoint_rows"] == 45
    assert madagascar_galana_report[
        "duplicate_card_occurrences_collapsed"
    ] == 5
    assert madagascar_galana_report[
        "unique_product_identities"
    ] == len(madagascar_galana_rows) == report[
        "madagascar_galana_mobil_source_rows"
    ] == 40
    assert madagascar_galana_report["family_identity_counts"] == {
        "C": 4, "G": 5, "H": 3, "I": 7, "M": 11, "T": 9, "TF": 1,
    }
    assert madagascar_galana_report[
        "exact_existing_identity_matches"
    ] == report[
        "madagascar_galana_mobil_products_matched_to_existing"
    ] == 24
    assert madagascar_galana_report[
        "new_country_catalog_identities"
    ] == report["madagascar_galana_mobil_products_added"] == 16
    assert madagascar_galana_report["records_with_packages"] == 40
    assert madagascar_galana_report["offers_created"] == 0
    madagascar_card_ids = [
        card["id"]
        for row in madagascar_galana_rows
        for card in row["specifications"]["source_cards"]
    ]
    assert len(madagascar_card_ids) == len(set(madagascar_card_ids)) == 45
    assert madagascar_galana_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/madagascar-galana-mobil-products.jsonl").read_bytes()
    ).hexdigest()
    assert all(
        row["market"] == "Madagascar"
        and row["brand"] == "MOBIL"
        and row["specifications"]["source_cards"]
        and row["specifications"]["source_packages"]
        and not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in madagascar_galana_rows
    )
    assert policy_by_id[
        "MADAGASCAR_GALANA_COMPLETE_MOBIL_PRODUCT_API"
    ]["source_sha256"] == madagascar_galana_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "MADAGASCAR_GALANA_COMPLETE_MOBIL_PRODUCT_API"
    ]["observed_count"] == 40
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='MADAGASCAR_GALANA_COMPLETE_MOBIL_PRODUCT_API'"
    ).fetchone()[0] == 16
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='MADAGASCAR_GALANA_COMPLETE_MOBIL_PRODUCT_API'"
    ).fetchone()[0] == 40
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='MADAGASCAR_GALANA_COMPLETE_MOBIL_PRODUCT_API'"
    ).fetchone()[0] == 0
    assert comoros_sch_report["sitemap_urls"] == 280
    assert comoros_sch_report["sitemap_url_counts"] == {
        "actualite_detail": 23,
        "documentation_detail": 4,
        "point_of_sale_detail": 183,
        "region_detail": 26,
    }
    assert comoros_sch_report["official_product_categories"] == [
        "Kérosène", "Gaz butane", "Jet A1", "Essence & Gasoil",
    ]
    assert comoros_sch_report["relevant_lubricant_product_rows"] == 0
    assert sum(
        document["printed_pages"]
        for document in comoros_sch_report["reviewed_documents"]
    ) == 42
    assert not any(
        comoros_sch_report["reviewed_document_keyword_hits"].values()
    )
    assert comoros_sch_report[
        "historical_shell_partnership_not_promoted_to_current_sku_evidence"
    ] is True
    assert comoros_sch_report["offers_created"] == 0
    assert report["comoros_sch_review_sha256"] == hashlib.sha256(
        (ROOT / "data/comoros-sch-lubricant-scope-review.json").read_bytes()
    ).hexdigest()
    assert policy_by_id[
        "COMOROS_SCH_COMPLETE_PUBLIC_SITE_LUBRICANT_SCOPE_REVIEW"
    ]["source_sha256"] == hashlib.sha256(
        (ROOT / "data/comoros-sch-lubricant-scope-review.json").read_bytes()
    ).hexdigest()
    assert comoros_sch_report["review_facts_sha256"] == (
        "74c9ec9c77c11780825fe1feaa4f30f1375d3c7b7c82718a651642064ab0b333"
    )
    assert policy_by_id[
        "COMOROS_SCH_COMPLETE_PUBLIC_SITE_LUBRICANT_SCOPE_REVIEW"
    ]["observed_count"] == 0
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id="
        "'COMOROS_SCH_COMPLETE_PUBLIC_SITE_LUBRICANT_SCOPE_REVIEW'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT bulk_ingest_allowed FROM sources "
        "WHERE source_id="
        "'COMOROS_SCH_COMPLETE_PUBLIC_SITE_LUBRICANT_SCOPE_REVIEW'"
    ).fetchone()[0] == 1
    assert chevron_us_report[
        "normalized_product_grade_rows"
    ] == len(chevron_us_rows) == 326
    assert chevron_us_report["source_product_pages"] == 162
    assert chevron_us_report["normalized_unique_product_pages"] == 161
    assert chevron_us_report[
        "duplicate_orphan_product_page_occurrences_collapsed"
    ] == 1
    assert chevron_us_report["pages_expanded_to_multiple_grades"] == 69
    assert chevron_us_report["pages_retained_as_ungraded_identity"] == 24
    assert chevron_us_report["families"] == {
        "C": 25, "G": 36, "H": 33, "I": 64, "M": 77,
        "S": 1, "T": 48, "TF": 21, "U": 21,
    }
    assert chevron_us_report["grade_kinds"] == {
        "concentration": 18, "iso_vg": 128, "nlgi": 34,
        "sae_engine": 71, "sae_gear": 24, "source_variant": 27,
        "ungraded": 24,
    }
    assert chevron_us_report["unique_linked_pds_urls"] == 204
    assert chevron_us_report["rows_with_non_pdf_pds_flag"] == 6
    assert report["chevron_us_current_source_rows"] == 326
    assert report[
        "chevron_us_current_products_matched_to_existing"
    ] == 1
    assert report["chevron_us_current_products_added"] == 325
    assert report["chevron_us_current_input_sha256"] == hashlib.sha256(
        (ROOT / "data/chevron-us-current-products.jsonl").read_bytes()
    ).hexdigest()
    assert policy_by_id[
        "CHEVRON_US_COMPLETE_CURRENT_PRODUCT_GRADE_CATALOG"
    ]["source_sha256"] == chevron_us_report["output_sha256"]
    assert policy_by_id[
        "CHEVRON_US_COMPLETE_CURRENT_PRODUCT_GRADE_CATALOG"
    ]["observed_count"] == 326
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='CHEVRON_US_COMPLETE_CURRENT_PRODUCT_GRADE_CATALOG'"
    ).fetchone()[0] == 325
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='CHEVRON_US_COMPLETE_CURRENT_PRODUCT_GRADE_CATALOG'"
    ).fetchone()[0] == 326
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='CHEVRON_US_COMPLETE_CURRENT_PRODUCT_GRADE_CATALOG'"
    ).fetchone()[0] == 0
    assert sum(
        bool(row["source_quality_flags"]) for row in chevron_us_rows
    ) == 6
    assert all(
        row["publication_scope"]
        == "attributed_nonexpressive_factual_fields_only"
        and not ({"description", "artwork", "contact", "sku"} & set(row))
        for row in chevron_us_rows
    )
    assert uruguay_ancap_report["catalog_product_families"] == 56
    assert uruguay_ancap_report["normalized_product_variants"] == len(uruguay_ancap_rows) == 88
    assert uruguay_ancap_report["families"] == {
        "E": 1, "G": 7, "H": 13, "I": 17, "M": 28, "T": 16, "TF": 3, "U": 3
    }
    assert uruguay_ancap_report["catalog_sha256"] == "a48cfd55716f8653ccd3f0bb34dc0d07a43eddf319b902c3a87aa40c151cd2a7"
    assert all(row["brand"] == "ANCAP" and row["market"] == "Uruguay" for row in uruguay_ancap_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in uruguay_ancap_rows)
    assert {
        row["technical"]["marine_grade_source_reported"]
        for row in uruguay_ancap_rows
        if row["technical"]["marine_grade_source_reported"]
    } == {"3012", "3015", "4015", "4020"}
    assert {
        row["technical"]["viscosity_source_reported"]
        for row in uruguay_ancap_rows
        if row["technical"]["viscosity_source_reported"]
    } == {"C460"}
    assert policy_by_id["URUGUAY_ANCAP_CURRENT_LUBRICANT_CATALOG"]["source_sha256"] == uruguay_ancap_report["normalized_output_sha256"]
    assert policy_by_id["URUGUAY_ANCAP_CURRENT_LUBRICANT_CATALOG"]["observed_count"] == 88
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='URUGUAY_ANCAP_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 88
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='URUGUAY_ANCAP_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 88
    assert colombia_terpel_report["product_cards_with_documents_observed"] == 30
    assert colombia_terpel_report["duplicate_audience_cards_collapsed"] == 3
    assert colombia_terpel_report["normalized_products"] == len(colombia_terpel_rows) == 27
    assert colombia_terpel_report["families"] == {"M": 18, "T": 4, "TF": 5}
    assert colombia_terpel_report["unique_source_documents"] == 53
    assert colombia_terpel_report["technical_sheet_links"] == 26
    assert colombia_terpel_report["safety_sheet_links"] == 27
    assert all(row["brand"] == "Terpel" and row["market"] == "Colombia" for row in colombia_terpel_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in colombia_terpel_rows)
    assert all(all(document["sha256"] for document in row["documents"]) for row in colombia_terpel_rows)
    assert policy_by_id["COLOMBIA_TERPEL_CURRENT_LUBRICANT_CATALOG"]["source_sha256"] == colombia_terpel_report["normalized_output_sha256"]
    assert policy_by_id["COLOMBIA_TERPEL_CURRENT_LUBRICANT_CATALOG"]["observed_count"] == 27
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='COLOMBIA_TERPEL_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 27
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='COLOMBIA_TERPEL_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 27
    assert guyana_guyoil_report["source_page_id"] == 1817
    assert guyana_guyoil_report["normalized_products"] == len(guyana_guyoil_rows) == 11
    assert guyana_guyoil_report["families"] == {"M": 7, "T": 4}
    assert guyana_guyoil_report["rows_with_sae"] == 5
    assert guyana_guyoil_report["rows_with_source_packages"] == 4
    assert guyana_guyoil_report["series_without_published_grades_report_only"] == [
        "Castrol Edge", "Castrol Magnatec", "Castrol GTX", "Castrol Actevo"
    ]
    assert all(row["brand"] == "Castrol" and row["market"] == "Guyana" for row in guyana_guyoil_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in guyana_guyoil_rows)
    assert policy_by_id["GUYANA_GUYOIL_CURRENT_CASTROL_LUBRICANT_CATALOG"]["source_sha256"] == guyana_guyoil_report["normalized_output_sha256"]
    assert policy_by_id["GUYANA_GUYOIL_CURRENT_CASTROL_LUBRICANT_CATALOG"]["observed_count"] == 11
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='GUYANA_GUYOIL_CURRENT_CASTROL_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 11
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='GUYANA_GUYOIL_CURRENT_CASTROL_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 11
    assert suriname_powerfull_report["normalized_products"] == len(suriname_powerfull_rows) == 9
    assert suriname_powerfull_report["families"] == {"G": 1, "H": 1, "M": 5, "T": 2}
    assert suriname_powerfull_report["rows_with_sae"] == 7
    assert suriname_powerfull_report["rows_with_api_or_api_gl"] == 7
    assert suriname_powerfull_report["rows_with_iso_vg"] == 1
    assert suriname_powerfull_report["grease_source_grade_without_published_nlgi"] == 1
    assert all(row["brand"] == "POWERFULL" and row["market"] == "Suriname" for row in suriname_powerfull_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in suriname_powerfull_rows)
    assert all(row["source_page_text_sha256"] for row in suriname_powerfull_rows)
    assert policy_by_id["SURINAME_POWERFULL_CURRENT_LUBRICANT_CATALOG"]["source_sha256"] == suriname_powerfull_report["normalized_output_sha256"]
    assert policy_by_id["SURINAME_POWERFULL_CURRENT_LUBRICANT_CATALOG"]["observed_count"] == 9
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='SURINAME_POWERFULL_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 9
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='SURINAME_POWERFULL_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 9
    assert trinidad_tobago_np_ultra_report["current_product_pages_audited"] == 63
    assert trinidad_tobago_np_ultra_report["normalized_series"] == 59
    assert trinidad_tobago_np_ultra_report["normalized_product_grade_identities"] == len(trinidad_tobago_np_ultra_rows) == 141
    assert trinidad_tobago_np_ultra_report["linked_document_urls_fetched"] == 79
    assert trinidad_tobago_np_ultra_report["unique_document_payloads"] == 76
    assert trinidad_tobago_np_ultra_report["families"] == {
        "C": 9, "G": 8, "H": 12, "I": 51, "M": 32,
        "S": 7, "T": 2, "TF": 11, "U": 9,
    }
    assert all(row["brand"] == "ULTRA" and row["market"] == "Trinidad and Tobago" for row in trinidad_tobago_np_ultra_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in trinidad_tobago_np_ultra_rows)
    assert all(row["source_page_text_sha256"] for row in trinidad_tobago_np_ultra_rows)
    assert policy_by_id["TRINIDAD_TOBAGO_NP_ULTRA_CURRENT_LUBRICANT_CATALOG"]["source_sha256"] == trinidad_tobago_np_ultra_report["normalized_output_sha256"]
    assert policy_by_id["TRINIDAD_TOBAGO_NP_ULTRA_CURRENT_LUBRICANT_CATALOG"]["observed_count"] == 141
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='TRINIDAD_TOBAGO_NP_ULTRA_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 141
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='TRINIDAD_TOBAGO_NP_ULTRA_CURRENT_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 141
    assert venezuela_pdv_report["normalized_products"] == len(venezuela_pdv_rows) == 23
    assert venezuela_pdv_report["cpe_package_rows"] == 39
    assert venezuela_pdv_report["unique_cpe_codes"] == 39
    assert venezuela_pdv_report["technical_pdfs_audited"] == 21
    assert venezuela_pdv_report["families"] == {"H": 2, "M": 17, "T": 2, "TF": 2}
    assert venezuela_pdv_report["rows_with_sae"] == 16
    assert venezuela_pdv_report["rows_with_api_or_api_gl"] == 18
    assert venezuela_pdv_report["rows_with_iso_vg"] == 2
    assert sum(len(row["packages"]) for row in venezuela_pdv_rows) == 39
    assert len({package["cpe"] for row in venezuela_pdv_rows for package in row["packages"]}) == 39
    assert all(row["brand"] == "PDV" and row["market"] == "Venezuela" for row in venezuela_pdv_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in venezuela_pdv_rows)
    assert policy_by_id["VENEZUELA_PDV_CURRENT_CPE_LUBRICANT_CATALOG"]["source_sha256"] == venezuela_pdv_report["normalized_output_sha256"]

    assert jamaica_futroil_tek_report["official_pages_audited"] == 2
    assert jamaica_futroil_tek_report["official_product_card_images_audited"] == 20
    assert jamaica_futroil_tek_report["futroil_normalized_product_grades"] == 8
    assert jamaica_futroil_tek_report["tek_normalized_product_grades"] == 21
    assert jamaica_futroil_tek_report["normalized_product_grade_identities"] == len(jamaica_futroil_tek_rows) == 29
    assert jamaica_futroil_tek_report["families"] == {
        "C": 2, "G": 2, "H": 4, "M": 11, "S": 1, "T": 4, "TF": 4, "U": 1,
    }
    assert jamaica_futroil_tek_report["rows_with_sae"] == 14
    assert jamaica_futroil_tek_report["rows_with_api_or_api_gl"] == 6
    assert jamaica_futroil_tek_report["rows_with_iso_vg"] == 6
    assert sum(row["brand"] == "FUTROIL" for row in jamaica_futroil_tek_rows) == 8
    assert sum(row["brand"] == "TEK" for row in jamaica_futroil_tek_rows) == 21
    assert all(row["market"] == "Jamaica" for row in jamaica_futroil_tek_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in jamaica_futroil_tek_rows)
    assert all(row["source_image_sha256"] for row in jamaica_futroil_tek_rows)
    assert policy_by_id["JAMAICA_FESCO_FUTROIL_CURRENT_LUBRICANT_CATALOG"]["source_sha256"] == jamaica_futroil_tek_report["normalized_output_sha256"]
    assert policy_by_id["JAMAICA_LUBIT_TEK_CURRENT_LUBRICANT_CATALOG"]["source_sha256"] == jamaica_futroil_tek_report["normalized_output_sha256"]

    assert cuba_cubalub_2007_report["records"] == len(cuba_cubalub_2007_rows) == 105
    assert cuba_cubalub_2007_report["pdf_pages"] == 17
    assert cuba_cubalub_2007_report["resolution_number"] == "122"
    assert cuba_cubalub_2007_report["families"] == {
        "C": 8, "G": 8, "H": 5, "M": 29, "S": 6, "T": 13, "TF": 1, "U": 35,
    }
    assert cuba_cubalub_2007_report["rows_with_api"] == 4
    assert cuba_cubalub_2007_report["rows_with_api_gl"] == 4
    assert len(cuba_cubalub_2007_report["explicitly_excluded_non_lubricants"]) == 4
    assert all(row["brand"] == "CUBALUB" and row["market"] == "CUBA" for row in cuba_cubalub_2007_rows)
    assert all(row["lifecycle_status"] == "historical_official_price_catalog_current_status_unverified" for row in cuba_cubalub_2007_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in cuba_cubalub_2007_rows)
    assert not any(
        row["technical"]["sae_engine"] or row["technical"]["sae_gear"]
        or row["technical"]["iso_vg"] or row["technical"]["nlgi"]
        for row in cuba_cubalub_2007_rows
    )
    assert policy_by_id["CUBA_CUBALUB_2007_OFFICIAL_PRICE_CATALOG"]["source_sha256"] == hashlib.sha256(
        (ROOT / "data/cuba-cubalub-2007-official-products.jsonl").read_bytes()
    ).hexdigest()
    assert policy_by_id["CUBA_CUBALUB_2007_OFFICIAL_PRICE_CATALOG"]["observed_count"] == 105
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='CUBA_CUBALUB_2007_OFFICIAL_PRICE_CATALOG'"
    ).fetchone()[0] == 105

    assert panama_acodeco_2020_report["named_product_grade_rows"] == len(panama_acodeco_2020_rows) == 45
    assert panama_acodeco_2020_report["pdf_pages"] == 2
    assert panama_acodeco_2020_report["brands"] == 19
    assert panama_acodeco_2020_report["retail_price_observations"] == 83
    assert panama_acodeco_2020_report["sae_distribution"] == {
        "10W-30": 19, "15W-40": 12, "20W-50": 12, "40": 1, "50": 1,
    }
    assert len(panama_acodeco_2020_report["generic_rows_report_only"]) == 9
    assert all(row["family_code"] == "M" and row["market"] == "Panama" for row in panama_acodeco_2020_rows)
    assert all(row["lifecycle_status"] == "historical_retail_price_observation_current_status_unverified" for row in panama_acodeco_2020_rows)
    assert all(row["technical"]["sae_engine"] for row in panama_acodeco_2020_rows)
    assert sum(len(row["observed_prices"]) for row in panama_acodeco_2020_rows) == 83
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in panama_acodeco_2020_rows)
    assert policy_by_id["PANAMA_ACODECO_2020_LUBRICANT_PRICE_SURVEY"]["source_sha256"] == hashlib.sha256(
        (ROOT / "data/panama-acodeco-2020-lubricant-price-survey.jsonl").read_bytes()
    ).hexdigest()
    assert policy_by_id["PANAMA_ACODECO_2020_LUBRICANT_PRICE_SURVEY"]["observed_count"] == 45
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='PANAMA_ACODECO_2020_LUBRICANT_PRICE_SURVEY'"
    ).fetchone()[0] == 45
    assert nicaragua_lubrinsa_report["current_seller_cards"] == len(nicaragua_lubrinsa_availability_rows) == 55
    assert nicaragua_lubrinsa_report["current_repsol_seller_cards"] == 42
    assert nicaragua_lubrinsa_report["current_auto_seller_cards"] == 13
    assert nicaragua_lubrinsa_report["scope_status_counts"] == {
        "canonical_local_product": 4,
        "global_product_nicaragua_availability": 41,
        "report_only_excluded": 10,
    }
    assert nicaragua_lubrinsa_report["current_in_scope_availability_occurrences"] == 45
    assert nicaragua_lubrinsa_report["current_in_scope_identity_hints_after_package_grouping"] == 38
    assert nicaragua_lubrinsa_report["repsol_identity_hints_after_package_grouping"] == 34
    assert nicaragua_lubrinsa_report["canonical_local_product_rows"] == len(nicaragua_lubrinsa_rows) == 4
    assert nicaragua_lubrinsa_report["image_payloads_audited"] == 55
    assert all(row["brand"] == "AUTO" and row["family_code"] == "TF" for row in nicaragua_lubrinsa_rows)
    assert all(row["market"] == "Nicaragua" for row in nicaragua_lubrinsa_rows)
    assert all(row["source_image_sha256"] for row in nicaragua_lubrinsa_rows)
    assert all(not ({"address", "phone", "email", "contact_person"} & set(row)) for row in nicaragua_lubrinsa_rows)
    assert policy_by_id["NICARAGUA_LUBRINSA_CURRENT_CATALOG"]["source_sha256"] == hashlib.sha256(
        (ROOT / "data/nicaragua-lubrinsa-current-local-fluids.jsonl").read_bytes()
    ).hexdigest()
    assert policy_by_id["NICARAGUA_LUBRINSA_CURRENT_CATALOG"]["observed_count"] == 4
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='NICARAGUA_LUBRINSA_CURRENT_CATALOG'"
    ).fetchone()[0] == 4
    assert honduras_hondulub_report["source_printed_product_rows"] == 110
    assert honduras_hondulub_report[
        "normalized_identity_hints_after_expansion_and_package_grouping"
    ] == len(honduras_hondulub_availability_rows) == 120
    assert honduras_hondulub_report["in_scope_product_grade_occurrences"] == 115
    assert honduras_hondulub_report["canonical_oil_star_product_rows"] == len(
        honduras_hondulub_rows
    ) == 31
    assert honduras_hondulub_report[
        "global_brand_honduras_availability_occurrences"
    ] == 84
    assert honduras_hondulub_report["report_only_generic_series"] == 4
    assert honduras_hondulub_report["excluded_non_product_equipment"] == 1
    assert honduras_hondulub_report["scope_status_counts"] == {
        "canonical_oil_star_product": 31,
        "excluded_non_product_equipment": 1,
        "global_product_honduras_availability": 84,
        "report_only_generic_series": 4,
    }
    assert honduras_hondulub_report["brands"] == {
        "OIL STAR": 31,
        "Phillips 66": 23,
        "Pyroil": 4,
        "Shell": 3,
        "TEK STAR": 58,
        "Ultrachem": 1,
    }
    assert honduras_hondulub_report["canonical_oil_star_families"] == {
        "G": 1, "H": 6, "I": 8, "M": 9, "T": 2, "TF": 5,
    }
    assert len(honduras_hondulub_report["source_image_facts"]) == 11
    assert all(
        row["brand"] == "OIL STAR" and row["market"] == "Honduras"
        for row in honduras_hondulub_rows
    )
    assert all(row["source_image_sha256"] for row in honduras_hondulub_rows)
    assert all(
        not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in honduras_hondulub_rows
    )
    assert policy_by_id[
        "HONDURAS_HONDULUB_CURRENT_PRODUCT_TABLES"
    ]["source_sha256"] == hashlib.sha256(
        (ROOT / "data/honduras-hondulub-current-oil-star-products.jsonl").read_bytes()
    ).hexdigest()
    assert policy_by_id[
        "HONDURAS_HONDULUB_CURRENT_PRODUCT_TABLES"
    ]["observed_count"] == 31
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='HONDURAS_HONDULUB_CURRENT_PRODUCT_TABLES'"
    ).fetchone()[0] == 31
    assert el_salvador_mecha_tool_report["current_product_cards"] == 26
    assert el_salvador_mecha_tool_report["current_card_categories"] == {
        "Automotriz": 12,
        "Industrial": 12,
        "Valgab": 2,
    }
    assert el_salvador_mecha_tool_report[
        "expanded_page_grade_occurrences"
    ] == 67
    assert el_salvador_mecha_tool_report[
        "duplicate_forza_language_page_grade_occurrences_collapsed"
    ] == 8
    assert el_salvador_mecha_tool_report[
        "normalized_product_identities"
    ] == len(el_salvador_mecha_tool_rows) == 59
    assert el_salvador_mecha_tool_report[
        "existing_gm_dexos_identity_match_candidates"
    ] == report["el_salvador_mecha_tool_products_matched_to_existing"] == 2
    assert el_salvador_mecha_tool_report[
        "new_manufacturer_catalog_identity_candidates"
    ] == report["el_salvador_mecha_tool_products_added"] == 57
    assert report["el_salvador_mecha_tool_source_rows"] == 59
    assert el_salvador_mecha_tool_report["product_images_audited"] == 26
    assert el_salvador_mecha_tool_report[
        "linked_pdf_references_audited"
    ] == 37
    assert el_salvador_mecha_tool_report[
        "unique_linked_pdf_payloads"
    ] == 33
    assert el_salvador_mecha_tool_report["brands"] == {
        "MECHA-TOOL": 56,
        "VALGAB": 3,
    }
    assert el_salvador_mecha_tool_report["families"] == {
        "H": 13,
        "I": 5,
        "M": 21,
        "S": 2,
        "TF": 6,
        "U": 12,
    }
    assert all(
        row["market"] == "El Salvador"
        and row["source_images"]
        and row["source_page_urls"]
        for row in el_salvador_mecha_tool_rows
    )
    assert all(
        not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in el_salvador_mecha_tool_rows
    )
    assert policy_by_id[
        "EL_SALVADOR_MECHA_TOOL_CURRENT_CATALOG"
    ]["source_sha256"] == hashlib.sha256(
        (ROOT / "data/el-salvador-mecha-tool-current-products.jsonl").read_bytes()
    ).hexdigest()
    assert policy_by_id[
        "EL_SALVADOR_MECHA_TOOL_CURRENT_CATALOG"
    ]["observed_count"] == 59
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='EL_SALVADOR_MECHA_TOOL_CURRENT_CATALOG'"
    ).fetchone()[0] == 57
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='EL_SALVADOR_MECHA_TOOL_CURRENT_CATALOG'"
    ).fetchone()[0] == 59
    assert db.execute(
        "SELECT count(*) FROM product_sources ps "
        "JOIN products p USING(product_id) "
        "WHERE ps.source_id='EL_SALVADOR_MECHA_TOOL_CURRENT_CATALOG' "
        "AND p.source_id='GM_DEXOS1_GEN3'"
    ).fetchone()[0] == 2
    assert belize_ilb_report["current_product_cards"] == 112
    assert belize_ilb_report[
        "normalized_product_label_identities"
    ] == len(belize_ilb_rows) == report[
        "belize_ilb_availability_source_rows"
    ] == 77
    assert belize_ilb_report[
        "package_only_card_duplicates_collapsed"
    ] == 35
    assert belize_ilb_report["product_images_referenced"] == 112
    assert belize_ilb_report["unique_product_image_payloads"] == 112
    assert belize_ilb_report["product_image_bytes"] == 7728126
    assert belize_ilb_report["brands"] == {"CHEVRON": 76, "REVOLUB": 1}
    assert belize_ilb_report["families"] == {
        "C": 2, "G": 10, "H": 6, "I": 15, "M": 19,
        "T": 14, "TF": 11,
    }
    assert all(
        row["market"] == "Belize"
        and row["source_card_ids"]
        and row["source_card_urls"]
        and row["source_image_sha256"]
        for row in belize_ilb_rows
    )
    assert all(
        not ({"address", "phone", "email", "contact_person"} & set(row))
        for row in belize_ilb_rows
    )
    assert belize_ilb_report["normalized_output_sha256"] == hashlib.sha256(
        (ROOT / "data/belize-ilb-current-availability.jsonl").read_bytes()
    ).hexdigest()
    assert report["belize_ilb_availability_input_sha256"] == (
        belize_ilb_report["normalized_output_sha256"]
    )
    assert policy_by_id[
        "BELIZE_ILB_CURRENT_PRODUCT_CATALOG"
    ]["source_sha256"] == belize_ilb_report["normalized_output_sha256"]
    assert policy_by_id[
        "BELIZE_ILB_CURRENT_PRODUCT_CATALOG"
    ]["observed_count"] == 77
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='BELIZE_ILB_CURRENT_PRODUCT_CATALOG'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='BELIZE_ILB_CURRENT_PRODUCT_CATALOG'"
    ).fetchone()[0] == 0
    assert belize_rymax_catalog_report["listing_pages"] == 22
    assert belize_rymax_catalog_report["listing_occurrences"] == 339
    assert belize_rymax_catalog_report["unique_product_urls"] == 325
    assert belize_rymax_catalog_report["highlight_repeat_occurrences"] == 14
    assert belize_rymax_catalog_report["cards_with_specifications"] == 266
    assert belize_rymax_catalog_report["cards_with_segments"] == 304
    assert belize_rymax_catalog_report["cards_with_viscosity_grades"] == 228
    assert belize_rymax_catalog_report["cards_with_images"] == 325
    assert belize_rymax_catalog_report["unique_document_urls"] == 588
    assert belize_rymax_assets_report["asset_urls_audited"] == 823
    assert belize_rymax_assets_report["image_urls_audited"] == 235
    assert belize_rymax_assets_report["document_urls_audited"] == 588
    assert belize_rymax_assets_report["image_bytes"] == 10663692
    assert belize_rymax_assets_report["document_bytes"] == 294091818
    assert belize_rymax_assets_report["unique_document_payloads"] == 587
    assert belize_rymax_products_report[
        "normalized_product_identities"
    ] == len(belize_rymax_rows) == report[
        "belize_rymax_source_rows"
    ] == 313
    assert belize_rymax_products_report[
        "duplicate_url_occurrences_collapsed"
    ] == 12
    assert belize_rymax_products_report["families"] == {
        "C": 10, "G": 33, "H": 38, "I": 23, "M": 108,
        "S": 28, "T": 39, "TF": 31, "U": 3,
    }
    assert all(
        row["brand"] == "RYMAX"
        and row["market"] == "Belize"
        and row["source_card_urls"]
        and row["source_image_sha256"]
        for row in belize_rymax_rows
    )
    assert {
        tuple(row["technical"]["api"])
        for row in belize_rymax_rows
        if row["product_name"] == "Motrax 2T"
    } == {("TA",), ("TB",), ("TC",)}
    assert belize_rymax_products_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/belize-rymax-current-products.jsonl").read_bytes()
    ).hexdigest()
    assert report["belize_rymax_products_input_sha256"] == (
        belize_rymax_products_report["normalized_output_sha256"]
    )
    assert policy_by_id[
        "BELIZE_RYMAX_CURRENT_PRODUCT_CATALOG"
    ]["source_sha256"] == belize_rymax_products_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "BELIZE_RYMAX_CURRENT_PRODUCT_CATALOG"
    ]["observed_count"] == 313
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='BELIZE_RYMAX_CURRENT_PRODUCT_CATALOG'"
    ).fetchone()[0] == 313
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='BELIZE_RYMAX_CURRENT_PRODUCT_CATALOG'"
    ).fetchone()[0] == 313
    assert bahamas_cbs_report["in_scope_unique_availability_cards"] == len(
        bahamas_cbs_rows
    ) == report["bahamas_cbs_availability_source_rows"] == 51
    assert bahamas_cbs_report["official_category_reported_counts"] == {
        "Grease & Lubricants": 17,
        "Motor Oils": 16,
        "Other Fluids, Treatments, & Chemicals": 23,
    }
    assert bahamas_cbs_report["in_scope_by_category"] == {
        "Auto Solvents & Cleaners": 1,
        "Electrical Grease & Lubricants": 1,
        "Grease & Lubricants": 17,
        "Motor Oils": 16,
        "Other Fluids, Treatments, & Chemicals": 16,
    }
    assert bahamas_cbs_report["families"] == {
        "C": 3, "G": 6, "H": 3, "M": 15,
        "S": 12, "TF": 3, "U": 9,
    }
    assert bahamas_cbs_report["normalized_output_sha256"] == hashlib.sha256(
        (ROOT / "data/bahamas-cbs-current-availability.jsonl").read_bytes()
    ).hexdigest()
    assert report["bahamas_cbs_availability_input_sha256"] == (
        bahamas_cbs_report["normalized_output_sha256"]
    )
    assert policy_by_id[
        "BAHAMAS_CBS_CURRENT_AVAILABILITY"
    ]["source_sha256"] == bahamas_cbs_report["normalized_output_sha256"]
    assert policy_by_id[
        "BAHAMAS_CBS_CURRENT_AVAILABILITY"
    ]["observed_count"] == 51
    assert all(
        row["market"] == "Bahamas"
        and row["item_sku"]
        and row["manufacturer_ref"]
        and row["source_card_url"]
        and "no_access_control_bypass" in row["source_quality_flags"]
        for row in bahamas_cbs_rows
    )
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='BAHAMAS_CBS_CURRENT_AVAILABILITY'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='BAHAMAS_CBS_CURRENT_AVAILABILITY'"
    ).fetchone()[0] == 0
    assert barbados_sol_report[
        "normalized_product_identities"
    ] == len(barbados_sol_rows) == report[
        "barbados_sol_availability_source_rows"
    ] == 33
    assert barbados_sol_report["listing_card_occurrences"] == 36
    assert barbados_sol_report["package_only_occurrences_collapsed"] == 3
    assert barbados_sol_report[
        "identities_with_conflicting_status_observations"
    ] == 4
    assert barbados_sol_report["families"] == {
        "C": 2, "G": 2, "H": 3, "I": 5, "M": 14,
        "T": 6, "U": 1,
    }
    assert barbados_sol_report["normalized_output_sha256"] == hashlib.sha256(
        (ROOT / "data/barbados-sol-recent-availability.jsonl").read_bytes()
    ).hexdigest()
    assert report["barbados_sol_availability_input_sha256"] == (
        barbados_sol_report["normalized_output_sha256"]
    )
    assert policy_by_id[
        "BARBADOS_SOL_RECENT_ECOMMERCE_CATALOG"
    ]["source_sha256"] == barbados_sol_report["normalized_output_sha256"]
    assert policy_by_id[
        "BARBADOS_SOL_RECENT_ECOMMERCE_CATALOG"
    ]["observed_count"] == 33
    assert all(
        row["brand"] == "MOBIL"
        and row["market"] == "Barbados"
        and row["listing_cards"]
        and row["technical"]
        for row in barbados_sol_rows
    )
    assert sum(
        len(row["listing_cards"]) for row in barbados_sol_rows
    ) == 36
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='BARBADOS_SOL_RECENT_ECOMMERCE_CATALOG'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='BARBADOS_SOL_RECENT_ECOMMERCE_CATALOG'"
    ).fetchone()[0] == 0
    assert shell_global_distributors_report[
        "country_section_rows"
    ] == len(shell_global_distributor_rows) == report[
        "shell_global_distributors_source_rows"
    ] == 118
    assert shell_global_distributors_report["unique_market_labels"] == 117
    assert shell_global_distributors_report[
        "duplicate_market_section_counts"
    ] == {"Cook Islands": 2}
    assert shell_global_distributors_report[
        "sections_with_distributor_details"
    ] == 117
    assert shell_global_distributors_report[
        "sections_without_distributor_details"
    ] == ["Tajikistan"]
    assert shell_global_distributors_report[
        "official_page_last_modified"
    ] == "2026-07-21T18:30Z"
    assert shell_global_distributors_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/shell-global-current-distributors.jsonl").read_bytes()
    ).hexdigest()
    assert report["shell_global_distributors_input_sha256"] == (
        shell_global_distributors_report["normalized_output_sha256"]
    )
    assert policy_by_id[
        "SHELL_GLOBAL_CURRENT_APPROVED_DISTRIBUTOR_LOCATOR"
    ]["source_sha256"] == shell_global_distributors_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "SHELL_GLOBAL_CURRENT_APPROVED_DISTRIBUTOR_LOCATOR"
    ]["observed_count"] == 118
    assert len({
        row["source_record_id"] for row in shell_global_distributor_rows
    }) == 118
    assert sum(
        len(row["distributor_names"])
        for row in shell_global_distributor_rows
    ) == 167
    assert all(
        row["product_scope_status"]
        == "no_country_sku_or_stock_inference_permitted"
        for row in shell_global_distributor_rows
    )
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='SHELL_GLOBAL_CURRENT_APPROVED_DISTRIBUTOR_LOCATOR'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='SHELL_GLOBAL_CURRENT_APPROVED_DISTRIBUTOR_LOCATOR'"
    ).fetchone()[0] == 0
    assert castrol_global_distributors_report[
        "distributor_rows"
    ] == len(castrol_global_distributor_rows) == report[
        "castrol_global_distributors_source_rows"
    ] == 368
    assert castrol_global_distributors_report["market_tables"] == 106
    assert castrol_global_distributors_report["unique_market_labels"] == 106
    assert castrol_global_distributors_report[
        "unique_distributor_names_casefolded"
    ] == 345
    assert castrol_global_distributors_report[
        "markets_with_multiple_distributor_rows"
    ] == 35
    assert castrol_global_distributors_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/castrol-global-current-distributors.jsonl").read_bytes()
    ).hexdigest()
    assert report["castrol_global_distributors_input_sha256"] == (
        castrol_global_distributors_report["normalized_output_sha256"]
    )
    assert policy_by_id[
        "CASTROL_GLOBAL_CURRENT_AUTHORISED_DISTRIBUTORS"
    ]["source_sha256"] == castrol_global_distributors_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "CASTROL_GLOBAL_CURRENT_AUTHORISED_DISTRIBUTORS"
    ]["observed_count"] == 368
    assert len({
        (
            row["market_label_as_published"],
            row["source_table_row"],
        )
        for row in castrol_global_distributor_rows
    }) == 368
    assert all(
        row["distributor_name"]
        and row["product_scope_status"]
        == "no_country_sku_or_stock_inference_permitted"
        for row in castrol_global_distributor_rows
    )
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='CASTROL_GLOBAL_CURRENT_AUTHORISED_DISTRIBUTORS'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='CASTROL_GLOBAL_CURRENT_AUTHORISED_DISTRIBUTORS'"
    ).fetchone()[0] == 0
    assert dominican_imca_mobil_report[
        "product_grade_rows"
    ] == len(dominican_imca_mobil_rows) == report[
        "dominican_imca_mobil_source_rows"
    ] == 51
    assert dominican_imca_mobil_report["source_pdf_pages"] == 32
    assert dominican_imca_mobil_report[
        "source_pages_with_products"
    ] == 29
    assert dominican_imca_mobil_report["source_pdf_creation_date"] == (
        "2025-12-09"
    )
    assert dominican_imca_mobil_report["source_pdf_sha256"] == (
        "9e7c730837583042997e2a9c32ba9f4424bc53a025e2d8bc4bf6f4535aad50ab"
    )
    assert dominican_imca_mobil_report["families"] == {
        "M": 41, "T": 7, "TF": 3,
    }
    assert dominican_imca_mobil_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (
            ROOT / "data/dominican-republic-imca-mobil-2025-products.jsonl"
        ).read_bytes()
    ).hexdigest()
    assert report["dominican_imca_mobil_input_sha256"] == (
        dominican_imca_mobil_report["normalized_output_sha256"]
    )
    assert report[
        "dominican_imca_mobil_products_matched_to_existing"
    ] == 28
    assert report["dominican_imca_mobil_products_added"] == 23
    assert report["dominican_imca_mobil_explicit_alias_matches"] == 5
    assert report["dominican_imca_mobil_multi_candidate_rows"] == 15
    assert policy_by_id[
        "DOMINICAN_REPUBLIC_IMCA_MOBIL_2025_CATALOG"
    ]["source_sha256"] == dominican_imca_mobil_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "DOMINICAN_REPUBLIC_IMCA_MOBIL_2025_CATALOG"
    ]["observed_count"] == 51
    assert all(
        row["brand"] == "MOBIL"
        and row["market"] == "Dominican Republic"
        and row["source_page"] in range(3, 32)
        and row["family_code"] in {"M", "T", "TF"}
        for row in dominican_imca_mobil_rows
    )
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='DOMINICAN_REPUBLIC_IMCA_MOBIL_2025_CATALOG'"
    ).fetchone()[0] == report["dominican_imca_mobil_products_added"]
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='DOMINICAN_REPUBLIC_IMCA_MOBIL_2025_CATALOG'"
    ).fetchone()[0] == 51
    assert dominican_imca_mobil_web_report[
        "sitemap_product_pages"
    ] == len(dominican_imca_mobil_web_rows) == report[
        "dominican_imca_mobil_web_source_rows"
    ] == 95
    assert dominican_imca_mobil_web_report["http_200_pages"] == 95
    assert dominican_imca_mobil_web_report[
        "unique_factual_projection_hashes"
    ] == 95
    assert dominican_imca_mobil_web_report[
        "unique_product_page_titles"
    ] == 95
    assert dominican_imca_mobil_web_report[
        "sitemap_last_modified_date_counts"
    ] == {"2021-04-27": 92, "2021-09-14": 1, "2026-04-01": 2}
    assert dominican_imca_mobil_web_report["category_counts"] == {
        "Automotriz": 27,
        "Flotillas": 15,
        "Grasas": 8,
        "Industrial": 35,
        "Maquinaria Pesada": 9,
        "Marítimo / Aviación": 7,
    }
    assert dominican_imca_mobil_web_report["product_type_counts"] == {
        "Mineral": 55,
        "Refrigerante": 2,
        "Semi-Sintético": 6,
        "Sintético": 31,
    }
    assert dominican_imca_mobil_web_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (
            ROOT / "data/dominican-republic-imca-mobil-web-pages.jsonl"
        ).read_bytes()
    ).hexdigest()
    assert report["dominican_imca_mobil_web_input_sha256"] == (
        dominican_imca_mobil_web_report["normalized_output_sha256"]
    )
    assert policy_by_id[
        "DOMINICAN_REPUBLIC_IMCA_MOBIL_LIVE_WEB_CATALOG"
    ]["source_sha256"] == dominican_imca_mobil_web_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "DOMINICAN_REPUBLIC_IMCA_MOBIL_LIVE_WEB_CATALOG"
    ]["observed_count"] == 95
    assert all(
        row["brand"] == "MOBIL"
        and row["http_status"] == 200
        and row["source_url"].startswith(
            "https://lubricantesmobil.imcadom.com/productos/"
        )
        and row["product_page_title"]
        and row["factual_projection_sha256"]
        and row["normalized_product_section_sha256"]
        for row in dominican_imca_mobil_web_rows
    )
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='DOMINICAN_REPUBLIC_IMCA_MOBIL_LIVE_WEB_CATALOG'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='DOMINICAN_REPUBLIC_IMCA_MOBIL_LIVE_WEB_CATALOG'"
    ).fetchone()[0] == 0
    assert mag1_current_report["leaf_product_pages"] == 114
    assert mag1_current_report[
        "included_products"
    ] == len(mag1_current_rows) == report[
        "mag1_current_official_source_rows"
    ] == 106
    assert mag1_current_report[
        "excluded_pages"
    ] == len(mag1_current_exclusions) == 8
    assert mag1_current_report["unique_pds_urls"] == 114
    assert mag1_current_report["unique_product_titles"] == 106
    assert mag1_current_report["families"] == {
        "G": 1, "H": 6, "I": 17, "M": 42, "S": 9,
        "T": 26, "TF": 2, "U": 3,
    }
    assert mag1_current_report[
        "pages_with_industry_oem_specifications"
    ] == 79
    assert mag1_current_report["pages_with_typical_properties"] == 91
    assert mag1_current_report[
        "pages_with_container_bulk_availability"
    ] == 106
    assert mag1_current_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/mag1-current-official-products.jsonl").read_bytes()
    ).hexdigest()
    assert mag1_current_report[
        "normalized_exclusions_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/mag1-current-official-exclusions.jsonl").read_bytes()
    ).hexdigest()
    assert report["mag1_current_official_input_sha256"] == (
        mag1_current_report["normalized_output_sha256"]
    )
    assert report["mag1_current_products_matched_to_existing"] == 3
    assert report["mag1_current_products_added"] == 103
    assert policy_by_id[
        "MAG1_CURRENT_OFFICIAL_PRODUCT_CATALOG"
    ]["source_sha256"] == mag1_current_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "MAG1_CURRENT_OFFICIAL_PRODUCT_CATALOG"
    ]["observed_count"] == 106
    assert all(
        row["brand"] == "MAG 1"
        and row["family_code"] in {"G", "H", "I", "M", "S", "T", "TF", "U"}
        and row["http_status"] == 200
        and row["pds_http_status"] == 200
        and row["source_url"].startswith("https://mag1.com/products/")
        and row["pds_url"].startswith("https://mag1.com/products/")
        and row["technical"]
        for row in mag1_current_rows
    )
    assert all(
        row["scope_status"]
        == "out_of_scope_cleaner_dressing_or_equipment_product"
        and "family_code" not in row
        for row in mag1_current_exclusions
    )
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='MAG1_CURRENT_OFFICIAL_PRODUCT_CATALOG'"
    ).fetchone()[0] == 103
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='MAG1_CURRENT_OFFICIAL_PRODUCT_CATALOG'"
    ).fetchone()[0] == 106
    for grade in ("SAE 10", "SAE 30", "SAE 50"):
        product_id = db.execute(
            "SELECT product_id FROM products "
            "WHERE source_id='MAG1_CURRENT_OFFICIAL_PRODUCT_CATALOG' "
            "AND family_code='T' AND product_name_raw=?",
            (f"MAG 1® TO-4 Torque Fluid {grade}",),
        ).fetchone()[0]
        assert db.execute(
            "SELECT spec_value FROM specifications "
            "WHERE product_id=? AND spec_type='sae_gear'",
            (product_id,),
        ).fetchone()[0] == grade
        assert db.execute(
            "SELECT count(*) FROM specifications "
            "WHERE product_id=? AND spec_type='sae_engine'",
            (product_id,),
        ).fetchone()[0] == 0
    assert haiti_lubex_mag1_report[
        "evidence_rows"
    ] == len(haiti_lubex_mag1_rows) == report[
        "haiti_lubex_mag1_presence_source_rows"
    ] == 1
    assert haiti_lubex_mag1_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/haiti-lubex-mag1-current-presence.jsonl").read_bytes()
    ).hexdigest()
    assert report["haiti_lubex_mag1_presence_input_sha256"] == (
        haiti_lubex_mag1_report["normalized_output_sha256"]
    )
    assert policy_by_id[
        "HAITI_LUBEX_MAG1_CURRENT_DISTRIBUTOR_PRESENCE"
    ]["source_sha256"] == haiti_lubex_mag1_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "HAITI_LUBEX_MAG1_CURRENT_DISTRIBUTOR_PRESENCE"
    ]["observed_count"] == 1
    assert haiti_lubex_mag1_rows[0][
        "product_scope_status"
    ] == "no_local_sku_stock_or_full_global_range_inference_permitted"
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='HAITI_LUBEX_MAG1_CURRENT_DISTRIBUTOR_PRESENCE'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='HAITI_LUBEX_MAG1_CURRENT_DISTRIBUTOR_PRESENCE'"
    ).fetchone()[0] == 0
    assert antigua_vadd_shell_report[
        "evidence_rows"
    ] == len(antigua_vadd_shell_rows) == report[
        "antigua_vadd_shell_presence_source_rows"
    ] == 1
    assert rubis_caribbean_total_report[
        "evidence_rows"
    ] == len(rubis_caribbean_total_rows) == report[
        "rubis_caribbean_total_presence_source_rows"
    ] == 6
    assert antigua_vadd_shell_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/antigua-vadd-shell-current-presence.jsonl").read_bytes()
    ).hexdigest() == report["antigua_vadd_shell_presence_input_sha256"]
    assert rubis_caribbean_total_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/rubis-caribbean-total-current-presence.jsonl").read_bytes()
    ).hexdigest() == report["rubis_caribbean_total_presence_input_sha256"]
    assert policy_by_id[
        "ANTIGUA_VADD_SHELL_CURRENT_DISTRIBUTOR_PRESENCE"
    ]["source_sha256"] == antigua_vadd_shell_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "RUBIS_CARIBBEAN_TOTAL_CURRENT_RETAIL_PRESENCE"
    ]["source_sha256"] == rubis_caribbean_total_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "ANTIGUA_VADD_SHELL_CURRENT_DISTRIBUTOR_PRESENCE"
    ]["observed_count"] == 1
    assert policy_by_id[
        "RUBIS_CARIBBEAN_TOTAL_CURRENT_RETAIL_PRESENCE"
    ]["observed_count"] == 6
    assert {row["market"] for row in antigua_vadd_shell_rows} == {
        "Antigua and Barbuda"
    }
    assert {row["market"] for row in rubis_caribbean_total_rows} == {
        "Antigua and Barbuda",
        "Barbados",
        "Grenada",
        "Guyana",
        "Saint Lucia",
        "Saint Vincent and the Grenadines",
    }
    assert all(
        row["product_scope_status"]
        == "no_local_sku_stock_or_full_global_range_inference_permitted"
        for row in antigua_vadd_shell_rows + rubis_caribbean_total_rows
    )
    for evidence_source_id in (
        "ANTIGUA_VADD_SHELL_CURRENT_DISTRIBUTOR_PRESENCE",
        "RUBIS_CARIBBEAN_TOTAL_CURRENT_RETAIL_PRESENCE",
    ):
        assert db.execute(
            "SELECT count(*) FROM products WHERE source_id=?",
            (evidence_source_id,),
        ).fetchone()[0] == 0
        assert db.execute(
            "SELECT count(*) FROM product_sources WHERE source_id=?",
            (evidence_source_id,),
        ).fetchone()[0] == 0
    assert grenada_sol_report["unique_skus"] == len(
        grenada_sol_sku_rows
    ) == report["grenada_sol_current_sku_rows"] == 54
    assert grenada_sol_report["unique_product_grade_identities"] == len(
        grenada_sol_product_rows
    ) == report["grenada_sol_current_product_rows"] == 43
    assert grenada_sol_report["product_grade_identities_by_family"] == {
        "G": 2, "H": 5, "I": 5, "M": 24, "T": 7,
    }
    assert grenada_sol_report["normalized_output_sha256"] == hashlib.sha256(
        (ROOT / "data/grenada-sol-current-skus.jsonl").read_bytes()
    ).hexdigest() == report["grenada_sol_current_skus_input_sha256"]
    assert grenada_sol_report[
        "normalized_products_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/grenada-sol-current-products.jsonl").read_bytes()
    ).hexdigest() == report["grenada_sol_current_products_input_sha256"]
    assert policy_by_id[
        "GRENADA_SOL_CURRENT_ECOMMERCE_CATALOG"
    ]["source_sha256"] == grenada_sol_report["normalized_products_sha256"]
    assert policy_by_id[
        "GRENADA_SOL_CURRENT_ECOMMERCE_CATALOG"
    ]["observed_count"] == 43
    assert report["grenada_sol_products_matched_to_existing"] == 31
    assert report["grenada_sol_products_added"] == 12
    assert report["grenada_sol_multi_candidate_rows"] == 14
    assert report["grenada_sol_family_corrections"] == 3
    assert report["grenada_sol_priced_skus"] == 49
    assert report["grenada_sol_zero_price_placeholder_skus"] == 5
    assert grenada_sol_report["availability"] == {
        "InStock": 49, "NotAvailable": 1, "OutOfStock": 4,
    }
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='GRENADA_SOL_CURRENT_ECOMMERCE_CATALOG'"
    ).fetchone()[0] == 43
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='GRENADA_SOL_CURRENT_ECOMMERCE_CATALOG'"
    ).fetchone()[0] == 54
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='GRENADA_SOL_CURRENT_ECOMMERCE_CATALOG' "
        "AND price_status='published_current_price' "
        "AND price_amount>0 AND price_currency='XCD'"
    ).fetchone()[0] == 49
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='GRENADA_SOL_CURRENT_ECOMMERCE_CATALOG' "
        "AND price_status='zero_price_placeholder_without_currency' "
        "AND price_amount=0 AND price_currency=''"
    ).fetchone()[0] == 5
    assert {
        row[1]
        for row in db.execute("PRAGMA table_info(product_offers)")
    } >= {
        "price_amount", "price_currency", "price_currency_symbol", "price_status",
        "availability", "source_url",
    }
    assert np_ultra_export_presence_report[
        "source_market_occurrences"
    ] == 14
    assert np_ultra_export_presence_report[
        "unique_market_rows"
    ] == len(np_ultra_export_presence_rows) == report[
        "np_ultra_export_presence_source_rows"
    ] == 13
    assert np_ultra_export_presence_report["repeated_source_labels"] == {
        "Grenada": 2,
    }
    assert np_ultra_export_presence_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/np-ultra-current-export-presence.jsonl").read_bytes()
    ).hexdigest() == report["np_ultra_export_presence_input_sha256"]
    assert policy_by_id[
        "NP_ULTRA_CURRENT_EXPORT_MARKET_PRESENCE"
    ]["source_sha256"] == np_ultra_export_presence_report[
        "normalized_output_sha256"
    ]
    assert policy_by_id[
        "NP_ULTRA_CURRENT_EXPORT_MARKET_PRESENCE"
    ]["observed_count"] == 13
    assert {row["market"] for row in np_ultra_export_presence_rows} == {
        "Anguilla",
        "Antigua and Barbuda",
        "Barbados",
        "British Virgin Islands",
        "Grenada",
        "Guyana",
        "Jamaica",
        "Montserrat",
        "Saint Kitts and Nevis",
        "Saint Lucia",
        "Saint Vincent and the Grenadines",
        "Sint Maarten (Dutch part)",
        "Suriname",
    }
    assert all(
        row["product_scope_status"]
        == "existing_np_ultra_product_catalog_not_replicated_by_market"
        for row in np_ultra_export_presence_rows
    )
    assert db.execute(
        "SELECT count(*) FROM products "
        "WHERE source_id='NP_ULTRA_CURRENT_EXPORT_MARKET_PRESENCE'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='NP_ULTRA_CURRENT_EXPORT_MARKET_PRESENCE'"
    ).fetchone()[0] == 0
    assert cayman_ace_report["listing_denominator"] == 157
    assert cayman_ace_report["listing_pages"] == 11
    assert cayman_ace_report[
        "normalized_fluid_skus"
    ] == len(cayman_ace_sku_rows) == report[
        "cayman_ace_current_sku_rows"
    ] == 142
    assert cayman_ace_report[
        "product_grade_identities"
    ] == len(cayman_ace_product_rows) == report[
        "cayman_ace_current_product_rows"
    ] == 116
    assert cayman_ace_report["package_skus_collapsed"] == 26
    assert cayman_ace_report[
        "excluded_rows"
    ] == len(cayman_ace_exclusions) == 15
    assert cayman_ace_report["families"] == {
        "C": 2, "E": 1, "G": 15, "H": 5, "I": 1,
        "M": 81, "S": 1, "T": 31, "U": 5,
    }
    assert cayman_ace_report["lifecycle"] == {
        "discontinued_current_detail_page": 141,
        "listed_current_catalog": 1,
    }
    assert cayman_ace_report["listing_availability"] == {
        "outstock": 142,
    }
    assert cayman_ace_report["priced_skus"] == report[
        "cayman_ace_priced_skus"
    ] == 139
    assert cayman_ace_report[
        "normalized_output_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/cayman-ace-current-automotive-fluids.jsonl").read_bytes()
    ).hexdigest() == report["cayman_ace_current_skus_input_sha256"]
    assert cayman_ace_report[
        "normalized_products_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/cayman-ace-current-automotive-products.jsonl").read_bytes()
    ).hexdigest() == report["cayman_ace_current_products_input_sha256"]
    assert policy_by_id[
        "CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG"
    ]["source_sha256"] == cayman_ace_report[
        "normalized_products_sha256"
    ]
    assert policy_by_id[
        "CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG"
    ]["observed_count"] == 116
    assert report["cayman_ace_products_matched_to_existing"] == 0
    assert report["cayman_ace_products_added"] == 116
    assert report["cayman_ace_multi_candidate_rows"] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG'"
    ).fetchone()[0] == 116
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG'"
    ).fetchone()[0] == 142
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG' "
        "AND lifecycle_status='historical_discontinued_retail_catalog'"
    ).fetchone()[0] == 141
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG' "
        "AND lifecycle_status='listed_current_catalog_unavailable'"
    ).fetchone()[0] == 1
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG' "
        "AND price_amount>0 AND price_currency='KYD'"
    ).fetchone()[0] == 139
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG' "
        "AND availability='outstock'"
    ).fetchone()[0] == 142
    assert zambia_gearpros_report[
        "shop_cards"
    ] == len(zambia_gearpros_sku_rows) == report[
        "zambia_gearpros_current_sku_rows"
    ] == 22
    assert zambia_gearpros_report[
        "product_grade_identities"
    ] == len(zambia_gearpros_product_rows) == report[
        "zambia_gearpros_current_product_rows"
    ] == 15
    assert zambia_gearpros_report["package_skus_collapsed"] == 7
    assert zambia_gearpros_report["families"] == {
        "C": 1, "H": 3, "I": 2, "M": 6, "T": 3,
    }
    assert zambia_gearpros_report["brands"] == {
        "CENTLUBE": 1, "MOBIL": 14,
    }
    assert zambia_gearpros_report["priced_skus"] == report[
        "zambia_gearpros_priced_skus"
    ] == 22
    assert zambia_gearpros_report["sale_skus"] == 18
    assert zambia_gearpros_report["skus_with_pds"] == 22
    assert zambia_gearpros_report["skus_with_approvals"] == 16
    assert zambia_gearpros_report["skus_with_requirements"] == 18
    assert zambia_gearpros_report["skus_with_recommendations"] == 17
    assert zambia_gearpros_report[
        "normalized_skus_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/zambia-gearpros-current-skus.jsonl").read_bytes()
    ).hexdigest() == report["zambia_gearpros_current_skus_input_sha256"]
    assert zambia_gearpros_report[
        "normalized_products_sha256"
    ] == hashlib.sha256(
        (ROOT / "data/zambia-gearpros-current-products.jsonl").read_bytes()
    ).hexdigest() == report["zambia_gearpros_current_products_input_sha256"]
    assert policy_by_id[
        "ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP"
    ]["source_sha256"] == zambia_gearpros_report[
        "normalized_products_sha256"
    ]
    assert policy_by_id[
        "ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP"
    ]["observed_count"] == 15
    assert report["zambia_gearpros_products_matched_to_existing"] + report[
        "zambia_gearpros_products_added"
    ] == 15
    assert report["zambia_gearpros_products_matched_to_existing"] == 2
    assert report["zambia_gearpros_products_added"] == 13
    assert report["zambia_gearpros_multi_candidate_rows"] == 0
    assert db.execute(
        "SELECT count(*) FROM product_sources "
        "WHERE source_id='ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP'"
    ).fetchone()[0] == 15
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP'"
    ).fetchone()[0] == 22
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP' "
        "AND lifecycle_status='listed_current_catalog'"
    ).fetchone()[0] == 22
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP' "
        "AND price_amount>0 AND price_currency='' "
        "AND price_currency_symbol='$'"
    ).fetchone()[0] == 22
    assert db.execute(
        "SELECT count(*) FROM product_offers "
        "WHERE source_id='ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP' "
        "AND availability="
        "'order_action_present_stock_quantity_not_published'"
    ).fetchone()[0] == 22
    assert policy_by_id["VENEZUELA_PDV_CURRENT_CPE_LUBRICANT_CATALOG"]["observed_count"] == 23
    assert db.execute(
        "SELECT count(*) FROM products WHERE source_id='VENEZUELA_PDV_CURRENT_CPE_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 23
    assert db.execute(
        "SELECT count(*) FROM product_sources WHERE source_id='VENEZUELA_PDV_CURRENT_CPE_LUBRICANT_CATALOG'"
    ).fetchone()[0] == 23
    assert policy_by_id["nsf-white-book"]["bulk_ingest_allowed"] is False
    assert policy_by_id["FLENDER_T7300_APPROVED_LUBRICANTS"]["bulk_ingest_allowed"] is False
    chemexpo_names = {row["product_name"].casefold() for row in epa_chemexpo_rows}
    assert "soilax grease cutter" not in chemexpo_names
    assert "carburetor & choke cleaner" not in chemexpo_names
    assert "t1f270 flatting & reducing compound" not in chemexpo_names
    assert "crown gasoline dryer & antifreeze" not in chemexpo_names
    assert policy_by_id["KEBS_SMARK_LUBRICANT_PRODUCTS"]["source_sha256"] == kebs_smark_report["normalized_output_sha256"]
    assert policy_by_id["KEBS_SMARK_LUBRICANT_PRODUCTS"]["observed_count"] == kebs_smark_report["normalized_products"]
    assert kebs_smark_report["directory_total_smarks"] == 42358
    assert kebs_smark_report["visible_search_cards"] == 4276
    assert kebs_smark_report["search_occurrences"] == 4271
    assert kebs_smark_report["unique_permits_observed"] == 2897
    assert kebs_smark_report["lubricant_scope_permits"] == 775
    assert kebs_smark_report["duplicate_or_renewal_permits_merged"] == 25
    assert kebs_smark_report["families"] == {"C": 6, "E": 2, "G": 17, "H": 98, "I": 22, "M": 316, "T": 205, "TF": 81, "U": 3}
    assert all(not ({"address", "phone", "email", "contact"} & set(row)) for row in kebs_smark_rows)
    for source_id, expected in (("UNBS_CERTIFIED_LUBRICANT_PRODUCTS", 46), ("TBS_CERTIFIED_LUBRICANT_PRODUCTS", 183)):
        assert policy_by_id[source_id]["source_sha256"] == east_africa_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == expected
    assert east_africa_report["source_directory_rows"] == {
        "UNBS_CERTIFIED_LUBRICANT_PRODUCTS": 13091,
        "TBS_CERTIFIED_LUBRICANT_PRODUCTS": 2642,
    }
    assert east_africa_report["lubricant_scope_certificate_rows"] == {
        "UNBS_CERTIFIED_LUBRICANT_PRODUCTS": 47,
        "TBS_CERTIFIED_LUBRICANT_PRODUCTS": 70,
    }
    assert east_africa_report["product_designation_occurrences"] == {
        "TBS_CERTIFIED_LUBRICANT_PRODUCTS": 184,
        "UNBS_CERTIFIED_LUBRICANT_PRODUCTS": 47,
    }
    assert east_africa_report["certificate_renewal_or_duplicate_occurrences_merged"] == 2
    assert east_africa_report["tbs_lifecycle_method"].startswith("Computed from the official issue/expiry dates")
    assert east_africa_report["families"] == {"C": 7, "G": 7, "H": 30, "I": 2, "M": 116, "T": 56, "TF": 9, "U": 2}
    assert all(not ({"location", "district", "address", "phone", "email", "contact"} & set(row)) for row in east_africa_rows)
    assert policy_by_id["SON_MANCAP_CHEMICAL_LUBRICANT_PRODUCTS"]["source_sha256"] == son_mancap_report["normalized_output_sha256"]
    assert policy_by_id["SON_MANCAP_CHEMICAL_LUBRICANT_PRODUCTS"]["observed_count"] == son_mancap_report["normalized_products"]
    assert report["son_mancap_input_sha256"] == son_mancap_report["normalized_output_sha256"]
    assert son_mancap_report["source_pdf_pages"] == 233
    assert son_mancap_report["source_certificate_rows"] == 2011
    assert son_mancap_report["lubricant_scope_certificate_rows"] == 286
    assert son_mancap_report["product_designation_occurrences"] == 613
    assert son_mancap_report["duplicate_product_occurrences_merged"] == 5
    assert son_mancap_report["manufacturers"] == 127
    assert son_mancap_report["families"] == {"G": 30, "H": 25, "I": 2, "M": 418, "T": 115, "TF": 18}
    assert all(not ({"address", "state", "phone", "email", "contacts", "certification_mark_artwork"} & set(row)) for row in son_mancap_rows)
    assert policy_by_id["RSB_SMARK_LUBRICANT_PRODUCTS"]["source_sha256"] == rsb_smark_report["normalized_output_sha256"]
    assert policy_by_id["RSB_SMARK_LUBRICANT_PRODUCTS"]["observed_count"] == rsb_smark_report["normalized_products"]
    assert report["rsb_smark_input_sha256"] == rsb_smark_report["normalized_output_sha256"]
    assert rsb_smark_report["source_directory_rows"] == 1843
    assert rsb_smark_report["source_last_serial_number"] == 1846
    assert rsb_smark_report["source_missing_serial_numbers"] == [1764, 1765, 1766]
    assert rsb_smark_report["lubricant_scope_rows"] == 9
    assert rsb_smark_report["manufacturers"] == 2
    assert rsb_smark_report["brands"] == 4
    assert rsb_smark_report["families"] == {"M": 8, "S": 1}
    assert all(row["lifecycle_status"] == "source_reported_valid" for row in rsb_smark_rows)
    assert all(not ({"location", "telephone", "phone", "email", "contacts", "standard_body_text", "certification_mark_artwork"} & set(row)) for row in rsb_smark_rows)
    assert policy_by_id["BIS_PRODUCT_CERTIFICATION_LUBRICANT_LICENCES"]["bulk_ingest_allowed"] is False
    assert policy_by_id["BPCL_MAK_PRODUCT_CATALOG"]["bulk_ingest_allowed"] is False
    assert policy_by_id["api-eolcs"]["observed_count"] == 35174
    assert policy_by_id["NORDIC_SWAN_EU_ECOLABEL_LUBRICANTS_CROSSCHECK"]["observed_count"] == 60
    assert policy_by_id["TAIWAN_MOENV_ECOLABEL_PRODUCTS_LUBRICANT_REVIEW"]["observed_count"] == 0
    assert policy_by_id["BANGLADESH_BSTI_CM_LUBRICANT_LICENCE_REVIEW"]["observed_count"] == 9
    assert policy_by_id["MALAYSIA_SIRIM_ENGINE_OIL_DIRECTORY_REVIEW"]["bulk_ingest_allowed"] is False
    assert policy_by_id["INDIANOIL_SERVO_PRODUCT_CATALOG"]["observed_count"] == 1600
    assert policy_by_id["SINGAPORE_GREEN_LABEL_LUBRICANT_SCOPE_REVIEW"]["observed_count"] == 0
    assert policy_by_id["THAILAND_GREEN_LABEL_TGL20_LUBRICANT_REVIEW"]["observed_count"] == 0
    assert policy_by_id["NZ_ECO_CHOICE_LUBRICANT_SCOPE_REVIEW"]["observed_count"] == 0
    assert policy_by_id["GECA_AUSTRALIA_LUBRICANT_SCOPE_REVIEW"]["observed_count"] == 0
    assert policy_by_id["HONG_KONG_GREEN_LABEL_LUBRICANT_SCOPE_REVIEW"]["observed_count"] == 0
    assert policy_by_id["MALAWI_MBS_CERTIFIED_PRODUCTS_LUBRICANT_REVIEW"]["observed_count"] == 0
    assert policy_by_id["ZIMBABWE_SAZ_CERTIFIED_PRODUCTS_LUBRICANT_REVIEW"]["observed_count"] == 0
    assert policy_by_id["MAURITIUS_MSB_MAURICERT_LUBRICANT_REVIEW"]["observed_count"] == 0
    assert policy_by_id["NAMIBIA_NSI_CERTIFIED_PRODUCTS_LUBRICANT_REVIEW"]["observed_count"] == 0
    assert biopreferred_report["source_occurrences"] == 1387
    assert biopreferred_report["duplicate_category_occurrences_merged"] == 495
    assert policy_by_id["INDONESIA_NPT_LUBRICANT_REGISTRY"]["source_sha256"] == indonesia_report["normalized_output_sha256"]
    assert policy_by_id["INDONESIA_NPT_LUBRICANT_REGISTRY"]["observed_count"] == indonesia_report["published_product_rows"]
    assert indonesia_report["source_pdf_pages"] == 211
    assert indonesia_report["lifecycle_assessments"] == {
        "expired_by_expiry_date": 4242,
        "potentially_active_by_expiry_date": 8332,
        "source_expiry_error": 1,
        "source_placeholder_registration_unverified": 51,
    }
    assert policy_by_id["THAILAND_DOEB_LUBRICANT_REGISTRY"]["source_sha256"] == thailand_doeb_report["normalized_output_sha256"]
    assert policy_by_id["THAILAND_DOEB_LUBRICANT_REGISTRY"]["observed_count"] == len(thailand_doeb_rows) == 5486
    assert report["thailand_doeb_input_sha256"] == hashlib.sha256((ROOT / "data/thailand-doeb-lubricant-products.jsonl").read_bytes()).hexdigest()
    assert thailand_doeb_report["source_snapshot_month"] == "2024-03"
    assert thailand_doeb_report["registration_holders"] == 234
    assert thailand_doeb_report["families"] == {"M": 5486}
    assert thailand_doeb_report["standards"] == {"ACEA": 380, "API": 5328, "ILSAC": 249, "JASO": 677, "NMMA": 11, "OEM": 99}
    assert thailand_doeb_report["source_quality_flags"] == {"nonstandard_sae_notation": 1, "registration_number_collision": 6}
    assert all(row["family_code"] == "M" and row["registration_numbers"] for row in thailand_doeb_rows)
    assert sum(row["source_occurrence_count"] for row in thailand_doeb_rows) == 6213
    assert policy_by_id["DLA_QPD_FSC_9150"]["source_sha256"] == dla_report["normalized_output_sha256"]
    assert policy_by_id["DLA_QPD_FSC_9150"]["observed_count"] == dla_report["normalized_products_by_source"]["DLA_QPD_FSC_9150"]
    assert policy_by_id["DLA_QPD_FSC_6850_LUBRICANT_SCOPE"]["source_sha256"] == dla_report["normalized_output_sha256"]
    assert policy_by_id["DLA_QPD_FSC_6850_LUBRICANT_SCOPE"]["observed_count"] == dla_report["normalized_products_by_source"]["DLA_QPD_FSC_6850_LUBRICANT_SCOPE"]
    assert policy_by_id["DLA_QPD_FSC_8030_LUBRICANT_SCOPE"]["source_sha256"] == dla_report["normalized_output_sha256"]
    assert policy_by_id["DLA_QPD_FSC_8030_LUBRICANT_SCOPE"]["observed_count"] == dla_report["normalized_products_by_source"]["DLA_QPD_FSC_8030_LUBRICANT_SCOPE"]
    assert dla_report["lifecycle_statuses"] == {
        "mixed_qualification_lifecycle_review": 1,
        "qualification_overdue_contact_qa": 46,
        "qualified_source_certified": 440,
        "qualified_source_due_for_certification": 23,
        "sam_inactive_source_review": 24,
        "stop_ship": 2,
    }
    assert policy_by_id["ZF_TE_ML"]["source_sha256"] == zf_report["normalized_output_sha256"]
    assert policy_by_id["ZF_TE_ML"]["observed_count"] == zf_report["unique_approval_numbers"]
    assert zf_report["approval_occurrences"] == 4919
    assert zf_report["pdfs"] == 28
    assert policy_by_id["ALLISON_APPROVED_FLUIDS"]["source_sha256"] == allison_report["normalized_output_sha256"]
    assert policy_by_id["ALLISON_APPROVED_FLUIDS"]["observed_count"] == allison_report["products"]
    assert allison_report["lists"] == 6
    assert allison_report["approval_occurrences"] == 119
    assert allison_report["unique_approval_numbers"] == 117
    assert policy_by_id["DRIVENTIC_DIWA_APPROVED_OILS"]["source_sha256"] == driventic_report["normalized_output_sha256"]
    assert policy_by_id["DRIVENTIC_DIWA_APPROVED_OILS"]["observed_count"] == driventic_report["products"]
    assert driventic_report["lists"] == 4
    assert driventic_report["approval_occurrences"] == 226
    assert policy_by_id["MERCEDES_DTFR_APPROVED_FLUIDS"]["source_sha256"] == mercedes_report["normalized_output_sha256"]
    assert policy_by_id["MERCEDES_DTFR_APPROVED_FLUIDS"]["observed_count"] == mercedes_report["products"]
    assert mercedes_report["sheets"] == 63
    assert mercedes_report["approval_occurrences"] == 2102
    assert mercedes_report["current_products"] == 1854
    assert mercedes_report["historical_only_products"] == 38
    assert policy_by_id["MERCEDES_BENZ_BEVO_APPROVED_FLUIDS"]["source_sha256"] == mercedes_bevo_report["normalized_output_sha256"]
    assert policy_by_id["MERCEDES_BENZ_BEVO_APPROVED_FLUIDS"]["observed_count"] == mercedes_bevo_report["products"]
    assert mercedes_bevo_report["sheets_inspected"] == 130
    assert mercedes_bevo_report["product_sheets"] == 92
    assert mercedes_bevo_report["approval_occurrences"] == 2461
    assert mercedes_bevo_report["current_products"] == 1870
    assert mercedes_bevo_report["historical_only_products"] == 43
    assert mercedes_bevo_report["bevo_product_id_collisions"] == {"FDKAI7": 2}
    assert policy_by_id["VOLVO_GENUINE_FLUIDS"]["source_sha256"] == volvo_report["normalized_output_sha256"]
    assert policy_by_id["VOLVO_GENUINE_FLUIDS"]["observed_count"] == volvo_report["products"]
    assert volvo_report["families"] == {"G": 6, "H": 5, "M": 3, "T": 13, "TF": 5}
    assert len(volvo_report["source_pages"]) == 5
    assert len(volvo_report["excluded_ungraded_engine_oil_series"]) == 3
    assert policy_by_id["MACK_GENUINE_FLUIDS"]["source_sha256"] == mack_report["normalized_output_sha256"]
    assert policy_by_id["MACK_GENUINE_FLUIDS"]["observed_count"] == mack_report["products"]
    assert policy_by_id["MACK_2014_APPROVED_OILS"]["source_sha256"] == mack_2014_report["normalized_output_sha256"]
    assert policy_by_id["MACK_2014_APPROVED_OILS"]["observed_count"] == mack_2014_report["normalized_products"]
    assert policy_by_id["CEYPETCO_OFFICIAL_LUBRICANT_CATALOG"]["source_sha256"] == ceypetco_report["normalized_output_sha256"]
    assert policy_by_id["CEYPETCO_OFFICIAL_LUBRICANT_CATALOG"]["observed_count"] == len(ceypetco_rows) == 47
    assert report["ceypetco_input_sha256"] == hashlib.sha256((ROOT / "data/ceypetco-lubricant-products.jsonl").read_bytes()).hexdigest()
    assert ceypetco_report["source_product_lines"] == 23
    assert ceypetco_report["technical_documents"] == 22
    assert ceypetco_report["families"] == {"E": 1, "G": 10, "H": 4, "I": 1, "M": 17, "S": 1, "T": 8, "TF": 5}
    assert ceypetco_report["quality_flags"] == {"conflicting_sae_within_current_tds": 1, "nonstandard_oem_notation_retained_verbatim": 1, "tds_color_table_conflicts_with_product_variant": 1}
    assert all(not ({"description", "marketing_text", "document_text", "artwork", "image"} & set(row)) for row in ceypetco_rows)
    assert policy_by_id["MAN_CURRENT_SERVICE_PRODUCTS"]["source_sha256"] == man_report["normalized_output_sha256"]
    assert policy_by_id["MAN_CURRENT_SERVICE_PRODUCTS"]["observed_count"] == man_report["products"]
    assert man_report["document_date"] == "2026-04"
    assert man_report["pdf_pages"] == 150
    assert man_report["recommendation_occurrences"] == 33
    assert man_report["families"] == {"C": 4, "G": 14, "H": 7, "M": 2, "S": 1, "T": 3, "TF": 1}
    assert policy_by_id["FUCHS_INDIA_PRODUCT_FINDER"]["source_sha256"] == fuchs_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_INDIA_PRODUCT_FINDER"]["observed_count"] == fuchs_report["products"]
    assert fuchs_report["embedded_source_rows"] == 1115
    assert fuchs_report["source_series_rows_excluded"] == 94
    assert fuchs_report["equipment_rows_excluded"] == 6
    assert fuchs_report["duplicate_source_occurrences_merged"] == 8
    assert fuchs_report["families"] == {"C": 23, "E": 3, "G": 251, "H": 55, "I": 57, "M": 82, "S": 90, "T": 97, "TF": 348, "U": 1}
    assert len(fuchs_rows) == 1007
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_rows)
    assert policy_by_id["FUCHS_US_PRODUCT_FINDER"]["source_sha256"] == fuchs_us_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_US_PRODUCT_FINDER"]["observed_count"] == fuchs_us_report["products"]
    assert fuchs_us_report["embedded_source_rows"] == 686
    assert fuchs_us_report["source_series_rows_excluded"] == 60
    assert fuchs_us_report["equipment_rows_excluded"] == 0
    assert fuchs_us_report["duplicate_source_occurrences_merged"] == 3
    assert fuchs_us_report["families"] == {"C": 6, "G": 168, "H": 23, "I": 24, "M": 41, "S": 43, "T": 48, "TF": 270}
    assert len(fuchs_us_rows) == 623
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_us_rows)
    assert policy_by_id["FUCHS_GERMANY_PRODUCT_FINDER"]["source_sha256"] == fuchs_germany_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_GERMANY_PRODUCT_FINDER"]["observed_count"] == fuchs_germany_report["products"]
    assert fuchs_germany_report["embedded_source_rows"] == 1464
    assert fuchs_germany_report["source_series_rows_excluded"] == 0
    assert fuchs_germany_report["equipment_rows_excluded"] == 0
    assert fuchs_germany_report["duplicate_source_occurrences_merged"] == 0
    assert fuchs_germany_report["families"] == {"C": 66, "G": 318, "H": 174, "I": 42, "M": 103, "S": 142, "T": 147, "TF": 466, "U": 6}
    assert len(fuchs_germany_rows) == 1464
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_germany_rows)
    assert policy_by_id["FUCHS_POLAND_PRODUCT_FINDER"]["source_sha256"] == fuchs_poland_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_POLAND_PRODUCT_FINDER"]["observed_count"] == fuchs_poland_report["products"]
    assert fuchs_poland_report["embedded_source_rows"] == 776
    assert fuchs_poland_report["source_series_rows_excluded"] == 81
    assert fuchs_poland_report["equipment_rows_excluded"] == 0
    assert fuchs_poland_report["duplicate_source_occurrences_merged"] == 5
    assert fuchs_poland_report["families"] == {"C": 7, "E": 3, "G": 116, "H": 58, "I": 37, "M": 114, "S": 27, "T": 81, "TF": 246, "U": 1}
    assert fuchs_poland_report["classification_basis"]["special_product_fallback"] == 8
    assert len(fuchs_poland_rows) == 690
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_poland_rows)
    assert policy_by_id["FUCHS_ITALY_PRODUCT_FINDER"]["source_sha256"] == fuchs_italy_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_ITALY_PRODUCT_FINDER"]["observed_count"] == fuchs_italy_report["products"]
    assert fuchs_italy_report["embedded_source_rows"] == 1174
    assert fuchs_italy_report["source_series_rows_excluded"] == 84
    assert fuchs_italy_report["equipment_rows_excluded"] == 4
    assert fuchs_italy_report["duplicate_source_occurrences_merged"] == 79
    assert fuchs_italy_report["families"] == {"C": 27, "E": 5, "G": 224, "H": 53, "I": 31, "M": 125, "S": 60, "T": 107, "TF": 374, "U": 1}
    assert fuchs_italy_report["classification_basis"]["special_product_fallback"] == 20
    assert len(fuchs_italy_rows) == 1007
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_italy_rows)
    assert policy_by_id["FUCHS_SWEDEN_PRODUCT_FINDER"]["source_sha256"] == fuchs_sweden_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_SWEDEN_PRODUCT_FINDER"]["observed_count"] == fuchs_sweden_report["products"]
    assert fuchs_sweden_report["embedded_source_rows"] == 675
    assert fuchs_sweden_report["source_series_rows_excluded"] == 0
    assert fuchs_sweden_report["equipment_rows_excluded"] == 0
    assert fuchs_sweden_report["duplicate_source_occurrences_merged"] == 0
    assert fuchs_sweden_report["families"] == {"C": 35, "E": 1, "G": 156, "H": 64, "I": 65, "M": 70, "S": 43, "T": 96, "TF": 137, "U": 8}
    assert fuchs_sweden_report["classification_basis"]["special_product_fallback"] == 7
    assert len(fuchs_sweden_rows) == 675
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_sweden_rows)
    assert policy_by_id["FUCHS_SPAIN_PRODUCT_FINDER"]["source_sha256"] == fuchs_spain_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_SPAIN_PRODUCT_FINDER"]["observed_count"] == fuchs_spain_report["products"]
    assert fuchs_spain_report["embedded_source_rows"] == 1017
    assert fuchs_spain_report["source_series_rows_excluded"] == 69
    assert fuchs_spain_report["equipment_rows_excluded"] == 6
    assert fuchs_spain_report["placeholder_rows_excluded"] == 1
    assert fuchs_spain_report["duplicate_source_occurrences_merged"] == 3
    assert fuchs_spain_report["families"] == {"C": 20, "G": 213, "H": 112, "I": 40, "M": 106, "S": 68, "T": 118, "TF": 260, "U": 1}
    assert len(fuchs_spain_rows) == 938
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_spain_rows)
    assert policy_by_id["FUCHS_FRANCE_PRODUCT_FINDER"]["source_sha256"] == fuchs_france_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_FRANCE_PRODUCT_FINDER"]["observed_count"] == fuchs_france_report["products"]
    assert fuchs_france_report["embedded_source_rows"] == 765
    assert fuchs_france_report["source_series_rows_excluded"] == 42
    assert fuchs_france_report["equipment_rows_excluded"] == 1
    assert fuchs_france_report["placeholder_rows_excluded"] == 0
    assert fuchs_france_report["duplicate_source_occurrences_merged"] == 17
    assert fuchs_france_report["families"] == {"C": 12, "G": 170, "H": 22, "I": 27, "M": 118, "S": 25, "T": 99, "TF": 232}
    assert fuchs_france_report["classification_basis"]["special_product_fallback"] == 3
    assert len(fuchs_france_rows) == 705
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_france_rows)
    assert policy_by_id["FUCHS_TURKEY_PRODUCT_FINDER"]["source_sha256"] == fuchs_turkey_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_TURKEY_PRODUCT_FINDER"]["observed_count"] == fuchs_turkey_report["products"]
    assert fuchs_turkey_report["embedded_source_rows"] == 632
    assert fuchs_turkey_report["source_series_rows_excluded"] == 44
    assert fuchs_turkey_report["equipment_rows_excluded"] == 2
    assert fuchs_turkey_report["placeholder_rows_excluded"] == 0
    assert fuchs_turkey_report["duplicate_source_occurrences_merged"] == 3
    assert fuchs_turkey_report["families"] == {"C": 15, "E": 1, "G": 138, "H": 28, "I": 37, "M": 31, "S": 37, "T": 43, "TF": 253}
    assert fuchs_turkey_report["classification_basis"]["special_product_fallback"] == 11
    assert len(fuchs_turkey_rows) == 583
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_turkey_rows)
    assert policy_by_id["FUCHS_CANADA_PRODUCT_FINDER"]["source_sha256"] == fuchs_canada_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_CANADA_PRODUCT_FINDER"]["observed_count"] == fuchs_canada_report["products"]
    assert fuchs_canada_report["embedded_source_rows"] == 323
    assert fuchs_canada_report["source_series_rows_excluded"] == 34
    assert fuchs_canada_report["equipment_rows_excluded"] == 0
    assert fuchs_canada_report["placeholder_rows_excluded"] == 0
    assert fuchs_canada_report["duplicate_source_occurrences_merged"] == 0
    assert fuchs_canada_report["families"] == {"C": 7, "G": 36, "H": 10, "I": 29, "M": 21, "S": 11, "T": 33, "TF": 142}
    assert fuchs_canada_report["classification_basis"].get("special_product_fallback", 0) == 0
    assert len(fuchs_canada_rows) == 289
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_canada_rows)
    assert policy_by_id["FUCHS_CHINA_PRODUCT_FINDER"]["source_sha256"] == fuchs_china_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_CHINA_PRODUCT_FINDER"]["observed_count"] == fuchs_china_report["products"]
    assert fuchs_china_report["embedded_source_rows"] == 281
    assert fuchs_china_report["source_series_rows_excluded"] == 2
    assert fuchs_china_report["equipment_rows_excluded"] == 0
    assert fuchs_china_report["placeholder_rows_excluded"] == 0
    assert fuchs_china_report["duplicate_source_occurrences_merged"] == 1
    assert fuchs_china_report["families"] == {"C": 9, "G": 85, "H": 13, "I": 14, "M": 25, "S": 15, "T": 41, "TF": 76}
    assert fuchs_china_report["classification_basis"].get("special_product_fallback", 0) == 0
    assert len(fuchs_china_rows) == 278
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_china_rows)
    assert policy_by_id["FUCHS_CZECH_PRODUCT_FINDER"]["source_sha256"] == fuchs_czech_report["normalized_output_sha256"]
    assert policy_by_id["FUCHS_CZECH_PRODUCT_FINDER"]["observed_count"] == fuchs_czech_report["products"]
    assert fuchs_czech_report["embedded_source_rows"] == 1253
    assert fuchs_czech_report["source_series_rows_excluded"] == 98
    assert fuchs_czech_report["equipment_rows_excluded"] == 6
    assert fuchs_czech_report["placeholder_rows_excluded"] == 0
    assert fuchs_czech_report["duplicate_source_occurrences_merged"] == 3
    assert fuchs_czech_report["families"] == {"C": 22, "E": 3, "G": 273, "H": 58, "I": 70, "M": 113, "S": 69, "T": 125, "TF": 412, "U": 1}
    assert fuchs_czech_report["classification_basis"].get("special_product_fallback", 0) == 0
    assert len(fuchs_czech_rows) == 1146
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in fuchs_czech_rows)
    for source_id, source_report, source_rows, embedded, series, equipment, duplicates, families in [
        ("FUCHS_MEXICO_PRODUCT_FINDER", fuchs_mexico_report, fuchs_mexico_rows, 364, 50, 0, 0, {"C": 2, "G": 122, "H": 8, "I": 13, "M": 14, "S": 26, "T": 17, "TF": 112}),
        ("FUCHS_SOUTH_AFRICA_PRODUCT_FINDER", fuchs_south_africa_report, fuchs_south_africa_rows, 864, 94, 6, 8, {"C": 23, "E": 3, "G": 187, "H": 47, "I": 44, "M": 50, "S": 54, "T": 73, "TF": 274, "U": 1}),
        ("FUCHS_BRAZIL_PRODUCT_FINDER", fuchs_brazil_report, fuchs_brazil_rows, 213, 30, 0, 1, {"C": 4, "G": 68, "H": 13, "I": 2, "M": 8, "S": 17, "T": 37, "TF": 33}),
    ]:
        assert policy_by_id[source_id]["source_sha256"] == source_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == source_report["products"] == len(source_rows)
        assert source_report["embedded_source_rows"] == embedded
        assert source_report["source_series_rows_excluded"] == series
        assert source_report["equipment_rows_excluded"] == equipment
        assert source_report["duplicate_source_occurrences_merged"] == duplicates
        assert source_report["families"] == families
        assert source_report["classification_basis"].get("special_product_fallback", 0) == 0
        assert all(not ({"description", "subtitle", "components"} & set(row)) for row in source_rows)
    swiss_report = additional_fuchs["switzerland"]["report"]
    swiss_rows = additional_fuchs["switzerland"]["rows"]
    assert swiss_report["exact_name_matches_to_fuchs_germany"] == 1453
    assert swiss_report["family_overrides_from_unique_germany_reference"] == 203
    assert swiss_report["special_product_fallback_rows_resolved"] == 234
    assert swiss_report["special_product_fallback_rows_unresolved"] == 0
    assert swiss_report["unique_swiss_products_without_germany_name_match"] == 11
    assert len(swiss_report["unique_swiss_source_record_ids"]) == 11
    assert sum(row["taxonomy_reconciliation"]["status"] == "exact_normalized_product_name_unique_reference_family" for row in swiss_rows) == 1453
    assert all("source_market_classification" in row for row in swiss_rows)
    for source_id, source_report, source_rows, embedded, series, duplicates, fallback, families in [
        ("FUCHS_NORWAY_PRODUCT_FINDER", fuchs_norway_report, fuchs_norway_rows, 650, 1, 0, 17, {"C": 35, "E": 1, "G": 138, "H": 66, "I": 66, "M": 66, "S": 47, "T": 97, "TF": 125, "U": 8}),
        ("FUCHS_HUNGARY_PRODUCT_FINDER", fuchs_hungary_report, fuchs_hungary_rows, 544, 37, 1, 3, {"C": 7, "E": 1, "G": 140, "H": 23, "I": 19, "M": 79, "S": 40, "T": 45, "TF": 151, "U": 1}),
    ]:
        assert policy_by_id[source_id]["source_sha256"] == source_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == source_report["products"] == len(source_rows)
        assert source_report["embedded_source_rows"] == embedded
        assert source_report["source_series_rows_excluded"] == series
        assert source_report["equipment_rows_excluded"] == 0
        assert source_report["placeholder_rows_excluded"] == 0
        assert source_report["duplicate_source_occurrences_merged"] == duplicates
        assert source_report["families"] == families
        assert source_report["classification_basis"].get("special_product_fallback", 0) == fallback
        assert all(not ({"description", "subtitle", "components"} & set(row)) for row in source_rows)
    for slug, spec in additional_fuchs_specs.items():
        source_id, embedded, products, series, equipment, duplicates, fallback, _, _, _, _, families = spec
        source_report = additional_fuchs[slug]["report"]
        source_rows = additional_fuchs[slug]["rows"]
        assert policy_by_id[source_id]["source_sha256"] == source_report["normalized_output_sha256"]
        assert policy_by_id[source_id]["observed_count"] == source_report["products"] == len(source_rows) == products
        assert source_report["embedded_source_rows"] == embedded
        assert source_report["source_series_rows_excluded"] == series
        assert source_report["equipment_rows_excluded"] == equipment
        expected_placeholders = 1 if slug == "ukraine" else 2 if slug == "saudi-arabia" else 0
        assert source_report["placeholder_rows_excluded"] == expected_placeholders
        assert source_report["duplicate_source_occurrences_merged"] == duplicates
        assert source_report["families"] == families
        assert source_report["classification_basis"].get("special_product_fallback", 0) == fallback
        assert all(not ({"description", "subtitle", "components"} & set(row)) for row in source_rows)
    assert policy_by_id["LIQUI_MOLY_2020_PRODUCT_CATALOG"]["source_sha256"] == liqui_moly_report["normalized_output_sha256"]
    assert policy_by_id["LIQUI_MOLY_2020_PRODUCT_CATALOG"]["observed_count"] == liqui_moly_report["products"] == len(liqui_moly_rows) == 419
    assert liqui_moly_report["source_pdf_sha256"] == "07837b72dce364298837dba2d990e1187bf9d169253acbf34f1fce585605a3b0"
    assert liqui_moly_report["pdf_pages"] == 204
    assert liqui_moly_report["pages_selected"] == 72
    assert liqui_moly_report["product_occurrences"] == 444
    assert liqui_moly_report["duplicate_occurrences_merged"] == 25
    assert liqui_moly_report["families"] == {"C": 7, "G": 37, "H": 27, "I": 3, "M": 165, "S": 38, "T": 74, "TF": 68}
    assert liqui_moly_report["unique_part_numbers"] == 1482
    assert liqui_moly_report["products_with_package_rows"] == 413
    assert all(row["lifecycle_status"] == "historical_catalog_current_status_unverified" for row in liqui_moly_rows)
    assert all(not ({"description", "subtitle", "components"} & set(row)) for row in liqui_moly_rows)
    assert policy_by_id["LIQUI_MOLY_CURRENT_OPENAPI"]["source_sha256"] == liqui_moly_current_report["normalized_output_sha256"]
    assert policy_by_id["LIQUI_MOLY_CURRENT_OPENAPI"]["observed_count"] == len(liqui_moly_current_rows) == 447
    assert liqui_moly_current_report["sitemap_master_products"] == 759
    assert liqui_moly_current_report["api_master_products_fetched"] == 742
    assert liqui_moly_current_report["sitemap_products_unresolved_by_api"] == 17
    assert liqui_moly_current_report["families"] == {"C": 8, "G": 34, "H": 13, "I": 19, "M": 136, "S": 65, "T": 69, "TF": 103}
    assert liqui_moly_current_report["lifecycle_assessments"] == {
        "current_exact_name_continuity_from_2020": 199,
        "current_not_observed_in_2020_catalog": 150,
        "current_possible_rename_or_reformulation_shared_article_sku": 96,
        "review_multiple_historical_candidates": 2,
    }
    assert liqui_moly_current_report["historical_products_linked_to_current"] == 294
    assert liqui_moly_current_report["historical_products_not_observed_current"] == 125
    assert liqui_moly_current_report["lifecycle_rows"] == len(liqui_moly_lifecycle_rows) == 572
    assert liqui_moly_current_report["lifecycle_output_sha256"] == hashlib.sha256((ROOT / "data/liqui-moly-2020-2026-lifecycle.jsonl").read_bytes()).hexdigest()
    assert all(not ({"description", "image", "subtitle", "components"} & set(row)) for row in liqui_moly_current_rows)
    assert policy_by_id["ANP_BRAZIL_LUBRICANT_REGISTRY"]["source_sha256"] == anp_report["normalized_output_sha256"]
    assert policy_by_id["ANP_BRAZIL_LUBRICANT_REGISTRY"]["observed_count"] == len(anp_rows) == 12664
    assert report["anp_brazil_input_sha256"] == hashlib.sha256((ROOT / "data/anp-brazil-lubricant-products.jsonl").read_bytes()).hexdigest()
    assert anp_report["csv_rows"] == 14960
    assert anp_report["duplicate_source_occurrences_merged"] == 2296
    assert anp_report["unique_registration_numbers"] == 8193
    assert anp_report["families"] == {"G": 345, "H": 206, "I": 725, "M": 7263, "S": 119, "T": 4006}
    assert all(row["registration_status"] == "ATIVO" for row in anp_rows)
    assert all("source_row_numbers" in row and "packages" in row for row in anp_rows)
    assert all("observation" not in row and "OBS." not in row for row in anp_rows)
    assert policy_by_id["ANP_BRAZIL_LUBRICANT_MONITORING_HISTORY"]["source_sha256"] == anp_monitoring_report["normalized_output_sha256"]
    assert policy_by_id["ANP_BRAZIL_LUBRICANT_MONITORING_HISTORY"]["observed_count"] == len(anp_monitoring_rows) == 11026
    assert report["anp_brazil_monitoring_input_sha256"] == hashlib.sha256((ROOT / "data/anp-brazil-monitoring-observations.jsonl").read_bytes()).hexdigest()
    assert anp_monitoring_report["official_xlsx_files"] == 28
    assert anp_monitoring_report["unique_sample_ids"] == 8177
    assert anp_monitoring_report["supplementary_rows"] == anp_monitoring_report["supplementary_quality_flags_joined"] == 59
    assert anp_monitoring_report["quality_flags"] == {
        "source_reported_additive_absence": 51,
        "source_reported_without_registration": 8,
    }
    assert policy_by_id["ANP_BRAZIL_LUBRICANT_MONITORING_PDF_HISTORY"]["source_sha256"] == anp_monitoring_pdf_report["normalized_output_sha256"]
    assert policy_by_id["ANP_BRAZIL_LUBRICANT_MONITORING_PDF_HISTORY"]["observed_count"] == len(anp_monitoring_pdf_rows) == 1425
    assert report["anp_brazil_monitoring_pdf_input_sha256"] == hashlib.sha256((ROOT / "data/anp-brazil-monitoring-pdf-observations.jsonl").read_bytes()).hexdigest()
    assert anp_monitoring_pdf_report["official_pdf_files"] == 3
    assert anp_monitoring_pdf_report["normalized_product_grade_holder_identities"] == 693
    assert [row["published_product_rows"] for row in anp_monitoring_pdf_report["files"]] == [782, 462, 181]
    assert [row["published_minus_reported"] for row in anp_monitoring_pdf_report["files"]] == [0, 0, -9]
    assert report["anp_brazil_monitoring_xlsx_source_observations"] == len(anp_monitoring_rows)
    assert report["anp_brazil_monitoring_pdf_source_observations"] == len(anp_monitoring_pdf_rows)
    assert report["anp_brazil_monitoring_source_observations"] == (
        len(anp_monitoring_rows) + len(anp_monitoring_pdf_rows) + len(anp_monitoring_pdf_exception_rows)
    )
    assert report["anp_brazil_monitoring_product_grade_identities"] == (
        report["anp_brazil_monitoring_identities_matched_to_current_registry"]
        + report["anp_brazil_monitoring_historical_identities_added"]
    )
    assert report["official_government_historical_market_monitoring_rows"] == report["anp_brazil_monitoring_historical_identities_added"]
    assert report["anp_brazil_monitoring_registered_historical_identities_added"] + report["anp_brazil_monitoring_unregistered_historical_identities_added"] == report["anp_brazil_monitoring_historical_identities_added"]
    assert all(row["lifecycle_status"] == "historical_market_sample_observation" for row in anp_monitoring_rows)
    assert all(not ({"registration_holder_cnpj", "collection_location", "address"} & set(row)) for row in anp_monitoring_rows)
    assert all(row["published_scope"] == "complete_analyzed_products_list" for row in anp_monitoring_pdf_rows)
    assert all(row["lifecycle_status"] == "historical_market_sample_observation" for row in anp_monitoring_pdf_rows)
    assert all(not ({"cnpj", "registration_holder_cnpj", "collection_location", "address", "municipality", "retailer"} & set(row)) for row in anp_monitoring_pdf_rows)
    assert policy_by_id["ANP_BRAZIL_LUBRICANT_MONITORING_PDF_EXCEPTIONS"]["source_sha256"] == anp_monitoring_pdf_exception_report["normalized_output_sha256"]
    assert policy_by_id["ANP_BRAZIL_LUBRICANT_MONITORING_PDF_EXCEPTIONS"]["observed_count"] == len(anp_monitoring_pdf_exception_rows) == 4837
    assert report["anp_brazil_monitoring_pdf_exceptions_input_sha256"] == hashlib.sha256((ROOT / "data/anp-brazil-monitoring-pdf-exceptions.jsonl").read_bytes()).hexdigest()
    assert anp_monitoring_pdf_exception_report["official_pdf_files"] == 73
    assert anp_monitoring_pdf_exception_report["appendix_row_occurrences"] == 5612
    assert anp_monitoring_pdf_exception_report["normalized_product_grade_holder_identities"] == 3566
    assert report["anp_brazil_monitoring_pdf_exception_source_observations"] == len(anp_monitoring_pdf_exception_rows)
    assert report["anp_brazil_monitoring_pdf_exception_raw_identities"] == 3035
    assert report["anp_brazil_monitoring_pdf_exception_semantic_target_identities"] == 3013
    assert report["anp_brazil_monitoring_pdf_exception_semantically_remapped_observations"] == 356
    assert report["anp_brazil_monitoring_pdf_exception_semantically_remapped_identities"] == 131
    assert all(row["published_scope"] == "published_nonconforming_product_appendices_only" for row in anp_monitoring_pdf_exception_rows)
    assert all(row["lifecycle_status"] == "historical_market_sample_nonconformity_observation" for row in anp_monitoring_pdf_exception_rows)
    assert all(len(row["product_name"]) <= 100 for row in anp_monitoring_pdf_exception_rows)
    assert all(not ({"cnpj", "registration_holder_cnpj", "collection_location", "address", "municipality", "retailer", "seller"} & set(row)) for row in anp_monitoring_pdf_exception_rows)
    forbidden_tables = {"users", "requests", "request_items", "prices", "oil_market_sales"}
    output_tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not forbidden_tables & output_tables
    db.close()
    print(json.dumps({
        "status": "ok",
        "canonical_rows": jsonl_rows,
        "active_offers": report["active_offers"],
        "blocked_bulk_sources": len(report["bulk_sources_blocked"]),
        "flagged_legacy_motor_enkt_conflicts": flagged_motor_enkt,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
