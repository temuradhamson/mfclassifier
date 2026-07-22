#!/usr/bin/env python3
"""Normalize Qingdao's 2021–2025 automotive-fluid inspection workbooks."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

import xlrd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/qingdao-2021-2025-automotive-fluid-inspections.jsonl"
REPORT = ROOT / "data/qingdao-2021-2025-automotive-fluid-inspections-report.json"
SNAPSHOT_DATE = "2026-07-22"
RIGHTS_URL = "https://www.qingdao.gov.cn/zwgk/xxgk/bgt/gkzn/"

PAGES = {
    "2021": {
        "source_id": "QINGDAO_CHINA_2021_AUTOMOTIVE_FLUID_INSPECTIONS",
        "source_url": "https://amr.qingdao.gov.cn/zwgk/tzgg/202111/t20211112_3817314.shtml",
        "report_date": "2021-11-12",
        "expected_relevant_rows": 9,
    },
    "2023": {
        "source_id": "QINGDAO_CHINA_2023_AUTOMOTIVE_FLUID_INSPECTIONS",
        "source_url": "https://amr.qingdao.gov.cn/zwgk/gggs/jgjcgs/202308/t20230822_7422566.shtml",
        "report_date": "2023-08-22",
        "expected_relevant_rows": 49,
    },
    "2024": {
        "source_id": "QINGDAO_CHINA_2024_AUTOMOTIVE_FLUID_INSPECTIONS",
        "source_url": "https://amr.qingdao.gov.cn/zwgk/gggs/jgjcgs/202409/t20240911_8258621.shtml",
        "report_date": "2024-09-11",
        "expected_relevant_rows": 45,
    },
    "2025_daily2": {
        "source_id": "QINGDAO_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTIONS_DAILY_2",
        "source_url": "https://amr.qingdao.gov.cn/zwgk/gggs/jgjcgs/202508/t20250804_9968842.shtml",
        "report_date": "2025-08-04",
        "expected_relevant_rows": 76,
    },
    "2025_daily4": {
        "source_id": "QINGDAO_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTIONS_DAILY_4",
        "source_url": "https://amr.qingdao.gov.cn/zwgk/gggs/jgjcgs/202511/t20251120_10372861.shtml",
        "report_date": "2025-11-20",
        "expected_relevant_rows": 20,
    },
    "2025_special4": {
        "source_id": "QINGDAO_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTIONS_SPECIAL_4",
        "source_url": "https://amr.qingdao.gov.cn/zwgk/gggs/jgjcgs/202512/t20251230_10426051.shtml",
        "report_date": "2025-12-30",
        "expected_relevant_rows": 40,
    },
    "2025_special6": {
        "source_id": "QINGDAO_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTIONS_SPECIAL_6",
        "source_url": "https://amr.qingdao.gov.cn/zwgk/gggs/jgjcgs/202512/t20251218_10410754.shtml",
        "report_date": "2025-12-18",
        "expected_relevant_rows": 23,
    },
}

# Every official workbook is pinned. The one fuel-only workbook is deliberately
# fetched and audited so a future content change cannot silently enter the catalog.
FILES = [
    ("2021", "coolant", "P020211112630106584956.xls", "8ad7db962d9a237277c6e1512b0ed8ecee5c56a6f54478080cdbc82fc33a53b7", 4),
    ("2021", "brake_fluid", "P020211112630110704088.xls", "4f65c28e38843cf41688f9ce5fbc7a377712c96acb2d7064bbb62a66239975a8", 1),
    ("2021", "engine_oil", "P020211112630118377847.xls", "86ae45b7c16c86ef82dacdb6316f06bfca35dbf97d6bfd4c7de39fad174248cb", 4),
    ("2023", "urea", "P020230822557282227031.xls", "c509b5570105e87063dc1280147afe5da8f984ceeed991773b09a564cf7a1952", 35),
    ("2023", "coolant", "P020230822557283243170.xls", "5f4e96580c76da5816edfcb6e869b4af32088b8d2e76dd74b809e9dd8b1e2ab7", 7),
    ("2023", "brake_fluid", "P020230822557283569793.xls", "b579f8c74d9614bd4d0b7f03320ab7e5f52ad480723f3b6d727cbe8ac0cabc08", 1),
    ("2023", "engine_oil", "P020230822557285339691.xls", "6b0ea8977cd276769f47b705a31904985d1a6e0cd1183255b7e1cd722be2113f", 6),
    ("2024", "urea", "P020240911511444161658.xls", "9944e5c1630109bd20d64cd918cef67e5dd3df864848cdd44c4d0a61968eadc1", 25),
    ("2024", "excluded_motor_fuel", "P020240911511444800035.xls", "80a396cced87f97e242235a65ebb9f5bc3045116fbdc702f9d85b3d4384422ed", 6),
    ("2024", "brake_fluid", "P020240911511446188778.xls", "d2f0e3ae0df1446c74247732c1283428c1792e8dbf8835be16a5ab4c2a438fb7", 20),
    ("2025_daily2", "diesel_engine_oil", "P020250804505998053149.xls", "af6f0c667365b59efa1be7e649f57d8f17c1246e77ec2a8862233dbdc08a00dc", 15),
    ("2025_daily2", "urea", "P020250804505998188416.xls", "a7078dbd4893cb04cdfb95725f8321342cf6f62df2a5a69a4c9734c9a7b3afda", 46),
    ("2025_daily2", "gasoline_engine_oil", "P020250804506001661093.xls", "22e2bbd650b27ef1aa118460414cf2b928277a975a966120cb96ac0bd43a5a5d", 15),
    ("2025_daily4", "washer_fluid", "P020251120349234072977.xls", "f4085d082f4861b907be24917f82e8fec4f20e8f105149e660f839d590e77395", 20),
    ("2025_special4", "coolant", "P020251208785362257189.xls", "adfb6a102ce55d9dfe09237440a4ffeb5a8ff481288d2975b189562d5260fff1", 20),
    ("2025_special4", "brake_fluid", "P020251208785362373318.xls", "2a87656f2054750c6e196ffc8d393d5937e94899908364d97bbe4e82150277ff", 20),
    ("2025_special6", "gasoline_detergent_additive", "P020251216787636134661.xls", "91e409157ec73527a49ef64833dfb170f31a476113a72ec5033f76a05379d2e9", 6),
    ("2025_special6", "vehicle_lubricant", "P020251216787636233154.xls", "c6efdabd90f0e9adc6919718c4c711c0c7c85af12e0583b57a844221cd81bf79", 17),
]

KIND = {
    "coolant": ("TF", "motor-vehicle engine coolant", "发动机冷却液"),
    "brake_fluid": ("TF", "motor-vehicle brake fluid", "机动车辆制动液"),
    "engine_oil": ("M", "motor-vehicle engine oil", "润滑油"),
    "diesel_engine_oil": ("M", "diesel engine oil", "柴油机油"),
    "gasoline_engine_oil": ("M", "gasoline engine oil", "汽油机油"),
    "urea": ("TF", "automotive aqueous urea solution", "车用尿素"),
    "washer_fluid": ("TF", "automotive windshield washer fluid", "汽车风窗玻璃清洗液"),
    "gasoline_detergent_additive": ("S", "automotive gasoline detergent additive", "车用汽油清净剂"),
}


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip()


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"/", "-", "--", "—", "——", "无", "未标注", "未注明"} else value


def attachment_url(page_key: str, filename: str, scheme: str = "https") -> str:
    if page_key == "2021":
        directory = "zwgk/tzgg/202111"
    elif page_key == "2023":
        directory = "zwgk/gggs/jgjcgs/202308"
    elif page_key == "2024":
        directory = "zwgk/gggs/jgjcgs/202409"
    elif page_key == "2025_daily2":
        directory = "zwgk/gggs/jgjcgs/202508"
    elif page_key == "2025_daily4":
        directory = "zwgk/gggs/jgjcgs/202511"
    else:
        directory = "zwgk/gggs/jgjcgs/202512"
    return f"{scheme}://amr.qingdao.gov.cn/{directory}/{filename}"


def fetch(page_key: str, filename: str, expected_sha256: str) -> bytes:
    request = urllib.request.Request(attachment_url(page_key, filename, "http"), headers={
        "User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0",
        "Referer": PAGES[page_key]["source_url"],
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise RuntimeError(f"Qingdao XLS changed for {filename}: expected {expected_sha256}, received {digest}")
    return payload


def source_rows(payload: bytes, expected_rows: int) -> tuple[str, str, list[dict]]:
    workbook = xlrd.open_workbook(file_contents=payload)
    populated = [sheet for sheet in workbook.sheets() if sheet.nrows]
    if len(populated) != 1:
        raise RuntimeError(f"Expected one populated worksheet, received {len(populated)}")
    sheet = populated[0]
    title = clean(sheet.cell_value(0, 0))
    scope = clean(sheet.cell_value(1, 0))
    headers = [clean(sheet.cell_value(4, column)) for column in range(sheet.ncols)]
    required = {"序号", "产品名称", "标称生产者名称", "生产日期或批号", "规格型号", "商标", "抽查结果", "不合格项目"}
    if not required.issubset(headers):
        raise RuntimeError(f"Unexpected Qingdao header in {title}: {headers!r}")
    index = {header: headers.index(header) for header in required}
    sampling_domain_index = headers.index("抽样领域") if "抽样领域" in headers else None
    inspected_unit_index = headers.index("受检单位名称") if "受检单位名称" in headers else None
    rows = []
    for row_index in range(5, sheet.nrows):
        serial = clean(sheet.cell_value(row_index, index["序号"]))
        if not re.fullmatch(r"\d+", serial):
            continue
        rows.append({
            "source_row": int(serial),
            "sampling_domain": clean(sheet.cell_value(row_index, sampling_domain_index)) if sampling_domain_index is not None else "",
            "inspected_unit": clean(sheet.cell_value(row_index, inspected_unit_index)) if inspected_unit_index is not None else "",
            "product_name": clean(sheet.cell_value(row_index, index["产品名称"])),
            "producer": empty_marker(sheet.cell_value(row_index, index["标称生产者名称"])),
            "production_date_or_batch": empty_marker(sheet.cell_value(row_index, index["生产日期或批号"])),
            "model": empty_marker(sheet.cell_value(row_index, index["规格型号"])),
            "brand_source_reported": empty_marker(sheet.cell_value(row_index, index["商标"])),
            "outcome_source_reported": clean(sheet.cell_value(row_index, index["抽查结果"])),
            "nonconforming_items_source_reported": empty_marker(sheet.cell_value(row_index, index["不合格项目"])),
        })
    if len(rows) != expected_rows or len({row["source_row"] for row in rows}) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} rows in {title}, received {len(rows)}")
    return title, scope, rows


def family_and_kind(file_kind: str, product_name: str) -> tuple[str, str, str]:
    if file_kind != "vehicle_lubricant":
        return KIND[file_kind]
    if "液压油" in product_name:
        return "H", "anti-wear hydraulic oil", "抗磨液压油"
    if "齿轮油" in product_name:
        return "T", "automotive gear oil", "车辆齿轮油"
    raise RuntimeError(f"Unclassified vehicle lubricant: {product_name}")


def manufacturer(row: dict) -> tuple[str, str, str]:
    source = row["producer"]
    if source:
        return source, source, "source_reported_nominal_producer"
    if row["sampling_domain"] == "生产领域" and row["inspected_unit"]:
        return row["inspected_unit"], "", "source_inspected_production_enterprise_used_as_producer"
    usable_brand = row["brand_source_reported"]
    if usable_brand and "图形" not in usable_brand:
        return usable_brand, "", "source_text_brand_fallback_producer_unreported"
    return f"未标注生产单位｜{row['product_name']}", "", "product_scoped_placeholder_source_producer_unreported"


def brand(row: dict, producer: str) -> tuple[str, str]:
    source = row["brand_source_reported"]
    if source and "图形" not in source and source not in {"图案", "图案商标"}:
        return source, "source_reported_text_brand"
    prefixes = (
        ("壳牌", "Shell"), ("上汽大众", "SAIC Volkswagen"), ("潍柴", "Weichai"),
        ("布雷博", "Brembo"), ("康普顿", "Copton"), ("昆仑之星", "Kunlun Star"),
        ("蓝星", "Bluestar"), ("美孚", "Mobil"),
    )
    for prefix, value in prefixes:
        if row["product_name"].startswith(prefix):
            return value, "brand_in_explicit_product_name"
    return producer, "nominal_producer_fallback_no_usable_text_brand"


def unique(values: list[str]) -> list[str]:
    return sorted({clean(value) for value in values if clean(value)})


def technical(row: dict, file_kind: str, family_code: str) -> tuple[dict, list[str]]:
    source = f"{row['product_name']} {row['model']}"
    normalized = (
        source.upper().replace("Ⅱ", "II").replace("－", "-").replace("–", "-")
        .replace("−", "-").replace("／", "/").replace("；", ";")
    )
    flags = []
    sae = [
        f"{winter}-{summer}" for winter, summer in re.findall(
            r"(?<![0-9])(0W|5W|10W|15W|20W|25W)\s*[-/]?\s*(20|30|40|50|60)(?![0-9])", normalized
        )
    ]
    if family_code == "T":
        sae.extend(
            f"{winter}W-{summer}" for winter, summer in re.findall(
                r"(?<![0-9])(70|75|80|85)W?\s*[-/]?\s*(80|85|90|110|140|190|250)(?![0-9])", normalized
            )
        )
    api = re.findall(
        r"(?<![A-Z0-9])(CF-4|CG-4|CH-4|CI-4|CJ-4|CK-4|SP|SN|SM|SL|SJ|SG|SF|CF|CD)(?![A-Z0-9])",
        normalized,
    )
    if re.search(r"(?<![A-Z0-9])CH-4\+(?![A-Z0-9])", normalized):
        flags.append("source_nonstandard_api_ch4_plus_suffix_preserved_in_model_normalized_to_api_ch4")
    api_gl = [f"GL-{grade}" for grade in re.findall(r"(?<![A-Z0-9])GL\s*-?\s*([1-6])(?![0-9])", normalized)]
    china_class = []
    iso_vg = []
    for prefix, grade in re.findall(r"(?<![A-Z0-9])(L-?H[MV])\s*-?\s*(\d{2,3})#?", normalized):
        prefix = prefix.replace("LH", "L-H") if "-" not in prefix else prefix
        china_class.append(f"{prefix} {grade}")
        iso_vg.append(grade)
    if family_code == "H" and not china_class:
        for prefix, grade in re.findall(r"(?<![A-Z0-9])(HM|HV)\s*-?\s*(\d{2,3})#?", normalized):
            china_class.append(f"L-{prefix} {grade}")
            iso_vg.append(grade)
            flags.append("source_hydraulic_class_without_l_prefix_normalized_to_china_l_class")
    if family_code == "H" and not iso_vg:
        grades = re.findall(r"(?<![0-9])(46|68)#(?![0-9])", normalized)
        iso_vg.extend(grades)
        if grades:
            flags.append("hydraulic_iso_vg_from_explicit_hash_grade_notation")
    dot = [f"DOT {grade}" for grade in re.findall(r"DOT\s*-?\s*([3-5])\+?", normalized)]
    hzy = [f"HZY{grade}" for grade in re.findall(r"HZY\s*-?\s*([3-6])", normalized)]
    coolant = []
    for prefix, grade in re.findall(r"(?<![A-Z])(LEC|HEC|LOC)\s*-?\s*II\s*-?\s*(15|25|26|30|35|40|45|50)?", normalized):
        coolant.append(f"{prefix}-II" + (f"-{grade}" if grade else ""))
    freezing = []
    if file_kind in {"coolant", "washer_fluid"}:
        freezing.extend(f"{int(value)} °C" for value in re.findall(r"(?<![0-9])(-?\d{1,2})\s*℃", normalized))
        for value in re.findall(r"(?<![0-9])(-\d{1,2})(?![0-9])", normalized):
            freezing.append(f"{int(value)} °C")
        if file_kind == "coolant":
            freezing.extend(f"-{grade} °C" for grade in re.findall(r"(?:LEC|HEC|LOC)\s*-?\s*II\s*-?\s*(15|25|26|30|35|40|45|50)", normalized))
    washer = []
    if file_kind == "washer_fluid":
        if "水基" in source:
            washer.append("水基型")
        if "普通型" in source:
            washer.append("普通型")
        if "夏季型" in source:
            washer.append("夏季型")
    urea = []
    if file_kind == "urea":
        urea = ["AUS 32"]
        if not re.search(r"AUS\s*32|ADBLUE", normalized):
            flags.append("aus32_derived_from_official_automotive_urea_inspection_scope")
    return {
        "api_source_reported": unique(api),
        "api_gl_source_reported": unique(api_gl),
        "sae_source_reported": unique(sae),
        "iso_vg_source_reported": unique(iso_vg),
        "china_lubricant_class_source_reported": unique(china_class),
        "acea_source_reported": [], "jaso_source_reported": [], "ilsac_source_reported": [],
        "oem_approval_source_reported": [],
        "brake_fluid_dot_source_reported": unique(dot),
        "brake_fluid_hzy_source_reported": unique(hzy),
        "coolant_class_source_reported": unique(coolant),
        "coolant_freezing_point_source_reported": unique(freezing) if file_kind == "coolant" else [],
        "washer_fluid_class_source_reported": unique(washer),
        "washer_fluid_freezing_point_source_reported": unique(freezing) if file_kind == "washer_fluid" else [],
        "urea_class_source_reported": urea,
    }, flags


def package_removed_model(value: str) -> str:
    value = value.replace("毫升", "mL").replace("千克", "kg").replace("公斤", "kg").replace("升", "L")
    value = re.sub(r"\b\d+(?:\.\d+)?\s*(?:mL|L|kg|g)\s*/\s*(?:瓶|桶|罐|盒)", "", value, flags=re.I)
    return clean(value).strip("，,、 ：:;；/")


def split_failures(value: str) -> list[str]:
    return unique([part for part in re.split(r"[;；、]", value) if clean(part)])


def outcome(value: str) -> str:
    return "nonconforming" if "不合格" in value else "conforming"


def main() -> None:
    records = []
    file_report = []
    excluded_fuel_rows = 0
    for page_key, file_kind, filename, expected_sha256, expected_rows in FILES:
        page = PAGES[page_key]
        payload = fetch(page_key, filename, expected_sha256)
        title, scope, rows = source_rows(payload, expected_rows)
        file_report.append({
            "page_key": page_key, "file_kind": file_kind, "title": title,
            "attachment_url": attachment_url(page_key, filename), "source_xls_sha256": expected_sha256,
            "source_rows": len(rows),
        })
        if file_kind == "excluded_motor_fuel":
            if {row["product_name"] for row in rows} - {"车用汽油", "车用柴油"}:
                raise RuntimeError("The excluded Qingdao fuel workbook contains a non-fuel product")
            excluded_fuel_rows += len(rows)
            continue
        for row in rows:
            family_code, kind_en, kind_zh = family_and_kind(file_kind, row["product_name"])
            producer, producer_source, producer_basis = manufacturer(row)
            product_brand, brand_basis = brand(row, producer)
            extracted, technical_flags = technical(row, file_kind, family_code)
            inspection_outcome = outcome(row["outcome_source_reported"])
            flags = [
                f"official_{page_key[:4]}_municipal_inspection_observation_not_current_catalog_offer",
                "source_xls_not_redistributed_factual_fields_only",
                *technical_flags,
            ]
            if producer_basis == "source_inspected_production_enterprise_used_as_producer":
                flags.append("production_domain_inspected_enterprise_is_product_manufacturer")
            if inspection_outcome == "nonconforming":
                flags.append("nonconforming_product_do_not_treat_as_approved_or_recommended")
            source_facts = {key: row[key] for key in sorted(row) if key != "inspected_unit"}
            records.append({
                "source_id": page["source_id"],
                "source_record_id": f"QD-CN-{page_key.upper()}-{Path(filename).stem[-12:]}-{row['source_row']:03d}",
                "source_row": row["source_row"], "source_workbook_kind": file_kind,
                "source_url": page["source_url"], "attachment_url": attachment_url(page_key, filename),
                "rights_url": RIGHTS_URL, "snapshot_date": SNAPSHOT_DATE, "report_date": page["report_date"],
                "market": "China / Qingdao",
                "manufacturer": producer, "manufacturer_source_reported": producer_source,
                "manufacturer_basis": producer_basis,
                "brand": product_brand, "brand_source_reported": row["brand_source_reported"],
                "brand_basis": brand_basis,
                "product_name": row["product_name"],
                "product_name_basis": "source_reported_sample_name_from_municipal_quality_inspection",
                "model_specification_source_reported": row["model"],
                "model_specification_without_package": package_removed_model(row["model"]),
                "product_kind_source_reported": kind_zh, "product_kind_english": kind_en,
                "family_code": family_code, "technical": extracted,
                "production_date_or_batch_source_reported": row["production_date_or_batch"],
                "inspection_standards_scope_source_reported": unique(re.findall(r"(?:GB|Q/)\s*[A-Z0-9/.-]+(?:\s+[A-Z0-9/.-]+)?", scope, re.I)),
                "inspection_outcome": inspection_outcome,
                "inspection_retest_confirmed_nonconforming": False,
                "nonconforming_items": split_failures(row["nonconforming_items_source_reported"]),
                "nonconforming_items_source_reported": row["nonconforming_items_source_reported"],
                "source_note": "",
                "lifecycle_status": f"official_{page_key[:4]}_qingdao_inspection_{inspection_outcome}_at_test_current_market_status_unverified",
                "source_quality_flags": unique(flags),
                "source_facts_sha256": hashlib.sha256(json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "evidence_status": f"official_government_{inspection_outcome}_product_inspection_observation",
            })

    records.sort(key=lambda row: row["source_record_id"])
    expected_page_counts = {page["source_id"]: page["expected_relevant_rows"] for page in PAGES.values()}
    actual_page_counts = dict(sorted(Counter(row["source_id"] for row in records).items()))
    if actual_page_counts != dict(sorted(expected_page_counts.items())):
        raise RuntimeError(f"Unexpected Qingdao page counts: {actual_page_counts!r}")
    if len(records) != 262 or excluded_fuel_rows != 6:
        raise RuntimeError(f"Expected 262 retained and six excluded rows, received {len(records)} and {excluded_fuel_rows}")
    if len({row["source_record_id"] for row in records}) != len(records):
        raise RuntimeError("Qingdao source record identifiers are not unique")

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_qingdao_2021_2025_automotive_fluid_inspections_normalized",
        "snapshot_date": SNAPSHOT_DATE, "rights_url": RIGHTS_URL,
        "source_pages": {key: value["source_url"] for key, value in PAGES.items()},
        "source_files": file_report, "source_workbooks": len(FILES),
        "source_all_rows": len(records) + excluded_fuel_rows,
        "retained_product_observations": len(records), "excluded_motor_fuel_rows": excluded_fuel_rows,
        "source_counts": actual_page_counts,
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "product_kinds": dict(sorted(Counter(row["product_kind_source_reported"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_api": sum(bool(row["technical"]["api_source_reported"]) for row in records),
        "rows_with_api_gl": sum(bool(row["technical"]["api_gl_source_reported"]) for row in records),
        "rows_with_sae": sum(bool(row["technical"]["sae_source_reported"]) for row in records),
        "rows_with_iso_vg": sum(bool(row["technical"]["iso_vg_source_reported"]) for row in records),
        "rows_with_china_lubricant_class": sum(bool(row["technical"]["china_lubricant_class_source_reported"]) for row in records),
        "rows_with_brake_class": sum(bool(row["technical"]["brake_fluid_dot_source_reported"] or row["technical"]["brake_fluid_hzy_source_reported"]) for row in records),
        "rows_with_coolant_class": sum(bool(row["technical"]["coolant_class_source_reported"]) for row in records),
        "rows_with_coolant_freezing_point": sum(bool(row["technical"]["coolant_freezing_point_source_reported"]) for row in records),
        "rows_with_washer_class": sum(bool(row["technical"]["washer_fluid_class_source_reported"]) for row in records),
        "rows_with_washer_freezing_point": sum(bool(row["technical"]["washer_fluid_freezing_point_source_reported"]) for row in records),
        "rows_with_aus32": sum(bool(row["technical"]["urea_class_source_reported"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One output row is one inspected batch observation. Strict product identity is resolved later while every batch occurrence remains linked.",
        "scope_note": "All 262 relevant rows from 17 official workbooks are retained. Six gasoline/diesel-fuel rows in the eighteenth workbook are audited and excluded.",
        "lifecycle_note": "A conforming result means only that the sampled batch passed this inspection; it is not a current offer, recommendation or blanket approval.",
        "privacy_note": "Retail sellers, enterprise identifiers, addresses, districts, sampling dates and laboratories are excluded. A production-domain inspected enterprise is retained only when it is the product manufacturer and the nominal-producer cell is empty.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
