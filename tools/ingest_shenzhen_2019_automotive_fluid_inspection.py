#!/usr/bin/env python3
"""Normalize all 60 automotive-fluid rows in Shenzhen's 2019 inspection XLS files."""

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
OUTPUT = ROOT / "data/shenzhen-2019-automotive-fluid-inspection.jsonl"
REPORT = ROOT / "data/shenzhen-2019-automotive-fluid-inspection-report.json"
SOURCE_ID = "SHENZHEN_CHINA_2019_AUTOMOTIVE_FLUID_INSPECTION"
SOURCE_URL = "https://www.sz.gov.cn/cn/xxgk/zfxxgj/scjg/cpzljy/content/post_6601774.html"
CONFORMING_URL = "http://www.sz.gov.cn/attachment/0/452/452428/6601774.xls"
NONCONFORMING_URL = "http://www.sz.gov.cn/attachment/0/452/452430/6601774.xls"
RIGHTS_URL = "https://www.sz.gov.cn/cn/qt/gywm/"
EXPECTED_SHA256 = {
    "conforming": "838dec55b34970ddbd4e6ccdcd7654f2551940c0104d676c5a631bd0cbb8b81e",
    "nonconforming": "cae0176f84915f288d929ef9e2bfd372475b96ff0670519bc6d154eb283ed846",
}
SNAPSHOT_DATE = "2026-07-22"
REPORT_DATE = "2019-12-25"
INSPECTION_STANDARDS = {
    "车用尿素溶液": ["GB 29518-2013"],
    "机动车制动液": ["GB 12981-2012"],
    "车用燃油添加剂": ["GB 19592-2004", "SZJG 11-2004", "GB/T 32859-2016"],
}


def clean(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip()


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"/", "-", "—"} else value


def fetch(url: str, expected_sha256: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0",
        "Referer": SOURCE_URL,
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise RuntimeError(f"Shenzhen 2019 XLS changed: expected {expected_sha256}, received {digest}")
    return payload


def manufacturer(value: object) -> tuple[str, str]:
    source = clean(value)
    normalized = re.sub(r"^(?:进口商|委托方|分装|销售商|经销商|出品)[：:]\s*", "", source)
    normalized = re.sub(r"有限公司出品$", "有限公司", normalized)
    return normalized, source


def classify(name: str, model: str) -> tuple[str, str, str]:
    joined = name + " " + model
    if any(token in joined for token in ("制动液", "刹车油", "刹车液", "离合器液")):
        return "TF", "机动车制动液", "motor-vehicle brake or clutch fluid"
    if any(token in joined for token in ("尿素", "尾气净化液", "尾气处理液", "氮氧化物还原剂")) or re.search(r"AUS\s*3[02]", joined, re.I):
        return "TF", "车用尿素溶液", "automotive aqueous urea solution"
    if any(token in joined for token in ("燃油", "汽油", "柴油复合剂", "喷油嘴", "气门")):
        return "S", "车用燃油添加剂", "automotive fuel detergent additive"
    raise RuntimeError(f"Unclassified Shenzhen 2019 product: {name!r} / {model!r}")


def technical(name: str, model: str) -> tuple[dict, list[str]]:
    joined = f"{name} {model}".upper().replace("－", "-").replace("／", "/")
    flags = []
    if re.search(r"D0T\s*-?\s*[345]", joined):
        flags.append("source_dot_zero_typo_normalized_to_dot")
    dot = [f"DOT {value}" for value in re.findall(r"D[O0]T\s*-?\s*([345])", joined)]
    hzy = [f"HZY{value}" for value in re.findall(r"HZY\s*([3456])", joined)]
    env = [f"ENV{value}" for value in re.findall(r"ENV\s*([46])", joined)]
    urea = []
    for value in re.findall(r"AUS\s*(30|32)", joined):
        urea.append(f"AUS {value}")
        if value == "30":
            flags.append("source_reported_atypical_aus30_not_normalized_to_aus32")
    return {
        "api_source_reported": [], "sae_source_reported": [],
        "acea_source_reported": [], "ilsac_source_reported": [],
        "brake_fluid_dot_source_reported": sorted(set(dot)),
        "brake_fluid_hzy_source_reported": sorted(set(hzy)),
        "brake_fluid_env_source_reported": sorted(set(env)),
        "coolant_class_source_reported": [],
        "coolant_freezing_point_source_reported": [],
        "washer_fluid_class_source_reported": [],
        "urea_class_source_reported": sorted(set(urea)),
    }, flags


def usable_brand(value: str) -> tuple[str, bool]:
    without_private_use = re.sub(r"[\ue000-\uf8ff]", " ", empty_marker(value))
    normalized = clean(without_private_use)
    return normalized, normalized != empty_marker(value)


def brand(source_brand: str, name: str, producer: str) -> tuple[str, str, list[str]]:
    normalized_brand, had_private_use = usable_brand(source_brand)
    flags = ["private_use_trademark_glyph_removed_from_normalized_brand"] if had_private_use else []
    if normalized_brand and normalized_brand not in {"图形", "图案", "图案商标", "图形商标"}:
        return normalized_brand, "source_reported_text_brand", flags
    prefixes = (
        ("奥迪", "Audi"), ("梅赛德斯-奔驰", "Mercedes-Benz"),
        ("博世", "Bosch"), ("江铃", "JMC"), ("雪佛龙", "Chevron"),
    )
    for prefix, normalized in prefixes:
        if name.startswith(prefix):
            return normalized, "brand_in_explicit_oem_product_name", flags
    return producer, "nominal_producer_fallback_no_usable_text_brand", flags


def package_removed_model(value: str) -> str:
    value = value.replace("毫升", "ml").replace("千克", "kg").replace("公斤", "kg").replace("升", "l")
    value = re.sub(r"\d+(?:\.\d+)?\s*(?:ml|mL|L|l|kg|KG|g)(?:\s*/\s*(?:支|瓶|桶|罐|盒))?(?:\s*[×xX]\s*\d+)?", "", value)
    value = re.sub(r"(?:^|\s)合格$", "", value)
    return clean(value).strip("，,、 ：:;；")


def split_failures(value: str) -> list[str]:
    value = clean(value)
    if not value:
        return []
    value = re.sub(r"(?:^|[、；;])\s*\d+[、.]\s*", ";", value)
    return [clean(part) for part in value.strip(";").split(";") if clean(part)]


def workbook_rows(payload: bytes, outcome: str) -> list[dict]:
    sheet = xlrd.open_workbook(file_contents=payload).sheet_by_name("汇总表")
    header = tuple(clean(sheet.cell_value(2, column)) for column in range(sheet.ncols))
    if header[:4] != ("序号", "受检单位名称", "样品名称", "标称商标"):
        raise RuntimeError(f"Unexpected Shenzhen 2019 columns: {header!r}")
    rows = []
    for row_number in range(3, sheet.nrows):
        values = [sheet.cell_value(row_number, column) for column in range(sheet.ncols)]
        if not isinstance(values[0], float) or not values[0].is_integer():
            continue
        rows.append({
            "source_row": int(values[0]), "product_name": clean(values[2]),
            "brand_source_reported": empty_marker(values[3]), "model": empty_marker(values[4]),
            "production_date": empty_marker(values[5]), "producer": clean(values[6]),
            "outcome_source_reported": clean(values[7]),
            "nonconforming_items_source_reported": clean(values[8]) if outcome == "nonconforming" else "",
            "source_note": empty_marker(values[9]) if outcome == "nonconforming" else empty_marker(values[8]),
            "source_workbook": outcome,
        })
    expected_count = 51 if outcome == "conforming" else 9
    if len(rows) != expected_count:
        raise RuntimeError(f"Expected {expected_count} {outcome} rows, received {len(rows)}")
    return rows


def main() -> None:
    payloads = {
        "conforming": fetch(CONFORMING_URL, EXPECTED_SHA256["conforming"]),
        "nonconforming": fetch(NONCONFORMING_URL, EXPECTED_SHA256["nonconforming"]),
    }
    raw_rows = []
    for outcome, payload in payloads.items():
        raw_rows.extend(workbook_rows(payload, outcome))

    records = []
    for row in raw_rows:
        outcome = row["source_workbook"]
        family, kind_zh, kind_en = classify(row["product_name"], row["model"])
        extracted, technical_flags = technical(row["product_name"], row["model"])
        producer, producer_source = manufacturer(row["producer"])
        product_brand, brand_basis, brand_flags = brand(row["brand_source_reported"], row["product_name"], producer)
        record_marker = "C" if outcome == "conforming" else "NC"
        flags = ["official_2019_municipal_inspection_observation_not_current_catalog_offer", *technical_flags, *brand_flags]
        if re.search(r"(?:^|\s)合格$", row["model"]):
            flags.append("source_model_conformity_word_not_treated_as_technical_specification")
        if "5inl" in row["product_name"]:
            flags.append("source_product_name_5inl_retained_without_silent_correction")
        if outcome == "nonconforming":
            flags.append("nonconforming_product_do_not_treat_as_approved_or_recommended")
        source_facts = {key: row[key] for key in sorted(row)}
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"SZ-CN-2019-{record_marker}-{row['source_row']:03d}",
            "source_row": row["source_row"], "source_workbook": outcome,
            "source_url": SOURCE_URL,
            "attachment_url": CONFORMING_URL if outcome == "conforming" else NONCONFORMING_URL,
            "rights_url": RIGHTS_URL, "snapshot_date": SNAPSHOT_DATE, "report_date": REPORT_DATE,
            "market": "China / Shenzhen", "manufacturer": producer,
            "manufacturer_source_reported": producer_source,
            "brand": product_brand, "brand_source_reported": row["brand_source_reported"],
            "brand_basis": brand_basis, "product_name": row["product_name"],
            "product_name_basis": "source_reported_sample_name_from_municipal_quality_inspection",
            "model_specification_source_reported": row["model"],
            "model_specification_without_package": package_removed_model(row["model"]),
            "product_kind_source_reported": kind_zh, "product_kind_english": kind_en,
            "family_code": family, "technical": extracted,
            "inspection_standards_scope_source_reported": INSPECTION_STANDARDS[kind_zh],
            "production_date_or_batch_source_reported": row["production_date"],
            "inspection_outcome": outcome, "inspection_retest_confirmed_nonconforming": False,
            "nonconforming_items": split_failures(row["nonconforming_items_source_reported"]),
            "nonconforming_items_source_reported": row["nonconforming_items_source_reported"],
            "source_note": row["source_note"],
            "lifecycle_status": f"official_2019_shenzhen_inspection_{outcome}_at_test_current_market_status_unverified",
            "source_quality_flags": sorted(set(flags)),
            "source_facts_sha256": hashlib.sha256(json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            "evidence_status": f"official_government_{outcome}_product_inspection_observation",
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_shenzhen_2019_complete_automotive_fluid_inspection_normalized",
        "source_id": SOURCE_ID, "source_url": SOURCE_URL,
        "attachment_urls": {"conforming": CONFORMING_URL, "nonconforming": NONCONFORMING_URL},
        "snapshot_date": SNAPSHOT_DATE, "report_date": REPORT_DATE,
        "source_xls_sha256": {key: hashlib.sha256(value).hexdigest() for key, value in payloads.items()},
        "source_rows": len(records),
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "source_product_types": dict(sorted(Counter(row["product_kind_source_reported"] for row in records).items())),
        "outcomes_by_product_type": {
            kind: dict(sorted(Counter(row["inspection_outcome"] for row in records if row["product_kind_source_reported"] == kind).items()))
            for kind in sorted({row["product_kind_source_reported"] for row in records})
        },
        "families_before_identity_merging": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_brake_class": sum(bool(row["technical"]["brake_fluid_dot_source_reported"] or row["technical"]["brake_fluid_hzy_source_reported"] or row["technical"]["brake_fluid_env_source_reported"]) for row in records),
        "rows_with_aus32": sum("AUS 32" in row["technical"]["urea_class_source_reported"] for row in records),
        "rows_with_atypical_aus30": sum("AUS 30" in row["technical"]["urea_class_source_reported"] for row in records),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One output row is one inspected batch observation. Product identities merge later only under strict producer, product and package-independent technical identity while every occurrence remains linked.",
        "scope_note": "Both official workbooks are complete: all 51 conforming and all nine nonconforming rows are retained, matching the official 20 urea + 20 fuel-additive + 20 brake-fluid program totals.",
        "lifecycle_note": "No-problem-found means only that the sampled batch passed this inspection. Neither outcome is treated as a current offer or blanket approval.",
        "privacy_note": "Inspected retailers are excluded; nominal producer, product, brand, model, batch date, outcome and failure facts are retained.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
