#!/usr/bin/env python3
"""Ingest the complete current official MAG 1 product sitemap.

Only factual product fields and tables are retained. Marketing prose and
images are represented by hashes/URLs and are not redistributed. Every leaf
product page is audited, including transparent out-of-scope exclusions.
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
from urllib.parse import urljoin, urlparse


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/mag1-current-official-products.jsonl"
EXCLUSIONS = ROOT / "data/mag1-current-official-exclusions.jsonl"
REPORT = ROOT / "data/mag1-current-official-catalog-report.json"
SOURCE_ID = "MAG1_CURRENT_OFFICIAL_PRODUCT_CATALOG"
SITEMAP_URL = "https://mag1.com/sitemap.xml"
USER_AGENT = (
    "Mozilla/5.0 (compatible; WorldLubricantsCatalog/1.0; "
    "+https://github.com/temuradhamson/mfclassifier)"
)
LEAF_RE = re.compile(r"/products/.+/(?:mag-1|mag1)-[^/]+/$")


def normalize_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        html.unescape(value).replace("\xa0", " "),
    ).strip()


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
    for node in root.findall("sm:url", namespace):
        url = (node.findtext("sm:loc", "", namespace) or "").strip()
        modified = (
            node.findtext("sm:lastmod", "", namespace) or ""
        ).strip()
        if LEAF_RE.search(urlparse(url).path):
            entries.append((url, modified))
    return entries


class ProductParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture_title = False
        self.capture_subhead = False
        self.capture_table_title = False
        self.capture_cell = False
        self.title_parts: list[str] = []
        self.subhead_parts: list[str] = []
        self.table_title_parts: list[str] = []
        self.cell_parts: list[str] = []
        self.current_table_title = ""
        self.current_row: list[str] = []
        self.tables: dict[str, list[list[str]]] = {}
        self.pds_url = ""
        self.image_url = ""

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "h1" and "text-page-header__headline" in classes:
            self.capture_title = True
        elif tag == "h5" and "text-page-header__subhead" in classes:
            self.capture_subhead = True
        elif tag == "h4" and "product-detail__table-title" in classes:
            self.capture_table_title = True
            self.table_title_parts = []
        elif tag == "tr":
            self.current_row = []
        elif tag == "td":
            self.capture_cell = True
            self.cell_parts = []
        elif tag == "a":
            href = attributes.get("href") or ""
            if (
                not self.pds_url
                and "product-detail__download-link" in classes
                and href.endswith("/pds/")
            ):
                self.pds_url = urljoin("https://mag1.com/", href)
        elif (
            tag == "img"
            and not self.image_url
            and (
                "product-detail__product-shot" in classes
                or "pds-product-shot" in classes
            )
        ):
            self.image_url = urljoin(
                "https://mag1.com/",
                attributes.get("src") or "",
            )

    def handle_data(self, data: str) -> None:
        if self.capture_title:
            self.title_parts.append(data)
        if self.capture_subhead:
            self.subhead_parts.append(data)
        if self.capture_table_title:
            self.table_title_parts.append(data)
        if self.capture_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self.capture_title:
            self.capture_title = False
        elif tag == "h5" and self.capture_subhead:
            self.capture_subhead = False
        elif tag == "h4" and self.capture_table_title:
            self.capture_table_title = False
            self.current_table_title = normalize_text(
                "".join(self.table_title_parts)
            )
            self.tables.setdefault(self.current_table_title, [])
        elif tag == "td" and self.capture_cell:
            self.capture_cell = False
            self.current_row.append(
                normalize_text("".join(self.cell_parts))
            )
        elif tag == "tr":
            if self.current_table_title and any(self.current_row):
                self.tables[self.current_table_title].append(
                    self.current_row
                )

    @property
    def title(self) -> str:
        return normalize_text("".join(self.title_parts))

    @property
    def subhead(self) -> str:
        return normalize_text("".join(self.subhead_parts))


def family_for(url: str, title: str) -> tuple[str, str]:
    path = urlparse(url).path
    if "/passenger-car-motor-oil/" in path:
        return "M", "passenger_car_engine_oil"
    if "/heavy-duty-diesel-engine-oils/" in path:
        return "M", "heavy_duty_engine_oil"
    if "/industrial-greases/anti-wear-hydraulic-oil/" in path:
        return "H", "hydraulic_oil"
    if (
        "/industrial-greases/synthetic-gear-oil/" in path
        or "/industrial-greases/conventional-gear-oil/" in path
    ):
        return "T", "automotive_gear_oil"
    if "/industrial-greases/" in path:
        return "I", "industrial_lubricant"
    if "/transmission-fluids/" in path:
        return "T", "transmission_or_driveline_fluid"
    if "/2-cycle-small-engine/" in path:
        if "gear oil" in title.casefold():
            return "T", "marine_gear_oil"
        if "compressor oil" in title.casefold() or "pump oil" in title.casefold():
            return "I", "small_equipment_industrial_oil"
        return "M", "two_or_four_cycle_engine_oil"
    if "/brake-fluid/" in path:
        return "TF", "brake_fluid"
    if (
        "/engine-oil-additives/" in path
        or "/gasoline-fuel-additives/" in path
    ):
        return "S", "engine_or_fuel_additive"
    if "/power-steering-fluid/" in path:
        return "T", "power_steering_fluid"
    if title == "MAG 1® White Lithium Grease":
        return "G", "aerosol_grease"
    if title in {
        "MAG 1® Silicone Spray",
        "MAG 1® Penetrating Oil",
        "MAG 1® Chain Lubricant",
    }:
        return "U", "maintenance_lubricant"
    return "", "out_of_scope_cleaner_dressing_or_equipment_product"


def ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def technical_for(
    title: str,
    family_code: str,
    tables: dict[str, list[list[str]]],
) -> dict[str, Any]:
    specification_rows = tables.get("Industry/OEM Specifications", [])
    specification_labels = [
        row[0] for row in specification_rows if row
    ]
    specification_text = " | ".join(specification_labels)
    sae_values = ordered_unique([
        re.sub(r"\s+", "", match.group(0).upper())
        for match in re.finditer(
            r"(?<![A-Z0-9])\d{1,2}W(?:\s*-\s*|\s*)\d{1,3}(?![A-Z0-9])",
            title,
            flags=re.IGNORECASE,
        )
    ])
    monograde = re.search(
        r"\bSAE\s+(\d{1,2})\b",
        title,
        flags=re.IGNORECASE,
    )
    if monograde:
        sae_values.append(f"SAE {monograde.group(1)}")
    api_allowed = (
        "CK-4", "CJ-4", "CI-4 PLUS", "CI-4", "CH-4", "CG-4",
        "CF-4", "CF-2", "CF", "SP", "SN PLUS", "SN", "SM", "SL",
        "SJ", "SH", "SG", "SF", "TC",
    )
    api: list[str] = []
    api_gl: list[str] = []
    for label in specification_labels:
        if not label.upper().startswith("API "):
            continue
        upper = label.upper()
        for token in api_allowed:
            if re.search(
                rf"(?<![A-Z0-9]){re.escape(token)}(?![A-Z0-9])",
                upper,
            ) and token not in api:
                api.append(token)
        for match in re.finditer(r"\bGL[- ]?([1-6])\b", upper):
            value = f"GL-{match.group(1)}"
            if value not in api_gl:
                api_gl.append(value)
    acea = ordered_unique([
        match.group(1).upper()
        for match in re.finditer(
            r"\bACEA\s+([A-Z]\d(?:/[A-Z]\d)?)\b",
            specification_text,
            flags=re.IGNORECASE,
        )
    ])
    ilsac = ordered_unique([
        f"GF-{match.group(1).upper()}"
        for match in re.finditer(
            r"\bILSAC\s+GF-?(\d[A-Z]?)\b",
            specification_text,
            flags=re.IGNORECASE,
        )
    ])
    jaso: list[str] = []
    for label in specification_labels:
        if "JASO" not in label.upper():
            continue
        upper = label.upper()
        for pattern, normalized in (
            (r"\bMA-?2\b", "MA2"),
            (r"\bMA-?1\b", "MA1"),
            (r"\bMA\b", "MA"),
            (r"\bMB\b", "MB"),
            (r"\bFB\b", "FB"),
            (r"\bFC\b", "FC"),
            (r"\bFD\b", "FD"),
            (r"\bDH-1\b", "DH-1"),
            (r"\bDH-2\b", "DH-2"),
            (r"\bDL-1\b", "DL-1"),
        ):
            if re.search(pattern, upper) and normalized not in jaso:
                jaso.append(normalized)
    nmma = ordered_unique([
        "TC-W3"
        for _ in re.finditer(
            r"\bTC-?W-?3\b",
            specification_text,
            flags=re.IGNORECASE,
        )
    ])
    iso_title = re.search(
        r"\bISO\s+(\d{1,4})\b",
        title,
        flags=re.IGNORECASE,
    )
    dot_title = re.search(
        r"\bDOT\s*([345](?:\.1)?)\b",
        title,
        flags=re.IGNORECASE,
    )
    typical = tables.get("Typical Properties", [])
    nlgi_values = ordered_unique([
        row[2]
        for row in typical
        if len(row) >= 3 and "NLGI" in row[0].upper() and row[2]
    ])
    sae_value = (sae_values + [""])[0]
    gear_context = family_code == "T"
    return {
        "sae_engine": "" if gear_context else sae_value,
        "sae_gear": sae_value if gear_context else "",
        "api": api,
        "api_gl": api_gl,
        "acea": acea,
        "ilsac": ilsac,
        "jaso": jaso,
        "nmma": nmma,
        "iso_vg": iso_title.group(1) if iso_title else "",
        "nlgi": nlgi_values,
        "dot": f"DOT {dot_title.group(1)}" if dot_title else "",
        "industry_oem_specifications": specification_rows,
    }


def parse_one(
    entry: tuple[str, str],
    product_payload: bytes,
) -> dict[str, Any]:
    url, last_modified = entry
    page_parser = ProductParser()
    page_parser.feed(product_payload.decode("utf-8", errors="replace"))
    if not page_parser.title or not page_parser.pds_url:
        raise AssertionError(f"{url}: title or PDS link missing")
    pds_payload = fetch(page_parser.pds_url)
    pds_parser = ProductParser()
    pds_parser.feed(pds_payload.decode("utf-8", errors="replace"))
    if pds_parser.title != page_parser.title:
        raise AssertionError(f"{url}: product/PDS title mismatch")
    family_code, source_category = family_for(url, page_parser.title)
    tables = {
        key: rows
        for key, rows in sorted(pds_parser.tables.items())
        if key and rows
    }
    factual_projection = {
        "title": page_parser.title,
        "subhead": pds_parser.subhead,
        "tables": tables,
        "sitemap_last_modified": last_modified,
    }
    projection_json = json.dumps(
        factual_projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    base = {
        "source_id": SOURCE_ID,
        "source_record_id": (
            "MAG1-"
            + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12].upper()
        ),
        "brand": "MAG 1",
        "product_name": page_parser.title,
        "source_url": url,
        "pds_url": page_parser.pds_url,
        "source_image_url": page_parser.image_url,
        "source_subhead": pds_parser.subhead,
        "sitemap_last_modified": last_modified,
        "snapshot_date": str(date.today()),
        "http_status": 200,
        "pds_http_status": 200,
        "factual_projection_sha256": hashlib.sha256(
            projection_json.encode("utf-8")
        ).hexdigest(),
        "product_page_sha256_observed": hashlib.sha256(
            product_payload
        ).hexdigest(),
        "pds_page_sha256_observed": hashlib.sha256(
            pds_payload
        ).hexdigest(),
        "source_quality_flags": [
            "complete_official_leaf_product_sitemap_denominator",
            "official_current_product_page_and_product_data_sheet",
            "source_reported_specifications_not_independent_approvals",
            "marketing_prose_and_images_not_redistributed",
        ],
    }
    if family_code:
        technical = technical_for(
            page_parser.title,
            family_code,
            tables,
        )
        base.update({
            "family_code": family_code,
            "source_category": source_category,
            "technical": technical,
            "industry_oem_specifications": technical[
                "industry_oem_specifications"
            ],
            "typical_properties": tables.get("Typical Properties", []),
            "container_bulk_availability": tables.get(
                "Container/Bulk Availability",
                [],
            ),
            "scope_status": "included_current_official_product",
            "lifecycle_status": "current_official_product_page",
        })
    else:
        base.update({
            "scope_status": source_category,
            "lifecycle_status": "current_official_out_of_scope_page",
        })
    return base


def render_rows(rows: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in sorted(rows, key=lambda value: value["source_url"])
    )


def main() -> None:
    sitemap_payload = fetch(SITEMAP_URL)
    entries = sitemap_entries(sitemap_payload)
    assert len(entries) == 114
    assert len({url for url, _ in entries}) == 114
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        product_payloads = list(
            executor.map(lambda item: fetch(item[0]), entries)
        )
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        rows = list(
            executor.map(
                lambda pair: parse_one(pair[0], pair[1]),
                zip(entries, product_payloads),
            )
        )
    included = [row for row in rows if row.get("family_code")]
    excluded = [row for row in rows if not row.get("family_code")]
    assert len(included) + len(excluded) == 114
    included_text = render_rows(included)
    excluded_text = render_rows(excluded)
    OUT.write_text(included_text, encoding="utf-8")
    EXCLUSIONS.write_text(excluded_text, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": "https://mag1.com/products/",
        "source_sitemap_url": SITEMAP_URL,
        "source_sitemap_sha256": hashlib.sha256(
            sitemap_payload
        ).hexdigest(),
        "snapshot_date": str(date.today()),
        "leaf_product_pages": len(rows),
        "included_products": len(included),
        "excluded_pages": len(excluded),
        "families": dict(sorted(Counter(
            row["family_code"] for row in included
        ).items())),
        "included_categories": dict(sorted(Counter(
            row["source_category"] for row in included
        ).items())),
        "excluded_titles": [
            row["product_name"]
            for row in sorted(excluded, key=lambda value: value["product_name"])
        ],
        "pages_with_industry_oem_specifications": sum(
            bool(row["industry_oem_specifications"]) for row in included
        ),
        "pages_with_typical_properties": sum(
            bool(row["typical_properties"]) for row in included
        ),
        "pages_with_container_bulk_availability": sum(
            bool(row["container_bulk_availability"]) for row in included
        ),
        "unique_product_titles": len({
            row["product_name"].casefold() for row in included
        }),
        "unique_pds_urls": len({row["pds_url"] for row in rows}),
        "normalized_output_sha256": hashlib.sha256(
            included_text.encode("utf-8")
        ).hexdigest(),
        "normalized_exclusions_sha256": hashlib.sha256(
            excluded_text.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "Complete current leaf-product denominator. Factual tables are "
            "source-reported; status labels are not independent approvals. "
            "Haiti distributor presence is separate and does not imply that "
            "every global MAG 1 SKU is locally stocked."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
