#!/usr/bin/env python3
"""Normalize Jilin's complete 2024 and 2025 automotive-fluid inspections."""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/jilin-2024-2025-automotive-fluid-inspections.jsonl"
REPORT = ROOT / "data/jilin-2024-2025-automotive-fluid-inspections-report.json"
SNAPSHOT_DATE = "2026-07-22"
RIGHTS_URL = "https://scjg.jl.gov.cn/gywm/"

SOURCES = {
    "2024": {
        "source_id": "JILIN_CHINA_2024_AUTOMOTIVE_FLUID_INSPECTION",
        "source_url": "https://scjg.jl.gov.cn/jianguan/zlcc/202501/t20250113_9032819.html",
        "attachment_url": "https://scjg.jl.gov.cn/jianguan/zlcc/202501/P020250113350321815316.pdf",
        "report_date": "2025-01-13",
        "source_pdf_sha256": "095535608bce0826e046264dc79be24c2f7c7d1429d252dd850f18aae6a35461",
        "expected_rows": 206,
        "expected_nonconforming": 12,
        "expected_suspected_counterfeit": 0,
        "expected_excluded_fuels": 7,
        "expected_pages": 17,
    },
    "2025": {
        "source_id": "JILIN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION",
        "source_url": "https://scjg.jl.gov.cn/jianguan/zlcc/202602/t20260202_9413231.html",
        "attachment_url": "https://scjg.jl.gov.cn/jianguan/zlcc/202602/P020260624601397455443.pdf",
        "report_date": "2026-02-02",
        "source_pdf_sha256": "e437192cab367b60ed0b2b58812e1eaebda2df643e41812a7c4eb45998368c3d",
        "expected_rows": 209,
        "expected_nonconforming": 13,
        "expected_suspected_counterfeit": 3,
        "expected_excluded_fuels": 4,
        "expected_pages": 20,
    },
}

# The indexed 2023 PDF was verified as removed (HTTP 404) on the snapshot date.
# It is recorded as a coverage gap, never reconstructed from search snippets.
UNAVAILABLE_2023_SOURCE = {
    "title": "2023年吉林省车用油品产品质量专项监督抽查结果汇总表",
    "attachment_url": "https://scjg.jl.gov.cn/jianguan/zlcc/202402/P020240410402479715129.pdf",
    "status_at_snapshot": "official_attachment_http_404_not_ingested",
}

EXCLUDED_MOTOR_FUELS = {
    "车用柴油",
    "车用乙醇汽油调和组分油",
    "车用乙醇汽油调合组分油",
    "变性燃料乙醇",
}

KIND = {
    "engine_oil": ("M", "motor-vehicle engine oil", "机动车发动机油"),
    "brake_fluid": ("TF", "motor-vehicle brake fluid", "机动车辆制动液"),
    "coolant": ("TF", "motor-vehicle engine coolant", "机动车发动机冷却液"),
    "washer_fluid": ("TF", "automotive windshield washer fluid", "汽车风窗玻璃清洗液"),
    "urea": ("TF", "automotive aqueous urea solution", "车用尿素水溶液"),
    "fuel_additive": ("S", "automotive fuel-system additive or cleaner", "车用燃油添加剂或清净剂"),
}


def clean(value: object) -> str:
    value = re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()
    # PDF line wrapping inserts spaces inside Chinese words and company names.
    return re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", value)


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"/", "-", "--", "—", "——", "无", "未标注", "未注明"} else value


def unique(values: list[str]) -> list[str]:
    return sorted({clean(value) for value in values if clean(value)})


def fetch(source: dict) -> bytes:
    request = urllib.request.Request(source["attachment_url"], headers={
        "User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0",
        "Referer": source["source_url"],
    })
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != source["source_pdf_sha256"]:
        raise RuntimeError(
            f"Jilin PDF changed: expected {source['source_pdf_sha256']}, received {digest}"
        )
    return payload


def source_rows(year: str, payload: bytes) -> tuple[int, list[dict]]:
    source = SOURCES[year]
    rows = []
    with pdfplumber.open(io.BytesIO(payload)) as document:
        if len(document.pages) != source["expected_pages"]:
            raise RuntimeError(f"Unexpected Jilin {year} page count: {len(document.pages)}")
        for source_page, page in enumerate(document.pages, start=1):
            tables = page.extract_tables()
            if len(tables) != 1:
                raise RuntimeError(f"Expected one table on Jilin {year} page {source_page}")
            table = tables[0]
            expected_header = (
                ["序号", "产品名称", "规格型号", "批号", "生产日期", "标称商标", "受检单位名称", "标称生产单位名称", "抽查结果", "不合格项目"]
                if year == "2024" else
                ["序号", "产品名称", "规格型号", "生产日期", "标称商标", "受检单位名称", "标称生产单位名称", "抽查结果", "不合格项目"]
            )
            header = [clean(value) for value in table[0]]
            if header != expected_header:
                raise RuntimeError(f"Unexpected Jilin {year} page {source_page} header: {header!r}")
            for values in table[1:]:
                values = [clean(value) for value in values]
                if len(values) != len(expected_header) or not values[0].isdigit():
                    raise RuntimeError(f"Unexpected Jilin {year} page {source_page} row: {values!r}")
                row = dict(zip(expected_header, values, strict=True))
                rows.append({
                    "source_row": int(row["序号"]),
                    "source_page": source_page,
                    "product_name": row["产品名称"],
                    "model": empty_marker(row["规格型号"]),
                    "batch": empty_marker(row.get("批号", "")),
                    "production_date": empty_marker(row["生产日期"]),
                    "brand_source_reported": empty_marker(row["标称商标"]),
                    "inspected_unit": empty_marker(row["受检单位名称"]),
                    "producer": empty_marker(row["标称生产单位名称"]),
                    "outcome_source_reported": clean(row["抽查结果"]),
                    "nonconforming_items_source_reported": empty_marker(row["不合格项目"]),
                })
    expected = source["expected_rows"]
    if len(rows) != expected or [row["source_row"] for row in rows] != list(range(1, expected + 1)):
        raise RuntimeError(f"Expected sequential 1..{expected} Jilin {year} rows, received {len(rows)}")
    return len(document.pages), rows


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def classify(product_name: str, model: str) -> str:
    name = compact(product_name)
    if name in EXCLUDED_MOTOR_FUELS:
        return "excluded_motor_fuel"
    if any(value in name for value in ("尿素", "尾气净化液", "氮氧化物还原剂", "催化还原剂", "柴油车尾气处理液")):
        return "urea"
    if any(value in name for value in ("制动液", "刹车油", "刹车液")):
        return "brake_fluid"
    if any(value in name for value in ("冷却液", "防冻液", "冷冻液", "不冻液")):
        return "coolant"
    if any(value in name for value in ("玻璃水", "玻璃清洗", "玻璃养护", "风窗洗涤", "玻璃清洁", "玻璃镀膜")):
        return "washer_fluid"
    if any(value in name for value in ("机油", "发动机油", "发动机润滑油", "天然气全合成油", "合成润滑油")):
        return "engine_oil"
    if any(value in name for value in ("清净剂", "燃油", "汽油复合剂", "汽油添加剂", "汽油发动机清洁剂", "除碳", "喷油嘴", "活塞环", "油添力")):
        return "fuel_additive"
    if "水基型" in compact(model):
        return "washer_fluid"
    raise RuntimeError(f"Unclassified Jilin automotive fluid: {product_name!r} / {model!r}")


def normalized_brand(value: str, product_name: str, producer: str) -> tuple[str, str]:
    source = clean(value)
    normalized = source
    normalized = re.sub(r"[（(]?\s*(?:图形|圖形)\s*[）)]?", "", normalized)
    normalized = re.sub(r"(?:及|、|\+)?\s*字母\s*(?:、|及|和|\+)?\s*商标?", "", normalized)
    normalized = re.sub(r"(?:及|、|\+)?\s*(?:图案|图形)\s*商标?", "", normalized)
    normalized = re.sub(r"(?:及|、|\+)?\s*商标$", "", normalized)
    normalized = clean(normalized).strip("+＋/、，, -（）()")
    generic = {"", "字母", "图案", "图形", "字母及", "及"}
    if normalized not in generic:
        return normalized, "source_reported_text_brand_cleaned_of_graphic_mark_labels"
    prefixes = (
        ("壳牌", "Shell"), ("丰田纯牌", "Toyota"), ("上汽大众", "SAIC Volkswagen"),
        ("美孚", "Mobil"), ("奥迪", "Audi"), ("昆仑", "Kunlun"),
        ("蓝星", "Bluestar"), ("久保田", "Kubota"), ("红旗", "Hongqi"),
        ("吉利", "Geely"), ("陕汽", "Shaanxi Auto"),
    )
    for prefix, product_brand in prefixes:
        if compact(product_name).startswith(prefix):
            return product_brand, "brand_in_explicit_oem_or_brand_product_name"
    return producer, "nominal_producer_fallback_no_usable_text_brand"


def manufacturer(source_value: str, product_name: str, source_brand: str) -> tuple[str, str, str, bool]:
    source_value = clean(source_value)
    denied = "否认该产品为其生产" in compact(source_value)
    if source_value and not denied:
        return source_value, source_value, "source_reported_nominal_producer", False
    fallback_brand, _ = normalized_brand(source_brand, product_name, "")
    if fallback_brand:
        return fallback_brand, source_value, "source_brand_fallback_nominal_producer_denied_or_unreported", denied
    return (
        f"未标注生产单位｜{clean(product_name)}", source_value,
        "product_scoped_placeholder_nominal_producer_denied_or_unreported", denied,
    )


def technical(product_name: str, model: str, kind: str) -> tuple[dict, list[str]]:
    source = f"{product_name} {model}"
    value = clean(source.upper())
    value = (
        value.replace("Ⅱ", "II").replace("‖", "II").replace("－", "-")
        .replace("–", "-").replace("−", "-").replace("／", "/")
    )
    flags = []
    sae = []
    api = []
    if kind == "engine_oil":
        # Source models frequently concatenate API and SAE (for example
        # ``SL5W-30``), so an ASCII word boundary would lose valid evidence.
        sae.extend(
            f"{winter}-{summer}" for winter, summer in re.findall(
                r"(0W|5W|10W|15W|20W|25W)\s*[-/]?\s*(20|30|40|50|60)(?![0-9])", value
            )
        )
        api.extend(
            re.sub(r"\s+", "", grade) for grade in re.findall(
                r"CF\s*-\s*4|CG\s*-\s*4|CH\s*-\s*4|CI\s*-\s*4|CJ\s*-\s*4|CK\s*-\s*4|FA\s*-\s*4|SP|SN|SM|SL|SJ|SG|SF|CF|CE|CD|CC",
                value,
            )
        )
        for grade in re.findall(r"(?:CC|CD|CE|CF|SF|SG|SJ|SL|SM|SN|SP)\s*(30|40|50|60)(?![0-9])", value):
            sae.append(grade)
        if re.search(r"CH\s*-\s*4\s*20W\s*/\s*50", value):
            sae.append("20W-50")
            flags.append("source_ch4_and_sae_without_separator_normalized")
    acea = re.findall(r"(?<![A-Z0-9])(A[1-7](?:/B[1-7])?|B[1-7]|C[1-6]|E[4-9])(?![A-Z0-9])", value)
    ilsac = [f"GF-{grade}" for grade in re.findall(r"GF\s*-?\s*([1-7])", value)]
    dot = [f"DOT {grade}" for grade in re.findall(r"DOT\s*-?\s*([3-5])", value)]
    if re.search(r"D0T\s*4", value):
        dot.append("DOT 4")
        flags.append("source_digit_zero_in_dot4_normalized")
    hzy = [f"HZY{grade}" for grade in re.findall(r"HZY\s*-?\s*([3-6])", value)]
    if re.search(r"HYZ\s*5", value):
        hzy.append("HZY5")
        flags.append("source_hyz5_transposition_normalized_to_hzy5")
    coolant = []
    for prefix, grade in re.findall(r"(?<![A-Z])(LEC|HEC|LOC)\s*-?\s*II\s*-?\s*(15|25|26|30|35|40|41|45|50)?", value):
        coolant.append(f"{prefix}-II" + (f"-{grade}" if grade else ""))
    freezing = []
    if kind in {"coolant", "washer_fluid"}:
        freezing.extend(f"{int(number)} °C" for number in re.findall(r"(?<![0-9])(-?\d{1,2})\s*℃", value))
        if kind == "coolant":
            freezing.extend(
                f"-{grade} °C" for grade in re.findall(r"(?:LEC|HEC|LOC)\s*-?\s*II\s*-?\s*(15|25|26|30|35|40|41|45|50)", value)
            )
    washer = []
    if kind == "washer_fluid":
        for marker in ("水基型", "普通型", "低温型", "夏季型"):
            if marker in compact(source):
                washer.append(marker)
    urea = []
    if kind == "urea":
        urea = ["AUS 32"]
        if not re.search(r"AUS\s*-?\s*32|ADBLUE", value):
            flags.append("aus32_derived_from_official_automotive_urea_inspection_scope")
    return {
        "api_source_reported": unique(api), "api_gl_source_reported": [],
        "sae_source_reported": unique(sae), "iso_vg_source_reported": [],
        "china_lubricant_class_source_reported": [], "acea_source_reported": unique(acea),
        "jaso_source_reported": [], "ilsac_source_reported": unique(ilsac),
        "oem_approval_source_reported": [],
        "brake_fluid_dot_source_reported": unique(dot),
        "brake_fluid_hzy_source_reported": unique(hzy),
        "coolant_class_source_reported": unique(coolant),
        "coolant_freezing_point_source_reported": unique(freezing) if kind == "coolant" else [],
        "washer_fluid_class_source_reported": unique(washer),
        "washer_fluid_freezing_point_source_reported": unique(freezing) if kind == "washer_fluid" else [],
        "urea_class_source_reported": urea,
    }, flags


def package_removed_model(value: str) -> str:
    value = value.replace("毫升", "mL").replace("千克", "kg").replace("公斤", "kg").replace("升", "L")
    value = re.sub(r"(?:净含量[:：]?)?\s*\d+(?:\.\d+)?\s*(?:mL|L|kg|g)(?:\s*/\s*(?:瓶|桶|罐|盒))?", "", value, flags=re.I)
    return clean(value).strip("，,、 ：:;；/")


def split_failures(value: str) -> list[str]:
    return unique([part for part in re.split(r"[;；、]", value) if clean(part)])


def main() -> None:
    records = []
    source_files = []
    excluded_fuels = []
    for year, source in SOURCES.items():
        payload = fetch(source)
        page_count, rows = source_rows(year, payload)
        source_files.append({
            "year": year, "source_url": source["source_url"],
            "attachment_url": source["attachment_url"],
            "source_pdf_sha256": source["source_pdf_sha256"],
            "source_rows": len(rows), "source_pages": page_count,
        })
        for row in rows:
            kind = classify(row["product_name"], row["model"])
            if kind == "excluded_motor_fuel":
                excluded_fuels.append({"year": year, "source_row": row["source_row"], "product_name": compact(row["product_name"])})
                continue
            family_code, kind_en, kind_zh = KIND[kind]
            producer, producer_source, producer_basis, producer_denied = manufacturer(
                row["producer"], row["product_name"], row["brand_source_reported"]
            )
            product_brand, brand_basis = normalized_brand(row["brand_source_reported"], row["product_name"], producer)
            extracted, technical_flags = technical(row["product_name"], row["model"], kind)
            inspection_outcome = "nonconforming" if "不合格" in row["outcome_source_reported"] else "conforming"
            suspected_counterfeit = "涉嫌假冒" in compact(row["outcome_source_reported"])
            flags = [
                f"official_{year}_provincial_inspection_observation_not_current_catalog_offer",
                "source_pdf_not_redistributed_factual_fields_only", *technical_flags,
            ]
            if inspection_outcome == "nonconforming":
                flags.append("nonconforming_product_do_not_treat_as_approved_or_recommended")
            if producer_denied:
                flags.append("source_nominal_producer_denied_authorship")
            if suspected_counterfeit:
                flags.append("source_reports_suspected_counterfeit_nominal_producer_not_attributed")
            # Retailer/inspected-unit data is deliberately absent from both the
            # normalized row and the row hash.
            source_facts = {key: value for key, value in row.items() if key != "inspected_unit"}
            records.append({
                "source_id": source["source_id"],
                "source_record_id": f"JL-CN-{year}-{row['source_row']:03d}",
                "source_row": row["source_row"], "source_page": row["source_page"],
                "source_url": source["source_url"], "attachment_url": source["attachment_url"],
                "rights_url": RIGHTS_URL, "snapshot_date": SNAPSHOT_DATE,
                "report_date": source["report_date"], "market": "China / Jilin",
                "manufacturer": producer, "manufacturer_source_reported": producer_source,
                "manufacturer_basis": producer_basis,
                "brand": product_brand, "brand_source_reported": row["brand_source_reported"],
                "brand_basis": brand_basis,
                "product_name": row["product_name"],
                "product_name_basis": "source_reported_sample_name_from_provincial_quality_inspection",
                "model_specification_source_reported": row["model"],
                "model_specification_without_package": package_removed_model(row["model"]),
                "product_kind_source_reported": kind_zh, "product_kind_english": kind_en,
                "family_code": family_code, "technical": extracted,
                "production_date_or_batch_source_reported": " / ".join(unique([row["production_date"], row["batch"]])),
                "inspection_standards_scope_source_reported": [],
                "inspection_outcome": inspection_outcome,
                "inspection_retest_confirmed_nonconforming": False,
                "inspection_suspected_counterfeit": suspected_counterfeit,
                "nonconforming_items": split_failures(row["nonconforming_items_source_reported"]),
                "nonconforming_items_source_reported": row["nonconforming_items_source_reported"],
                "source_note": "",
                "lifecycle_status": f"official_{year}_jilin_inspection_{inspection_outcome}_at_test_current_market_status_unverified",
                "source_quality_flags": unique(flags),
                "source_facts_sha256": hashlib.sha256(
                    json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
                "evidence_status": f"official_government_{inspection_outcome}_product_inspection_observation",
            })

    expected_retained = sum(source["expected_rows"] - source["expected_excluded_fuels"] for source in SOURCES.values())
    if len(records) != expected_retained or len(excluded_fuels) != 11:
        raise RuntimeError(f"Expected {expected_retained} retained and 11 excluded rows")
    for year, source in SOURCES.items():
        year_rows = [row for row in records if row["source_id"] == source["source_id"]]
        if sum(row["inspection_outcome"] == "nonconforming" for row in year_rows) != source["expected_nonconforming"]:
            raise RuntimeError(f"Unexpected Jilin {year} nonconforming count")
        if sum(row["inspection_suspected_counterfeit"] for row in year_rows) != source["expected_suspected_counterfeit"]:
            raise RuntimeError(f"Unexpected Jilin {year} suspected-counterfeit count")
    if len({row["source_record_id"] for row in records}) != len(records):
        raise RuntimeError("Jilin source record identifiers are not unique")

    records.sort(key=lambda row: row["source_record_id"])
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_jilin_2024_2025_automotive_fluid_inspections_normalized",
        "snapshot_date": SNAPSHOT_DATE, "rights_url": RIGHTS_URL,
        "source_files": source_files,
        "source_all_rows": sum(source["expected_rows"] for source in SOURCES.values()),
        "retained_product_observations": len(records),
        "excluded_motor_fuel_rows": len(excluded_fuels),
        "excluded_motor_fuels": excluded_fuels,
        "unavailable_historical_source": UNAVAILABLE_2023_SOURCE,
        "source_counts": dict(sorted(Counter(row["source_id"] for row in records).items())),
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "suspected_counterfeit": sum(row["inspection_suspected_counterfeit"] for row in records),
        "product_kinds": dict(sorted(Counter(row["product_kind_english"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_api": sum(bool(row["technical"]["api_source_reported"]) for row in records),
        "rows_with_sae": sum(bool(row["technical"]["sae_source_reported"]) for row in records),
        "rows_with_acea": sum(bool(row["technical"]["acea_source_reported"]) for row in records),
        "rows_with_ilsac": sum(bool(row["technical"]["ilsac_source_reported"]) for row in records),
        "rows_with_brake_class": sum(bool(row["technical"]["brake_fluid_dot_source_reported"] or row["technical"]["brake_fluid_hzy_source_reported"]) for row in records),
        "rows_with_coolant_class": sum(bool(row["technical"]["coolant_class_source_reported"]) for row in records),
        "rows_with_coolant_freezing_point": sum(bool(row["technical"]["coolant_freezing_point_source_reported"]) for row in records),
        "rows_with_washer_class": sum(bool(row["technical"]["washer_fluid_class_source_reported"]) for row in records),
        "rows_with_washer_freezing_point": sum(bool(row["technical"]["washer_fluid_freezing_point_source_reported"]) for row in records),
        "rows_with_aus32": sum(bool(row["technical"]["urea_class_source_reported"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One output row is one inspected batch observation. Strict product identity is resolved later while every occurrence remains linked.",
        "scope_note": "All 415 official table rows were audited; 404 lubricant, coolant, brake, washer, urea and fuel-additive observations are retained and 11 motor-fuel rows are excluded.",
        "historical_gap_note": "The indexed official 2023 attachment currently returns HTTP 404 and is not represented as ingested data.",
        "privacy_note": "Retail sellers and inspected units are excluded from normalized records and factual hashes; only product-side facts are retained.",
        "lifecycle_note": "A conforming result applies only to the sampled batch and does not prove a current offer, recommendation or blanket approval.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
