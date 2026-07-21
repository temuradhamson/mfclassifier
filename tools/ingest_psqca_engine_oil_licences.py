#!/usr/bin/env python3
"""Normalize public PSQCA certification-mark licences for engine lubricating oils.

The Pakistan Standards and Quality Control Authority exposes a public WebForms
verification page searchable by certified product.  The two relevant search
options are mono-grade and multi-grade internal-combustion-engine lubricating
oil.  A result is a licence-level certified brand scope, not an individual SAE
or API formulation; the loader preserves that distinction explicitly.
"""

from __future__ import annotations

import hashlib
import html
import http.cookiejar
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "psqca-engine-oil-licences.jsonl"
REPORT = ROOT / "data" / "psqca-engine-oil-licences-report.json"
SOURCE_ID = "PSQCA_ENGINE_OIL_CM_LICENCES"
SOURCE_URL = "https://icq.psqca.com.pk/e_services/t_cmverify.aspx"
STANDARD_URL = "https://psqca.com.pk/cs/Chemical/PS%20343-2009.pdf"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-data)"

PRODUCT_SCOPES = {
    "271": "Internal Combustion Engine Lubricating Oil (Mono Grade)",
    "290": "Internal Combustion Engine Lubricating Oil (Multi Grade)",
}


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def plain(fragment: str) -> str:
    return clean(re.sub(r"<[^>]+>", " ", fragment))


def hidden_fields(page: bytes) -> dict[str, str]:
    text = page.decode("utf-8", errors="replace")
    return {
        html.unescape(name): html.unescape(value)
        for name, value in re.findall(
            r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"',
            text,
            re.I,
        )
    }


def options(page: bytes) -> dict[str, str]:
    text = page.decode("utf-8", errors="replace")
    select = re.search(r'<select[^>]+id="ddl_product"[^>]*>(.*?)</select>', text, re.I | re.S)
    if not select:
        raise RuntimeError("PSQCA product selector is missing")
    return {
        html.unescape(value): plain(label)
        for value, label in re.findall(
            r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', select.group(1), re.I | re.S
        )
    }


class Client:
    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(self, fields: dict[str, str] | None = None) -> bytes:
        data = urllib.parse.urlencode(fields).encode() if fields is not None else None
        request = urllib.request.Request(SOURCE_URL, data=data, headers={"User-Agent": USER_AGENT})
        with self.opener.open(request, timeout=120) as response:
            payload = response.read()
        if not payload:
            raise RuntimeError("PSQCA returned an empty response")
        return payload


def search(client: Client, product_id: str) -> tuple[bytes, bytes]:
    start = client.request()
    available = options(start)
    if available.get(product_id) != PRODUCT_SCOPES[product_id]:
        raise RuntimeError(
            f"PSQCA product scope changed for {product_id}: {available.get(product_id)!r}"
        )
    fields = hidden_fields(start)
    fields.update({
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "txt_licenseno": "",
        "txt_manufacturer": "",
        "ddl_product": product_id,
        "txt_brand": "",
        "btn_new": "Search",
    })
    return start, client.request(fields)


def parse_date(value: str) -> str:
    return datetime.strptime(value, "%d-%m-%Y").date().isoformat()


def normalize_licence(value: str) -> str:
    return re.sub(r"\s+", "", clean(value)).upper()


def normalize_manufacturer(value: str) -> str:
    # The public Unit Name sometimes appends only a city. Keep the exact source
    # spelling separately, but do not publish location as part of the holder.
    value = clean(value).rstrip(" ,.")
    value = re.sub(r",\s*(?:Karachi|Hyderabad|Lahore|Gujranwala)\.?$", "", value, flags=re.I)
    return clean(value).rstrip(" ,.")


def result_rows(page: bytes, product_id: str) -> list[dict]:
    text = page.decode("utf-8", errors="replace")
    table = re.search(r'<table[^>]+id="dg_rcpt".*?</table>', text, re.I | re.S)
    if not table:
        raise RuntimeError(f"PSQCA result table missing for product {product_id}")
    rows = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(0), re.I | re.S)[1:]:
        cells = [plain(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.I | re.S)]
        if not cells or not any(cells):
            continue
        if len(cells) != 7:
            raise RuntimeError(f"Unexpected PSQCA result row: {cells!r}")
        licence, unit_name, product, brand, issued, expires, status = cells
        if not all([licence, unit_name, product, brand, issued, expires, status]):
            raise RuntimeError(f"Incomplete PSQCA result row: {cells!r}")
        if status not in {"Valid", "Expired"}:
            raise RuntimeError(f"Unknown PSQCA lifecycle status: {status!r}")
        rows.append({
            "licence_number": normalize_licence(licence),
            "manufacturer": normalize_manufacturer(unit_name),
            "manufacturer_source_reported": unit_name,
            "certified_product_scope": product,
            "brand": brand,
            "issued_at": parse_date(issued),
            "expires_at": parse_date(expires),
            "source_status": status,
            "search_product_id": product_id,
            "search_product_scope": PRODUCT_SCOPES[product_id],
        })
    return rows


def main() -> None:
    client = Client()
    occurrences = []
    response_hashes = {}
    selector_hashes = {}
    for product_id in PRODUCT_SCOPES:
        start, result = search(client, product_id)
        selector_hashes[product_id] = hashlib.sha256(start).hexdigest()
        response_hashes[product_id] = hashlib.sha256(result).hexdigest()
        occurrences.extend(result_rows(result, product_id))

    by_licence: dict[str, dict] = {}
    for row in occurrences:
        licence = row["licence_number"]
        if licence in by_licence and by_licence[licence] != row:
            raise RuntimeError(f"Conflicting PSQCA rows for licence {licence}")
        by_licence[licence] = row

    records = []
    for licence, row in sorted(by_licence.items()):
        source_facts = {key: row[key] for key in sorted(row)}
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"PSQCA-{licence}",
            "source_url": SOURCE_URL,
            "standard_url": STANDARD_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Pakistan",
            "licence_number": licence,
            "manufacturer": row["manufacturer"],
            "manufacturer_source_reported": row["manufacturer_source_reported"],
            "brand": row["brand"],
            "product_name": row["brand"],
            "product_name_basis": "source_reported_certified_brand_scope_not_individual_grade",
            "certified_product_scope": row["certified_product_scope"],
            "family_code": "M",
            "technical": {
                "certified_standard": ["PS 343"],
                "sae": [],
                "api": [],
                "grade_scope_source_reported": [row["search_product_scope"]],
            },
            "issued_at": row["issued_at"],
            "expires_at": row["expires_at"],
            "source_status": row["source_status"],
            "lifecycle_status": (
                "certification_valid_as_of_source_query"
                if row["source_status"] == "Valid"
                else "certification_expired"
            ),
            "search_product_id": row["search_product_id"],
            "search_product_scope": row["search_product_scope"],
            "source_quality_flags": [
                "licence_covers_certified_brand_scope_not_individual_sae_api_formulation"
            ],
            "source_facts_sha256": hashlib.sha256(
                json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "evidence_status": "official_government_product_certification_brand_scope",
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records
    )
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_pakistan_engine_oil_certification_licences_normalized",
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "standard_url": STANDARD_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "source_product_scopes": PRODUCT_SCOPES,
        "source_occurrences": len(occurrences),
        "normalized_licence_brand_scopes": len(records),
        "duplicates_merged": len(occurrences) - len(records),
        "lifecycle_statuses": dict(sorted(Counter(r["lifecycle_status"] for r in records).items())),
        "families": {"M": len(records)},
        "selector_page_sha256_by_scope": selector_hashes,
        "result_page_sha256_by_scope": response_hashes,
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One row is one PSQCA CM licence + source-reported brand + certified engine-lubricating-oil scope. It is not an individual SAE/API formulation.",
        "technical_note": "PS 343 is retained as certification evidence. No SAE or API grade is inferred because the public result row does not publish one.",
        "privacy_note": "No addresses, contacts or personal data are retained. A trailing city in Unit Name is removed from the normalized manufacturer while the exact public unit spelling is retained for audit.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
