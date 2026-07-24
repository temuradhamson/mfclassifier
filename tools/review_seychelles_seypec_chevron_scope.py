#!/usr/bin/env python3
"""Audit SEYPEC's current Chevron lubricant presence without inventing SKUs."""

from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "seychelles-seypec-chevron-scope-review.json"
BASE = "https://www.seypec.com"
ROBOTS_URL = f"{BASE}/robots.txt"
LUBRICANTS_URL = f"{BASE}/services/chevron-lubricants"
STATIONS_URL = f"{BASE}/services/service-stations"
TERMS_URL = f"{BASE}/terms-conditions"
SOURCE_ID = "SEYCHELLES_SEYPEC_CHEVRON_MARKET_PRESENCE_REVIEW"
SNAPSHOT_DATE = "2026-07-24"


def fetch(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "mfclassifier-source-review/1.0"},
    )
    with urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"{url}: HTTP {response.status}")
        return response.read()


def clean(fragment: str) -> str:
    return re.sub(
        r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))
    ).strip()


def first(pattern: str, html: str) -> str:
    match = re.search(pattern, html, flags=re.I | re.S)
    if not match:
        raise RuntimeError("SEYPEC source structure changed: " + pattern)
    return clean(match.group(1))


def main() -> None:
    robots = fetch(ROBOTS_URL)
    lubricant_page = fetch(LUBRICANTS_URL)
    stations_page = fetch(STATIONS_URL)
    terms_page = fetch(TERMS_URL)
    lubricant_html = lubricant_page.decode("utf-8")
    stations_html = stations_page.decode("utf-8")
    terms_html = terms_page.decode("utf-8")

    title = first(r'<h1[^>]*>(.*?)</h1>', lubricant_html)
    lubricant_body = first(
        r'field--name-body.*?field--item">(.*?)</div>\s*</div>',
        lubricant_html,
    )
    station_summary = first(
        r'<span class="header-summary">(.*?)</span>', stations_html
    )
    station_body = first(
        r'field--name-body.*?field--item">(.*?)</div>\s*</div>',
        stations_html,
    )
    station_names = [
        clean(value)
        for value in re.findall(
            r'<h4[^>]*>(.*?)</h4>', stations_html, flags=re.I | re.S
        )
    ]
    terms_body = first(
        r'field--name-body.*?field--item">(.*?)</div>\s*</div>',
        terms_html,
    )

    required_lubricant_facts = [
        "A variety of lubricants are available both from the SEYPEC HQ",
        "hydraulic equipment, turbines, compressors",
        "electrical generators, pumps, marine engines",
        "type, brand and grade of lubricants that you may require",
    ]
    if title != "Chevron Lubricants" or not all(
        value in lubricant_body for value in required_lubricant_facts
    ):
        raise RuntimeError("SEYPEC Chevron market-presence facts changed")
    if "Chevron Lubricants" not in station_body:
        raise RuntimeError("SEYPEC station lubricant availability disappeared")
    if len(station_names) != 11 or len(set(station_names)) != 11:
        raise RuntimeError(
            f"SEYPEC station-card denominator changed: {len(station_names)}"
        )
    if not station_summary.startswith("Ten service stations"):
        raise RuntimeError("SEYPEC station summary denominator changed")
    if "SEYPEC has 8 service stations" not in station_body.replace("\xa0", " "):
        raise RuntimeError("SEYPEC island station-count text changed")
    if "Reproduction of any of the materials on this website is prohibited" not in terms_body:
        raise RuntimeError("SEYPEC reproduction restriction changed")

    image_path = first(
        r'<img src="([^"]*Delo%20Family%20Shot%20NA%202016\.png)"',
        lubricant_html,
    )
    image_url = urljoin(BASE, image_path)
    image_payload = fetch(image_url)
    facts = {
        "market_presence": {
            "brand": "Chevron",
            "market": "Seychelles",
            "availability_channels": [
                "SEYPEC headquarters",
                "SEYPEC service-station retail outlets",
            ],
            "applications_source_reported": [
                "automotive",
                "hydraulic equipment",
                "turbines",
                "compressors",
                "agricultural equipment",
                "construction equipment",
                "electrical generators",
                "pumps",
                "marine engines",
            ],
        },
        "explicit_local_product_series": 0,
        "explicit_local_product_grade_rows": 0,
        "explicit_local_package_skus": 0,
        "current_local_price_rows": 0,
        "offers_created": 0,
        "listed_service_station_cards": station_names,
        "station_count_source_conflict": {
            "header_summary": station_summary,
            "body_island_arithmetic": "8 Mahe + 2 Praslin + 1 La Digue = 11",
            "listed_station_cards": len(station_names),
        },
        "illustrative_image": {
            "url": image_url,
            "filename_scope": "Delo Family Shot NA 2016",
            "sha256": hashlib.sha256(image_payload).hexdigest(),
            "used_as_local_sku_evidence": False,
        },
    }
    report = {
        "schema_version": 1,
        "status": "current_brand_market_presence_confirmed_no_local_sku_denominator",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "owner": "Seychelles Petroleum Company Limited",
        "market": "Seychelles",
        "source_urls": {
            "robots": ROBOTS_URL,
            "lubricants": LUBRICANTS_URL,
            "service_stations": STATIONS_URL,
            "terms": TERMS_URL,
        },
        "source_sha256": {
            "robots": hashlib.sha256(robots).hexdigest(),
            "lubricants": hashlib.sha256(lubricant_page).hexdigest(),
            "service_stations": hashlib.sha256(stations_page).hexdigest(),
            "terms": hashlib.sha256(terms_page).hexdigest(),
        },
        **facts,
        "facts_sha256": hashlib.sha256(
            json.dumps(
                facts,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "publication_status": (
            "count_and_market_presence_evidence_only_permission_required"
        ),
        "scope_limit": (
            "SEYPEC confirms current Chevron lubricant availability and broad "
            "applications, but directs customers to contact it for type, "
            "brand and grade. The embedded 2016 North America Delo family "
            "image is illustrative and is not a Seychelles SKU denominator."
        ),
    }
    OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "market_presence_observations": 1,
        "explicit_local_product_grade_rows": 0,
        "listed_service_station_cards": len(station_names),
        "facts_sha256": report["facts_sha256"],
    }))


if __name__ == "__main__":
    main()
