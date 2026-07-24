#!/usr/bin/env python3
"""Expand Chevron US' complete current catalog into product-grade identities.

Only factual identifiers and evidence hashes are published.  Expressive page
copy and PDS text remain in the ignored local cache.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "data" / "chevron-us-complete-product-discovery.jsonl"
PDS_INVENTORY = ROOT / "data" / "chevron-us-pds-inventory.jsonl"
PAGE_CACHE = ROOT / ".cache" / "chevron-us-pages"
OUT = ROOT / "data" / "chevron-us-current-products.jsonl"
REPORT = ROOT / "data" / "chevron-us-current-products-report.json"
SOURCE_ID = "CHEVRON_US_COMPLETE_CURRENT_PRODUCT_GRADE_CATALOG"
SNAPSHOT_DATE = "2026-07-24"


def grades(kind: str, values: str) -> tuple[str, list[str]]:
    return kind, values.split() if values else [""]


# Explicit PDS-heading/table or current-page denominators.  A missing entry is
# deliberately one ungraded identity: prose/application numbers are never
# silently reinterpreted as viscosity grades.
VARIANTS: dict[str, tuple[str, list[str]]] = {
    "aries": grades("iso_vg", "32 46 100 150 220 320"),
    "black-pearl-grease-ep-1-2": grades("nlgi", "1 2"),
    "black-pearl-grease-hm-1": grades("nlgi", "1"),
    "black-pearl-grease-sri-2": grades("nlgi", "2"),
    "bright-cut-metalworking-fluid": grades("source_variant", "NHG NM AM AH"),
    "capella-p": grades("iso_vg", "68"),
    "capella-wf": grades("iso_vg", "32 68"),
    "cetus-advantage": grades("iso_vg", "32 46 68 100 150 220 320 460"),
    "cetus-de": grades("iso_vg", "32 68 100 150"),
    "cetus-elitesyn-mgx": grades("iso_vg", "32 46 68 100 150"),
    "cetus-elitesyn-ng": grades("iso_vg", "68 100 150"),
    "cetus-pao-hc": grades("iso_vg", "220"),
    "chevron-compressor-oil": grades("source_variant", "260"),
    "chevron-cylinder-oil-w": grades("iso_vg", "220 460 680"),
    "chevron-form-oil-22": grades("iso_vg", "22"),
    "chevron-gear-oil-gl-1": grades("sae_gear", "90 140"),
    "chevron-htf-e-100": grades("source_variant", "E-100"),
    "chevron-htf-p-150": grades("source_variant", "P-150"),
    "chevron-htf-p-200": grades("source_variant", "P-200"),
    "chevron-hydraulic-oil-5606a": grades("source_variant", "5606A"),
    "chevron-hydraulic-oil-aw": grades("iso_vg", "32 46 68"),
    "chevron-open-gear-lubricant": grades("source_variant", "250-NC"),
    "chevron-paper-machine-oil-premium": grades("iso_vg", "150 220 320"),
    "chevron-red-chain-bar-oils": grades("iso_vg", "68 100 150 220"),
    "chevron-way-lubricant": grades("iso_vg", "32 68 220"),
    "clarity-aw": grades("iso_vg", "32 46 68"),
    "clarity-bio-elitesyn-aw": grades("iso_vg", "32 46 68"),
    "clarity-elitesyn-aw-sae-32-46-68": grades("iso_vg", "32 46 68"),
    "clarity-machine-oils": grades("iso_vg", "150 220 320 460"),
    "clarity-saw-guide-oils": grades("iso_vg", "46 100 150"),
    "clarity-synthetic-hydraulic-oil-aw": grades("iso_vg", "32 46 68"),
    "clarity-synthetic-machine-oil": grades("iso_vg", "150 220 320 460"),
    "delo-100-motor-oils": grades("sae_engine", "40"),
    "delo-1000-marine": grades("sae_engine", "30 40"),
    "delo-400-sng": grades("sae_engine", "15W-40"),
    "delo-400-sp-0w-30": grades("sae_engine", "0W-30"),
    "delo-400-xle-sae-10w-30": grades("sae_engine", "10W-30"),
    "delo-400-xle-sb-15w-40": grades("sae_engine", "15W-40"),
    "delo-400-xsp-15w-40": grades("sae_engine", "15W-40"),
    "delo-400-xsp-fa-5w-30": grades("sae_engine", "5W-30"),
    "delo-400-xsp-sae-5w-30": grades("sae_engine", "5W-30"),
    "delo-400-xsp-sae-5w-40": grades("sae_engine", "5W-40"),
    "delo-400-zfa-sae-10w-30": grades("sae_engine", "10W-30"),
    "delo-400": grades("sae_engine", "10W 20 30 40 50"),
    "delo-600-adf-10w-30": grades("sae_engine", "10W-30"),
    "delo-600-adf-15w-40": grades("sae_engine", "15W-40"),
    "delo-710-hb-rt-sae-20w-40": grades("sae_engine", "20W-40"),
    "delo-710-ls": grades("sae_engine", "20W-40 40"),
    "delo-elc-advanced-antifreezecoolant-5050": grades(
        "concentration", "Concentrate 50/50 60/40 40/60"
    ),
    "delo-elc-antifreeze-coolant": grades(
        "concentration", "Concentrate 50/50"
    ),
    "delo-elc-pg-antifreezecoolant": grades(
        "concentration", "Concentrate 50/50"
    ),
    "delo-eli-corrosion-inhibitor": grades(
        "concentration", "Super-concentrate"
    ),
    "delo-extreme-ep-5": grades("sae_gear", "80W-90 85W-140"),
    "delo-gear-esi-sae-80w-90": grades("sae_gear", "80W-90"),
    "delo-gear-esi-sae-85w-140": grades("sae_gear", "85W-140"),
    "delo-gear-ls": grades("sae_gear", "80W-90"),
    "delo-syn-amt-xdt-sae-75w-90": grades("sae_gear", "75W-90"),
    "delo-syn-gear-hd-sae-75w-90": grades("sae_gear", "75W-90"),
    "delo-syn-gear-xda": grades("sae_gear", "75W-85"),
    "delo-syn-gear-xdm-sae-75w-90-80w-140": grades("sae_gear", "75W-90 80W-140"),
    "delo-syn-grease-sfe-ep-0": grades("nlgi", "0"),
    "delo-syn-tdl-75w-90": grades("sae_gear", "75W-90"),
    "delo-syn-trans-hd-sae-50": grades("sae_gear", "50"),
    "delo-syn-trans-xe": grades("sae_gear", "75W-90"),
    "delo-syn-trans-xv-sae-75w-80": grades("sae_gear", "75W-80"),
    "delo-torqforce-fd": grades("sae_gear", "60"),
    "delo-torqforce-syn": grades("sae_gear", "5W-30"),
    "delo-torqforce": grades("sae_gear", "10W 30 50 60"),
    "delo-xlc-antifreeze-coolant": grades(
        "concentration", "Concentrate 50/50"
    ),
    "delo-xli-corrosion-inhibitor-concentrate": grades(
        "concentration", "Concentrate"
    ),
    "gst-advantage-ep": grades("iso_vg", "32 46"),
    "gst-advantage-ro": grades("iso_vg", "32 46"),
    "gst-oil": grades("iso_vg", "32 46 68 100"),
    "havoline-2-cycle-engine-oil": grades("source_variant", "TC-W3"),
    "havoline-conventional-antifreezecoolant": grades(
        "concentration", "Concentrate 50/50"
    ),
    "havoline-full-synthetic-ls-limited-slip-gear-lubricant": grades("sae_gear", "75W-90 75W-140"),
    "havoline-high-mileage-synblend-motor-oil": grades("sae_engine", "0W-20 5W-20 5W-30 10W-30"),
    "havoline-lifelong-full-synthetic-motor-oil": grades("sae_engine", "0W-20 5W-20 5W-30 10W-30"),
    "havoline-motor-oil": grades("sae_engine", "10W-30 10W-40 20W-50"),
    "havoline-pro-ds-full-synthetic-euro-motor-oil": grades("sae_engine", "0W-30 5W-40"),
    "havoline-pro-ds-full-synthetic-motor-oil": grades("sae_engine", "0W-16 0W-20 0W-40 5W-20 5W-30 5W-40 10W-30"),
    # The current page body/SKU list governs while the linked PDS endpoint
    # serves Chevron's explicit temporary-difficulty response.
    "havoline-synblend-dx-motor-oil": grades("sae_engine", "0W-20 5W-30"),
    "havoline-synblend-motor-oil": grades("sae_engine", "5W-20 5W-30"),
    "havoline-universal-antifreezecoolant": grades(
        "concentration", "Concentrate"
    ),
    "havoline-xtended-life-antifreezecoolant": grades(
        "concentration", "Concentrate 50/50"
    ),
    "hdax-3100-ashless-gas-engine-oils": grades("sae_engine", "15W-40 40"),
    "hdax-3200-low-ash-gas-engine-oils": grades("sae_engine", "30 40"),
    "hdax-5100-ashless-gas-engine-oil": grades("sae_engine", "15W-40 30 40"),
    "hdax-5200-low-ash-gas-engine-oils": grades("sae_engine", "15W-40 30 40"),
    "hdax-5300-medium-ash-gas-engine-oil": grades("sae_engine", "40"),
    "hdax-6500-lfg": grades("sae_engine", "40"),
    "hdax-9200-low-ash-gas-engine-oil": grades("sae_engine", "40"),
    "hdax-9500-gas-engine-oil": grades("sae_engine", "40"),
    "hdax-9700": grades("sae_engine", "40"),
    "hdax-pf-antifreezecoolant--premixed-5050": grades("concentration", "50/50"),
    "meropa-elitesyn-wl": grades("iso_vg", "320 680"),
    "meropa-elitesyn-xm": grades("iso_vg", "150 220 320 460 680"),
    "meropa-xl": grades("iso_vg", "68 150 220 320 460 680"),
    "meropa": grades("iso_vg", "68 100 150 220 320 460 680 1000 1500"),
    "multifak-ep-00-0-1-2-greases": grades("nlgi", "000 00 0 1 2"),
    # Current page heading is the only live grade denominator; its PDS
    # endpoint currently returns the same temporary-difficulty response.
    "paralux-process-oils": grades("source_variant", "701 1001 2401 6001"),
    "rando-hd-premium-oil-mv": grades("iso_vg", "32"),
    "rando-hd": grades("iso_vg", "10 22 32 46 68 100 150 220 320"),
    "rando-hdz": grades("iso_vg", "15 22 32 46 68 100"),
    "rando-wm-32": grades("iso_vg", "32"),
    "regal-hd-57": grades("source_variant", "HD-57"),
    "regal-hh": grades("source_variant", "13 68"),
    "regal-ro": grades("iso_vg", "32 46 68 100 150 220 320 460"),
    "regal-sgt": grades("iso_vg", "22"),
    "rykon-ep-2-grease": grades("nlgi", "2"),
    "rykon-hd-2-grease": grades("nlgi", "2"),
    "rykon-hd-2-m5-grease": grades("nlgi", "2"),
    "sil-x-1-grease": grades("nlgi", "1"),
    "starplex-ep-0-00-1-2-greases": grades("nlgi", "00 0 1 2"),
    "starplex-ep-1-2-m3-grease": grades("nlgi", "1 2"),
    "starplex-hd-1-2-greases": grades("nlgi", "1 2"),
    "starplex-hd-1-2-m5-greases": grades("nlgi", "1 2"),
    "starplex-hd-m3": grades("nlgi", "1 2"),
    "starplex-syn-grease-ep-1-m5": grades("nlgi", "1"),
    "starplex-syn-grease-hd-15": grades("nlgi", "1.5"),
    "starplex-syn-grease-xd-15": grades("nlgi", "1.5"),
    "talcor-ogp-4-gear-oil": grades("source_variant", "#000"),
    "talcor-ogp-6-gear-oil": grades("source_variant", "#000"),
    "taro-20-dp": grades("sae_engine", "30 40"),
    "taro-30-dp": grades("sae_engine", "30 40"),
    "taro-40-xl": grades("sae_engine", "40"),
    "taro-50-xl": grades("sae_engine", "40"),
    "taro-ultra-20-40-70-100-140": grades("source_variant", "20 40 70 100 140"),
    "tegra-synthetic-barrier-fluid": grades("source_variant", "5-cSt 17-cSt"),
    "texclad-2": grades("nlgi", "2"),
    "ultra-duty-hd-0-1-2-greases": grades("nlgi", "0 1 2"),
    "ultra-duty-xd-00": grades("nlgi", "00"),
    "ursa-hydraulic-oil-10w": grades("sae_engine", "10W"),
    "ursa-super-plus-ec-10W-30": grades("sae_engine", "10W-30"),
    "ursa-super-plus-ec-sae-15w-40": grades("sae_engine", "15W-40"),
    "veritas-800-marine-oil": grades("sae_engine", "30"),
    "way-oils-vistac": grades("iso_vg", "68 220"),
}


FAMILY_OVERRIDES = {
    "capella-p": "C", "capella-wf": "C", "cetus-advantage": "C",
    "cetus-de": "C", "cetus-elitesyn-mgx": "C",
    "cetus-elitesyn-ng": "C", "cetus-pao-hc": "C",
    "chevron-1000-thf": "T", "chevron-compressor-oil": "C",
    "chevron-hydraulic-oil-5606a": "H", "chevron-tmgl-premium": "M",
    "delo-710-hb-rt-sae-20w-40": "M", "delo-syn-tdl-75w-90": "T",
    "delo-torqforce-mp": "T", "delo-torqforce-syn-fd-1": "T",
    "gst-2190-ep": "U", "gst-advantage-ep": "U",
    "gst-advantage-ro": "U", "gst-oil": "U",
    "havoline-full-synthetic-ls-limited-slip-gear-lubricant": "T",
    "hdax-9500-gas-engine-oil": "M", "regal-hd-57": "U",
    "regal-hh": "U", "regal-ro": "U", "regal-sgt": "U",
    "ursa-hydraulic-oil-10w": "H",
}


def family(row: dict, slug: str) -> str:
    if slug in FAMILY_OVERRIDES:
        return FAMILY_OVERRIDES[slug]
    category = row["source_category"]
    if category == "Greases":
        return "G"
    if "Coolants & antifreezes" in category:
        return "TF"
    if "Transmission/Gear oils" in category:
        return "T"
    if "Hydraulic oils" in category:
        return "H"
    if category == "Engine oils" or "Engine oils," in category:
        return "M"
    if category == "System Cleaner":
        return "S"
    return "I"


def brand(name: str) -> str:
    plain = name.replace("®", "").replace("™", "").strip()
    if plain.casefold().startswith("delo "):
        return "Delo"
    if plain.casefold().startswith("havoline"):
        return "Havoline"
    if plain.casefold().startswith("ursa "):
        return "Ursa"
    return "Chevron"


def product_name(series: str, grade: str) -> str:
    plain = re.sub(r"\s+", " ", series).strip()
    if not grade:
        return plain
    # Do not append a value already present verbatim at the series tail.
    normalized = grade.lstrip("#")
    if re.search(
        rf"(?<![A-Za-z0-9.-])#?{re.escape(normalized)}$", plain, re.I
    ):
        return plain
    return f"{plain} {grade}"


def main() -> None:
    discovery = [
        json.loads(line) for line in DISCOVERY.read_text().splitlines() if line
    ]
    inventory = [
        json.loads(line) for line in PDS_INVENTORY.read_text().splitlines()
        if line
    ]
    assert len(discovery) == 166
    assert sum(not row["excluded_from_lubricant_scope"] for row in discovery) == 162
    assert len(inventory) == 204

    pds_by_url = {row["document_url"]: row for row in inventory}
    rows = []
    page_grade_counts: dict[str, int] = {}
    ungraded_pages = []
    for source in discovery:
        if source["excluded_from_lubricant_scope"]:
            continue
        slug = source["source_path"].rsplit("/", 1)[-1][:-5]
        if slug == "test":
            # Live orphan/test page duplicates the canonical Delo XLI page,
            # has pageTitle "test", and publishes no PDS/SDS link.
            continue
        cache_id = hashlib.sha256(source["source_path"].encode()).hexdigest()[:20]
        cached_page = PAGE_CACHE / f"{cache_id}.html"
        payload = cached_page.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == source["source_page_sha256"]
        grade_kind, grade_values = VARIANTS.get(slug, ("", [""]))
        if not grade_kind:
            ungraded_pages.append(slug)
        page_grade_counts[slug] = len(grade_values)
        linked_documents = [pds_by_url[url] for url in source["pds_urls"]]
        evidence = (
            "current_product_page_heading_and_sku_list"
            if slug in {"havoline-synblend-dx-motor-oil", "paralux-process-oils"}
            else "linked_current_product_data_sheet"
            if grade_kind
            else "current_product_page_identity_no_explicit_grade_split"
        )
        for grade in grade_values:
            specs: dict[str, object] = {
                "sae_engine": grade if grade_kind == "sae_engine" else "",
                "sae_gear": grade if grade_kind == "sae_gear" else "",
                "iso_vg": grade if grade_kind == "iso_vg" else "",
                "nlgi": grade if grade_kind == "nlgi" else "",
                "source_variant": grade if grade_kind not in {
                    "", "sae_engine", "sae_gear", "iso_vg", "nlgi"
                } else "",
            }
            if slug == "taro-ultra-20-40-70-100-140":
                specs["sae_engine"] = "50"
            record_key = f"{source['source_record_id']}|{grade_kind}|{grade}"
            rows.append({
                "source_id": SOURCE_ID,
                "source_record_id": (
                    "CHEVRON-US-"
                    + hashlib.sha256(record_key.encode()).hexdigest()[:20].upper()
                ),
                "brand": brand(source["product_name"]),
                "manufacturer": "Chevron U.S.A. Inc.",
                "market": "US",
                "family_code": family(source, slug),
                "product_name": product_name(source["product_name"], grade),
                "source_series": source["product_name"],
                "source_grade": grade,
                "source_grade_kind": grade_kind,
                "source_grade_evidence": evidence,
                "source_category": source["source_category"],
                "source_url": source["source_url"],
                "source_page_sha256": source["source_page_sha256"],
                "technical_documents": [{
                    "url": document["document_url"],
                    "sha256": document["document_sha256"],
                    "text_sha256": document["extracted_text_sha256"],
                    "printed_pages": document["printed_pages"],
                    "retrieval_status": document["retrieval_status"],
                } for document in linked_documents],
                "snapshot_date": SNAPSHOT_DATE,
                "lifecycle_status": "listed_on_current_official_catalog_page",
                "publication_scope": "attributed_nonexpressive_factual_fields_only",
                "specifications": specs,
                "source_quality_flags": (
                    ["official_pds_endpoint_temporarily_returned_non_pdf_html"]
                    if any(
                        document["retrieval_status"] != "public_pdf_downloaded"
                        for document in linked_documents
                    )
                    else []
                ),
            })

    assert len(page_grade_counts) == 161
    assert len(rows) == sum(page_grade_counts.values())
    assert len({row["source_record_id"] for row in rows}) == len(rows)
    assert len({
        (row["product_name"].casefold(), row["family_code"])
        for row in rows
    }) == len(rows)
    OUT.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in sorted(rows, key=lambda row: row["source_record_id"])
        ),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "status": "complete_current_product_grade_denominator_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_product_pages": 162,
        "normalized_unique_product_pages": 161,
        "duplicate_orphan_product_page_occurrences_collapsed": 1,
        "collapsed_duplicate_source_path": "/en_us/home/products/test.html",
        "normalized_product_grade_rows": len(rows),
        "pages_expanded_to_multiple_grades": sum(
            value > 1 for value in page_grade_counts.values()
        ),
        "pages_retained_as_ungraded_identity": len(ungraded_pages),
        "ungraded_source_paths": sorted(ungraded_pages),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "brands": dict(sorted(Counter(row["brand"] for row in rows).items())),
        "grade_kinds": dict(sorted(Counter(
            row["source_grade_kind"] or "ungraded" for row in rows
        ).items())),
        "grade_evidence": dict(sorted(Counter(
            row["source_grade_evidence"] for row in rows
        ).items())),
        "rows_with_non_pdf_pds_flag": sum(
            bool(row["source_quality_flags"]) for row in rows
        ),
        "linked_pds_url_occurrences": sum(
            len(row["technical_documents"]) for row in rows
        ),
        "unique_linked_pds_urls": len({
            document["url"]
            for row in rows for document in row["technical_documents"]
        }),
        "source_discovery_sha256": hashlib.sha256(DISCOVERY.read_bytes()).hexdigest(),
        "source_pds_inventory_sha256": hashlib.sha256(
            PDS_INVENTORY.read_bytes()
        ).hexdigest(),
        "output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "remaining_enrichment": (
            "Per-grade API/ACEA/JASO/OEM claims require a separate table-aware "
            "pass; series-level claims are intentionally not copied onto every "
            "grade."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
