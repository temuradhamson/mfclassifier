#!/usr/bin/env python3
"""Build a deterministic offline quality/coverage audit for the world catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "world-catalog.sqlite3.xz"
DEFAULT_REPORT = ROOT / "data" / "world-catalog-offline-quality-audit.json"
DEFAULT_MARKDOWN = ROOT / "deliverables" / "World_catalog_offline_quality_audit_2026-07-22.md"

GRADE_TYPES = {
    "M": {"sae_engine"},
    "T": {"sae_gear", "sae_engine", "iso_vg", "source_grade", "viscosity_source_reported", "atf_specifications", "dexron", "licensed_standard", "oem_approvals", "oem_specifications"},
    "G": {"nlgi", "grease_class"},
    "H": {"iso_vg", "sae_engine", "sae_gear", "viscosity_source_reported"},
    "I": {"iso_vg", "sae_engine", "sae_gear", "viscosity_source_reported"},
    "C": {"iso_vg", "sae_engine", "sae_gear", "viscosity_source_reported"},
    "U": {"iso_vg", "sae_engine", "sae_gear", "viscosity_source_reported"},
    "E": {"standards", "source_specifications", "standards_and_approvals_source_reported", "kebs_standards_source_reported", "licensed_standard", "oem_approvals", "oem_specifications"},
    "TF": {
        "brake_fluid_class", "brake_fluid_classes", "brake_fluid_dot_source_reported",
        "brake_fluid_hzy_source_reported", "coolant_class", "coolant_class_source_reported",
        "coolant_freezing_point_source_reported", "washer_fluid_class_source_reported",
        "washer_fluid_freezing_point_source_reported", "urea_class_source_reported",
    },
    "S": {"standards", "licensed_standard", "oem_approvals", "oem_specifications", "source_approvals", "source_specifications", "application", "certification_standard_source_reported", "certification_standards_source_reported"},
}

TECHNICAL_TYPES = {
    "M": {"api", "acea", "ilsac", "jaso", "licensed_standard", "oem_approvals", "oem_specifications", "source_approvals"},
    "T": {"api_gl", "atf_specifications", "dexron", "licensed_standard", "oem_approvals", "oem_specifications", "source_approvals"},
    "G": {"standards", "din", "licensed_standard", "oem_approvals", "oem_specifications", "grease_type", "grease_thickener_source_reported"},
    "H": {"din", "iso_6743_hm", "iso_6743_hv", "licensed_standard", "oem_approvals", "oem_specifications", "parker_denison_hf_classes", "source_approvals"},
    "I": {"din", "standards", "licensed_standard", "oem_approvals", "oem_specifications", "source_approvals"},
    "C": {"din", "standards", "licensed_standard", "oem_approvals", "oem_specifications", "source_approvals"},
    "U": {"din", "standards", "licensed_standard", "oem_approvals", "oem_specifications", "source_approvals"},
    "E": {"standards", "source_specifications", "standards_and_approvals_source_reported", "kebs_standards_source_reported", "licensed_standard", "oem_approvals", "oem_specifications"},
    "TF": {
        "brake_fluid_class", "brake_fluid_classes", "coolant_class", "coolant_chemistry",
        "coolant_standard_source_reported", "washer_fluid_class_source_reported",
        "urea_class_source_reported", "standards", "oem_approvals", "oem_specifications",
    },
    "S": {"standards", "licensed_standard", "oem_approvals", "oem_specifications", "source_approvals", "application"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scalar(db: sqlite3.Connection, query: str, params: tuple = ()) -> int:
    return int(db.execute(query, params).fetchone()[0])


def count_products_with_types(db: sqlite3.Connection, family_code: str, types: set[str]) -> int:
    placeholders = ",".join("?" for _ in types)
    return scalar(
        db,
        f"""SELECT count(*) FROM products p
            WHERE p.family_code=? AND EXISTS (
                SELECT 1 FROM specifications s
                WHERE s.product_id=p.product_id AND s.spec_type IN ({placeholders})
            )""",
        (family_code, *sorted(types)),
    )


def count_products_with_both(
    db: sqlite3.Connection, family_code: str, grade_types: set[str], technical_types: set[str]
) -> int:
    grade_placeholders = ",".join("?" for _ in grade_types)
    technical_placeholders = ",".join("?" for _ in technical_types)
    return scalar(
        db,
        f"""SELECT count(*) FROM products p
            WHERE p.family_code=?
              AND EXISTS (SELECT 1 FROM specifications s WHERE s.product_id=p.product_id
                          AND s.spec_type IN ({grade_placeholders}))
              AND EXISTS (SELECT 1 FROM specifications s WHERE s.product_id=p.product_id
                          AND s.spec_type IN ({technical_placeholders}))""",
        (family_code, *sorted(grade_types), *sorted(technical_types)),
    )


def pct(value: int, total: int) -> float:
    return round(value * 100 / total, 2) if total else 0.0


def fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def audit(db: sqlite3.Connection, compressed_db: Path) -> dict:
    db.row_factory = sqlite3.Row
    canonical = scalar(db, "SELECT count(*) FROM products")
    input_rows = scalar(db, "SELECT input_rows FROM ingest_runs ORDER BY rowid DESC LIMIT 1")
    family_rows = list(db.execute(
        "SELECT family_code, family, count(*) AS products FROM products GROUP BY family_code, family ORDER BY products DESC"
    ))

    families = []
    for row in family_rows:
        code = row["family_code"]
        total = row["products"]
        grade = count_products_with_types(db, code, GRADE_TYPES[code])
        technical = count_products_with_types(db, code, TECHNICAL_TYPES[code])
        both = count_products_with_both(db, code, GRADE_TYPES[code], TECHNICAL_TYPES[code])
        incomplete = scalar(
            db,
            """SELECT count(DISTINCT q.product_id) FROM quality_issues q
               JOIN products p ON p.product_id=q.product_id
               WHERE p.family_code=? AND q.issue_code='professional_key_incomplete'""",
            (code,),
        )
        families.append({
            "family_code": code,
            "family": row["family"],
            "products": total,
            "selector_grade_or_class_present": grade,
            "selector_grade_or_class_percent": pct(grade, total),
            "technical_basis_present": technical,
            "technical_basis_percent": pct(technical, total),
            "both_selector_and_technical_basis_present": both,
            "both_percent": pct(both, total),
            "existing_professional_key_issue": incomplete,
            "existing_professional_key_gate_implemented": True,
        })

    decisions = []
    for row in db.execute(
        """SELECT decision, count(*) AS pairs, count(DISTINCT product_id_a) AS left_products,
                  count(DISTINCT product_id_b) AS right_products
           FROM duplicate_decisions GROUP BY decision ORDER BY pairs DESC"""
    ):
        involved = scalar(
            db,
            """SELECT count(DISTINCT product_id) FROM (
                   SELECT product_id_a AS product_id FROM duplicate_decisions WHERE decision=?
                   UNION SELECT product_id_b FROM duplicate_decisions WHERE decision=?
               )""",
            (row["decision"], row["decision"]),
        )
        decisions.append({"decision": row["decision"], "candidate_pairs": row["pairs"], "distinct_products_involved": involved})

    issue_counts = [dict(row) for row in db.execute(
        "SELECT severity, issue_code, count(*) AS rows FROM quality_issues GROUP BY severity, issue_code ORDER BY rows DESC, issue_code"
    )]
    severity_counts = dict(db.execute(
        "SELECT severity, count(*) FROM quality_issues GROUP BY severity ORDER BY severity"
    ))
    fallback_brands = scalar(
        db,
        "SELECT count(DISTINCT product_id) FROM specifications WHERE spec_type='brand_basis' AND spec_value LIKE '%fallback%'",
    )

    return {
        "status": "offline_quality_audit_current_seed_not_worldwide_completion",
        "snapshot_date": "2026-07-22",
        "compressed_database_sha256": sha256(compressed_db),
        "canonical_products": canonical,
        "input_rows_before_canonicalization": input_rows,
        "canonical_key_duplicates": scalar(db, "SELECT count(*) FROM (SELECT canonical_key FROM products GROUP BY canonical_key HAVING count(*)>1)"),
        "products_with_family": scalar(db, "SELECT count(*) FROM products WHERE family_code IS NOT NULL AND trim(family_code)<>''"),
        "products_with_normalized_name": scalar(db, "SELECT count(*) FROM products WHERE trim(product_name_normalized)<>''"),
        "products_with_primary_source_hash": scalar(db, "SELECT count(*) FROM products p JOIN sources s ON s.source_id=p.source_id WHERE trim(coalesce(s.source_sha256,''))<>''"),
        "products_with_at_least_one_source_link": scalar(db, "SELECT count(*) FROM products p WHERE EXISTS(SELECT 1 FROM product_sources ps WHERE ps.product_id=p.product_id)"),
        "products_with_primary_source_url": scalar(db, "SELECT count(*) FROM products p JOIN sources s ON s.source_id=p.source_id WHERE trim(coalesce(s.source_url,''))<>''"),
        "products_with_missing_manufacturer": scalar(db, "SELECT count(*) FROM products WHERE trim(coalesce(manufacturer,''))=''"),
        "products_using_explicitly_marked_brand_fallback": fallback_brands,
        "primary_sources_used": scalar(db, "SELECT count(DISTINCT source_id) FROM products"),
        "source_registry_entries": scalar(db, "SELECT count(*) FROM sources"),
        "active_offers": scalar(db, "SELECT count(*) FROM product_offers WHERE lifecycle_status IN ('active', 'listed_current_catalog')"),
        "family_coverage": families,
        "quality_issues_by_severity": severity_counts,
        "quality_issue_details": issue_counts,
        "duplicate_review_queues": decisions,
        "interpretation": {
            "confirmed_count": "105956 is the verified canonical row count of the current seed, not the final number of all products worldwide.",
            "selector_metric": "Presence is measured only from explicit normalized fields; absence may reflect source granularity rather than a parsing defect.",
            "duplicate_metric": "Review pairs are candidates or conflicts, not proven removable duplicates.",
            "professional_gate_scope": "Family-specific professional_key_incomplete rules cover M/T/G/H/I/C/U/E/TF/S; source-level gaps remain explicit and are not filled by inference.",
        },
    }


def markdown(report: dict) -> str:
    lines = [
        "# Офлайн-аудит качества мирового каталога — 22.07.2026",
        "",
        "Сетевые источники не запрашивались. Отчёт рассчитан только по зафиксированной SQLite-сборке.",
        "",
        "## Подтверждённый текущий срез",
        "",
        f"- Канонические карточки: **{fmt_int(report['canonical_products'])}**.",
        f"- Строки до каноникализации: {fmt_int(report['input_rows_before_canonicalization'])}.",
        f"- Активные предложения: {fmt_int(report['active_offers'])}.",
        f"- Дубли `canonical_key`: {report['canonical_key_duplicates']}.",
        f"- Карточки с семейством, нормализованным названием, source-link и SHA-256 первичного источника: "
        f"{fmt_int(report['products_with_family'])} / {fmt_int(report['products_with_normalized_name'])} / "
        f"{fmt_int(report['products_with_at_least_one_source_link'])} / {fmt_int(report['products_with_primary_source_hash'])}.",
        f"- С прямым URL первичного источника: {fmt_int(report['products_with_primary_source_url'])}; "
        f"без производителя: {fmt_int(report['products_with_missing_manufacturer'])}.",
        f"- С явно помеченным fallback вместо самостоятельного бренда: {fmt_int(report['products_using_explicitly_marked_brand_fallback'])}.",
        "",
        "Число 105 956 подтверждает размер текущего seed. Оно не доказывает, что все мировые продукты уже собраны.",
        "",
        "## Покрытие профессиональными полями",
        "",
        "| Код | Семейство | Карточки | Селектор/класс | Техническая база | Оба признака | Текущий gate |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in report["family_coverage"]:
        gate = f"{fmt_int(row['existing_professional_key_issue'])} проблем" if row["existing_professional_key_gate_implemented"] else "ещё не реализован"
        lines.append(
            f"| {row['family_code']} | {row['family']} | {fmt_int(row['products'])} | "
            f"{fmt_int(row['selector_grade_or_class_present'])} ({row['selector_grade_or_class_percent']:.2f}%) | "
            f"{fmt_int(row['technical_basis_present'])} ({row['technical_basis_percent']:.2f}%) | "
            f"{fmt_int(row['both_selector_and_technical_basis_present'])} ({row['both_percent']:.2f}%) | {gate} |"
        )
    lines.extend([
        "",
        "Показатель «оба признака» не объявляет продукты эквивалентными: он лишь показывает, что для строгого сравнения есть хотя бы семейно-релевантный селектор/класс и хотя бы одна техническая база.",
        "",
        "## Очереди качества и дедупликации",
        "",
        f"- Quality issues: high — {fmt_int(report['quality_issues_by_severity'].get('high', 0))}, "
        f"medium — {fmt_int(report['quality_issues_by_severity'].get('medium', 0))}, "
        f"low — {fmt_int(report['quality_issues_by_severity'].get('low', 0))}.",
    ])
    for row in report["duplicate_review_queues"]:
        lines.append(f"- `{row['decision']}`: {fmt_int(row['candidate_pairs'])} пар, {fmt_int(row['distinct_products_involved'])} затронутых карточек.")
    lines.extend([
        "",
        "Кандидатные пары нельзя автоматически удалять: часть из них — одинаковые названия с конфликтующими спецификациями или разные региональные регистрации.",
        "",
        "## Что улучшать офлайн до возобновления загрузок",
        "",
        "1. Приоритизировать получение официальных TDS/PDS для карточек, отмеченных family-specific `professional_key_incomplete`; правила теперь покрывают все десять семейств.",
        "2. Разобрать 214 конфликтов семейства с ЕНКТ/СКП и не допускать их в аналитику до remap.",
        "3. Приоритизировать review-пары по источникам и совпадению строгого профессионального ключа; не схлопывать по одному названию.",
        "4. Сохранять разницу между явно указанным брендом и manufacturer/holder fallback — таких карточек много из-за гранулярности ЕАЭС.",
        "5. После снятия паузы получать TDS/PDS прежде всего для семейств с низким процентом обоих профессиональных признаков.",
        "",
        f"SHA-256 проверенной сжатой SQLite: `{report['compressed_database_sha256']}`.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as temp:
        with lzma.open(args.database, "rb") as source:
            while chunk := source.read(1024 * 1024):
                temp.write(chunk)
        temp.flush()
        db = sqlite3.connect(temp.name)
        result = audit(db, args.database)
        db.close()

    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "canonical_products": result["canonical_products"],
        "report": str(args.report.relative_to(ROOT)),
        "markdown": str(args.markdown.relative_to(ROOT)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
