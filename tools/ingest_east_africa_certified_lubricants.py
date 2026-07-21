#!/usr/bin/env python3
"""Normalize lubricant products from the public UNBS and TBS certification directories."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "east-africa-certified-lubricant-products.jsonl"
REPORT = ROOT / "data" / "east-africa-certified-lubricant-products-report.json"
CACHE = ROOT / ".cache" / "east-africa-certification"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-directories)"
SOURCES = {
    "UNBS_CERTIFIED_LUBRICANT_PRODUCTS": {
        "url": "https://cims.unbs.go.ug/api/website/",
        "context_url": "https://unbs.go.ug/content.php?pg=content&src=product-certification",
        "market": "UG",
        "authority": "Uganda National Bureau of Standards (UNBS)",
        "cache": "unbs-certified-products.html",
    },
    "TBS_CERTIFIED_LUBRICANT_PRODUCTS": {
        "url": "https://www.tbs.go.tz/index.php/companies",
        "context_url": "https://www.tbs.go.tz/pages/certification",
        "market": "TZ",
        "authority": "Tanzania Bureau of Standards (TBS)",
        "cache": "tbs-certified-companies.html",
    },
}


def clean(value: str | None) -> str:
    value = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: str | None = None
        self.fragments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.table = []
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.row is not None and tag in {"td", "th"}:
            self.cell = tag
            self.fragments = []

    def handle_data(self, data: str) -> None:
        if self.cell:
            self.fragments.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.cell == tag:
            assert self.row is not None
            self.row.append(clean(" ".join(self.fragments)))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row and self.table is not None:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def fetch(source: dict) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / source["cache"]
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
    error = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read()
            if b"CERTIFIED PRODUCT" not in body.upper() and b"CERTIFIED COMPANIES" not in body.upper():
                raise RuntimeError("unexpected certification-directory response")
            path.write_bytes(body)
            return body
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            error = exc
            time.sleep(min(10, attempt + 1))
    raise RuntimeError(f"Failed to fetch {source['url']}: {error}")


def largest_table(body: bytes) -> list[list[str]]:
    parser = TableParser()
    parser.feed(body.decode("utf-8", "ignore"))
    if not parser.tables:
        raise RuntimeError("No HTML table found")
    return max(parser.tables, key=len)


def family_for(product_type: str) -> tuple[str, str] | None:
    value = f" {normalize(product_type)} "
    if any(token in value for token in (" cleaner ", " remover ", " edible ", " cosmetic ", " hair oil ", " cooking oil ", " petroleum jelly ")):
        return None
    rules = [
        ("TF", "official_brake_fluid_product_type", (" brake fluid ", " brake fluids ")),
        ("TF", "official_coolant_product_type", (" coolant ", " antifreeze ")),
        ("T", "official_transmission_or_gear_oil_product_type", (" transmission fluid ", " gear oil ", " gear lubricant ", " gear lubricants ")),
        ("H", "official_hydraulic_oil_product_type", (" hydraulic oil ", " hydraulic lubricant oil ", " hydraulic systems ")),
        ("C", "official_compressor_oil_product_type", (" compressor oil ",)),
        ("U", "official_turbine_oil_product_type", (" turbine oil ",)),
        ("E", "official_transformer_oil_product_type", (" transformer oil ", " insulating oil ")),
        ("G", "official_lubricating_grease_product_type", (" lubricating grease ", " grease ")),
        ("M", "official_engine_oil_product_type", (" engine oil ", " engine oils ", " engine lubricating oil ", " engine lubricating oils ", " motor oil ", " two stroke ", " two strokes ", " two stroke cycle ", " four stroke ", " four stroke cycle ", " motorcycle gasoline engines ", " motorcycle engine oil ")),
        ("I", "official_industrial_or_process_oil_product_type", (" heat transfer oil ", " cutting oil ", " metalworking fluid ")),
    ]
    for family, basis, tokens in rules:
        if any(token in value for token in tokens):
            return family, basis
    return None


def split_tbs_designations(value: str) -> list[str]:
    value = clean(value).strip(" ,")
    if not value:
        return []
    if value.count("(") > value.count(")") and "," in value.split("(", 1)[1]:
        # One TBS row wraps a comma-separated product list in an unclosed
        # generic heading: "GP PETROL ENGINE (PRODUCT A, PRODUCT B, ...".
        value = value.split("(", 1)[1]
    # TBS uses commas for distinct certified trade designations. Ampersand with
    # surrounding spaces is also a separator when both sides are product names.
    parts = []
    for comma_part in re.split(r",+", value):
        parts.extend(re.split(r"\s+&\s+(?=[A-Z0-9])", comma_part))
    return [clean(part).strip(" ,") for part in parts if clean(part).strip(" ,")]


def parse_unbs(table: list[list[str]], source_id: str, source: dict) -> list[dict]:
    rows = []
    for row in table[1:]:
        if len(row) != 9:
            continue
        source_row, permit, product_type, company, _district, designation, standard, status, expiry = row
        classified = family_for(product_type)
        if not classified or not company or not designation:
            continue
        family, basis = classified
        rows.append({
            "source_id": source_id,
            "source_row": int(source_row) if source_row.isdigit() else None,
            "permit_number": permit,
            "product_type": product_type,
            "company": company,
            "designation": designation,
            "standard": standard,
            "status": normalize(status),
            "issue_date": "",
            "expiry_date": expiry,
            "family_code": family,
            "classification_basis": basis,
            "source_url": source["url"],
        })
    return rows


def parse_tbs(table: list[list[str]], source_id: str, source: dict) -> tuple[list[dict], int]:
    rows = []
    unsplit = 0
    for source_row, row in enumerate(table[1:], 1):
        if len(row) != 8:
            continue
        company, product_type, designation_list, permit, _location, standard, issue, expiry = row
        classified = family_for(product_type)
        if not classified or not company or not designation_list:
            continue
        family, basis = classified
        designations = split_tbs_designations(designation_list)
        if not designations:
            unsplit += 1
            continue
        for designation in designations:
            rows.append({
                "source_id": source_id,
                "source_row": source_row,
                "permit_number": permit,
                "product_type": product_type,
                "company": company,
                "designation": designation,
                "standard": standard,
                "status": "valid_by_expiry_date" if parse_date(expiry) >= date.fromisoformat(SNAPSHOT_DATE) else "expired_by_expiry_date",
                "issue_date": issue,
                "expiry_date": expiry,
                "family_code": family,
                "classification_basis": basis,
                "source_url": source["url"],
            })
    return rows, unsplit


def parse_date(value: str) -> date:
    for pattern in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(clean(value), pattern).date()
        except ValueError:
            pass
    return date.min


def technical(designation: str, product_type: str, context: str, family: str) -> dict:
    designation_upper = clean(designation).upper().replace("–", "-").replace("—", "-")
    upper = clean(f"{designation} {context}").upper().replace("–", "-").replace("—", "-")
    sae = sorted({f"{a}W-{b}" for a, b in re.findall(r"(?<!\d)(0|5|10|15|20|25)W[- /]?([2345]0)(?!\d)", upper)})
    sae_monograde = sorted(set(re.findall(r"\bSAE\s*(20W|15W|10W|5W|20|30|40|50|60)\b", upper)))
    sae_monograde = [value for value in sae_monograde if not any(grade.startswith(value + "-") for grade in sae)]
    sae_gear = sorted({f"{a}W-{b}" for a, b in re.findall(r"(?<!\d)(70|75|80|85)W[- /]?(90|110|140|190|250)(?!\d)", upper)})
    sae_gear.extend(f"SAE {value}" for value in re.findall(r"\bSAE\s+(?:EP[- ]?)?(90|110|140|190|250)\b", upper))
    api_engine = sorted(set(re.findall(r"\b(?:API\s*[: -]?\s*)?(SP|SN(?:\s+PLUS)?|SM|SL|SJ|SG|CK[- ]?4|CJ[- ]?4|CI[- ]?4|CH[- ]?4|CF[- ]?4|CF)\b", upper)))
    api_engine = [re.sub(r"^(C(?:I|J|K|H|F))[- ]?4", r"\1-4", value) for value in api_engine]
    api_gl = sorted({f"GL-{value}" for value in re.findall(r"\bGL[- ]?([1-6])\b", upper)})
    iso_explicit = sorted(set(re.findall(r"\bISO\s*(?:VG)?\s*(15|22|32|46|68|100|150|220|320|460|680|1000|1500)\b", upper)))
    iso_inferred = []
    industrial_gear = family == "T" and any(token in normalize(product_type) for token in ("industrial gear", "l ckd"))
    if (family in {"H", "I", "C", "U"} or industrial_gear) and not iso_explicit:
        match = re.search(r"(?:^|\D)(15|22|32|46|68|100|150|220|320|460|680|1000|1500)\s*$", designation_upper)
        if match and not re.search(r"\bSAE\s*(?:EP[- ]?)?" + re.escape(match.group(1)) + r"\b", designation_upper):
            iso_inferred = [match.group(1)]
    dot = sorted({f"DOT {value}" for value in re.findall(r"\bDOT[- ]*([345])\b", upper)})
    temperature_c = sorted({int(value) for value in re.findall(r"(-?\d{1,2})\s*°?C\b", upper)})
    return {
        "sae": sorted(set(sae)),
        "sae_monograde": sorted(set(sae_monograde)),
        "sae_gear": sorted(set(sae_gear)),
        "api": sorted(set(api_engine)),
        "api_gl": api_gl,
        "iso_vg_explicit": iso_explicit,
        "iso_vg_designation_inferred": iso_inferred,
        "dot": dot,
        "temperature_c": temperature_c,
    }


def main() -> None:
    source_tables = {source_id: largest_table(fetch(source)) for source_id, source in SOURCES.items()}
    unbs_rows = parse_unbs(source_tables["UNBS_CERTIFIED_LUBRICANT_PRODUCTS"], "UNBS_CERTIFIED_LUBRICANT_PRODUCTS", SOURCES["UNBS_CERTIFIED_LUBRICANT_PRODUCTS"])
    tbs_rows, tbs_unsplit = parse_tbs(source_tables["TBS_CERTIFIED_LUBRICANT_PRODUCTS"], "TBS_CERTIFIED_LUBRICANT_PRODUCTS", SOURCES["TBS_CERTIFIED_LUBRICANT_PRODUCTS"])
    occurrences = unbs_rows + tbs_rows

    grouped: dict[tuple[str, str, str, str, str], list[dict]] = defaultdict(list)
    for row in occurrences:
        key = (
            row["source_id"], normalize(row["company"]), normalize(row["designation"]),
            row["family_code"], normalize(row["product_type"]),
        )
        grouped[key].append(row)

    records = []
    for key, rows in sorted(grouped.items()):
        first = max(rows, key=lambda row: (parse_date(row["expiry_date"]), row["permit_number"], row["source_row"] or 0))
        source = SOURCES[first["source_id"]]
        permits = []
        seen_permits = set()
        for row in sorted(rows, key=lambda item: (item["permit_number"], item["expiry_date"], item["source_row"] or 0)):
            permit_identity = (row["permit_number"], row["expiry_date"], row["source_row"])
            if permit_identity in seen_permits:
                continue
            seen_permits.add(permit_identity)
            permits.append({
                "permit_number": row["permit_number"],
                "status": row["status"],
                "issue_date": row["issue_date"],
                "expiry_date": row["expiry_date"],
                "standard": row["standard"],
                "source_row": row["source_row"],
            })
        is_valid = any(row["status"] in {"valid", "valid_by_expiry_date"} and parse_date(row["expiry_date"]) >= date.fromisoformat(SNAPSHOT_DATE) for row in rows)
        identity = "|".join(key)
        prefix = "UNBS-QM" if first["source_id"].startswith("UNBS") else "TBS-SM"
        records.append({
            "source_id": first["source_id"],
            "source_record_id": prefix + "-" + hashlib.sha256(identity.encode()).hexdigest()[:16].upper(),
            "source_url": source["url"],
            "source_context_url": source["context_url"],
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "market": source["market"],
            "certification_authority": source["authority"],
            "manufacturer": first["company"],
            "brand": first["company"],
            "product_name": first["designation"],
            "source_product_type": first["product_type"],
            "family_code": first["family_code"],
            "classification_basis": first["classification_basis"],
            "technical": technical(first["designation"], first["product_type"], " ".join(row["standard"] for row in rows), first["family_code"]),
            "standards": sorted({row["standard"] for row in rows if row["standard"] and normalize(row["standard"]) != "null"}),
            "permit_entries": permits,
            "source_occurrence_count": len(rows),
            "lifecycle_status": "valid_certification_permit" if is_valid else "historical_expired_certification_permit",
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    source_counts = Counter(row["source_id"] for row in records)
    report = {
        "status": "official_public_government_product_certification_directories_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_directory_rows": {
            source_id: len(table) - 1 for source_id, table in source_tables.items()
        },
        "lubricant_scope_certificate_rows": {
            "UNBS_CERTIFIED_LUBRICANT_PRODUCTS": len(unbs_rows),
            "TBS_CERTIFIED_LUBRICANT_PRODUCTS": len({row["source_row"] for row in tbs_rows}),
        },
        "product_designation_occurrences": dict(sorted(Counter(row["source_id"] for row in occurrences).items())),
        "normalized_products": len(records),
        "normalized_products_by_source": dict(sorted(source_counts.items())),
        "certificate_renewal_or_duplicate_occurrences_merged": len(occurrences) - len(records),
        "manufacturers": len({(row["market"], row["manufacturer"]) for row in records}),
        "lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "families_by_source": {
            source_id: dict(sorted(Counter(row["family_code"] for row in records if row["source_id"] == source_id).items()))
            for source_id in SOURCES
        },
        "tbs_in_scope_rows_without_product_designation": tbs_unsplit,
        "tbs_lifecycle_method": "Computed from the official issue/expiry dates at the snapshot; the TBS table does not publish a separate live status flag.",
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "rights_note": "Public certification-directory facts only. Locations/districts, contacts and standards body text are excluded; standard designations are retained as certification evidence.",
        "excluded_fields": ["location", "district", "address", "contacts", "standard_body_text"],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
