#!/usr/bin/env python3
"""Verify reproducibility, provenance and quality gates for the world catalog seed."""

from __future__ import annotations

import hashlib
import gzip
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = json.loads((ROOT / "data/world-catalog-report.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "data/global-source-policy.json").read_text(encoding="utf-8"))
    jaso_report = json.loads((ROOT / "data/jaso-filed-oils-report.json").read_text(encoding="utf-8"))
    licensed_report = json.loads((ROOT / "data/official-licensed-products-report.json").read_text(encoding="utf-8"))
    biopreferred_report = json.loads((ROOT / "data/usda-biopreferred-products-report.json").read_text(encoding="utf-8"))
    zf_report = json.loads((ROOT / "data/zf-te-ml-approved-products-report.json").read_text(encoding="utf-8"))
    allison_report = json.loads((ROOT / "data/allison-approved-fluids-report.json").read_text(encoding="utf-8"))
    driventic_report = json.loads((ROOT / "data/driventic-diwa-approved-oils-report.json").read_text(encoding="utf-8"))
    mercedes_report = json.loads((ROOT / "data/mercedes-dtfr-approved-fluids-report.json").read_text(encoding="utf-8"))
    mercedes_bevo_report = json.loads((ROOT / "data/mercedes-bevo-approved-fluids-report.json").read_text(encoding="utf-8"))
    volvo_report = json.loads((ROOT / "data/volvo-genuine-fluids-report.json").read_text(encoding="utf-8"))
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
        "denmark": ("FUCHS_DENMARK_PRODUCT_FINDER", 641, 640, 1, 0, 0, 20, 613, 27, 638, 1, {"C": 35, "E": 1, "G": 137, "H": 66, "I": 65, "M": 66, "S": 47, "T": 93, "TF": 122, "U": 8}),
        "finland": ("FUCHS_FINLAND_PRODUCT_FINDER", 639, 599, 38, 0, 2, 5, 554, 45, 581, 0, {"C": 33, "E": 2, "G": 133, "H": 63, "I": 37, "M": 79, "S": 33, "T": 85, "TF": 128, "U": 6}),
        "portugal": ("FUCHS_PORTUGAL_PRODUCT_FINDER", 529, 484, 42, 2, 1, 2, 443, 41, 460, 10, {"C": 19, "E": 1, "G": 137, "H": 35, "I": 30, "M": 79, "S": 54, "T": 66, "TF": 62, "U": 1}),
        "romania": ("FUCHS_ROMANIA_PRODUCT_FINDER", 794, 691, 91, 1, 11, 1, 679, 12, 690, 1, {"C": 19, "E": 3, "G": 176, "H": 42, "I": 29, "M": 76, "S": 56, "T": 85, "TF": 204, "U": 1}),
        "austria": ("FUCHS_AUSTRIA_PRODUCT_FINDER", 1057, 952, 94, 6, 5, 0, 937, 15, 952, 0, {"C": 23, "E": 3, "G": 237, "H": 54, "I": 53, "M": 78, "S": 75, "T": 95, "TF": 333, "U": 1}),
        "greece": ("FUCHS_GREECE_PRODUCT_FINDER", 1074, 966, 97, 6, 5, 0, 951, 15, 966, 0, {"C": 23, "E": 3, "G": 237, "H": 55, "I": 57, "M": 84, "S": 75, "T": 96, "TF": 335, "U": 1}),
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
    indonesia_report = json.loads((ROOT / "data/indonesia-npt-lubricant-products-report.json").read_text(encoding="utf-8"))
    indonesia_rows = [json.loads(line) for line in (ROOT / "data/indonesia-npt-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    dla_report = json.loads((ROOT / "data/dla-qpd-lubricant-products-report.json").read_text(encoding="utf-8"))
    dla_rows = [json.loads(line) for line in (ROOT / "data/dla-qpd-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    blue_angel_report = json.loads((ROOT / "data/blue-angel-de-uz-178-products-report.json").read_text(encoding="utf-8"))
    blue_angel_rows = [json.loads(line) for line in (ROOT / "data/blue-angel-de-uz-178-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    korea_ecolabel_report = json.loads((ROOT / "data/korea-ecolabel-el611-lubricants-report.json").read_text(encoding="utf-8"))
    korea_ecolabel_rows = [json.loads(line) for line in (ROOT / "data/korea-ecolabel-el611-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    korea_el509_report = json.loads((ROOT / "data/korea-ecolabel-el509-washer-fluids-report.json").read_text(encoding="utf-8"))
    korea_el509_rows = [json.loads(line) for line in (ROOT / "data/korea-ecolabel-el509-washer-fluids.jsonl").read_text(encoding="utf-8").splitlines() if line]
    uae_moiat_report = json.loads((ROOT / "data/uae-moiat-conformity-products-report.json").read_text(encoding="utf-8"))
    uae_moiat_rows = [json.loads(line) for line in (ROOT / "data/uae-moiat-conformity-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    epa_safer_choice_report = json.loads((ROOT / "data/epa-safer-choice-lubricants-report.json").read_text(encoding="utf-8"))
    epa_safer_choice_rows = [json.loads(line) for line in (ROOT / "data/epa-safer-choice-lubricants.jsonl").read_text(encoding="utf-8").splitlines() if line]
    kebs_smark_report = json.loads((ROOT / "data/kebs-smark-lubricant-products-report.json").read_text(encoding="utf-8"))
    kebs_smark_rows = [json.loads(line) for line in (ROOT / "data/kebs-smark-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    east_africa_report = json.loads((ROOT / "data/east-africa-certified-lubricant-products-report.json").read_text(encoding="utf-8"))
    east_africa_rows = [json.loads(line) for line in (ROOT / "data/east-africa-certified-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    son_mancap_report = json.loads((ROOT / "data/son-mancap-chemical-lubricant-products-report.json").read_text(encoding="utf-8"))
    son_mancap_rows = [json.loads(line) for line in (ROOT / "data/son-mancap-chemical-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rsb_smark_report = json.loads((ROOT / "data/rsb-smark-lubricant-products-report.json").read_text(encoding="utf-8"))
    rsb_smark_rows = [json.loads(line) for line in (ROOT / "data/rsb-smark-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    jsonl_gz_path = ROOT / "data/world-catalog-products.jsonl.gz"
    with gzip.open(jsonl_gz_path, "rt", encoding="utf-8") as stream:
        lines = [json.loads(line) for line in stream if line.strip()]
    local_jsonl_path = ROOT / "data/world-catalog-products.jsonl"
    if local_jsonl_path.exists():
        with local_jsonl_path.open("rb") as plain, gzip.open(jsonl_gz_path, "rb") as packed:
            assert hashlib.sha256(plain.read()).digest() == hashlib.sha256(packed.read()).digest()
    assert report["status"] == "seed_only_world_catalog_incomplete"
    assert report["confirmed_world_total"] is None
    assert len(lines) == report["canonical_rows"]
    assert len({row["product_id"] for row in lines}) == len(lines)
    assert len({row["canonical_key"] for row in lines}) == len(lines)
    assert report["normalized_input_sha256"] == hashlib.sha256((ROOT / "data/catalog-v3.json").read_bytes()).hexdigest()

    for source in policy["sources"]:
        if source.get("source_locator") and source.get("source_sha256"):
            actual = hashlib.sha256((ROOT / source["source_locator"]).read_bytes()).hexdigest()
            assert actual == source["source_sha256"], source["source_id"]
        if not source["bulk_ingest_allowed"]:
            assert source["source_id"] in report["bulk_sources_blocked"]

    db = sqlite3.connect(ROOT / "data/world-catalog.sqlite3")
    with (ROOT / "data/world-catalog.sqlite3").open("rb") as plain, gzip.open(ROOT / "data/world-catalog.sqlite3.gz", "rb") as packed:
        assert hashlib.sha256(plain.read()).digest() == hashlib.sha256(packed.read()).digest()
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert db.execute("SELECT count(*) FROM products").fetchone()[0] == len(lines)
    assert len(lines) == 48325
    assert report["jaso_source_rows"] == jaso_report["rows"] == 3630
    assert report["jaso_unique_oil_codes"] == jaso_report["unique_oil_codes"] == 3629
    assert report["official_filed_registry_rows"] == 3629
    assert report["official_licensed_source_rows"] == licensed_report["rows"] == 3037
    assert report["official_licensed_registry_rows"] == 3037
    assert report["blue_angel_source_rows"] == blue_angel_report["normalized_products"] == len(blue_angel_rows) == 148
    assert report["blue_angel_products_matched_to_existing"] == 21
    assert report["blue_angel_products_added"] == report["official_ecolabel_product_registry_rows"] == 127
    assert report["korea_ecolabel_source_rows"] == korea_ecolabel_report["normalized_products"] == len(korea_ecolabel_rows) == 20
    assert report["korea_ecolabel_products_matched_to_existing"] == 0
    assert report["korea_ecolabel_products_added"] == 20
    assert report["korea_ecolabel_el509_source_rows"] == korea_el509_report["normalized_products"] == len(korea_el509_rows) == 9
    assert report["korea_ecolabel_el509_products_matched_to_existing"] == 0
    assert report["korea_ecolabel_el509_products_added"] == 9
    assert report["official_government_ecolabel_registry_rows"] == 29
    assert report["uae_moiat_source_rows"] == uae_moiat_report["normalized_products"] == len(uae_moiat_rows) == 1840
    assert report["official_government_product_conformity_registry_rows"] == 1840
    assert report["epa_safer_choice_source_rows"] == epa_safer_choice_report["normalized_products"] == len(epa_safer_choice_rows) == 2
    assert report["kebs_smark_source_rows"] == kebs_smark_report["normalized_products"] == len(kebs_smark_rows) == 750
    assert report["east_africa_certified_source_rows"] == east_africa_report["normalized_products"] == len(east_africa_rows) == 229
    assert report["east_africa_certified_source_rows_by_source"] == east_africa_report["normalized_products_by_source"] == {
        "TBS_CERTIFIED_LUBRICANT_PRODUCTS": 183,
        "UNBS_CERTIFIED_LUBRICANT_PRODUCTS": 46,
    }
    assert report["son_mancap_source_rows"] == son_mancap_report["normalized_products"] == len(son_mancap_rows) == 608
    assert report["rsb_smark_source_rows"] == rsb_smark_report["normalized_products"] == len(rsb_smark_rows) == 9
    assert report["official_government_product_certification_registry_rows"] == 1596
    assert report["usda_biopreferred_source_rows"] == biopreferred_report["rows"] == 892
    assert report["official_government_program_rows"] == 894
    assert report["anp_brazil_source_rows"] == anp_report["normalized_product_grade_rows"] == len(anp_rows) == 12664
    assert report["indonesia_npt_source_rows"] == indonesia_report["published_product_rows"] == len(indonesia_rows) == 12626
    assert report["indonesia_npt_rows_with_registration_value"] == indonesia_report["rows_with_registration_value"] == 12575
    assert report["indonesia_npt_rows_with_source_data_issue"] == indonesia_report["rows_with_source_placeholder_no_registration_number"] == 51
    assert indonesia_report["unique_registration_numbers"] == 12565
    assert indonesia_report["registration_number_collisions"] == 10
    assert report["official_government_regulatory_registry_rows"] == 25239
    assert report["official_government_registry_source_data_issue_rows"] == 51
    assert report["dla_qpd_source_rows"] == dla_report["normalized_products"] == len(dla_rows) == 456
    assert report["official_government_qualified_product_registry_rows"] == 456
    assert report["dla_qpd_source_rows_by_source"] == dla_report["normalized_products_by_source"] == {
        "DLA_QPD_FSC_6850_LUBRICANT_SCOPE": 25,
        "DLA_QPD_FSC_9150": 431,
    }
    assert dla_report["active_qpls_in_scope"] == 62
    assert dla_report["qpls_by_fsc"] == {"6850_lubricant_scope": 6, "9150": 56}
    assert len(dla_report["fsc_6850_excluded_active_qpls"]) == 18
    assert not ({q.removeprefix("QPL-") for q in dla_report["fsc_6850_excluded_active_qpls"]} & {"6529", "8188", "AS8660", "25017", "29608", "32490"})
    assert dla_report["government_designations"] == 118
    assert dla_report["published_manufacturer_product_occurrences"] == 480
    assert dla_report["plant_rows_without_product_designation_excluded"] == 766
    assert report["zf_te_ml_source_rows"] == zf_report["unique_approval_numbers"] == 1498
    assert report["official_oem_approval_rows"] == 5475
    assert report["official_manufacturer_catalog_rows"] == 5331
    assert report["official_oem_service_recommendation_rows"] == 30
    assert report["allison_source_rows"] == allison_report["products"] == 104
    assert report["driventic_diwa_source_rows"] == driventic_report["products"] == 226
    assert report["mercedes_dtfr_source_rows"] == mercedes_report["products"] == 1892
    assert report["mercedes_bevo_source_rows"] == mercedes_bevo_report["products"] == 1913
    assert report["mercedes_bevo_products_matched_to_existing"] == 158
    assert report["mercedes_bevo_products_added"] == 1755
    assert report["volvo_genuine_source_rows"] == volvo_report["products"] == 32
    assert report["man_service_source_rows"] == man_report["products"] == 32
    assert report["man_service_products_matched_to_existing"] == 2
    assert report["man_service_products_added"] == 30
    assert report["fuchs_india_source_rows"] == fuchs_report["products"] == 1007
    assert report["fuchs_india_products_matched_to_existing"] == 22
    assert report["fuchs_india_products_added"] == 985
    assert report["fuchs_us_source_rows"] == fuchs_us_report["products"] == 623
    assert report["fuchs_us_products_matched_to_existing"] == 124
    assert report["fuchs_us_products_added"] == 499
    assert report["fuchs_cross_market_exact_name_family_rows"] == 118
    assert report["fuchs_cross_market_family_conflict_rows"] == 4
    assert report["fuchs_germany_source_rows"] == fuchs_germany_report["products"] == 1464
    assert report["fuchs_germany_products_matched_to_existing"] == 447
    assert report["fuchs_germany_products_added"] == 1017
    assert report["fuchs_germany_cross_market_exact_name_family_rows"] == 441
    assert report["fuchs_germany_cross_market_family_conflict_rows"] == 79
    assert report["fuchs_poland_source_rows"] == fuchs_poland_report["products"] == 690
    assert report["fuchs_poland_products_matched_to_existing"] == 540
    assert report["fuchs_poland_products_added"] == 150
    assert report["fuchs_poland_cross_market_exact_name_family_rows"] == 560
    assert report["fuchs_poland_cross_market_family_conflict_rows"] == 59
    assert report["fuchs_italy_source_rows"] == fuchs_italy_report["products"] == 1007
    assert report["fuchs_italy_products_matched_to_existing"] == 637
    assert report["fuchs_italy_products_added"] == 370
    assert report["fuchs_italy_cross_market_exact_name_family_rows"] == 657
    assert report["fuchs_italy_cross_market_family_conflict_rows"] == 28
    assert report["fuchs_sweden_source_rows"] == fuchs_sweden_report["products"] == 675
    assert report["fuchs_sweden_products_matched_to_existing"] == 358
    assert report["fuchs_sweden_products_added"] == 317
    assert report["fuchs_sweden_cross_market_exact_name_family_rows"] == 379
    assert report["fuchs_sweden_cross_market_family_conflict_rows"] == 17
    assert report["fuchs_spain_source_rows"] == fuchs_spain_report["products"] == 938
    assert report["fuchs_spain_products_matched_to_existing"] == 719
    assert report["fuchs_spain_products_added"] == 219
    assert report["fuchs_spain_cross_market_exact_name_family_rows"] == 743
    assert report["fuchs_spain_cross_market_family_conflict_rows"] == 19
    assert report["fuchs_france_source_rows"] == fuchs_france_report["products"] == 705
    assert report["fuchs_france_products_matched_to_existing"] == 499
    assert report["fuchs_france_products_added"] == 206
    assert report["fuchs_france_cross_market_exact_name_family_rows"] == 532
    assert report["fuchs_france_cross_market_family_conflict_rows"] == 12
    assert report["fuchs_turkey_source_rows"] == fuchs_turkey_report["products"] == 583
    assert report["fuchs_turkey_products_matched_to_existing"] == 414
    assert report["fuchs_turkey_products_added"] == 169
    assert report["fuchs_turkey_cross_market_exact_name_family_rows"] == 423
    assert report["fuchs_turkey_cross_market_family_conflict_rows"] == 5
    assert report["fuchs_canada_source_rows"] == fuchs_canada_report["products"] == 289
    assert report["fuchs_canada_products_matched_to_existing"] == 138
    assert report["fuchs_canada_products_added"] == 151
    assert report["fuchs_canada_cross_market_exact_name_family_rows"] == 152
    assert report["fuchs_canada_cross_market_family_conflict_rows"] == 5
    assert report["fuchs_china_source_rows"] == fuchs_china_report["products"] == 278
    assert report["fuchs_china_products_matched_to_existing"] == 198
    assert report["fuchs_china_products_added"] == 80
    assert report["fuchs_china_cross_market_exact_name_family_rows"] == 202
    assert report["fuchs_china_cross_market_family_conflict_rows"] == 0
    assert report["fuchs_czech_source_rows"] == fuchs_czech_report["products"] == 1146
    assert report["fuchs_czech_products_matched_to_existing"] == 1035
    assert report["fuchs_czech_products_added"] == 111
    assert report["fuchs_czech_cross_market_exact_name_family_rows"] == 1063
    assert report["fuchs_czech_cross_market_family_conflict_rows"] == 19
    assert report["fuchs_mexico_source_rows"] == fuchs_mexico_report["products"] == 314
    assert report["fuchs_mexico_products_matched_to_existing"] == 251
    assert report["fuchs_mexico_products_added"] == 63
    assert report["fuchs_mexico_cross_market_exact_name_family_rows"] == 258
    assert report["fuchs_mexico_cross_market_family_conflict_rows"] == 3
    assert report["fuchs_south_africa_source_rows"] == fuchs_south_africa_report["products"] == 756
    assert report["fuchs_south_africa_products_matched_to_existing"] == 712
    assert report["fuchs_south_africa_products_added"] == 44
    assert report["fuchs_south_africa_cross_market_exact_name_family_rows"] == 725
    assert report["fuchs_south_africa_cross_market_family_conflict_rows"] == 2
    assert report["fuchs_brazil_source_rows"] == fuchs_brazil_report["products"] == 182
    assert report["fuchs_brazil_products_matched_to_existing"] == 176
    assert report["fuchs_brazil_products_added"] == 6
    assert report["fuchs_brazil_cross_market_exact_name_family_rows"] == 182
    assert report["fuchs_brazil_cross_market_family_conflict_rows"] == 0
    assert report["fuchs_norway_source_rows"] == fuchs_norway_report["products"] == 649
    assert report["fuchs_norway_products_matched_to_existing"] == 604
    assert report["fuchs_norway_products_added"] == 45
    assert report["fuchs_norway_cross_market_exact_name_family_rows"] == 630
    assert report["fuchs_norway_cross_market_family_conflict_rows"] == 15
    assert report["fuchs_hungary_source_rows"] == fuchs_hungary_report["products"] == 506
    assert report["fuchs_hungary_products_matched_to_existing"] == 352
    assert report["fuchs_hungary_products_added"] == 154
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
    assert report["duplicate_decisions"]["review_cross_source_identity"] == 3206
    assert report["duplicate_decisions"]["keep_separate_blue_angel_family_conflict"] == 34
    assert report["duplicate_decisions"]["review_brand_alias_identity"] == 2
    assert report["duplicate_decisions"]["review_liqui_moly_multi_registry_identity"] == 49
    assert report["duplicate_decisions"]["review_liqui_moly_current_multiple_historical_candidates"] == 4
    assert report["duplicate_decisions"]["review_fuchs_multi_registry_identity"] == 4451
    assert report["duplicate_decisions"]["keep_separate_fuchs_market_family_conflict"] == 502
    assert report["aichilon_products_matched_to_existing"] == 255
    assert report["aichilon_products_added"] == 60
    assert report["aichilon_rows_excluded"] == 2
    assert db.execute("SELECT count(*) FROM product_offers").fetchone()[0] == report["offers"] == 3859
    assert db.execute("SELECT count(*) FROM product_offers WHERE lifecycle_status='active'").fetchone()[0] == report["active_offers"] == 1455
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_filed_registry'").fetchone()[0] == 3629
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_licensed_registry'").fetchone()[0] == 3037
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_ecolabel_product_registry'").fetchone()[0] == 127
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_ecolabel_registry'").fetchone()[0] == 29
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_product_conformity_registry'").fetchone()[0] == 1840
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_product_certification_registry'").fetchone()[0] == 1596
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_program_catalog'").fetchone()[0] == 894
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_regulatory_registry'").fetchone()[0] == 25239
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_registry_source_data_issue'").fetchone()[0] == 51
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_qualified_product_registry'").fetchone()[0] == 456
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_oem_approval_registry'").fetchone()[0] == 5475
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_manufacturer_product_catalog'").fetchone()[0] == 5331
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_oem_service_recommendation'").fetchone()[0] == 30
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='ALLISON_APPROVAL_NUMBER'").fetchone()[0] == 119
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='MERCEDES_DTFR_PRODUCT_ID'").fetchone()[0] == 1892
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='MERCEDES_BEVO_PRODUCT_ID'").fetchone()[0] == 1914
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='BLUE_ANGEL_PRODUCT_PAGE'").fetchone()[0] == 149
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='KOREA_ECOLABEL_CERTIFICATE'").fetchone()[0] == 29
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='VOLVO_PART_NUMBER'").fetchone()[0] == 20
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='VOLVO_GENUINE_FLUIDS'").fetchone()[0] == 32
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
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='ANP_BRAZIL_REGISTRATION_NUMBER'").fetchone()[0] == 12664
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='INDONESIA_NPT_REGISTRATION_NUMBER'").fetchone()[0] == 12575
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='INDONESIA_NPT_LUBRICANT_REGISTRY'").fetchone()[0] == 12626
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='source_registration_number_missing'").fetchone()[0] == 51
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='DLA_QPD_FSC_9150'").fetchone()[0] == 431
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='DLA_QPD_FSC_6850_LUBRICANT_SCOPE'").fetchone()[0] == 25
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='BLUE_ANGEL_DE_UZ_178'").fetchone()[0] == 148
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='KOREA_ECOLABEL_EL611'").fetchone()[0] == 20
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='KOREA_ECOLABEL_EL509'").fetchone()[0] == 9
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='UAE_MOIAT_PRODUCT_CONFORMITY'").fetchone()[0] == 1840
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='EPA_SAFER_CHOICE_LUBRICANTS'").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM external_codes WHERE source_id='EPA_SAFER_CHOICE_LUBRICANTS'").fetchone()[0] == 12
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
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='DLA_QPL_NUMBER'").fetchone()[0] == 457
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='dla_qpd_lifecycle_restriction'").fetchone()[0] == 93
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='FUCHS_PRODUCT_UID'").fetchone()[0] == 16300
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
    assert policy_by_id["DLA_QPD_FSC_9150"]["source_sha256"] == dla_report["normalized_output_sha256"]
    assert policy_by_id["DLA_QPD_FSC_9150"]["observed_count"] == dla_report["normalized_products_by_source"]["DLA_QPD_FSC_9150"]
    assert policy_by_id["DLA_QPD_FSC_6850_LUBRICANT_SCOPE"]["source_sha256"] == dla_report["normalized_output_sha256"]
    assert policy_by_id["DLA_QPD_FSC_6850_LUBRICANT_SCOPE"]["observed_count"] == dla_report["normalized_products_by_source"]["DLA_QPD_FSC_6850_LUBRICANT_SCOPE"]
    assert dla_report["lifecycle_statuses"] == {
        "mixed_qualification_lifecycle_review": 1,
        "qualification_overdue_contact_qa": 46,
        "qualified_source_certified": 363,
        "qualified_source_due_for_certification": 23,
        "sam_inactive_source_review": 21,
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
        assert source_report["placeholder_rows_excluded"] == 0
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
    forbidden_tables = {"users", "requests", "request_items", "prices", "oil_market_sales"}
    output_tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not forbidden_tables & output_tables
    db.close()
    print(json.dumps({
        "status": "ok",
        "canonical_rows": len(lines),
        "active_offers": report["active_offers"],
        "blocked_bulk_sources": len(report["bulk_sources_blocked"]),
        "flagged_legacy_motor_enkt_conflicts": flagged_motor_enkt,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
