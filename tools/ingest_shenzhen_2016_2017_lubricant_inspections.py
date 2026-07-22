#!/usr/bin/env python3
"""Normalize all 140 rows in Shenzhen's 2016 and 2017 lubricant inspections."""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/shenzhen-2016-2017-lubricant-inspections.jsonl"
REPORT = ROOT / "data/shenzhen-2016-2017-lubricant-inspections-report.json"
SNAPSHOT_DATE = "2026-07-22"
RIGHTS_URL = "https://www.sz.gov.cn/cn/qt/gywm/"
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

SOURCES = {
    "2016": {
        "source_id": "SHENZHEN_CHINA_2016_LUBRICANT_INSPECTION",
        "source_url": "https://www.sz.gov.cn/szzt2010/zdlyzl/zlzscqjg/chcgg/content/post_1345944.html",
        "report_date": "2017-04-27",
        "expected_counts": {"conforming": 72, "nonconforming": 8},
        "documents": {
            "conforming": {
                "attachment_url": "https://www.sz.gov.cn/attachment/0/105/105065/1345944.docx",
                "download_url": "http://www.sz.gov.cn/attachment/0/105/105065/1345944.docx",
                "sha256": "c59935f376802184ee4940e75b713f649b1973ae499143e7b571510384702667",
            },
            "nonconforming": {
                "attachment_url": "https://www.sz.gov.cn/attachment/0/105/105066/1345944.docx",
                "download_url": "http://www.sz.gov.cn/attachment/0/105/105066/1345944.docx",
                "sha256": "ae6eca3c2743e7818d788e72e49bb32e0d7791f9a67b0e25916a4a9d48d5b9b2",
            },
        },
    },
    "2017": {
        "source_id": "SHENZHEN_CHINA_2017_LUBRICANT_INSPECTION",
        "source_url": "https://www.sz.gov.cn/szzt2010/wgkzl/glgk/jgxxgk/zljg/content/post_1352727.html",
        "report_date": "2017-11-15",
        "expected_counts": {"conforming": 57, "nonconforming": 3},
        "documents": {
            "conforming": {
                "attachment_url": "https://www.sz.gov.cn/attachment/0/111/111069/1352727.docx",
                "download_url": "http://www.sz.gov.cn/attachment/0/111/111069/1352727.docx",
                "sha256": "d479a8a3741f378d3c862f662568297c9ec0865d2f7ba6cfe0058804f55aac36",
            },
            "nonconforming": {
                "attachment_url": "https://www.sz.gov.cn/attachment/0/111/111070/1352727.docx",
                "download_url": "http://www.sz.gov.cn/attachment/0/111/111070/1352727.docx",
                "sha256": "fe9b52eac18678cd2dc96cc3e02adbfaf56efc29c1397ad8cc398b8ede8b4e35",
            },
        },
    },
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def empty_marker(value: object) -> str:
    value = clean(value)
    return "" if value in {"/", "-", "——", "—", "无", "无标注", "未标注"} else value


def fetch(url: str, expected_sha256: str, referer: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 MFClassifierResearch/1.0",
        "Referer": referer,
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise RuntimeError(f"Shenzhen DOCX changed: expected {expected_sha256}, received {digest}")
    return payload


def docx_rows(payload: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    tables = root.findall(".//w:tbl", WORD_NS)
    if len(tables) != 1:
        raise RuntimeError(f"Expected one DOCX table, received {len(tables)}")
    rows = []
    for table_row in tables[0].findall("./w:tr", WORD_NS):
        values = []
        for cell in table_row.findall("./w:tc", WORD_NS):
            values.append(clean("".join(node.text or "" for node in cell.findall(".//w:t", WORD_NS))))
        rows.append(values)
    return rows


def source_rows(year: str, outcome: str, payload: bytes) -> list[dict]:
    rows = docx_rows(payload)
    expected_header = ("序号", "受检单位名称", "样品名称")
    if tuple(rows[0][:3]) != expected_header or len(rows[0]) != 8:
        raise RuntimeError(f"Unexpected Shenzhen {year} {outcome} header: {rows[0]!r}")
    normalized = []
    for values in rows[1:]:
        if len(values) != 8 or not values[0].isdigit():
            raise RuntimeError(f"Unexpected Shenzhen {year} table row: {values!r}")
        normalized.append({
            "source_row": int(values[0]),
            "product_name": values[2],
            "brand_source_reported": empty_marker(values[3]),
            "model": empty_marker(values[4]),
            "production_date": empty_marker(values[5]),
            "producer": empty_marker(values[6]),
            "outcome_source_reported": values[7],
            "nonconforming_items_source_reported": values[7] if outcome == "nonconforming" else "",
            "source_workbook": outcome,
        })
    expected = SOURCES[year]["expected_counts"][outcome]
    if len(normalized) != expected:
        raise RuntimeError(f"Expected {expected} Shenzhen {year} {outcome} rows, received {len(normalized)}")
    return normalized


def manufacturer(value: str, brand_value: str, product_name: str) -> tuple[str, str, str]:
    source = clean(value)
    normalized = re.sub(r"^(?:灌装厂|销售商|进口商|服务中心)[：:]\s*", "", source)
    normalized = re.sub(r"(?:有限公司)?(?:装制|出品)$", lambda match: "有限公司" if match.group(0).startswith("有限公司") else "", normalized)
    normalized = clean(normalized).strip("/，,;；")
    if normalized:
        return normalized, source, "source_reported_nominal_producer_cleaned_of_role_prefix"
    usable_brand = clean(brand_value)
    if usable_brand and usable_brand not in {"图形", "图案", "图形商标", "图案商标"}:
        return usable_brand, source, "source_text_brand_fallback_producer_unreported"
    return f"未标注生产单位｜{clean(product_name)}", source, "product_scoped_placeholder_source_producer_unreported"


def brand(value: str, product_name: str, producer: str) -> tuple[str, str, list[str]]:
    source = clean(value)
    flags = []
    if source.lower() == "guif":
        return "Gulf", "source_guif_typo_normalized_to_gulf", ["source_guif_typo_normalized_to_gulf"]
    if source and source not in {"图形", "图案", "图形商标", "图案商标"}:
        return source, "source_reported_text_brand", flags
    prefixes = (
        ("BMW", "BMW"), ("博世", "Bosch"), ("美孚", "Mobil"),
        ("壳牌", "Shell"), ("嘉实多", "Castrol"), ("丰田", "Toyota"),
        ("奇瑞", "Chery"), ("江铃", "JMC"), ("海湾", "Gulf"),
        ("埃尔夫", "ELF"), ("金富力", "Havoline"),
    )
    for prefix, normalized in prefixes:
        if product_name.upper().startswith(prefix.upper()):
            return normalized, "brand_in_explicit_product_name", flags
    return producer, "nominal_producer_fallback_no_usable_text_brand", flags


def technical(product_name: str, model: str) -> tuple[dict, list[str]]:
    joined = f"{product_name} {model}".upper()
    joined = (
        joined.replace("－", "-").replace("–", "-").replace("−", "-")
        .replace("／", "/").replace("：", ":").replace("，", ",")
    )
    flags = []
    if re.search(r"(?<![A-Z0-9])OW\s*[-/]?\s*40(?![0-9])", joined):
        joined = re.sub(r"(?<![A-Z0-9])OW(?=\s*[-/]?\s*40)", "0W", joined)
        flags.append("source_letter_o_in_ow40_normalized_to_sae_0w40")
    sae = [
        f"{winter}-{summer}"
        for winter, summer in re.findall(
            r"(?<![0-9])(0W|5W|10W|15W|20W|25W)\s*[-/]?\s*(20|30|40|50|60)(?![0-9])",
            joined,
        )
    ]
    sae.extend(re.findall(r"\bSAE\s*[-/:]?\s*(30|40|50|60)\b", joined))
    api = []
    api_pattern = r"(?<![A-Z0-9])(CD-2|CF-4|CG-4|CH-4|CI-4|CJ-4|CK-4|CC|CD|CE|CF|CG|SF|SG|SJ|SL|SM|SN|SP)(?![A-Z0-9])"
    api.extend(re.findall(api_pattern, joined))
    for value in re.findall(r"(?<![A-Z0-9])(CF4|CG4|CH4|CI4|CJ4|CK4)(?![A-Z0-9])", joined):
        api.append(re.sub(r"([A-Z]{2})(4)$", r"\1-\2", value))
        flags.append("source_api_grade_without_hyphen_normalized")
    for value in re.findall(r"API\s*[-.:]?\s*(CF4|CG4|CH4|CI4|CJ4|CK4|CC|CD|CE|CF|CG|SF|SG|SJ|SL|SM|SN|SP)", joined):
        normalized = re.sub(r"([A-Z]{2})(4)$", r"\1-\2", value)
        api.append(normalized)
        if normalized != value:
            flags.append("source_api_grade_without_hyphen_normalized")
    acea = []
    for left, right in re.findall(r"(?<![A-Z0-9])([AB][1-7])\s*/\s*([AB][1-7])(?:-\d{2})?", joined):
        acea.append(f"{left}/{right}")
    acea.extend(re.findall(r"(?<![A-Z0-9])(C[1-6]|E[4-9])(?:-\d{2})?(?![A-Z0-9])", joined))
    ilsac = [f"GF-{grade}" for grade in re.findall(r"(?:ILSAC|IL\s*SAC)?\s*GF\s*-?\s*([1-7])", joined)]
    if "IL SAC" in joined:
        flags.append("source_ilsac_spacing_typo_normalized")
    oem = []
    for value in re.findall(r"WSS\s*-?\s*M2C\s*[A-Z0-9 -]+", joined):
        value = re.split(r"\s+(?:SAE|API|SEMI|\d+(?:\.\d+)?\s*(?:L|升))", value)[0]
        oem.append(clean(re.sub(r"\s+", " ", value)).replace("WSS ", "WSS-"))
    return {
        "api_source_reported": sorted(set(api)),
        "api_gl_source_reported": [],
        "sae_source_reported": sorted(set(sae)),
        "iso_vg_source_reported": [],
        "china_lubricant_class_source_reported": [],
        "acea_source_reported": sorted(set(acea)),
        "jaso_source_reported": [],
        "ilsac_source_reported": sorted(set(ilsac)),
        "oem_approval_source_reported": sorted(set(oem)),
        "brake_fluid_dot_source_reported": [],
        "brake_fluid_hzy_source_reported": [],
        "coolant_class_source_reported": [],
        "coolant_freezing_point_source_reported": [],
        "washer_fluid_class_source_reported": [],
        "urea_class_source_reported": [],
    }, flags


def package_removed_model(value: str) -> str:
    value = value.replace("毫升", "ml").replace("千克", "kg").replace("公斤", "kg").replace("升", "L")
    value = re.sub(r"\b\d+(?:\.\d+)?\s*(?:GAL|ml|mL|L|l|kg|KG|g)\s*(?:/\s*(?:支|瓶|桶|罐|盒))?", "", value, flags=re.I)
    value = re.sub(r"(?:合格品|合格)$", "", value)
    return clean(value).strip("，,、 ：:;；/")


def split_failures(value: str) -> list[str]:
    value = clean(value)
    if not value:
        return []
    value = re.sub(r"(?:^|[、；;])\s*\d+[、.]\s*", ";", value)
    return [clean(part) for part in re.split(r"[;；]", value.strip(";")) if clean(part)]


def main() -> None:
    payloads = {}
    raw_rows = []
    for year, source in SOURCES.items():
        for outcome, document in source["documents"].items():
            payload = fetch(document["download_url"], document["sha256"], source["source_url"])
            payloads[(year, outcome)] = payload
            for row in source_rows(year, outcome, payload):
                row.update({"year": year, "inspection_outcome": outcome})
                raw_rows.append(row)

    records = []
    for row in raw_rows:
        source = SOURCES[row["year"]]
        document = source["documents"][row["inspection_outcome"]]
        producer, producer_source, producer_basis = manufacturer(
            row["producer"], row["brand_source_reported"], row["product_name"]
        )
        product_brand, brand_basis, brand_flags = brand(
            row["brand_source_reported"], row["product_name"], producer
        )
        extracted, technical_flags = technical(row["product_name"], row["model"])
        outcome = row["inspection_outcome"]
        marker = "C" if outcome == "conforming" else "NC"
        flags = [
            f"official_{row['year']}_municipal_inspection_observation_not_current_catalog_offer",
            "source_docx_not_redistributed_factual_fields_only",
            *brand_flags, *technical_flags,
        ]
        if outcome == "nonconforming":
            flags.append("nonconforming_product_do_not_treat_as_approved_or_recommended")
        if re.search(r"(?:合格品|合格)$", row["model"]):
            flags.append("source_model_conformity_word_not_treated_as_technical_specification")
        source_facts = {key: row[key] for key in sorted(row)}
        records.append({
            "source_id": source["source_id"],
            "source_record_id": f"SZ-CN-{row['year']}-{marker}-{row['source_row']:03d}",
            "source_row": row["source_row"], "source_workbook": outcome,
            "source_url": source["source_url"], "attachment_url": document["attachment_url"],
            "rights_url": RIGHTS_URL, "snapshot_date": SNAPSHOT_DATE,
            "report_date": source["report_date"], "market": "China / Shenzhen",
            "manufacturer": producer, "manufacturer_source_reported": producer_source,
            "manufacturer_basis": producer_basis,
            "brand": product_brand, "brand_source_reported": row["brand_source_reported"],
            "brand_basis": brand_basis, "product_name": row["product_name"],
            "product_name_basis": "source_reported_sample_name_from_municipal_quality_inspection",
            "model_specification_source_reported": row["model"],
            "model_specification_without_package": package_removed_model(row["model"]),
            "product_kind_source_reported": "润滑油",
            "product_kind_english": "motor-vehicle engine lubricant",
            "family_code": "M", "technical": extracted,
            "inspection_standards_scope_source_reported": ["GB 11121-2006", "GB 11122-2006"],
            "production_date_or_batch_source_reported": row["production_date"],
            "inspection_outcome": outcome, "inspection_retest_confirmed_nonconforming": False,
            "nonconforming_items": split_failures(row["nonconforming_items_source_reported"]),
            "nonconforming_items_source_reported": row["nonconforming_items_source_reported"],
            "source_note": "", "lifecycle_status": (
                f"official_{row['year']}_shenzhen_inspection_{outcome}_at_test_current_market_status_unverified"
            ),
            "source_quality_flags": sorted(set(flags)),
            "source_facts_sha256": hashlib.sha256(
                json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "evidence_status": f"official_government_{outcome}_product_inspection_observation",
        })

    if len(records) != 140 or len({row["source_record_id"] for row in records}) != 140:
        raise RuntimeError(f"Expected 140 unique Shenzhen observations, received {len(records)}")
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_shenzhen_2016_2017_complete_lubricant_inspections_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_docx_sha256": {
            f"{year}_{outcome}": hashlib.sha256(payload).hexdigest()
            for (year, outcome), payload in sorted(payloads.items())
        },
        "source_observations": len(records),
        "source_counts": dict(sorted(Counter(row["source_id"] for row in records).items())),
        "outcomes": dict(sorted(Counter(row["inspection_outcome"] for row in records).items())),
        "outcomes_by_source": {
            source_id: dict(sorted(Counter(
                row["inspection_outcome"] for row in records if row["source_id"] == source_id
            ).items()))
            for source_id in sorted({row["source_id"] for row in records})
        },
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_sae": sum(bool(row["technical"]["sae_source_reported"]) for row in records),
        "rows_with_api": sum(bool(row["technical"]["api_source_reported"]) for row in records),
        "rows_with_acea": sum(bool(row["technical"]["acea_source_reported"]) for row in records),
        "rows_with_ilsac": sum(bool(row["technical"]["ilsac_source_reported"]) for row in records),
        "rows_with_oem_approval": sum(bool(row["technical"]["oem_approval_source_reported"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One output row is one inspected batch observation; strict package-independent identity reconciliation happens in the catalog builder.",
        "scope_note": "All 80 rows from 2016 and all 60 rows from 2017 are retained, matching the official 72+8 and 57+3 outcome totals.",
        "lifecycle_note": "Inspection outcomes are historical batch evidence, never current offers or blanket approvals.",
        "privacy_note": "Inspected retailers are excluded; only nominal producer, product, brand, model, production date, outcome and failure facts are retained.",
        "rights_note": "The official DOCX files are not redistributed; only attributed non-expressive factual fields are normalized.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
