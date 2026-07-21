#!/usr/bin/env python3
"""Download lubricant and technical-fluid products from UAE MOIAT open data."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "uae-moiat-conformity-products.jsonl"
REPORT = ROOT / "data" / "uae-moiat-conformity-products-report.json"
CACHE = ROOT / ".cache" / "uae-moiat-conformity"
SOURCE_PAGE_URL = "https://moiat.gov.ae/en/open-data/product-conformity-data"
SOURCE_RIGHTS_URL = "https://moiat.gov.ae/en/open-data"
PRODUCTS_API_URL = "https://moiat.gov.ae/api/OpenDataDocumentLibrary/GetCertificateProducts"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (official-open-data-lubricant-registry)"

# IDs and labels are published in the official Product Type filter. Empty
# categories are retained in the report so coverage remains auditable.
PRODUCT_TYPES = {
    14519: ("Lubrications", None),
    14539: ("Brake Fluids", "TF"),
    14540: ("Automatic movement transfer liquid", "T"),
    14541: ("Lubricating Oils for Four-Stroke Cycle Motorcycle Gasoline Engines", "M"),
    14542: ("Lubricating oil for Internal Combustion Engines", "M"),
    14544: ("Lubricants Oils", None),
    14608: ("Lubricants Oils", None),
    14885: ("Lubricating oil-Voluntary", None),
    14985: ("Lubricating oil", None),
    15089: ("Lubricating oil for engine", "M"),
    15096: ("Non-Petroleum Base Brake Fluids for Hydraulic Systems", "TF"),
    15097: ("Lubricants, industrial oils and related products (EMA/EMB)", "M"),
    14545: ("AD BLU", "TF"),
    14609: ("AD BLU", "TF"),
}


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z\u0600-\u06ff]+", " ", value).strip()


def cached_get(url: str, cache_name: str) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    error = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read()
            if not body:
                raise RuntimeError("empty response")
            path.write_bytes(body)
            time.sleep(0.12)
            return body
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            error = exc
            time.sleep(min(12, 1.5 * (attempt + 1)))
    raise RuntimeError(f"Failed after retries: {url}: {error}")


class ListingParser(HTMLParser):
    """Extract certificate cards from the server-rendered result list."""

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.card: dict | None = None
        self.capture_tag = ""
        self.buffer: list[str] = []
        self.cards: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = values.get("class") or ""
        if self.card is None and tag == "div" and "border-b" in classes and "gap-6" in classes:
            self.card = {}
            self.depth = 1
        elif self.card is not None and tag == "div":
            self.depth += 1
        if self.card is not None and tag in {"h5", "h6", "p"}:
            self.capture_tag = tag
            self.buffer = []
        if self.card is not None and tag == "button" and values.get("data-certificateid"):
            self.card["certificate_id"] = values["data-certificateid"]

    def handle_data(self, data: str) -> None:
        if self.card is not None and self.capture_tag:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.card is not None and tag == self.capture_tag:
            value = clean("".join(self.buffer))
            if tag == "h5":
                self.card["certificate_type"] = value
            elif tag == "h6":
                self.card["_label"] = value
            elif tag == "p" and self.card.get("_label"):
                self.card[self.card.pop("_label")] = value
            self.capture_tag = ""
        if self.card is not None and tag == "div":
            self.depth -= 1
            if self.depth == 0:
                if self.card.get("certificate_id"):
                    self.cards.append(self.card)
                self.card = None


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.cell: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []
        self.pages: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in {"th", "td"}:
            self.in_cell = True
            self.cell = []
        if values.get("data-page", "").isdigit():
            self.pages.append(int(values["data-page"]))

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"}:
            self.row.append(clean("".join(self.cell)))
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)


def listing_url(product_type_id: int, page: int) -> str:
    query = urllib.parse.urlencode({"producttypeid": product_type_id, "page": page})
    return f"{SOURCE_PAGE_URL}?{query}"


def last_listing_page(body: str, product_type_id: int, has_cards: bool) -> int:
    pattern = rf"producttypeid={product_type_id}(?:&amp;|&)[^\"']*?page=(\d+)"
    pages = [int(value) for value in re.findall(pattern, body)]
    return max(pages, default=(1 if has_cards else 0))


def product_api_url(certificate_id: str, page: int) -> str:
    query = urllib.parse.urlencode({"certificateID": certificate_id, "lang": "en", "page": page})
    return f"{PRODUCTS_API_URL}?{query}"


def parse_products(body: bytes) -> tuple[list[dict], int]:
    parser = TableParser()
    parser.feed(body.decode("utf-8", "ignore"))
    product_rows = []
    in_products = False
    for row in parser.rows:
        if row == ["Brand", "Model", "Description", "Barcode"]:
            in_products = True
            continue
        if in_products and len(row) == 4:
            product_rows.append(dict(zip(["brand", "model", "description", "barcode"], row)))
    return product_rows, max(parser.pages, default=1)


def infer_family(product_type_id: int, brand: str, model: str, description: str) -> tuple[str, str]:
    fixed = PRODUCT_TYPES[product_type_id][1]
    if fixed:
        return fixed, "official_product_type"
    raw = clean(f"{brand} {model} {description}").upper().replace("‐", "-").replace("–", "-")
    value = f" {normalize(raw)} "
    rules = [
        ("G", [" grease ", " greases ", " lithium ", " calcium ", " nlgi ", " شحم "]),
        ("TF", [" coolant ", " antifreeze ", " brake fluid ", " adblue ", " washer fluid ", " dot 3 ", " dot 4 ", " dot iii ", " dot iv "]),
        ("T", [" atf ", " cvt ", " dct ", " gear oil ", " transmission ", " axle ", " dexron ", " dexon ", " gl 4 ", " gl 5 "]),
        ("H", [" hydraulic ", " hydraulik ", " hvlp ", " hm 32 ", " hm 46 ", " hm 68 "]),
        ("C", [" compressor ", " refrigeration oil "]),
        ("U", [" turbine "]),
        ("E", [" transformer ", " insulating oil "]),
        ("M", [" engine oil ", " motor oil ", " diesel engine ", " gasoline engine ", " petrol engine ", " api sn ", " api sp ", " api sm ", " api sl ", " api sj ", " api sh ", " api sg ", " api ck 4 ", " api cj 4 ", " api ci 4 ", " api ch 4 ", " api cf 4 "]),
        ("I", [" industrial ", " slideway ", " spindle ", " circulating ", " cutting oil ", " metalworking ", " heat transfer "]),
    ]
    for family, tokens in rules:
        matched_token = next((token for token in tokens if token in value), None)
        if matched_token:
            return family, f"product_text_rule:{matched_token.strip()}"
    if re.search(r"(?<!\d)(?:0|5|10|15|20|25)W[- ]?\d{2}(?!\d)", raw):
        return "M", "product_text_rule:sae_engine_grade"
    if re.search(r"(?<!\d)(?:70|75|80|85)W(?:[- ]?\d{2,3})?(?!\d)", raw):
        return "T", "product_text_rule:sae_gear_grade"
    if re.search(r"API\s*[:\-]?\s*(?:SP|SN|SM|SL|SJ|SH|SG|CK\s*-?\s*4|CJ\s*-?\s*4|CI\s*-?\s*4|CH\s*-?\s*4|CF\s*-?\s*4|CF)", raw):
        return "M", "product_text_rule:api_engine_class"
    if re.search(r"(?:CI|CH|CJ|CK)\s*-?\s*4(?:SL|SN)?", raw):
        return "M", "product_text_rule:embedded_api_engine_class"
    if re.search(r"\bACEA\s*-?\s*(?:[ACE]\d|A\d/B\d)\b|\b(?:ILSAC\s*)?GF\s*-?\s*[1-7]\b", raw):
        return "M", "product_text_rule:acea_or_ilsac_engine_class"
    if re.search(r"\b(?:EMA|EMB)\s*\d", raw):
        return "M", "product_text_rule:ema_emb_engine_oil_code"
    if re.search(r"\b(?:DEX(?:RON|ON)?|DX)\s*-?\s*(?:III|3|VI|6)\b", raw):
        return "T", "product_text_rule:dexron_transmission_class"
    return "S", "generic_lubricant_product_type_requires_review"


def technical(text: str) -> dict:
    upper = clean(text).upper().replace("‐", "-").replace("–", "-")
    sae = sorted(set(re.findall(r"(?<!\d)((?:0|5|10|15|20|25)W[- ]?\d{2})(?!\d)", upper)))
    sae = [value.replace(" ", "-") for value in sae]
    sae_gear = sorted(set(re.findall(r"(?<!\d)((?:70|75|80|85)W(?:[- ]?\d{2,3})?)(?!\d)", upper)))
    sae_gear = [value.replace(" ", "-") for value in sae_gear]
    api = []
    for match in re.findall(r"\bAPI\s*[:\-]?\s*(SP|SN\s*PLUS|SN|SM|SL|SJ|SH|SG|CK\s*-?\s*4|CJ\s*-?\s*4|CI\s*-?\s*4\s*PLUS|CI\s*-?\s*4|CH\s*-?\s*4|CG\s*-?\s*4|CF\s*-?\s*4|CF|FA\s*-?\s*4)\b", upper):
        compact = re.sub(r"\s+", " ", match).strip()
        grade = re.match(r"^(CK|CJ|CI|CH|CG|CF|FA)\s*-?\s*4(?:\s+PLUS)?$", compact)
        if grade:
            compact = f"{grade.group(1)}-4" + (" PLUS" if "PLUS" in compact else "")
        api.append(compact)
    api = sorted(set(api))
    api_gl = sorted(set(re.findall(r"\b(?:API\s+)?(GL[- ]?[1-6])\b", upper)))
    api_gl = [value.replace(" ", "-") for value in api_gl]
    iso_vg = sorted(set(re.findall(r"\bISO\s*(?:VG)?\s*(15|22|32|46|68|100|150|220|320|460|680|1000)\b", upper)), key=int)
    nlgi = sorted(set(re.findall(r"\bNLGI\s*(000|00|0|[1-6])\b", upper)))
    dot = sorted(set(re.findall(r"\bDOT\s*([345](?:\.1)?)\b", upper)))
    acea = sorted(set(re.findall(r"\b(?:ACEA\s*)?([ACE][0-9](?:/[BCE][0-9])?|A[0-9]/B[0-9])\b", upper)))
    jaso = sorted(set(re.findall(r"\bJASO\s+(MA2|MA|MB|FB|FC|FD|DL-1|DH-1|DH-2)\b", upper)))
    return {"sae": sae, "sae_gear": sae_gear, "api": api, "api_gl": api_gl, "acea": acea, "jaso": jaso, "iso_vg": iso_vg, "nlgi": nlgi, "dot": dot}


def product_identity(model: str, description: str, barcode: str, brand: str) -> tuple[str, str]:
    """Separate an explicit terminal package from a formula/model identity."""
    product_name = clean(model or description or barcode or brand)
    package = ""
    match = re.match(
        r"^(.*?)(1000|500|250|200|100|50)\s*(ML)$|"
        r"^(.*?)(1000|208|205|200|60|25|20|18|5|4|1)\s*(L)$",
        product_name,
        flags=re.I,
    )
    if match and clean(match.group(1) or match.group(4)):
        if match.group(3):
            base, quantity, unit = match.group(1), match.group(2), match.group(3)
        else:
            base, quantity, unit = match.group(4), match.group(5), match.group(6)
        product_name = clean(base)
        package = f"{quantity} {unit.upper()}"
    return product_name, package


def lifecycle(expiry: str) -> str:
    try:
        end = datetime.strptime(expiry, "%d/%m/%Y").date()
    except ValueError:
        return "certificate_date_unknown"
    return "certificate_active_at_snapshot" if end >= date.fromisoformat(SNAPSHOT_DATE) else "certificate_expired_before_snapshot"


def main() -> None:
    certificates: dict[str, dict] = {}
    listing_pages_by_type = {}
    response_hashes: list[str] = []
    for product_type_id, (expected_label, _) in PRODUCT_TYPES.items():
        first = cached_get(listing_url(product_type_id, 1), f"listing-{product_type_id}-1.html")
        response_hashes.append(hashlib.sha256(first).hexdigest())
        parser = ListingParser()
        parser.feed(first.decode("utf-8", "ignore"))
        pages = last_listing_page(first.decode("utf-8", "ignore"), product_type_id, bool(parser.cards))
        listing_pages_by_type[str(product_type_id)] = pages
        cards = parser.cards
        for page in range(2, pages + 1):
            body = cached_get(listing_url(product_type_id, page), f"listing-{product_type_id}-{page}.html")
            response_hashes.append(hashlib.sha256(body).hexdigest())
            page_parser = ListingParser()
            page_parser.feed(body.decode("utf-8", "ignore"))
            cards.extend(page_parser.cards)
        for card in cards:
            card["official_product_type_id"] = product_type_id
            card["expected_product_type_label"] = expected_label
            existing = certificates.get(card["certificate_id"])
            if existing and existing != card:
                raise RuntimeError(f"Conflicting certificate metadata: {card['certificate_id']}")
            certificates[card["certificate_id"]] = card
        print(f"type={product_type_id} pages={pages} certificates={len(cards)}", flush=True)

    certificate_ids = sorted(certificates, key=int)
    uncached_ids = [certificate_id for certificate_id in certificate_ids if not (CACHE / f"products-{certificate_id}-1.html").exists()]
    if uncached_ids:
        print(f"prefetch_product_details={len(uncached_ids)} workers=6", flush=True)
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                pool.submit(cached_get, product_api_url(certificate_id, 1), f"products-{certificate_id}-1.html"): certificate_id
                for certificate_id in uncached_ids
            }
            for completed, future in enumerate(as_completed(futures), 1):
                future.result()
                if completed % 100 == 0 or completed == len(futures):
                    print(f"prefetched={completed}/{len(futures)}", flush=True)

    extra_pages = []
    for certificate_id in certificate_ids:
        first_body = (CACHE / f"products-{certificate_id}-1.html").read_bytes()
        _, pages = parse_products(first_body)
        extra_pages.extend((certificate_id, page) for page in range(2, pages + 1))
    uncached_extra_pages = [
        (certificate_id, page) for certificate_id, page in extra_pages
        if not (CACHE / f"products-{certificate_id}-{page}.html").exists()
    ]
    if uncached_extra_pages:
        print(f"prefetch_extra_product_pages={len(uncached_extra_pages)} workers=6", flush=True)
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                pool.submit(cached_get, product_api_url(certificate_id, page), f"products-{certificate_id}-{page}.html"): (certificate_id, page)
                for certificate_id, page in uncached_extra_pages
            }
            for completed, future in enumerate(as_completed(futures), 1):
                future.result()
                if completed % 100 == 0 or completed == len(futures):
                    print(f"prefetched_extra={completed}/{len(futures)}", flush=True)

    occurrences = []
    empty_certificates = []
    for index, certificate_id in enumerate(certificate_ids, 1):
        certificate = certificates[certificate_id]
        body = cached_get(product_api_url(certificate_id, 1), f"products-{certificate_id}-1.html")
        response_hashes.append(hashlib.sha256(body).hexdigest())
        rows, pages = parse_products(body)
        for page in range(2, pages + 1):
            page_body = cached_get(product_api_url(certificate_id, page), f"products-{certificate_id}-{page}.html")
            response_hashes.append(hashlib.sha256(page_body).hexdigest())
            page_rows, _ = parse_products(page_body)
            rows.extend(page_rows)
        seen = set()
        certificate_occurrences = []
        for source_row_number, row in enumerate(rows, 1):
            identity = tuple(clean(row[key]) for key in ["brand", "model", "description", "barcode"])
            if identity in seen:
                continue
            seen.add(identity)
            family, basis = infer_family(certificate["official_product_type_id"], *identity[:3])
            certificate_occurrences.append({
                **row,
                "certificate_id": certificate_id,
                "certificate_number": clean(certificate.get("Certificate Number")),
                "certificate_type": clean(certificate.get("certificate_type")),
                "official_product_type_id": certificate["official_product_type_id"],
                "official_product_type": clean(certificate.get("Product Type")) or certificate["expected_product_type_label"],
                "organization_name": clean(certificate.get("Organization Name")),
                "country": clean(certificate.get("Country")),
                "issue_date": clean(certificate.get("Issue Date")),
                "expiry_date": clean(certificate.get("Expiry Date")),
                "family_code": family,
                "classification_basis": basis,
                "source_product_row": source_row_number,
            })
        known_families = {row["family_code"] for row in certificate_occurrences if row["family_code"] != "S"}
        if len(known_families) == 1:
            inherited_family = next(iter(known_families))
            for row in certificate_occurrences:
                if row["family_code"] == "S":
                    row["family_code"] = inherited_family
                    row["classification_basis"] = "unambiguous_family_inherited_within_certificate"
        occurrences.extend(certificate_occurrences)
        if not rows:
            empty_certificates.append(certificate_id)
        if index % 50 == 0 or index == len(certificates):
            print(f"details={index}/{len(certificates)} product_occurrences={len(occurrences)}", flush=True)

    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in occurrences:
        product_name, package = product_identity(row["model"], row["description"], row["barcode"], row["brand"])
        row["canonical_product_name"] = product_name
        row["package"] = package
        brand_identity = normalize(row["brand"]) or normalize(row["organization_name"])
        grouped[(brand_identity, normalize(product_name), row["family_code"])].append(row)

    records = []
    for key, rows in sorted(grouped.items()):
        first = rows[0]
        product_name = first["canonical_product_name"]
        certificates_for_product = []
        for row in rows:
            certificate_entry = {k: row[k] for k in [
                "certificate_id", "certificate_number", "certificate_type", "official_product_type_id",
                "official_product_type", "organization_name", "country", "issue_date", "expiry_date",
            ]}
            if certificate_entry not in certificates_for_product:
                certificates_for_product.append(certificate_entry)
        certificate_entries = sorted(certificates_for_product, key=lambda item: (item["certificate_id"], item["certificate_number"]))
        texts = sorted({clean(" ".join([row["model"], row["description"], row["barcode"]])) for row in rows})
        source_record_hash = hashlib.sha256("|".join(key).encode()).hexdigest()[:16]
        records.append({
            "source_id": "UAE_MOIAT_PRODUCT_CONFORMITY",
            "source_record_id": f"AE-MOIAT-{source_record_hash}",
            "source_url": listing_url(first["official_product_type_id"], 1),
            "source_rights_url": SOURCE_RIGHTS_URL,
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "market": "United Arab Emirates",
            "product_name": product_name,
            "brand": clean(first["brand"]) or clean(first["organization_name"]),
            "manufacturer": clean(first["organization_name"]),
            "family_code": first["family_code"],
            "classification_basis": first["classification_basis"],
            "source_descriptions": sorted({clean(row["description"]) for row in rows if clean(row["description"])}),
            "source_models": sorted({clean(row["model"]) for row in rows if clean(row["model"])}),
            "barcodes": sorted({clean(row["barcode"]) for row in rows if clean(row["barcode"])}),
            "packages": sorted({row["package"] for row in rows if row["package"]}),
            "technical": technical(" ".join(texts)),
            "certificate_entries": certificate_entries,
            "lifecycle_status": (
                "certificate_active_at_snapshot" if any(lifecycle(item["expiry_date"]) == "certificate_active_at_snapshot" for item in certificate_entries)
                else "certificate_expired_before_snapshot" if certificate_entries
                else "certificate_date_unknown"
            ),
            "source_occurrence_count": len(rows),
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "official_uae_government_open_product_conformity_registry_normalized",
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "source_page_url": SOURCE_PAGE_URL,
        "source_rights_url": SOURCE_RIGHTS_URL,
        "products_api_url": PRODUCTS_API_URL,
        "listing_pages_by_product_type": listing_pages_by_type,
        "certificate_cards": len(certificates),
        "certificates_without_product_rows": empty_certificates,
        "product_certificate_occurrences": len(occurrences),
        "normalized_products": len(records),
        "cross_certificate_occurrences_merged": len(occurrences) - len(records),
        "brands": len({normalize(row["brand"]) for row in records}),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "source_responses_manifest_sha256": hashlib.sha256("\n".join(sorted(response_hashes)).encode()).hexdigest(),
        "rights_note": "The official MOIAT Open Data page states that open data can be freely used, reused, distributed and shared without restrictions.",
        "grain_note": "One normalized row is brand/organization + model/product name + professional family. Exact product occurrences across ECAS/EQM or renewed certificates are merged while every certificate and barcode remains attached.",
        "count_note": "The website's displayed total-count behaves as the last listing page number, not the certificate-row total; observed certificate cards and product rows are counted directly.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["certificate_cards", "product_certificate_occurrences", "normalized_products", "families"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
