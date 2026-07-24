#!/usr/bin/env python3
"""Review the complete official SCH Comoros public site for lubricant products."""

from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "comoros-sch-lubricant-scope-review.json"
SITEMAP_URL = "https://www.sch-km.com/sitemap-fr.xml"
PRODUCT_URL = "https://www.sch-km.com/nos-produits"
REPORT_2023_URL = (
    "https://www.sch-km.com/uploads/media/67b8296cc8ca0/"
    "rapport-sch-2023-compressed.pdf"
)
PROSPECTUS_2024_URL = (
    "https://www.sch-km.com/uploads/media/68245a445aa51/"
    "depliant-sch-2024.pdf"
)
EXPECTED = {
    "sitemap_sha256": (
        "6d5e896381ee8254c2d40598bae7de4b63c2a65857231d2d8bd6e5769595a4eb"
    ),
    "product_page_sha256": (
        "2aa7935cd296293668def154a33ba2924c8f5f0c910b4d27145babc7132378dd"
    ),
    "annual_report_sha256": (
        "10d708d8b35caf886e63d77b51d0df7bd29db22a3342d860651c2d2b688e5237"
    ),
    "prospectus_sha256": (
        "d0c1c9107b182533d4bc5bcc867733a568da12bdd0bacf1a638cec243c249b06"
    ),
}
PRODUCT_CATEGORIES = ["Kérosène", "Gaz butane", "Jet A1", "Essence & Gasoil"]


def fetch(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "mfclassifier-source-review/1.0"},
    )
    with urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"{url}: HTTP {response.status}")
        return response.read()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    sitemap = fetch(SITEMAP_URL)
    product_page = fetch(PRODUCT_URL)
    annual_report = fetch(REPORT_2023_URL)
    prospectus = fetch(PROSPECTUS_2024_URL)
    observed_hashes = {
        "sitemap_sha256": sha256(sitemap),
        "product_page_sha256": sha256(product_page),
        "annual_report_sha256": sha256(annual_report),
        "prospectus_sha256": sha256(prospectus),
    }
    if observed_hashes != EXPECTED:
        raise RuntimeError(
            "SCH source bytes changed; repeat the complete scope review: "
            + repr(observed_hashes)
        )

    urls = [
        node.text
        for node in ET.fromstring(sitemap).findall(".//{*}loc")
        if node.text
    ]
    html = product_page.decode("utf-8")
    content_match = re.search(
        r'<div class="main-content"><ul class="custom-list">(.*?)</ul>',
        html,
        flags=re.DOTALL,
    )
    if not content_match:
        raise RuntimeError("SCH product-list container disappeared")
    product_categories = [
        unescape(re.sub(r"<[^>]+>", "", value)).strip()
        for value in re.findall(
            r"<li>(.*?)</li>", content_match.group(1), flags=re.DOTALL
        )
    ]
    if product_categories != PRODUCT_CATEGORIES:
        raise RuntimeError(
            "SCH official product denominator changed: "
            + repr(product_categories)
        )

    facts = {
        "sitemap_url": SITEMAP_URL,
        "sitemap_urls": len(urls),
        "sitemap_url_counts": {
            "actualite_detail": sum("/actualite/" in url for url in urls),
            "documentation_detail": sum(
                "/documentation/" in url for url in urls
            ),
            "point_of_sale_detail": sum(
                "/points-de-vente/" in url for url in urls
            ),
            "region_detail": sum("/regions/" in url for url in urls),
        },
        "official_product_page_url": PRODUCT_URL,
        "official_product_categories": product_categories,
        "relevant_lubricant_product_rows": 0,
        "reviewed_documents": [
            {
                "url": REPORT_2023_URL,
                "printed_pages": 36,
                "sha256": observed_hashes["annual_report_sha256"],
            },
            {
                "url": PROSPECTUS_2024_URL,
                "printed_pages": 6,
                "sha256": observed_hashes["prospectus_sha256"],
            },
        ],
        "reviewed_document_keyword_hits": {
            "antifreeze": 0,
            "brake_fluid": 0,
            "grease": 0,
            "huile": 0,
            "lubricant": 0,
            "shell": 0,
        },
    }
    facts_sha256 = hashlib.sha256(
        json.dumps(
            facts, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    report = {
        "schema_version": 1,
        "status": "reviewed_zero_relevant_product_rows",
        "snapshot_date": "2026-07-24",
        "source_id": "COMOROS_SCH_COMPLETE_PUBLIC_SITE_LUBRICANT_SCOPE_REVIEW",
        "owner": "Société Comorienne des Hydrocarbures",
        "market": "Comoros",
        **facts,
        **observed_hashes,
        "review_facts_sha256": facts_sha256,
        "scope_limit": (
            "Zero rows applies to the complete current official SCH public "
            "site and its two published corporate product documents, not to "
            "every possible third-party retail product in Comoros."
        ),
        "historical_shell_partnership_not_promoted_to_current_sku_evidence": True,
        "offers_created": 0,
    }
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "sitemap_urls": len(urls),
        "official_product_categories": len(product_categories),
        "relevant_lubricant_product_rows": 0,
        "review_facts_sha256": facts_sha256,
    }))


if __name__ == "__main__":
    main()
