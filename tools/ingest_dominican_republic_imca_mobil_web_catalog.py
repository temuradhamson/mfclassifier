#!/usr/bin/env python3
"""Audit all live product pages in IMCA's official Mobil sitemap.

The HTML contains dynamic nonces, so raw page hashes are not reproducible.
Instead, each row hashes a stable factual projection of the product section:
published title, categories, sitemap last-modified timestamp and normalized
product-section text.  The expressive body text itself is not redistributed.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/dominican-republic-imca-mobil-web-pages.jsonl"
REPORT = ROOT / "data/dominican-republic-imca-mobil-web-report.json"
SOURCE_ID = "DOMINICAN_REPUBLIC_IMCA_MOBIL_LIVE_WEB_CATALOG"
BASE = "https://lubricantesmobil.imcadom.com"
SITEMAP_URL = BASE + "/productos-sitemap.xml"
ARCHIVE_URL = BASE + "/productos/"
USER_AGENT = (
    "Mozilla/5.0 (compatible; WorldLubricantsCatalog/1.0; "
    "+https://github.com/temuradhamson/mfclassifier)"
)
CATEGORY_NAMES = {
    "automotriz": "Automotriz",
    "flotillas": "Flotillas",
    "grasas": "Grasas",
    "industrial": "Industrial",
    "maquinaria-pesada": "Maquinaria Pesada",
    "maritimo-aviacion": "Marítimo / Aviación",
}
COMBINED_CATEGORY_NAMES = {
    "automotrizflotillas": ["Automotriz", "Flotillas"],
    "maquinaria-pesadaautomotriz": ["Maquinaria Pesada", "Automotriz"],
}
PRODUCT_TYPE_PREFIXES = (
    ("semi-sintetico-", "Semi-Sintético"),
    ("sintetico-", "Sintético"),
    ("refrigerante-", "Refrigerante"),
    ("mineral-", "Mineral"),
)


def normalize_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        html.unescape(value).replace("\xa0", " "),
    ).strip()


class ProductPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_h1 = False
        self.h1_parts: list[str] = []
        self.title = ""
        self.product_started = False
        self.product_finished = False
        self.product_parts: list[str] = []
        self.categories: list[str] = []
        self.product_types: list[str] = []
        self.taxonomy_slugs: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if tag == "h1" and not self.title:
            self.in_h1 = True
            self.h1_parts = []
        classes = (attributes.get("class") or "").split()
        if tag == "div" and "type-productos" in classes:
            for class_name in classes:
                if class_name.startswith("product-cats-"):
                    slug = class_name.removeprefix("product-cats-")
                    if slug not in self.taxonomy_slugs:
                        self.taxonomy_slugs.append(slug)
                    decoded = slug.removesuffix("-2")
                    for prefix, product_type in PRODUCT_TYPE_PREFIXES:
                        if decoded.startswith(prefix):
                            decoded = decoded.removeprefix(prefix)
                            if product_type not in self.product_types:
                                self.product_types.append(product_type)
                            break
                    categories = COMBINED_CATEGORY_NAMES.get(
                        decoded,
                        [CATEGORY_NAMES.get(decoded, decoded)],
                    )
                    for category in categories:
                        if category not in self.categories:
                            self.categories.append(category)
        if (
            self.product_started
            and not self.product_finished
            and tag in {"p", "li", "br", "h2", "h3", "h4", "td", "th"}
        ):
            self.product_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.in_h1:
            self.h1_parts.append(data)
        if self.product_started and not self.product_finished:
            normalized = normalize_text(data)
            if normalized.upper().startswith("SOLICITA TU COTIZACIÓN"):
                self.product_finished = True
            elif normalized:
                self.product_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self.in_h1:
            self.title = normalize_text("".join(self.h1_parts))
            self.in_h1 = False
            self.product_started = True
            self.product_parts.append(self.title)

    def product_text(self) -> str:
        return normalize_text(" ".join(self.product_parts))


def fetch(url: str, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"{url}: HTTP {response.status}")
                return response.read()
        except Exception as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{url}: fetch failed after {attempts} attempts") from last_error


def sitemap_entries(payload: bytes) -> list[tuple[str, str]]:
    root = ET.fromstring(payload)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    entries: list[tuple[str, str]] = []
    for url_node in root.findall("sm:url", namespace):
        location = (url_node.findtext("sm:loc", "", namespace) or "").strip()
        modified = (
            url_node.findtext("sm:lastmod", "", namespace) or ""
        ).strip()
        if location.rstrip("/") != ARCHIVE_URL.rstrip("/"):
            entries.append((location, modified))
    return entries


def ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def extract_sae(text: str) -> list[str]:
    return ordered_unique([
        re.sub(r"\s+", "", match.group(0).upper())
        for match in re.finditer(
            r"(?<![A-Z0-9])\d{1,2}W(?:\s*-\s*|\s*)\d{1,3}(?![A-Z0-9])",
            text,
            flags=re.IGNORECASE,
        )
    ])


def extract_label_nearby_tokens(
    text: str,
    label: str,
    allowed: tuple[str, ...],
) -> list[str]:
    results: list[str] = []
    upper = text.upper()
    for match in re.finditer(rf"\b{re.escape(label)}\b", upper):
        window = upper[match.end():match.end() + 120]
        for token in allowed:
            if re.search(
                rf"(?<![A-Z0-9]){re.escape(token)}(?![A-Z0-9])",
                window,
            ) and token not in results:
                results.append(token)
    return results


def extract_viscosity_statements(text: str) -> list[str]:
    statements: list[str] = []
    for match in re.finditer(
        r"\bViscosidad(?:es)?\b.{0,120}",
        text,
        flags=re.IGNORECASE,
    ):
        statement = re.split(r"[.;]", match.group(0), maxsplit=1)[0]
        statement = normalize_text(statement)
        if statement and statement not in statements:
            statements.append(statement)
    return statements


def parse_page(
    entry: tuple[str, str],
    payload: bytes,
) -> dict[str, Any]:
    url, last_modified = entry
    parser = ProductPageParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    product_text = parser.product_text()
    if not parser.title or len(product_text) < len(parser.title):
        raise AssertionError(f"{url}: product section was not parsed")
    factual_projection = {
        "title": parser.title,
        "categories": sorted(parser.categories),
        "product_types": sorted(parser.product_types),
        "taxonomy_slugs": sorted(parser.taxonomy_slugs),
        "sitemap_last_modified": last_modified,
        "normalized_product_section_text": product_text,
    }
    factual_projection_sha256 = hashlib.sha256(
        json.dumps(
            factual_projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    api = extract_label_nearby_tokens(
        product_text,
        "API",
        (
            "CK-4", "CJ-4", "CI-4 PLUS", "CI-4", "CH-4", "CG-4",
            "CF-4", "CF-2", "CF", "SP", "SN PLUS", "SN", "SM", "SL",
            "SJ", "SH", "SG", "TC", "GL-6", "GL-5", "GL-4",
        ),
    )
    return {
        "source_id": SOURCE_ID,
        "source_record_id": (
            "IMCA-WEB-"
            + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12].upper()
        ),
        "brand": "MOBIL",
        "product_page_title": parser.title,
        "source_url": url,
        "source_categories": sorted(parser.categories),
        "source_product_types": sorted(parser.product_types),
        "source_taxonomy_slugs": sorted(parser.taxonomy_slugs),
        "sitemap_last_modified": last_modified,
        "snapshot_date": str(date.today()),
        "http_status": 200,
        "normalized_product_section_sha256": hashlib.sha256(
            product_text.encode("utf-8")
        ).hexdigest(),
        "factual_projection_sha256": factual_projection_sha256,
        "technical_tokens": {
            "sae": extract_sae(product_text),
            "api": api,
            "api_gl": [value for value in api if value.startswith("GL-")],
            "acea": extract_label_nearby_tokens(
                product_text,
                "ACEA",
                (
                    "A1/B1", "A3/B3", "A3/B4", "A5/B5", "A7/B7",
                    "C1", "C2", "C3", "C4", "C5", "C6",
                    "E4", "E6", "E7", "E8", "E9", "E11",
                ),
            ),
            "jaso": extract_label_nearby_tokens(
                product_text,
                "JASO",
                ("MA", "MA1", "MA2", "MB", "DH-1", "DH-2", "DL-1"),
            ),
            "viscosity_statements": extract_viscosity_statements(
                product_text
            ),
        },
        "evidence_scope": (
            "live_official_authorized_distributor_product_or_series_page"
        ),
        "lifecycle_status": (
            "live_page_sitemap_date_preserved_formulation_freshness_not_inferred"
        ),
        "source_quality_flags": [
            "complete_official_product_sitemap_denominator",
            "raw_html_contains_dynamic_nonces_not_used_as_reproducible_hash",
            "stable_factual_projection_hash",
            "source_reported_technical_tokens_not_independent_approvals",
            "expressive_product_body_not_redistributed",
        ],
    }


def main() -> None:
    sitemap_payload = fetch(SITEMAP_URL)
    entries = sitemap_entries(sitemap_payload)
    assert len(entries) == 95
    assert len({url for url, _ in entries}) == 95

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        payloads = list(executor.map(lambda item: fetch(item[0]), entries))
    rows = [
        parse_page(entry, payload)
        for entry, payload in zip(entries, payloads)
    ]
    assert len({row["source_record_id"] for row in rows}) == 95
    assert all(row["http_status"] == 200 for row in rows)

    rows.sort(key=lambda row: row["source_url"])
    rendered = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )
    OUT.write_text(rendered, encoding="utf-8")
    date_counts = Counter(
        row["sitemap_last_modified"][:10] for row in rows
    )
    category_counts = Counter(
        category
        for row in rows
        for category in row["source_categories"]
    )
    product_type_counts = Counter(
        product_type
        for row in rows
        for product_type in row["source_product_types"]
    )
    report = {
        "source_id": SOURCE_ID,
        "source_url": ARCHIVE_URL,
        "source_sitemap_url": SITEMAP_URL,
        "source_sitemap_sha256": hashlib.sha256(
            sitemap_payload
        ).hexdigest(),
        "snapshot_date": str(date.today()),
        "sitemap_product_pages": len(rows),
        "http_200_pages": sum(row["http_status"] == 200 for row in rows),
        "unique_factual_projection_hashes": len({
            row["factual_projection_sha256"] for row in rows
        }),
        "unique_product_page_titles": len({
            row["product_page_title"].casefold() for row in rows
        }),
        "pages_with_sae_tokens": sum(
            bool(row["technical_tokens"]["sae"]) for row in rows
        ),
        "pages_with_api_tokens": sum(
            bool(row["technical_tokens"]["api"]) for row in rows
        ),
        "sitemap_last_modified_date_counts": dict(sorted(date_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "product_type_counts": dict(sorted(product_type_counts.items())),
        "normalized_output_sha256": hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "Complete live page denominator. Sitemap dates are preserved; "
            "a live URL does not prove a recently reformulated product."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
