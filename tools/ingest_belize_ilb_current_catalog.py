#!/usr/bin/env python3
"""Build the current International Lubricants of Belize catalog evidence.

ILB's official WordPress catalog exposes 112 current cards.  Package-only
variants collapse to 77 exact product-label identities.  This country layer
records Belize availability and source evidence; it does not create duplicate
manufacturer identities for the global Chevron portfolio.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AVAILABILITY_OUT = ROOT / "data/belize-ilb-current-availability.jsonl"
REPORT_OUT = ROOT / "data/belize-ilb-current-catalog-report.json"

SNAPSHOT_DATE = "2026-07-24"
SOURCE_ID = "BELIZE_ILB_CURRENT_PRODUCT_CATALOG"
HOME_URL = "https://ilb.bz/"
CATALOG_URL = "https://ilb.bz/shop/"
API_TEMPLATE = (
    "https://ilb.bz/wp-json/wp/v2/product?per_page=100&page={page}&_embed=1"
)
UA = "MFClassifier evidence catalog/1.0"

EXPECTED_CARD_COUNT = 112
EXPECTED_IDENTITY_COUNT = 77
EXPECTED_PAGE_FACTS_SHA256 = (
    "a959b266891a7492fe3c8fc56607fe86c86b8a6b2872939d3f8e66d330c0c552"
)
EXPECTED_IMAGE_FACTS_SHA256 = (
    "1ada8003f9f13d07fd8ae1b3726651bf5567642c4eb30a4d027b91dcbd53bf1f"
)


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def clean_text(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def canonical_label(value):
    value = html.unescape(value).upper().replace("–", "-")
    value = re.sub(r"\([^)]*\)?", " ", value)
    value = re.sub(r"\s+-\s+(?:DRUM|BUCKET)\s*$", "", value)
    value = re.sub(r"\s+(?:DRUM|BUCKET|120 LBS)\s*$", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -")
    value = re.sub(r"^CHV\s+", "CHEVRON ", value)
    value = value.replace("HDISO", "HD ISO")
    value = value.replace("PRODS FULL", "PRO DS FULL")
    for old, new in (
        ("85W140", "85W-140"),
        ("80W90", "80W-90"),
        ("75W90", "75W-90"),
        ("10W30", "10W-30"),
        ("15W40", "15W-40"),
    ):
        value = value.replace(old, new)
    value = value.replace("MULTIFAK GREASE EP 2", "MULTIFAK EP 2")
    return value


def package_hint(value):
    hints = re.findall(r"\(([^)]*)\)", html.unescape(value))
    suffix = re.search(r"\s+-\s+(DRUM|BUCKET)\s*$", value, re.I)
    if suffix:
        hints.append(suffix.group(1))
    if re.search(r"\s+120 LBS\s*$", value, re.I):
        hints.append("120 LBS")
    return [re.sub(r"\s+", " ", hint).strip() for hint in hints if hint.strip()]


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def category(row):
    terms = row.get("_embedded", {}).get("wp:term", [])
    names = [
        clean_text(term.get("name", ""))
        for group in terms
        for term in group
        if term.get("taxonomy") == "product_cat"
    ]
    return names[0] if names else ""


def family_for(label, category_name):
    text = f"{label} {category_name}".upper()
    if "GREASE" in text or "GRS " in text:
        return "G"
    if "GEAR" in text or "MULTIGEAR" in text or "MEROPA" in text or "SUGARTEX" in text:
        return "T"
    if any(token in text for token in ("ATF", "TRANSMISSION", "TORQFORCE", "THF", "POWER STEERING")):
        return "TF"
    if any(token in text for token in ("COOLANT", "ANTIFREEZE", "INHIBITOR", "BRAKE FLUID")):
        return "TF"
    if any(token in text for token in ("HYDRAULIC", "RANDO", "AW-M")):
        return "H"
    if any(token in text for token in ("COMPRESSOR", "CETUS", "CAPELLA")):
        return "C"
    if any(token in text for token in ("MOTOR OIL", "ENGINE OIL", "DELO 400", "URSA", "MCO 4T", "2-CYCLE")):
        return "M"
    return "I"


def technical(label, family):
    values = {
        "sae_engine": "",
        "sae_gear": "",
        "iso_vg": "",
        "nlgi": "",
        "source_grade": "",
        "api": [],
        "api_gl": [],
        "acea": [],
        "ilsac": [],
        "jaso": [],
        "dot": "",
        "coolant_class": "",
        "performance": [],
    }
    sae_pattern = r"\b(\d{1,2}W-\d{2}|\d{1,2}W|\d{2})\b"
    if family in {"M", "T"}:
        sae = re.search(rf"\b(?:SAE\s+)?{sae_pattern[2:]}", label)
    elif family == "TF":
        sae = re.search(rf"\bSAE\s+{sae_pattern[2:]}", label)
    else:
        sae = None
    if sae:
        if family == "T":
            values["sae_gear"] = sae.group(1)
        elif family in {"M", "TF"} and "ATF" not in label:
            values["sae_engine"] = sae.group(1)
    iso_vg = re.search(r"\bISO\s+(\d{2,4})\b", label)
    if iso_vg:
        values["iso_vg"] = iso_vg.group(1)
    nlgi = re.search(r"\bNLGI\s+([0-6](?:/[0-6])?)\b", label)
    if nlgi:
        values["nlgi"] = nlgi.group(1)
    api_gl = re.findall(r"\bGL-[1-6]\b", label)
    values["api_gl"] = sorted(set(api_gl))
    api = re.findall(
        r"\b(?:SP|SN(?:\s+PLUS)?|SM|SL|SJ|CK-4|CJ-4|CI-4(?:\s+PLUS)?|CH-4|CF-4|CF-2|CF)\b",
        label,
    )
    values["api"] = sorted(set(api))
    dot = re.search(r"\bDOT\s+([3-5](?:\.1)?)\b", label)
    if dot:
        values["dot"] = f"DOT {dot.group(1)}"
    if "50/50" in label or "PREMIXED" in label:
        values["coolant_class"] = "50/50 premix"
    if "TC-W3" in label:
        values["performance"].append("NMMA TC-W3 (source label)")
    return values


def main():
    raw_pages = [get(API_TEMPLATE.format(page=page)) for page in (1, 2)]
    rows = [row for payload in raw_pages for row in json.loads(payload)]
    if len(rows) != EXPECTED_CARD_COUNT:
        raise RuntimeError(f"ILB card denominator changed: {len(rows)}")

    page_facts = []
    grouped = defaultdict(list)
    image_payloads = {}
    for row in rows:
        media = row.get("_embedded", {}).get("wp:featuredmedia", [])
        image_url = media[0].get("source_url", "") if media else ""
        image_sha = ""
        image_bytes = 0
        if image_url:
            payload = get(image_url)
            image_sha = sha256(payload)
            image_bytes = len(payload)
            image_payloads.setdefault(
                image_sha,
                {"sha256": image_sha, "bytes": image_bytes, "urls": []},
            )["urls"].append(image_url)
        title = clean_text(row["title"]["rendered"])
        fact = {
            "id": row["id"],
            "title": title,
            "canonical_label": canonical_label(title),
            "url": row["link"],
            "category": category(row),
            "modified_gmt": row["modified_gmt"],
            "image_url": image_url,
            "image_sha256": image_sha,
            "image_bytes": image_bytes,
        }
        page_facts.append(fact)
        grouped[fact["canonical_label"]].append(fact)

    page_facts.sort(key=lambda fact: fact["id"])
    page_hash = sha256(
        json.dumps(page_facts, sort_keys=True, ensure_ascii=False).encode()
    )
    image_facts = sorted(image_payloads.values(), key=lambda fact: fact["sha256"])
    for fact in image_facts:
        fact["urls"].sort()
    image_hash = sha256(
        json.dumps(image_facts, sort_keys=True, ensure_ascii=False).encode()
    )
    if EXPECTED_PAGE_FACTS_SHA256 and page_hash != EXPECTED_PAGE_FACTS_SHA256:
        raise RuntimeError(f"ILB page facts changed: {page_hash}")
    if EXPECTED_IMAGE_FACTS_SHA256 and image_hash != EXPECTED_IMAGE_FACTS_SHA256:
        raise RuntimeError(f"ILB image facts changed: {image_hash}")

    if len(grouped) != EXPECTED_IDENTITY_COUNT:
        raise RuntimeError(f"ILB identity denominator changed: {len(grouped)}")

    output = []
    for index, (label, cards) in enumerate(sorted(grouped.items()), 1):
        brand = "REVOLUB" if label.startswith("REVOLUB ") else "CHEVRON"
        family = family_for(label, cards[0]["category"])
        output.append({
            "source_record_id": f"ILB-BZ-{index:03d}",
            "source_id": SOURCE_ID,
            "snapshot_date": SNAPSHOT_DATE,
            "source_url": CATALOG_URL,
            "seller": "International Lubricants of Belize",
            "market": "Belize",
            "brand": brand,
            "product_name": label,
            "family_code": family,
            "technical": technical(label, family),
            "packages": sorted({
                hint
                for card in cards
                for hint in package_hint(card["title"])
            }),
            "source_card_ids": sorted(card["id"] for card in cards),
            "source_card_urls": sorted(card["url"] for card in cards),
            "source_image_urls": sorted({
                card["image_url"] for card in cards if card["image_url"]
            }),
            "source_image_sha256": sorted({
                card["image_sha256"] for card in cards if card["image_sha256"]
            }),
            "product_identity_hint": normalize(f"{brand}-{label}-{family}"),
            "scope_status": "global_brand_belize_availability",
            "lifecycle_status": "listed_in_current_official_distributor_catalog",
            "source_quality_flags": [
                "complete_current_wordpress_product_catalog",
                "package_only_cards_collapsed",
                "product_image_payload_sha256_verified",
                "technical_values_limited_to_explicit_product_label",
                "manufacturer_identity_pending_or_linked_in_global_brand_pass",
            ],
        })

    normalized = "\n".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) for row in output
    ) + "\n"
    output_hash = sha256(normalized.encode())
    AVAILABILITY_OUT.write_text(normalized, encoding="utf-8")

    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "source_url": HOME_URL,
        "catalog_url": CATALOG_URL,
        "api_urls": [API_TEMPLATE.format(page=page) for page in (1, 2)],
        "current_product_cards": len(rows),
        "normalized_product_label_identities": len(output),
        "package_only_card_duplicates_collapsed": len(rows) - len(output),
        "brands": dict(sorted(Counter(row["brand"] for row in output).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in output).items())),
        "categories": dict(sorted(Counter(fact["category"] for fact in page_facts).items())),
        "product_images_referenced": sum(bool(fact["image_url"]) for fact in page_facts),
        "unique_product_image_payloads": len(image_facts),
        "product_image_bytes": sum(fact["bytes"] for fact in image_facts),
        "page_facts_sha256": page_hash,
        "image_facts_sha256": image_hash,
        "normalized_output_sha256": output_hash,
        "quality_note": (
            "Complete current ILB distributor catalog. Package variants are "
            "collapsed only when their normalized printed product labels match. "
            "Chevron and Revolub rows are Belize availability evidence, not new "
            "manufacturer master identities; specifications are limited to "
            "values printed in product titles."
        ),
    }
    REPORT_OUT.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
