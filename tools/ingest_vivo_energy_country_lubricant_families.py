#!/usr/bin/env python3
"""Normalize named lubricant families from all Vivo Energy country pages."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "vivo-energy-country-lubricant-families.jsonl"
REPORT = ROOT / "data" / "vivo-energy-country-lubricant-families-report.json"
CACHE = ROOT / ".cache" / "vivo-country-pages"
SOURCE_ID = "VIVO_ENERGY_CURRENT_COUNTRY_LUBRICANT_FAMILIES"
BASE = "https://www.vivoenergy.com"
INDEX_URL = f"{BASE}/en/where-we-operate"
ROBOTS_URL = f"{BASE}/robots.txt"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "mfclassifier-source-ingest/1.0"

FAMILY_MAP = {
    "Shell Advance": "M",
    "Shell Longlife Coolant": "TF",
    "Shell Helix": "M",
    "Shell Rimula": "M",
    "Shell Gadus": "G",
    "Shell Spirax": "T",
    "Shell Tellus": "H",
}

EXPECTED_SHELL_MARKET_SLUGS = {
    "botswana", "burkina-faso", "cape-verde", "cote-divoire", "gabon",
    "ghana", "guinea", "kenya", "madagascar", "malawi", "mali",
    "mauritius", "morocco", "mozambique", "namibia", "rwanda",
    "senegal", "tanzania", "tunisia", "uganda", "zambia", "zimbabwe",
}

MARKET_NAMES = {
    "cape-verde": "Cabo Verde",
    "cote-divoire": "Côte d'Ivoire",
    "democratic-republic-of-congo": "Democratic Republic of the Congo",
    "reunion": "Réunion",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def clean(fragment: str) -> str:
    return re.sub(
        r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))
    ).strip()


def section_items(page: str, heading: str) -> list[str]:
    match = re.search(
        rf'id="{re.escape(heading)}-content".*?<ul>(.*?)</ul>',
        page,
        flags=re.I | re.S,
    )
    return (
        [clean(value) for value in re.findall(
            r"<li>(.*?)</li>", match.group(1), re.I | re.S
        )]
        if match else []
    )


def source_links(index: str) -> list[dict]:
    values = []
    seen = set()
    for href, label in re.findall(
        r'<a[^>]+href="([^"]*where-we-operate/[^"]+)"[^>]*>(.*?)</a>',
        index,
        flags=re.I | re.S,
    ):
        if href in seen:
            continue
        seen.add(href)
        slug = href.rstrip("/").rsplit("/", 1)[-1]
        raw_label = clean(label).removesuffix(" Open link menu")
        values.append({
            "href": href,
            "slug": slug,
            "market": MARKET_NAMES.get(slug, raw_label),
            "url": urllib.parse.urljoin(BASE, href),
        })
    return values


def fetch_country(source: dict) -> dict:
    payload = fetch(source["url"])
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{source['slug']}.html").write_bytes(payload)
    page = payload.decode("utf-8")
    return {
        **source,
        "payload": payload,
        "retail": section_items(page, "Retail lubricants"),
        "commercial": section_items(page, "Lubes"),
    }


def main() -> None:
    index_payload = fetch(INDEX_URL)
    robots = fetch(ROBOTS_URL)
    index = index_payload.decode("utf-8")
    robots_text = robots.decode("utf-8")
    links = source_links(index)
    if len(links) != 29 or len({row["slug"] for row in links}) != 29:
        raise RuntimeError(f"Vivo country denominator changed: {len(links)}")
    if "Disallow: /search/" not in robots_text:
        raise RuntimeError("Vivo robots policy changed")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        countries = list(executor.map(fetch_country, links))

    shell_markets = {
        country["slug"]
        for country in countries
        if any(
            item.startswith("Shell ")
            for item in country["retail"] + country["commercial"]
        )
    }
    if shell_markets != EXPECTED_SHELL_MARKET_SLUGS:
        raise RuntimeError(
            "Vivo named Shell-market denominator changed: "
            + repr({
                "missing": sorted(EXPECTED_SHELL_MARKET_SLUGS - shell_markets),
                "new": sorted(shell_markets - EXPECTED_SHELL_MARKET_SLUGS),
            })
        )

    records = []
    reviewed_zero_named_family_markets = []
    source_label_occurrences = 0
    for country in countries:
        source_label_occurrences += len(
            country["retail"] + country["commercial"]
        )
        if country["slug"] not in shell_markets:
            reviewed_zero_named_family_markets.append(country["market"])
            continue
        retail = country["retail"]
        commercial = country["commercial"]
        expected_retail = {
            "Shell Advance Mortorcycle motor oil",
            "Shell Longlife Coolant",
            "Shell Helix Passenger car motor oil",
            "Shell Rimula Heavy duty motor oil",
            "Shell Gadus",
        }
        if set(retail) != expected_retail:
            raise RuntimeError(
                f"{country['market']}: retail family list changed: {retail!r}"
            )
        labels = {
            "Shell Advance": [retail[0]],
            "Shell Longlife Coolant": [
                value for value in retail + commercial
                if value == "Shell Longlife Coolant"
            ],
            "Shell Helix": [
                value for value in retail
                if value.startswith("Shell Helix ")
            ],
            "Shell Rimula": [
                value for value in retail + commercial
                if value.startswith("Shell Rimula")
            ],
            "Shell Gadus": [
                value for value in retail + commercial
                if value == "Shell Gadus"
            ],
            "Shell Spirax": [
                value for value in commercial
                if value == "Shell Spirax"
            ],
            "Shell Tellus": [
                value for value in commercial
                if value == "Shell Tellus"
            ],
        }
        if any(not values for values in labels.values()):
            raise RuntimeError(
                f"{country['market']}: incomplete named family set: {labels!r}"
            )
        for name, family in FAMILY_MAP.items():
            channels = []
            if any(value in retail for value in labels[name]):
                channels.append("retail")
            if any(value in commercial for value in labels[name]):
                channels.append("commercial")
            facts = {
                "market": country["market"],
                "product_family": name,
                "family_code": family,
                "source_labels": labels[name],
                "availability_channels": channels,
            }
            records.append({
                "source_id": SOURCE_ID,
                "source_record_id": (
                    f"VIVO-{country['slug'].upper()}-"
                    f"{list(FAMILY_MAP).index(name) + 1:02d}"
                ),
                "source_url": country["url"],
                "source_page_sha256": hashlib.sha256(
                    country["payload"]
                ).hexdigest(),
                "snapshot_date": SNAPSHOT_DATE,
                "market": country["market"],
                "manufacturer": "Shell",
                "brand": "Shell",
                "local_marketer": f"Vivo Energy {country['market']}",
                "product_name": name,
                "family_code": family,
                "lifecycle_status": (
                    "listed_on_current_official_country_page"
                ),
                "evidence_status": (
                    "official_country_marketer_current_named_product_family"
                ),
                "source_labels": labels[name],
                "availability_channels": channels,
                "technical": {
                    "sae_engine": "", "sae_gear": "", "iso_vg": "",
                    "nlgi": "", "api": [], "api_gl": [], "acea": [],
                    "ilsac": [], "jaso": [],
                },
                "source_facts_sha256": hashlib.sha256(
                    json.dumps(
                        facts,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest(),
                "source_quality_flags": [
                    "family_level_country_availability_not_product_grade_or_sku",
                    *(
                        ["source_advance_motorcycle_typo_retained_in_source_label"]
                        if name == "Shell Advance" else []
                    ),
                ],
            })

    if len(records) != 154:
        raise RuntimeError(f"Expected 154 country-family rows, found {len(records)}")
    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "complete_current_vivo_country_page_sweep_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "owner": "Vivo Energy",
        "index_url": INDEX_URL,
        "robots_url": ROBOTS_URL,
        "index_sha256": hashlib.sha256(index_payload).hexdigest(),
        "robots_sha256": hashlib.sha256(robots).hexdigest(),
        "country_pages_reviewed": len(countries),
        "countries_with_named_shell_families": len(shell_markets),
        "reviewed_zero_named_family_country_pages": len(
            reviewed_zero_named_family_markets
        ),
        "reviewed_zero_named_family_markets": sorted(
            reviewed_zero_named_family_markets
        ),
        "country_family_rows": len(records),
        "unique_named_families": len(FAMILY_MAP),
        "source_label_occurrences_all_country_pages": (
            source_label_occurrences
        ),
        "families": dict(sorted(Counter(
            row["family_code"] for row in records
        ).items())),
        "market_rows": dict(sorted(Counter(
            row["market"] for row in records
        ).items())),
        "country_page_sha256": {
            country["market"]: hashlib.sha256(
                country["payload"]
            ).hexdigest()
            for country in countries
        },
        "offers_created": 0,
        "normalized_output_sha256": hashlib.sha256(
            output_text.encode()
        ).hexdigest(),
        "grain_note": (
            "One row per country and unique named Shell product family after "
            "retail/commercial duplicates are collapsed. Generic Engen text on "
            "Réunion and pages without named family lists create no products."
        ),
        "scope_note": (
            "These are country-market family observations, not grade, package, "
            "price, stock or complete manufacturer-product denominators."
        ),
        "publication_scope": (
            "Attributed factual country-market family names, channels, source "
            "labels, URLs and hashes only; images and page prose are excluded."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
