#!/usr/bin/env python3
"""Extract lubricant-related factual rows from the public USDA BioPreferred catalog."""

from __future__ import annotations

import hashlib
import html
import http.cookiejar
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "usda-biopreferred-products.jsonl"
REPORT = ROOT / "data" / "usda-biopreferred-products-report.json"
URL = "https://www.biopreferred.gov/BioPreferred/faces/catalog/Catalog.xhtml"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"

CATEGORIES = [
    "Intermediates - Lubricant Components",
    "Heat Transfer Fluids",
    "Hydraulic Fluids",
    "Lavatory Flushing Fluids",
    "Lubricants or Greases",
    "Penetrating Lubricants",
    "Metalworking Fluids",
    "Firearm Lubricants",
    "Greases",
    "Chain and Cable Lubricants",
    "Forming Lubricants",
    "Gear Lubricants",
    "Multipurpose Lubricants",
    "Turbine Drip Oils",
    "Other Lubricants",
    "Slide Way Lubricants",
    "Pneumatic Equipment Lubricants",
    "Water Turbine Bearing Oils",
    "Fluid-Filled Transformers",
    "2-Cycle Engine Oils",
    "Engine Crankcase Oil",
]

FAMILY_BY_CATEGORY = {
    "Heat Transfer Fluids": "TF",
    "Hydraulic Fluids": "H",
    "Lavatory Flushing Fluids": "TF",
    "Greases": "G",
    "Gear Lubricants": "T",
    "Turbine Drip Oils": "U",
    "Water Turbine Bearing Oils": "U",
    "Fluid-Filled Transformers": "E",
    "2-Cycle Engine Oils": "M",
    "Engine Crankcase Oil": "M",
}


class ProductTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict] = []
        self.row: dict | None = None
        self.cell_index = -1
        self.in_name = False
        self.in_cell = False
        self.name_parts: list[str] = []
        self.company_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "tr" and values.get("data-rk"):
            self.row = {
                "product_id": values["data-rk"],
                "product_name": "",
                "company": "",
                "description_sha256": "",
                "usda_certified_biobased": False,
                "mandatory_federal_purchasing": False,
            }
            self.cell_index = -1
        elif self.row is not None and tag == "td":
            self.cell_index += 1
            self.in_cell = True
        elif self.row is not None and tag == "img":
            title = values.get("title", "")
            if "granted a BioPreferred Program Certified label" in title:
                self.row["usda_certified_biobased"] = True
            if "mandatory federal purchasing product category" in title:
                self.row["mandatory_federal_purchasing"] = True
        elif self.row is not None and tag == "span" and ":id-" in values.get("id", ""):
            self.in_name = True
            self.name_parts = []
            description = html.unescape(values.get("title", ""))
            description = re.sub(r"<[^>]+>", " ", description)
            description = " ".join(description.split())
            if description:
                self.row["description_sha256"] = hashlib.sha256(description.encode("utf-8")).hexdigest()

    def handle_data(self, data: str) -> None:
        if self.row is None:
            return
        if self.in_name:
            self.name_parts.append(data)
        elif self.in_cell and self.cell_index == 3:
            self.company_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.row is None:
            return
        if tag == "span" and self.in_name:
            self.row["product_name"] = " ".join("".join(self.name_parts).split())
            self.in_name = False
        elif tag == "td":
            if self.cell_index == 3:
                self.row["company"] = " ".join("".join(self.company_parts).split())
                self.company_parts = []
            self.in_cell = False
        elif tag == "tr":
            if self.row["product_name"] and self.row["company"]:
                self.rows.append(self.row)
            self.row = None


def family_for(categories: list[str], name: str) -> str:
    for category in categories:
        if category in FAMILY_BY_CATEGORY:
            return FAMILY_BY_CATEGORY[category]
    value = name.casefold()
    if "grease" in value:
        return "G"
    if "hydraulic" in value:
        return "H"
    if any(token in value for token in ["coolant", "heat transfer", "flushing fluid"]):
        return "TF"
    if any(token in value for token in ["gear oil", "transmission fluid"]):
        return "T"
    if any(token in value for token in ["engine oil", "motor oil", "2-cycle", "2 cycle", "two-cycle"]):
        return "M"
    return "S"


def normalized_rows_sha256(rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def view_state(payload: str) -> str:
    partial = re.findall(r'javax\.faces\.ViewState[^>]*><!\[CDATA\[([^\]]+)', payload)
    if partial:
        return html.unescape(partial[-1])
    inputs = re.findall(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)', payload)
    assert inputs
    return html.unescape(inputs[-1])


def category_links(payload: str) -> dict[str, str]:
    links = {}
    pattern = re.compile(r'<a id="([^"]+)"[^>]*>([^<]+)</a>')
    for source_id, label in pattern.findall(payload):
        links[html.unescape(label).strip()] = html.unescape(source_id)
    return links


def ajax_category(opener, action_url: str, state: str, source_id: str) -> str:
    data = {
        "javax.faces.partial.ajax": "true",
        "javax.faces.source": source_id,
        "javax.faces.partial.execute": "@all",
        "javax.faces.partial.render": "subpage-content-wrap catalog-browse-and-search-form:catalog-search catalog-browse-and-search-form",
        source_id: source_id,
        "catalog-browse-and-search-form": "catalog-browse-and-search-form",
        "javax.faces.ViewState": state,
    }
    request = urllib.request.Request(
        action_url,
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": URL,
        },
    )
    with opener.open(request, timeout=120) as response:
        return response.read().decode("utf-8", "ignore")


def updated_html(payload: str, update_id: str) -> str:
    pattern = re.compile(rf'<update id="{re.escape(update_id)}"><!\[CDATA\[(.*?)\]\]></update>', re.S)
    match = pattern.search(payload)
    assert match, update_id
    return match.group(1)


def main() -> None:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    request = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    with opener.open(request, timeout=120) as response:
        initial = response.read().decode("utf-8", "ignore")
        action_url = urllib.parse.urljoin(URL, response.url)
    links = category_links(initial)
    missing = sorted(set(CATEGORIES) - set(links))
    assert not missing, missing
    state = view_state(initial)
    by_product: dict[str, dict] = {}
    category_counts = {}
    source_occurrences = defaultdict(int)

    for category in CATEGORIES:
        payload = ajax_category(opener, action_url, state, links[category])
        state = view_state(payload)
        parser = ProductTableParser()
        parser.feed(updated_html(payload, "subpage-content-wrap"))
        category_counts[category] = len(parser.rows)
        for row in parser.rows:
            product_id = row["product_id"]
            source_occurrences[product_id] += 1
            if product_id not in by_product:
                by_product[product_id] = {**row, "categories": set()}
            else:
                current = by_product[product_id]
                assert current["product_name"] == row["product_name"], product_id
                assert current["company"] == row["company"], product_id
                current["usda_certified_biobased"] |= row["usda_certified_biobased"]
                current["mandatory_federal_purchasing"] |= row["mandatory_federal_purchasing"]
                current["description_sha256"] = current["description_sha256"] or row["description_sha256"]
            by_product[product_id]["categories"].add(category)

    products = []
    for product_id, row in by_product.items():
        categories = sorted(row.pop("categories"))
        products.append({
            **row,
            "categories": categories,
            "family_code": family_for(categories, row["product_name"]),
            "source_id": "usda-biopreferred",
            "source_url": URL,
            "source_record_id": product_id,
            "source_occurrences": source_occurrences[product_id],
            "snapshot_date": SNAPSHOT_DATE,
        })
    products.sort(key=lambda row: int(row["product_id"]))
    assert len(products) == len({row["product_id"] for row in products})
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in products), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": "usda-biopreferred",
        "source_url": URL,
        "rows": len(products),
        "companies": len({row["company"] for row in products}),
        "certified_biobased_rows": sum(row["usda_certified_biobased"] for row in products),
        "mandatory_federal_purchasing_rows": sum(row["mandatory_federal_purchasing"] for row in products),
        "source_occurrences": sum(source_occurrences.values()),
        "duplicate_category_occurrences_merged": sum(source_occurrences.values()) - len(products),
        "category_counts": category_counts,
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "normalized_factual_rows_sha256": normalized_rows_sha256(products),
        "copyright_scope": "Product/company/category/program facts retained; marketing descriptions are not republished, only SHA-256 evidence hashes are stored.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
