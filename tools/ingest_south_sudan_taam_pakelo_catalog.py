#!/usr/bin/env python3
"""Normalize Taam Petroleum South Sudan's complete Pakelo category catalog."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/south-sudan-taam-pakelo-products.jsonl"
REPORT = ROOT / "data/south-sudan-taam-pakelo-report.json"
SOURCE_ID = "SOUTH_SUDAN_TAAM_PAKELO_COMPLETE_CATEGORY_CATALOG"
BASE_URL = "https://www.taampetroleum.com/"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"
CATEGORY_PAGES = [
    ("Passenger cars and Vans", "cars-and-vans.php"),
    ("Truck and Bus", "truck-bus.php"),
    ("Earth moving machinery", "earth-moving-machinery.php"),
    ("Motorbikes 2 stroke / 4 stroke", "motorbikes-2-stroke-4-stroke.php"),
    ("Racing", "racing.php"),
    ("Marine", "marine.php"),
    ("Industry", "industry.php"),
    ("Food Grade", "food-grade.php"),
    ("Biodegradable", "biodegradable.php"),
    ("Sprays and Additives", "additives-and-spray.php"),
]
EXACT_ZF_MATCHES = {
    "0014.18": "ZF002007",
    "0166.16": "ZF012042",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


class ProductParser(HTMLParser):
    FIELDS = {"pr_prodotti", "pr_sae", "pr_codice", "pr_text_descr"}

    def __init__(self) -> None:
        super().__init__()
        self.capture = ""
        self.buffer: list[str] = []
        self.current: dict[str, str] = {}
        self.rows: list[dict[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        class_name = dict(attrs).get("class", "")
        if class_name in self.FIELDS:
            self.capture = class_name
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture and tag in {"div", "font"}:
            value = re.sub(
                r"\s+", " ", html.unescape("".join(self.buffer))
            ).strip()
            self.current[self.capture] = value
            if self.capture == "pr_text_descr":
                self.rows.append(self.current)
                self.current = {}
            self.capture = ""


def family_for(name: str, description: str, category: str) -> str:
    joined = f"{name} {description} {category}".casefold()
    if any(token in joined for token in (
        "antifreeze", "coolant", "brake fluid", "lhm fluid",
        "non tox freeze",
    )):
        return "TF"
    if any(token in joined for token in ("grease", "grasso", "vaselba")):
        return "G"
    if any(token in joined for token in (
        "spray", "chain", "white oil", "food grade",
        "sprays and additives",
    )):
        return "S"
    if any(token in joined for token in (
        "compressor", "vacuum pump",
    )):
        return "C"
    if any(token in joined for token in (
        "hydraulic", "suspension fluid", "fork and suspension",
        "raisol oil", "safety fluid",
    )):
        if any(token in joined for token in (
            "stou", "utto", "multiservice 4", "universal diesel fk-2",
        )):
            return "T"
        return "H"
    if any(token in joined for token in (
        "transmission", "differential", "final drives", "wet brakes",
        "stou", "utto",
    )):
        return "T"
    if any(token in joined for token in (
        "worm gear", "reduction unit", "gearsint", "allsint ep",
        "erolube ep",
    )):
        return "I"
    if any(token in joined for token in (
        "engine", "2t", "motorbike", "racing krypton", "golden diesel",
        "goldenstar", "krypton", "multisint",
    )):
        return "M"
    return "S"


def parsed_grade(source_grade: str) -> dict[str, str]:
    grade = source_grade.strip()
    if not grade:
        return {}
    if grade.upper().startswith("SAE "):
        return {
            "sae_engine": grade[4:].upper().replace("/", "-").replace(" ", "")
        }
    if grade.upper().startswith("ISO "):
        return {"iso_vg": grade[4:].strip()}
    if grade.upper().startswith("NLGI "):
        return {"nlgi": grade[5:].strip()}
    return {"source_grade": grade}


def main() -> None:
    occurrences: list[dict] = []
    page_fact_hashes = {}
    page_counts = {}
    for category, filename in CATEGORY_PAGES:
        url = BASE_URL + filename
        payload = fetch(url)
        parser = ProductParser()
        parser.feed(payload.decode(errors="replace"))
        if not parser.rows:
            raise RuntimeError(f"Taam category page empty: {url}")
        page_counts[category] = len(parser.rows)
        normalized_page = []
        for row in parser.rows:
            required = {"pr_prodotti", "pr_codice", "pr_text_descr"}
            if not required <= set(row):
                raise RuntimeError(f"Incomplete Taam product block: {url}")
            occurrence = {
                "source_category": category,
                "source_url": url,
                "source_product_name": row["pr_prodotti"],
                "source_grade": row.get("pr_sae", ""),
                "product_code": row["pr_codice"],
                "description": row["pr_text_descr"],
            }
            occurrences.append(occurrence)
            normalized_page.append(occurrence)
        page_fact_hashes[filename] = hashlib.sha256(
            json.dumps(
                normalized_page, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    if len(occurrences) != 216:
        raise RuntimeError(
            f"Taam product occurrence denominator changed: {len(occurrences)}"
        )
    by_code: dict[str, list[dict]] = defaultdict(list)
    for row in occurrences:
        by_code[row["product_code"]].append(row)
    if len(by_code) != 175:
        raise RuntimeError(
            f"Taam unique product-code denominator changed: {len(by_code)}"
        )

    records = []
    for index, (product_code, rows) in enumerate(sorted(by_code.items()), 1):
        identities = {
            (
                row["source_product_name"], row["source_grade"],
                row["description"],
            )
            for row in rows
        }
        if len(identities) != 1:
            raise RuntimeError(f"Taam product-code collision: {product_code}")
        source_name, source_grade, description = next(iter(identities))
        categories = sorted({row["source_category"] for row in rows})
        source_urls = sorted({row["source_url"] for row in rows})
        family = family_for(source_name, description, " ".join(categories))
        specs = {
            **parsed_grade(source_grade),
            "product_code": product_code,
            "source_grade": source_grade,
            "source_categories": categories,
            "source_page_urls": source_urls,
            "source_occurrences": len(rows),
            "description_sha256": hashlib.sha256(
                description.encode()
            ).hexdigest(),
            "source_quality_flags": [
                "current_live_distributor_page_without_published_page_update_date",
                "category_pages_publish_function_and_grade_but_not_api_acea_oem_approval_tables",
            ],
        }
        facts = {
            "source_product_name": source_name,
            "source_grade": source_grade,
            "product_code": product_code,
            "categories": categories,
            "source_urls": source_urls,
            "description_sha256": specs["description_sha256"],
        }
        suffix = f" {source_grade}" if source_grade else ""
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"TAAM-SS-{index:03d}",
            "source_url": BASE_URL + "products.php",
            "snapshot_date": SNAPSHOT_DATE,
            "market": "South Sudan",
            "manufacturer": "Pakelo Lubricants",
            "brand": "PAKELO",
            "product_name": f"Pakelo {source_name}{suffix}",
            "source_product_name": source_name,
            "family_code": family,
            "existing_zf_source_record_id": EXACT_ZF_MATCHES.get(
                product_code, ""
            ),
            "evidence_status": "official_south_sudan_distributor_product_catalog",
            "lifecycle_status": "live_official_distributor_catalog_page",
            "specifications": specs,
            "source_facts_sha256": hashlib.sha256(
                json.dumps(
                    facts, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "live_official_south_sudan_distributor_complete_category_catalog",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "category_pages": len(CATEGORY_PAGES),
        "page_counts": page_counts,
        "product_occurrences": len(occurrences),
        "duplicate_category_occurrences": len(occurrences) - len(records),
        "unique_product_codes": len(records),
        "product_code_collisions": 0,
        "exact_existing_zf_identity_matches": len(EXACT_ZF_MATCHES),
        "new_distributor_catalog_identities": len(records) - len(EXACT_ZF_MATCHES),
        "families": dict(sorted(Counter(
            row["family_code"] for row in records
        ).items())),
        "records_with_sae": sum(
            bool(row["specifications"].get("sae_engine")) for row in records
        ),
        "records_with_iso_vg": sum(
            bool(row["specifications"].get("iso_vg")) for row in records
        ),
        "records_with_nlgi": sum(
            bool(row["specifications"].get("nlgi")) for row in records
        ),
        "page_facts_sha256": page_fact_hashes,
        "normalized_output_sha256": hashlib.sha256(
            output_text.encode()
        ).hexdigest(),
        "denominator_note": "Ten category pages publish 216 product occurrences. Exact product-code deduplication removes 41 repeated category occurrences, leaving 175 unique identities with no code/title/grade collision.",
        "publication_scope": "Factual product names, grades, product codes, category membership and evidence hashes only; descriptions, artwork and contacts are not redistributed.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
