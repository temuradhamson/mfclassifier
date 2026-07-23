#!/usr/bin/env python3
"""Build the current YPFB Refinación lubricant catalog from official product pages.

The public ANH operator list is not a product registry.  This source therefore
uses only YPFB Refinación product cards and their official technical sheets.
Marketing prose is deliberately excluded from the normalized output.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urldefrag


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/bolivia-ypfb-current-lubricants.jsonl"
REPORT = ROOT / "data/bolivia-ypfb-current-lubricants-report.json"
API_URL = "https://www.ypfbrefinacion.com.bo/wp-json/wp/v2/pages?per_page=100&context=view"
CATALOG_URL = "https://www.ypfbrefinacion.com.bo/wp-content/uploads/2024/05/CProductos.pdf"
SNAPSHOT_DATE = "2026-07-23"
UA = "MFClassifier evidence catalog/1.0"


def variants(family: str, grades: list[dict], packages: list[str], **specs: object) -> dict:
    return {"family_code": family, "grades": grades, "packages": packages, "specs": specs}


PRODUCTS = {
    # Automotive line: one product card per commercial grade.
    "extrem-g13-sae-10w-30-api-sn-plus": variants(
        "M", [{"sae_engine": "10W-30"}], ["4 L", "1 L"], api=["SN PLUS"], ilsac=["GF-5"]
    ),
    "extrem-g13-sae-10w-40-api-sn-plus": variants(
        "M", [{"sae_engine": "10W-40"}], ["4 L", "1 L"], api=["SN PLUS"]
    ),
    "gx-extra-sae-15w-40-api-sl-cf": variants(
        "M", [{"sae_engine": "15W-40"}], ["4 L", "1 L"], api=["SL", "CF"]
    ),
    "gx-extra-sae-20w-50-api-sl-cf": variants(
        "M", [{"sae_engine": "20W-50"}], ["4 L", "1 L"], api=["SL", "CF"]
    ),
    "gx-extra-sae-40-api-sl-cf": variants(
        "M", [{"sae_engine": "40"}], ["4 L", "1 L"], api=["SL", "CF"]
    ),
    "moto-4t-sae-20w-50": variants(
        "M", [{"sae_engine": "20W-50"}], ["1 L"], api=["SL"], jaso=["MA", "MA2"]
    ),
    "lub-2t-sae-30-api-tc": variants(
        "M", [{"sae_engine": "30"}], ["1 L"], api=["TC"], jaso=["FB"]
    ),
    "dx-turbo-sae-15w-40-api-ci-4-sl": variants(
        "M", [{"sae_engine": "15W-40"}], ["20 L", "4 L"], api=["CI-4", "SL"], acea=["E7"]
    ),
    "dx-plus-sae-20w-50-api-cg-4-sl": variants(
        "M", [{"sae_engine": "20W-50"}], ["20 L", "4 L"], api=["CG-4", "SL"]
    ),
    "dx-plus-sae-40-api-cg-4-sl": variants(
        "M", [{"sae_engine": "40"}], ["20 L", "4 L"], api=["CG-4", "SL"]
    ),
    "t-mec-t4-sae-80w-90-api-gl-4": variants(
        "T", [{"sae_gear": "80W-90"}], ["20 L"], api_gl=["GL-4"]
    ),
    "t-mec-t5-sae-80w-90-api-gl-5": variants(
        "T", [{"sae_gear": "80W-90"}], ["20 L"], api_gl=["GL-5"]
    ),
    "t-mec-t5-sae-85w-140-api-gl-5": variants(
        "T", [{"sae_gear": "85W-140"}], ["20 L"], api_gl=["GL-5"]
    ),
    # Industrial line. Multi-grade tables are expanded to one product variant
    # per explicitly published SAE/ISO VG/NLGI grade.
    "lub-had-hidraulico-anti-desgaste-iso-68": variants(
        "H", [{"iso_vg": "68"}], ["20 L", "208 L"]
    ),
    "litiogras-nlgi-n2-n3": variants(
        "G",
        [{"nlgi": "2", "din": ["DIN 51825 KP2K"]}, {"nlgi": "3", "din": ["DIN 51825 KP3K"]}],
        ["16 kg"],
        thickener="lithium soap",
    ),
    "lub-cyo": variants(
        "I", [{"iso_vg": "150"}, {"iso_vg": "220"}], ["208 L"], application="steam and gas cylinders"
    ),
    "lub-ftt": variants(
        "TF", [{"iso_vg": grade} for grade in ("32", "46", "68", "100")], ["208 L"]
    ),
    "lub-atb": variants(
        "I",
        [{"iso_vg": grade} for grade in ("68", "100", "150")],
        ["208 L"],
        performance=["General Electric GEK-32568-F"],
    ),
    "lub-mpn": variants(
        "I", [{"iso_vg": "100"}, {"iso_vg": "150"}], ["208 L"], application="pneumatic rock-drill oil"
    ),
    "lub-eps": variants(
        "G",
        [{"iso_vg": grade} for grade in ("68", "220", "320")],
        ["208 L"],
        performance=["U.S. Steel 224", "AGMA 9005-E02", "DIN 51517-3 CLP", "GM LS 2 EP Gear Oil"],
    ),
    "lub-aoh": variants(
        "H", [{"iso_vg": grade} for grade in ("32", "46", "68", "100", "150")], ["208 L"]
    ),
    "lub-mtl": variants(
        "T",
        [{"sae_gear": "80W-90"}, {"sae_gear": "85W-140"}],
        ["208 L"],
        api_gl=["GL-5"],
        performance=["MIL-L-2105D"],
    ),
    "lub-fep": variants(
        "T",
        [{"sae_gear": "10W"}, {"sae_gear": "30"}, {"sae_gear": "50"}],
        ["208 L"],
        api=["CD"],
        performance=["Caterpillar TO-4", "Allison C-4"],
    ),
    "lub-meg-aa-sae-40": variants(
        "M", [{"sae_engine": "40"}], ["208 L"], application="ashless stationary natural-gas engine oil"
    ),
    "lub-meg": variants(
        "M", [{"sae_engine": "40"}], ["208 L"], api=["CD"], application="low-ash stationary natural-gas engine oil"
    ),
    "lub-fta": variants(
        "T", [{"sae_gear": "10W-30"}], ["20 L"], application="UTTO agricultural tractor fluid"
    ),
    "lub-had-tp": variants(
        "H",
        [{"iso_vg": grade} for grade in ("32", "46", "68", "100")],
        ["20 L", "208 L"],
        performance=["DIN 51524-2", "ISO 11158 HM"],
    ),
}


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def pdf_links(rendered: str) -> list[str]:
    links = re.findall(r"""href=["']([^"']+\.pdf(?:#[^"']*)?)["']""", html.unescape(rendered), re.I)
    return list(dict.fromkeys(urldefrag(link)[0] for link in links))


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    api_bytes = get(API_URL)
    pages = json.loads(api_bytes)
    selected = {}
    for page in pages:
        link = page.get("link", "")
        match = re.search(r"/linea-(?:automotriz|industrial)/([^/]+)/", link)
        if not match:
            continue
        slug = match.group(1)
        if slug in PRODUCTS:
            selected[slug] = page

    missing = sorted(set(PRODUCTS) - set(selected))
    if missing:
        raise RuntimeError(f"Missing expected YPFB product pages: {missing}")

    catalog_bytes = get(CATALOG_URL)
    catalog_sha = sha256(catalog_bytes)
    document_cache: dict[str, str] = {CATALOG_URL: catalog_sha}
    rows = []
    page_facts = []
    for slug in sorted(PRODUCTS):
        page = selected[slug]
        config = PRODUCTS[slug]
        title = clean_title(page["title"]["rendered"])
        rendered = page["content"]["rendered"]
        links = pdf_links(rendered)
        for link in links:
            if link not in document_cache:
                document_cache[link] = sha256(get(link))
        technical_sheet = next((link for link in links if "SEGURIDAD" not in link.upper()), "")
        safety_sheets = [link for link in links if "SEGURIDAD" in link.upper()]
        facts = {
            "wp_page_id": page["id"],
            "slug": slug,
            "title": title,
            "modified": page["modified"],
            "link": page["link"],
            "pdf_links": links,
        }
        facts_sha = sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True).encode())
        page_facts.append(facts)
        for index, grade in enumerate(config["grades"], 1):
            technical = {
                "sae_engine": grade.get("sae_engine", ""),
                "sae_gear": grade.get("sae_gear", ""),
                "iso_vg": grade.get("iso_vg", ""),
                "nlgi": grade.get("nlgi", ""),
                "api": config["specs"].get("api", []),
                "api_gl": config["specs"].get("api_gl", []),
                "acea": config["specs"].get("acea", []),
                "ilsac": config["specs"].get("ilsac", []),
                "jaso": config["specs"].get("jaso", []),
                "din": grade.get("din", config["specs"].get("din", [])),
                "performance": config["specs"].get("performance", []),
            }
            grade_label = (
                technical["sae_engine"]
                or technical["sae_gear"]
                or (f"ISO VG {technical['iso_vg']}" if technical["iso_vg"] else "")
                or (f"NLGI {technical['nlgi']}" if technical["nlgi"] else "")
            )
            product_name = title if len(config["grades"]) == 1 else f"{title} — {grade_label}"
            row = {
                "source_id": "BOLIVIA_YPFB_CURRENT_LUBRICANT_CATALOG",
                "source_record_id": f"YPFB-BO-{page['id']}-{index}",
                "market": "Bolivia",
                "manufacturer": "YPFB Refinación S.A.",
                "brand": "YPFB",
                "product_name": product_name,
                "product_line": "automotive" if "/linea-automotriz/" in page["link"] else "industrial",
                "family_code": config["family_code"],
                "packages": config["packages"],
                "technical": technical,
                "application": config["specs"].get("application", ""),
                "thickener": config["specs"].get("thickener", ""),
                "lifecycle_status": "current_official_catalog",
                "evidence_status": "official_state_owned_manufacturer_product_catalog",
                "snapshot_date": SNAPSHOT_DATE,
                "source_url": page["link"],
                "source_page_id": page["id"],
                "source_page_modified": page["modified"],
                "source_page_facts_sha256": facts_sha,
                "technical_sheet_url": technical_sheet,
                "technical_sheet_sha256": document_cache.get(technical_sheet, ""),
                "safety_sheet_urls": safety_sheets,
                "safety_sheet_sha256": [document_cache[url] for url in safety_sheets],
                "catalog_url": CATALOG_URL,
                "catalog_sha256": catalog_sha,
                "source_quality_flags": [
                    "official_product_identity_and_specifications",
                    "catalog_presence_not_independent_performance_approval",
                    "multi_grade_tables_expanded_to_one_row_per_published_grade",
                    "marketing_prose_excluded",
                ],
            }
            rows.append(row)

    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    report = {
        "source_id": "BOLIVIA_YPFB_CURRENT_LUBRICANT_CATALOG",
        "snapshot_date": SNAPSHOT_DATE,
        "wp_total_pages": len(pages),
        "selected_product_pages": len(selected),
        "normalized_product_variants": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "automotive_variants": sum(row["product_line"] == "automotive" for row in rows),
        "industrial_variants": sum(row["product_line"] == "industrial" for row in rows),
        "unique_source_documents": len(document_cache),
        "wp_api_response_sha256": sha256(api_bytes),
        "selected_page_facts_sha256": sha256(
            json.dumps(page_facts, ensure_ascii=False, sort_keys=True).encode()
        ),
        "catalog_sha256": catalog_sha,
        "normalized_output_sha256": sha256(OUT.read_bytes()),
        "source_access_boundary": (
            "The ANH public operator list exposes companies and licences, not product-level records; "
            "the authenticated SIREHIDRO/HYDRO product layer was not represented as public data."
        ),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
