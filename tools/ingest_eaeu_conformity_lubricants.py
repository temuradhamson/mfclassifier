#!/usr/bin/env python3
"""Normalize product-level lubricant evidence from the official EAEU registry.

The source is an open-data conformity-document register, not a manufacturer
catalog.  A record is promoted only when a product detail contains a specific
marketed designation or grade.  Generic declarations such as "motor oils in
assortment" remain counted in the audit report but do not become products.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "eaeu-conformity-lubricant-products.jsonl"
REPORT = ROOT / "data" / "eaeu-conformity-lubricant-products-report.json"
CACHE = ROOT / ".cache" / "eaeu-conformity-lubricants"
SOURCE_ID = "EAEU_CONFORMITY_LUBRICANT_PRODUCTS"
SOURCE_URL = "https://tech.eaeunion.org/tech/registers/35-1"
RIGHTS_URL = "https://opendata.eaeunion.org/opendata/ru/api/apiodata"
ODATA_URL = "https://tech.eaeunion.org/odata/ConformityDocDetailsType"
REST_URL = "https://tech.eaeunion.org/spd2/find"
REST_COLLECTION = "kbdallread.service-prop-35_1-conformityDocDetailsType"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (official-open-data-lubricant-registry)"
ID_BATCH_SIZE = 250
DETAIL_BATCH_SIZE = 40
DEFAULT_WORKERS = 4

# Exact 10-digit commodity codes observed in the register for the regulated
# lubricant / technical-fluid scope.  Exact-code queries use the registry's
# index and avoid the pathological deep-$skip behaviour of text search.
COMMODITY_CODES = (
    "2710198100",
    "2710198200",  # motor, compressor and turbine lubricating oils
    "2710198300",
    "2710198400",  # hydraulic-purpose fluids
    "2710198700",
    "2710198800",  # gear and reduction-gear oils
    "2710199100",
    "2710199400",  # electrical insulating oils
    "2710199800",  # other lubricating and other oils
    "2710199900",
    "3403110000",
    "3403191000",
    "3403199000",
    "3403910000",
    "3403990000",  # other lubricating preparations
    "3819000000",  # hydraulic brake and transmission fluids
    "3820000000",  # antifreeze and prepared de-icing fluids
)

COMMODITY_CODE_FIELDS = (
    "technicalRegulationObjectDetails.productDetails.commodityCode",
)

# Russian is the register language.  English terms cover source-entered trade
# designations and make the crawl resilient to future national submissions.
SEARCH_TERMS = (
    "моторн",
    "трансмиссионн",
    "гидравлическ",
    "компрессорн",
    "турбинн",
    "трансформаторн",
    "редукторн",
    "циркуляционн",
    "пластичн",
    "консистентн",
    "антифриз",
    "охлаждающ",
    "тормозн",
    "engine oil",
    "motor oil",
    "gear oil",
    "hydraulic oil",
    "lubricating oil",
    "grease",
    "coolant",
    "antifreeze",
    "brake fluid",
    " atf",
)

DETAIL_FIELDS = (
    "docId",
    "docCreationDate",
    "docStartDate",
    "docValidityDate",
    "unifiedCountryCode.value",
    "conformityDocKindCode",
    "conformityDocKindName",
    "technicalRegulationId",
    "docStatusDetails.docStatusCode",
    "resourceItemStatusDetails.validityPeriodDetails",
    "technicalRegulationObjectDetails.productDetails.productName",
    "technicalRegulationObjectDetails.productDetails.productTradeName",
    "technicalRegulationObjectDetails.productDetails.productText",
    "technicalRegulationObjectDetails.productDetails.additionalInfoText",
    "technicalRegulationObjectDetails.productDetails.commodityCode",
    "technicalRegulationObjectDetails.productDetails.productInstanceDetails.productName",
    "technicalRegulationObjectDetails.productDetails.productInstanceDetails.productText",
    "technicalRegulationObjectDetails.productDetails.productInstanceDetails.commodityCode",
    "technicalRegulationObjectDetails.manufacturerDetails.businessEntityName",
    "complianceProvidingDocDetails.docName",
)

RELEVANT_CODE_PREFIXES = (
    "2710198",  # compressor, motor, hydraulic and other lubricating oils
    "2710199",  # other petroleum oils, retained only with a strong name
    "3403",     # lubricating preparations
    "3819",     # hydraulic brake/transmission fluids
    "3820",     # antifreeze and prepared de-icing fluids
)

GENERIC_NAMES = {
    "масло",
    "масла",
    "масло моторное",
    "масла моторные",
    "моторное масло",
    "моторные масла",
    "масло трансмиссионное",
    "масла трансмиссионные",
    "трансмиссионное масло",
    "трансмиссионные масла",
    "масло гидравлическое",
    "масла гидравлические",
    "гидравлическое масло",
    "гидравлические масла",
    "смазка",
    "смазки",
    "пластичная смазка",
    "пластичные смазки",
    "смазочные материалы",
    "антифриз",
    "антифризы",
    "охлаждающая жидкость",
    "охлаждающие жидкости",
    "тормозная жидкость",
    "тормозные жидкости",
    "engine oil",
    "motor oil",
    "gear oil",
    "hydraulic oil",
    "lubricating oil",
    "grease",
    "coolant",
    "antifreeze",
    "brake fluid",
    "-",
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n;,.")


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", clean(value)).casefold().replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я]+", " ", text).strip()


def source_date(value: object) -> str:
    if isinstance(value, dict):
        value = value.get("$date")
    return clean(value)[:10]


def safe_slug(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def odata_id_url(term: str, skip: int) -> str:
    escaped = term.replace("'", "''")
    expression = (
        "technicalRegulationObjectDetails/productDetails/any(p:"
        "p/productName ne null and contains(tolower(p/productName),"
        f"'{escaped}'))"
    )
    query = urllib.parse.urlencode(
        {
            "$top": ID_BATCH_SIZE,
            "$skip": skip,
            "$select": "Id",
            "$filter": expression,
        }
    )
    return f"{ODATA_URL}?{query}"


def fetch_id_page(term: str, skip: int) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"ids-b{ID_BATCH_SIZE}-{safe_slug(term)}-{skip:07d}.json"
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(odata_id_url(term, skip), headers={"User-Agent": USER_AGENT})
    error: Exception | None = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=150) as response:
                payload = response.read()
            parsed = json.loads(payload)
            if not isinstance(parsed.get("value"), list):
                raise RuntimeError(parsed.get("error") or parsed.get("Message") or "invalid OData response")
            path.write_bytes(payload)
            time.sleep(0.18)
            return payload
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            error = exc
            time.sleep(min(20, 2 * (attempt + 1)))
    raise RuntimeError(f"EAEU OData failed for {term!r}, skip={skip}: {error}")


def rest_detail_url(limit: int) -> str:
    fields = json.dumps({name: 1 for name in DETAIL_FIELDS}, ensure_ascii=False, separators=(",", ":"))
    query = urllib.parse.urlencode({"collection": REST_COLLECTION, "limit": limit, "fields": fields})
    return f"{REST_URL}?{query}"


def rest_id_url(limit: int) -> str:
    fields = json.dumps({"_id": 1}, separators=(",", ":"))
    query = urllib.parse.urlencode({"collection": REST_COLLECTION, "limit": limit, "fields": fields})
    return f"{REST_URL}?{query}"


def fetch_code_id_page(code: str, field: str, after_id: str) -> bytes:
    """Fetch one exact-code page using indexed ObjectId keyset pagination."""
    CACHE.mkdir(parents=True, exist_ok=True)
    slice_id = safe_slug(f"{field}|{code}")
    cursor = after_id or "start"
    path = CACHE / f"code-ids-b{ID_BATCH_SIZE}-{slice_id}-{cursor}.json"
    if path.exists():
        return path.read_bytes()
    clauses = [f"{{{json.dumps(field)}:{json.dumps(code)}}}"]
    if after_id:
        clauses.append(f'{{"_id":{{"$gt":ObjectId({json.dumps(after_id)})}}}}')
    # The public service accepts Mongo-like literals, so ObjectId must remain
    # unquoted while ordinary values remain JSON escaped.
    body = ('{"$and":[' + ",".join(clauses) + "]}").encode("utf-8")
    request = urllib.request.Request(
        rest_id_url(ID_BATCH_SIZE),
        data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "text/plain"},
        method="POST",
    )
    error: Exception | None = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            parsed = json.loads(payload)
            rows = parsed.get("result")
            if not isinstance(rows, list):
                raise RuntimeError(parsed.get("message") or "invalid REST code response")
            ids = [clean((row.get("_id") or {}).get("$oid")) for row in rows]
            if any(not value for value in ids) or ids != sorted(ids):
                raise RuntimeError("REST code page omitted an ObjectId or broke ascending keyset order")
            path.write_bytes(payload)
            time.sleep(0.08)
            return payload
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            error = exc
            time.sleep(min(20, 2 * (attempt + 1)))
    raise RuntimeError(f"EAEU REST code query failed for {field}={code}, after={after_id or 'start'}: {error}")


def fetch_detail_batch(record_ids: list[str]) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    identity = "\n".join(sorted(record_ids))
    path = CACHE / f"details-{safe_slug(identity)}-{len(record_ids):03d}.json"
    if path.exists():
        return path.read_bytes()
    object_ids = ",".join(f'ObjectId("{value}")' for value in record_ids)
    body = f'{{"_id":{{"$in":[{object_ids}]}}}}'.encode("utf-8")
    request = urllib.request.Request(
        rest_detail_url(len(record_ids)),
        data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "text/plain"},
        method="POST",
    )
    error: Exception | None = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=150) as response:
                payload = response.read()
            parsed = json.loads(payload)
            if not isinstance(parsed.get("result"), list):
                raise RuntimeError(parsed.get("message") or "invalid REST response")
            path.write_bytes(payload)
            time.sleep(0.12)
            return payload
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            error = exc
            time.sleep(min(20, 2 * (attempt + 1)))
    raise RuntimeError(f"EAEU REST detail batch failed: {error}")


def crawl_term_ids(term: str, max_pages: int) -> dict:
    """Fetch one search slice; every raw page is an independent checkpoint."""
    record_ids: set[str] = set()
    page_hashes: list[str] = []
    matched = 0
    pages = 0
    skip = 0
    truncated = False
    while True:
        payload = fetch_id_page(term, skip)
        page_hashes.append(hashlib.sha256(payload).hexdigest())
        rows = json.loads(payload)["value"]
        for row in rows:
            record_ids.add(row["Id"])
        matched += len(rows)
        pages += 1
        print(
            json.dumps(
                {"term": term, "page": pages, "rows": len(rows), "matched": matched, "term_unique_ids": len(record_ids)},
                ensure_ascii=False,
            ),
            flush=True,
        )
        if len(rows) < ID_BATCH_SIZE:
            break
        if max_pages and pages >= max_pages:
            truncated = True
            break
        skip += ID_BATCH_SIZE
    return {
        "term": term,
        "record_ids": sorted(record_ids),
        "matched": matched,
        "pages": pages,
        "truncated": truncated,
        "page_hashes": page_hashes,
    }


def crawl_code_ids(code: str, field: str, max_pages: int) -> dict:
    """Fetch an exact commodity-code slice with stable ObjectId cursors."""
    record_ids: set[str] = set()
    page_hashes: list[str] = []
    matched_total = None
    pages = 0
    after_id = ""
    truncated = False
    while True:
        payload = fetch_code_id_page(code, field, after_id)
        parsed = json.loads(payload)
        page_hashes.append(hashlib.sha256(payload).hexdigest())
        rows = parsed["result"]
        ids = [clean((row.get("_id") or {}).get("$oid")) for row in rows]
        record_ids.update(ids)
        pages += 1
        if matched_total is None:
            matched_total = int(parsed.get("matchedDocuments") or len(rows))
        print(
            json.dumps(
                {
                    "commodity_code": code,
                    "commodity_field": field.rsplit(".", 1)[-1],
                    "page": pages,
                    "rows": len(rows),
                    "slice_unique_ids": len(record_ids),
                    "source_matches": matched_total,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if len(rows) < ID_BATCH_SIZE:
            break
        if max_pages and pages >= max_pages:
            truncated = True
            break
        next_after = ids[-1]
        if not next_after or next_after == after_id:
            raise RuntimeError(f"EAEU code keyset did not advance for {field}={code}")
        after_id = next_after
    return {
        "slice": f"{field}={code}",
        "record_ids": sorted(record_ids),
        "matched": matched_total or 0,
        "pages": pages,
        "truncated": truncated,
        "page_hashes": page_hashes,
    }


def fetch_detail_result(batch_ids: list[str]) -> tuple[list[str], bytes, list[dict]]:
    payload = fetch_detail_batch(batch_ids)
    return batch_ids, payload, json.loads(payload)["result"]


def crawl(
    terms: tuple[str, ...],
    max_pages: int,
    workers: int = DEFAULT_WORKERS,
    strategy: str = "codes",
) -> tuple[dict[str, dict], dict]:
    workers = max(1, workers)
    if strategy == "codes":
        slices = [(code, field) for code in COMMODITY_CODES for field in COMMODITY_CODE_FIELDS]
        jobs = [(f"{field}={code}", crawl_code_ids, (code, field, max_pages)) for code, field in slices]
    else:
        jobs = [(term, crawl_term_ids, (term, max_pages)) for term in terms]
    slice_results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(jobs))) as executor:
        futures = {executor.submit(function, *arguments): name for name, function, arguments in jobs}
        for future in as_completed(futures):
            result = future.result()
            slice_results[futures[future]] = result

    record_ids: set[str] = set()
    counts: dict[str, int] = {}
    pages_by_term: dict[str, int] = {}
    truncated_terms: list[str] = []
    page_hashes: list[str] = []
    for name, _, _ in jobs:
        result = slice_results[name]
        record_ids.update(result["record_ids"])
        counts[name] = result["matched"]
        pages_by_term[name] = result["pages"]
        page_hashes.extend(result["page_hashes"])
        if result["truncated"]:
            truncated_terms.append(name)

    documents: dict[str, dict] = {}
    ordered_ids = sorted(record_ids)
    batches = [ordered_ids[offset : offset + DETAIL_BATCH_SIZE] for offset in range(0, len(ordered_ids), DETAIL_BATCH_SIZE)]
    completed_rows = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_detail_result, batch): batch for batch in batches}
        for future in as_completed(futures):
            batch_ids, payload, rows = future.result()
            page_hashes.append(hashlib.sha256(payload).hexdigest())
            for row in rows:
                record_id = clean((row.get("_id") or {}).get("$oid"))
                if not record_id:
                    continue
                row["Id"] = record_id
                documents[record_id] = row
            completed_rows += len(batch_ids)
            if completed_rows % 1000 == 0 or completed_rows == len(ordered_ids):
                print(
                    json.dumps(
                        {"detail_rows": completed_rows, "detail_total": len(ordered_ids), "documents": len(documents)},
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
    missing_ids = sorted(record_ids - documents.keys())
    if missing_ids:
        raise RuntimeError(f"REST projection omitted {len(missing_ids)} requested documents; first={missing_ids[0]}")
    return documents, {
        "query_matches_by_term": counts,
        "query_pages_by_term": pages_by_term,
        "query_truncated_terms": truncated_terms,
        "crawl_strategy": strategy,
        "commodity_codes": list(COMMODITY_CODES) if strategy == "codes" else [],
        "commodity_code_fields": list(COMMODITY_CODE_FIELDS) if strategy == "codes" else [],
        "detail_projection_fields": list(DETAIL_FIELDS),
        "cached_response_manifest_sha256": hashlib.sha256("\n".join(sorted(page_hashes)).encode()).hexdigest(),
    }


def nested_codes(product: dict) -> list[str]:
    values = list(product.get("commodityCode") or [])
    for instance in product.get("productInstanceDetails") or []:
        values.extend(instance.get("commodityCode") or [])
    return sorted({re.sub(r"\D", "", clean(value)) for value in values if clean(value)})


def is_relevant_code(code: str) -> bool:
    return any(code.startswith(prefix) for prefix in RELEVANT_CODE_PREFIXES)


def strip_transaction_details(value: str) -> str:
    value = clean(value).replace("10W/", "10W-").replace("15W/", "15W-").replace("20W/", "20W-")
    value = re.sub(r"(?i)\b(?:дата\s+(?:изготовления|выпуска)|д/?и|срок\s+годности|с/?г)\b.*$", "", value)
    value = re.sub(r"(?i)[,;]\s*(?:фас\.?|упаковка|количество|партия)\b.*$", "", value)
    value = re.sub(r"(?i)[,;]\s*\d+\s*(?:канистр|бочек|банок|шт\.?|уп\.?|л\b|ml\b).*$", "", value)
    return clean(value)


def infer_family(text: str) -> tuple[str, str]:
    value = f" {normalize(text)} "
    rules = (
        ("TF", (" смазочно охлаждающ", " антифриз", " охлаждающ", " coolant ", " antifreeze ", " тормозн", " brake fluid ", " стеклоомыва")),
        ("G", (" смазка ", " смазки ", " пластич", " консистент", " grease ", " nlgi ", " литиев", " lithium grease ")),
        ("T", (" трансмиссион", " gear oil ", " transmission fluid ", " atf ", " dexron ", " gl 4 ", " gl 5 ", " редукторн")),
        ("H", (" гидравлическ", " hydraulic ", " hvlp ", " hlp ", " hv 32 ", " hm 46 ")),
        ("C", (" компрессорн", " compressor oil ", " refrigeration oil ")),
        ("U", (" турбинн", " turbine oil ")),
        ("E", (" трансформаторн", " insulating oil ", " transformer oil ", " электроизоляц")),
        ("M", (" моторн", " engine oil ", " motor oil ", " four stroke ", " two stroke ", " 4t ", " 2t ")),
        ("I", (" индустриальн", " industrial oil ", " циркуляционн", " slideway ", " spindle ", " cutting oil ", " metalworking ")),
    )
    for family, tokens in rules:
        token = next((item for item in tokens if item in value), None)
        if token:
            return family, f"product_text_rule:{token.strip()}"
    if re.search(r"(?<!\d)(?:0|5|10|15|20|25)W[- /]?\d{2}(?!\d)", text, re.I):
        return "M", "technical_rule:sae_engine"
    if re.search(r"(?<!\d)(?:70|75|80|85)W(?:[- /]?\d{2,3})?(?!\d)", text, re.I):
        return "T", "technical_rule:sae_gear"
    return "S", "generic_lubricant_requires_review"


def technical(text: str) -> dict:
    upper = clean(text).upper().replace("‐", "-").replace("–", "-")
    sae_engine = sorted(set(re.findall(r"(?<!\d)((?:0|5|10|15|20|25)W[- /]?\d{2})(?!\d)", upper)))
    sae_engine = [re.sub(r"W[- /]?", "W-", item) for item in sae_engine]
    sae_gear = sorted(set(re.findall(r"(?<!\d)((?:70|75|80|85)W(?:[- /]?\d{2,3})?)(?!\d)", upper)))
    sae_gear = [re.sub(r"W[- /]?", "W-", item) for item in sae_gear]
    api = sorted(set(re.findall(r"\bAPI\s*[:\-]?\s*(SP|SN\s*PLUS|SN|SM|SL|SJ|SH|SG|CK-?4|CJ-?4|CI-?4|CH-?4|CG-?4|CF-?4|CF)\b", upper)))
    api_gl = sorted({item.replace(" ", "-") for item in re.findall(r"\b(?:API\s+)?(GL[- ]?[1-6])\b", upper)})
    acea = sorted(set(re.findall(r"\bACEA\s*([ACE]\d(?:[-/]\d{2})?|A\d/B\d)\b", upper)))
    jaso = sorted(set(re.findall(r"\bJASO\s+(MA2|MA|MB|FB|FC|FD|DL-1|DH-1|DH-2)\b", upper)))
    iso_vg = sorted(set(re.findall(r"\bISO\s*(?:VG)?\s*(15|22|32|46|68|100|150|220|320|460|680|1000)\b", upper)), key=int)
    nlgi = sorted(set(re.findall(r"\bNLGI\s*(000|00|0|[1-6])\b", upper)))
    dot = sorted(set(re.findall(r"\bDOT\s*([345](?:\.1)?)\b", upper)))
    dexron = sorted(set(re.findall(r"\bDEXRON\s*(II|III|IV|VI|2|3|4|6)\b", upper)))
    return {
        key: value
        for key, value in {
            "sae_engine": sae_engine,
            "sae_gear": sae_gear,
            "api": api,
            "api_gl": api_gl,
            "acea": acea,
            "jaso": jaso,
            "iso_vg": iso_vg,
            "nlgi": nlgi,
            "brake_fluid_class": [f"DOT {item}" for item in dot],
            "atf_specifications": [f"Dexron {item}" for item in dexron],
        }.items()
        if value
    }


def explicit_brand(text: str) -> str:
    patterns = (
        r"(?i)\b(?:т\.?\s*м\.?|торгов(?:ая|ой)\s+марк(?:а|и)|марки)\s*[«\"']([^»\"']{2,80})[»\"']",
        r"(?i)\bbrand\s*[:\-]?\s*[«\"']?([A-Z0-9][A-Z0-9 .&+_-]{1,60})",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean(match.group(1))
    return ""


def specific_designation(value: str) -> bool:
    normal = normalize(value)
    if not normal or normal in GENERIC_NAMES:
        return False
    if any(token in normal for token in ("в ассортименте", "согласно приложению", "различных марок", "не указано", "нет данных")):
        return False
    if len(value) > 320 or value.count(";") > 4:
        return False
    if re.match(
        r"(?i)^(?:\d+(?:\.\d+)+\s+|условия\b|гост\b|номер\s+партии\b|штрих(?:овой)?\s+код\b|"
        r"определение\b|перечень\b|общие\s+сведения\b|изготовитель\b|срок\s+хранения\b)",
        value,
    ):
        return False
    category_hits = sum(
        bool(re.search(pattern, normal))
        for pattern in (
            r"моторн\w* масл|масл\w* моторн",
            r"трансмиссионн\w* масл|масл\w* трансмиссионн",
            r"гидравлическ\w* (?:масл|жидкост)|(?:масл|жидкост)\w* гидравлическ",
            r"компрессорн\w* масл|масл\w* компрессорн",
            r"пластичн\w* смаз|смаз\w* пластичн",
            r"консистентн\w* смаз|смаз\w* консистентн",
            r"охлаждающ\w* жидкост|жидкост\w* охлаждающ",
            r"тормозн\w* жидкост|жидкост\w* тормозн",
        )
    )
    if category_hits >= 2 and not technical(value):
        return False
    if re.search(r"(?i)\b(?:торгов(?:ой|ая)\s+марк(?:и|а)|trade\s*mark)\b", value) and not technical(value) and not re.search(r"(?i)\b(?:модель|тип|арт(?:икул)?\.?)\b", value):
        return False
    if re.match(r"(?i)^(?:жидкости\s+и\s+масла|масла\s+(?:моторные|трансмиссионные|гидравлические|компрессорные))\b", value) and not technical(value) and not re.search(r"[«\"'][^»\"']{3,}[»\"']", value):
        return False
    # A grade, standard, quoted mark, article, Latin model or non-generic
    # remainder makes the source designation product-level enough to retain.
    if technical(value):
        return True
    if re.search(r"[«\"'][^»\"']{2,}[»\"']|\b(?:арт(?:икул)?\.?|модель|тип)\b", value, re.I):
        return True
    latin_tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+._/-]{1,}\b", value)
    if latin_tokens:
        return True
    if re.search(r"\b(?=[0-9A-ZА-ЯЁ-]{3,}\b)(?=[0-9A-ZА-ЯЁ-]*\d)(?=[0-9A-ZА-ЯЁ-]*[A-ZА-ЯЁ])[0-9A-ZА-ЯЁ-]+\b", value):
        return True
    return False


def has_product_lexicon(value: str) -> bool:
    normal = f" {normalize(value)} "
    return any(
        token in normal
        for token in (
            "масло",
            "масла",
            "смазка",
            "смазки",
            "жидкость",
            "жидкости",
            "антифриз",
            "тосол",
            " oil ",
            " grease ",
            " fluid ",
            " coolant ",
            " antifreeze ",
            " lubricant ",
        )
    )


def lifecycle(row: dict) -> str:
    validity = source_date(row.get("docValidityDate"))
    if validity:
        try:
            return "certificate_active_at_snapshot" if date.fromisoformat(validity) >= date.fromisoformat(SNAPSHOT_DATE) else "certificate_expired_before_snapshot"
        except ValueError:
            pass
    return "certificate_date_unknown"


def card_url(record_id: str) -> str:
    return f"{SOURCE_URL}/ru/registryList/conformityDocs/view/{record_id}"


def normalize_documents(documents: dict[str, dict]) -> tuple[list[dict], dict]:
    candidates: list[dict] = []
    rejection_counts = Counter()
    family_counts = Counter()
    for record_id in sorted(documents):
        row = documents[record_id]
        technical_object = row.get("technicalRegulationObjectDetails") or {}
        manufacturers = [clean(item.get("businessEntityName")) for item in technical_object.get("manufacturerDetails") or []]
        manufacturers = [item for item in manufacturers if item and normalize(item) not in {"нет данных", "не указано"}]
        manufacturer_candidates = list(dict.fromkeys(manufacturers))
        manufacturer = manufacturer_candidates[0] if manufacturer_candidates else ""
        for product_index, product in enumerate(technical_object.get("productDetails") or [], 1):
            codes = nested_codes(product)
            main_name = strip_transaction_details(clean(product.get("productName")))
            alternatives = [main_name]
            alternatives.extend(strip_transaction_details(clean(item)) for item in product.get("productTradeName") or [])
            for instance in product.get("productInstanceDetails") or []:
                alternatives.append(strip_transaction_details(clean(instance.get("productName"))))
            alternatives = list(dict.fromkeys(item for item in alternatives if item))
            relevant_by_code = any(is_relevant_code(code) for code in codes)
            for designation in alternatives:
                context = " ".join(
                    [designation, main_name]
                    + [clean(item) for item in product.get("productTradeName") or []]
                    + [clean(product.get("productText")), clean(product.get("additionalInfoText"))]
                )
                family, family_basis = infer_family(context)
                relevant_by_name = has_product_lexicon(designation)
                if not relevant_by_code and not relevant_by_name:
                    rejection_counts["not_lubricant_scope"] += 1
                    continue
                if not relevant_by_name and not re.match(r"(?i)^(?:модель|марка|тип)\b", designation):
                    rejection_counts["non_product_text_with_relevant_code"] += 1
                    continue
                if not specific_designation(designation):
                    rejection_counts["generic_or_aggregated_designation"] += 1
                    continue
                if not manufacturer:
                    rejection_counts["manufacturer_missing"] += 1
                    continue
                brand = explicit_brand(context)
                brand_basis = "explicit_source_trademark" if brand else "manufacturer_holder_fallback"
                brand = brand or manufacturers[0]
                specs = technical(context)
                evidence = {
                    "record_id": row["Id"],
                    "document_number": clean(row.get("docId")),
                    "document_kind": clean(row.get("conformityDocKindName")),
                    "document_start_date": source_date(row.get("docStartDate")),
                    "document_validity_date": source_date(row.get("docValidityDate")),
                    "document_status_code": clean((row.get("docStatusDetails") or {}).get("docStatusCode")),
                    "document_country": clean((row.get("unifiedCountryCode") or {}).get("value")),
                    "source_url": card_url(row["Id"]),
                }
                candidates.append(
                    {
                        "manufacturer": manufacturer,
                        "manufacturer_candidates": manufacturer_candidates,
                        "brand": brand,
                        "brand_basis": brand_basis,
                        "product_name": designation,
                        "family_code": family,
                        "family_basis": family_basis,
                        "tnved_codes": codes,
                        "technical_regulations": sorted(set(row.get("technicalRegulationId") or [])),
                        "standards_and_evidence_documents": [clean(item.get("docName")) for item in row.get("complianceProvidingDocDetails") or [] if clean(item.get("docName"))],
                        "specifications": specs,
                        "evidence": evidence,
                        "lifecycle_status": lifecycle(row),
                        "source_product_index": product_index,
                    }
                )

    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for item in candidates:
        key = (
            normalize(item["manufacturer"]),
            normalize(item["brand"]),
            normalize(item["product_name"]),
            item["family_code"],
        )
        grouped[key].append(item)

    records = []
    duplicate_occurrences = 0
    for sequence, (key, occurrences) in enumerate(sorted(grouped.items()), 1):
        evidence_by_id = {item["evidence"]["record_id"]: item["evidence"] for item in occurrences}
        evidence = sorted(evidence_by_id.values(), key=lambda item: (item["document_start_date"], item["document_number"], item["record_id"]))
        duplicate_occurrences += len(occurrences) - 1
        tnved = sorted({code for item in occurrences for code in item["tnved_codes"]})
        regulations = sorted({code for item in occurrences for code in item["technical_regulations"]})
        standards = sorted({value for item in occurrences for value in item["standards_and_evidence_documents"]})
        merged_specs: dict[str, list] = defaultdict(list)
        for item in occurrences:
            for name, values in item["specifications"].items():
                merged_specs[name].extend(values)
        specs = {name: sorted(set(values)) for name, values in merged_specs.items()}
        latest = max(occurrences, key=lambda item: (item["evidence"]["document_start_date"], item["evidence"]["record_id"]))
        exemplar = latest
        identity = "|".join(map(str, key))
        source_record_id = "EAEU-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        record = {
            "source_id": SOURCE_ID,
            "source_record_id": source_record_id,
            "source_url": latest["evidence"]["source_url"],
            "source_registry_url": SOURCE_URL,
            "source_rights_url": RIGHTS_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "market": "EAEU",
            "manufacturer": exemplar["manufacturer"],
            "manufacturer_candidates": sorted({name for item in occurrences for name in item["manufacturer_candidates"]}),
            "brand": exemplar["brand"],
            "brand_basis": exemplar["brand_basis"],
            "product_name": exemplar["product_name"],
            "family_code": exemplar["family_code"],
            "family_basis": exemplar["family_basis"],
            "lifecycle_status": latest["lifecycle_status"],
            "tnved_codes": tnved,
            "technical_regulations": regulations,
            "standards_and_evidence_documents": standards,
            "specifications": specs,
            "certificate_occurrence_count": len(evidence),
            "certificate_evidence": evidence,
        }
        records.append(record)
        family_counts[record["family_code"]] += 1

    audit = {
        "candidate_occurrences": len(candidates),
        "deduplicated_product_rows": len(records),
        "duplicate_certificate_occurrences_merged": duplicate_occurrences,
        "families": dict(sorted(family_counts.items())),
        "rejections": dict(sorted(rejection_counts.items())),
        "explicit_brand_rows": sum(row["brand_basis"] == "explicit_source_trademark" for row in records),
        "manufacturer_holder_fallback_rows": sum(row["brand_basis"] == "manufacturer_holder_fallback" for row in records),
        "rows_with_tnved": sum(bool(row["tnved_codes"]) for row in records),
        "rows_with_technical_regulation": sum(bool(row["technical_regulations"]) for row in records),
    }
    return records, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terms", nargs="*", help="Override the audited default query-term set")
    parser.add_argument(
        "--strategy",
        choices=("codes", "terms"),
        default="codes",
        help="Indexed exact TN VED crawl (default) or supplemental product-name search",
    )
    parser.add_argument("--max-pages", type=int, default=0, help="Diagnostic cap per query slice; 0 means complete pagination")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Concurrent official requests (default: 4)")
    args = parser.parse_args()
    terms = tuple(args.terms) if args.terms else SEARCH_TERMS
    documents, crawl_audit = crawl(terms, args.max_pages, args.workers, args.strategy)
    records, normalization_audit = normalize_documents(documents)
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    diagnostic = bool(args.max_pages)
    output_path = CACHE / "diagnostic-products.jsonl" if diagnostic else OUTPUT
    report_path = CACHE / "diagnostic-report.json" if diagnostic else REPORT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "diagnostic_truncated_not_for_catalog" if diagnostic else "official_eaeu_open_data_product_evidence_normalized",
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_rights_url": RIGHTS_URL,
        "odata_url": ODATA_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "search_terms": list(terms) if args.strategy == "terms" else [],
        "crawl_strategy": args.strategy,
        "unique_conformity_documents": len(documents),
        **crawl_audit,
        **normalization_audit,
        "normalized_output_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "grain_note": "One row is a deduplicated manufacturer/holder + reported product designation + family identity; certificate renewals and repeat occurrences are retained as evidence, not duplicate products.",
        "quality_note": "The registry is conformity evidence, not proof of current market availability. Generic assortment declarations, missing-manufacturer rows and non-product descriptions are excluded.",
        "publication_scope": "Factual product/manufacturer designations, TN VED codes, technical regulations, document identifiers/status/dates and direct official card URLs only; addresses, contacts, prose, layouts and attachments are excluded.",
        "output_path": str(output_path.relative_to(ROOT)),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
