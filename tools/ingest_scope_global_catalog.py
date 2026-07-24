#!/usr/bin/env python3
"""Normalize Scope Lubricants' complete live manufacturer product catalog."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/scope-global-products.jsonl"
REPORT = ROOT / "data/scope-global-report.json"
SOURCE_ID = "SCOPE_GLOBAL_COMPLETE_LIVE_PRODUCT_CATALOG"
BASE_URL = "https://scopelubricant.com/"
API_URL = BASE_URL + "wp-json/wp/v2/"
CATALOG_PDF_URL = (
    BASE_URL + "wp-content/uploads/2023/12/Scope-Lubricants-Products.pdf"
)
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"

EXPECTED_PRODUCT_IDS = {
    743, 762, 775, 776, 778, 781, 782, 794, 796, 797, 798,
    1355, 1363, 1364, 1431, 1432, 1433, 1434, 1435, 1436, 1437,
    1438, 1439, 1440, 1441, 1442, 1443, 1444, 1445, 1465, 1468,
    1469, 1470, 1471, 1472, 1474, 1475, 1481, 1482, 1484, 1485,
    1486, 1487, 2348, 2350, 2351, 2352, 2618, 2719, 2728, 2736,
    2740, 3114, 3123, 3125, 3127, 3156, 3158, 3163, 3308, 3312,
    3924,
}
CATEGORY_NAMES = {
    41: "Synthetic Engine Oils",
    42: "Automotive Gear Oils",
    43: "Diesel Engine Oils",
    44: "Gasoline Engine Oils",
    45: "Industrial Lubricants",
    46: "Automatic Transmission Fluids",
    56: "Brake Fluids",
    57: "Greases",
    58: "Marine Lubricants",
    60: "Coolants",
    188: "E-Vehicle / Hybrid Fluid",
    213: "Specialty Lubricants",
}

# Each tuple is (professional grade field, source grade, extra specifications).
VARIANTS: dict[int, list[tuple[str, str, dict]]] = {
    3308: [
        ("sae_engine", sae, {"tbn": tbn})
        for tbn in ("24", "30", "40", "50")
        for sae in ("30", "40", "50")
    ],
    3158: [("sae_engine", x, {}) for x in ("0W-16", "0W-20", "5W-20", "5W-30", "5W-40")],
    3127: [("dot", "DOT 5.1", {})],
    2719: [("sae_engine", "0W-20", {})],
    2728: [("source_grade", "Hybrid/EV ATF", {})],
    2618: [("source_grade", "Hybrid/EV thermal-management fluid", {})],
    2736: [("dot", "DOT 4", {})],
    2740: [("nlgi", "2", {})],
    743: [("sae_engine", x, {}) for x in ("5W-30", "5W-40")],
    762: [("sae_engine", x, {}) for x in ("5W-30", "5W-40", "5W-50")],
    3114: [("sae_engine", "10W-40", {})],
    2348: [("sae_engine", x, {}) for x in ("10W-30", "10W-40", "20W-40")],
    2350: [("sae_engine", x, {}) for x in ("10W-30", "15W-40", "20W-50", "40")],
    2351: [("sae_engine", x, {}) for x in ("10W-30", "10W-40", "15W-40")],
    2352: [("sae_engine", x, {}) for x in ("15W-40", "10W-40", "20W-50")],
    782: [("iso_vg", x, {}) for x in ("32", "46", "68", "100", "150", "220")],
    1363: [("iso_vg", x, {}) for x in ("32", "46", "68", "100")],
    3125: [("iso_vg", x, {}) for x in ("32", "46", "68")],
    1438: [("sae_engine", x, {}) for x in ("10W-30", "10W-40", "15W-40")],
    1431: [("sae_engine", x, {}) for x in ("10W-30", "10W-40", "15W-40", "20W-40", "20W-50")],
    1468: [("iso_vg", x, {}) for x in ("32", "46", "68", "100")],
    1439: [("sae_engine", x, {}) for x in ("10W-30", "10W-40", "15W-40", "20W-50")],
    1432: [("sae_engine", x, {}) for x in ("10W-30", "10W-40", "15W-40", "20W-40", "20W-50")],
    797: [("nlgi", x, {}) for x in ("1", "2", "3")],
    1469: [("iso_vg", x, {}) for x in ("32", "46", "68", "100", "150", "220", "320", "460")],
    1445: [("sae_gear", x, {}) for x in ("90", "140", "80W-90", "85W-90", "85W-140")],
    1440: [("sae_engine", x, {}) for x in ("10W-40", "15W-40", "20W-50", "30")],
    1433: [("sae_engine", x, {}) for x in ("10W-40", "15W-40", "20W-40", "20W-50", "40", "50")],
    796: [("nlgi", x, {}) for x in ("2", "3")],
    3312: [("nlgi", "2", {})],
    1470: [("iso_vg", x, {}) for x in ("32", "46", "68", "100", "150", "220", "320", "460")],
    1441: [("sae_engine", x, {}) for x in ("25W-60", "20W-50", "15W-40", "40", "50")],
    1434: [("sae_engine", x, {}) for x in ("10W-40", "15W-40", "20W-40", "20W-50", "40", "50")],
    1364: [("nlgi", "2", {})],
    1481: [("nlgi", "1.5", {})],
    1355: [("source_grade", "CVT", {})],
    3163: [("source_grade", "DX-VI", {})],
    1471: [("iso_vg", x, {}) for x in ("32", "46", "68", "100")],
    1442: [("sae_engine", x, {}) for x in ("10W-40", "15W-40", "20W-50", "40", "50")],
    1435: [("sae_engine", x, {}) for x in ("20W-50", "10W-40", "10W-30", "20W-40")],
    778: [("source_grade", "DX-III", {})],
    1482: [("nlgi", "2", {})],
    1472: [("iso_vg", x, {}) for x in ("32", "46", "68", "100")],
    1443: [("sae_engine", x, {}) for x in ("15W-40", "20W-50", "40", "50")],
    1436: [("sae_engine", x, {}) for x in ("20", "30")],
    3156: [("dot", "DOT 4", {})],
    794: [("dot", "DOT 3", {})],
    781: [("source_grade", "DX-II", {})],
    1486: [
        ("sae_engine", sae, {"tbn": tbn})
        for tbn in ("12", "15") for sae in ("30", "40", "50")
    ],
    1485: [
        ("sae_engine", sae, {"tbn": tbn})
        for tbn in ("6", "9") for sae in ("30", "40", "50")
    ],
    1474: [("source_grade", "Soluble Cutting Oil", {})],
    1444: [("sae_engine", x, {}) for x in ("15W-40", "20W-50", "40", "50")],
    1437: [("source_grade", "TC-W3", {})],
    1487: [("sae_engine", x, {}) for x in ("30", "40", "50")],
    3123: [("nlgi", x, {}) for x in ("2", "3")],
    1484: [("nlgi", x, {}) for x in ("2", "3")],
    1475: [
        ("source_grade", "Neat Cut Ferrous", {}),
        ("source_grade", "Neat Cut Non-Ferrous", {}),
    ],
    1465: [("sae_gear", x, {}) for x in ("10W", "30", "40", "50")],
    3924: [("source_grade", "DCT", {})],
    798: [("source_grade", "Freezo 100 Coolant", {})],
    776: [("sae_gear", x, {}) for x in ("90", "140", "80W-90", "85W-90", "85W-140")],
    775: [
        ("iso_vg", iso, {"david_brown_grade": db})
        for iso, db in zip(
            ("68", "100", "150", "220", "320", "460"),
            ("2EP", "3EP", "4EP", "5EP", "6EP", "7EP"),
        )
    ],
}
API_BY_ID = {
    3158: ["SP"], 2719: ["SP"], 743: ["SN"], 762: ["SM", "CF"],
    3114: ["SP"], 2348: ["SM", "CF"], 2350: ["SL", "CF"],
    2351: ["CK-4"], 2352: ["CI-4", "SL"], 1438: ["CJ-4"],
    1431: ["SN"], 1439: ["CI-4", "SL"], 1432: ["SM"],
    1440: ["CH-4", "SJ"], 1433: ["SL", "CF"], 1441: ["CG-4", "SJ"],
    1434: ["SJ", "CF"], 1442: ["CF-4", "SJ"], 1435: ["SJ", "CF"],
    1443: ["CF-4", "SG"], 1436: ["TC"], 1444: ["CF", "SF"],
}
API_GL_BY_ID = {1445: ["GL-5"], 776: ["GL-4"]}
FAMILY_BY_ID = {
    **{product_id: "M" for product_id in (
        3158, 2719, 743, 762, 3114, 2348, 2350, 2351, 2352,
        1438, 1431, 1439, 1432, 1440, 1433, 1441, 1434, 1442,
        1435, 1443, 1436, 1444, 1437, 3308, 1486, 1485, 1487,
    )},
    **{product_id: "T" for product_id in (
        2728, 1355, 3163, 778, 781, 1465, 3924, 1445, 776,
    )},
    **{product_id: "TF" for product_id in (
        3127, 2618, 2736, 3156, 794, 798,
    )},
    **{product_id: "G" for product_id in (
        2740, 797, 796, 3312, 1364, 1481, 1482, 3123, 1484,
    )},
    **{product_id: "H" for product_id in (782, 1363)},
    **{product_id: "C" for product_id in (3125, 1471)},
    **{product_id: "I" for product_id in (
        1468, 1469, 1470, 1472, 775,
    )},
    **{product_id: "S" for product_id in (1474, 1475)},
}
EXACT_EXISTING_TARGETS = {
    (1435, "20W-50"): ("JASO_4T", "2283"),
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


class ProductPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.div_depth = 0
        self.table_start_depth = 0
        self.spec_start_depth = 0
        self.in_cell = False
        self.cell_buffer: list[str] = []
        self.current_row: list[str] = []
        self.table_rows: list[list[str]] = []
        self.spec_text: list[str] = []
        self.pdf_urls: list[str] = []
        self.availability = ""

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        if tag == "div":
            self.div_depth += 1
            classes = values.get("class", "") or ""
            if "product-specification-table" in classes:
                self.table_start_depth = self.div_depth
            if "woocommerce-Tabs-panel--specification" in classes:
                self.spec_start_depth = self.div_depth
        if self.table_start_depth and tag in {"td", "th"}:
            self.in_cell = True
            self.cell_buffer = []
        if tag == "a":
            url = values.get("href", "") or ""
            if url.lower().split("?", 1)[0].endswith(".pdf"):
                self.pdf_urls.append(url)
        if (
            tag == "meta"
            and values.get("property") == "product:availability"
        ):
            self.availability = values.get("content", "") or ""

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_buffer.append(data)
        if self.spec_start_depth:
            self.spec_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.table_start_depth and tag in {"td", "th"} and self.in_cell:
            value = re.sub(
                r"\s+", " ", html.unescape(" ".join(self.cell_buffer))
            ).strip()
            self.current_row.append(value)
            self.in_cell = False
        if self.table_start_depth and tag == "tr":
            if self.current_row:
                self.table_rows.append(self.current_row)
            self.current_row = []
        if tag == "div":
            if self.table_start_depth == self.div_depth:
                self.table_start_depth = 0
            if self.spec_start_depth == self.div_depth:
                self.spec_start_depth = 0
            self.div_depth -= 1


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def base_name_for(title: str) -> str:
    value = clean(title).split("|", 1)[0].strip()
    value = re.sub(
        r"\s+[–-]\s+(?:Lithium Complex Grease)$", "", value,
        flags=re.I,
    )
    return value


def token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold().replace("o", "0"))


def variant_is_evidenced(
    table_rows: list[list[str]],
    field: str,
    grade: str,
    extra: dict,
    source_title: str,
) -> bool:
    table_tokens = {token(cell) for row in table_rows for cell in row}
    if field == "source_grade":
        return True
    header_tokens = {
        token(cell) for cell in (table_rows[0] if table_rows else [])
    }
    grade_tokens = {token(grade)}
    if field in {"sae_engine", "sae_gear"}:
        grade_tokens.add(token("SAE " + grade))
    elif field == "iso_vg":
        grade_tokens.update({token("ISO " + grade), token("ISO VG " + grade)})
    elif field == "nlgi":
        grade_tokens.add(token("NLGI " + grade))
    if not (
        grade_tokens.intersection(table_tokens)
        or any(
            header.endswith(candidate)
            for header in header_tokens
            for candidate in grade_tokens
        )
    ):
        return False
    if (
        extra.get("tbn")
        and token(extra["tbn"] + " TBN") not in table_tokens
        and token(extra["tbn"] + " TBN") not in token(source_title)
    ):
        return False
    if (
        extra.get("david_brown_grade")
        and token(extra["david_brown_grade"]) not in table_tokens
    ):
        return False
    return True


def main() -> None:
    product_rows = json.loads(fetch(
        API_URL
        + "product?per_page=100&_fields=id,slug,link,date,modified,title,"
        + "content,excerpt,product_cat"
    ))
    if len(product_rows) != 62:
        raise RuntimeError(
            f"Scope live product denominator changed: {len(product_rows)}"
        )
    if {row["id"] for row in product_rows} != EXPECTED_PRODUCT_IDS:
        raise RuntimeError("Scope reviewed live product identity set changed")
    if set(VARIANTS) != EXPECTED_PRODUCT_IDS:
        raise RuntimeError("Scope reviewed variant map is incomplete")
    if set(FAMILY_BY_ID) != EXPECTED_PRODUCT_IDS:
        raise RuntimeError("Scope reviewed family map is incomplete")

    taxonomy_rows = json.loads(fetch(API_URL + "product_cat?per_page=100"))
    taxonomy_by_id = {
        row["id"]: clean(row["name"]) for row in taxonomy_rows
    }
    for category_id, name in CATEGORY_NAMES.items():
        if taxonomy_by_id.get(category_id) != name:
            raise RuntimeError(
                f"Scope product category changed: {category_id}"
            )

    def fetch_product(row: dict) -> tuple[int, bytes]:
        return row["id"], fetch(row["link"])

    with ThreadPoolExecutor(max_workers=4) as pool:
        page_payloads = dict(pool.map(fetch_product, product_rows))

    parsed_pages = {}
    all_pdf_urls = set()
    for row in product_rows:
        parser = ProductPageParser()
        parser.feed(page_payloads[row["id"]].decode(errors="replace"))
        if not parser.table_rows and row["id"] != 2740:
            raise RuntimeError(
                f"Scope product specification table missing: {row['id']}"
            )
        if parser.availability != "instock":
            raise RuntimeError(
                f"Scope live page availability changed: {row['id']}"
            )
        variants_evidenced = all(
            variant_is_evidenced(
                parser.table_rows,
                field,
                grade,
                extra,
                row["title"]["rendered"],
            )
            for field, grade, extra in VARIANTS[row["id"]]
        )
        if all(
            not extra and token(grade) in token(row["title"]["rendered"])
            for _, grade, extra in VARIANTS[row["id"]]
        ):
            variants_evidenced = True
        if not variants_evidenced:
            raise RuntimeError(
                f"Scope reviewed variant table changed: {row['id']}"
            )
        pdf_urls = sorted(set(parser.pdf_urls))
        all_pdf_urls.update(pdf_urls)
        parsed_pages[row["id"]] = {
            "table_rows": parser.table_rows,
            "specification_text": clean(" ".join(parser.spec_text)),
            "pdf_urls": pdf_urls,
            "availability": parser.availability,
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        pdf_payloads = dict(zip(
            sorted(all_pdf_urls),
            pool.map(fetch, sorted(all_pdf_urls)),
        ))
    catalog_pdf = fetch(CATALOG_PDF_URL)

    records = []
    page_facts = []
    for row in sorted(product_rows, key=lambda item: item["id"]):
        product_id = row["id"]
        parsed = parsed_pages[product_id]
        source_title = clean(row["title"]["rendered"])
        base_name = base_name_for(source_title)
        categories = sorted(
            CATEGORY_NAMES[category_id]
            for category_id in row["product_cat"]
            if category_id in CATEGORY_NAMES
        )
        documents = [
            {
                "url": url,
                "sha256": hashlib.sha256(pdf_payloads[url]).hexdigest(),
                "bytes": len(pdf_payloads[url]),
            }
            for url in parsed["pdf_urls"]
        ]
        specification_sha = hashlib.sha256(
            parsed["specification_text"].encode()
        ).hexdigest()
        table_sha = hashlib.sha256(json.dumps(
            parsed["table_rows"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()).hexdigest()
        page_facts.append({
            "product_id": product_id,
            "slug": row["slug"],
            "title": source_title,
            "modified": row["modified"],
            "categories": categories,
            "table_sha256": table_sha,
            "specification_text_sha256": specification_sha,
            "documents": documents,
            "variant_rows": len(VARIANTS[product_id]),
        })
        for variant_index, (field, grade, extra) in enumerate(
            VARIANTS[product_id], 1
        ):
            target = EXACT_EXISTING_TARGETS.get(
                (product_id, grade), ("", "")
            )
            specifications = {
                field: grade,
                "source_grade": grade,
                **extra,
                "api": API_BY_ID.get(product_id, []),
                "api_gl": API_GL_BY_ID.get(product_id, []),
                "source_product_id": product_id,
                "source_slug": row["slug"],
                "source_categories": categories,
                "source_modified": row["modified"],
                "source_availability_meta": parsed["availability"],
                "source_table_sha256": table_sha,
                "source_specification_text_sha256": specification_sha,
                "source_document_urls": [item["url"] for item in documents],
                "source_document_sha256": [
                    item["sha256"] for item in documents
                ],
                "source_quality_flags": [
                    "complete_live_manufacturer_product_endpoint",
                    "product_grade_read_from_live_technical_table",
                    "source_reported_specifications_not_independent_approvals",
                    "zero_price_quote_workflow_not_treated_as_retail_offer",
                    "somalia_named_on_manufacturer_catalog_map_but_no_sku_availability_inferred",
                ],
            }
            if product_id == 1437:
                specifications["performance"] = ["NMMA TC-W3"]
            if product_id == 1465:
                specifications["performance"] = ["Caterpillar TO-4"]
            if product_id in {1355, 2728}:
                specifications["performance"] = ["CVT/ATF application"]
            if product_id == 3924:
                specifications["performance"] = ["DCT application"]
            grade_label = (
                f"SAE {grade}" if field in {"sae_engine", "sae_gear"}
                else f"ISO VG {grade}" if field == "iso_vg"
                else f"NLGI {grade}" if field == "nlgi"
                else grade
            )
            if extra.get("tbn"):
                grade_label += f" TBN {extra['tbn']}"
            facts = {
                "product_id": product_id,
                "base_name": base_name,
                "source_title": source_title,
                "family": FAMILY_BY_ID[product_id],
                "field": field,
                "grade": grade,
                "extra": extra,
                "categories": categories,
                "modified": row["modified"],
                "table_sha256": table_sha,
                "specification_text_sha256": specification_sha,
                "documents": documents,
                "api": specifications["api"],
                "api_gl": specifications["api_gl"],
                "target": target,
            }
            records.append({
                "source_id": SOURCE_ID,
                "source_record_id": (
                    f"SCOPE-{product_id}-{variant_index:02d}"
                ),
                "source_url": row["link"],
                "snapshot_date": SNAPSHOT_DATE,
                "market": "Global manufacturer catalog",
                "manufacturer": "United Grease & Lubricants Co. LLC",
                "brand": "SCOPE",
                "product_name": f"SCOPE {base_name} {grade_label}".strip(),
                "source_product_name": source_title,
                "family_code": FAMILY_BY_ID[product_id],
                "existing_target_source_id": target[0],
                "existing_target_source_record_id": target[1],
                "evidence_status": "official_live_manufacturer_product_catalog",
                "lifecycle_status": "live_current_manufacturer_product_page",
                "specifications": specifications,
                "source_facts_sha256": hashlib.sha256(json.dumps(
                    facts, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"),
                ).encode()).hexdigest(),
            })

    if len(records) != 200:
        raise RuntimeError(
            f"Scope product-grade denominator changed: {len(records)}"
        )
    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "complete_live_manufacturer_product_catalog",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "product_endpoint_rows": len(product_rows),
        "nonempty_product_categories": len(CATEGORY_NAMES),
        "taxonomy_product_counts": {
            CATEGORY_NAMES[row["id"]]: row["count"]
            for row in taxonomy_rows if row["id"] in CATEGORY_NAMES
        },
        "category_occurrences": sum(
            len(row["product_cat"]) for row in product_rows
        ),
        "multi_category_products": sum(
            len(row["product_cat"]) > 1 for row in product_rows
        ),
        "identity_rows": len(records),
        "family_identity_counts": dict(sorted(Counter(
            row["family_code"] for row in records
        ).items())),
        "grade_field_counts": dict(sorted(Counter(
            next(
                field for field in (
                    "sae_engine", "sae_gear", "iso_vg", "nlgi", "dot",
                    "source_grade",
                )
                if field in row["specifications"]
            )
            for row in records
        ).items())),
        "linked_document_observations": sum(
            len(row["documents"]) for row in page_facts
        ),
        "unique_linked_document_urls": len(all_pdf_urls),
        "unique_linked_document_payloads": len({
            hashlib.sha256(payload).hexdigest()
            for payload in pdf_payloads.values()
        }),
        "catalog_pdf_url": CATALOG_PDF_URL,
        "catalog_pdf_sha256": hashlib.sha256(catalog_pdf).hexdigest(),
        "catalog_pdf_bytes": len(catalog_pdf),
        "catalog_map_market_presence_observation": "Somalia",
        "somalia_sku_availability_inferred": False,
        "exact_existing_identity_matches": len(EXACT_EXISTING_TARGETS),
        "new_manufacturer_catalog_identities": (
            len(records) - len(EXACT_EXISTING_TARGETS)
        ),
        "page_facts": page_facts,
        "normalized_output_sha256": hashlib.sha256(
            output_text.encode()
        ).hexdigest(),
        "publication_scope": (
            "Factual product names, professional grades, source-reported API/GL "
            "classes, category membership, document links and evidence hashes "
            "only; descriptions, technical tables, TDS/MSDS files, artwork and "
            "contacts are not redistributed."
        ),
        "denominator_note": (
            "The live WordPress product endpoint contains 62 products in 12 "
            "non-empty technical categories and every card is included. Reviewed "
            "technical-table expansion produces 200 product-grade identities, "
            "including SAE×TBN marine combinations. The manufacturer catalog map "
            "names Somalia as market presence, but the 200 identities remain one "
            "global manufacturer catalog and are not multiplied into Somalia SKU "
            "availability or offers."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "product_cards": len(product_rows),
        "identity_rows": len(records),
        "linked_documents": len(all_pdf_urls),
        "output_sha256": report["normalized_output_sha256"],
    }))


if __name__ == "__main__":
    main()
