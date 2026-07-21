#!/usr/bin/env python3
"""Normalize FUCHS Switzerland and reconcile its sparse taxonomy to Germany."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from ingest_fuchs_india_catalog import normalized
from ingest_fuchs_us_catalog import ingest_catalog


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/fuchs-switzerland-products.jsonl"
REPORT = ROOT / "data/fuchs-switzerland-products-report.json"
GERMANY = ROOT / "data/fuchs-germany-products.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    report = ingest_catalog(
        out=OUT,
        report_path=REPORT,
        source_url="https://www.fuchs.com/ch/en/products/service-links/product-finder/",
        imprint_url="https://www.fuchs.com/ch/en/imprint/",
        source_id="FUCHS_SWITZERLAND_PRODUCT_FINDER",
        record_prefix="FUCHS-CH",
        manufacturer="FUCHS LUBRICANTS SWITZERLAND SA",
        market="CH",
        expected_embedded=1466,
        expected_products=1464,
        snapshot_date="2026-07-21",
        rights_review="The official imprint permits use, copying and distribution for informational purposes within an organisation when the copyright notice is retained, and prohibits commercial use. Only attributed factual fields are republished; marketing descriptions are excluded and represented only by SHA-256 evidence hashes.",
    )

    germany_by_name = defaultdict(list)
    for row in read_jsonl(GERMANY):
        germany_by_name[normalized(row["product_name"])].append(row)

    rows = read_jsonl(OUT)
    exact_matches = family_overrides = fallback_rows_resolved = 0
    unique_rows = []
    for row in rows:
        source_family = row["family_code"]
        source_basis = row["classification_basis"]
        matches = germany_by_name[normalized(row["product_name"])]
        reference_families = {match["family_code"] for match in matches}
        row["source_market_classification"] = {
            "family_code": source_family,
            "classification_basis": source_basis,
        }
        if matches and len(reference_families) == 1:
            exact_matches += 1
            reference_family = next(iter(reference_families))
            family_overrides += source_family != reference_family
            fallback_rows_resolved += source_basis == "special_product_fallback"
            row["family_code"] = reference_family
            row["classification_basis"] = (
                "exact_name_family_reconciled_from_fuchs_germany"
                if source_family != reference_family
                else "exact_name_family_confirmed_by_fuchs_germany"
            )
            row["taxonomy_reconciliation"] = {
                "status": "exact_normalized_product_name_unique_reference_family",
                "reference_source_id": "FUCHS_GERMANY_PRODUCT_FINDER",
                "reference_source_record_ids": sorted(match["source_record_id"] for match in matches),
                "family_before": source_family,
                "family_after": reference_family,
            }
        else:
            assert not matches, f"ambiguous Germany taxonomy for {row['product_name']}"
            unique_rows.append(row["source_record_id"])
            row["taxonomy_reconciliation"] = {
                "status": "unique_swiss_product_no_germany_name_match",
                "reference_source_id": "FUCHS_GERMANY_PRODUCT_FINDER",
                "reference_source_record_ids": [],
                "family_before": source_family,
                "family_after": source_family,
            }

    assert exact_matches == 1453
    assert family_overrides == 203
    assert fallback_rows_resolved == 234
    assert len(unique_rows) == 11
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    report.update({
        "products": len(rows),
        "families_before_taxonomy_reconciliation": report["families"],
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "exact_name_matches_to_fuchs_germany": exact_matches,
        "family_overrides_from_unique_germany_reference": family_overrides,
        "special_product_fallback_rows_resolved": fallback_rows_resolved,
        "special_product_fallback_rows_unresolved": sum(row["classification_basis"] == "special_product_fallback" for row in rows),
        "unique_swiss_products_without_germany_name_match": len(unique_rows),
        "unique_swiss_source_record_ids": unique_rows,
        "germany_reference_sha256": hashlib.sha256(GERMANY.read_bytes()).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "taxonomy_reconciliation_rule": "Override the Swiss derived family only when the exact normalized product name has one unique family in the official FUCHS Germany catalog; retain both the original and reconciled classifications.",
    })
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
