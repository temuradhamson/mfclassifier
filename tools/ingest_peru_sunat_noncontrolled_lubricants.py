#!/usr/bin/env python3
"""Normalize explicit lubricant/technical-fluid rows from Peru SUNAT's list.

The source is a national regulatory evaluation list, not a product approval
catalogue.  It proves only that the named product was published as "NO
CONTROLADO" under DS 268-2019-EF.  The script audits every printed item number,
uses a deliberately broad candidate screen, and then retains only explicit
lubricant, grease, coolant, brake-fluid, hydraulic-fluid or closely related
service-fluid names from a reviewed item allow-list.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "peru-sunat-noncontrolled-lubricants.jsonl"
REPORT = ROOT / "data" / "peru-sunat-noncontrolled-lubricants-report.json"
SOURCE_ID = "PERU_SUNAT_2025_NONCONTROLLED_LUBRICANT_PRODUCTS"
SOURCE_URL = "https://orientacion.sunat.gob.pe/sites/default/files/inline-files/PORTAL%203%20Productos%20NO%20CONTROLADOS%20NACIONAL%20DS%20268%202019%20%2030.04.2025_2.pdf"
LANDING_URL = "https://orientacion.sunat.gob.pe/insumos-quimicos-y-bienes-fiscalizados"
SNAPSHOT_DATE = "2026-07-22"
SOURCE_LIST_DATE = "2025-04-30"
EXPECTED_PDF_SHA256 = "f8e154f1b352853fcc95aabebf4543b71905eef8e097742cc87b7b93c4e61ce8"
EXPECTED_PAGES = 302
EXPECTED_ALL_ROWS = 4518
EXPECTED_CANDIDATES = 176


CANDIDATE_PATTERN = re.compile(
    r"\b(?:fluid|paste|chain|bearing|gear|hydraulic|motor|engine|brake|cool\w*|"
    r"anti\w*freeze|refriger\w*|fork|silicone|moly\w*|ptfe|penetrant|penetrating)\b|"
    r"anti.?seize|release agent|rust inhibitor|corrosion inhibitor|gras[ao]|grease|"
    r"lub|aceite|\boil\b",
    re.I,
)

# Item numbers were reviewed against the exact pinned PDF table.  Rows that
# merely mention oil during cleaning/testing, food oils, paints, sealants,
# degreasers and laboratory standards are intentionally absent.
FAMILY_ITEMS = {
    "TF": {
        572, 834, 835, 2709,
        3245, 3246, 3247, 3248, 3249, 3250, 3251, 3254, 3256,
    },
    "H": {3495},
    "G": {
        433, 922, 1137, 1152, 1153, 1451, 1723, 1728, 2057, 2058, 2059,
        2060, 2599, 2826, 2832, 2863, 2864, 2957, 2991, 3157, 3806, 3910,
        4430,
    },
    "I": {364, 1338},
    "S": {
        482, 483, 617, 1734, 2266,
        169, 329, 365, 366, 367, 368, 459, 571, 578, 707, 836, 1049, 1050,
        1051, 1083, 1170, 1611, 1694, 1700, 1725, 1726, 1727, 1759, 1760,
        2621, 2622, 2623, 2624, 2625, 2626, 2627, 2828, 2829, 2830, 2831,
        2848, 2992, 2993, 3009, 3183, 3417, 3515, 3971, 3977, 3979, 3980,
        3995, 3996, 4157, 4192, 4394,
    },
}

# Exact source occurrences that identify the same product/code are collapsed;
# every printed item number remains attached to the normalized identity.
DUPLICATE_ITEM_GROUPS = (
    {365, 366},
    {367, 368},
    {482, 483},
    {1152, 1153},
    {1728, 2057},
    {2828, 2829},
    {2863, 2864},
    {3979, 3980},
)

BRANDS = {
    "ABRO": "ABRO",
    "AFS FILTER": "AFS",
    "ANTICONGELANTE/REFRIGERANTE PRESTONE": "Prestone",
    "AUTOPROFI": "AUTOPROFI",
    "BG ": "BG",
    "CHO-LUBE": "CHO-LUBE",
    "DRAKEOL": "DRAKEOL",
    "ELAN-PLUS": "ELAN-Plus",
    "FLUID FILM": "FLUID FILM",
    "FORTIFICADOR DE ACEITE DE MOTOR ASTRATECH": "ASTRATECH",
    "LOCTITE": "LOCTITE",
    "LUBRIZOL": "Lubrizol",
    "MAXXPOWER": "MAXXPOWER",
    "MOLYKOTE": "MOLYKOTE",
    "NOVALUBE": "NOVALUBE",
    "NYCO GREASE": "NYCO",
    "NYCOLUBE": "NYCO",
    "POWER LUBE": "POWER LUBE",
    "PRESTONE": "Prestone",
    "ROYCO": "ROYCO",
    "SUPER LUBE": "SUPER LUBE",
    "SYNTHA-TECH": "SYNTHA-TECH",
    "TRATAMIENTO PARA ACEITE DE MOTOR ASTRATECH": "ASTRATECH",
    "ULTILUBE": "ULTILUBE",
    "WEICOLUB": "WEICOLUB",
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_pdf() -> bytes:
    request = urllib.request.Request(SOURCE_URL, headers={
        "User-Agent": "MFClassifierResearch/1.0 (public-government-regulatory-data)",
    })
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    if not payload.startswith(b"%PDF-"):
        raise RuntimeError("SUNAT source did not return a PDF")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_PDF_SHA256:
        raise RuntimeError(f"SUNAT PDF changed: expected {EXPECTED_PDF_SHA256}, got {digest}")
    return payload


def parse_rows(payload: bytes) -> list[dict]:
    rows = []
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        if len(pdf.pages) != EXPECTED_PAGES:
            raise RuntimeError(f"Expected {EXPECTED_PAGES} pages, got {len(pdf.pages)}")
        for page_number, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            if len(tables) != 1:
                raise RuntimeError(f"Expected one table on page {page_number}, got {len(tables)}")
            for source in tables[0][1:]:
                if len(source) != 3 or not clean(source[0]).isdigit():
                    raise RuntimeError(f"Unexpected SUNAT table row on page {page_number}: {source!r}")
                item = int(clean(source[0]))
                evaluation = clean(source[2])
                # Item 828 has a long identifier list overprinted into the
                # result cell by the source PDF.  The visible final words are
                # still NO CONTROLADO; preserve the anomaly without treating
                # the OCR-like identifier fragments as an evaluation value.
                if item == 828 and evaluation == "100EN,O 2 4C7O2N, 2T4R7O3L2A, 2D4O7 53,":
                    evaluation = "NO CONTROLADO"
                rows.append({
                    "item": item,
                    "page": page_number,
                    "source_product": clean(source[1]),
                    "evaluation": evaluation,
                })
    if [row["item"] for row in rows] != list(range(1, EXPECTED_ALL_ROWS + 1)):
        raise RuntimeError("SUNAT item numbers are not the exact sequential range 1..4518")
    if any(row["evaluation"] != "NO CONTROLADO" for row in rows):
        raise RuntimeError("Unexpected evaluation value in pinned SUNAT list")
    candidates = [row for row in rows if CANDIDATE_PATTERN.search(row["source_product"])]
    if len(candidates) != EXPECTED_CANDIDATES:
        raise RuntimeError(f"Candidate screen drifted: expected {EXPECTED_CANDIDATES}, got {len(candidates)}")
    return rows


def family_by_item() -> dict[int, str]:
    result = {}
    for family, items in FAMILY_ITEMS.items():
        for item in items:
            if item in result:
                raise RuntimeError(f"SUNAT item {item} assigned to multiple families")
            result[item] = family
    return result


def brand_from_name(name: str) -> str:
    upper = name.upper()
    for prefix, brand in BRANDS.items():
        if prefix in upper:
            return brand
    return ""


def source_code_text(name: str) -> list[str]:
    values = []
    for match in re.findall(r"\(([^()]*(?:c[oó]digo|code|number|n[uú]mero|item|parte|article)[^()]*)\)", name, re.I):
        value = clean(match)
        if value not in values:
            values.append(value)
    return values


def identity_anchor(item: int) -> int:
    for group in DUPLICATE_ITEM_GROUPS:
        if item in group:
            return min(group)
    return item


def normalize_group(rows: list[dict], family: str) -> dict:
    primary = rows[0]
    item_numbers = [row["item"] for row in rows]
    source_names = [row["source_product"] for row in rows]
    facts = {
        "items": item_numbers,
        "pages": [row["page"] for row in rows],
        "source_products": source_names,
        "evaluation": "NO CONTROLADO",
    }
    return {
        "source_id": SOURCE_ID,
        "source_record_id": f"SUNAT-PE-DS268-ITEM-{item_numbers[0]:04d}",
        "source_url": SOURCE_URL,
        "source_landing_url": LANDING_URL,
        "source_item_numbers": item_numbers,
        "source_pdf_pages": [row["page"] for row in rows],
        "source_product_fields": source_names,
        "source_code_text": sorted({value for name in source_names for value in source_code_text(name)}),
        "source_evaluation": "NO CONTROLADO",
        "source_list_date": SOURCE_LIST_DATE,
        "source_facts_sha256": hashlib.sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "market": "Peru",
        "manufacturer_or_certificate_holder": "",
        "brand": brand_from_name(primary["source_product"]),
        "product_name": primary["source_product"],
        "family_code": family,
        "technical": {},
        "lifecycle_status": "listed_noncontrolled_as_of_2025_04_30_current_status_unverified",
        "evidence_status": "official_government_regulatory_product_evaluation_list",
        "source_quality_flags": [
            "source_proves_noncontrolled_regulatory_status_not_product_performance_or_approval",
            "manufacturer_and_certificate_holder_not_published",
            "product_type_retained_only_when_explicit_in_source_name",
        ],
    }


def main() -> None:
    payload = fetch_pdf()
    rows = parse_rows(payload)
    assigned = family_by_item()
    by_item = {row["item"]: row for row in rows}
    if not set(assigned).issubset({row["item"] for row in rows if CANDIDATE_PATTERN.search(row["source_product"])}):
        raise RuntimeError("Reviewed SUNAT item fell outside the reproducible broad candidate screen")
    grouped = {}
    for item, family in assigned.items():
        grouped.setdefault((identity_anchor(item), family), []).append(by_item[item])
    records = [normalize_group(sorted(group_rows, key=lambda row: row["item"]), family) for (_, family), group_rows in sorted(grouped.items())]
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "status": "official_peru_sunat_noncontrolled_lubricant_product_evidence_normalized",
        "source_url": SOURCE_URL,
        "source_pdf_sha256": hashlib.sha256(payload).hexdigest(),
        "source_pdf_pages": EXPECTED_PAGES,
        "source_pdf_title": "Productos Consultados VIGENCIA DEL DS 268 2019 EF.xlsx",
        "source_pdf_created_at": "2025-05-20T10:08:21-05:00",
        "source_list_date": SOURCE_LIST_DATE,
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "audited_all_product_rows": len(rows),
        "broad_candidate_rows_reviewed": EXPECTED_CANDIDATES,
        "relevant_source_occurrences": len(assigned),
        "duplicate_source_occurrences_collapsed": len(assigned) - len(records),
        "normalized_product_identities": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_excluded_after_candidate_review": EXPECTED_CANDIDATES - len(assigned),
        "source_table_extraction_anomalies": 1,
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "method": "all 4,518 sequential table rows parsed; 176 broad lexical candidates manually reviewed; only explicit lubricant and technical-fluid names retained",
        "scope_warning": "NO CONTROLADO is a SUNAT regulatory evaluation result, not a lubricant approval or performance certification",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
