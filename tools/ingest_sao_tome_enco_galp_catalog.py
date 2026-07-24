#!/usr/bin/env python3
"""Normalize ENCO São Tomé's complete current public Galp product API."""

from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sao-tome-enco-current-galp-products.jsonl"
REPORT = ROOT / "data" / "sao-tome-enco-current-galp-products-report.json"
SITE = "https://www.enco.st"
API = "https://encoserver.exportech.com.pt"
HOME_URL = f"{SITE}/"
PRODUCTS_PAGE_URL = f"{SITE}/produtos.html"
MAIN_JS_URL = f"{SITE}/main.js"
PRODUCTS_API_URL = f"{API}/api/products?limit=1000"
ACTIVE_PRODUCTS_API_URL = f"{API}/api/products?active=true&limit=1000"
PRODUCT_CATEGORIES_API_URL = f"{API}/api/product-categories"
SOURCE_ID = "SAO_TOME_ENCO_COMPLETE_CURRENT_GALP_PRODUCT_API"
SNAPSHOT_DATE = "2026-07-24"


def fetch(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "mfclassifier-source-ingest/1.0"},
    )
    with urlopen(request, timeout=90) as response:
        if response.status != 200:
            raise RuntimeError(f"{url}: HTTP {response.status}")
        return response.read()


def clean_html(fragment: str) -> str:
    return re.sub(
        r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment))
    ).strip()


def main() -> None:
    home = fetch(HOME_URL)
    products_page = fetch(PRODUCTS_PAGE_URL)
    main_js = fetch(MAIN_JS_URL)
    api_payload = fetch(PRODUCTS_API_URL)
    active_api_payload = fetch(ACTIVE_PRODUCTS_API_URL)
    categories_payload = fetch(PRODUCT_CATEGORIES_API_URL)
    api_data = json.loads(api_payload)
    active_api_data = json.loads(active_api_payload)
    categories = json.loads(categories_payload)

    if api_data != active_api_data:
        raise RuntimeError("ENCO complete and active product denominators differ")
    if (
        api_data.get("total") != 1
        or api_data.get("pages") != 1
        or len(api_data.get("products", [])) != 1
    ):
        raise RuntimeError(
            "ENCO complete product API denominator changed: "
            + repr({
                "total": api_data.get("total"),
                "pages": api_data.get("pages"),
                "rows": len(api_data.get("products", [])),
            })
        )
    if len(categories) != 1 or categories[0].get("slug") != "produtos-galp":
        raise RuntimeError("ENCO product category denominator changed")
    if API.encode() not in main_js:
        raise RuntimeError("ENCO frontend API origin changed")
    if b"/api/products" not in products_page:
        raise RuntimeError("ENCO products page no longer consumes product API")
    if b"distribuidora oficial dos produtos Galp" not in home:
        raise RuntimeError("ENCO official Galp distributor statement changed")
    if b"Todos os direitos reservados" not in products_page:
        raise RuntimeError("ENCO footer rights statement changed")

    product = api_data["products"][0]
    expected = {
        "_id": "69d783a6cee10f6790f236de",
        "title": "Galp Formula 15w40",
        "slug": "galp-formula-15w40",
        "active": True,
        "category_slug": "produtos-galp",
    }
    observed = {
        "_id": product.get("_id"),
        "title": product.get("title"),
        "slug": product.get("slug"),
        "active": product.get("active"),
        "category_slug": (product.get("category") or {}).get("slug"),
    }
    if observed != expected:
        raise RuntimeError("ENCO current product identity changed: " + repr(observed))
    detail_url = f"{API}/api/products/{product['_id']}"
    detail_payload = fetch(detail_url)
    detail = json.loads(detail_payload).get("product")
    if detail != product:
        raise RuntimeError("ENCO product-list/detail payloads differ")
    image_payload = fetch(product["image"])

    technical_text = clean_html(product["html"]).upper()
    if "API CD/SF" not in technical_text or "MIL L-2104 C" not in technical_text:
        raise RuntimeError("ENCO source specifications changed")
    specs = {
        "sae_engine": "15W-40",
        "sae_gear": "",
        "iso_vg": "",
        "nlgi": "",
        "api": ["CD", "SF"],
        "api_gl": [],
        "acea": [],
        "ilsac": [],
        "jaso": [],
        "military_specifications": ["MIL-L-2104C"],
    }
    factual_projection = {
        "source_product_id": product["_id"],
        "source_title": product["title"],
        "source_slug": product["slug"],
        "source_category_id": product["category"]["_id"],
        "source_category_name": product["category"]["name"],
        "source_category_slug": product["category"]["slug"],
        "active": product["active"],
        "created_at": product["createdAt"],
        "updated_at": product["updatedAt"],
        "specifications": specs,
    }
    row = {
        "source_id": SOURCE_ID,
        "source_record_id": "ENCO-ST-" + product["_id"].upper(),
        "manufacturer": "Galp",
        "brand": "Galp",
        "local_distributor": "ENCO — Energia & Combustíveis",
        "market": "São Tomé and Príncipe",
        "family_code": "M",
        "product_name": "Galp Formula 15W-40",
        "source_series": "Galp Formula",
        "source_grade": "15W-40",
        "source_grade_kind": "sae_engine",
        "source_grade_evidence": "current_product_api_title",
        "source_product_id": product["_id"],
        "source_slug": product["slug"],
        "source_category": product["category"]["name"],
        "source_url": (
            f"{SITE}/detalhes_do_produto.html?id={product['_id']}"
        ),
        "source_api_url": PRODUCTS_API_URL,
        "source_detail_api_url": detail_url,
        "source_api_sha256": hashlib.sha256(api_payload).hexdigest(),
        "source_detail_api_sha256": hashlib.sha256(detail_payload).hexdigest(),
        "source_image_url": product["image"],
        "source_image_sha256": hashlib.sha256(image_payload).hexdigest(),
        "source_created_at": product["createdAt"],
        "source_updated_at": product["updatedAt"],
        "source_factual_projection_sha256": hashlib.sha256(
            json.dumps(
                factual_projection,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "snapshot_date": SNAPSHOT_DATE,
        "lifecycle_status": "active_on_current_official_distributor_api",
        "evidence_status": "official_country_distributor_complete_current_api",
        "publication_scope": (
            "attributed_transformed_nonexpressive_factual_fields_only"
        ),
        "technical": specs,
        "source_quality_flags": [],
    }
    OUT.write_text(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "status": "complete_current_public_product_api_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "owner": "ENCO — Energia & Combustíveis",
        "market": "São Tomé and Príncipe",
        "homepage_url": HOME_URL,
        "products_page_url": PRODUCTS_PAGE_URL,
        "frontend_api_origin": API,
        "products_api_url": PRODUCTS_API_URL,
        "active_products_api_url": ACTIVE_PRODUCTS_API_URL,
        "product_categories_api_url": PRODUCT_CATEGORIES_API_URL,
        "homepage_sha256": hashlib.sha256(home).hexdigest(),
        "products_page_sha256": hashlib.sha256(products_page).hexdigest(),
        "main_js_sha256": hashlib.sha256(main_js).hexdigest(),
        "products_api_sha256": hashlib.sha256(api_payload).hexdigest(),
        "active_products_api_sha256": hashlib.sha256(
            active_api_payload
        ).hexdigest(),
        "product_categories_api_sha256": hashlib.sha256(
            categories_payload
        ).hexdigest(),
        "api_reported_total": api_data["total"],
        "api_reported_pages": api_data["pages"],
        "api_product_rows": len(api_data["products"]),
        "active_product_rows": 1,
        "normalized_product_grade_rows": 1,
        "product_categories": 1,
        "families": {"M": 1},
        "rows_with_sae": 1,
        "rows_with_api": 1,
        "rows_with_military_specification": 1,
        "offers_created": 0,
        "output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": (
            "One current public API record; only attributed product identity, "
            "grade, standards, category, dates, source links and hashes are "
            "retained. Description, HTML and image bytes are not redistributed."
        ),
        "scope_limit": (
            "The current ENCO public API denominator is one active product. "
            "Nine hard-coded frontend fallback examples are not source records "
            "and are not ingested."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
