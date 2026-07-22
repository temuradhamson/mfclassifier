#!/usr/bin/env python3
"""Normalize Shanghai's complete 2023-2025 lubricant inspection tables."""

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
OUTPUT = ROOT / "data/shanghai-2023-2025-lubricant-inspections.jsonl"
REPORT = ROOT / "data/shanghai-2023-2025-lubricant-inspections-report.json"
RIGHTS_URL = "https://www.shanghai.gov.cn/nw44398/20200824/0001-44398_45637.html"
SNAPSHOT_DATE = "2026-07-22"

SOURCES = (
    {
        "source_id": "SHANGHAI_CHINA_2023_INDUSTRIAL_LUBRICANT_INSPECTION_1",
        "source_url": "https://scjgj.sh.gov.cn/923/20230821/2c984a728a15e02c018a17a844d623f4.html",
        "report_date": "2023-08-21", "kind": "industrial", "expected_rows": 64,
        "expected_sha256": "3f2359c30b38c5e0b158bc2b25faad1fbc4b431c97ce7af2659cd7a2ebed2ed4",
    },
    {
        "source_id": "SHANGHAI_CHINA_2023_INDUSTRIAL_LUBRICANT_INSPECTION_2",
        "source_url": "https://scjgj.sh.gov.cn/923/20231121/2c984a728bdfc867018befd976ca2dbb.html",
        "report_date": "2023-11-21", "kind": "industrial", "expected_rows": 35,
        "expected_sha256": "b7cfd6ea2ae3385eda74fc9870813408a93474933bb9a7a994477c33a630e64d",
    },
    {
        "source_id": "SHANGHAI_CHINA_2024_INDUSTRIAL_LUBRICANT_INSPECTION",
        "source_url": "https://scjgj.sh.gov.cn/923/20240924/2c984a7292079f74019222bb71ac71e7.html",
        "report_date": "2024-09-24", "kind": "industrial", "expected_rows": 131,
        "expected_sha256": "bc6ac7dfe55b9220f2cc68af18f74864a30b1aab674fb6428284714a417e1fb9",
    },
    {
        "source_id": "SHANGHAI_CHINA_2025_ENGINE_OIL_INSPECTION",
        "source_url": "https://scjgj.sh.gov.cn/923/20250728/2c984a72984f47f201985041e2560dfa.html",
        "report_date": "2025-07-28", "kind": "engine", "expected_rows": 30,
        "expected_sha256": "a162ba0813d7c6a728a26230ceb0ac3f60e4615aa95c4a4172cfe90b33582e71",
    },
    {
        "source_id": "SHANGHAI_CHINA_2025_INDUSTRIAL_LUBRICANT_INSPECTION",
        "source_url": "https://scjgj.sh.gov.cn/923/20251111/2c984a729a0b6239019a721b444c52ff.html",
        "report_date": "2025-11-11", "kind": "industrial", "expected_rows": 130,
        "expected_sha256": "727550023f5f72fe0bf7bad3feeb4149f0ec318b763788472813a0d419e6e7fc",
    },
)


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"/", "//", "///", "-", "—", "未标注", "未注明"} else value


class TableParser(HTMLParser):
    """Collect nested content tables without depending on non-stdlib HTML packages."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.table_stack: list[list[list[str]]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.table_stack.append([])
        elif tag == "tr" and self.table_stack:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None:
            assert self.row is not None
            self.row.append(clean("".join(self.cell)))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.table_stack[-1].append(self.row)
            self.row = None
        elif tag == "table" and self.table_stack:
            self.tables.append(self.table_stack.pop())


def fetch(source: dict) -> bytes:
    request = urllib.request.Request(source["source_url"], headers={
        "User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0",
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != source["expected_sha256"]:
        raise RuntimeError(
            f"Shanghai page changed for {source['source_id']}: "
            f"expected {source['expected_sha256']}, received {digest}"
        )
    return payload


def source_rows(payload: bytes, source: dict) -> list[dict]:
    parser = TableParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    rows = []
    row_number = 0
    expected_header = ["样品标称名称", "标称商标", "标称规格型号", "标称生产日期/批号", "标称生产者名称"]
    for table in parser.tables:
        if not table or table[0][:5] != expected_header:
            continue
        nonconforming_table = len(table[0]) == 9 and table[0][-1] == "不合格项目"
        for values in table[1:]:
            if len(values) not in {8, 9}:
                raise RuntimeError(f"Unexpected Shanghai row width in {source['source_id']}: {values!r}")
            row_number += 1
            rows.append({
                "source_row": row_number,
                "product_name": values[0],
                "brand_source_reported": empty_marker(values[1]),
                "model": values[2],
                "production_date": empty_marker(values[3]),
                "producer": values[4],
                "inspection_outcome": "nonconforming" if nonconforming_table else "conforming",
                "nonconforming_items_source_reported": values[8] if nonconforming_table else "",
            })
    if len(rows) != source["expected_rows"]:
        raise RuntimeError(
            f"Expected {source['expected_rows']} rows for {source['source_id']}, received {len(rows)}"
        )
    return rows


def family(row: dict, source_kind: str) -> tuple[str, str]:
    if source_kind == "engine":
        return "M", "motor-vehicle engine oil"
    value = row["product_name"] + " " + row["model"]
    if any(token in value for token in ("液压", "抗磨", "液压导轨")):
        return "H", "hydraulic oil"
    if any(token in value for token in ("压缩机", "冷冻机")):
        return "C", "compressor or refrigeration oil"
    if any(token in value for token in ("汽轮机", "透平")):
        return "U", "turbine oil"
    if any(token in value for token in ("变压器", "绝缘油")):
        return "E", "electrical insulating oil"
    if any(token in value for token in ("齿轮", "传动", "变速箱")):
        return "T", "gear or transmission oil"
    return "I", "industrial lubricating oil"


def extract_technical(row: dict, family_code: str) -> dict:
    value = (row["product_name"] + " " + row["model"]).upper().replace("－", "-").replace("–", "-")
    sae = [
        f"{winter}-{summer}"
        for winter, summer in re.findall(r"(?<![0-9])(0W|5W|10W|15W|20W|25W)\s*-?\s*([0-9]{2,3})(?![0-9])", value)
    ]
    api = re.findall(r"(?<![A-Z0-9])(CF-4|CH-4|CI-4|CJ-4|CK-4|CD|CF|SG|SJ|SL|SM|SN|SP|SQ)(?![A-Z0-9])", value)
    api_gl = [f"GL-{grade}" for grade in re.findall(r"(?:API\s*)?GL\s*-?\s*([1-6])", value)]
    iso_vg = re.findall(r"ISO\s*VG\s*([0-9]{1,4})", value)
    cn_classes = re.findall(r"(?<![A-Z])L\s*-\s*(HM|HG|HL|HR|HV|HS|CK[BCDE]|DA[ABCHJ]|TSA|AN|FD|QB)\s*-?\s*([0-9]{1,4})?", value)
    normalized_classes = []
    for code, grade in cn_classes:
        normalized_classes.append(f"L-{code}{grade}" if grade else f"L-{code}")
        if grade and family_code in {"H", "I", "C", "U", "E"}:
            iso_vg.append(grade)
    if not iso_vg and family_code in {"H", "I", "C", "U", "E"}:
        match = re.search(r"(?<![A-Z0-9])(?:HM|HG|HL|HV|CK[BCDE]|DA[ABCHJ]|TSA|AN|FD|QB)[- ]?([0-9]{2,4})(?![0-9])", value)
        if match:
            iso_vg.append(match.group(1))
    return {
        "api_source_reported": sorted(set(api)),
        "api_gl_source_reported": sorted(set(api_gl)),
        "sae_source_reported": sorted(set(sae)),
        "iso_vg_source_reported": sorted(set(iso_vg), key=lambda item: int(item)),
        "china_lubricant_class_source_reported": sorted(set(normalized_classes)),
        "acea_source_reported": [], "ilsac_source_reported": [],
        "brake_fluid_dot_source_reported": [], "brake_fluid_hzy_source_reported": [],
        "coolant_class_source_reported": [], "washer_fluid_class_source_reported": [],
        "urea_class_source_reported": [],
    }


def normalized_brand(source_brand: str, producer: str) -> tuple[str, str]:
    if not source_brand:
        return producer, "nominal_producer_fallback_no_usable_text_brand"
    parts = []
    for part in re.split(r"[+＋/]", source_brand):
        part = clean(part)
        part = re.sub(r"(?:注册)?商标|图形|图案|字母", "", part).strip(" -（）()")
        if part:
            parts.append(part)
    parts = list(dict.fromkeys(parts))
    if not parts:
        return producer, "nominal_producer_fallback_graphic_mark_only"
    return " / ".join(parts), "source_reported_text_brand_cleaned_of_graphic_mark_labels"


def package_removed_model(value: str) -> str:
    value = value.replace("毫升", "ml").replace("升", "L").replace("千克", "kg").replace("公斤", "kg")
    value = re.sub(r"(?:净含量|含量|规格)\s*[：:]?\s*", "", value)
    value = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ml|mL|L|l|kg|KG|g)\s*(?:/\s*(?:瓶|桶))?", "", value)
    value = re.sub(r"(?:皮重|毛重)[^,，;；]*", "", value)
    return clean(value).strip("，,、;； ")


def main() -> None:
    records = []
    source_digests = {}
    for source in SOURCES:
        payload = fetch(source)
        source_digests[source["source_id"]] = hashlib.sha256(payload).hexdigest()
        for row in source_rows(payload, source):
            family_code, kind_en = family(row, source["kind"])
            technical = extract_technical(row, family_code)
            technical_flags = []
            if re.search(r"(?<![A-Za-z0-9])Cl-4(?![A-Za-z0-9])", row["model"]):
                technical["api_source_reported"] = sorted(set(technical["api_source_reported"] + ["CI-4"]))
                technical_flags.append("source_latin_lowercase_l_in_cl4_normalized_to_api_ci4")
            producer = clean(row["producer"]).rstrip("）)")
            brand, brand_basis = normalized_brand(row["brand_source_reported"], producer)
            source_facts = {
                "product_name": row["product_name"], "brand": row["brand_source_reported"],
                "model": row["model"], "production_date": row["production_date"],
                "producer": row["producer"], "outcome": row["inspection_outcome"],
                "nonconforming_items": row["nonconforming_items_source_reported"],
            }
            records.append({
                "source_id": source["source_id"],
                "source_record_id": f"SH-CN-{source['report_date'].replace('-', '')}-{row['source_row']:03d}",
                "source_row": row["source_row"], "source_url": source["source_url"],
                "attachment_url": source["source_url"], "rights_url": RIGHTS_URL,
                "snapshot_date": SNAPSHOT_DATE, "report_date": source["report_date"],
                "market": "China / Shanghai", "manufacturer": producer,
                "manufacturer_source_reported": row["producer"],
                "brand": brand, "brand_source_reported": row["brand_source_reported"],
                "brand_basis": brand_basis, "product_name": row["product_name"],
                "product_name_basis": "source_reported_sample_name_from_municipal_quality_inspection",
                "model_specification_source_reported": row["model"],
                "model_specification_without_package": package_removed_model(row["model"]),
                "product_kind_source_reported": "发动机机油" if source["kind"] == "engine" else "工业用润滑油",
                "product_kind_english": kind_en, "family_code": family_code,
                "technical": technical,
                "production_date_or_batch_source_reported": row["production_date"],
                "inspection_outcome": row["inspection_outcome"],
                "inspection_retest_confirmed_nonconforming": False,
                "nonconforming_items": [clean(x) for x in re.split(r"[、，,]", row["nonconforming_items_source_reported"]) if clean(x)],
                "nonconforming_items_source_reported": row["nonconforming_items_source_reported"],
                "source_note": "", "inspection_standards_scope_source_reported": [],
                "lifecycle_status": f"official_shanghai_inspection_{row['inspection_outcome']}_at_test_current_market_status_unverified",
                "source_quality_flags": [
                    "official_municipal_inspection_observation_not_current_catalog_offer",
                    "source_html_not_redistributed_factual_fields_only",
                    *technical_flags,
                ],
                "source_facts_sha256": hashlib.sha256(
                    json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
                "evidence_status": f"official_government_{row['inspection_outcome']}_product_inspection_observation",
            })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_shanghai_2023_2025_complete_lubricant_inspections_normalized",
        "snapshot_date": SNAPSHOT_DATE, "source_pages": len(SOURCES),
        "source_html_sha256": source_digests, "source_observations": len(records),
        "source_counts": dict(sorted(Counter(row["source_id"] for row in records).items())),
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_sae": sum(bool(row["technical"]["sae_source_reported"]) for row in records),
        "rows_with_api": sum(bool(row["technical"]["api_source_reported"]) for row in records),
        "rows_with_api_gl": sum(bool(row["technical"]["api_gl_source_reported"]) for row in records),
        "rows_with_iso_vg": sum(bool(row["technical"]["iso_vg_source_reported"]) for row in records),
        "rows_with_china_lubricant_class": sum(bool(row["technical"]["china_lubricant_class_source_reported"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One row is one inspected batch observation. Strict package-independent product reconciliation is performed only by the catalog builder.",
        "lifecycle_note": "A conforming result applies only to the sampled batch. No observation is treated as a current offer or blanket product approval.",
        "privacy_note": "Sampled retailers, shopping centres, platforms and certification-agency columns are excluded.",
        "rights_note": "Official source HTML is not redistributed; only attributed non-expressive product and inspection facts are normalized.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
