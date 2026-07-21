#!/usr/bin/env python3
"""Ingest current LIQUI MOLY product facts through its public search API.

The manufacturer publishes both the API endpoint and its read token in the
current Oils page.  Product identifiers come from the official GB/English XML
sitemap, so the collector does not have to crawl paginated category pages.
Only factual fields are retained; descriptions and images are deliberately
discarded.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/liqui-moly-current-products.jsonl"
REPORT = ROOT / "data/liqui-moly-current-products-report.json"
LIFECYCLE = ROOT / "data/liqui-moly-2020-2026-lifecycle.jsonl"
HISTORICAL = ROOT / "data/liqui-moly-2020-products.jsonl"
CACHE = Path("/tmp/liqui-moly-current-api-facts.json")
LANDING_URL = "https://www.liqui-moly.com/en/gb/oils.html"
SITEMAP_URL = "https://www.liqui-moly.com/sitemap/www.liqui-moly.com/sitemap_gb_en.xml"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"


def fetch(url: str, headers: dict[str, str] | None = None, attempts: int = 4) -> bytes:
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as exc:  # network retries are part of reproducible collection
            error = exc
            if attempt + 1 < attempts:
                time.sleep(0.4 * (2**attempt))
    raise RuntimeError(f"failed to fetch {url}") from error


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(value).casefold()).strip()


def clean_text(value) -> str:
    """Normalize an API scalar without trusting its occasionally mixed type."""
    return html.unescape(value).strip() if isinstance(value, str) else ""


def clean_list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [clean_text(item) for item in value if clean_text(item)]


def official_contract() -> tuple[str, str, bytes, bytes]:
    landing = fetch(LANDING_URL)
    page = landing.decode("utf-8", "replace")
    api_match = re.search(r'"apiUrl":"([^"]+)"', page)
    token_match = re.search(r'"authToken":"([^"]+)"', page)
    if not api_match or not token_match:
        raise RuntimeError("LIQUI MOLY public API contract was not found on the Oils page")
    api_url = api_match.group(1).replace(r"\/", "/")
    sitemap = fetch(SITEMAP_URL)
    return api_url, token_match.group(1), landing, sitemap


def sitemap_products(payload: bytes) -> list[dict]:
    root = ET.fromstring(payload)
    ns = {
        "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "image": "http://www.google.com/schemas/sitemap-image/1.1",
    }
    rows = []
    for entry in root.findall("s:url", ns):
        loc = entry.findtext("s:loc", namespaces=ns) or ""
        match = re.search(r"-p(\d{6})\.html$", loc)
        if not match:
            continue
        title = entry.findtext("image:image/image:title", namespaces=ns) or ""
        rows.append({"master_sku": f"P{match.group(1)}", "source_url": loc, "sitemap_title": html.unescape(title)})
    rows.sort(key=lambda row: row["master_sku"])
    return rows


def api_product(api_url: str, token: str, source: dict) -> dict:
    url = api_url + urllib.parse.quote(source["master_sku"]) + "/"
    payload = fetch(url, {
        "Accept": "application/json",
        "Authorization": "Basic " + token,
        "X-Requested-With": "XMLHttpRequest",
    })
    result = json.loads(payload)
    product = result.get("masterProduct")
    if not isinstance(product, dict) or product.get("sku") != source["master_sku"]:
        return {**source, "api_unresolved": True}
    return {
        **source,
        "product_name": clean_text(product.get("title")) or source["sitemap_title"],
        "specifications": clean_list(product.get("specifications")),
        "approvals": clean_list(product.get("approvals")),
        "recommendations": clean_list(product.get("recommendations")),
        "articles": sorted([
            {
                "sku": str(article.get("sku") or "").strip(),
                "content": html.unescape(str(article.get("content") or "")).strip(),
                "container_type": html.unescape(str(article.get("contentType") or "")).strip(),
                "language_line": html.unescape(str(article.get("languageLine") or "")).strip(),
            }
            for article in product.get("articleSku") or []
            if article.get("sku")
        ], key=lambda row: (row["sku"], row["content"], row["container_type"])),
    }


def historical_families() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    families: dict[str, set[str]] = {}
    article_families: dict[str, set[str]] = {}
    for line in HISTORICAL.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        families.setdefault(normalize(row["product_name"]), set()).add(row["family_code"])
        for part_number in row["part_numbers"]:
            article_families.setdefault(str(part_number), set()).add(row["family_code"])
    return families, article_families


def family_for(row: dict, historical: dict[str, set[str]], historical_articles: dict[str, set[str]]) -> tuple[str, str]:
    title = normalize(row["product_name"])
    facts = normalize(" ".join(row["specifications"] + row["approvals"] + row["recommendations"]))
    text = f"{title} {facts}"
    old = historical.get(title, set())
    if len(old) == 1:
        return next(iter(old)), "exact_historical_product_name"
    old_article_families = {
        family
        for article in row["articles"]
        for family in historical_articles.get(article["sku"], set())
    }
    if len(old_article_families) == 1:
        return next(iter(old_article_families)), "historical_article_sku_overlap"

    if re.search(r"\b(?:compressor|air compressor|refrigeration) oil\b", title):
        return "C", "current_title_compressor_oil"
    if re.search(r"\b(?:hydraulic|central hydraulic|power steering|liftgate|fork oil|shock absorber oil)\b", title):
        return "H", "current_title_hydraulic_fluid"
    if re.search(r"\b(?:gear oil|transmission oil|automatic transmission|dual clutch|dct|cvt|atf|hypoid|differential oil|axle oil|gearbox oil)\b", title) or re.search(r"\bapi gl [1-6]\b", facts):
        return "T", "current_title_or_fact_transmission_oil"
    if re.search(r"\b(?:engine oil|motor oil|motoroil|2 stroke oil|2t motor|4t motor|lawnmower oil|marine.*oil)\b", title) or re.search(r"\b(?:acea [abce][0-9]|api (?:sq|sp|sn|sm|sl|sj|ck 4|cj 4|ci 4|ch 4))\b", facts):
        return "M", "current_title_or_fact_engine_oil"
    if re.search(r"(?<![0-9])(?:0|5|10|15|20|25)w(?: |-|)[0-9]{1,2}(?![0-9])", title) or re.search(r"\b(?:motor bike 2t|motor bike 4t|hd classic sae|hd synth)\b", title):
        return "M", "current_title_engine_sae_grade"
    if re.search(r"\b(?:grease|paste|anti seize|fitting grease|bearing grease|lubricating grease)\b", title):
        return "G", "current_title_grease_or_paste"
    if re.search(r"\b(?:chain oil|saw chain oil|vacuum pump oil|machine oil|spindle oil|circulating oil|turbine oil)\b", title):
        return "U" if "turbine oil" in title else "I", "current_title_industrial_oil"
    if re.search(r"\b(?:gun oil|contact oil|chain spray|tacky lube|maintenance spray|multispray|ceramic longlife spray)\b", title):
        return "I", "current_title_specialty_lubricant"
    if re.search(r"\b(?:ceramic powder spray|treatment spray for garden equipment)\b", title):
        return "I", "current_title_specialty_lubricant"
    if re.search(r"\b(?:pro line ceramic spray)\b", title):
        return "G", "current_title_grease_or_paste"
    if re.search(r"\b(?:pag air conditioning oil|air conditioning oil)\b", title):
        return "C", "current_title_refrigeration_oil"
    if re.search(r"\b(?:foam filter oil|filter oil)\b", title):
        return "TF", "current_title_filter_fluid"
    if re.search(r"\b(?:coolant|antifreeze|anti freeze|brake fluid|radiator|def additive|adblue)\b", title):
        return "TF", "current_title_cooling_or_technical_fluid"
    if re.search(r"\b(?:oil additive|gear protect|cera tec|motor protect|viscoplus|oil smoke stop|oil loss stop|hydraulic lifter additive|atf additive|friction modifier|speed tec|super kote|mos2)\b", title):
        return "S", "current_title_lubricant_additive"
    if re.search(r"\b(?:additive|fuel protect|fuel system treatment|diesel flow fit|diesel smoke stop|diesel purge|engine wear protector|oil treatment|engine preserver|motor conserve|octane booster|petrol stabilizer|gasoline stabilizer|lead substitute|valve protection|diesel particulate filter protector|dfi cleaner)\b", title):
        return "S", "current_title_fuel_or_service_additive"
    if re.search(r"\b(?:engine flush|engine clean|motor clean|engine compartment cleaner|gearbox interior cleaner|transmission cleaner|brake and parts cleaner|brake and chain cleaner|rapid cleaner|a c system cleaner|air conditioner system cleaner|carburetor and valve cleaner|carburetor housing cleaner|catalytic system clean|catalytic system cleaner|dpf cleaner|dpf gpf cleaner|particulate filter cleaner|particulate filter purge|injection cleaner|injector.*cleaner|gasoline engine system cleaner|gasoline system cleaner|diesel system cleaner|fuel system cleaner|intake system cleaner|throttle valve cleaner|guntec.*cleaner|electronic spray|cleaner and thinner|universal cleaner)\b", title):
        return "TF", "current_title_technical_cleaner_or_flush"
    if re.search(r"\b(?:top tec gear|top tec mtf)\b", title):
        return "T", "current_title_transmission_product"
    if re.search(r"\b(?:lubricant|lubricating|chain lube|multi purpose spray|penetrating oil|silicone spray|ptfe powder spray|gun grease|tire fitting spray)\b", title):
        return "I", "current_title_lubricating_specialty"
    return "", "outside_lubricants_and_technical_fluids_scope"


def technical(row: dict) -> dict:
    facts = " ".join([row["product_name"], *row["specifications"], *row["approvals"], *row["recommendations"]]).upper().replace("–", "-")
    sae = sorted(set(re.findall(r"(?<![0-9])((?:0|5|10|15|20|25)W[- ]?[0-9]{1,2}|(?:70|75|80|85)W(?:[- ]?[0-9]{2,3})?)(?![0-9])", facts)))
    api = sorted(set(re.findall(r"\bAPI\s+([A-Z]{1,2}(?:-[0-9])?)\b", facts)))
    acea = sorted(set(re.findall(r"\bACEA\s+([A-Z][0-9](?:/[A-Z][0-9])?)\b", facts)))
    iso_vg = sorted(set(re.findall(r"\bISO(?:\s+VG)?\s*([0-9]{1,4})\b", facts)), key=int)
    return {
        "sae_grades": [value.replace(" ", "-") for value in sae],
        "api": api,
        "acea": acea,
        "iso_vg": iso_vg,
    }


def main() -> None:
    api_url, token, landing, sitemap = official_contract()
    source_rows = sitemap_products(sitemap)
    cached = []
    if CACHE.exists():
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
    if [row.get("master_sku") for row in cached] == [row["master_sku"] for row in source_rows]:
        products = cached
        print(f"reused {len(products)} cached API facts", flush=True)
    else:
        products = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(api_product, api_url, token, row) for row in source_rows]
            for index, future in enumerate(futures, 1):
                products.append(future.result())
                if index % 100 == 0:
                    print(f"fetched {index}/{len(futures)}", flush=True)
        CACHE.write_text(json.dumps(products, ensure_ascii=False), encoding="utf-8")

    historical, historical_articles = historical_families()
    records = []
    excluded = []
    for row in products:
        if row.get("api_unresolved"):
            excluded.append({"master_sku": row["master_sku"], "product_name": row["sitemap_title"], "reason": "sitemap_product_not_resolved_by_current_api"})
            continue
        family, basis = family_for(row, historical, historical_articles)
        if not family:
            excluded.append({"master_sku": row["master_sku"], "product_name": row["product_name"], "reason": basis})
            continue
        record = {
            "source_id": "LIQUI_MOLY_CURRENT_OPENAPI",
            "source_record_id": row["master_sku"],
            "manufacturer": "LIQUI MOLY GmbH",
            "brand": "LIQUI MOLY",
            "product_name": row["product_name"],
            "family_code": family,
            "market": "GB_EN",
            "lifecycle_status": "listed_as_of_current_official_catalog",
            "master_sku": row["master_sku"],
            "articles": row["articles"],
            "specifications": row["specifications"],
            "approvals": row["approvals"],
            "recommendations": row["recommendations"],
            "technical": technical(row),
            "classification_basis": basis,
            "source_url": row["source_url"],
            "sitemap_url": SITEMAP_URL,
            "api_base_url": api_url,
            "snapshot_date": SNAPSHOT_DATE,
        }
        records.append(record)
    records.sort(key=lambda row: (normalize(row["product_name"]), row["family_code"], row["master_sku"]))
    excluded.sort(key=lambda row: (normalize(row["product_name"]), row["master_sku"]))
    historical_rows = [json.loads(line) for line in HISTORICAL.read_text(encoding="utf-8").splitlines() if line]
    historical_by_id = {row["source_record_id"]: row for row in historical_rows}
    historical_name_ids: dict[str, set[str]] = {}
    historical_article_ids: dict[str, set[str]] = {}
    for historical_row in historical_rows:
        historical_name_ids.setdefault(normalize(historical_row["product_name"]), set()).add(historical_row["source_record_id"])
        for article_sku in historical_row["part_numbers"]:
            historical_article_ids.setdefault(str(article_sku), set()).add(historical_row["source_record_id"])

    lifecycle_rows = []
    linked_historical_ids = set()
    lifecycle_counts = Counter()
    for row in records:
        exact_name_ids = historical_name_ids.get(normalize(row["product_name"]), set())
        article_skus = {article["sku"] for article in row["articles"]}
        shared_article_ids = {
            historical_id
            for article_sku in article_skus
            for historical_id in historical_article_ids.get(article_sku, set())
        }
        candidate_ids = sorted(exact_name_ids | shared_article_ids)
        candidates = []
        for historical_id in candidate_ids:
            historical_row = historical_by_id[historical_id]
            candidates.append({
                "source_record_id": historical_id,
                "product_name": historical_row["product_name"],
                "family_code": historical_row["family_code"],
                "exact_normalized_name": historical_id in exact_name_ids,
                "shared_article_skus": sorted(article_skus & set(historical_row["part_numbers"]), key=int),
            })
        if not candidates:
            assessment = "current_not_observed_in_2020_catalog"
        elif len(candidates) > 1:
            assessment = "review_multiple_historical_candidates"
        elif candidates[0]["exact_normalized_name"]:
            assessment = "current_exact_name_continuity_from_2020"
        else:
            assessment = "current_possible_rename_or_reformulation_shared_article_sku"
        row["historical_candidates"] = candidates
        row["lifecycle_assessment"] = assessment
        linked_historical_ids.update(candidate_ids)
        lifecycle_counts[assessment] += 1
        lifecycle_rows.append({
            "record_type": "current_product_assessment",
            "current_master_sku": row["master_sku"],
            "current_product_name": row["product_name"],
            "current_family_code": row["family_code"],
            "assessment": assessment,
            "historical_candidates": candidates,
            "source_url": row["source_url"],
        })
    for historical_row in historical_rows:
        if historical_row["source_record_id"] not in linked_historical_ids:
            lifecycle_rows.append({
                "record_type": "historical_product_not_observed_current",
                "historical_source_record_id": historical_row["source_record_id"],
                "historical_product_name": historical_row["product_name"],
                "historical_family_code": historical_row["family_code"],
                "assessment": "not_observed_in_current_2026_gb_catalog_not_proof_discontinued",
                "source_url": historical_row["source_url"],
                "source_pages": historical_row["source_pages"],
            })
    lifecycle_rows.sort(key=lambda row: (row["record_type"], normalize(row.get("current_product_name") or row.get("historical_product_name") or "")))
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    LIFECYCLE.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in lifecycle_rows), encoding="utf-8")
    current_names = {normalize(row["product_name"]) for row in records}
    historical_names = set(historical)
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": "LIQUI_MOLY_CURRENT_OPENAPI",
        "landing_url": LANDING_URL,
        "sitemap_url": SITEMAP_URL,
        "api_base_url": api_url,
        "landing_sha256": hashlib.sha256(landing).hexdigest(),
        "sitemap_sha256": hashlib.sha256(sitemap).hexdigest(),
        "sitemap_master_products": len(source_rows),
        "api_master_products_fetched": sum(not row.get("api_unresolved") for row in products),
        "sitemap_products_unresolved_by_api": sum(bool(row.get("api_unresolved")) for row in products),
        "lubricant_and_technical_fluid_products": len(records),
        "excluded_non_scope_products": len(excluded),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "classification_basis": dict(sorted(Counter(row["classification_basis"] for row in records).items())),
        "unique_article_skus": len({article["sku"] for row in records for article in row["articles"]}),
        "products_with_articles": sum(bool(row["articles"]) for row in records),
        "exact_name_overlap_with_2020": len(current_names & historical_names),
        "historical_names_not_in_current_scope": len(historical_names - current_names),
        "current_names_not_in_2020": len(current_names - historical_names),
        "lifecycle_assessments": dict(sorted(lifecycle_counts.items())),
        "historical_products_linked_to_current": len(linked_historical_ids),
        "historical_products_not_observed_current": len(historical_rows) - len(linked_historical_ids),
        "lifecycle_rows": len(lifecycle_rows),
        "lifecycle_output_sha256": hashlib.sha256(LIFECYCLE.read_bytes()).hexdigest(),
        "excluded_products": excluded,
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Current product identity, family, approvals, recommendations, master/article SKUs and package facts; marketing descriptions and images are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "excluded_products"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
