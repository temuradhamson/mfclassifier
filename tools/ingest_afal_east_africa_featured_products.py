#!/usr/bin/env python3
"""Normalize AFAL's six featured Caltex/Chevron products and market scope."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/afal-east-africa-featured-products.jsonl"
REPORT = ROOT / "data/afal-east-africa-featured-products-report.json"
SOURCE_ID = "AFAL_CALTEX_EAST_AFRICA_FEATURED_PRODUCTS"
SOURCE_URL = "https://www.afal.co/"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture_h4 = False
        self.buffer: list[str] = []
        self.pending_image: dict[str, str] | None = None
        self.cards: list[dict[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        if tag == "img":
            alt = html.unescape(values.get("alt", "")).strip()
            src = values.get("src", "")
            if (
                src
                and re.search(r"\b(?:SAE\s*)?(?:\d{1,2}W[- ]\d{2}|\d{2})\b", alt, re.I)
                and any(name in alt.casefold() for name in ("delo", "havoline"))
            ):
                self.pending_image = {"image_alt": alt, "image_url": src}
        elif tag == "h4" and self.pending_image:
            self.capture_h4 = True
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.capture_h4:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h4" and self.capture_h4 and self.pending_image:
            heading = re.sub(r"\s+", " ", "".join(self.buffer)).strip()
            self.cards.append({**self.pending_image, "source_heading": heading})
            self.pending_image = None
            self.capture_h4 = False


def main() -> None:
    page_payload = fetch(SOURCE_URL)
    page_text = page_payload.decode(errors="replace")
    parser = PageParser()
    parser.feed(page_text)
    if len(parser.cards) != 6:
        raise RuntimeError(
            f"AFAL featured-product denominator changed: {len(parser.cards)}"
        )

    visible_markets = [
        "Kenya", "Uganda", "Burundi", "Rwanda",
        "Eastern Democratic Republic of Congo",
    ]
    metadata_markets = [*visible_markets, "South Sudan"]
    if not all(value in page_text for value in visible_markets):
        raise RuntimeError("AFAL visible distributor market scope changed")
    if "South Sudan" not in page_text:
        raise RuntimeError("AFAL structured metadata market scope changed")

    records = []
    for index, card in enumerate(parser.cards, 1):
        image_payload = fetch(card["image_url"])
        name = card["image_alt"].strip()
        sae_match = re.search(
            r"\b(?:SAE\s*)?(\d{1,2}W[- ]\d{2}|\d{2})\b", name, re.I
        )
        if not sae_match:
            raise RuntimeError(f"AFAL SAE missing: {name}")
        sae = sae_match.group(1).upper().replace(" ", "-")
        brand = "DELO" if name.casefold().startswith("delo ") else "HAVOLINE"
        factual = {
            "name": name,
            "source_heading": card["source_heading"],
            "sae_engine": sae,
            "brand": brand,
            "image_url": card["image_url"],
            "image_sha256": hashlib.sha256(image_payload).hexdigest(),
            "visible_markets": visible_markets,
            "metadata_markets": metadata_markets,
        }
        facts_hash = hashlib.sha256(
            json.dumps(
                factual, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"AFAL-EA-{index:03d}",
            "source_url": SOURCE_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "market": "East Africa regional",
            "manufacturer": "Chevron Lubricants",
            "brand": brand,
            "product_name": name,
            "family_code": "M",
            "evidence_status": "official_authorized_regional_distributor_featured_product",
            "lifecycle_status": "live_official_regional_homepage_featured_product",
            "specifications": {
                "sae_engine": sae,
                "source_heading": card["source_heading"],
                "source_image_alt": card["image_alt"],
                "source_image_url": card["image_url"],
                "source_image_sha256": factual["image_sha256"],
                "visible_distributor_markets": visible_markets,
                "structured_metadata_markets": metadata_markets,
                "source_page_date_modified": "2021-04-07",
                "source_quality_flags": [
                    "regional_market_scope_conflict_visible_text_omits_south_sudan_but_structured_metadata_includes_it",
                    "live_page_featured_product_not_a_complete_catalog_and_freshness_not_independently_proven",
                ],
            },
            "source_facts_sha256": facts_hash,
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "live_official_authorized_regional_distributor_featured_products",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "featured_product_cards": len(records),
        "families": {"M": len(records)},
        "brands": {"DELO": 3, "HAVOLINE": 3},
        "visible_distributor_markets": visible_markets,
        "structured_metadata_markets": metadata_markets,
        "source_page_date_modified": "2021-04-07",
        "images_hashed": len(records),
        "offers_created": 0,
        "normalized_output_sha256": hashlib.sha256(
            output_text.encode()
        ).hexdigest(),
        "denominator_note": "The live official homepage visibly features exactly six product cards; it is not represented as AFAL's complete product catalog.",
        "scope_note": "The visible distributor paragraph lists five markets, while current structured metadata additionally lists South Sudan. The discrepancy is retained and no card is expanded into country-specific stock or availability.",
        "publication_scope": "Factual product names, SAE grades, attributed regional scope, image links and hashes only; images, descriptions and contacts are not redistributed.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
