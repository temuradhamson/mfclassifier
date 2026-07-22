#!/usr/bin/env python3
"""Normalize all lubricant rows in Ecuador INEN's current quality-seal list."""

from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "ecuador-inen-current-certified-lubricants.jsonl"
REPORT = ROOT / "data" / "ecuador-inen-current-certified-lubricants-report.json"
ANNOUNCEMENTS = ROOT / "data" / "ecuador-inen-certified-lubricants.jsonl"
SOURCE_ID = "ECUADOR_INEN_2026_07_CURRENT_CERTIFIED_LUBRICANTS"
LANDING_URL = "https://www.normalizacion.gob.ec/direccion-tecnica-de-validacion-y-certificacion/1000/"
DRIVE_VIEW_URL = "https://drive.google.com/file/d/1PpPul73S1hdaKy2ZG7Re76gV1nOw7IFP/view"
DOWNLOAD_URL = "https://drive.usercontent.google.com/download?id=1PpPul73S1hdaKy2ZG7Re76gV1nOw7IFP&export=download&confirm=t"
SNAPSHOT_DATE = "2026-07-22"
EXPECTED_PDF_SHA256 = "42bac24e08c30af8966cce6025a24e7ba2ce84487c712afba2d303c9a8111c26"
EXPECTED_PAGES = 81
EXPECTED_ALL_ROWS = 1763
EXPECTED_RELEVANT_ROWS = 410
RELEVANT_STANDARDS = {
    "NTE INEN 2027:2024": "M",
    "NTE INEN 2030:2024": "M",
    "NTE INEN 2028:2021": "T",
    "NTE INEN 2029:2018": "I",
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_pdf() -> bytes:
    request = urllib.request.Request(DOWNLOAD_URL, headers={
        "User-Agent": "MFClassifierResearch/1.0 (public-government-certification-data)",
    })
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    if not payload.startswith(b"%PDF-"):
        raise RuntimeError("INEN current list did not return a PDF")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_PDF_SHA256:
        raise RuntimeError(f"INEN current PDF changed: expected {EXPECTED_PDF_SHA256}, got {digest}")
    return payload


def source_rows(payload: bytes) -> tuple[list[dict], int]:
    rows = []
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        if len(pdf.pages) != EXPECTED_PAGES:
            raise RuntimeError(f"Expected {EXPECTED_PAGES} pages, got {len(pdf.pages)}")
        for page_number, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            if len(tables) != 1:
                raise RuntimeError(f"Expected one table on PDF page {page_number}, got {len(tables)}")
            for page_row, source in enumerate(tables[0], 1):
                values = [clean(value) for value in source]
                if len(values) != 9:
                    raise RuntimeError(f"Unexpected table width on page {page_number}, row {page_row}")
                if values[0] == "EMPRESA":
                    continue
                rows.append({
                    "source_pdf_page": page_number,
                    "source_pdf_table_row": page_row,
                    "holder": values[0],
                    "source_product": values[1],
                    "brand": values[2],
                    "updated_at": "" if values[4] in {"", "---"} else values[4],
                    "issued_at": values[5],
                    "expires_at": values[6],
                    "standard": values[7],
                    "certificate_number": values[8],
                })
    if len(rows) != EXPECTED_ALL_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ALL_ROWS} complete register rows, got {len(rows)}")
    if len({row["certificate_number"] for row in rows}) != EXPECTED_ALL_ROWS:
        raise RuntimeError("INEN certificate numbers are not unique in the pinned register")
    relevant = [row for row in rows if row["standard"] in RELEVANT_STANDARDS]
    if len(relevant) != EXPECTED_RELEVANT_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_RELEVANT_ROWS} lubricant rows, got {len(relevant)}")
    return relevant, len(rows)


def source_text_key(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "", value)


def normalized_working_text(value: str) -> str:
    value = clean(value).upper().replace("–", "-").replace("—", "-")
    value = re.sub(r"(?<=\d)\s+W\b", "W", value)
    value = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "-", value)
    value = re.sub(r"\b(CF|CG|CH|CI|CJ|CK)\s*-?\s*([0-4])\b", r"\1-\2", value)
    value = re.sub(r"\bGL\s*-?\s*([1-6])\b", r"GL-\1", value)
    value = re.sub(r"\bMA\s*2\b", "MA2", value)
    value = re.sub(r"\b(SQ|SP|SN)-RC\b", r"\1 RC", value)
    return value


ENGINE_API = re.compile(
    r"(?<![A-Z0-9-])(SQ|SP|SN|SM|SL|SJ|SH|SG|SF|SE|SD|SC|CC|CD|CE|CF-4|CF-2|CF|CG-4|CH-4|CI-4(?:\s+PLUS)?|CJ-4|CK-4)(?![A-Z0-9-])"
)


def technical(source_product: str, family: str) -> dict:
    value = normalized_working_text(source_product)
    multigrades = []
    for winter, summer in re.findall(r"(?<![0-9])(0W|5W|10W|15W|20W|25W|75W|80W|85W)\s*-?\s*(20|30|40|50|60|80|85|90|140)(?![0-9])", value):
        multigrades.append(f"{winter}-{summer}")
    monogrades = []
    for candidate in re.findall(r"\bSAE\s*:?[ ,.-]*(10W|20W|30|40|50|60|90|140|250)\b", value):
        if not any(candidate in grade for grade in multigrades):
            monogrades.append(candidate)
    if family == "T" and not multigrades and not monogrades:
        match = re.search(r"\b(75W-?85|75W-?90|80W-?90|85W-?90|85W-?140|90|140|250)\b", value)
        if match:
            candidate = match.group(1)
            multigrades.append(re.sub(r"^(\d+W)(\d+)$", r"\1-\2", candidate))
    if family == "M" and not multigrades and not monogrades:
        match = re.search(r"\b(0W-?20|5W-?20|5W-?30|5W-?40|10W-?30|10W-?40|15W-?40|15W-?50|20W-?50|25W-?50|25W-?60|10W|40|50)\b", value)
        if match:
            candidate = match.group(1)
            candidate = re.sub(r"^(\d+W)(\d+)$", r"\1-\2", candidate)
            (multigrades if re.search(r"W-?\d", candidate) else monogrades).append(candidate)
    api_gl = sorted(set(re.findall(r"\bGL-[1-6]\b", value))) if family == "T" else []
    api = sorted(set(ENGINE_API.findall(value))) if family == "M" else []
    jaso = sorted(set(re.findall(r"\b(?:JASO\s*)?(MA2|MA|MB)\b", value))) if family == "M" else []
    ilsac = sorted(set(re.findall(r"\bGF-?[1-7]\b", value))) if family == "M" else []
    acea = sorted(set(re.findall(r"(?<![A-Z0-9])(?:ACEA\s*)?(E[4-9]|A[1-7]/B[1-7]|C[1-6])(?![A-Z0-9])", value))) if family == "M" else []
    return {
        "sae": sorted(set(multigrades + monogrades)),
        "api": api,
        "api_gl": api_gl,
        "jaso": jaso,
        "ilsac": [item.replace("GF", "GF-") if "-" not in item else item for item in ilsac],
        "acea": acea,
        "resource_conserving": ["RC"] if re.search(r"(?<![A-Z])RC(?![A-Z])", value) else [],
    }


def product_name(source_product: str, family: str) -> str:
    value = clean(source_product)
    value = re.sub(
        r"^Aceites? lubricantes? para (?:motores de )?combusti[oó]n interna de (?:ciclo|Ciclo) (?:de )?(?:Otto|Diesel|Di[eé]sel)\.?\s*",
        "", value, flags=re.I,
    )
    value = re.sub(
        r"^Aceites? lubricantes? para transmisiones manuales y diferenciales de equipo automotor\.?\s*",
        "", value, flags=re.I,
    )
    if family == "I":
        return value.strip(" .,;")
    markers = []
    sae = re.search(r"\bSAE\b", value, re.I)
    if sae:
        markers.append(sae.start())
    grade = re.search(r"(?<![0-9])(0W|5W|10W|15W|20W|25W|75W|80W|85W)\s*-?\s*(20|30|40|50|60|85|90|140)(?![0-9])", value, re.I)
    if grade and re.search(r"\b(API|GL|SP|SN|SL|SQ|CF|CI|CJ|CK|JASO|GF-?)\b", value[grade.end():], re.I):
        markers.append(grade.start())
    if family == "T" and not markers:
        grade = re.search(r"\b(90|140|250)\s+(?:API\s*:?[ -]*)?GL\s*-?\s*[1-6]\b", value, re.I)
        if grade:
            markers.append(grade.start())
    if markers:
        value = value[:min(markers)]
    return clean(value).strip(" .,;-")


def normalize(row: dict) -> dict:
    standard_family = RELEVANT_STANDARDS[row["standard"]]
    if standard_family == "I":
        family = "I"
    elif re.search(r"transmisiones manuales", row["source_product"], re.I):
        family = "T"
    else:
        family = "M"
    extracted = technical(row["source_product"], family)
    name = product_name(row["source_product"], family)
    source_facts = {key: row[key] for key in (
        "holder", "source_product", "brand", "updated_at", "issued_at",
        "expires_at", "standard", "certificate_number",
    )}
    lifecycle = (
        "certificate_valid_as_of_catalog_snapshot"
        if date.fromisoformat(row["expires_at"]) >= date.fromisoformat(SNAPSHOT_DATE)
        else "certificate_expired_before_catalog_snapshot"
    )
    return {
        "source_id": SOURCE_ID,
        "source_record_id": f"INEN-EC-CERT-{row['certificate_number']}",
        "source_pdf_page": row["source_pdf_page"],
        "source_pdf_table_row": row["source_pdf_table_row"],
        "source_url": DRIVE_VIEW_URL,
        "source_landing_url": LANDING_URL,
        "source_product_field": row["source_product"],
        "source_facts_sha256": hashlib.sha256(json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "market": "Ecuador",
        "manufacturer_or_certificate_holder": row["holder"],
        "brand": row["brand"],
        "product_name": name,
        "family_code": family,
        "technical": extracted,
        "certificate_number": row["certificate_number"],
        "updated_at": row["updated_at"],
        "issued_at": row["issued_at"],
        "expires_at": row["expires_at"],
        "certified_standard": row["standard"],
        "lifecycle_status": lifecycle,
        "evidence_status": "official_government_current_product_certification_registry",
        "source_quality_flags": [
            "official_pdf_table_factual_fields_only_no_source_document_redistribution",
            *(["source_product_family_conflicts_with_certified_standard_family"] if family != standard_family else []),
        ],
    }


def main() -> None:
    payload = fetch_pdf()
    source, all_rows = source_rows(payload)
    records = sorted((normalize(row) for row in source), key=lambda row: row["certificate_number"])
    if any(not row["product_name"] for row in records):
        raise RuntimeError("INEN normalization produced an empty product name")
    non_base = [row for row in records if row["family_code"] != "I"]
    missing_sae = [row["source_record_id"] for row in non_base if not row["technical"]["sae"]]
    missing_performance = [row["source_record_id"] for row in non_base if not (row["technical"]["api"] or row["technical"]["api_gl"])]
    if missing_sae or missing_performance:
        raise RuntimeError(f"Incomplete INEN professional extraction: SAE={missing_sae}, performance={missing_performance}")
    announcement_rows = [json.loads(line) for line in ANNOUNCEMENTS.read_text(encoding="utf-8").splitlines() if line]
    current_by_text = {}
    for row in records:
        current_by_text.setdefault(source_text_key(row["source_product_field"]), []).append(row["source_record_id"])
    announcement_matches = {
        row["source_record_id"]: current_by_text[source_text_key(row["source_product_field"])][0]
        for row in announcement_rows
        if len(current_by_text.get(source_text_key(row["source_product_field"]), [])) == 1
    }
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "status": "official_ecuador_inen_current_quality_seal_registry_normalized",
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "source_url": DRIVE_VIEW_URL,
        "source_pdf_sha256": hashlib.sha256(payload).hexdigest(),
        "source_pdf_pages": EXPECTED_PAGES,
        "source_pdf_title": "LISTA SELLO INEN - 2026-07-09.xlsb",
        "source_pdf_created_at": "2026-07-15T14:19:48-05:00",
        "audited_all_certificate_rows": all_rows,
        "normalized_products": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "certified_standards": dict(sorted(Counter(row["certified_standard"] for row in records).items())),
        "distinct_holders": len({row["manufacturer_or_certificate_holder"] for row in records}),
        "distinct_brands": len({row["brand"] for row in records}),
        "rows_with_sae": sum(bool(row["technical"]["sae"]) for row in records),
        "rows_with_api": sum(bool(row["technical"]["api"]) for row in records),
        "rows_with_api_gl": sum(bool(row["technical"]["api_gl"]) for row in records),
        "rows_with_jaso": sum(bool(row["technical"]["jaso"]) for row in records),
        "rows_with_ilsac": sum(bool(row["technical"]["ilsac"]) for row in records),
        "rows_with_acea": sum(bool(row["technical"]["acea"]) for row in records),
        "valid_at_snapshot": sum(row["lifecycle_status"] == "certificate_valid_as_of_catalog_snapshot" for row in records),
        "source_standard_family_conflicts": sum("source_product_family_conflicts_with_certified_standard_family" in row["source_quality_flags"] for row in records),
        "announcement_rows_reviewed": len(announcement_rows),
        "announcement_rows_exactly_matched_to_current": len(announcement_matches),
        "announcement_rows_not_in_current_registry": len(announcement_rows) - len(announcement_matches),
        "announcement_to_current_record": dict(sorted(announcement_matches.items())),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "method": "all 1,763 certificates parsed from 81 PDF tables; exact certificate lifecycle and professional fields retained",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
