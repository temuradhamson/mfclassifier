#!/usr/bin/env python3
"""Build the explicit POWERFULL lubricant portfolio published in Suriname.

The local brand/distributor site exposes nine individual product pages in its
current service sitemap.  This extractor verifies every expected page and its
key technical claims.  It keeps source-reported performance facts while
excluding marketing prose and does not silently turn the grease label EP-3
into an NLGI class.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/suriname-powerfull-current-lubricants.jsonl"
REPORT = ROOT / "data/suriname-powerfull-current-lubricants-report.json"
SOURCE_ID = "SURINAME_POWERFULL_CURRENT_LUBRICANT_CATALOG"
SITEMAP_URL = "https://powerfulllub.sr/ova_sev-sitemap.xml"
SNAPSHOT_DATE = "2026-07-23"
UA = "MFClassifier evidence catalog/1.0"


PRODUCTS = [
    {
        "slug": "powerfull-10w40",
        "name": "POWERFULL 10W-40",
        "family_code": "M",
        "sae_engine": "10W-40",
        "api": ["SN", "CF"],
        "required": ["Product specificaties: API-SN/CF"],
    },
    {
        "slug": "calcium-grease-ep-3",
        "name": "POWERFULL Calcium Grease EP-3",
        "family_code": "G",
        "source_grade": "EP-3",
        "required": ["Calcium Grease EP 3", "calciumzeep"],
    },
    {
        "slug": "85w140-gear-oils-gl5",
        "name": "POWERFULL Gear Oil 85W-140 GL-5",
        "family_code": "T",
        "sae_gear": "85W-140",
        "api_gl": ["GL-5", "MT-1"],
        "performance": [
            "SAE J2360", "Mack GO-J", "Arvin Meritor O76-A",
        ],
        "required": ["SAE J2360", "API GL-5", "API MT-1", "MACK GO-J"],
    },
    {
        "slug": "80w90-gear-oil",
        "name": "POWERFULL Gear Oil 80W-90 GL-5",
        "family_code": "T",
        "sae_gear": "80W-90",
        "api_gl": ["GL-5", "MT-1"],
        "performance": [
            "SAE J2360", "Mack GO-J", "Arvin Meritor O76-D",
            "Ford WSP-M2C197-A",
        ],
        "required": ["SAE J2360", "API GL-5", "API MT-1", "Ford WSP-M2C197-A"],
    },
    {
        "slug": "hydraulic-oil-aw-68",
        "name": "POWERFULL Hydraulic Oil AW 68",
        "family_code": "H",
        "iso_vg": "68",
        "source_grade": "AW 68",
        "required": ["Hydraulic AW 68", "hydraulische systemen"],
    },
    {
        "slug": "sae-50-synthetic",
        "name": "POWERFULL SAE 50 Synthetic",
        "family_code": "M",
        "sae_engine": "50",
        "api": ["CF", "CF-2"],
        "required": ["API CF, CF-2"],
    },
    {
        "slug": "sae-40-synthetic",
        "name": "POWERFULL SAE 40 Synthetic",
        "family_code": "M",
        "sae_engine": "40",
        "api": ["CJ-4", "SN", "CD", "CE", "CF-4", "CG-4", "CH-4", "CI-4", "CI-4 Plus"],
        "acea": ["E7-04", "A5/B5", "A3/B4", "A3/B3"],
        "performance": [
            "CAT ECF-3", "CAT ECF-1", "CAT TO-2", "MB 228.5", "MB 228.3",
            "MB 228.1", "MB 227.1", "Cummins CES 20081", "Cummins CES 20078",
            "Volvo VDS-4", "Volvo VDS-3", "Volvo VDS-2",
            "Mack EO-O Premium Plus 2007", "Mack EO-N", "Allison C-4",
        ],
        "required": ["API CJ-4/SN", "ACEA E7-04", "Cummins CES 20081", "Volvo VDS-4"],
    },
    {
        "slug": "15w40-synthetic",
        "name": "POWERFULL 15W-40 Synthetic",
        "family_code": "M",
        "sae_engine": "15W-40",
        "api": ["CJ-4", "SN", "CI-4", "CH-4", "CG-4", "CF-4", "CF"],
        "acea": ["E7-04", "A5/B5"],
        "performance": [
            "MB 228.5", "Cummins CES 20081", "Volvo VDS-4",
            "Mack EO-N", "CAT ECF-3",
        ],
        "required": ["API CJ-4/SN", "Cummins CES 20081", "Volvo VDS-4", "CAT ECF-3"],
    },
    {
        "slug": "sae-30-synthetic",
        "name": "POWERFULL SAE 30 Synthetic",
        "family_code": "M",
        "sae_engine": "30",
        "api": ["SN", "SM", "SL", "SH", "SG", "SJ"],
        "ilsac": ["GF-5"],
        "required": ["API-SN", "ILSAC GF-5"],
    },
]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and data.strip():
            self.parts.append(data.strip())


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def text_from_html(value: bytes) -> str:
    parser = TextExtractor()
    parser.feed(value.decode("utf-8", "replace"))
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()


def main() -> None:
    sitemap_bytes = get(SITEMAP_URL)
    sitemap_text = sitemap_bytes.decode("utf-8", "replace")
    sitemap_facts = [
        {"url": url, "lastmod": lastmod}
        for url, lastmod in re.findall(
            r"<loc><!\[CDATA\[(.*?)\]\]></loc>.*?"
            r"<lastmod><!\[CDATA\[(.*?)\]\]></lastmod>",
            sitemap_text,
            flags=re.DOTALL,
        )
    ]
    expected_urls = {
        f"https://powerfulllub.sr/index.php/services/{product['slug']}/"
        for product in PRODUCTS
    }
    if {row["url"] for row in sitemap_facts} != expected_urls:
        raise RuntimeError("POWERFULL current product sitemap membership changed")
    sitemap_facts_sha = sha256(
        json.dumps(sitemap_facts, ensure_ascii=False, sort_keys=True).encode()
    )
    rows = []
    page_text_hashes = {}
    facts = []

    for index, product in enumerate(PRODUCTS, 1):
        page_url = f"https://powerfulllub.sr/index.php/services/{product['slug']}/"
        if page_url not in sitemap_text:
            raise RuntimeError(f"POWERFULL product disappeared from sitemap: {page_url}")
        page_bytes = get(page_url)
        page_text = text_from_html(page_bytes)
        missing = [
            token for token in product["required"]
            if token.casefold() not in page_text.casefold()
        ]
        if missing:
            raise RuntimeError(f"POWERFULL facts changed for {product['slug']}: {missing}")
        page_text_hashes[page_url] = sha256(page_text.encode())
        technical = {
            "sae_engine": product.get("sae_engine", ""),
            "sae_gear": product.get("sae_gear", ""),
            "api": product.get("api", []),
            "api_gl": product.get("api_gl", []),
            "acea": product.get("acea", []),
            "ilsac": product.get("ilsac", []),
            "iso_vg": product.get("iso_vg", ""),
            "nlgi": "",
            "source_grade": product.get("source_grade", ""),
            "performance": product.get("performance", []),
        }
        facts.append({"url": page_url, "name": product["name"], "technical": technical})
        quality_flags = [
            "official_local_brand_product_page",
            "source_reported_performance_claims_not_independent_approvals",
            "marketing_prose_excluded",
        ]
        if product["slug"] == "calcium-grease-ep-3":
            quality_flags.append("ep_3_source_grade_not_silently_interpreted_as_nlgi")
        if product["slug"] == "hydraulic-oil-aw-68":
            quality_flags.append("iso_vg_68_normalized_from_explicit_hydraulic_aw_68_product_grade")
        rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"POWERFULL-SR-{index:02d}",
            "market": "Suriname",
            "manufacturer": "",
            "brand_owner_and_distributor": "POWERFULL LUBRICATION N.V.",
            "brand": "POWERFULL",
            "product_name": product["name"],
            "family_code": product["family_code"],
            "technical": technical,
            "lifecycle_status": "listed_on_current_official_brand_site",
            "evidence_status": "official_local_brand_product_page",
            "snapshot_date": SNAPSHOT_DATE,
            "source_url": page_url,
            "source_page_text_sha256": page_text_hashes[page_url],
            "source_quality_flags": quality_flags,
        })

    if len(rows) != 9:
        raise RuntimeError(f"POWERFULL audit matrix drift: {len(rows)} rows")
    facts_sha = sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True).encode())
    for row in rows:
        row["source_facts_sha256"] = facts_sha
        row["source_sitemap_facts_sha256"] = sitemap_facts_sha

    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "source_sitemap_facts_sha256": sitemap_facts_sha,
        "source_page_text_sha256": page_text_hashes,
        "source_facts_sha256": facts_sha,
        "normalized_products": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "rows_with_sae": sum(
            bool(row["technical"]["sae_engine"] or row["technical"]["sae_gear"])
            for row in rows
        ),
        "rows_with_api_or_api_gl": sum(
            bool(row["technical"]["api"] or row["technical"]["api_gl"])
            for row in rows
        ),
        "rows_with_iso_vg": sum(bool(row["technical"]["iso_vg"]) for row in rows),
        "grease_source_grade_without_published_nlgi": 1,
        "normalized_output_sha256": sha256(OUT.read_bytes()),
        "deferred_sources": {
            "SOL_SURINAME_ECOMMERCE": (
                "Official catalog discovered with exact product codes, packages, stock and SRD prices; "
                "origin returned Cloudflare 525 during the reproducible fetch and remains pending."
            ),
        },
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
