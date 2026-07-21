#!/usr/bin/env python3
"""Normalize factual product cards from the official Cummins-hosted Valvoline catalog."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cummins-valvoline-2022-products.jsonl"
REPORT = ROOT / "data" / "cummins-valvoline-2022-products-report.json"
CACHE_PDF = ROOT / ".cache" / "cummins-valvoline-eu-2022.pdf"
SOURCE_ID = "CUMMINS_VALVOLINE_EU_2022_CATALOG"
SOURCE_URL = "https://www.cummins.com/sites/default/files/Europe/2204606-valvoline-eu-cummins-product-catalog-apr22.pdf"
CURRENT_REGISTRY_URL = "https://quickserve.cummins.com/info/qsol/news/oil_registration.html"
SNAPSHOT_DATE = "2026-07-21"
DOCUMENT_DATE = "2022-04"
EXPECTED_PDF_SHA256 = "aad161c366c35e74fcd331771bb4d6194470e26099f970f878b2d96d2b3cc401"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"

SKU_PATTERN = re.compile(r"(?:VE)?\d{5,}", re.I)
SAE_PATTERN = re.compile(r"(?<!\d)((?:0|5|10|15|20)W-?\d{2}|(?:70|75|80|85)W-?\d{2,3}|SAE\s*\d{2})(?!\d)", re.I)
API_PATTERN = re.compile(r"\b(?:CK|CJ|CI|CH|CF|FA|SP|SN|SM|SL|SJ)-?\d?\+?\b", re.I)
ACEA_PATTERN = re.compile(r"\b(?:A\d|B\d|C\d|E\d)(?:[-/]\d{2})?\b", re.I)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
        if response.headers.get("Content-Encoding", "").casefold() == "gzip" or payload[:2] == b"\x1f\x8b":
            payload = gzip.decompress(payload)
        return payload


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00ad", "")).strip()


def family_for(page_number: int, quarter: int, title_y: float, title: str) -> str:
    if page_number == 3:
        return "M"
    if page_number == 4:
        return "M" if quarter < 2 and title_y < 400 else "T"
    if page_number == 5:
        return "G" if title_y < 190 else ("TF" if title.startswith(("OEM ", "HD ")) else "G")
    if page_number == 6:
        if title.startswith(("Valmarin",)):
            return "M"
        if title.startswith(("Valvoline S.T.O.U.",)):
            return "S"
        if title.startswith(("Valvoline UTTO", "Valvoline Unitrac")):
            return "T"
        return "G"
    if page_number == 7:
        return "C" if title.startswith("Compressor Oil") else "I"
    if page_number == 8:
        return "H"
    if page_number == 9:
        if title.startswith("Valvoline Turbine Oil"):
            return "U"
        return "H" if title.startswith(("Valvoline HVLP", "Valvoline HLVP")) else "I"
    if page_number == 10:
        return "I"
    raise AssertionError((page_number, title))


def grouped_lines(words: list[dict]) -> list[tuple[float, list[dict]]]:
    groups: dict[float, list[dict]] = defaultdict(list)
    for word in words:
        groups[round(float(word["top"]), 1)].append(word)
    return [(y, sorted(group, key=lambda word: word["x0"])) for y, group in sorted(groups.items())]


def package_offers(package_groups: list[tuple[float, list[dict]]]) -> tuple[list[dict], list[str]]:
    if len(package_groups) < 2:
        return [], ["source_card_has_no_machine_readable_package_matrix"]
    package_words = package_groups[0][1]
    sku_rows = []
    for _, words in package_groups[1:]:
        slots = [word for word in words if SKU_PATTERN.fullmatch(word["text"]) or word["text"] == "-"]
        if not slots:
            continue
        joined = " ".join(word["text"] for word in words).casefold()
        variant = "concentrate" if "concentrate" in joined else "ready_to_use" if "ready to use" in joined else "catalog_product"
        sku_rows.append((variant, slots))
    if not sku_rows:
        return [], ["source_card_has_no_machine_readable_sku_row"]
    reference_slots = max((slots for _, slots in sku_rows), key=len)
    package_cells: list[list[dict]] = [[] for _ in reference_slots]
    for word in package_words:
        center = (word["x0"] + word["x1"]) / 2
        index = min(range(len(reference_slots)), key=lambda i: abs(center - (reference_slots[i]["x0"] + reference_slots[i]["x1"]) / 2))
        package_cells[index].append(word)
    package_names = [clean(" ".join(word["text"] for word in sorted(cell, key=lambda item: item["x0"]))) for cell in package_cells]
    offers = []
    flags = []
    for variant, slots in sku_rows:
        if len(slots) != len(reference_slots):
            flags.append("source_package_matrix_row_width_mismatch_retained_without_inference")
            continue
        for package_name, slot in zip(package_names, slots):
            if slot["text"] == "-":
                continue
            offers.append({
                "package_name": package_name,
                "article_number": slot["text"],
                "variant": variant,
            })
    if not all(offer["package_name"] for offer in offers):
        flags.append("source_package_label_alignment_requires_review")
    return offers, sorted(set(flags))


def technical_fields(title: str, family: str, standards_lines: list[str]) -> dict:
    source_text = "; ".join(standards_lines)
    specifications: dict = {"standards_and_approvals_source_reported": standards_lines}
    sae = SAE_PATTERN.search(title)
    if sae:
        grade = sae.group(1).upper().replace("SAE", "SAE ").replace("  ", " ")
        specifications["sae_engine" if family == "M" else "sae_gear"] = grade
    if family in {"H", "I", "C", "U"}:
        grade = re.search(r"(?:^|\s)(\d{1,3})(?:\s|$)", title)
        if grade:
            specifications["iso_vg"] = grade.group(1)
    if family == "G":
        grade = re.search(r"(?:^|\s)(00|0|1(?:\.5)?|2(?:/3)?|3)(?:\s|$)", title)
        if grade:
            specifications["nlgi"] = grade.group(1)
    api = sorted({value.upper() for value in API_PATTERN.findall(source_text)})
    acea = sorted({value.upper() for value in ACEA_PATTERN.findall(source_text)})
    cummins = sorted(set(re.findall(r"(?:Cummins\s+)?CES\s*(\d{5})", source_text, re.I)))
    if api:
        specifications["api"] = api
    if acea:
        specifications["acea"] = acea
    if cummins:
        specifications["cummins_ces_source_reported"] = cummins
    if family == "TF":
        if "Ready-To-Use" in title or "-67" in title:
            specifications["product_form"] = "ready_to_use"
        elif any("Concentrate" in line for line in standards_lines):
            specifications["product_form"] = "concentrate_and_ready_to_use_variants"
    return specifications


def main() -> None:
    payload = fetch(SOURCE_URL)
    digest = hashlib.sha256(payload).hexdigest()
    assert digest == EXPECTED_PDF_SHA256, digest
    CACHE_PDF.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PDF.write_bytes(payload)

    records = []
    with pdfplumber.open(CACHE_PDF) as pdf:
        assert len(pdf.pages) == 11
        for page_number in range(3, 11):
            page = pdf.pages[page_number - 1]
            page_words = page.extract_words(extra_attrs=["fontname", "size"])
            for quarter in range(4):
                x0 = quarter * page.width / 4
                x1 = (quarter + 1) * page.width / 4
                quarter_words = [word for word in page_words if x0 <= word["x0"] < x1]
                title_words = [
                    word for word in quarter_words
                    if "CondensedBold" in word["fontname"] and 8.5 <= float(word["size"]) <= 9.5
                ]
                titles = [
                    (y, clean(" ".join(word["text"] for word in words)))
                    for y, words in grouped_lines(title_words)
                ]
                for index, (title_y, title) in enumerate(titles):
                    bottom = titles[index + 1][0] - 1 if index + 1 < len(titles) else 770
                    card_words = [word for word in quarter_words if title_y - 2 <= word["top"] < bottom]
                    package_groups = grouped_lines([
                        word for word in card_words if 4.8 <= float(word["size"]) <= 5.2
                    ])
                    offers, flags = package_offers(package_groups)
                    package_top = package_groups[0][0] if package_groups else bottom
                    standard_words = [
                        word for word in card_words
                        if word["top"] < package_top - 1
                        and 4.3 <= float(word["size"]) <= 5.7
                        and not (4.8 <= float(word["size"]) <= 5.2)
                        and "CondensedBold" not in word["fontname"]
                    ]
                    standards_lines = [
                        clean(" ".join(word["text"] for word in words))
                        for _, words in grouped_lines(standard_words)
                    ]
                    family = family_for(page_number, quarter, title_y, title)
                    if title == "Valvoline HLP":
                        flags.append("source_product_title_missing_viscosity_grade")
                    if title.startswith("Valvoline HLVP"):
                        flags.append("source_product_title_hlvp_notation_retained_verbatim")
                    identity = f"{page_number}|{quarter}|{title_y}|{title}"
                    records.append({
                        "source_id": SOURCE_ID,
                        "source_record_id": "CUMMINS-VALVOLINE-2022-" + hashlib.sha256(identity.encode()).hexdigest()[:16],
                        "brand": "Valvoline",
                        "manufacturer": "Valvoline",
                        "product_name": title,
                        "family_code": family,
                        "market": "EUROPE_CUMMINS_VALVOLINE_2022",
                        "source_url": SOURCE_URL,
                        "source_document": "Valvoline Product Catalogue Europe, Cummins-hosted, April 2022",
                        "source_document_date": DOCUMENT_DATE,
                        "source_page": page_number,
                        "snapshot_date": SNAPSHOT_DATE,
                        "lifecycle_status": "historical_catalog_as_published_2022_04_current_status_unverified",
                        "specifications": technical_fields(title, family, standards_lines),
                        "packages": offers,
                        "source_quality_flags": sorted(set(flags)),
                    })

    assert len(records) == 166
    assert len({row["source_record_id"] for row in records}) == 166
    assert len({(row["product_name"], row["family_code"]) for row in records}) == 165
    article_products: dict[str, set[str]] = defaultdict(set)
    for row in records:
        for offer in row["packages"]:
            article_products[offer["article_number"]].add(row["source_record_id"])
    colliding_articles = {article for article, products in article_products.items() if len(products) > 1}
    for row in records:
        if any(offer["article_number"] in colliding_articles for offer in row["packages"]):
            row["source_quality_flags"] = sorted(set(row["source_quality_flags"] + [
                "source_article_number_cross_product_collision_retained_verbatim"
            ]))
    package_occurrences = sum(len(row["packages"]) for row in records)
    unique_article_numbers = {offer["article_number"] for row in records for offer in row["packages"]}
    assert package_occurrences >= 500
    assert len(unique_article_numbers) >= 490
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "document_date": DOCUMENT_DATE,
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "current_cummins_registration_registry_url": CURRENT_REGISTRY_URL,
        "source_pdf_sha256": digest,
        "pdf_pages": 11,
        "normalized_products": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "package_offer_occurrences": package_occurrences,
        "unique_article_numbers": len(unique_article_numbers),
        "cross_product_colliding_article_numbers": len(colliding_articles),
        "rows_with_sae": sum(bool(row["specifications"].get("sae_engine") or row["specifications"].get("sae_gear")) for row in records),
        "rows_with_iso_vg": sum(bool(row["specifications"].get("iso_vg")) for row in records),
        "rows_with_nlgi": sum(bool(row["specifications"].get("nlgi")) for row in records),
        "rows_with_api": sum(bool(row["specifications"].get("api")) for row in records),
        "rows_with_cummins_ces": sum(bool(row["specifications"].get("cummins_ces_source_reported")) for row in records),
        "source_quality_flags": dict(sorted(Counter(flag for row in records for flag in row["source_quality_flags"]).items())),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Attributed non-expressive product, grade, standard, package and article-number facts only; marketing prose, images and catalog design are excluded.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
