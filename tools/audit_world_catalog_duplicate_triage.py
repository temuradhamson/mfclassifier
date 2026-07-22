#!/usr/bin/env python3
"""Classify unresolved duplicate-review pairs without inventing product identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import sqlite3
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "world-catalog.sqlite3.xz"
DEFAULT_BUILD_REPORT = ROOT / "data" / "world-catalog-report.json"
DEFAULT_REPORT = ROOT / "data" / "world-catalog-duplicate-triage.json"
DEFAULT_MARKDOWN = ROOT / "deliverables" / "World_catalog_duplicate_triage_2026-07-22.md"

SIGNATURE_FIELDS = {
    "M": ("sae_engine", "api", "acea", "ilsac", "jaso", "jaso_family_detail", "licensed_standard", "oem_approvals"),
    "T": ("sae_gear", "sae_engine", "iso_vg", "api_gl", "atf_specifications", "dexron", "licensed_standard", "oem_approvals"),
    "G": ("nlgi", "grease_class", "licensed_standard", "standards", "oem_approvals"),
    "H": ("iso_vg", "din", "iso_6743_hm", "iso_6743_hv", "licensed_standard", "oem_approvals"),
    "I": ("iso_vg", "din", "licensed_standard", "standards", "oem_approvals"),
    "C": ("iso_vg", "din", "licensed_standard", "standards", "oem_approvals"),
    "U": ("iso_vg", "din", "licensed_standard", "standards", "oem_approvals"),
    "E": ("standards", "source_specifications", "licensed_standard", "oem_approvals"),
    "TF": (
        "brake_fluid_class", "brake_fluid_classes", "brake_fluid_class_source_reported",
        "brake_fluid_dot_source_reported", "brake_fluid_hzy_source_reported", "coolant_class",
        "coolant_class_source_reported", "coolant_freezing_point_source_reported",
        "washer_fluid_class_source_reported", "washer_fluid_freezing_point_source_reported",
        "urea_class_source_reported", "coolant_chemistry", "product_form", "licensed_standard",
        "oem_approvals",
    ),
    "S": ("licensed_standard", "standards", "source_specifications", "application", "oem_approvals"),
}

# Only fields whose disjoint values normally identify different physical grades/classes.
# Performance approvals are additive and therefore are not conflicts by themselves.
EXCLUSIVE_FIELDS = {
    "M": ("sae_engine", "jaso_family_detail"),
    "T": ("sae_gear", "sae_engine", "iso_vg"),
    "G": ("nlgi", "grease_class"),
    "H": ("iso_vg",), "I": ("iso_vg",), "C": ("iso_vg",), "U": ("iso_vg",),
    "E": (),
    "TF": (
        "brake_fluid_class", "brake_fluid_classes", "brake_fluid_class_source_reported",
        "brake_fluid_dot_source_reported", "brake_fluid_hzy_source_reported",
        "coolant_class", "coolant_class_source_reported", "coolant_freezing_point_source_reported",
        "washer_fluid_class_source_reported", "washer_fluid_freezing_point_source_reported",
        "urea_class_source_reported", "product_form",
    ),
    "S": (),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fmt(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def signature(specs: dict[str, set[str]], family: str) -> tuple:
    return tuple(
        (field, tuple(sorted(specs.get(field, ()))))
        for field in SIGNATURE_FIELDS[family]
        if specs.get(field)
    )


def audit(db: sqlite3.Connection, database: Path, build_report: dict) -> dict:
    db.row_factory = sqlite3.Row
    specs: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in db.execute("SELECT product_id, spec_type, spec_value FROM specifications"):
        specs[row["product_id"]][row["spec_type"]].add(row["spec_value"])
    codes: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in db.execute("SELECT product_id, code_system, code_value FROM external_codes"):
        codes[row["product_id"]].add((row["code_system"], row["code_value"]))
    incomplete = {
        row[0] for row in db.execute(
            "SELECT product_id FROM quality_issues WHERE issue_code='professional_key_incomplete'"
        )
    }
    products = {
        row["product_id"]: row for row in db.execute(
            "SELECT product_id, product_name_normalized, family_code, source_id FROM products"
        )
    }

    status_counts = Counter()
    decision_status_counts = Counter()
    family_status_counts = Counter()
    shared_code_systems = Counter()
    examples = defaultdict(list)
    reviewed_products = set()
    review_pairs = list(db.execute(
        "SELECT product_id_a, product_id_b, decision, reason FROM duplicate_decisions WHERE decision LIKE 'review_%'"
    ))
    for row in review_pairs:
        left_id, right_id = row["product_id_a"], row["product_id_b"]
        left, right = products[left_id], products[right_id]
        family = left["family_code"]
        reviewed_products.update((left_id, right_id))
        conflicts = []
        matches = []
        for field in SIGNATURE_FIELDS[family]:
            left_values = specs[left_id].get(field, set())
            right_values = specs[right_id].get(field, set())
            if left_values and right_values and left_values & right_values:
                matches.append(field)
        for field in EXCLUSIVE_FIELDS[family]:
            left_values = specs[left_id].get(field, set())
            right_values = specs[right_id].get(field, set())
            if left_values and right_values and left_values.isdisjoint(right_values):
                conflicts.append(field)
        left_signature = signature(specs[left_id], family)
        right_signature = signature(specs[right_id], family)
        names_equal = left["product_name_normalized"] == right["product_name_normalized"]
        both_complete = left_id not in incomplete and right_id not in incomplete
        if conflicts:
            status = "explicit_exclusive_specification_conflict"
        elif both_complete and names_equal and left_signature and left_signature == right_signature:
            status = "complete_exact_signature_candidate"
        elif matches:
            status = "compatible_partial_specification_review"
        else:
            status = "insufficient_comparable_evidence"
        status_counts[status] += 1
        decision_status_counts[(row["decision"], status)] += 1
        family_status_counts[(family, status)] += 1
        shared_codes = codes[left_id] & codes[right_id]
        for system, _ in shared_codes:
            shared_code_systems[system] += 1
        if len(examples[status]) < 5:
            examples[status].append({
                "product_id_a": left_id,
                "product_id_b": right_id,
                "family_code": family,
                "source_id_a": left["source_id"],
                "source_id_b": right["source_id"],
                "matching_fields": matches,
                "conflicting_exclusive_fields": conflicts,
                "shared_code_systems": sorted({system for system, _ in shared_codes}),
            })

    return {
        "status": "offline_duplicate_triage_no_unproven_auto_merge",
        "snapshot_date": "2026-07-22",
        "compressed_database_sha256": sha256(database),
        "canonical_products": build_report["canonical_rows"],
        "review_pairs": len(review_pairs),
        "distinct_products_in_review": len(reviewed_products),
        "self_pairs_remaining": sum(row["product_id_a"] == row["product_id_b"] for row in review_pairs),
        "already_applied_safe_merges": {
            "gm_dual_standard_same_license_manufacturer_name_family_viscosity": build_report["gm_dual_standard_license_rows_merged"],
            "canonical_input_rows_collapsed": build_report["canonical_input_rows_collapsed"],
        },
        "retained_source_code_collisions": {
            "gm_same_license_different_product_names": build_report["gm_license_code_name_collisions_retained"],
        },
        "resolved_keep_separate_pairs": {
            "explicit_professional_signature_conflict": build_report["duplicate_decisions"].get(
                "keep_separate_professional_signature_conflict", 0
            ),
            "conflicting_fields": build_report.get("duplicate_review_conflicts_resolved", {}),
        },
        "duplicate_decision_rows_collapsed": {
            "by_decision_combination": build_report.get("duplicate_decision_pair_rows_collapsed", {}),
            "total_extra_rows_removed": sum(build_report.get("duplicate_decision_pair_rows_collapsed", {}).values()),
        },
        "triage_status_counts": dict(sorted(status_counts.items())),
        "by_decision_and_status": [
            {"decision": decision, "triage_status": status, "pairs": count}
            for (decision, status), count in sorted(decision_status_counts.items())
        ],
        "by_family_and_status": [
            {"family_code": family, "triage_status": status, "pairs": count}
            for (family, status), count in sorted(family_status_counts.items())
        ],
        "shared_code_system_counts": dict(sorted(shared_code_systems.items())),
        "examples": dict(sorted(examples.items())),
        "policy": {
            "explicit_conflict": "Keep separate; disjoint exclusive grade/class facts outweigh name similarity.",
            "exact_signature_candidate": "High-priority review, not automatic identity proof: formulation revision, market and lifecycle can still differ.",
            "partial": "Require a common official product code or cross-reference plus missing TDS/PDS fields.",
            "insufficient": "Do not merge from name/company similarity alone.",
            "registration_code": "A shared code is interpreted by system semantics; ANP registration numbers are not unique product-grade identifiers.",
        },
    }


def markdown(report: dict) -> str:
    lines = [
        "# Офлайн-триаж дублей мирового каталога — 22.07.2026",
        "",
        "Новые источники не запрашивались. Пары анализируются только по уже сохранённым нормализованным полям, кодам и provenance.",
        "",
        "## Результат",
        "",
        f"- Канонические карточки после доказанных merge: **{fmt(report['canonical_products'])}**.",
        f"- Оставшиеся review-пары: {fmt(report['review_pairs'])}; затронуто {fmt(report['distinct_products_in_review'])} карточек.",
        f"- Self-pairs в очереди: {report['self_pairs_remaining']}.",
        f"- Доказательно объединены одинаковые GM dexos2/dexosD строки: {report['already_applied_safe_merges']['gm_dual_standard_same_license_manufacturer_name_family_viscosity']}.",
        f"- Сохранена несхлопнутой GM-коллизия одного license code с разными названиями: {report['retained_source_code_collisions']['gm_same_license_different_product_names']}.",
        f"- Доказательно переведено в `keep_separate` по конфликтующим профессиональным полям — пар: {fmt(report['resolved_keep_separate_pairs']['explicit_professional_signature_conflict'])}.",
        f"- Повторных строк решений для тех же пар удалено: {fmt(report['duplicate_decision_rows_collapsed']['total_extra_rows_removed'])}; все причины объединены в единственной строке пары.",
        "",
        "## Классы оставшейся очереди",
        "",
        "| Статус | Пар | Действие |",
        "|---|---:|---|",
    ]
    actions = {
        "explicit_exclusive_specification_conflict": "Оставить раздельно",
        "complete_exact_signature_candidate": "Приоритетная ручная/кодовая сверка",
        "compatible_partial_specification_review": "Получить недостающий TDS/PDS или официальный cross-reference",
        "insufficient_comparable_evidence": "Не объединять по названию",
    }
    for status, count in report["triage_status_counts"].items():
        lines.append(f"| `{status}` | {fmt(count)} | {actions[status]} |")
    lines.extend([
        "",
        "Полная профессиональная сигнатура всё равно не является автоматическим доказательством одной формулы: возможны региональная рецептура, новая редакция или разные lifecycle-срезы. Поэтому оставшиеся пары не схлопываются без уникального кода с подходящей семантикой либо прямого официального cross-reference.",
        "",
        "## Следующий офлайн-порядок",
        "",
        "1. Сначала закрывать exact-signature candidates, где есть официальный уникальный manufacturer product ID.",
        "2. Конфликтующие SAE/ISO VG/NLGI/классы сразу фиксировать как `keep_separate`.",
        "3. Partial-пары сопоставлять только после получения недостающего профессионального поля.",
        "4. ANP registration number не использовать как уникальный product-grade key: один номер может включать несколько исполнений.",
        "",
        f"SHA-256 проверенной SQLite.xz: `{report['compressed_database_sha256']}`.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--build-report", type=Path, default=DEFAULT_BUILD_REPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    build_report = json.loads(args.build_report.read_text(encoding="utf-8"))
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as temp:
        with lzma.open(args.database, "rb") as source:
            while chunk := source.read(1024 * 1024):
                temp.write(chunk)
        temp.flush()
        db = sqlite3.connect(temp.name)
        result = audit(db, args.database, build_report)
        db.close()
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({
        "status": "ok", "canonical_products": result["canonical_products"],
        "review_pairs": result["review_pairs"], "self_pairs": result["self_pairs_remaining"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
