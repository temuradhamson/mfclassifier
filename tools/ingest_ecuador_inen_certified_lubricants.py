#!/usr/bin/env python3
"""Normalize lubricant rows from three official Ecuador INEN announcements."""

from __future__ import annotations

import hashlib
import html
import json
import re
import ssl
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "ecuador-inen-certified-lubricants.jsonl"
REPORT = ROOT / "data" / "ecuador-inen-certified-lubricants-report.json"
SNAPSHOT_DATE = "2026-07-22"
API_BASE = "https://www.normalizacion.gob.ec/wp-json/wp/v2/posts/"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-data)"

SOURCES = {
    7405: {
        "source_id": "ECUADOR_INEN_2024_08_CERTIFIED_LUBRICANTS",
        "date": "2024-08-08",
        "url": "https://www.normalizacion.gob.ec/mas-empresas-se-suman-a-la-calidad-conoce-las-empresas-que-en-este-mes-han-accedido-a-las-certificaciones-del-inen-5/",
        "content_sha256": "8d5e8f7fac0423e75d1f333e24ce8619239f67982bf07f9b99354312802329ab",
        "all_table_rows": 55,
        "relevant_rows": 16,
    },
    7649: {
        "source_id": "ECUADOR_INEN_2025_01_CERTIFIED_LUBRICANTS",
        "date": "2025-02-11",
        "url": "https://www.normalizacion.gob.ec/conoce-las-empresas-que-en-el-mes-de-enero-han-accedido-a-las-certificaciones-del-inen/",
        "content_sha256": "7aa64dbac6e28c25973a895ec56c311573ee42e5792b647f979527cba67ab7c9",
        "all_table_rows": 33,
        "relevant_rows": 2,
    },
    7707: {
        "source_id": "ECUADOR_INEN_2025_02_CERTIFIED_LUBRICANTS",
        "date": "2025-03-12",
        "url": "https://www.normalizacion.gob.ec/conoce-las-empresas-que-en-el-mes-de-febrero-accedieron-a-las-certificaciones-del-inen/",
        "content_sha256": "fad7a7df0fc0b08bbceb3a1a5d2105fb37ac5361ab306f1b261bf403622595ae",
        "all_table_rows": 67,
        "relevant_rows": 12,
    },
}


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[dict]]] = []
        self.table: list[list[dict]] | None = None
        self.row: list[dict] | None = None
        self.cell: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {
                "text": [],
                "rowspan": int(attrs_dict.get("rowspan") or 1),
                "colspan": int(attrs_dict.get("colspan") or 1),
            }

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.cell["text"] = clean(" ".join(self.cell["text"]))
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def expand_rows(table: list[list[dict]]) -> list[list[str]]:
    expanded = []
    carry: dict[int, tuple[str, int]] = {}
    for source_row in table:
        row: list[str] = []
        column = 0
        for cell in source_row:
            while column in carry:
                value, remaining = carry[column]
                row.append(value)
                if remaining == 1:
                    del carry[column]
                else:
                    carry[column] = (value, remaining - 1)
                column += 1
            for _ in range(cell["colspan"]):
                row.append(cell["text"])
                if cell["rowspan"] > 1:
                    carry[column] = (cell["text"], cell["rowspan"] - 1)
                column += 1
        while column in carry:
            value, remaining = carry[column]
            row.append(value)
            if remaining == 1:
                del carry[column]
            else:
                carry[column] = (value, remaining - 1)
            column += 1
        expanded.append(row)
    return expanded


def fetch_post(post_id: int, expected: dict) -> tuple[dict, str]:
    request = urllib.request.Request(API_BASE + str(post_id), headers={"User-Agent": USER_AGENT})
    # INEN currently serves an incomplete TLS chain. Exact content hashes below
    # pin the public response; no authentication or access control is bypassed.
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(request, timeout=120, context=context) as response:
        post = json.load(response)
    content = post["content"]["rendered"]
    digest = hashlib.sha256(content.encode()).hexdigest()
    if post["id"] != post_id or post["link"] != expected["url"]:
        raise RuntimeError(f"Unexpected INEN post identity for {post_id}")
    if post["date"][:10] != expected["date"] or digest != expected["content_sha256"]:
        raise RuntimeError(f"INEN post {post_id} changed: {digest}")
    return post, content


def relevant_rows(content: str, expected: dict) -> list[list[str]]:
    parser = TableParser()
    parser.feed(content)
    tables = [expand_rows(table) for table in parser.tables]
    candidates = [table for table in tables if any("EMPRESA" in " ".join(row).upper() for row in table)]
    if not candidates:
        raise RuntimeError("INEN product table was not found")
    table = candidates[0]
    if len(table) - 1 != expected["all_table_rows"]:
        raise RuntimeError(f"Unexpected INEN table denominator: {len(table) - 1}")
    rows = [row for row in table[1:] if re.search(r"(?i)aceites? lubricantes?", " ".join(row))]
    if len(rows) != expected["relevant_rows"]:
        raise RuntimeError(f"Unexpected INEN lubricant count: {len(rows)}")
    return rows


def product_identity(source_text: str) -> tuple[str, str, list[str], list[str], list[str], list[str]]:
    upper = clean(source_text).upper()
    family = "T" if "TRANSMISIONES MANUALES" in upper else "M"
    prefix = re.sub(
        r"^ACEITES? LUBRICANTES? PARA (?:MOTORES DE )?COMBUSTI[ÓO]N INTERNA DE CICLO (?:DE )?(?:OTTO|DIESEL)\.?\s*",
        "", clean(source_text), flags=re.I,
    )
    prefix = re.sub(
        r"^ACEITES? LUBRICANTES? PARA TRANSMISIONES MANUALES Y DIFERENCIALES DE EQUIPO AUTOMOTOR\.?\s*",
        "", prefix, flags=re.I,
    )
    name = re.split(
        r"\s*,?\s*(?:SAE\s*:|(?=\d{1,2}W\s*-?\s*\d{2}\s*,?\s*API\s*:))",
        prefix, maxsplit=1, flags=re.I,
    )[0].strip(" .,;")
    sae_match = re.search(r"\bSAE\s*:\s*([0-9]{1,3}(?:W\s*-?\s*[0-9]{2})?)", upper)
    if not sae_match:
        sae_match = re.search(r"\b([0-9]{1,2}W\s*-?\s*[0-9]{2})\s*,?\s*API\s*:", upper)
    sae = []
    if sae_match:
        value = re.sub(r"\s+", "", sae_match.group(1)).replace("W-", "W-")
        value = re.sub(r"^(\d{1,2}W)(\d{2})$", r"\1-\2", value)
        sae = [value]
    api = []
    jaso = []
    api_match = re.search(r"\bAPI\s*:\s*(.+)$", upper)
    if api_match:
        tail = clean(api_match.group(1)).replace("CI 4", "CI-4").replace("CJ 4", "CJ-4").replace("CK 4", "CK-4").replace("GL 4", "GL-4").replace("GL 5", "GL-5")
        tail = tail.replace("MA 2", "MA2")
        if "JASO" in tail:
            jaso = re.findall(r"JASO\s+(MA2|MA1|MA|MB)", tail)
            tail = re.sub(r"JASO\s+(?:MA2|MA1|MA|MB)\s*/?", "", tail).strip(" /,")
        api = [value for value in re.split(r"\s*/\s*|\s*,\s*", tail) if value]
    api_gl = [value for value in api if value.startswith("GL-")]
    api = [value for value in api if not value.startswith("GL-")]
    return family, name, sae, api, api_gl, jaso


def normalize_row(post_id: int, row_index: int, row: list[str], source: dict) -> dict:
    holder = row[0]
    source_product = row[1]
    brand = row[2] if len(row) >= 3 and row[2] else holder
    family, product_name, sae, api, api_gl, jaso = product_identity(source_product)
    source_facts = {
        "post_id": post_id,
        "source_row": row_index,
        "holder": holder,
        "source_product": source_product,
        "brand": brand,
    }
    return {
        "source_id": source["source_id"],
        "source_record_id": f"INEN-EC-{post_id}-{row_index:03d}",
        "source_post_id": post_id,
        "source_row": row_index,
        "source_url": source["url"],
        "source_product_field": source_product,
        "source_facts_sha256": hashlib.sha256(json.dumps(source_facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "announcement_date": source["date"],
        "market": "Ecuador",
        "manufacturer_or_certificate_holder": holder,
        "brand": brand,
        "product_name": product_name,
        "family_code": family,
        "technical": {"sae": sae, "api": api, "api_gl": api_gl, "jaso": jaso},
        "lifecycle_status": "official_inen_certification_announcement_current_status_unverified",
        "evidence_status": "official_government_product_certification_announcement",
        "source_quality_flags": [
            "announcement_does_not_publish_certificate_number_or_expiry",
            "official_source_tls_chain_incomplete_content_pinned_by_sha256",
        ],
    }


def main() -> None:
    records = []
    post_report = {}
    for post_id, source in SOURCES.items():
        _, content = fetch_post(post_id, source)
        rows = relevant_rows(content, source)
        for index, row in enumerate(rows, 1):
            records.append(normalize_row(post_id, index, row, source))
        post_report[str(post_id)] = {
            "source_id": source["source_id"],
            "source_url": source["url"],
            "content_sha256": source["content_sha256"],
            "all_product_rows": source["all_table_rows"],
            "relevant_rows": len(rows),
        }
    records.sort(key=lambda row: row["source_record_id"])
    if len(records) != 30 or len({row["source_record_id"] for row in records}) != 30:
        raise RuntimeError("Expected 30 unique INEN lubricant announcement rows")
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "status": "official_ecuador_inen_certification_announcements_normalized",
        "dataset_snapshot_date": SNAPSHOT_DATE,
        "posts": post_report,
        "audited_all_product_rows": sum(source["all_table_rows"] for source in SOURCES.values()),
        "normalized_products": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_sae": sum(bool(row["technical"]["sae"]) for row in records),
        "rows_with_api": sum(bool(row["technical"]["api"]) for row in records),
        "rows_with_jaso": sum(bool(row["technical"]["jaso"]) for row in records),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "method": "complete official announcement tables audited; exact holder, brand, product, SAE and API/JASO facts retained",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
