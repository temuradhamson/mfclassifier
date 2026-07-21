#!/usr/bin/env python3
"""Normalize lubricant-scope products from the public KEBS S-Mark directory."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "kebs-smark-lubricant-products.jsonl"
REPORT = ROOT / "data" / "kebs-smark-lubricant-products-report.json"
CACHE = ROOT / ".cache" / "kebs-smark"
SOURCE_URL = "https://www.kebs.org/products-with-smarks/"
SOURCE_CONTEXT_URL = "https://www.kebs.org/marks-of-quality/"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-directory)"
SEARCH_TERMS = [
    "oil", "lubricant", "grease", "coolant", "antifreeze", "hydraulic fluid",
    "brake fluid", "transmission fluid", "metalworking fluid", "cutting fluid",
    "engine oil", "motor oil", "gear oil", "automatic transmission oil",
    "hydraulic oil", "compressor oil", "turbine oil", "transformer oil",
    "chain lubricant", "machine oil", "heat transfer oil", "refrigeration oil",
    "power steering fluid", "radiator coolant", "industrial lubricant",
]


def clean(value: str | None) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", value).strip()


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


def page_url(term: str, index: int) -> str:
    return SOURCE_URL + "?" + urllib.parse.urlencode({"act": "", "index": index, "search": term})


def cache_path(term: str, index: int) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", term.casefold()).strip("-")
    return CACHE / f"{slug}-{index:05d}.html"


def fetch(term: str, index: int) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = cache_path(term, index)
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(page_url(term, index), headers={"User-Agent": USER_AGENT})
    error = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = response.read()
            page_text = body.decode("utf-8", "ignore")
            if not re.search(r"Dispalying\s+\d+\s+to\s+\d+\s+of\s+[\d,]+\s+S-Marks|Search\s+result\s*\(\s*0\s*\)|\b0\s+S-Marks\b", page_text, re.I):
                raise RuntimeError("unexpected KEBS response")
            path.write_bytes(body)
            time.sleep(0.03)
            return body
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            error = exc
            time.sleep(min(10, 1.2 * (attempt + 1)))
    raise RuntimeError(f"Failed KEBS page {term!r} index={index}: {error}")


def result_count(body: bytes) -> int:
    text = body.decode("utf-8", "ignore")
    match = re.search(r"Dispalying\s+\d+\s+to\s+\d+\s+of\s+([\d,]+)\s+S-Marks", text, re.I)
    if match:
        return int(match.group(1).replace(",", ""))
    if re.search(r"\b0\s+S-Marks\b|Search\s+result\s*\(\s*0\s*\)", text, re.I):
        return 0
    raise RuntimeError("KEBS result count not found")


def capture(card: str, pattern: str) -> str:
    match = re.search(pattern, card, re.I | re.S)
    return clean(match.group(1)) if match else ""


def parse_page(body: bytes, term: str, index: int) -> list[dict]:
    text = body.decode("utf-8", "ignore")
    rows = []
    for card in re.split(r'<div\s+class="w3layouts-advert\s*"\s*>', text)[1:]:
        card = card.split('<div style="clear:both"></div>', 1)[0]
        permit = capture(card, r"SM#\s*<font[^>]*>(.*?)</font>")
        product = capture(card, r"Product:</h4>.*?<h3>\s*<font[^>]*>(.*?)</font>")
        brand = capture(card, r"Brand:</h4>.*?<h4>(.*?)</h4>")
        company = capture(card, r"Company:</h4>.*?<h5>(.*?)</h5>")
        standard = capture(card, r'<div\s+class="job-body".*?<div[^>]*>(.*?)</div>')
        status = capture(card, r'<div\s+class="job-suffix".*?<h3>\s*<font[^>]*>(.*?)</font>')
        issue_date = capture(card, r"Issue:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
        expiry_date = capture(card, r"Expiry:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
        if not permit or not product:
            continue
        rows.append({
            "permit_number": permit,
            "product": product,
            "brand": brand,
            "company": company,
            "standard": standard,
            "status": status,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "search_term": term,
            "source_index": index,
            "source_url": page_url(term, index),
        })
    return rows


def visible_card_count(body: bytes) -> int:
    return len(re.findall(rb'<div\s+class="w3layouts-advert\s*"\s*>', body, re.I))


def family_for(row: dict) -> tuple[str, str] | None:
    product = f" {normalize(row['product'])} "
    if any(token in product for token in (" oil filter ", " oil filters ", " lubricant filter ", " lubricant filters ")):
        return None
    value = normalize(" ".join([row["product"], row["brand"], row["standard"]]))
    padded = f" {value} "
    exclusions = (
        " edible oil ", " cooking oil ", " vegetable oil ", " hair oil ",
        " body oil ", " massage oil ", " baby oil ", " essential oil ",
        " petroleum jelly cosmetic ", " oil paint ", " printing ink ",
        " oil based paint ", " oil seed ", " oil cake ",
    )
    if any(token in padded for token in exclusions):
        return None
    rules = [
        ("TF", "brake_fluid", (" brake fluid ",)),
        ("TF", "engine_or_radiator_coolant", (" engine coolant ", " radiator coolant ", " antifreeze ", " anti freeze ", " cooling system coolant ")),
        ("T", "transmission_or_gear_lubricant", (" transmission fluid ", " transmission oil ", " automatic transmission ", " manual transmission oil ", " atf ", " gear oil ", " gear lubricant ", " gear lubricating oil ", " axle oil ", " differential oil ", " cvt fluid ", " dct fluid ")),
        ("H", "hydraulic_or_power_steering_fluid", (" hydraulic oil ", " hydraulic fluid ", " hydraulic lubricating oil ", " power steering fluid ", " hydrostatic fluid ")),
        ("C", "compressor_or_refrigeration_oil", (" compressor oil ", " refrigeration oil ", " refrigerating oil ")),
        ("U", "turbine_oil", (" turbine oil ",)),
        ("E", "transformer_or_insulating_oil", (" transformer oil ", " insulating oil ", " dielectric oil ")),
        ("G", "lubricating_grease", (" lubricating grease ", " lubricating greases ", " lubricant grease ", " automotive grease ", " bearing grease ", " multipurpose grease ", " multi purpose grease ", " chassis grease ", " wheel bearing grease ", " grease specification ")),
        ("M", "engine_or_motor_oil", (" engine oil ", " engine oils ", " motor oil ", " motor oils ", " crankcase oil ", " two stroke oil ", " four stroke oil ", " 2t oil ", " 4t oil ")),
        ("I", "industrial_or_process_lubricant", (" lubricating oil ", " industrial lubricant ", " machine oil ", " machinery oil ", " cutting oil ", " cutting fluid ", " metalworking fluid ", " chain oil ", " chain lubricant ", " heat transfer oil ", " quenching oil ", " slideway oil ", " spindle oil ", " circulating oil ", " mould oil ", " mold oil ", " shuttering oil ", " rust preventive oil ", " wire rope lubricant ")),
    ]
    for family, basis, tokens in rules:
        if any(token in padded for token in tokens):
            return family, basis
    return None


def technical(text: str) -> dict:
    upper = clean(text).upper().replace("–", "-").replace("—", "-")
    sae = sorted(set(re.findall(r"(?<!\d)((?:0|5|10|15|20|25)W[- ]?\d{2})(?!\d)", upper)))
    sae = [value.replace(" ", "-") for value in sae]
    sae_mono = sorted(set(re.findall(r"\bSAE\s*((?:0|5|10|15|20|25)W|20|30|40|50|60)\b", upper)))
    sae_gear = sorted(set(re.findall(r"(?<!\d)((?:70|75|80|85)W(?:[- ]?\d{2,3})?)(?!\d)", upper)))
    sae_gear = [value.replace(" ", "-") for value in sae_gear]
    api = sorted(set(re.findall(r"\bAPI\s*[-:]?\s*(SP|SN(?:\s+PLUS)?|SM|SL|SJ|CI[- ]?4(?:\s+PLUS)?|CJ[- ]?4|CK[- ]?4|CH[- ]?4|CF[- ]?4|CF)\b", upper)))
    api = [re.sub(r"^(C(?:I|J|K|H|F))[- ]?4", r"\1-4", value) for value in api]
    iso_vg = sorted(set(re.findall(r"\bISO\s*(?:VG)?\s*(22|32|46|68|100|150|220|320|460|680)\b", upper)))
    nlgi = sorted(set(re.findall(r"\bNLGI\s*(000|00|0|1|2|3|4|5|6)\b", upper)))
    return {"sae": sae, "sae_monograde": sae_mono, "sae_gear": sae_gear, "api": api, "iso_vg": iso_vg, "nlgi": nlgi}


def main() -> None:
    first_pages = {term: fetch(term, 0) for term in SEARCH_TERMS}
    counts = {term: result_count(body) for term, body in first_pages.items()}
    requests = [(term, index) for term, count in counts.items() for index in range(10, count, 10)]
    pages = {(term, 0): body for term, body in first_pages.items()}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch, term, index): (term, index) for term, index in requests}
        for future in as_completed(futures):
            pages[futures[future]] = future.result()

    occurrences = []
    for (term, index), body in sorted(pages.items()):
        occurrences.extend(parse_page(body, term, index))
    by_permit: dict[str, dict] = {}
    for row in occurrences:
        permit = normalize(row["permit_number"])
        if permit not in by_permit:
            by_permit[permit] = row | {"search_terms": [row["search_term"]], "source_urls": [row["source_url"]]}
        else:
            target = by_permit[permit]
            target["search_terms"] = sorted(set(target["search_terms"] + [row["search_term"]]))
            target["source_urls"] = sorted(set(target["source_urls"] + [row["source_url"]]))

    scoped = []
    excluded = []
    for row in by_permit.values():
        classified = family_for(row)
        if not classified:
            excluded.append(row)
            continue
        family, basis = classified
        scoped.append(row | {"family_code": family, "classification_basis": basis})

    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in scoped:
        key = (normalize(row["company"]), normalize(row["brand"]), normalize(row["product"]), row["family_code"])
        grouped[key].append(row)

    records = []
    for key, rows in sorted(grouped.items()):
        first = sorted(rows, key=lambda row: (row["expiry_date"], row["permit_number"]), reverse=True)[0]
        permits = []
        for row in sorted(rows, key=lambda item: item["permit_number"]):
            permits.append({
                "permit_number": row["permit_number"],
                "status": normalize(row["status"]),
                "issue_date": row["issue_date"],
                "expiry_date": row["expiry_date"],
                "standard": row["standard"],
                "source_urls": row["source_urls"],
            })
        valid = any(normalize(row["status"]) == "valid" for row in rows)
        identity = "|".join(key)
        source_record_id = "KEBS-SM-" + hashlib.sha256(identity.encode()).hexdigest()[:16].upper()
        combined = " ".join([first["product"], first["brand"], *[row["standard"] for row in rows]])
        records.append({
            "source_id": "KEBS_SMARK_LUBRICANT_PRODUCTS",
            "source_record_id": source_record_id,
            "source_url": SOURCE_URL,
            "source_context_url": SOURCE_CONTEXT_URL,
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "market": "KE",
            "manufacturer": first["company"],
            "brand": first["brand"] or first["company"],
            "product_name": first["product"],
            "family_code": first["family_code"],
            "classification_basis": first["classification_basis"],
            "technical": technical(combined),
            "standards": sorted({row["standard"] for row in rows if row["standard"]}),
            "permit_entries": permits,
            "source_permit_count": len(rows),
            "search_terms": sorted({term for row in rows for term in row["search_terms"]}),
            "lifecycle_status": "valid_smark_permit" if valid else "historical_expired_smark_permit",
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_public_government_product_certification_directory_normalized",
        "source_id": "KEBS_SMARK_LUBRICANT_PRODUCTS",
        "source_url": SOURCE_URL,
        "source_context_url": SOURCE_CONTEXT_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "directory_total_smarks": result_count(fetch("", 0)),
        "search_result_counts": counts,
        "downloaded_search_pages": len(pages),
        "visible_search_cards": sum(visible_card_count(body) for body in pages.values()),
        "search_occurrences": len(occurrences),
        "visible_cards_not_parsed": sum(visible_card_count(body) for body in pages.values()) - len(occurrences),
        "unique_permits_observed": len(by_permit),
        "lubricant_scope_permits": len(scoped),
        "out_of_scope_permits_excluded": len(excluded),
        "normalized_products": len(records),
        "duplicate_or_renewal_permits_merged": len(scoped) - len(records),
        "manufacturers": len({row["manufacturer"] for row in records}),
        "brands": len({row["brand"] for row in records}),
        "lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "rights_note": "Public product-verification facts only; Kenya Standard text is not copied. Standard designation/title is retained as certification evidence.",
        "excluded_fields": ["addresses", "contacts", "standard_body_text"],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
