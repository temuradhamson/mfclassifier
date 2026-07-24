#!/usr/bin/env python3
"""Discover the complete public Chevron Lubricants US product-page denominator."""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.chevronlubricants.com"
INDEX_URL = f"{BASE}/en_us/home/products/by_brand.html"
LANDING_PATHS = {
    "/en_us/home/products/by_brand.html",
    "/en_us/home/products/equipment_type.html",
    "/en_us/home/products/equipmenttype.html",
    "/en_us/home/products/product_category.html",
}
OUTPUT = ROOT / "data" / "chevron-us-complete-product-discovery.jsonl"
REPORT = ROOT / "data" / "chevron-us-complete-product-discovery-report.json"
PRODUCT_PATH_RE = re.compile(r"/en_us/home/products/[^/]+\.html$")
TEchron_PATHS = {
    "/en_us/home/products/techron-complete-fuel-system-cleaner.html",
    "/en_us/home/products/techron-diesel.html",
    "/en_us/home/products/techron-fuel-injector-cleaner.html",
    "/en_us/home/products/techron-high-mileage-fuel-system-cleaner.html",
}


def fetch(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "mfclassifier-source-discovery/1.0"},
    )
    with urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"{url}: HTTP {response.status}")
        return response.read()


def clean_html(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        unescape(re.sub(r"<[^>]+>", " ", value)),
    ).strip()


def first(pattern: str, html: str) -> str:
    match = re.search(pattern, html, flags=re.DOTALL | re.IGNORECASE)
    return clean_html(match.group(1)) if match else ""


def discover_one(path: str) -> dict:
    url = urljoin(BASE, path)
    payload = fetch(url)
    html = payload.decode("utf-8")
    titles = {
        clean_html(value)
        for value in re.findall(
            r'<div class="title h4"><h1>(.*?)</h1>',
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
    }
    categories = {
        clean_html(value)
        for value in re.findall(
            r'<div class="eyebrow">(.*?)</div>',
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
    }
    if len(titles) != 1 or len(categories) != 1:
        raise RuntimeError(
            f"{path}: expected one product title/category, "
            f"got {titles!r}/{categories!r}"
        )
    document_urls = sorted({
        unescape(value)
        for value in re.findall(
            r'href="(https://cglapps\.chevron\.com/[^"]+'
            r'(?:PDSDetailPage|SDSDetailPage)\.aspx\?[^"]+)"',
            html,
            flags=re.IGNORECASE,
        )
    })
    pds_urls = [
        url for url in document_urls if "pdsdetailpage" in url.casefold()
        and "sdsdetailpage" not in url.casefold()
    ]
    sds_urls = [
        url for url in document_urls if "sdsdetailpage" in url.casefold()
    ]
    title = next(iter(titles))
    category = next(iter(categories))
    return {
        "source_record_id": (
            "CHEVRON-US-PAGE-"
            + hashlib.sha256(path.encode()).hexdigest()[:16]
        ),
        "source_url": url,
        "source_path": path,
        "source_page_sha256": hashlib.sha256(payload).hexdigest(),
        "source_page_title": first(
            r'<meta name="pageTitle" content="([^"]*)"', html
        ),
        "product_name": title,
        "source_category": category,
        "pds_urls": pds_urls,
        "sds_urls": sds_urls,
        "document_urls": document_urls,
        "excluded_from_lubricant_scope": path in TEchron_PATHS,
        "exclusion_reason": (
            "fuel_system_cleaner_not_lubricant_or_technical_fluid"
            if path in TEchron_PATHS else ""
        ),
        "snapshot_date": "2026-07-24",
        "source_id": "CHEVRON_US_COMPLETE_LIVE_PRODUCT_PAGE_DISCOVERY",
    }


def main() -> None:
    index_payload = fetch(INDEX_URL)
    index_html = index_payload.decode("utf-8")
    paths = sorted({
        unescape(value)
        for value in re.findall(r'href=["\']([^"\']+)["\']', index_html)
        if PRODUCT_PATH_RE.fullmatch(unescape(value))
        and unescape(value) not in LANDING_PATHS
    })
    if len(paths) != 166:
        raise RuntimeError(
            f"Chevron complete by-brand denominator changed: {len(paths)}"
        )
    if not TEchron_PATHS.issubset(paths):
        raise RuntimeError("Chevron Techron exclusion paths disappeared")
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(discover_one, paths))
    rows.sort(key=lambda row: row["source_path"])
    OUTPUT.write_text(
        "".join(
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    category_counts: dict[str, int] = {}
    for row in rows:
        category_counts[row["source_category"]] = (
            category_counts.get(row["source_category"], 0) + 1
        )
    report = {
        "schema_version": 1,
        "status": "complete_live_product_page_denominator_discovered",
        "snapshot_date": "2026-07-24",
        "source_id": "CHEVRON_US_COMPLETE_LIVE_PRODUCT_PAGE_DISCOVERY",
        "index_url": INDEX_URL,
        "index_sha256": hashlib.sha256(index_payload).hexdigest(),
        "product_page_urls": len(rows),
        "in_scope_candidate_pages": sum(
            not row["excluded_from_lubricant_scope"] for row in rows
        ),
        "excluded_fuel_system_cleaner_pages": sum(
            row["excluded_from_lubricant_scope"] for row in rows
        ),
        "pages_with_pds": sum(bool(row["pds_urls"]) for row in rows),
        "pages_with_sds": sum(bool(row["sds_urls"]) for row in rows),
        "unique_document_urls": len({
            url for row in rows for url in row["document_urls"]
        }),
        "source_category_page_counts": dict(sorted(category_counts.items())),
        "normalized_output_sha256": hashlib.sha256(
            OUTPUT.read_bytes()
        ).hexdigest(),
        "publication_scope": (
            "Non-expressive product title, category, document URL and "
            "evidence hashes only; no descriptions, artwork or documents "
            "are redistributed."
        ),
        "normalization_status": (
            "Discovery complete; product-grade expansion, technical parsing "
            "and strict cross-source matching remain pending."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "product_pages": len(rows),
        "in_scope": report["in_scope_candidate_pages"],
        "excluded": report["excluded_fuel_system_cleaner_pages"],
        "categories": len(category_counts),
        "pages_with_pds": report["pages_with_pds"],
        "sha256": report["normalized_output_sha256"],
    }))


if __name__ == "__main__":
    main()
