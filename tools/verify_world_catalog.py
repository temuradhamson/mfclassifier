#!/usr/bin/env python3
"""Verify reproducibility, provenance and quality gates for the world catalog seed."""

from __future__ import annotations

import hashlib
import gzip
import json
import lzma
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    scania_report = json.loads((ROOT / "data/scania-genuine-oils-report.json").read_text(encoding="utf-8"))
    scania_rows = [json.loads(line) for line in (ROOT / "data/scania-genuine-oils.jsonl").read_text(encoding="utf-8").splitlines() if line]
    brava_report = json.loads((ROOT / "data/brava-official-products-report.json").read_text(encoding="utf-8"))
    brava_rows = [json.loads(line) for line in (ROOT / "data/brava-official-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ceypetco_report = json.loads((ROOT / "data/ceypetco-lubricant-products-report.json").read_text(encoding="utf-8"))
    ceypetco_rows = [json.loads(line) for line in (ROOT / "data/ceypetco-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
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
        "switzerland": ("FUCHS_SWITZERLAND_PRODUCT_FINDER", 1466, 1464, 0, 2, 0, 234, 1434, 30, 1458, 1, {"C": 66, "G": 317, "H": 174, "I": 42, "M": 103, "S": 139, "T": 146, "TF": 471, "U": 6}),
        "korea": ("FUCHS_KOREA_PRODUCT_FINDER", 249, 221, 28, 0, 0, 0, 174, 47, 181, 0, {"G": 12, "H": 11, "I": 3, "M": 67, "S": 16, "T": 34, "TF": 78}),
        "uae": ("FUCHS_UAE_PRODUCT_FINDER", 1073, 965, 97, 6, 5, 0, 949, 16, 964, 0, {"C": 23, "E": 3, "G": 237, "H": 55, "I": 57, "M": 83, "S": 75, "T": 96, "TF": 335, "U": 1}),
        "argentina": ("FUCHS_ARGENTINA_PRODUCT_FINDER", 35, 5, 30, 0, 0, 0, 5, 0, 5, 0, {"G": 4, "TF": 1}),
        "chile": ("FUCHS_CHILE_PRODUCT_FINDER", 549, 496, 49, 4, 0, 0, 484, 12, 494, 0, {"C": 16, "E": 3, "G": 173, "H": 72, "I": 34, "M": 30, "S": 31, "T": 72, "TF": 64, "U": 1}),
        "ukraine": ("FUCHS_UKRAINE_PRODUCT_FINDER", 918, 842, 65, 6, 4, 0, 824, 18, 841, 0, {"C": 15, "E": 3, "G": 204, "H": 31, "I": 49, "M": 88, "S": 72, "T": 92, "TF": 288}),
        "slovakia": ("FUCHS_SLOVAKIA_PRODUCT_FINDER", 1074, 966, 97, 6, 5, 0, 951, 15, 966, 0, {"C": 23, "E": 3, "G": 237, "H": 55, "I": 57, "M": 84, "S": 75, "T": 96, "TF": 335, "U": 1}),
        "slovenia": ("FUCHS_SLOVENIA_PRODUCT_FINDER", 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, {"M": 1}),
        "croatia": ("FUCHS_CROATIA_PRODUCT_FINDER", 1082, 975, 96, 6, 5, 0, 954, 21, 971, 0, {"C": 23, "E": 3, "G": 238, "H": 52, "I": 57, "M": 89, "S": 74, "T": 103, "TF": 335, "U": 1}),
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
    philippines_bps_report = json.loads((ROOT / "data/philippines-bps-brake-fluid-products-report.json").read_text(encoding="utf-8"))
    philippines_bps_rows = [json.loads(line) for line in (ROOT / "data/philippines-bps-brake-fluid-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ghana_gsa_report = json.loads((ROOT / "data/ghana-gsa-certified-lubricant-products-report.json").read_text(encoding="utf-8"))
    ghana_gsa_rows = [json.loads(line) for line in (ROOT / "data/ghana-gsa-certified-lubricant-products.jsonl").read_text(encoding="utf-8").splitlines() if line]
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
        assert hashlib.sha256(plain.read()).digest() == hashlib.sha256(packed.read()).digest()
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert db.execute("SELECT count(*) FROM products").fetchone()[0] == len(lines)
    assert len(lines) == 98137
    assert report["jaso_source_rows"] == jaso_report["rows"] == 3630
    assert report["jaso_unique_oil_codes"] == jaso_report["unique_oil_codes"] == 3629
    assert report["official_filed_registry_rows"] == 3629
    assert report["official_licensed_source_rows"] == licensed_report["rows"] == 3037
    assert report["official_licensed_registry_rows"] == 3037
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
    assert report["official_manufacturer_catalog_rows"] == 5610
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
    assert report["duplicate_decisions"]["review_cross_source_identity"] == 5039
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
    assert report["duplicate_decisions"]["review_fuchs_multi_registry_identity"] == 6652
    assert report["duplicate_decisions"]["keep_separate_fuchs_market_family_conflict"] == 529
    assert report["aichilon_products_matched_to_existing"] == 255
    assert report["aichilon_products_added"] == 60
    assert report["aichilon_rows_excluded"] == 2
    assert db.execute("SELECT count(*) FROM product_offers").fetchone()[0] == report["offers"] == 3953
    assert db.execute("SELECT count(*) FROM product_offers WHERE lifecycle_status IN ('active', 'listed_current_catalog')").fetchone()[0] == report["active_offers"] == 2534
    assert db.execute("SELECT count(*) FROM product_offers WHERE lifecycle_status='listed_current_catalog'").fetchone()[0] == report["current_catalog_listed_offers"] == 1079
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_filed_registry'").fetchone()[0] == 3629
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_licensed_registry'").fetchone()[0] == 3037
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_ecolabel_product_registry'").fetchone()[0] == 127
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_ecolabel_registry'").fetchone()[0] == 33
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_product_conformity_registry'").fetchone()[0] == 40284
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_product_certification_registry'").fetchone()[0] == 1612
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_program_catalog'").fetchone()[0] == 894
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_regulatory_registry'").fetchone()[0] == 30725
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_registry_source_data_issue'").fetchone()[0] == 51
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_government_qualified_product_registry'").fetchone()[0] == 456
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_oem_approval_registry'").fetchone()[0] == 5475
    assert db.execute("SELECT count(*) FROM products WHERE evidence_status='official_manufacturer_product_catalog'").fetchone()[0] == 5610
    assert db.execute("SELECT count(*) FROM products WHERE source_id='BRAVA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 69
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='BRAVA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 69
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='BRAVA_PART_NUMBER'").fetchone()[0] == 94
    assert db.execute("SELECT count(DISTINCT code_value) FROM external_codes WHERE code_system='BRAVA_PART_NUMBER'").fetchone()[0] == 93
    assert db.execute("SELECT count(*) FROM product_offers WHERE source_id='BRAVA_LUBRICANTS_OFFICIAL_CATALOG'").fetchone()[0] == 94
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
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='ANP_BRAZIL_REGISTRATION_NUMBER'").fetchone()[0] == 12664
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='INDONESIA_NPT_REGISTRATION_NUMBER'").fetchone()[0] == 12575
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='INDONESIA_NPT_LUBRICANT_REGISTRY'").fetchone()[0] == 12626
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='source_registration_number_missing'").fetchone()[0] == 51
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='THAILAND_DOEB_LUBRICANT_REGISTRY'").fetchone()[0] == 5486
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='THAILAND_DOEB_REGISTRATION_NUMBER'").fetchone()[0] == 6213
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='thailand_doeb_registration_number_collision'").fetchone()[0] == 6
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='thailand_doeb_nonstandard_sae_notation'").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='DLA_QPD_FSC_9150'").fetchone()[0] == 431
    assert db.execute("SELECT count(*) FROM product_sources WHERE source_id='DLA_QPD_FSC_6850_LUBRICANT_SCOPE'").fetchone()[0] == 25
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
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='DLA_QPL_NUMBER'").fetchone()[0] == 457
    assert db.execute("SELECT count(*) FROM quality_issues WHERE issue_code='dla_qpd_lifecycle_restriction'").fetchone()[0] == 93
    assert db.execute("SELECT count(*) FROM external_codes WHERE code_system='FUCHS_PRODUCT_UID'").fetchone()[0] == 22254
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
    assert epa_chemexpo_report["source_category_product_occurrences"] == 10019
    assert epa_chemexpo_report["kept_product_occurrences"] == 7217
    assert epa_chemexpo_report["excluded_product_occurrences"] == 2802
    assert len(epa_chemexpo_rows) == 5714
    assert report["epa_chemexpo_products_matched_to_existing"] == 268
    assert report["epa_chemexpo_products_added"] == 5446
    assert epa_chemexpo_report["kept_product_occurrences"] + epa_chemexpo_report["excluded_product_occurrences"] == 10019
    assert epa_chemexpo_report["within_source_occurrences_merged"] == epa_chemexpo_report["kept_product_occurrences"] - len(epa_chemexpo_rows)
    assert epa_chemexpo_report["licence"] == "CC0"
    assert epa_chemexpo_report["cpdat_release"] == "4.1 (May 2025)"
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
        assert source_report["placeholder_rows_excluded"] == (1 if slug == "ukraine" else 0)
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
