#!/usr/bin/env python3
"""Capture the complete current Sol Grenada lubricant ecommerce catalog.

The source is a country ecommerce surface backed by k-eCommerce. Product
packages/SKUs remain evidence and offers; product identity is derived only from
the name printed on the detail page. Marketing prose and images are not stored.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/grenada-sol-current-skus.jsonl"
PRODUCTS_OUT = ROOT / "data/grenada-sol-current-products.jsonl"
REPORT = ROOT / "data/grenada-sol-current-catalog-report.json"
SOURCE_ID = "GRENADA_SOL_CURRENT_ECOMMERCE_CATALOG"
BASE_URL = "https://grenada.solpetroleum.com/"
CATEGORY_SLUGS = (
    "diesel-engine-oils",
    "gasoline-engine-oils",
    "gear-oils",
    "greases",
    "air-compressor-oils",
    "hydraulic-oils",
    "industrial-gear-oils",
    "outboard-motorcycle-oils",
    "transmission-oils",
)
PRODUCT_SCOPE_STATUS = (
    "country_sku_availability_not_global_manufacturer_range_inference"
)


def fetch(url: str, attempts: int = 5) -> bytes:
    for attempt in range(attempts):
        result = subprocess.run(
            [
                "curl", "-LsS", "--max-time", "60",
                "-w", "\n%{http_code}", url,
            ],
            capture_output=True,
        )
        status_match = re.search(rb"\n(\d{3})\Z", result.stdout)
        status = int(status_match.group(1)) if status_match else 0
        if status == 200:
            payload = result.stdout[:status_match.start()]
            time.sleep(2)
            return payload
        if status == 429 and attempt + 1 < attempts:
            time.sleep(30)
            continue
        raise RuntimeError(f"HTTP {status or 'transport error'} for {url}")
    raise AssertionError("unreachable")


def visible_text(fragment: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        html.unescape(re.sub(r"<[^>]+>", " ", fragment)),
    ).strip()


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    return visible_text(match.group(1)) if match else ""


def detail_candidates(path: str) -> list[str]:
    direct = urljoin(BASE_URL, path)
    parts = [part for part in urlparse(direct).path.split("/") if part]
    candidates = [direct]
    if len(parts) > 1:
        candidates.append(urljoin(BASE_URL, parts[-1]))
    return list(dict.fromkeys(candidates))


def normalize_availability(value: str) -> str:
    normalized = re.sub(r"[^a-z]", "", value.casefold())
    return {
        "instock": "InStock",
        "outofstock": "OutOfStock",
        "notavailable": "NotAvailable",
    }.get(normalized, value.rsplit("/", 1)[-1])


def structured_specs(
    product_name: str,
    description: str,
    spec_text: str,
    categories: set[str],
) -> dict:
    standard_evidence = " ".join((product_name, spec_text))
    upper = standard_evidence.upper().replace("–", "-").replace("‑", "-")
    grade_evidence = " ".join((product_name, description, spec_text))
    grade_upper = grade_evidence.upper().replace("–", "-").replace("‑", "-")
    api_gl = sorted(set(re.findall(r"\bAPI\s*(GL-\d[A-Z]?)\b", upper)))
    api_values = set(
        value
        for value in re.findall(
            r"\bAPI\s+((?:C[ABCDEFGHJK]|S[ABCDEFGHJKLMNP]|F[AM])"
            r"(?:-\d)?(?:\s+PLUS)?)\b",
            upper,
        )
        if value not in api_gl
    )
    for api_group in re.findall(
        r"\bAPI\s+((?:C[A-Z]|S[A-Z]|F[AM])(?:-\d)?"
        r"(?:/(?:C[A-Z]|S[A-Z]|F[AM])(?:-\d)?)+)",
        upper,
    ):
        api_values.update(api_group.split("/"))
    api = sorted(api_values)
    acea = sorted(set(re.findall(
        r"\bACEA\s+([ABCEF]\d(?:-\d{2})?(?:/[ABCEF]?\d(?:-\d{2})?)*)\b",
        upper,
    )))
    ilsac = sorted(set(re.findall(r"\bILSAC\s+(GF-\d[A-Z]?)\b", upper)))
    jaso = sorted(set(re.findall(
        r"\bJASO\s+((?:MA2?|MB|FC|FD|DH-\d(?:-\d{2})?))\b",
        upper,
    )))
    sae_candidates = re.findall(
        r"\b((?:0|5|10|15|20|25|70|75|80|85)\s*W[ -]?\d{2,3})\b",
        grade_upper,
    )
    sae_candidates.extend(re.findall(
        r"\bSAE(?:\s+VISCOSITY)?(?:\s+GRADE)?\s+(10|20|30|40|50|60)\b",
        grade_upper,
    ))
    trailing_grade = re.search(
        r"\b(10|20|30|40|50|60)\b(?:\s+OIL)?\W*$",
        product_name,
        re.I,
    )
    if trailing_grade and not sae_candidates:
        sae_candidates.append(trailing_grade.group(1))
    sae = sorted(set(
        re.sub(r"W[- ]?", "W-", value.replace(" ", ""), flags=re.I)
        for value in sae_candidates
    ))
    gear_scope = bool(categories & {
        "gear-oils", "industrial-gear-oils", "transmission-oils",
    })
    engine_scope = bool(categories & {
        "diesel-engine-oils", "gasoline-engine-oils",
        "outboard-motorcycle-oils",
    })
    sae_gear = sae if gear_scope and not engine_scope else []
    sae_engine = sae if engine_scope else []
    nlgi = sorted(set(re.findall(r"\bNLGI(?:\s+GRADE)?\s*([0-6])\b", upper)))
    iso_vg = set(re.findall(
        r"\bISO(?:\s+VISCOSITY)?(?:\s+VG|\s+GRADE)\s*(\d{2,4})\b",
        upper,
    ))
    if (
        categories & {"air-compressor-oils", "hydraulic-oils"}
        or re.search(r"\bMOBILGEAR\s+600\s+XP\b", product_name, re.I)
    ):
        identity_grade = re.search(
            r"\b(\d{2,4})\b(?:\s+OIL)?\W*$",
            product_name,
            re.I,
        )
        if identity_grade:
            iso_vg.add(identity_grade.group(1))
    return {
        "sae_engine": sae_engine,
        "sae_gear": sae_gear,
        "api": api,
        "api_gl": api_gl,
        "acea": acea,
        "ilsac": ilsac,
        "jaso": jaso,
        "nlgi": nlgi,
        "iso_vg": sorted(iso_vg),
    }


def parse_detail(payload: bytes, listing: dict) -> dict:
    page = payload.decode("utf-8", errors="replace")
    source_title = first_match(r"<h1>(.*?)</h1>", page)
    source_code = first_match(
        r'class="product-details-code".*?<span>(.*?)</span>',
        page,
    )
    listing_code = listing["code"]
    assert re.sub(r"_GROUP$", "", listing_code, flags=re.I) == source_code, (
        listing_code, source_code, listing["detail_url"]
    )
    description_html = re.search(
        r'class="product-details-desc">(.*?)</div>',
        page,
        re.I | re.S,
    )
    description_fragment = description_html.group(1) if description_html else ""
    description = visible_text(description_fragment)
    strong_names = [
        visible_text(value)
        for value in re.findall(
            r"<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>",
            description_fragment,
            re.I | re.S,
        )
        if visible_text(value)
    ]
    product_name = strong_names[0].strip(" .,:;-") if strong_names else ""
    description_identity = re.split(
        r"\s+(?:is|are)\s+(?:an?\s+)?",
        description,
        maxsplit=1,
        flags=re.I,
    )[0].strip(" .,:;-")
    strong_has_grade = bool(re.search(
        r"\b(?:\d{1,2}\s*W[- ]?\d{2,3}|\d{2,4})\b",
        product_name,
        re.I,
    ))
    description_has_grade = bool(re.search(
        r"\b(?:\d{1,2}\s*W[- ]?\d{2,3}|\d{2,4})\b",
        description_identity,
        re.I,
    ))
    if (
        description_identity
        and len(description_identity) <= 100
        and (
            not product_name
            or (
                not strong_has_grade
                and description_has_grade
                and description_identity.casefold().startswith(
                    product_name.casefold()
                )
            )
        )
    ):
        product_name = description_identity
    if not product_name or len(product_name) > 100:
        product_name = source_title
    if product_name.casefold() in {"mobil dte", "mobil dte oils"}:
        dte_grade = re.search(r"M-DTE(\d{2,3})", source_code, re.I)
        assert dte_grade, (source_code, product_name)
        product_name = f"Mobil DTE {dte_grade.group(1)}"
    spec_html = re.search(
        r'id="tab-1"[^>]*>(.*?)(?=<div\s+class="tab-pane|\Z)',
        page,
        re.I | re.S,
    )
    spec_fragment = spec_html.group(1) if spec_html else ""
    spec_fragment = re.sub(
        r"</(?:li|p|strong|div)>",
        ";",
        spec_fragment,
        flags=re.I,
    )
    spec_text = visible_text(spec_fragment)
    json_ld_match = re.search(
        r"<script\s+type=['\"]application/ld\+json['\"]\s*>(.*?)</script>",
        page,
        re.I | re.S,
    )
    if json_ld_match:
        json_ld = json.loads(json_ld_match.group(1))
        offer = json_ld["offers"]
        detail_json_ld_status = "present"
    else:
        tracking = re.search(
            r"TrackingEvent\.addProductData\('[^']+', (\{.*?\})\);",
            page,
            re.S,
        )
        assert tracking, (listing["code"], listing["detail_url"])
        tracking_row = json.loads(tracking.group(1))
        availability = first_match(
            r'class="[^"]*productpage-Availability-label[^"]*"[^>]*>'
            r'.*?Availability:\s*</strong>\s*([^<]+)',
            page,
        )
        offer = {
            "price": tracking_row.get("Price"),
            "priceCurrency": (
                tracking_row.get("Currency") or listing["currency"]
            ),
            "availability": normalize_availability(availability),
        }
        json_ld = {"brand": {"name": tracking_row.get("Brand", "")}}
        detail_json_ld_status = "missing_fallback_to_detail_tracking_data"
    canonical = first_match(
        r'<link\s+rel="canonical"\s+href="([^"]+)"',
        page,
    )
    specification_items = [
        item.strip(" .")
        for item in re.split(r";|\n", spec_text)
        if item.strip(" .")
    ]
    price_currency = offer.get("priceCurrency") or listing["currency"]
    availability = normalize_availability(
        offer.get("availability", "") or listing["availability"]
    )
    price = str(offer.get("price", ""))
    price_status = (
        "published_current_price"
        if price_currency and float(price or 0) > 0
        else "zero_price_placeholder_without_currency"
    )
    factual_projection = {
        "source_code": source_code,
        "source_listing_title": source_title,
        "product_name": product_name,
        "price": offer.get("price"),
        "price_currency": price_currency,
        "price_status": price_status,
        "availability": availability,
        "detail_json_ld_status": detail_json_ld_status,
        "specification_items": specification_items,
    }
    return {
        "source_id": SOURCE_ID,
        "source_record_id": f"SOL-GD-{source_code}",
        "market": "Grenada",
        "brand": (
            json_ld.get("brand", {}).get("name") or listing["brand"]
        ).upper(),
        "product_name": product_name,
        "source_listing_title": source_title,
        "source_product_code": source_code,
        "source_listing_code": listing_code,
        "source_categories": sorted(listing["categories"]),
        "source_category_occurrence_count": len(listing["categories"]),
        "source_url": canonical or listing["detail_url"],
        "snapshot_date": str(date.today()),
        "price": price,
        "price_currency": price_currency,
        "price_status": price_status,
        "availability": availability,
        "detail_json_ld_status": detail_json_ld_status,
        "sales_uom": first_match(
            r'class="price price-current">.*?</strong>\s*/([^<]+)',
            page,
        ),
        "technical": structured_specs(
            product_name,
            description,
            spec_text,
            listing["categories"],
        ),
        "published_specification_items": specification_items,
        "published_specification_text_sha256": hashlib.sha256(
            spec_text.encode("utf-8")
        ).hexdigest(),
        "product_scope_status": PRODUCT_SCOPE_STATUS,
        "factual_projection_sha256": hashlib.sha256(
            json.dumps(
                factual_projection,
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        "source_quality_flags": [
            "complete_official_country_ecommerce_category_denominator",
            "current_price_and_availability_observation",
            "package_sku_not_assumed_to_be_distinct_product_identity",
            "source_reported_specifications_not_independent_approvals",
            "marketing_prose_and_images_not_redistributed",
        ] + (
            ["source_detail_json_ld_missing_factual_tracking_fallback_used"]
            if detail_json_ld_status != "present"
            else []
        ),
    }


def family_code(row: dict) -> str:
    categories = set(row["source_categories"])
    product_name = row["product_name"].casefold()
    if "greases" in categories:
        return "G"
    if "hydraulic-oils" in categories:
        return "H"
    if "air-compressor-oils" in categories:
        return "I"
    if "industrial-gear-oils" in categories:
        return "I"
    if "gear-oils" in categories:
        if (
            product_name.startswith("mobilgear")
            or "mobil shc" in product_name
        ):
            return "I"
        return "T"
    if "transmission-oils" in categories:
        return "T"
    if categories & {
        "diesel-engine-oils", "gasoline-engine-oils",
        "outboard-motorcycle-oils",
    }:
        return "M"
    raise RuntimeError(f"Unclassified Sol Grenada row: {row!r}")


def product_identity(row: dict) -> tuple:
    technical = row["technical"]
    return (
        row["brand"],
        row["product_name"].casefold(),
        family_code(row),
        tuple(technical["sae_engine"]),
        tuple(technical["sae_gear"]),
        tuple(technical["iso_vg"]),
        tuple(technical["nlgi"]),
        tuple(technical["api"]),
        tuple(technical["api_gl"]),
        tuple(technical["acea"]),
        tuple(technical["ilsac"]),
        tuple(technical["jaso"]),
    )


def grouped_products(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[product_identity(row)].append(row)
    products = []
    for identity, sku_rows in sorted(groups.items(), key=lambda item: item[0]):
        sku_rows.sort(key=lambda row: row["source_product_code"])
        representative = sku_rows[0]
        identity_payload = json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
        )
        group_id = hashlib.sha256(identity_payload.encode()).hexdigest()[:16]
        products.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"SOL-GD-PRODUCT-{group_id.upper()}",
            "market": "Grenada",
            "brand": representative["brand"],
            "product_name": representative["product_name"],
            "family_code": family_code(representative),
            "technical": representative["technical"],
            "source_sku_record_ids": [
                row["source_record_id"] for row in sku_rows
            ],
            "source_product_codes": [
                row["source_product_code"] for row in sku_rows
            ],
            "source_listing_titles": [
                row["source_listing_title"] for row in sku_rows
            ],
            "source_urls": sorted({
                row["source_url"] for row in sku_rows
            }),
            "sku_count": len(sku_rows),
            "published_specification_items": sorted({
                item
                for row in sku_rows
                for item in row["published_specification_items"]
            }),
            "snapshot_date": str(date.today()),
            "lifecycle_status": "current_country_ecommerce_product_identity",
            "source_quality_flags": [
                "country_ecommerce_package_skus_collapsed_by_professional_identity",
                "source_reported_specifications_not_independent_approvals",
                "no_global_mobil_range_inference",
            ],
        })
    return products


def main() -> None:
    listings: dict[str, dict] = {}
    category_counts = {}
    category_page_hashes = {}
    for slug in CATEGORY_SLUGS:
        url = urljoin(BASE_URL, slug)
        page = fetch(url).decode("utf-8", errors="replace")
        category_projection = []
        cards = re.findall(
            r'<div class="ejs-productitem.*?(?=<div class="ejs-productitem|'
            r'</form>)',
            page,
            re.I | re.S,
        )
        count = 0
        for card in cards:
            tracking = re.search(
                r"TrackingEvent\.addProductData\('[^']+', (\{.*?\})\);",
                card,
                re.S,
            )
            path = re.search(r'data-product-url="([^"]+)"', card)
            if not tracking or not path:
                continue
            raw = json.loads(tracking.group(1))
            code = raw["Code"]
            availability = first_match(
                r'productListing-availability-label[^>]*>'
                r".*?Availability:\s*([^<]+)",
                card,
            )
            count += 1
            category_projection.append({
                "code": code,
                "title": raw["Title"],
                "brand": raw["Brand"],
                "price": raw.get("Price"),
                "currency": raw.get("Currency", ""),
                "availability": normalize_availability(availability),
                "detail_path": path.group(1),
            })
            row = listings.setdefault(code, {
                "code": code,
                "title": raw["Title"],
                "brand": raw["Brand"],
                "price": raw.get("Price"),
                "currency": raw.get("Currency", ""),
                "availability": normalize_availability(availability),
                "categories": set(),
                "detail_paths": [],
            })
            assert row["title"] == raw["Title"]
            assert row["brand"] == raw["Brand"]
            row["categories"].add(slug)
            row["detail_paths"].append(path.group(1))
        category_counts[slug] = count
        category_page_hashes[slug] = hashlib.sha256(
            json.dumps(
                sorted(category_projection, key=lambda item: item["code"]),
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

    rows = []
    failed = {}
    for code in sorted(listings):
        listing = listings[code]
        payload = None
        selected_url = ""
        attempted = []
        for path in listing.pop("detail_paths"):
            for url in detail_candidates(path):
                if url in attempted:
                    continue
                attempted.append(url)
                try:
                    payload = fetch(url)
                    selected_url = url
                    break
                except RuntimeError as error:
                    if "HTTP 404" not in str(error):
                        raise
            if payload is not None:
                break
        if payload is None:
            failed[code] = attempted
            continue
        listing["detail_url"] = selected_url
        rows.append(parse_detail(payload, listing))

    assert not failed, failed
    assert len(rows) == len(listings)
    assert len({row["source_product_code"] for row in rows}) == len(rows)
    rendered = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )
    OUT.write_text(rendered, encoding="utf-8")
    products = grouped_products(rows)
    products_rendered = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in products
    )
    PRODUCTS_OUT.write_text(products_rendered, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": BASE_URL,
        "snapshot_date": str(date.today()),
        "category_pages_checked": len(CATEGORY_SLUGS),
        "category_listing_occurrences": sum(category_counts.values()),
        "category_listing_occurrences_by_category": category_counts,
        "unique_skus": len(rows),
        "unique_product_grade_identities": len(products),
        "product_grade_identities_by_family": dict(sorted(Counter(
            row["family_code"] for row in products
        ).items())),
        "package_skus_collapsed_by_identity": len(rows) - len(products),
        "identity_groups_with_multiple_package_skus": sum(
            row["sku_count"] > 1 for row in products
        ),
        "brands": dict(sorted(Counter(row["brand"] for row in rows).items())),
        "availability": dict(sorted(
            Counter(row["availability"] for row in rows).items()
        )),
        "priced_skus": sum(
            row["price_status"] == "published_current_price" for row in rows
        ),
        "zero_price_placeholder_skus": sum(
            row["price_status"] == "zero_price_placeholder_without_currency"
            for row in rows
        ),
        "currency": sorted({
            row["price_currency"] for row in rows if row["price_currency"]
        }),
        "skus_with_structured_specifications": sum(
            any(row["technical"].values()) for row in rows
        ),
        "detail_json_ld_statuses": dict(sorted(Counter(
            row["detail_json_ld_status"] for row in rows
        ).items())),
        "category_page_sha256": category_page_hashes,
        "normalized_output_sha256": hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest(),
        "normalized_products_sha256": hashlib.sha256(
            products_rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "All published lubricant leaf categories and product SKUs were "
            "checked. Package SKUs are retained as offers/evidence and grouped "
            "into product-grade identities; no global Mobil range inference."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
