#!/usr/bin/env python3
"""Normalize all 100 automotive-fluid rows in Shenzhen's 2025 inspection PDF."""

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
OUTPUT = ROOT / "data/shenzhen-2025-automotive-fluid-inspection.jsonl"
REPORT = ROOT / "data/shenzhen-2025-automotive-fluid-inspection-report.json"
SOURCE_ID = "SHENZHEN_CHINA_2025_AUTOMOTIVE_FLUID_INSPECTION"
SOURCE_URL = "https://www.sz.gov.cn/cn/xxgk/zfxxgj/tzgg/content/mpost_12770607.html"
ATTACHMENT_URL = "http://www.sz.gov.cn/attachment/1/1711/1711226/12770607.pdf"
RIGHTS_URL = "https://www.sz.gov.cn/cn/qt/gywm/"
EXPECTED_PDF_SHA256 = "6cb5b14209ad9717d4d790175889d5b19bb5917016f2449e6317d821a12a1905"
SNAPSHOT_DATE = "2026-07-21"
REPORT_DATE = "2026-05-09"

SOURCE_TYPES = {
    "润滑油": ("M", "motor-vehicle engine lubricating oil"),
    "冷却液": ("TF", "motor-vehicle coolant"),
    "车用尿素溶液": ("TF", "automotive aqueous urea solution"),
    "燃油添加剂": ("S", "automotive gasoline detergent additive"),
    "玻璃水": ("TF", "automotive windshield washer fluid"),
    "制动液": ("TF", "motor-vehicle brake fluid"),
}


def clean(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip()


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"/", "-", "—"} else value


def fetch() -> bytes:
    request = urllib.request.Request(ATTACHMENT_URL, headers={
        "User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0",
        "Referer": SOURCE_URL,
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_PDF_SHA256:
        raise RuntimeError(f"Shenzhen 2025 PDF changed: expected {EXPECTED_PDF_SHA256}, received {digest}")
    return payload


def producer(value: str) -> tuple[str, str]:
    source = clean(value)
    normalized = re.sub(r"^(?:委托方|分装|销售商|中国地区总运营商)[：:]\s*", "", source)
    return normalized, source


def source_rows(payload: bytes) -> list[dict]:
    rows = []
    with pdfplumber.open(io.BytesIO(payload)) as document:
        if len(document.pages) != 5:
            raise RuntimeError(f"Expected five PDF pages, received {len(document.pages)}")
        for page_number, page in enumerate(document.pages, 1):
            tables = page.extract_tables()
            if len(tables) != 1:
                raise RuntimeError(f"Expected one table on page {page_number}, received {len(tables)}")
            for values in tables[0]:
                values = [clean(value) for value in values]
                if len(values) != 9 or not values[0].isdigit() or values[1] not in SOURCE_TYPES:
                    continue
                rows.append({
                    "source_row": int(values[0]), "source_page": page_number,
                    "product_type": values[1], "product_name": values[3],
                    "brand_source_reported": empty_marker(values[4]), "model": values[5],
                    "production_date": empty_marker(values[6]), "producer": values[7],
                    "outcome_source_reported": values[8],
                })
    rows.sort(key=lambda row: row["source_row"])
    if len(rows) != 100 or len({row["source_row"] for row in rows}) != 100:
        raise RuntimeError(f"Expected 100 unique automotive rows, received {len(rows)}")
    return rows


def extract_technical(row: dict) -> tuple[dict, list[str]]:
    model = row["model"].upper().replace("Ⅱ", "II").replace("－", "-")
    flags = []
    if re.search(r"\bCL-4\b", model):
        model_for_api = re.sub(r"\bCL-4\b", "CI-4", model)
        flags.append("pdf_text_layer_lowercase_l_normalized_to_api_ci4")
    else:
        model_for_api = model
    api = re.findall(r"(?<![A-Z0-9])(CD|CF|CF-4|CH-4|CI-4|CJ-4|CK-4|SG|SJ|SL|SM|SN|SP|SQ)(?![A-Z0-9])", model_for_api)
    sae = [f"{winter}-{summer}" for winter, summer in re.findall(r"(?<![0-9])(0W|5W|10W|15W|20W|25W)\s*-?\s*([0-9]{2})(?![0-9])", model)]
    acea = re.findall(r"(?<![A-Z0-9])(A3/B4|C[235])(?![A-Z0-9])", model)
    ilsac = re.findall(r"GF-6A|GF-6", model)
    dot = [f"DOT {value}" for value in re.findall(r"DOT\s*-?\s*([345])", model)]
    hzy = [f"HZY{value}" for value in re.findall(r"HZY\s*([345])", model)]
    coolant = re.findall(r"(?:LEC|HEC|LOC)-II-(?:15|25|26|35|40|45|50)", model.replace(" ", ""))
    washer = []
    if "水基型" in row["model"]:
        washer = ["水基型低温型" if "低温型" in row["model"] else "水基型普通型"]
    urea = ["AUS 32"] if re.search(r"AUS\s*32", row["product_name"] + " " + row["model"], re.I) else []
    return {
        "api_source_reported": sorted(set(api)), "sae_source_reported": sorted(set(sae)),
        "acea_source_reported": sorted(set(acea)), "ilsac_source_reported": sorted(set(ilsac)),
        "brake_fluid_dot_source_reported": sorted(set(dot)),
        "brake_fluid_hzy_source_reported": sorted(set(hzy)),
        "coolant_class_source_reported": sorted(set(coolant)),
        "washer_fluid_class_source_reported": washer,
        "urea_class_source_reported": urea,
    }, flags


def brand(row: dict, producer_name: str) -> tuple[str, str]:
    source_brand = row["brand_source_reported"]
    if source_brand and source_brand not in {"图形", "图案"} and "图形" not in source_brand:
        return source_brand, "source_reported_text_brand"
    oem_prefixes = (
        ("BMW", "BMW"), ("丰田", "Toyota"), ("雷克萨斯", "Lexus"),
        ("一汽奥迪", "Audi"), ("奥迪", "Audi"), ("梅赛德斯-AMG", "Mercedes-AMG"),
        ("米其林", "Michelin"), ("解放", "FAW Jiefang"),
    )
    for prefix, value in oem_prefixes:
        if row["product_name"].startswith(prefix):
            return value, "brand_in_explicit_oem_product_name"
    return producer_name, "nominal_producer_fallback_no_usable_text_brand"


def package_removed_model(value: str) -> str:
    value = value.replace("毫升", "ml").replace("千克", "kg").replace("升", "l")
    value = re.sub(r"(?:\d+(?:\.\d+)?\s*(?:ml|mL|L|l|kg|KG|g))\s*/\s*(?:瓶|桶)", "", value)
    return clean(value).strip("，,、 ")


def main() -> None:
    payload = fetch()
    raw_rows = source_rows(payload)
    records = []
    for row in raw_rows:
        family_code, kind_en = SOURCE_TYPES[row["product_type"]]
        flags = ["official_2025_municipal_inspection_observation_not_current_catalog_offer"]
        if row["product_type"] == "润滑油" and "汽油复合剂" in row["product_name"]:
            family_code, kind_en = "S", "automotive gasoline detergent additive"
            flags.append("source_product_type_lubricant_corrected_to_fuel_additive_from_explicit_product_name")
        technical, technical_flags = extract_technical(row)
        flags.extend(technical_flags)
        producer_name, producer_source = producer(row["producer"])
        product_brand, brand_basis = brand(row, producer_name)
        outcome = "conforming" if row["outcome_source_reported"] == "合格" else "nonconforming"
        source_facts = {key: row[key] for key in sorted(row)}
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"SZ-CN-2025-{row['source_row']:03d}",
            "source_row": row["source_row"], "source_page": row["source_page"],
            "source_url": SOURCE_URL, "attachment_url": ATTACHMENT_URL, "rights_url": RIGHTS_URL,
            "snapshot_date": SNAPSHOT_DATE, "report_date": REPORT_DATE,
            "market": "China / Shenzhen",
            "manufacturer": producer_name, "manufacturer_source_reported": producer_source,
            "brand": product_brand, "brand_source_reported": row["brand_source_reported"],
            "brand_basis": brand_basis,
            "product_name": row["product_name"],
            "product_name_basis": "source_reported_sample_name_from_municipal_quality_inspection",
            "model_specification_source_reported": row["model"],
            "model_specification_without_package": package_removed_model(row["model"]),
            "product_kind_source_reported": row["product_type"],
            "product_kind_english": kind_en, "family_code": family_code,
            "technical": technical,
            "production_date_or_batch_source_reported": row["production_date"],
            "inspection_outcome": outcome,
            "inspection_retest_confirmed_nonconforming": False,
            "nonconforming_items": ["low-temperature cranking viscosity"] if outcome == "nonconforming" else [],
            "nonconforming_items_source_reported": "低温动力黏度" if outcome == "nonconforming" else "",
            "source_note": "",
            "lifecycle_status": f"official_2025_shenzhen_inspection_{outcome}_at_test_current_market_status_unverified",
            "source_quality_flags": flags,
            "source_facts_sha256": hashlib.sha256(json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            "evidence_status": f"official_government_{outcome}_product_inspection_observation",
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_shenzhen_2025_complete_automotive_fluid_inspection_normalized",
        "source_id": SOURCE_ID, "source_url": SOURCE_URL, "attachment_url": ATTACHMENT_URL,
        "snapshot_date": SNAPSHOT_DATE, "report_date": REPORT_DATE,
        "source_pdf_sha256": hashlib.sha256(payload).hexdigest(), "source_pdf_pages": 5,
        "source_all_rows": 246, "source_automotive_rows": len(records),
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "source_product_types": dict(sorted(Counter(row["product_kind_source_reported"] for row in records).items())),
        "families_before_identity_merging": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_api": sum(bool(row["technical"]["api_source_reported"]) for row in records),
        "rows_with_sae": sum(bool(row["technical"]["sae_source_reported"]) for row in records),
        "rows_with_acea": sum(bool(row["technical"]["acea_source_reported"]) for row in records),
        "rows_with_ilsac": sum(bool(row["technical"]["ilsac_source_reported"]) for row in records),
        "rows_with_brake_class": sum(bool(row["technical"]["brake_fluid_dot_source_reported"] or row["technical"]["brake_fluid_hzy_source_reported"]) for row in records),
        "rows_with_coolant_class": sum(bool(row["technical"]["coolant_class_source_reported"]) for row in records),
        "rows_with_washer_class": sum(bool(row["technical"]["washer_fluid_class_source_reported"]) for row in records),
        "rows_with_aus32": sum(bool(row["technical"]["urea_class_source_reported"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One output row is one inspected batch observation. The catalog builder merges only strict same producer + product + package-independent technical identity and preserves every occurrence.",
        "scope_note": "Exactly the 100 automotive-product rows are retained; 146 furniture, panel, plywood and drone rows are excluded by the official product-type column.",
        "lifecycle_note": "Conforming means only that the sampled batch passed this inspection. Neither outcome is treated as a current commercial offer or a blanket product approval.",
        "privacy_note": "Inspected retailers are excluded from normalized records; only nominal producer, product, brand, model and inspection provenance remain.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
