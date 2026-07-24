#!/usr/bin/env python3
"""Normalize the complete current Rymax Lubricants Rwanda product catalog.

The server-rendered Load More endpoint publishes 81 card occurrences over six
pages, including thirteen repeated URLs.  The 68 unique detail pages are
normalized once.  Published approvals, grades and document hashes are retained;
descriptions, artwork, contacts and document files are not redistributed.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/rwanda-rymax-current-products.jsonl"
REPORT = ROOT / "data/rwanda-rymax-current-report.json"
SOURCE_ID = "RWANDA_RYMAX_CURRENT_COMPLETE_PAGINATED_CATALOG"
LISTING_URL = "https://rymax-lubricants.rw/products"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"


def fetch(url: str, xhr: bool = False) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if xhr:
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


class CardLinks(HTMLParser):
    def __init__(self, scoped: bool) -> None:
        super().__init__()
        self.scoped = scoped
        self.active = not scoped
        self.depth = 0
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if (
            self.scoped and not self.active and tag == "div"
            and values.get("x-ref") == "entries"
        ):
            self.active = True
            self.depth = 1
            return
        if self.active and self.scoped and tag == "div":
            self.depth += 1
        href = values.get("href", "")
        if self.active and tag == "a" and "/products/" in href:
            self.links.append(href.split("#")[0])

    def handle_endtag(self, tag: str) -> None:
        if self.active and self.scoped and tag == "div":
            self.depth -= 1
            if self.depth == 0:
                self.active = False


class ProductPage(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture = ""
        self.capture_class = ""
        self.buffer: list[str] = []
        self.title = ""
        self.primary: list[str] = []
        self.current_heading = ""
        self.sections: dict[str, list[str]] = {}
        self.document_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"h1", "h5", "small", "p"}:
            self.capture = tag
            self.capture_class = values.get("class", "")
            self.buffer = []
        href = values.get("href", "")
        if tag == "a" and href.casefold().split("?")[0].endswith(".pdf"):
            self.document_urls.append(href)

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != self.capture:
            return
        value = re.sub(
            r"\s+", " ", html.unescape("".join(self.buffer))
        ).strip()
        if tag == "h1" and not self.title:
            self.title = value
        elif (
            tag == "p" and self.title
            and "text-primary-500" in self.capture_class
        ):
            self.primary.append(value)
        elif tag == "h5":
            self.current_heading = value
        elif tag == "small" and self.current_heading:
            self.sections.setdefault(self.current_heading, []).append(value)
        self.capture = ""


def family_for(categories: list[str], product_type: str) -> str:
    joined = " ".join(categories + [product_type]).casefold()
    if "coolant" in joined or "antfreeze" in joined:
        return "C"
    if "brake fluid" in joined:
        return "TF"
    if "grease" in joined:
        return "G"
    if "transformer" in joined:
        return "E"
    if "hydraulic" in joined:
        return "H"
    if "gear oil" in joined and "industrial" not in joined:
        return "T"
    if "atf" in joined or "transmission fluid" in joined:
        return "T"
    if "agricultural" in joined or "tractor engine and transmission" in joined:
        return "T"
    if any(value in joined for value in [
        "engine oil", "passenger car", "truck engine", "motorcycle", "marine",
    ]):
        return "M"
    if any(value in joined for value in [
        "turbine", "industrial gear", "heat transfer", "cutting oil",
    ]):
        return "I"
    return "U"


def split_api(value: str) -> list[str]:
    body = re.sub(r"^API\s+", "", value, flags=re.I).strip()
    return [
        item.strip()
        for item in re.split(r"[/,]", body)
        if item.strip()
    ]


def specifications(
    name: str,
    product_type: str,
    categories: list[str],
    grades: list[str],
    approvals: list[str],
    family: str,
) -> dict:
    specs: dict[str, object] = {
        "product_type": product_type,
        "source_categories": categories,
        "approvals_source_reported": approvals,
    }
    text = " ".join([name, *grades])
    multi = re.search(r"\b(\d{1,2}W[- ]\d{2,3})\b", text, re.I)
    mono = re.search(r"\b(?:SAE\s*)?(10W|30|40|50|90|140)\s*$", text, re.I)
    sae = ""
    if multi:
        sae = multi.group(1).upper().replace(" ", "-")
    elif mono and family in {"M", "T"}:
        sae = mono.group(1).upper()
    if sae:
        specs["sae_gear" if family == "T" and "gear" in " ".join(categories).casefold() else "sae_engine"] = sae
    elif family == "H":
        source_sae = re.search(r"\b(10W|30|40|50)\s*$", name, re.I)
        if source_sae:
            specs["source_reported_sae"] = source_sae.group(1).upper()

    iso_match = None
    if family in {"H", "I"} and any(
        name.casefold().startswith(prefix)
        for prefix in ("hydra aw ", "erato ", "gevitro tws ", "themperion ")
    ):
        iso_match = re.search(r"\b(32|46|68|100|150|220|320|460)\s*$", name)
    if iso_match:
        specs["iso_vg"] = iso_match.group(1)

    if family == "G":
        nlgi = re.search(r"\b(?:EP(?:-B)?\s*)?([0-3])\s*$", name, re.I)
        if nlgi:
            specs["nlgi"] = nlgi.group(1)
        if "lithium" in product_type.casefold():
            specs["thickener"] = (
                "lithium complex"
                if "complex" in product_type.casefold() else "lithium"
            )

    api: list[str] = []
    api_gl: list[str] = []
    acea: list[str] = []
    jaso: list[str] = []
    for approval in approvals:
        upper = approval.upper()
        if upper.startswith("API GL-"):
            api_gl.extend(split_api(approval))
        elif upper.startswith("API "):
            api.extend(split_api(approval))
        elif upper.startswith("ACEA "):
            acea.append(re.sub(r"^ACEA\s+", "", approval, flags=re.I))
        elif upper.startswith("JASO "):
            jaso.append(re.sub(r"^JASO\s+", "", approval, flags=re.I))
    if api:
        specs["api"] = sorted(set(api))
    if api_gl:
        specs["api_gl"] = sorted(set(api_gl))
    if acea:
        specs["acea"] = sorted(set(acea))
    if jaso:
        specs["jaso"] = sorted(set(jaso))

    lower_name = name.casefold()
    if family == "T" and lower_name.startswith("atexio "):
        specs["atf_specifications"] = [name.removeprefix("Atexio ").strip()]
    if "2-stroke" in product_type.casefold():
        specs["engine_cycle"] = "2T"
    elif "4-stroke" in product_type.casefold():
        specs["engine_cycle"] = "4T"
    if family == "TF":
        specs["brake_fluid_class"] = "DOT 4"
    if family == "C":
        specs["coolant_class"] = "Tropical ready-to-use"
        if name.casefold().endswith("green"):
            specs["coolant_color"] = "green"
        elif name.casefold().endswith("red"):
            specs["coolant_color"] = "red"
    return specs


def parse_product(url: str) -> dict:
    payload = fetch(url)
    parser = ProductPage()
    parser.feed(payload.decode(errors="replace"))
    if not parser.title or not parser.primary:
        raise RuntimeError(f"Incomplete Rymax page structure: {url}")
    categories = parser.sections.get("Ibyice", [])
    grades = parser.sections.get("Urwego rw'amavuta", [])
    approvals = parser.sections.get("Ibyemezo", [])
    product_type = parser.primary[0]
    source_product_name = parser.title
    if parser.title.casefold() == "dione tc ready-to-use":
        if url.rstrip("/").endswith("-green"):
            source_product_name += " Green"
        elif url.rstrip("/").endswith("-red"):
            source_product_name += " Red"
    family = family_for(categories, product_type)
    document_urls = list(dict.fromkeys(parser.document_urls))
    documents = []
    for document_url in document_urls:
        document_payload = fetch(document_url)
        documents.append({
            "url": document_url,
            "sha256": hashlib.sha256(document_payload).hexdigest(),
            "document_type": (
                "TDS" if "TDS" in document_url.upper()
                else "SDS" if "SDS" in document_url.upper()
                else "technical_document"
            ),
        })
    factual_material = json.dumps({
        "title": parser.title,
        "product_type": product_type,
        "categories": categories,
        "grades": grades,
        "approvals": approvals,
        "documents": documents,
    }, ensure_ascii=False, sort_keys=True)
    return {
        "source_url": url,
        # The localized Statamic pages contain request-specific HTML tokens.
        # Hash the normalized factual projection instead of volatile markup.
        "source_page_facts_sha256": hashlib.sha256(
            factual_material.encode()
        ).hexdigest(),
        "source_facts_sha256": hashlib.sha256(factual_material.encode()).hexdigest(),
        "brand": "RYMAX",
        "product_name": f"Rymax {source_product_name}",
        "source_product_name": source_product_name,
        "family_code": family,
        "specifications": specifications(
            parser.title, product_type, categories, grades, approvals, family
        ),
        "technical_documents": documents,
    }


def main() -> None:
    listing_links: dict[int, list[str]] = {}
    occurrences: list[str] = []
    for page in range(1, 7):
        url = LISTING_URL if page == 1 else f"{LISTING_URL}/p{page}"
        payload = fetch(url, xhr=page > 1)
        parser = CardLinks(scoped=page == 1)
        parser.feed(payload.decode(errors="replace"))
        expected = 16 if page <= 5 else 1
        if len(parser.links) != expected:
            raise RuntimeError(
                f"Rymax page {page} count changed: {len(parser.links)}"
            )
        listing_links[page] = parser.links
        occurrences.extend(parser.links)
    if len(occurrences) != 81:
        raise RuntimeError("Rymax card occurrence denominator changed")
    unique_urls = sorted(set(occurrences))
    if len(unique_urls) != 68:
        raise RuntimeError("Rymax unique detail-page denominator changed")

    with ThreadPoolExecutor(max_workers=8) as executor:
        parsed = list(executor.map(parse_product, unique_urls))
    records = []
    occurrence_counts = Counter(occurrences)
    for index, row in enumerate(sorted(parsed, key=lambda item: item["source_url"]), 1):
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"RYMAX-RW-{index:03d}",
            "listing_url": LISTING_URL,
            "listing_occurrences": occurrence_counts[row["source_url"]],
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Rwanda",
            "manufacturer": "Rymax Lubricants",
            "lifecycle_status": "current_official_country_catalog",
            "evidence_status": "current_official_brand_country_complete_paginated_catalog",
            **row,
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "current_official_country_complete_paginated_catalog_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "listing_pages": 6,
        "listing_card_occurrences": len(occurrences),
        "duplicate_listing_occurrences": len(occurrences) - len(unique_urls),
        "unique_product_pages": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "source_categories": dict(sorted(Counter(
            category for row in records
            for category in row["specifications"]["source_categories"]
        ).items())),
        "products_with_approvals": sum(
            bool(row["specifications"]["approvals_source_reported"])
            for row in records
        ),
        "products_with_documents": sum(
            bool(row["technical_documents"]) for row in records
        ),
        "technical_documents": sum(
            len(row["technical_documents"]) for row in records
        ),
        "document_types": dict(sorted(Counter(
            document["document_type"] for row in records
            for document in row["technical_documents"]
        ).items())),
        "listing_page_link_occurrences_sha256": {
            str(page): hashlib.sha256(
                json.dumps(
                    parser_links,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            for page, parser_links in sorted(listing_links.items())
        },
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "denominator_note": "Six listing responses contain 81 card occurrences (16×5 + 1); thirteen repeat an existing URL, leaving 68 unique product detail pages normalized once.",
        "publication_scope": "Factual product names, categories, grades, approvals, document links and hashes only; descriptions, artwork, contacts and source documents are excluded.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
