#!/usr/bin/env python3
"""Inventory ACE Cayman's current automotive-class lubricant/fluid listings.

The source class mixes fluids with a small number of automotive parts and
cleaning aerosols. The complete listing denominator is retained in the report;
only explicitly in-scope lubricant, grease, additive and technical-fluid rows
are written to the normalized SKU layer.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/cayman-ace-current-automotive-fluids.jsonl"
PRODUCTS = ROOT / "data/cayman-ace-current-automotive-products.jsonl"
EXCLUSIONS = ROOT / "data/cayman-ace-current-automotive-exclusions.jsonl"
REPORT = ROOT / "data/cayman-ace-current-automotive-report.json"
SOURCE_ID = "CAYMAN_ACE_CURRENT_AUTOMOTIVE_FLUID_CATALOG"
BASE_URL = "https://shop.acecayman.com"
LISTING_URL = (
    BASE_URL
    + "/inet/storefront/store.php?top={offset}&class=125&department=08"
    + "&mode=browsecategory&refine=Y"
)
OFFSETS = tuple(range(0, 165, 15))
EXCLUDED_SOURCE_NAMES = {
    "CARB & THROT BODY CLNR 13OZ": "cleaning_aerosol_outside_scope",
    "FLAG": "non_product_merchandising_item",
    "GAS SHOCKS": "automotive_part_outside_scope",
    "N0-CHLR LOW VOC BPC 15OZ": "brake_parts_cleaner_outside_scope",
    "RADIATOR": "automotive_part_outside_scope",
    "RADIATOR (16MM)": "automotive_part_outside_scope",
    "ROTOR": "automotive_part_outside_scope",
    "SHOCK": "automotive_part_outside_scope",
    "TIE ROD END": "automotive_part_outside_scope",
    "VPS THROTTLE BODY SPRAY": "cleaning_aerosol_outside_scope",
}


def clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value).replace("\xa0", " ")).strip()


def fetch(url: str, attempts: int = 4) -> bytes:
    for attempt in range(attempts):
        result = subprocess.run(
            [
                "curl", "-LsS", "--fail", "--max-time", "60",
                "-A", "Mozilla/5.0 (compatible; catalog-research/1.0)",
                url,
            ],
            capture_output=True,
        )
        if result.returncode == 0:
            return result.stdout
        if attempt + 1 == attempts:
            raise RuntimeError(
                f"fetch failed after {attempts} attempts: {url}: "
                + result.stderr.decode("utf-8", errors="replace")
            )
        time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def parse_cards(payload: bytes) -> tuple[int, list[dict]]:
    source = payload.decode("utf-8", errors="replace")
    count_match = re.search(r"(\d+) found, showing page \d+ of \d+", source)
    assert count_match
    total = int(count_match.group(1))
    blocks = re.findall(
        r'<div valign="top".*?<div class="product_body">(.*?)'
        r"</div>\s*</div></div>",
        source,
        flags=re.S,
    )
    rows = []
    for block in blocks:
        link_match = re.search(
            r'<h4 class="store_product_name"><a href="([^"]+)">(.*?)</a>',
            block,
            flags=re.S,
        )
        sku_match = re.search(
            r'<span class="store_product_sku">SKU:\s*(.*?)</span>',
            block,
            flags=re.S,
        )
        price_match = re.search(
            r'<div class="product_price">(.*?)</div>', block, flags=re.S
        )
        stock_match = re.search(r'alt\s*=\s*"(badge-[^"]+)"', block)
        assert link_match and sku_match and price_match and stock_match
        price_text = clean(price_match.group(1))
        amount_match = re.search(r"\$([\d,]+(?:\.\d+)?)", price_text)
        rows.append({
            "source_sku": clean(sku_match.group(1)),
            "source_product_name": clean(link_match.group(2)),
            "source_url": urljoin(BASE_URL, link_match.group(1)),
            "listing_availability": stock_match.group(1).removeprefix("badge-"),
            "listing_price_amount": (
                float(amount_match.group(1).replace(",", ""))
                if amount_match else None
            ),
            "listing_price_currency": "KYD" if amount_match else "",
        })
    return total, rows


def detail_fields(payload: bytes) -> dict:
    source = payload.decode("utf-8", errors="replace")
    title_match = re.search(
        r'<h1 id="product-title"[^>]*>(.*?)</h1>', source, flags=re.S
    )
    sku_match = re.search(r'<span class="part_no">SKU:\s*(.*?)</span>', source)
    description_match = re.search(
        r'<p class="store_product_description">(.*?)</p>', source, flags=re.S
    )
    lifecycle_match = re.search(
        r'<span id="qty-number"[^>]*>(.*?)</span>', source, flags=re.S
    )
    assert title_match and sku_match and description_match
    table = {}
    for key, value in re.findall(
        r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', source, flags=re.S
    ):
        table[clean(key).rstrip(":")] = clean(value)
    return {
        "detail_product_name": clean(title_match.group(1)),
        "detail_sku": clean(sku_match.group(1)),
        "description_text": clean(description_match.group(1)),
        "description_sha256": hashlib.sha256(
            clean(description_match.group(1)).encode("utf-8")
        ).hexdigest(),
        "detail_lifecycle": (
            clean(lifecycle_match.group(1)) if lifecycle_match else ""
        ),
        "manufacturer": table.get("Manufacturer", ""),
        "source_brand": table.get("Brand", ""),
        "unit_of_measure": table.get("U/M", ""),
    }


def family_for(title: str) -> str:
    upper = title.upper()
    if "COOLANT" in upper or "ANTIFREEZE" in upper:
        return "C"
    if re.search(r"\bDEF\b", upper):
        return "E"
    if "GREASE" in upper or re.search(r"\bGR[.-]", upper):
        return "G"
    if "HYD" in upper:
        return "H"
    if "ISO 220 GEAR" in upper:
        return "I"
    if any(
        token in upper
        for token in (
            "ATF", "TRANSMISSION", "TRANS.FL", "GEAR OIL", "HPGO",
            "P/STG", "PWR.STRG", "BRAKE FLUID", "BRK FLD", "UNITRAC",
            "DEXTRON", "MOTUL RBF",
        )
    ) or re.search(r"\b(?:75W|80W|85W)\s*-?\s*\d{2,3}\b", upper):
        return "T"
    if any(
        token in upper
        for token in (
            "CLEANER", "CLNR", "TREATMENT", "WATER REMOVER",
        )
    ):
        return "U"
    if "WD-40" in upper:
        return "S"
    return "M"


def specifications(title: str, description: str, family: str) -> dict:
    text = f"{title} {description}".upper()
    specs: dict[str, list[str]] = {}
    sae = []
    for winter, hot in re.findall(
        r"(?<!\d)(?:SAE\s*)?"
        r"(0W|5W|10W|15W|20W|75W|80W|85W)[- ]?(\d{2,3})\b",
        text,
    ):
        value = f"{winter}-{hot}"
        if value not in sae:
            sae.append(value)
    if sae:
        specs["sae_gear" if family in {"I", "T"} else "sae_engine"] = sae
    monogrades = []
    for value in re.findall(r"\bSAE\s*(30|40|50)\b", text):
        if value not in monogrades:
            monogrades.append(value)
    if monogrades and family == "M":
        specs.setdefault("sae_engine", []).extend(monogrades)
    iso_vg = []
    for value in re.findall(r"\b(?:ISO|AW#?)\s*(32|46|68|220)\b", text):
        if value not in iso_vg:
            iso_vg.append(value)
    if iso_vg:
        specs["iso_vg"] = iso_vg
    dot = []
    for value in re.findall(r"\bDOT\s*([345])\b", text):
        label = f"DOT {value}"
        if label not in dot:
            dot.append(label)
    if "DOT 3&4" in text or "DOT 3 & 4" in text:
        dot = ["DOT 3", "DOT 4"]
    if dot:
        specs["dot"] = dot
    api = []
    for value in re.findall(r"\bAPI\s+((?:SP|SN|SM|SL|SJ|CI-4|CJ-4|CK-4|CF-4|GL-5))\b", text):
        if value not in api:
            api.append(value)
    if api:
        specs["api"] = api
    return specs


def product_grade_label(value: str) -> str:
    label = value.upper().strip()
    label = re.sub(r"\s*\(\s*884721\s*\)\s*$", "", label)
    package_suffixes = (
        r"(?:12/1|6/1)?\s*(?:"
        r"55\s*(?:GAL(?:LON)?|GL|G)|"
        r"5\s*(?:GAL(?:LON)?|GL|G|QRTS?|QTS?|QT)|"
        r"GALLON|GAL|GL|QRTS?|QRT|QUART|QT|PT|"
        r"32\s*OZ|15\s*OZ|14\.1\s*OZ\.?\s*CART\.?|12\s*OZ|"
        r"1\s*LB|35\s*LB|35#|1#|CTG\.?|CART\.?"
        r")"
    )
    previous = None
    while previous != label:
        previous = label
        label = re.sub(
            rf"\s*[-/]?\s*{package_suffixes}(?:\s*EXP\.?)?\s*$",
            "",
            label,
        ).strip(" ./-")
    label = re.sub(r"\s+", " ", label)
    alias = {
        "10W40 MAXLIFE": "MAXLIFE 10W40",
        "20W50 MAXLIFE OIL": "MAXLIFE 20W50",
        "MAX LIFE 20W50 MOTOR OIL": "MAXLIFE 20W50",
        "DOT 3&4 BRK FLD": "DOT 3&4 BRAKE FLUID",
        "P/STG.FL": "POWER STEERING FLUID",
        "PWR.STRG.FLUID": "POWER STEERING FLUID",
        "PB SAE15W-40": "PREMIUM BLUE SAE15W-40",
        "PREMIUM BLUE 15W-40": "PREMIUM BLUE SAE15W-40",
        "HPGO85W140": "HPGO 85W140",
        "SAE5W30 ADV. FULL SYN.": "ADVANCED FULL SYNTHETIC SAE5W30",
        "5W30 ADV. FULL SYN.": "ADVANCED FULL SYNTHETIC SAE5W30",
    }
    return alias.get(label, label)


def product_rows_from_skus(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        specs_key = json.dumps(
            row["specifications"], ensure_ascii=False, sort_keys=True
        )
        key = (
            row["brand"],
            row["family_code"],
            product_grade_label(row["source_product_name"]),
            specs_key,
        )
        groups.setdefault(key, []).append(row)
    products = []
    for (brand, family, label, _), members in sorted(groups.items()):
        skus = sorted(row["source_sku"] for row in members)
        source_names = sorted({
            row["source_product_name"] for row in members
        })
        urls = sorted({row["source_url"] for row in members})
        manufacturers = sorted({
            row["manufacturer"] for row in members if row["manufacturer"]
        })
        group_material = json.dumps(
            [brand, family, label, members[0]["specifications"]],
            ensure_ascii=False,
            sort_keys=True,
        )
        group_hash = hashlib.sha256(
            group_material.encode("utf-8")
        ).hexdigest()
        products.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"ACE-CAYMAN-PRODUCT-{group_hash[:20]}",
            "country": "Cayman Islands",
            "product_name": label,
            "source_product_names": source_names,
            "brand": brand,
            "manufacturers": manufacturers,
            "family_code": family,
            "specifications": members[0]["specifications"],
            "source_skus": skus,
            "source_sku_count": len(skus),
            "source_urls": urls,
            "lifecycle_status": (
                "listed_current_catalog_unavailable"
                if any(
                    row["lifecycle_status"] == "listed_current_catalog"
                    for row in members
                )
                else "historical_discontinued_retail_catalog"
            ),
            "snapshot_date": str(date.today()),
            "source_quality_flags": sorted({
                flag
                for row in members
                for flag in row["source_quality_flags"]
            }),
        })
    return products


def render(rows: list[dict]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )


def main() -> None:
    listing_rows = []
    totals = set()
    for offset in OFFSETS:
        total, rows = parse_cards(fetch(LISTING_URL.format(offset=offset)))
        totals.add(total)
        listing_rows.extend(rows)
        time.sleep(1.25)
    assert totals == {157}
    assert len(listing_rows) == len({
        row["source_sku"] for row in listing_rows
    }) == 157

    exclusions = []
    relevant = []
    for listing in listing_rows:
        reason = EXCLUDED_SOURCE_NAMES.get(listing["source_product_name"])
        if reason:
            exclusions.append({
                "source_id": SOURCE_ID,
                "source_sku": listing["source_sku"],
                "source_product_name": listing["source_product_name"],
                "source_url": listing["source_url"],
                "exclusion_reason": reason,
            })
            continue
        detail_payload = fetch(listing["source_url"])
        detail = detail_fields(detail_payload)
        assert detail["detail_sku"] == listing["source_sku"]
        assert detail["detail_product_name"] == listing["source_product_name"]
        family = family_for(listing["source_product_name"])
        brand = detail["source_brand"]
        if not brand and "VALVOLINE" in detail["manufacturer"].upper():
            brand = "VALVOLINE"
        if not brand and "MAG 1" in detail["description_text"].upper():
            brand = "MAG 1"
        if not brand and listing["source_product_name"].startswith("MOTUL "):
            brand = "MOTUL"
        if not brand and listing["source_product_name"].startswith("RED N TACKY"):
            brand = "LUCAS OIL"
        if not brand and listing["source_product_name"].startswith("WD-40"):
            brand = "WD-40"
        quality_flags = [
            "official_country_retailer_current_detail_page",
            "source_abbreviated_product_title_retained_verbatim",
            "marketing_description_not_redistributed",
        ]
        if (
            brand == "MOTUL"
            and "MEGUIAR" in detail["manufacturer"].upper()
        ):
            quality_flags.append(
                "source_brand_title_conflicts_with_manufacturer_field"
            )
        relevant.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"ACE-CAYMAN-{listing['source_sku']}",
            "country": "Cayman Islands",
            "source_sku": listing["source_sku"],
            "source_product_name": listing["source_product_name"],
            "manufacturer": detail["manufacturer"],
            "brand": brand,
            "family_code": family,
            "specifications": specifications(
                listing["source_product_name"],
                detail["description_text"],
                family,
            ),
            "unit_of_measure": detail["unit_of_measure"],
            "price_amount": listing["listing_price_amount"],
            "price_currency": listing["listing_price_currency"],
            "listing_availability": listing["listing_availability"],
            "lifecycle_status": (
                "discontinued_current_detail_page"
                if detail["detail_lifecycle"].lower() == "discontinued"
                else "listed_current_catalog"
            ),
            "source_url": listing["source_url"],
            "snapshot_date": str(date.today()),
            "description_sha256": detail["description_sha256"],
            "source_quality_flags": quality_flags,
        })
        time.sleep(1.25)

    relevant.sort(key=lambda row: row["source_sku"])
    exclusions.sort(key=lambda row: row["source_sku"])
    products = product_rows_from_skus(relevant)
    relevant_rendered = render(relevant)
    product_rendered = render(products)
    exclusion_rendered = render(exclusions)
    OUT.write_text(relevant_rendered, encoding="utf-8")
    PRODUCTS.write_text(product_rendered, encoding="utf-8")
    EXCLUSIONS.write_text(exclusion_rendered, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": LISTING_URL.format(offset=0),
        "snapshot_date": str(date.today()),
        "listing_denominator": len(listing_rows),
        "listing_pages": len(OFFSETS),
        "normalized_fluid_skus": len(relevant),
        "product_grade_identities": len(products),
        "package_skus_collapsed": len(relevant) - len(products),
        "excluded_rows": len(exclusions),
        "exclusion_reasons": dict(sorted(Counter(
            row["exclusion_reason"] for row in exclusions
        ).items())),
        "families": dict(sorted(Counter(
            row["family_code"] for row in relevant
        ).items())),
        "lifecycle": dict(sorted(Counter(
            row["lifecycle_status"] for row in relevant
        ).items())),
        "listing_availability": dict(sorted(Counter(
            row["listing_availability"] for row in relevant
        ).items())),
        "priced_skus": sum(
            row["price_amount"] is not None for row in relevant
        ),
        "normalized_output_sha256": hashlib.sha256(
            relevant_rendered.encode("utf-8")
        ).hexdigest(),
        "normalized_products_sha256": hashlib.sha256(
            product_rendered.encode("utf-8")
        ).hexdigest(),
        "exclusions_sha256": hashlib.sha256(
            exclusion_rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "The complete current automotive class was enumerated. Explicit "
            "parts and cleaning aerosols are excluded; source descriptions "
            "are hashed and used only for factual parsing, not redistributed."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
