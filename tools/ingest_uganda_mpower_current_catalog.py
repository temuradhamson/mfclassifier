#!/usr/bin/env python3
"""Normalize the complete current MPower Oil Uganda product-page catalog.

The two official listing pages enumerate all linked Goldstar and Lubex detail
pages.  Only factual product, package and specification fields are retained.
Marketing prose, benefits, contacts and imagery are deliberately excluded.
Source contradictions remain explicit and are not promoted into strict keys.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/uganda-mpower-current-products.jsonl"
REPORT = ROOT / "data/uganda-mpower-current-report.json"
SOURCE_ID = "UGANDA_MPOWER_CURRENT_COMPLETE_PRODUCT_PAGES"
BASE_URL = "https://mpoweroil.com/"
LISTINGS = {
    "GOLDSTAR": "goldstarproducts.html",
    "LUBEX": "lubexproducts.html",
}
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if value:
            self.parts.append(value)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def visible_text(payload: bytes) -> str:
    parser = VisibleText()
    parser.feed(payload.decode(errors="replace"))
    return " | ".join(parser.parts)


def item(filename: str, brand: str, name: str, family: str, packages: list[str], **specifications: object) -> dict:
    return {
        "filename": filename,
        "brand": brand,
        "product_name": name,
        "family_code": family,
        "packages": packages,
        "specifications": specifications,
    }


PRODUCTS = [
    item("goldstargearoil.html", "GOLDSTAR", "Goldstar Multipurpose Gear Oil GL4", "T", ["5 L"], source_reported_sae_values=["SAE 140", "SAE 85W-140"], source_reported_api_gl_values=["GL-4 product title", "GL-5 specification/application"], standards=["MIL-L-2105D"], oem_specifications=["MB 235.0", "MAN 342 Type MT", "Volvo 97310", "ZF TE-ML 17B", "ZF TE-ML 19B"], source_quality_flags=["product_title_gl4_conflicts_with_published_gl5_specification", "source_description_sae140_conflicts_with_application_sae85w140"], source_conflict_note="No SAE or API GL value is promoted into the strict equivalence key."),
    item("goldstardextron2.html", "GOLDSTAR", "Goldstar ATF Dextron II", "T", ["5 L"], atf_specifications=["GM Dexron II"], source_reported_spelling="Dextron II"),
    item("goldstarpetrolengine.html", "GOLDSTAR", "Goldstar Petrol Engine Oil SAE 40", "M", ["1 L", "5 L", "20 L"], sae_engine="40", api=["CD", "SF"], standards=["MIL-L-2104C", "MACK T-7", "PL2-IS13656-1993"]),
    item("goldstardeiselengine.html", "GOLDSTAR", "Goldstar Diesel Engine Oil SAE 50", "M", ["5 L"], sae_engine="50", api=["CD", "SF"], standards=["MIL-L-2104C", "MACK T-7", "PL2-IS13656-1993"]),
    item("goldstar2toil.html", "GOLDSTAR", "Goldstar 2T Oil", "M", ["5 L"], engine_cycle="2T", source_reported_performance=["JASO T203", "API SL/JASO", "MA-2"], source_quality_flags=["two_stroke_product_page_reports_four_stroke_jaso_ma2_style_performance_not_promoted_to_strict_key"]),
    item("gearoilgl4.html", "LUBEX", "Lubex Multipurpose Gear Oil GL4", "T", ["20 L", "200 L"], source_reported_sae_values=["SAE 140", "SAE 85W-140"], source_reported_api_gl_values=["GL-4 product title", "GL-5 specification/application"], standards=["MIL-L-2105D"], oem_specifications=["MB 235.0", "MAN 342 Type MT", "Volvo 97310", "ZF TE-ML 17B", "ZF TE-ML 19B"], source_quality_flags=["product_title_gl4_conflicts_with_published_gl5_specification", "source_description_sae140_conflicts_with_application_sae85w140"], source_conflict_note="No SAE or API GL value is promoted into the strict equivalence key."),
    item("lubexhydraulic.html", "LUBEX", "Lubex Hydraulic Oil", "H", ["20 L"], standards=["DIN 51524-2", "DIN 51524-3"], oem_specifications=["Denison HF-0", "Denison HF-1", "Denison HF-2", "Vickers M-2950-S", "Vickers I-286-S", "Cincinnati Milacron P-68", "Cincinnati Milacron P-69", "Cincinnati Milacron P-70"], source_quality_flags=["product_page_publishes_no_iso_vg_grade"]),
    item("lubexATFdextron.html", "LUBEX", "Lubex ATF Dextron II", "T", ["5 L"], atf_specifications=["GM Dexron II"], source_reported_spelling="Dextron II"),
    item("lubexDieselEngine.html", "LUBEX", "Lubex Diesel Engine Oil SAE 50", "M", ["5 L"], sae_engine="50", api=["CD", "SF"], standards=["MIL-L-2104C", "MACK T-7", "PL2-IS13656-1993"]),
    item("lubex2toil.html", "LUBEX", "Lubex 2T Oil", "M", ["250 mL", "900 mL"], engine_cycle="2T", source_reported_performance=["JASO T203", "API SL/JASO", "MA-2"], source_quality_flags=["two_stroke_product_page_reports_four_stroke_jaso_ma2_style_performance_not_promoted_to_strict_key"]),
    item("lubexpetrolengine.html", "LUBEX", "Lubex Petrol Engine Oil SAE 40", "M", ["1 L", "5 L", "20 L"], sae_engine="40", api=["CD", "SF"], standards=["MIL-L-2104C", "MACK T-7", "PL2-IS13656-1993"]),
    item("lubexturbomax.html", "LUBEX", "Lubex Turbo Max SAE 15W-40", "M", ["1 L", "5 L", "20 L", "200 L"], sae_engine="15W-40", api=["CI-4", "SL"], acea=["E7"], oem_specifications=["Mack EO-O Premium Plus", "Caterpillar ECF-1A", "Caterpillar ECF-2", "Caterpillar ECF-3", "Volvo VDS-4", "Cummins CES 20081", "MB 228.3", "MTU Type II"], standards=["MIL-L-2104E"], source_quality_flags=["description_c14_typo_resolved_by_explicit_meets_specifications_ci4"]),
    item("lubexgearoilgl5.html", "LUBEX", "Lubex Multipurpose Gear Oil GL5", "T", ["20 L", "200 L"], api_gl=["GL-5"], source_reported_sae_values=["SAE 140", "SAE 85W-140"], standards=["MIL-L-2105D"], oem_specifications=["MB 235.0", "MAN 342 Type MT", "Volvo 97310", "ZF TE-ML 17B", "ZF TE-ML 19B"], source_quality_flags=["source_description_sae140_conflicts_with_application_sae85w140"], source_conflict_note="API GL-5 is explicit and retained; no SAE is promoted into the strict key."),
    item("lubexmagum40.html", "LUBEX", "Lubex Magumn SAE 40", "M", ["20 L", "200 L"], sae_engine="40", api=["CF", "SJ"], standards=["MIL-L-2104C", "MACK T-7"], source_reported_spelling="Magumn 40"),
    item("lubexgrease.html", "LUBEX", "Lubex Grease MP2/MP3", "G", ["1 kg", "1.5 kg", "15 kg", "150 kg"], nlgi="3", thickener="lithium", grease_type="EP multipurpose", source_reported_consistency=["MP2/MP3 product title", "MP3, NLGI 3 specification"], source_quality_flags=["combined_mp2_mp3_title_but_only_nlgi3_is_explicitly_specified"]),
    item("lubextruckmax.html", "LUBEX", "Lubex Truck Max SAE 15W-40", "M", ["1 L", "2 L", "5 L", "200 L"], sae_engine="15W-40", api=["CF-4"], acea=["E3"], source_reported_api_values=["CF-4/SL in description", "CF-4/SG in Meets Specifications"], oem_specifications=["Mack EO-O Premium Plus", "Caterpillar ECF-1A", "Caterpillar ECF-2", "Caterpillar ECF-3", "Volvo VDS-4"], standards=["MIL-L-2104E"], source_quality_flags=["published_secondary_api_class_conflict_sl_vs_sg_not_promoted_to_strict_key"]),
]


def main() -> None:
    listing_payloads = {
        brand: fetch(urljoin(BASE_URL, filename))
        for brand, filename in LISTINGS.items()
    }
    discovered: dict[str, str] = {}
    for brand, payload in listing_payloads.items():
        for filename in re.findall(
            r'href=["\']([^"\']+\.html)["\']',
            payload.decode(errors="replace"),
            re.I,
        ):
            if filename in {row["filename"] for row in PRODUCTS}:
                discovered[filename] = brand
    expected = {row["filename"]: row["brand"] for row in PRODUCTS}
    if discovered != expected:
        raise RuntimeError(f"Product-page denominator changed: {discovered!r}")

    records = []
    page_hashes = {}
    for index, source in enumerate(PRODUCTS, 1):
        url = urljoin(BASE_URL, source["filename"])
        payload = fetch(url)
        text = visible_text(payload)
        for token in ["Product Detail", "Available in"]:
            if token.casefold() not in text.casefold():
                raise RuntimeError(f"{source['filename']} missing token {token}")
        page_sha = hashlib.sha256(payload).hexdigest()
        page_hashes[source["filename"]] = page_sha
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"MPOWER-UG-{index:03d}",
            "source_url": url,
            "listing_url": urljoin(BASE_URL, LISTINGS[source["brand"]]),
            "source_page_sha256": page_sha,
            "source_facts_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Uganda",
            "manufacturer": "MPower Oil Company Ltd.",
            "brand": source["brand"],
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "packages": source["packages"],
            "lifecycle_status": "current_official_catalog",
            "evidence_status": "current_local_manufacturer_complete_product_page_catalog",
            "specifications": source["specifications"],
        })

    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "current_local_manufacturer_complete_product_pages_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "listing_pages": len(LISTINGS),
        "detail_pages": len(records),
        "brands": dict(sorted(Counter(row["brand"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "package_occurrences": sum(len(row["packages"]) for row in records),
        "quality_flags": dict(sorted(Counter(
            flag for row in records
            for flag in row["specifications"].get("source_quality_flags", [])
        ).items())),
        "listing_page_sha256": {
            brand: hashlib.sha256(payload).hexdigest()
            for brand, payload in sorted(listing_payloads.items())
        },
        "detail_page_sha256": dict(sorted(page_hashes.items())),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "denominator_note": "All 5 Goldstar and 11 Lubex detail pages linked from the two official product listings are included.",
        "availability_note": "Pages identify packages but publish no price, stock quantity or order action; no offers are created.",
        "publication_scope": "Factual product names, packages, specifications, evidence URLs and hashes only; descriptions, benefits, contacts and images are excluded.",
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
