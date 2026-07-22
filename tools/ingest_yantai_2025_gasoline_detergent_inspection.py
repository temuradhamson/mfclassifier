#!/usr/bin/env python3
"""Normalize Yantai's 2025 gasoline-detergent inspection observations."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/yantai-2025-gasoline-detergent-inspection.jsonl"
REPORT = ROOT / "data/yantai-2025-gasoline-detergent-inspection-report.json"
SNAPSHOT_DATE = "2026-07-22"
SOURCE_ID = "YANTAI_CHINA_2025_GASOLINE_DETERGENT_INSPECTION"
SOURCE_URL = "https://www.yantai.gov.cn/col/col43304/art/2026/art_4583d515ea8241c287923bc9ca6480d8.html"
RIGHTS_URL = "https://www.yantai.gov.cn/"
REPORT_DATE = "2026-04-15"
SOURCE_HTML_SHA256 = "b87f4e6ff53c591878ea114f219b63b0a350c1a0ecd4be734ffe238d87000eb0"
EXPECTED_HEADER = [
    "序号", "产品名称", "被抽样企业名称", "被抽样企业统一社会信用代码",
    "标称生产单位", "商标", "规格型号", "生产日期/批号", "综合判定",
    "不合格项目（名称）", "抽样领域", "抽样日期", "检验/判定依据", "检验单位",
]


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"", "-", "—", "——", "/", "-/-"} else value


class TableRows(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.row is not None and self.cell is not None:
            self.row.append(clean("".join(self.cell)))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
            self.cell = None


def fetch() -> bytes:
    request = urllib.request.Request(SOURCE_URL, headers={
        "User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0",
    })
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != SOURCE_HTML_SHA256:
        raise RuntimeError(f"Yantai HTML changed: expected {SOURCE_HTML_SHA256}, received {digest}")
    return payload


def source_rows(payload: bytes) -> tuple[list[dict], int]:
    text = payload.decode("utf-8-sig")
    if '<meta name="PubDate" content="2026-04-15 09:26">' not in text:
        raise RuntimeError("Unexpected Yantai publication date")
    parser = TableRows()
    parser.feed(text)
    headers = [index for index, row in enumerate(parser.rows) if row == EXPECTED_HEADER]
    if len(headers) != 1:
        raise RuntimeError(f"Expected one Yantai inspection header, received {len(headers)}")
    start = headers[0] + 1
    all_rows = []
    for row in parser.rows[start:]:
        if len(row) != 14 or not row[0].isdigit():
            if all_rows:
                break
            continue
        all_rows.append(row)
    if len(all_rows) != 350 or [int(row[0]) for row in all_rows] != list(range(1, 351)):
        raise RuntimeError(f"Expected sequential Yantai rows 1..350, received {len(all_rows)}")
    relevant = []
    for values in all_rows:
        if values[1] != "车用汽油清净剂":
            continue
        relevant.append({
            "source_row": int(values[0]),
            "product_name": values[1],
            "producer": empty_marker(values[4]),
            "brand_source_reported": empty_marker(values[5]),
            "model": empty_marker(values[6]),
            "production_date_or_batch": empty_marker(values[7]),
            "outcome_source_reported": values[8],
            "nonconforming_items_source_reported": empty_marker(values[9]),
            "sampling_date": empty_marker(values[11]),
            "inspection_standard": empty_marker(values[12]),
        })
    if len(relevant) != 15 or any(row["outcome_source_reported"] != "合格" for row in relevant):
        raise RuntimeError(f"Expected 15 conforming Yantai detergent rows, received {len(relevant)}")
    return relevant, len(all_rows)


def normalize_brand(value: str, producer: str) -> tuple[str, str]:
    value = clean(value)
    if value and value not in {"图形", "图片", "英文", "字母", "图形商标"}:
        return value, "source_reported_text_brand"
    return producer, "nominal_producer_fallback_no_usable_text_brand"


def package_removed_model(value: str) -> str:
    value = value.replace("净含量", "")
    value = re.sub(r"[:：]?\s*\d+(?:\.\d+)?\s*(?:mL|ml|ML|L|l)(?:\s*/\s*(?:瓶|罐|桶))?", "", value)
    return clean(value).strip("，,、 ：:;；/")


def technical() -> dict:
    return {
        "api_source_reported": [], "api_gl_source_reported": [],
        "sae_source_reported": [], "iso_vg_source_reported": [],
        "china_lubricant_class_source_reported": [], "acea_source_reported": [],
        "jaso_source_reported": [], "ilsac_source_reported": [],
        "oem_approval_source_reported": [], "brake_fluid_dot_source_reported": [],
        "brake_fluid_hzy_source_reported": [], "coolant_class_source_reported": [],
        "coolant_freezing_point_source_reported": [], "washer_fluid_class_source_reported": [],
        "washer_fluid_freezing_point_source_reported": [], "urea_class_source_reported": [],
    }


def main() -> None:
    payload = fetch()
    source, all_rows = source_rows(payload)
    records = []
    for row in source:
        brand, brand_basis = normalize_brand(row["brand_source_reported"], row["producer"])
        source_facts = dict(row)
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"YT-CN-2025-{row['source_row']:03d}",
            "source_row": row["source_row"], "source_url": SOURCE_URL,
            "attachment_url": SOURCE_URL, "rights_url": RIGHTS_URL,
            "snapshot_date": SNAPSHOT_DATE, "report_date": REPORT_DATE,
            "market": "China / Yantai", "manufacturer": row["producer"],
            "manufacturer_source_reported": row["producer"],
            "manufacturer_basis": "source_reported_nominal_producer",
            "brand": brand, "brand_source_reported": row["brand_source_reported"],
            "brand_basis": brand_basis, "product_name": row["product_name"],
            "product_name_basis": "source_reported_sample_name_from_municipal_quality_inspection",
            "model_specification_source_reported": row["model"],
            "model_specification_without_package": package_removed_model(row["model"]),
            "product_kind_source_reported": "车用汽油清净剂",
            "product_kind_english": "automotive gasoline detergent additive",
            "family_code": "S", "technical": technical(),
            "production_date_or_batch_source_reported": row["production_date_or_batch"],
            "inspection_standards_scope_source_reported": [row["inspection_standard"]],
            "inspection_outcome": "conforming", "inspection_retest_confirmed_nonconforming": False,
            "nonconforming_items": [], "nonconforming_items_source_reported": "",
            "source_note": f"Official sampling date: {row['sampling_date']}",
            "lifecycle_status": "official_2025_yantai_inspection_conforming_at_test_current_market_status_unverified",
            "source_quality_flags": [
                "official_2025_municipal_inspection_observation_not_current_catalog_offer",
                "source_html_not_redistributed_factual_fields_only",
            ],
            "source_facts_sha256": hashlib.sha256(
                json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "evidence_status": "official_government_conforming_product_inspection_observation",
        })
    records.sort(key=lambda row: row["source_record_id"])
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_yantai_2025_gasoline_detergent_inspections_normalized",
        "snapshot_date": SNAPSHOT_DATE, "source_id": SOURCE_ID,
        "source_url": SOURCE_URL, "source_html_sha256": SOURCE_HTML_SHA256,
        "source_all_product_rows": all_rows,
        "retained_product_observations": len(records),
        "excluded_out_of_scope_rows": all_rows - len(records),
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "distinct_nominal_producers": len({row["manufacturer"] for row in records}),
        "distinct_source_brands": len({row["brand_source_reported"] for row in records if row["brand_source_reported"]}),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "scope_note": "All 350 rows were audited; exactly 15 automotive gasoline detergent observations are retained and 335 unrelated industrial products are excluded.",
        "privacy_note": "Sampled enterprises, social-credit codes and the laboratory are excluded; only product-side facts are retained.",
        "lifecycle_note": "A conforming result applies only to the sampled batch and does not prove a current offer, recommendation or blanket approval.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
