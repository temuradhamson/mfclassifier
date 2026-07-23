#!/usr/bin/env python3
"""Extract lubricant-scope item specifications from Guatemala's public SIGES catalog."""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "guatemala-siges-lubricant-nomenclature.jsonl"
REPORT = ROOT / "data" / "guatemala-siges-lubricant-nomenclature-report.json"
SOURCE_ID = "GUATEMALA_SIGES_LUBRICANT_ITEM_NOMENCLATURE"
SOURCE_URL = "https://apps.maga.gob.gt/compras/insumos"
SNAPSHOT_DATE = "2026-07-23"
EXPECTED_CATALOG_ROWS = 206416
EXPECTED_UPDATE = "13/07/2026 11:41"
EXPECTED_SELECTED_RAW_SHA256 = "174380b63cef99959bb3c0132c763816b1ebc96bf3b197dc0cde900a0ff1568a"
SEARCH_TERMS = ("aceite", "grasa", "lubricante", "refrigerante", "anticongelante", "hidráulico", "fluido", "líquido de frenos")


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", str(value or "")))).strip()


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "MFClassifierResearch/1.0 (public-government-nomenclature)"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8")


def parse_rows(page: str) -> list[tuple[str, ...]]:
    body_match = re.search(r"<tbody>([\s\S]*?)</tbody>", page)
    if not body_match:
        return []
    rows = []
    for table_row in re.findall(r"<tr>([\s\S]*?)</tr>", body_match.group(1)):
        cells = tuple(clean(cell) for cell in re.findall(r"<td[^>]*>([\s\S]*?)</td>", table_row))
        if len(cells) == 7:
            rows.append(cells)
    return rows


def page_url(term: str, page: int = 1) -> str:
    query = urllib.parse.urlencode({"itemsPerPage": 100, "currentFilter": term, "page": page})
    return f"{SOURCE_URL}?{query}"


def fetch_term(term: str) -> list[tuple[str, ...]]:
    first = fetch(page_url(term))
    pages = max([1] + [int(value) for value in re.findall(r"page=(\d+)", first)])
    payloads = [first]
    if pages > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            payloads.extend(pool.map(lambda page: fetch(page_url(term, page)), range(2, pages + 1)))
    return [row for payload in payloads for row in parse_rows(payload)]


def in_scope(row: tuple[str, ...]) -> bool:
    budget_line, _, item, characteristics, _, _, _ = row
    if budget_line == "262":
        return "cupón" not in characteristics.casefold() and item != "Combustibles y lubricante para eventos electorales y consultivos"
    return item == "Refrigerante" and "Enfriamiento de motores" in characteristics


def family(item: str, characteristics: str) -> str:
    value = f"{item} {characteristics}".casefold()
    if "líquido de frenos" in value or "uso: frenos" in value:
        return "TF"
    if "refrigerante" in value or "enfriamiento de motores" in value or "anticongelante" in value:
        return "C"
    if "grasa" in item.casefold():
        return "G"
    if any(token in value for token in ("hidrául", "hidraulic", "dirección hidráulica")) and not any(token in value for token in ("transmisión", "engranaje", "diferencial")):
        return "H"
    if any(token in value for token in ("transmisión", "engranaje", "diferencial", "caja automática", "caja de transmisión", " atf", "cvt")):
        return "T"
    if "uso: motor" in value or "motores a gasolina" in value or "motores diésel" in value:
        return "M"
    if any(token in value for token in ("compresor", "turbina", "dieléctr", "refrigeración", "corte en metales")):
        return "I"
    return "S"


def technical(characteristics: str) -> dict:
    upper = characteristics.upper()
    sae = []
    for value in re.findall(r"(?<![A-Z0-9])(?:0W[- ]?\d{2}|5W[- ]?\d{2}|10W[- ]?\d{2}|15W[- ]?\d{2}|20W[- ]?\d{2}|25W[- ]?\d{2}|70W|75W(?:[- ]?\d{2,3})?|80W(?:[- ]?\d{2,3})?|85W(?:[- ]?\d{2,3})?|SAE[- ]?(?:10|20|30|40|50|70|80|85|90|110|140|190|250))(?![A-Z0-9])", upper):
        normalized = re.sub(r"^SAE[- ]?", "", value).replace(" ", "")
        normalized = re.sub(r"^(\d+W)(\d+)$", r"\1-\2", normalized)
        if normalized not in sae:
            sae.append(normalized)
    iso_vg = []
    for value in re.findall(r"\bISO(?:\s+VG)?\s*[-:]?\s*(32|40|46|68|100|150|220|320|460|680)\b", upper):
        if value not in iso_vg:
            iso_vg.append(value)
    api_gl = sorted(set(re.findall(r"\bGL[- ]?([1-6])\b", upper)))
    dot = sorted(set(re.findall(r"\bDOT\s*([345](?:\.1)?)\b", upper)))
    nlgi = sorted(set(re.findall(r"\bNLGI\s*(?:G)?([0-6])\b", upper)))
    return {"sae": sae, "iso_vg": iso_vg, "api_gl": [f"GL-{value}" for value in api_gl], "dot": [f"DOT {value}" for value in dot], "nlgi": nlgi}


def main() -> None:
    landing = fetch(page_url("aceite"))
    total_match = re.search(r"Total de Insumos:\s*(\d+)", landing)
    update_match = re.search(r"Datos actualizados el\s*([^<]+?)\s*-", landing)
    if not total_match or int(total_match.group(1)) != EXPECTED_CATALOG_ROWS:
        raise RuntimeError("SIGES catalog denominator changed")
    if not update_match or clean(update_match.group(1)) != EXPECTED_UPDATE:
        raise RuntimeError("SIGES update timestamp changed")

    all_rows: dict[str, tuple[str, ...]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(SEARCH_TERMS)) as pool:
        for rows in pool.map(fetch_term, SEARCH_TERMS):
            for row in rows:
                all_rows[row[-1]] = row
    selected = sorted((row for row in all_rows.values() if in_scope(row)), key=lambda row: int(row[-1]))
    normalized_raw = json.dumps(selected, ensure_ascii=False, separators=(",", ":")).encode()
    selected_digest = hashlib.sha256(normalized_raw).hexdigest()
    if EXPECTED_SELECTED_RAW_SHA256 != "TO_BE_PINNED" and selected_digest != EXPECTED_SELECTED_RAW_SHA256:
        raise RuntimeError(f"SIGES selected source rows changed: {selected_digest}")

    by_code: dict[str, list[tuple[str, ...]]] = defaultdict(list)
    for row in selected:
        by_code[row[1]].append(row)
    records = []
    for code in sorted(by_code, key=int):
        rows = by_code[code]
        budget_line, _, item, characteristics, _, _, _ = rows[0]
        if len({(row[0], row[2], row[3]) for row in rows}) != 1:
            raise RuntimeError(f"SIGES item code {code} has conflicting definitions")
        presentations = [
            {"presentation": row[4], "quantity_and_unit": row[5], "presentation_code": row[6]}
            for row in rows
        ]
        family_code = family(item, characteristics)
        spec = technical(characteristics)
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"SIGES-GT-ITEM-{code}",
            "source_url": SOURCE_URL,
            "source_item_code": code,
            "source_budget_line": budget_line,
            "source_item_name": item,
            "source_characteristics": characteristics,
            "source_presentations": presentations,
            "source_facts_sha256": hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "source_catalog_updated_at": EXPECTED_UPDATE,
            "market": "Guatemala",
            "brand": "Brand not stated (SIGES source)",
            "product_name": f"{item} — {characteristics.rstrip(';')}",
            "family_code": family_code,
            "technical": spec,
            "lifecycle_status": "current_government_procurement_nomenclature_as_of_snapshot_not_market_availability",
            "evidence_status": "official_government_procurement_item_nomenclature",
            "source_quality_flags": [
                "generic_procurement_item_not_a_commercial_brand_product",
                "nomenclature_presence_is_not_performance_approval_or_market_availability",
                "source_presentations_collapsed_to_one_technical_item_identity",
            ],
        })
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "status": "official_guatemala_siges_lubricant_nomenclature_normalized",
        "source_url": SOURCE_URL,
        "source_catalog_updated_at": EXPECTED_UPDATE,
        "source_catalog_total_rows": EXPECTED_CATALOG_ROWS,
        "search_terms": list(SEARCH_TERMS),
        "search_union_rows": len(all_rows),
        "selected_source_presentations": len(selected),
        "normalized_item_identities": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "selected_raw_sha256": selected_digest,
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "method": "complete paginated searches across eight Spanish lubricant terms; official budget line 262 plus explicit engine-coolant rows; coupon and aggregate event-service rows excluded; presentations collapsed by SIGES item code",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
