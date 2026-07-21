#!/usr/bin/env python3
"""Ingest current CPC Taiwan lubricant product sheets covered by Taiwan OGD data sets."""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import re
import ssl
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "taiwan-cpc-lubricant-products.jsonl"
REPORT = ROOT / "data" / "taiwan-cpc-lubricant-products-report.json"
SOURCE_ID = "TAIWAN_CPC_CURRENT_LUBRICANT_CATALOG"
SNAPSHOT_DATE = "2026-07-21"
DIRECTORY_URL = "https://cpclube.cpc.com.tw/News_eBook.aspx?PageSize=1000&_CSN={category}&n=7478&page=1&sms=12330"
DATASET_URLS = {
    "motor": "https://data.gov.tw/en/datasets/25519",
    "industrial": "https://data.gov.tw/en/datasets/25570",
    "grease": "https://data.gov.tw/en/datasets/25571",
}
LICENSE_URL = "https://data.gov.tw/license"
INTERMEDIATE_CA_URL = "http://sslserver.twca.com.tw/cacert/secure_sha2_2023G3.crt"
INTERMEDIATE_CA_SHA256 = "1a2c75fd096e0499e9ff6ac74e526f61eaae3edfc8c2ea4436fee0c24d8b7d0e"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"

CATEGORIES = {
    28: "industrial_oils",
    29: "vehicle_oils_and_fluids",
    30: "marine_engine_oils",
    31: "greases",
    32: "base_oils",
    33: "apex_motorcycle_oils",
    34: "mirage_pro_automotive_oils",
}
EXPECTED_CATEGORY_COUNTS = {28: 103, 29: 62, 30: 12, 31: 21, 32: 9, 33: 7, 34: 10}

API_CLASSES = ["FA-4", "CK-4", "CJ-4", "CI-4", "CH-4", "CG-4", "CF", "SQ", "SP", "SN", "SM", "SL", "SJ", "SH", "SG"]
ACEA_CLASSES = [f"{letter}{number}" for letter in "ABCE" for number in range(1, 13)]
SAE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*W\s*[/\-]?\s*(\d{2,3})(?!\d)", re.I)


def fetch(url: str, context: ssl.SSLContext | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, context=context, timeout=120) as response:
        return response.read()


def verified_context() -> tuple[ssl.SSLContext, str]:
    der = fetch(INTERMEDIATE_CA_URL)
    digest = hashlib.sha256(der).hexdigest()
    assert digest == INTERMEDIATE_CA_SHA256, digest
    pem = ssl.DER_cert_to_PEM_cert(der)
    context = ssl.create_default_context()
    context.load_verify_locations(cadata=pem)
    return context, digest


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value).replace("\u00ad", "")).strip()


def compact_cjk_spaces(value: str) -> str:
    value = clean(value)
    previous = None
    while value != previous:
        previous = value
        value = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", value)
    return value


def parse_roc_date(value: str) -> str:
    year, month, day = (int(part) for part in value.split("-"))
    return f"{year + 1911:04d}-{month:02d}-{day:02d}"


def family_for(category: int, title: str) -> str:
    if category == 28:
        if "液壓" in title:
            return "H"
        if "空壓" in title or "冷凍機油" in title:
            return "C"
        if "透平" in title or "氣渦輪" in title:
            return "U"
        if "變壓器" in title:
            return "E"
        if "清潔劑" in title or "分散劑" in title:
            return "S"
        return "I"
    if category == 29:
        if any(value in title for value in ("煞車", "水箱", "AdBlue")):
            return "TF"
        if any(value in title for value in ("變速器", "傳動油", "齒輪油")):
            return "T"
        return "M"
    if category == 30:
        return "M"
    if category == 31:
        return "G"
    if category == 32:
        return "S"
    if category == 33:
        return "T" if "齒輪油" in title else "M"
    if category == 34:
        return "T" if "ATF" in title or "CVTF" in title else "M"
    raise AssertionError((category, title))


def brand_for(title: str) -> str:
    if "MiRAGE" in title or "Mirage" in title or "APEX" in title:
        return "MiRAGE"
    return "CPC Kuo Kuang"


def normalized_product_name(title: str) -> str:
    title = title.replace("國光牌", "").strip()
    if title.startswith("APEX"):
        return f"MiRAGE {title}"
    if title.startswith(("MiRAGE", "Mirage", "PRO ")):
        return title
    return f"CPC Kuo Kuang {title}"


def grade_mapping(source_text: str, title: str, product_code: str) -> tuple[str, str]:
    # Prefer the manufacturer product-number row in the same table. This avoids
    # selecting the first of several grade tables embedded in a shared sheet.
    for block_match in re.finditer(r"Grade\s*No\.(.*?)(?=備\s*註|$)", source_text, flags=re.I | re.S):
        block = block_match.group(1)
        iso_match = re.search(r"Viscosity\s*Grade\s*,?\s*ISO\s*VG\s*((?:\d+(?:\.\d+)?\s+){0,20}\d+(?:\.\d+)?)", block, flags=re.I)
        code_match = re.search(r"Product\s*No\.\s*((?:(?:LA|LB|LM|M)\s*\d{5}\s*)+)", block, flags=re.I)
        if not iso_match or not code_match:
            continue
        values = re.findall(r"\d+(?:\.\d+)?", iso_match.group(1))
        codes = [re.sub(r"\s+", "", value.upper()) for value in re.findall(r"(?:LA|LB|LM|M)\s*\d{5}", code_match.group(1), flags=re.I)]
        if product_code.upper() in codes and len(codes) == len(values):
            return product_code.upper(), values[codes.index(product_code.upper())]

    title_key = re.sub(r"[^A-Z0-9]", "", title.upper())
    for match in re.finditer(
        r"Grade\s*No\.(.*?)Viscosity\s*Grade\s*,?\s*ISO\s*VG\s*((?:\d+(?:\.\d+)?\s+){0,20}\d+(?:\.\d+)?)",
        source_text,
        flags=re.I | re.S,
    ):
        labels = re.findall(r"[A-Za-z]+\s*-?\s*\d+[A-Za-z]*|\d+[A-Za-z]*", match.group(1))
        values = re.findall(r"\d+(?:\.\d+)?", match.group(2))
        labels = [re.sub(r"[^A-Z0-9]", "", label.upper()) for label in labels]
        if len(labels) != len(values):
            continue
        matches = [(label, value) for label, value in zip(labels, values) if label and label in title_key]
        if matches:
            return max(matches, key=lambda item: len(item[0]))
    return "", ""


def api_classes(title: str, source_text: str, family: str) -> list[str]:
    if family != "M":
        return []
    title_key = re.sub(r"[^A-Z0-9]", "", title.upper())
    source_key = re.sub(r"\s+", "", source_text.upper())
    values = []
    for value in API_CLASSES:
        compact = value.replace("-", "")
        source_form = value.replace("-", "[- ]?")
        in_source = bool(re.search(rf"API.{{0,16}}{source_form}(?![A-Z0-9])", source_key))
        in_title = bool(re.search(rf"(?:^|C3|E6|E9|ACEA){compact}(?:CF|$|\d{{1,3}}W|FULLY|SYNTHETIC)", title_key))
        if in_source or in_title:
            values.append(value)
    return values


def acea_classes(title: str, source_text: str, family: str) -> list[str]:
    if family != "M":
        return []
    title_key = re.sub(r"[^A-Z0-9]", "", title.upper())
    source_key = re.sub(r"\s+", "", source_text.upper())
    values = []
    for value in ACEA_CLASSES:
        if re.search(rf"ACEA.{{0,12}}{value}(?!\d)", source_key) or re.search(rf"(?:^|PRO|OIL){value}(?:SN|SP|SQ|CK4)", title_key):
            values.append(value)
    return values


def source_standards(source_text: str) -> list[str]:
    patterns = [
        r"DIN\s*\d{4,6}(?:[-/]\d+)?",
        r"ISO\s*\d{4,6}(?:[-/]\d+)?",
        r"SAE\s*J\s*\d{3,5}",
        r"FMVSS\s*116",
        r"JIS\s*[A-Z]\s*-?\s*\d{3,6}",
        r"GEK\s*-?\s*\d+[A-Z]?",
        r"MIL\s*-?\s*[A-Z]+\s*-?\s*\d+[A-Z]?",
        r"ZF\s*TE\s*-?\s*ML\s*\d+[A-Z]?",
        r"MB\s*\d{3}\.\d+",
        r"VW\s*\d{3}\.\d+",
        r"BMW\s*Longlife\s*-?\s*\d+",
    ]
    values = set()
    for pattern in patterns:
        for value in re.findall(pattern, source_text, flags=re.I):
            values.add(clean(value))
    return sorted(values, key=str.casefold)


def nlgi_grade(title: str, source_text: str, family: str) -> str:
    if family != "G":
        return ""
    chinese = {"0": "0", "一": "1", "二": "2", "三": "3"}
    match = re.search(r"([0一二三])號", title)
    if match:
        return chinese[match.group(1)]
    values = set(re.findall(r"NLGI.{0,40}?No\.?\s*([0-3])", source_text, flags=re.I | re.S))
    return next(iter(values)) if len(values) == 1 else ""


def package_source_text(source_text: str) -> str:
    match = re.search(r"包\s*裝\s*[：:](.*?)(?:|本\s*(?:油品|類|產品)|$)", source_text, flags=re.S)
    return compact_cjk_spaces(match.group(1)) if match else ""


def restriction_matches(segment: str, title: str, grade_label: str, nlgi: str, product_code: str) -> bool:
    product_code_restrictions = {
        re.sub(r"\s+", "", value.upper())
        for value in re.findall(r"[（(]\s*((?:LA|LB|LM|M)\s*\d{5})\s*[）)]", segment, flags=re.I)
    }
    if product_code_restrictions and product_code.upper() not in product_code_restrictions:
        return False
    restriction = re.search(r"[（(]([^）)]*(?:限|除)[^）)]*)[）)]", segment)
    if not restriction:
        return True
    body = restriction.group(1)
    identity = re.sub(r"[^A-Z0-9]", "", title.upper())
    identity += re.sub(r"[^A-Z0-9]", "", grade_label.upper())
    if nlgi:
        identity += f"NO{nlgi}"
    selectors = [re.sub(r"[^A-Z0-9]", "", value.upper()) for value in re.findall(r"(?:NO\.?\s*)?[A-Z]*\d+[A-Z]*|\bC\b", body, flags=re.I)]
    matched = any(value and value in identity for value in selectors)
    return not matched if "除" in body else matched


def parse_packages(source_text: str, title: str, grade_label: str, nlgi: str, product_code: str) -> tuple[list[dict], str]:
    raw = package_source_text(source_text)
    if not raw:
        return [], ""
    segmented = re.sub(r"[\uf081-\uf084①-⑨]", "|", raw)
    segmented = re.sub(r"○\s*[1-9]", "|", segmented)
    segments = [value.strip(" 。；;,") for value in segmented.split("|") if value.strip(" 。；;,")]
    packages = []
    seen = set()
    for segment in segments:
        if not restriction_matches(segment, title, grade_label, nlgi, product_code):
            continue
        if "散裝" in segment:
            key = ("bulk", None, None)
            if key not in seen:
                packages.append({"package_name_source": "散裝", "unit": "bulk", "quantity": None, "units_per_case": None})
                seen.add(key)
        for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(公升|公斤)\s*(瓶裝|桶裝|聽裝|條裝)", segment):
            quantity, source_unit, container = match.groups()
            unit = "l" if source_unit == "公升" else "kg"
            key = (container, float(quantity), unit)
            if key not in seen:
                packages.append({"package_name_source": clean(match.group(0)), "unit": unit, "quantity": float(quantity), "units_per_case": None})
                seen.add(key)
        for match in re.finditer(r"(條|箱)\s*/\s*(\d+(?:\.\d+)?)\s*(公升|公斤)(?:\s*\*\s*(\d+))?", segment):
            container, quantity, source_unit, units_per_case = match.groups()
            unit = "l" if source_unit == "公升" else "kg"
            count = int(units_per_case) if units_per_case else None
            key = (container, float(quantity), unit, count)
            if key not in seen:
                packages.append({
                    "package_name_source": clean(match.group(0)),
                    "unit": unit,
                    "quantity": float(quantity),
                    "units_per_case": count,
                })
                seen.add(key)
        for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(公升|公斤)\s*\*?\s*(\d+)\s*(?:瓶)?箱裝", segment):
            quantity, source_unit, count = match.groups()
            unit = "l" if source_unit == "公升" else "kg"
            key = ("case", float(quantity), unit, int(count))
            if key not in seen:
                packages.append({"package_name_source": clean(match.group(0)), "unit": unit, "quantity": float(quantity), "units_per_case": int(count)})
                seen.add(key)
    return packages, raw


def technical_fields(title: str, source_text: str, family: str, product_code: str) -> tuple[dict, str, str]:
    specifications: dict = {}
    sae = SAE_PATTERN.search(title)
    if sae:
        specifications["sae_engine" if family == "M" else "sae_gear"] = f"{sae.group(1)}W-{sae.group(2)}"
    api = api_classes(title, source_text, family)
    acea = acea_classes(title, source_text, family)
    if api:
        specifications["api"] = api
    if acea:
        specifications["acea"] = acea
    compact_source = re.sub(r"\s+", "", source_text.upper())
    jaso = sorted({value for value in ("MA2", "MA", "MB", "FD", "FC") if re.search(rf"JASO.{{0,12}}{value}", compact_source)})
    if jaso:
        specifications["jaso"] = jaso
    dot = sorted({f"DOT {value}" for value in re.findall(r"DOT\s*([345](?:\.1)?)", source_text, flags=re.I)})
    if dot:
        specifications["brake_fluid_classes"] = dot
    grade_label, iso_vg = grade_mapping(source_text, title, product_code)
    if iso_vg and family in {"H", "I", "C", "U"}:
        specifications["iso_vg"] = iso_vg
        specifications["grade_no_source_reported"] = grade_label
    nlgi = nlgi_grade(title, source_text, family)
    if nlgi:
        specifications["nlgi"] = nlgi
    standards = source_standards(source_text)
    if standards:
        specifications["oem_and_industry_standards_source_reported"] = standards
    if family == "S" and "基礎油" in title:
        specifications["product_form"] = "lubricant_base_oil"
    if family == "TF" and "AdBlue" in title:
        specifications["product_form"] = "diesel_exhaust_fluid"
    return specifications, grade_label, nlgi


def parse_listing(payload: bytes, category: int) -> list[dict]:
    page = payload.decode("utf-8-sig")
    pattern = re.compile(
        r'<a\s+href="(https://cpclube-ws\.cpc\.com\.tw/[^"]+/index\.html)"[^>]+title="([^"]+)"[^>]*>.*?<i class="mark">([^<]+)</i>',
        flags=re.S,
    )
    records = []
    for ebook_url, raw_title, raw_date in pattern.findall(page):
        title = clean(raw_title).removeprefix("[另開新視窗]").removesuffix("電子書").strip()
        match = re.fullmatch(r"((?:LA|LB|LM)\d{5}|M\s*\d{5})(?:-\s*)?\s*(.+)", title)
        assert match, title
        product_code_raw, product_title = match.groups()
        product_code = re.sub(r"\s+", "", product_code_raw)
        records.append({
            "category": category,
            "product_code": product_code,
            "product_code_source": product_code_raw,
            "product_title_source": product_title.strip(),
            "product_sheet_url": ebook_url,
            "product_sheet_data_url": ebook_url.rsplit("/", 1)[0] + "/data.json",
            "product_sheet_update_date": parse_roc_date(raw_date.strip()),
        })
    return records


def main() -> None:
    context, ca_digest = verified_context()
    listing_payloads = {
        category: fetch(DIRECTORY_URL.format(category=category), context)
        for category in CATEGORIES
    }
    listing_rows = [
        row
        for category, payload in listing_payloads.items()
        for row in parse_listing(payload, category)
    ]
    assert Counter(row["category"] for row in listing_rows) == EXPECTED_CATEGORY_COUNTS
    assert len(listing_rows) == 224
    assert len({row["product_code"] for row in listing_rows}) == 224
    assert len({row["product_sheet_data_url"] for row in listing_rows}) == 224

    def get_product_sheet(row: dict) -> tuple[str, bytes]:
        return row["product_code"], fetch(row["product_sheet_data_url"], context)

    product_sheet_payloads = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        for product_code, payload in executor.map(get_product_sheet, listing_rows):
            product_sheet_payloads[product_code] = payload

    records = []
    for row in listing_rows:
        payload = product_sheet_payloads[row["product_code"]]
        pages = json.loads(payload.decode("utf-8-sig"))
        source_text = clean(" ".join(page["page_content"] for _, page in sorted(pages.items(), key=lambda item: int(item[0]))))
        title = row["product_title_source"]
        family = family_for(row["category"], title)
        specifications, grade_label, nlgi = technical_fields(title, source_text, family, row["product_code"])
        packages, packages_source = parse_packages(source_text, title, grade_label, nlgi, row["product_code"])
        flags = []
        if not packages:
            flags.append("source_package_text_present_but_no_product_specific_structured_offer")
        if family in {"H", "I", "C", "U"} and re.search(r"Viscosity\s*Grade\s*,?\s*ISO\s*VG", source_text, flags=re.I) and not specifications.get("iso_vg"):
            flags.append("source_multigrade_table_not_safely_aligned_to_listing_title")
        record = {
            "source_id": SOURCE_ID,
            "source_record_id": f"TAIWAN-CPC-{row['product_code']}",
            "brand": brand_for(title),
            "manufacturer": "CPC Corporation, Taiwan",
            "product_name": normalized_product_name(title),
            "product_name_source": title,
            "manufacturer_product_code": row["product_code"],
            "manufacturer_product_code_source": row["product_code_source"],
            "family_code": family,
            "source_category": CATEGORIES[row["category"]],
            "source_category_code": row["category"],
            "market": "TW",
            "source_url": DIRECTORY_URL.format(category=row["category"]),
            "product_sheet_url": row["product_sheet_url"],
            "product_sheet_data_url": row["product_sheet_data_url"],
            "product_sheet_update_date": row["product_sheet_update_date"],
            "product_sheet_data_sha256": hashlib.sha256(payload).hexdigest(),
            "product_sheet_pages": len(pages),
            "source_dataset_urls": list(DATASET_URLS.values()),
            "source_license_url": LICENSE_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_current_official_product_sheet_directory",
            "specifications": specifications,
            "packages": packages,
            "packages_source_reported": packages_source,
            "source_quality_flags": flags,
        }
        records.append(record)

    records.sort(key=lambda row: (row["source_category_code"], row["manufacturer_product_code"]))
    assert len(records) == 224
    assert all(row["packages_source_reported"] for row in records)
    assert all(row["packages"] or row["source_quality_flags"] for row in records)
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_directory_url": DIRECTORY_URL.format(category=0),
        "source_dataset_urls": DATASET_URLS,
        "source_license_url": LICENSE_URL,
        "intermediate_ca_url": INTERMEDIATE_CA_URL,
        "intermediate_ca_sha256": ca_digest,
        "categories": {CATEGORIES[key]: value for key, value in EXPECTED_CATEGORY_COUNTS.items()},
        "current_product_cards": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "brands": dict(sorted(Counter(row["brand"] for row in records).items())),
        "structured_package_offers": sum(len(row["packages"]) for row in records),
        "products_with_structured_package_offers": sum(bool(row["packages"]) for row in records),
        "rows_with_sae": sum(bool(row["specifications"].get("sae_engine") or row["specifications"].get("sae_gear")) for row in records),
        "rows_with_api": sum(bool(row["specifications"].get("api")) for row in records),
        "rows_with_acea": sum(bool(row["specifications"].get("acea")) for row in records),
        "rows_with_jaso": sum(bool(row["specifications"].get("jaso")) for row in records),
        "rows_with_iso_vg": sum(bool(row["specifications"].get("iso_vg")) for row in records),
        "rows_with_nlgi": sum(bool(row["specifications"].get("nlgi")) for row in records),
        "source_quality_flags": dict(sorted(Counter(flag for row in records for flag in row["source_quality_flags"]).items())),
        "listing_page_sha256": {
            CATEGORIES[category]: hashlib.sha256(payload).hexdigest()
            for category, payload in listing_payloads.items()
        },
        "product_sheet_data_aggregate_sha256": hashlib.sha256("".join(
            hashlib.sha256(product_sheet_payloads[row["product_code"]]).hexdigest()
            for row in sorted(listing_rows, key=lambda value: value["product_code"])
        ).encode()).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Attributed derived factual names, product codes, dates, grades, standards and package facts under Taiwan Open Government Data License 1.0; descriptive prose, page images and layout are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
