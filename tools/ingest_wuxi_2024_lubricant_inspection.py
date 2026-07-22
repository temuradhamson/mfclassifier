#!/usr/bin/env python3
"""Normalize all ten rows in Wuxi's complete 2024 lubricant inspection."""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

import xlrd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/wuxi-2024-lubricant-inspection.jsonl"
REPORT = ROOT / "data/wuxi-2024-lubricant-inspection-report.json"
SNAPSHOT_DATE = "2026-07-22"
SOURCE_ID = "WUXI_CHINA_2024_LUBRICANT_INSPECTION"
SOURCE_URL = "https://scjgj.wuxi.gov.cn/doc/2024/09/04/4386075.shtml"
ATTACHMENT_URL = "https://scjgj.wuxi.gov.cn/uploadfiles/202409/04/2024090411272748275710.xls"
RIGHTS_URL = "https://scjgj.wuxi.gov.cn/"
REPORT_DATE = "2024-09-04"
SOURCE_XLS_SHA256 = "d9d6b453523985b306e6fe5a84cffd5355bd03445e796226113a2febcbe3a9fa"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"-", "—", "——", "/", "无", "未标注"} else value


def unique(values: list[str]) -> list[str]:
    return sorted({clean(value) for value in values if clean(value)})


def fetch() -> bytes:
    request = urllib.request.Request(ATTACHMENT_URL, headers={
        "User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0",
        "Referer": SOURCE_URL,
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != SOURCE_XLS_SHA256:
        raise RuntimeError(f"Wuxi XLS changed: expected {SOURCE_XLS_SHA256}, received {digest}")
    return payload


def source_rows(payload: bytes) -> list[dict]:
    workbook = xlrd.open_workbook(file_contents=payload)
    if workbook.sheet_names() != ["汇总"]:
        raise RuntimeError(f"Unexpected Wuxi workbook sheets: {workbook.sheet_names()!r}")
    sheet = workbook.sheet_by_name("汇总")
    expected_title = "润滑油产品质量监督抽查企业名单及结果"
    expected_header = [
        "序号", "产品具体名称", "商标", "生产日期/货号", "规格型号",
        "标称生产企业", "标称生产企业地址", "受检单位", "样品来源", "抽查结果",
    ]
    if clean(sheet.cell_value(0, 0)) != expected_title:
        raise RuntimeError(f"Unexpected Wuxi workbook title: {sheet.cell_value(0, 0)!r}")
    if [clean(sheet.cell_value(1, column)) for column in range(10)] != expected_header:
        raise RuntimeError("Unexpected Wuxi workbook header")
    rows = []
    for row_index in range(2, sheet.nrows):
        values = [clean(sheet.cell_value(row_index, column)) for column in range(10)]
        if not any(values):
            continue
        source_number = sheet.cell_value(row_index, 0)
        if not isinstance(source_number, float) or not source_number.is_integer():
            raise RuntimeError(f"Unexpected Wuxi source row {row_index + 1}: {values!r}")
        rows.append({
            "source_row": int(source_number),
            "product_name": values[1],
            "brand_source_reported": empty_marker(values[2]),
            "production_date_or_batch": empty_marker(values[3]),
            "model": empty_marker(values[4]),
            "producer": empty_marker(values[5]),
            "outcome_source_reported": values[9],
        })
    if len(rows) != 10 or [row["source_row"] for row in rows] != list(range(1, 11)):
        raise RuntimeError(f"Expected sequential Wuxi rows 1..10, received {len(rows)}")
    if any(row["outcome_source_reported"] != "合格" for row in rows):
        raise RuntimeError("The official Wuxi page reports 100% conformity, but a row differs")
    return rows


def classify(product_name: str, model: str) -> tuple[str, str, str]:
    joined = f"{product_name} {model}".upper().replace("（", "(").replace("）", ")")
    if "液压油" in joined or re.search(r"L\s*-?\s*H(?:M|L|V|S|G)", joined):
        return "H", "hydraulic oil", "液压油"
    if (
        "机油" in joined
        or "发动机油" in joined
        or re.search(r"(?<![0-9])(?:0W|5W|10W|15W|20W|25W)\s*-?\s*(?:20|30|40|50|60)(?![0-9])", joined)
    ):
        return "M", "motor-vehicle engine oil", "机动车发动机油"
    raise RuntimeError(f"Unclassified Wuxi lubricant: {product_name!r} / {model!r}")


def normalize_brand(source_value: str, product_name: str, producer: str) -> tuple[str, str]:
    value = re.sub(r"(?:\+|，|,)?\s*图形$", "", clean(source_value)).strip("+，, ")
    if value:
        return value, "source_reported_text_brand_cleaned_of_graphic_mark_label"
    product_prefixes = (
        ("壳牌", "Shell"), ("美孚", "Mobil"), ("昆仑", "Kunlun"),
        ("胜牌", "Valvoline"), ("福星", "Sinopec Fuxing"),
    )
    for prefix, brand in product_prefixes:
        if clean(product_name).startswith(prefix):
            return brand, "brand_in_explicit_product_name"
    return producer, "nominal_producer_fallback_no_usable_text_brand"


def technical(product_name: str, model: str, family_code: str) -> tuple[dict, list[str]]:
    joined = f"{product_name} {model}".upper()
    joined = joined.replace("（", "(").replace("）", ")").replace("－", "-").replace("–", "-")
    flags = []
    sae = [
        f"{winter}-{summer}"
        for winter, summer in re.findall(
            r"(?<![0-9])(0W|5W|10W|15W|20W|25W)\s*-?\s*(20|30|40|50|60)(?![0-9])",
            joined,
        )
    ]
    api = []
    if family_code == "M":
        api.extend(re.findall(
            r"(?<![A-Z0-9])(CF-4|CG-4|CH-4|CI-4|CJ-4|CK-4|CC|CD|CE|CF|SF|SG|SJ|SL|SM|SN|SP)(?![A-Z0-9])",
            joined,
        ))
    china_classes = []
    iso_vg = []
    if family_code == "H":
        match = re.search(r"L\s*-?\s*(H(?:M|L|V|S|G))\s*(?:\([^)]*\))?\s*(\d{1,3})", joined)
        if match:
            china_classes.append(f"L-{match.group(1)} {int(match.group(2))}")
            iso_vg.append(str(int(match.group(2))))
            flags.append("iso_vg_derived_from_explicit_gb_l_hydraulic_viscosity_grade")
    return {
        "api_source_reported": unique(api),
        "api_gl_source_reported": [],
        "sae_source_reported": unique(sae),
        "iso_vg_source_reported": unique(iso_vg),
        "china_lubricant_class_source_reported": unique(china_classes),
        "acea_source_reported": [],
        "jaso_source_reported": [],
        "ilsac_source_reported": [],
        "oem_approval_source_reported": [],
        "brake_fluid_dot_source_reported": [],
        "brake_fluid_hzy_source_reported": [],
        "coolant_class_source_reported": [],
        "coolant_freezing_point_source_reported": [],
        "washer_fluid_class_source_reported": [],
        "washer_fluid_freezing_point_source_reported": [],
        "urea_class_source_reported": [],
    }, flags


def package_removed_model(value: str) -> str:
    value = value.replace("升", "L")
    value = re.sub(r"\b\d+(?:\.\d+)?\s*(?:L|KG)\s*/\s*(?:桶|瓶|罐|盒)", "", value, flags=re.I)
    return clean(value).strip("，,、 ：:;；/")


def main() -> None:
    payload = fetch()
    source = source_rows(payload)
    records = []
    for row in source:
        family_code, kind_en, kind_zh = classify(row["product_name"], row["model"])
        brand, brand_basis = normalize_brand(
            row["brand_source_reported"], row["product_name"], row["producer"]
        )
        extracted, technical_flags = technical(row["product_name"], row["model"], family_code)
        source_facts = dict(row)
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"WX-CN-2024-{row['source_row']:03d}",
            "source_row": row["source_row"],
            "source_url": SOURCE_URL,
            "attachment_url": ATTACHMENT_URL,
            "rights_url": RIGHTS_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "report_date": REPORT_DATE,
            "market": "China / Wuxi",
            "manufacturer": row["producer"],
            "manufacturer_source_reported": row["producer"],
            "manufacturer_basis": "source_reported_nominal_producer",
            "brand": brand,
            "brand_source_reported": row["brand_source_reported"],
            "brand_basis": brand_basis,
            "product_name": row["product_name"],
            "product_name_basis": "source_reported_sample_name_from_municipal_quality_inspection",
            "model_specification_source_reported": row["model"],
            "model_specification_without_package": package_removed_model(row["model"]),
            "product_kind_source_reported": kind_zh,
            "product_kind_english": kind_en,
            "family_code": family_code,
            "technical": extracted,
            "production_date_or_batch_source_reported": row["production_date_or_batch"],
            "inspection_standards_scope_source_reported": [],
            "inspection_outcome": "conforming",
            "inspection_retest_confirmed_nonconforming": False,
            "nonconforming_items": [],
            "nonconforming_items_source_reported": "",
            "source_note": "",
            "lifecycle_status": "official_2024_wuxi_inspection_conforming_at_test_current_market_status_unverified",
            "source_quality_flags": unique([
                "official_2024_municipal_inspection_observation_not_current_catalog_offer",
                "source_xls_not_redistributed_factual_fields_only",
                *technical_flags,
            ]),
            "source_facts_sha256": hashlib.sha256(
                json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "evidence_status": "official_government_conforming_product_inspection_observation",
        })
    if len({row["source_record_id"] for row in records}) != 10:
        raise RuntimeError("Wuxi source record identifiers are not unique")
    records.sort(key=lambda row: row["source_record_id"])
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_wuxi_2024_complete_lubricant_inspection_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "attachment_url": ATTACHMENT_URL,
        "source_xls_sha256": SOURCE_XLS_SHA256,
        "source_rows": len(source),
        "retained_product_observations": len(records),
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_api": sum(bool(row["technical"]["api_source_reported"]) for row in records),
        "rows_with_sae": sum(bool(row["technical"]["sae_source_reported"]) for row in records),
        "rows_with_china_lubricant_class": sum(bool(row["technical"]["china_lubricant_class_source_reported"]) for row in records),
        "rows_with_iso_vg": sum(bool(row["technical"]["iso_vg_source_reported"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One output row is one inspected batch observation; strict identity is resolved later while the occurrence remains linked.",
        "scope_note": "All ten rows in the official complete workbook are retained: eight engine oils and two hydraulic oils; all sampled batches conformed.",
        "privacy_note": "Sampled sellers, inspected units and addresses are deliberately excluded; only product-side factual fields are retained.",
        "lifecycle_note": "A conforming result applies only to the sampled batch and does not prove a current offer, recommendation or blanket approval.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
