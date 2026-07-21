#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS US finder."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from ingest_fuchs_india_catalog import (
    classify_family,
    extract_technical,
    factual_lines,
    fetch,
    flatten_groups,
    is_series,
    is_non_product_placeholder,
    normalized,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fuchs-us-products.jsonl"
REPORT = ROOT / "data" / "fuchs-us-products-report.json"
SOURCE_URL = "https://www.fuchs.com/us/en/products/service-links/product-finder/"
IMPRINT_URL = "https://www.fuchs.com/us/en/imprint/"
SNAPSHOT_DATE = "2026-07-20"


def ingest_catalog(
    *, out: Path, report_path: Path, source_url: str, imprint_url: str,
    source_id: str, record_prefix: str, manufacturer: str, market: str,
    expected_embedded: int, expected_products: int,
) -> dict:
    payload = fetch(source_url)
    imprint_payload = fetch(imprint_url)
    page = payload.decode("utf-8", errors="replace")
    match = re.search(r"var FuchsProductRawData = (\{.*?\});\s*</script>", page, re.S)
    assert match, "embedded FuchsProductRawData not found"
    source = json.loads(match.group(1))
    assert len(source["products"]) == expected_embedded
    group_index = flatten_groups(source["productGroups"])
    brand_index = {row["uid"]: row["title"] for row in source["brands"]}
    industry_index = {row["uid"]: row["title"] for row in source["industries"]}

    excluded = []
    grouped = defaultdict(list)
    for row in source["products"]:
        if is_series(row["title"]):
            excluded.append({"uid": row["uid"], "title": row["title"], "reason": "series_not_specific_product_grade"})
            continue
        if is_non_product_placeholder(row["title"]):
            excluded.append({"uid": row["uid"], "title": row["title"], "reason": "non_product_test_placeholder"})
            continue
        grouped[normalized(row["title"])].append(row)

    records = []
    duplicate_occurrences_merged = 0
    for rows in grouped.values():
        rows = sorted(rows, key=lambda row: (-int(row.get("quality") or 0), row["uid"]))
        primary = rows[0]
        uids = sorted({row["uid"] for row in rows})
        duplicate_occurrences_merged += len(rows) - 1
        group_uids = sorted({uid for row in rows for uid in row.get("productGroups", []) + row.get("productGroupRootline", [])})
        paths = sorted({tuple(group_index[uid]["path"]) for uid in group_uids if uid in group_index})
        brands = sorted({brand_index[uid] for row in rows for uid in row.get("brands", []) if uid in brand_index})
        industries = sorted({industry_index[uid] for row in rows for uid in row.get("industries", []) if uid in industry_index})
        specifications = sorted({line for row in rows for line in factual_lines(row.get("specifications", ""))})
        approvals = sorted({line for row in rows for line in factual_lines(row.get("approvals", ""))})
        recommendations = sorted({line for row in rows for line in factual_lines(row.get("recommendations", ""))})
        source_text = " ".join(
            [primary["title"]]
            + [row.get("subtitle", "") + " " + row.get("description", "") + " " + row.get("components", "") for row in rows]
            + specifications + approvals + recommendations
        )
        family, basis = classify_family(primary["title"], [list(path) for path in paths], source_text)
        if not family:
            for row in rows:
                excluded.append({"uid": row["uid"], "title": row["title"], "reason": basis})
            continue
        technical = extract_technical(source_text, family)
        records.append({
            "source_id": source_id,
            "source_record_id": f"{record_prefix}-{uids[0]}",
            "source_uids": uids,
            "manufacturer": manufacturer,
            "brand": brands[0] if brands else "FUCHS",
            "brand_lines": brands,
            "product_name": primary["title"].strip(),
            "family_code": family,
            "classification_basis": basis,
            "market": market,
            "product_group_paths": [list(path) for path in paths],
            "industries": industries,
            "specifications": specifications,
            "approvals": approvals,
            "fuchs_recommendations": recommendations,
            "technical": technical,
            "flags": {
                "eu_ecolabel": any(bool(row.get("isEcolabel")) for row in rows),
                "bluev": any(bool(row.get("isBluev")) for row in rows),
                "special_applications": any(bool(row.get("isSpecialApplications")) for row in rows),
            },
            "source_product_dates": sorted({row.get("date", "") for row in rows if row.get("date")}),
            "source_description_sha256": sorted({hashlib.sha256((row.get("description") or "").encode()).hexdigest() for row in rows}),
            "source_urls": ["https://www.fuchs.com" + row["url"] for row in rows],
            "source_url": source_url,
            "snapshot_date": SNAPSHOT_DATE,
            "grain_warning": "compound_designation_review" if "/" in primary["title"] else "",
        })

    records.sort(key=lambda row: (normalized(row["product_name"]), row["source_record_id"]))
    assert len(records) == expected_products
    assert len({row["source_record_id"] for row in records}) == len(records)
    assert len({normalized(row["product_name"]) for row in records}) == len(records)
    out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": source_id,
        "source_url": source_url,
        "imprint_url": imprint_url,
        "source_html_sha256": hashlib.sha256(payload).hexdigest(),
        "imprint_html_sha256": hashlib.sha256(imprint_payload).hexdigest(),
        "embedded_source_rows": len(source["products"]),
        "products": len(records),
        "source_series_rows_excluded": sum(row["reason"] == "series_not_specific_product_grade" for row in excluded),
        "equipment_rows_excluded": sum(row["reason"] == "excluded_equipment" for row in excluded),
        "placeholder_rows_excluded": sum(row["reason"] == "non_product_test_placeholder" for row in excluded),
        "duplicate_source_occurrences_merged": duplicate_occurrences_merged,
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "brand_lines": len({brand for row in records for brand in row["brand_lines"]}),
        "compound_designation_review_rows": sum(bool(row["grain_warning"]) for row in records),
        "classification_basis": dict(sorted(Counter(row["classification_basis"] for row in records).items())),
        "normalized_output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "rights_review": "Only factual fields are republished with attribution. Marketing descriptions are excluded and represented only by SHA-256 evidence hashes; the applicable imprint limits copying of documentation for commercial use.",
        "publication_scope": "Product identity, region, group, specifications, approvals, recommendations and derived technical fields; no marketing descriptions or page layout.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    report = ingest_catalog(
        out=OUT, report_path=REPORT, source_url=SOURCE_URL, imprint_url=IMPRINT_URL,
        source_id="FUCHS_US_PRODUCT_FINDER", record_prefix="FUCHS-US",
        manufacturer="FUCHS LUBRICANTS CO.", market="US",
        expected_embedded=686, expected_products=623,
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
