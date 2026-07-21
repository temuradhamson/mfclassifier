#!/usr/bin/env python3
"""Extract lubricant-grade facts from LIQUI MOLY's official 2020 PDF catalog."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/liqui-moly-2020-products.jsonl"
REPORT = ROOT / "data/liqui-moly-2020-products-report.json"
PDF_URL = "https://www.liqui-moly.com/fileadmin/user_upload/Downloads/Technische_Informationen/Kataloge_und_Prospekte/EN/5603.pdf"
CATALOG_PAGE_URL = "https://www.liqui-moly.com/en/gb/product-catalog-p002680.html"
DOCUMENT_DATE = "2020-04-23"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"
RELEVANT_PAGES = set(range(16, 48)) | set(range(60, 68)) | set(range(94, 110)) | set(range(113, 124)) | set(range(128, 132)) | {133}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def page_items(page) -> list[dict]:
    rows = []

    def visitor(text, _cm, tm, font, _size):
        value = " ".join(text.split())
        if value:
            rows.append({"text": value, "x": round(float(tm[4]), 1), "y": round(float(tm[5]), 1), "font": str((font or {}).get("/BaseFont", ""))})

    page.extract_text(visitor_text=visitor)
    return rows


def is_product_title(row: dict) -> bool:
    value = row["text"]
    if "Bold" not in row["font"] or not 95 <= row["x"] <= 340 or row["y"] <= 45:
        return False
    lower = value.casefold()
    if len(value) > 90 or value.endswith(".") or value.endswith(":"):
        return False
    if lower in {"tbn20", "important", "area of use", "cont. packaging part", "unit no."}:
        return False
    if lower.startswith(("especially ", "particularly ", "suitable ", "special development for ", "for maximum ", "for the ", "always ", "with improved ", "provides ", "protects ", "use bioci", "before use", "fely.")):
        return False
    if any(fragment in lower for fragment in ["vehicles with service", "product information before use"]):
        return False
    return bool(re.search(r"[A-Za-z]", value))


def family_for(page: int, title: str) -> str:
    upper = title.upper()
    if upper == "EXHAUST ASSEMBLY PASTE":
        return "G"
    if page <= 30:
        return "M"
    if page == 31 and any(token in upper for token in ["MOTOR OIL", "MOTOROIL", "2-STROKE"]):
        return "M"
    if 31 <= page <= 39:
        return "H" if upper.startswith("HYDRAULIC OIL") else "T"
    if page in {40, 41}:
        return "C" if "COMPRESSOR" in upper else "H"
    if page == 42:
        return "C" if "COMPRESSOR" in upper else "G"
    if 43 <= page <= 46:
        return "G"
    if page == 47:
        return "G" if "FITTING" in upper and "PASTE" in upper else "S"
    if 60 <= page <= 62:
        return "TF"
    if page == 63:
        return "TF" if any(token in upper for token in ["COOLANT", "ANTIFREEZE"]) else "S"
    if 64 <= page <= 67:
        return "TF" if any(token in upper for token in ["CLEANER", "LEAK FINDER", "DETECTOR"]) else "S"
    if 94 <= page <= 96:
        return "M" if re.search(r"\b(?:0|5|10|15|20|25)W-?\d{2}\b", upper) and "ENGINE" in upper else "TF"
    if 97 <= page <= 100:
        return "M"
    if page == 101:
        return "S" if "STOU" in upper or "UTTO" in upper else "M"
    if 102 <= page <= 107:
        return "H" if upper.startswith("HYDRAULIC OIL") else "T"
    if page == 108:
        return "H" if upper.startswith("HYDRAULIC OIL") or upper == "LIFTGATE OIL" else "TF"
    if page == 109:
        return "G"
    if 113 <= page <= 114:
        return "TF"
    if 115 <= page <= 120:
        return "M"
    if page == 121:
        return "T"
    if page == 122:
        return "H" if "FORK OIL" in upper or "SHOCK ABSORBER" in upper else "TF"
    if page == 123:
        if "CHAIN LUBE" in upper:
            return "I"
        return "TF" if "CLEANER" in upper or "FILTER OIL" in upper else "S"
    if page == 128:
        return "M" if "MOTOR OIL" in upper else "TF"
    if page == 129:
        return "M"
    if page == 130:
        if "GREASE" in upper:
            return "G"
        if "CLEANER" in upper:
            return "TF"
        return "T"
    if page == 131:
        return "TF" if "CLEANER" in upper or "ANTIFREEZE" in upper else "S"
    if page == 133:
        if "CHAIN OIL" in upper:
            return "I"
        if "MOTOR OIL" in upper or "MOTOROIL" in upper or "LAWNMOWER OIL" in upper or "EQUIPMENT OIL" in upper:
            return "M"
        return "TF"
    raise AssertionError((page, title))


def technical_from_text(title: str, block_text: str) -> dict:
    upper = f"{title} {block_text}".upper().replace("–", "-")
    result = {}
    sae = sorted(set(re.findall(r"(?<![0-9])((?:0|5|10|15|20|25)W[- ]?[0-9]{2}|(?:70|75|80|85)W(?:[- ]?[0-9]{2,3})?|SAE\s+[0-9]{2,3}W?)(?![0-9])", upper)))
    if sae:
        result["sae_grades"] = [re.sub(r"^SAE\s+", "", value).replace(" ", "") for value in sae]
    api = sorted(set(re.findall(r"\bAPI\s+([A-Z]{1,2}(?:-[0-9])?)\b", upper)))
    acea = sorted(set(re.findall(r"\bACEA\s+([A-Z][0-9](?:/[A-Z][0-9])?)\b", upper)))
    if api:
        result["api"] = api
    if acea:
        result["acea"] = acea
    iso_vg = sorted(set(re.findall(r"\bISO(?:\s+VG)?\s*([0-9]{1,4})\b", upper)), key=int)
    if iso_vg:
        result["iso_vg"] = iso_vg
    return result


def main() -> None:
    payload = fetch(PDF_URL)
    reader = PdfReader(BytesIO(payload))
    assert len(reader.pages) == 204
    occurrences = []
    rejected_bold_rows = []
    for page_number in sorted(RELEVANT_PAGES):
        items = page_items(reader.pages[page_number - 1])
        candidates = sorted([row for row in items if is_product_title(row)], key=lambda row: -row["y"])
        for index, title_row in enumerate(candidates):
            lower_y = candidates[index + 1]["y"] if index + 1 < len(candidates) else 45
            block = [row for row in items if lower_y < row["y"] <= title_row["y"]]
            left_text = " ".join(row["text"] for row in sorted(block, key=lambda row: -row["y"]) if 95 <= row["x"] < 345 and "Bold" not in row["font"])
            part_numbers = sorted({row["text"] for row in block if 500 <= row["x"] <= 535 and "Bold" in row["font"] and re.fullmatch(r"[0-9]{4,6}", row["text"])}, key=int)
            packages = sorted({row["text"] for row in block if 465 <= row["x"] < 516 and re.fullmatch(r"[0-9.,]+\s*(?:ml|l|g|kg)\s+[0-9]+", row["text"], re.I)})
            title = title_row["text"].strip()
            occurrences.append({
                "product_name": title,
                "family_code": family_for(page_number, title),
                "source_page": page_number,
                "part_numbers": part_numbers,
                "package_rows": packages,
                "technical": technical_from_text(title, left_text),
                "fact_block_sha256": hashlib.sha256(left_text.encode()).hexdigest(),
            })
        rejected_bold_rows.extend(row["text"] for row in items if "Bold" in row["font"] and 95 <= row["x"] <= 340 and row["y"] > 45 and not is_product_title(row))

    grouped = defaultdict(list)
    for row in occurrences:
        grouped[(normalize(row["product_name"]), row["family_code"])].append(row)
    records = []
    for (name_key, family), rows in grouped.items():
        product_name = rows[0]["product_name"]
        records.append({
            "source_id": "LIQUI_MOLY_2020_PRODUCT_CATALOG",
            "source_record_id": "LM-2020-" + hashlib.sha256(f"{name_key}|{family}".encode()).hexdigest()[:16],
            "manufacturer": "LIQUI MOLY GmbH",
            "brand": "LIQUI MOLY",
            "product_name": product_name,
            "family_code": family,
            "market": "GLOBAL_EN",
            "lifecycle_status": "historical_catalog_current_status_unverified",
            "document_date": DOCUMENT_DATE,
            "source_pages": sorted({row["source_page"] for row in rows}),
            "part_numbers": sorted({number for row in rows for number in row["part_numbers"]}, key=int),
            "package_rows": sorted({value for row in rows for value in row["package_rows"]}),
            "technical": {key: sorted({value for row in rows for value in row["technical"].get(key, [])}) for key in {key for row in rows for key in row["technical"]}},
            "fact_block_sha256": sorted({row["fact_block_sha256"] for row in rows}),
            "source_url": PDF_URL,
            "catalog_page_url": CATALOG_PAGE_URL,
            "snapshot_date": SNAPSHOT_DATE,
        })
    records.sort(key=lambda row: (normalize(row["product_name"]), row["family_code"]))
    assert len(occurrences) == 444
    assert len(records) == 419
    assert all(row["part_numbers"] for row in records)
    assert not any(len({candidate["family_code"] for candidate in records if normalize(candidate["product_name"]) == normalize(row["product_name"])}) > 1 for row in records)
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "document_date": DOCUMENT_DATE,
        "source_id": "LIQUI_MOLY_2020_PRODUCT_CATALOG",
        "source_url": PDF_URL,
        "catalog_page_url": CATALOG_PAGE_URL,
        "source_pdf_sha256": hashlib.sha256(payload).hexdigest(),
        "pdf_pages": len(reader.pages),
        "pages_selected": len(RELEVANT_PAGES),
        "product_occurrences": len(occurrences),
        "products": len(records),
        "duplicate_occurrences_merged": len(occurrences) - len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "products_with_part_numbers": sum(bool(row["part_numbers"]) for row in records),
        "unique_part_numbers": len({number for row in records for number in row["part_numbers"]}),
        "products_with_package_rows": sum(bool(row["package_rows"]) for row in records),
        "rejected_bold_rows": sorted(set(rejected_bold_rows)),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Historical product identity, family, source page, part numbers, package labels and derived technical facts; marketing descriptions and page layout are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
