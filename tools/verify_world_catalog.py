#!/usr/bin/env python3
"""Verify reproducibility, provenance and quality gates for the world catalog seed."""

from __future__ import annotations

import hashlib
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
    lines = [json.loads(line) for line in (ROOT / "data/world-catalog-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
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
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert db.execute("SELECT count(*) FROM products").fetchone()[0] == len(lines)
    assert len(lines) == 15189
    assert report["jaso_source_rows"] == jaso_report["rows"] == 3630
    assert report["jaso_unique_oil_codes"] == jaso_report["unique_oil_codes"] == 3629
    assert report["official_filed_registry_rows"] == 3629
    assert report["official_licensed_source_rows"] == licensed_report["rows"] == 3037
    assert report["official_licensed_registry_rows"] == 3037
    assert report["usda_biopreferred_source_rows"] == biopreferred_report["rows"] == 892
    assert report["official_government_program_rows"] == 892
    assert report["zf_te_ml_source_rows"] == zf_report["unique_approval_numbers"] == 1498
    assert report["official_oem_approval_rows"] == 5475
    assert report["official_manufacturer_catalog_rows"] == 1535
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
    assert report["fuchs_india_products_matched_to_existing"] == 6
    assert report["fuchs_india_products_added"] == 1001
    assert report["fuchs_us_source_rows"] == fuchs_us_report["products"] == 623
    assert report["fuchs_us_products_matched_to_existing"] == 121
    assert report["fuchs_us_products_added"] == 502
    assert report["fuchs_cross_market_exact_name_family_rows"] == 118
    assert report["fuchs_cross_market_family_conflict_rows"] == 4
    assert report["duplicate_decisions"]["review_cross_source_identity"] == 312
    assert report["duplicate_decisions"]["review_brand_alias_identity"] == 2
    assert report["duplicate_decisions"]["review_fuchs_multi_registry_identity"] == 39
    assert report["duplicate_decisions"]["keep_separate_fuchs_market_family_conflict"] == 6
    assert report["aichilon_products_matched_to_existing"] == 255
    assert report["aichilon_products_added"] == 60
    assert report["aichilon_rows_excluded"] == 2
    assert db.execute("SELECT count(*) FROM product_offers").fetchone()[0] == report["offers"] == 2874
    assert db.execute("SELECT count(*) FROM product_offers WHERE lifecycle_status='active'").fetchone()[0] == report["active_offers"] == 1455
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_filed_registry'").fetchone()[0] == 3629
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_licensed_registry'").fetchone()[0] == 3037
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_program_catalog'").fetchone()[0] == 892
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_oem_approval_registry'").fetchone()[0] == 5475
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_manufacturer_product_catalog'").fetchone()[0] == 1535
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_oem_service_recommendation'").fetchone()[0] == 30
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='ALLISON_APPROVAL_NUMBER'").fetchone()[0] == 119
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='MERCEDES_DTFR_PRODUCT_ID'").fetchone()[0] == 1892
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='MERCEDES_BEVO_PRODUCT_ID'").fetchone()[0] == 1914
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='VOLVO_PART_NUMBER'").fetchone()[0] == 20
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='VOLVO_GENUINE_FLUIDS'").fetchone()[0] == 32
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='MAN_CURRENT_SERVICE_PRODUCTS'").fetchone()[0] == 32
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_INDIA_PRODUCT_FINDER'").fetchone()[0] == 1007
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='FUCHS_US_PRODUCT_FINDER'").fetchone()[0] == 623
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='FUCHS_PRODUCT_UID'").fetchone()[0] == 1641
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
    assert biopreferred_report["source_occurrences"] == 1387
    assert biopreferred_report["duplicate_category_occurrences_merged"] == 495
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
