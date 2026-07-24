#!/usr/bin/env python3
"""Collect the complete current Rymax Lubricants Belize product catalog."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARD_OUT = ROOT / "data/belize-rymax-current-product-cards.jsonl"
REPORT_OUT = ROOT / "data/belize-rymax-current-catalog-report.json"

SNAPSHOT_DATE = "2026-07-24"
SOURCE_ID = "BELIZE_RYMAX_CURRENT_PRODUCT_CATALOG"
CATALOG_URL = "https://rymax-lubricants.bz/products"
UA = "MFClassifier evidence catalog/1.0"
EXPECTED_LISTING_OCCURRENCES = 339
EXPECTED_UNIQUE_PRODUCT_URLS = 325
EXPECTED_NORMALIZED_CARDS_SHA256 = (
    "8546ac306eb1d988dacb63a635f3b37cddbc4add8929bedf1627c881f5ec641d"
)


def get(url, *, ajax=False):
    headers = {"User-Agent": UA}
    if ajax:
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def text(value):
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def first(pattern, source):
    match = re.search(pattern, source, flags=re.I | re.S)
    return text(match.group(1)) if match else ""


def section_values(source, heading):
    match = re.search(
        rf"<h5[^>]*>\s*{re.escape(heading)}\s*</h5>"
        r"(.*?)(?=<div class=\"lg:mt-10 mt-8\"|"
        r"<div class=\"flex flex-wrap gap-4|</div>\s*</div>\s*</div>)",
        source,
        flags=re.I | re.S,
    )
    if not match:
        return []
    return [
        value
        for value in (text(raw) for raw in re.findall(
            r"<small[^>]*>(.*?)</small>", match.group(1), flags=re.I | re.S
        ))
        if value
    ]


def listing_urls():
    occurrences = []
    listing_hashes = []
    for page in range(1, 23):
        url = CATALOG_URL if page == 1 else f"{CATALOG_URL}/p{page}"
        payload = get(url, ajax=page > 1)
        listing_hashes.append({
            "page": page,
            "url": url,
            "sha256": sha256(payload),
            "bytes": len(payload),
        })
        source = payload.decode("utf-8", "replace")
        if page == 1:
            source = source.split('x-ref="entries"', 1)[1]
            source = source.split('x-show="loadMore"', 1)[0]
        occurrences.extend(re.findall(
            r'href="(https://rymax-lubricants\.bz/products/[^"?#]+)"',
            source,
        ))
    if len(occurrences) != EXPECTED_LISTING_OCCURRENCES:
        raise RuntimeError(f"Rymax listing denominator changed: {len(occurrences)}")
    urls = sorted(set(occurrences))
    if len(urls) != EXPECTED_UNIQUE_PRODUCT_URLS:
        raise RuntimeError(f"Rymax unique URL denominator changed: {len(urls)}")
    return occurrences, urls, listing_hashes


def parse_card(url):
    payload = get(url)
    source = payload.decode("utf-8", "replace")
    title = first(r"<h1[^>]*>(.*?)</h1>", source)
    subtitle = first(
        r"<h1[^>]*>.*?</h1>\s*<p[^>]*>(.*?)</p>",
        source,
    )
    description = first(
        r">\s*Description\s*</h4>\s*<div[^>]*>(.*?)</div>",
        source,
    )
    image_match = re.search(
        r'<img[^>]+class="w-full object-cover"[^>]+src="([^"]+)"',
        source,
        flags=re.I | re.S,
    )
    documents = sorted(set(re.findall(
        r'href="([^"]+\.pdf(?:\?[^"]*)?)"',
        source,
        flags=re.I,
    )))
    if not title:
        raise RuntimeError(f"Rymax product title missing: {url}")
    return {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "source_url": url,
        "brand": "RYMAX",
        "product_name": title,
        "product_subtitle": subtitle,
        "specifications_source_reported": section_values(source, "Specifications"),
        "segments": section_values(source, "Segments"),
        "viscosity_grades": section_values(source, "Viscosity Grades"),
        "description_factual_excerpt": description,
        "product_image_url": html.unescape(image_match.group(1)) if image_match else "",
        "document_urls": [html.unescape(value) for value in documents],
        "page_sha256": sha256(payload),
        "page_bytes": len(payload),
    }


def main():
    occurrences, urls, listing_hashes = listing_urls()
    with ThreadPoolExecutor(max_workers=6) as pool:
        cards = list(pool.map(parse_card, urls))
    cards.sort(key=lambda row: row["source_url"])
    normalized = "\n".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) for row in cards
    ) + "\n"
    normalized_hash = sha256(normalized.encode())
    if normalized_hash != EXPECTED_NORMALIZED_CARDS_SHA256:
        raise RuntimeError(f"Rymax normalized card facts changed: {normalized_hash}")
    CARD_OUT.write_text(normalized, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "catalog_url": CATALOG_URL,
        "listing_pages": 22,
        "listing_occurrences": len(occurrences),
        "unique_product_urls": len(cards),
        "highlight_repeat_occurrences": len(occurrences) - len(cards),
        "cards_with_specifications": sum(bool(row["specifications_source_reported"]) for row in cards),
        "cards_with_segments": sum(bool(row["segments"]) for row in cards),
        "cards_with_viscosity_grades": sum(bool(row["viscosity_grades"]) for row in cards),
        "cards_with_images": sum(bool(row["product_image_url"]) for row in cards),
        "document_references": sum(len(row["document_urls"]) for row in cards),
        "unique_document_urls": len({url for row in cards for url in row["document_urls"]}),
        "listing_page_facts": listing_hashes,
        "normalized_cards_sha256": normalized_hash,
    }
    REPORT_OUT.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
