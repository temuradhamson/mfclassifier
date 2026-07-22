#!/usr/bin/env python3
"""Normalize two complete Beijing 2018 automotive-fluid inspection releases."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import xlrd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/beijing-2018-automotive-fluid-inspections.jsonl"
REPORT = ROOT / "data/beijing-2018-automotive-fluid-inspections-report.json"
SNAPSHOT_DATE = "2026-07-22"
RIGHTS_URL = "https://www.beijing.gov.cn/zhengce/zhengcefagui/201905/t20190522_61986.html"

FIRST_SOURCE_ID = "BEIJING_CHINA_2018_AUTOMOTIVE_FLUID_INSPECTION_1"
FIRST_SOURCE_URL = "https://scjgj.beijing.gov.cn/zwxx/gs/cpzlgs/201909/t20190904_267303.html"
FIRST_ATTACHMENT_URL = "https://scjgj.beijing.gov.cn/zwxx/gs/cpzlgs/201909/P020260407525207722676.xls"
FIRST_REPORT_DATE = "2018-04-21"
FIRST_EXPECTED_XLS_SHA256 = "beb28359a68d509305cc5fc8efa4887007a4cf4e18c31e53a3505724b9bedaa7"

SECOND_SOURCE_ID = "BEIJING_CHINA_2018_AUTOMOTIVE_FLUID_INSPECTION_2"
SECOND_SOURCE_URL = "https://scjgj.beijing.gov.cn/zwxx/gs/cpzlgs/201909/t20190904_267220.html"
SECOND_REPORT_DATE = "2018-09-26"
SECOND_EXPECTED_HTML_SHA256 = "f79e58800a664df053d043fdea2b25679744f68fea2347e9976762a2238cd9b9"

RELEVANT_KINDS = {
    "车用汽油清净剂": ("S", "automotive gasoline detergent additive"),
    "车用尿素溶液": ("TF", "automotive aqueous urea solution"),
    "柴油机油、汽油机油": ("M", "motor-vehicle engine oil"),
    "发动机冷却液": ("TF", "motor-vehicle engine coolant"),
    "机动车制动液": ("TF", "motor-vehicle brake fluid"),
}
FIRST_EXPECTED_COUNTS = {
    "车用汽油清净剂": 9, "车用尿素溶液": 22, "柴油机油、汽油机油": 76,
    "发动机冷却液": 35, "机动车制动液": 5,
}
SECOND_TABLE_KINDS = {
    11: "车用汽油清净剂", 12: "车用尿素溶液",
    13: "柴油机油、汽油机油", 16: "发动机冷却液",
}
SECOND_EXPECTED_COUNTS = {
    "车用汽油清净剂": 9, "车用尿素溶液": 47,
    "柴油机油、汽油机油": 86, "发动机冷却液": 5,
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"/", "//", "///", "-", "--", "—", "无", "未标注", "未注明", "未提供"} else value


def fetch(url: str, expected_sha256: str, referer: str | None = None) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0"}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise RuntimeError(f"Beijing source changed: expected {expected_sha256}, received {digest}")
    return payload


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.stack: list[list[list[str]]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self.stack.append([])
        elif tag == "tr" and self.stack:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self.cell is not None:
            assert self.row is not None
            self.row.append(clean("".join(self.cell)))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.stack[-1].append(self.row)
            self.row = None
        elif tag == "table" and self.stack:
            self.tables.append(self.stack.pop())


def first_rows(payload: bytes) -> list[dict]:
    sheet = xlrd.open_workbook(file_contents=payload).sheet_by_index(0)
    section = ""
    counters = Counter()
    rows = []
    for row_index in range(sheet.nrows):
        values = [clean(sheet.cell_value(row_index, col)) for col in range(sheet.ncols)]
        section_match = re.match(r"^\d+、(.+)$", values[0])
        if section_match:
            section = section_match.group(1)
            continue
        if section not in RELEVANT_KINDS or not re.fullmatch(r"\d+(?:\.0)?", values[0]):
            continue
        counters[section] += 1
        rows.append({
            "source_id": FIRST_SOURCE_ID, "source_url": FIRST_SOURCE_URL,
            "attachment_url": FIRST_ATTACHMENT_URL, "report_date": FIRST_REPORT_DATE,
            "source_kind": section, "source_row": counters[section],
            "producer": values[1], "product_name": values[2],
            "brand_source_reported": empty_marker(values[3]), "model": values[4],
            "production_date": empty_marker(values[5]), "outcome_source_reported": values[6],
            "nonconforming_items_source_reported": empty_marker(values[7]),
            "source_note": empty_marker(values[8]),
        })
    if dict(counters) != FIRST_EXPECTED_COUNTS:
        raise RuntimeError(f"Unexpected Beijing first-release counts: {dict(counters)!r}")
    return rows


def second_rows(payload: bytes) -> list[dict]:
    parser = TableParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    counters = Counter()
    rows = []
    for table_index, source_kind in SECOND_TABLE_KINDS.items():
        table = parser.tables[table_index]
        if len(table) < 3 or table[0][:2] != ["序号", "企业名称"]:
            raise RuntimeError(f"Unexpected Beijing HTML table {table_index}: {table[:2]!r}")
        for values in table[2:]:
            if len(values) not in {8, 9} or not values[0].isdigit():
                raise RuntimeError(f"Unexpected Beijing HTML row: {values!r}")
            if len(values) == 8:
                # One official row omits the production date/batch cell entirely.
                values = values[:5] + [""] + values[5:]
            counters[source_kind] += 1
            rows.append({
                "source_id": SECOND_SOURCE_ID, "source_url": SECOND_SOURCE_URL,
                "attachment_url": SECOND_SOURCE_URL, "report_date": SECOND_REPORT_DATE,
                "source_kind": source_kind, "source_row": counters[source_kind],
                "producer": values[1], "product_name": values[2],
                "brand_source_reported": empty_marker(values[3]), "model": values[4],
                "production_date": empty_marker(values[5]), "outcome_source_reported": values[6],
                "nonconforming_items_source_reported": empty_marker(values[7]),
                "source_note": empty_marker(values[8]),
            })
    if dict(counters) != SECOND_EXPECTED_COUNTS:
        raise RuntimeError(f"Unexpected Beijing second-release counts: {dict(counters)!r}")
    return rows


def manufacturer(value: str) -> tuple[str, str, str]:
    source = clean(value)
    entrusted = re.search(r"[（(]委托(.+?)[）)]$", source)
    if entrusted:
        return clean(entrusted.group(1)), source, "entrusted_producer_explicit_in_source_enterprise_field"
    return source, source, "source_reported_enterprise"


def normalized_brand(source_brand: str, producer: str) -> tuple[str, str]:
    if not source_brand:
        return producer, "nominal_producer_fallback_no_usable_text_brand"
    value = re.sub(r"[（(]?\s*(?:图形|图案|文字商标)\s*[）)]?", "", source_brand)
    value = clean(value).strip("+＋/ -（）()")
    if not value:
        return producer, "nominal_producer_fallback_graphic_mark_only"
    return value, "source_reported_text_brand_cleaned_of_graphic_mark_labels"


def technical(row: dict) -> tuple[dict, list[str]]:
    source = f"{row['product_name']} {row['model']}"
    value = (
        source.upper().replace("－", "-").replace("–", "-").replace("−", "-")
        .replace("﹣", "-").replace("／", "/").replace("＆", "&")
    )
    flags = []
    sae = [
        f"{winter}-{summer}"
        for winter, summer in re.findall(r"(?<![0-9])(0W|5W|10W|15W|20W|25W)\s*[-/]?\s*([0-9]{2})(?![0-9])", value)
    ]
    sae.extend(re.findall(r"\bSAE\s*[/ -]?\s*(30|40|50|60)\b", value))
    api = re.findall(
        r"(?<![A-Z0-9])(CF-4|CG-4|CH-4|CI-4|CJ-4|CK-4|CD|CE|CF|CG|SF|SG|SJ|SL|SM|SN|SP|SQ)(?![A-Z0-9])",
        value,
    )
    ilsac = re.findall(r"GF\s*-?\s*([1-7])", value)
    acea = re.findall(r"(?<![A-Z0-9])(A[1-7]|B[1-5]|C[1-6]|E[4-9])(?=$|[^A-Z0-9])", value)
    jaso = re.findall(r"(?<![A-Z0-9])(DH-1|DH-2|DL-1)(?![A-Z0-9])", value)
    dot = [f"DOT {grade}" for grade in re.findall(r"DOT\s*-?\s*([345])", value)]
    hzy = [f"HZY{grade}" for grade in re.findall(r"HZY\s*-?\s*([3456])", value)]
    coolant_classes = re.findall(r"(?:LEC|HEC|LOC)-?[ⅡII]+-?\d{0,2}", value)
    freezing_points = [f"-{degree} °C" for degree in re.findall(r"(?<![0-9])-\s*(\d{1,2})\s*℃", value)]
    urea = ["AUS 32"] if re.search(r"AUS\s*32", value) else []
    if re.search(r"(?<![A-Z0-9])CI\s+15W", value):
        flags.append("source_api_ci_without_dash_retained_as_ci_not_silently_promoted_to_ci4")
    return {
        "api_source_reported": sorted(set(api)),
        "api_gl_source_reported": [], "sae_source_reported": sorted(set(sae)),
        "iso_vg_source_reported": [], "china_lubricant_class_source_reported": [],
        "acea_source_reported": sorted(set(acea)),
        "jaso_source_reported": sorted(set(jaso)),
        "ilsac_source_reported": sorted({f"GF-{grade}" for grade in ilsac}),
        "brake_fluid_dot_source_reported": sorted(set(dot)),
        "brake_fluid_hzy_source_reported": sorted(set(hzy)),
        "coolant_class_source_reported": sorted(set(coolant_classes)),
        "coolant_freezing_point_source_reported": sorted(set(freezing_points)),
        "washer_fluid_class_source_reported": [],
        "urea_class_source_reported": urea,
    }, flags


def package_removed_model(value: str) -> str:
    value = value.replace("毫升", "ml").replace("千克", "kg").replace("公斤", "kg").replace("升", "L")
    value = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ml|mL|L|l|kg|KG|g)\s*(?:/\s*(?:瓶|桶))?", "", value)
    return clean(value).strip("，,、 ：:;；")


def outcome(value: str) -> str:
    if "不合格" in value:
        return "nonconforming"
    if "合格" in value:
        return "conforming"
    raise RuntimeError(f"Unknown Beijing inspection outcome: {value!r}")


def main() -> None:
    first_payload = fetch(FIRST_ATTACHMENT_URL, FIRST_EXPECTED_XLS_SHA256, FIRST_SOURCE_URL)
    second_payload = fetch(SECOND_SOURCE_URL, SECOND_EXPECTED_HTML_SHA256)
    raw_rows = first_rows(first_payload) + second_rows(second_payload)
    records = []
    for row in raw_rows:
        family_code, kind_en = RELEVANT_KINDS[row["source_kind"]]
        producer, producer_source, producer_basis = manufacturer(row["producer"])
        brand, brand_basis = normalized_brand(row["brand_source_reported"], producer)
        extracted, technical_flags = technical(row)
        inspection_outcome = outcome(row["outcome_source_reported"])
        release = "1" if row["source_id"] == FIRST_SOURCE_ID else "2"
        kind_code = {
            "车用汽油清净剂": "ADD",
            "车用尿素溶液": "UREA",
            "柴油机油、汽油机油": "M",
            "发动机冷却液": "COOL",
            "机动车制动液": "BRAKE",
        }[row["source_kind"]]
        source_facts = {key: row[key] for key in sorted(row)}
        flags = [
            "official_2018_municipal_inspection_observation_not_current_catalog_offer",
            "source_document_not_redistributed_factual_fields_only", *technical_flags,
        ]
        if inspection_outcome == "nonconforming":
            flags.append("nonconforming_product_do_not_treat_as_approved_or_recommended")
        if "复查检验合格" in row["source_note"]:
            flags.append("source_note_reports_follow_up_reinspection_conforming")
        records.append({
            "source_id": row["source_id"],
            "source_record_id": f"BJ-CN-2018-{release}-{kind_code}-{row['source_row']:03d}",
            "source_row": row["source_row"], "source_url": row["source_url"],
            "attachment_url": row["attachment_url"], "rights_url": RIGHTS_URL,
            "snapshot_date": SNAPSHOT_DATE, "report_date": row["report_date"],
            "market": "China / Beijing", "manufacturer": producer,
            "manufacturer_source_reported": producer_source, "manufacturer_basis": producer_basis,
            "brand": brand, "brand_source_reported": row["brand_source_reported"],
            "brand_basis": brand_basis, "product_name": row["product_name"],
            "product_name_basis": "source_reported_sample_name_from_municipal_quality_inspection",
            "model_specification_source_reported": row["model"],
            "model_specification_without_package": package_removed_model(row["model"]),
            "product_kind_source_reported": row["source_kind"],
            "product_kind_english": kind_en, "family_code": family_code,
            "technical": extracted, "inspection_standards_scope_source_reported": [],
            "production_date_or_batch_source_reported": row["production_date"],
            "inspection_outcome": inspection_outcome,
            "inspection_retest_confirmed_nonconforming": False,
            "nonconforming_items": [
                clean(item) for item in re.split(r"[、，,；;]", row["nonconforming_items_source_reported"]) if clean(item)
            ],
            "nonconforming_items_source_reported": row["nonconforming_items_source_reported"],
            "source_note": row["source_note"],
            "lifecycle_status": f"official_2018_beijing_inspection_{inspection_outcome}_at_test_current_market_status_unverified",
            "source_quality_flags": sorted(set(flags)),
            "source_facts_sha256": hashlib.sha256(
                json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "evidence_status": f"official_government_{inspection_outcome}_product_inspection_observation",
        })

    if len(records) != 294 or len({row["source_record_id"] for row in records}) != 294:
        raise RuntimeError(f"Expected 294 unique Beijing observations, received {len(records)}")
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_beijing_2018_complete_automotive_fluid_inspections_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_xls_sha256": FIRST_EXPECTED_XLS_SHA256,
        "source_html_sha256": SECOND_EXPECTED_HTML_SHA256,
        "source_observations": len(records),
        "source_counts": dict(sorted(Counter(row["source_id"] for row in records).items())),
        "source_product_types": dict(sorted(Counter(row["product_kind_source_reported"] for row in records).items())),
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_sae": sum(bool(row["technical"]["sae_source_reported"]) for row in records),
        "rows_with_api": sum(bool(row["technical"]["api_source_reported"]) for row in records),
        "rows_with_ilsac": sum(bool(row["technical"]["ilsac_source_reported"]) for row in records),
        "rows_with_acea": sum(bool(row["technical"]["acea_source_reported"]) for row in records),
        "rows_with_jaso": sum(bool(row["technical"]["jaso_source_reported"]) for row in records),
        "rows_with_coolant_class": sum(bool(row["technical"]["coolant_class_source_reported"]) for row in records),
        "rows_with_coolant_freezing_point": sum(bool(row["technical"]["coolant_freezing_point_source_reported"]) for row in records),
        "rows_with_brake_class": sum(bool(row["technical"]["brake_fluid_dot_source_reported"] or row["technical"]["brake_fluid_hzy_source_reported"]) for row in records),
        "rows_with_explicit_aus32": sum(bool(row["technical"]["urea_class_source_reported"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One row is one inspected batch observation; the catalog builder reconciles only strict package-independent product identities.",
        "lifecycle_note": "Inspection outcomes are historical batch evidence, never current offers or blanket approvals.",
        "privacy_note": "The releases contain producer-level product tables, not sampled retailer details; no contact or address fields are retained.",
        "rights_note": "The official XLS/HTML documents are not redistributed; only attributed non-expressive product and inspection facts are normalized.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
