#!/usr/bin/env python3
"""Build the current Trinidad & Tobago NP ULTRA lubricant portfolio.

NP's current WordPress archive publishes product *series*, while its linked
PDS/MSDS documents publish the individual viscosity/consistency variants.
This audit expands those variants, collapses three proven duplicate pages,
keeps coolant concentrate and premix separate, and records every current
page/document as evidence without redistributing the PDFs.
"""

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
OUT = ROOT / "data/trinidad-tobago-np-ultra-current-lubricants.jsonl"
REPORT = ROOT / "data/trinidad-tobago-np-ultra-current-lubricants-report.json"
SOURCE_ID = "TRINIDAD_TOBAGO_NP_ULTRA_CURRENT_LUBRICANT_CATALOG"
BASE = "https://www.np.co.tt/ultra_product/"
SNAPSHOT_DATE = "2026-07-23"
UA = "MFClassifier evidence catalog/1.0"


def P(slug, name, family, grades=("",), grade_type="", *,
      api=(), api_gl=(), acea=(), ilsac=(), performance=(), required=(),
      aliases=(), flags=()):
    return {
        "slug": slug, "name": name, "family": family, "grades": grades,
        "grade_type": grade_type, "api": api, "api_gl": api_gl,
        "acea": acea, "ilsac": ilsac, "performance": performance,
        "required": required or (name.split()[0],), "aliases": aliases,
        "flags": flags,
    }


# Audited against all current pages and their 79 linked documents (76 unique
# payloads), plus NP's official 2019 catalogue.  PDS/MSDS values are treated as
# source-reported facts, not independent OEM approvals.
PRODUCTS = [
    P("brake-fluid", "Platinum Brake Fluid", "TF", ("DOT 3", "DOT 4"), "source",
      required=("Brake Fluid", "DOT 3", "DOT 4")),
    P("cp-1009-68-semi-syn-ammonia-refrigeration-compressor-fluid",
      "ULTRA CP-1009 Semi-Syn Ammonia Refrigeration Compressor Fluid", "C", ("68",), "iso"),
    P("cp-1516-68-syn-pag-gas-compressor-oil",
      "ULTRA CP 1516 Syn PAG Gas Compressor Oil", "C", ("68",), "iso"),
    P("cp-1542-46-syn-pag-air-compressor-fluid",
      "ULTRA CP 1542 Syn PAG Air Compressor Fluid", "C", ("46",), "iso"),
    P("cp-4126-100-150-syn-diester-air-compressor-fluid",
      "ULTRA CP 4126 Syn Diester Air Compressor Fluid", "C", ("100", "150"), "iso"),
    P("cp-4601-46-100-syn-pao-gas-compressor-fluid",
      "ULTRA CP 4601 Syn PAO Gas Compressor Fluid", "C", ("46", "100"), "iso",
      performance=("USDA H-2 (source-reported)",)),
    P("cp-4608-100-syn-pao-air-compressor-fluid",
      "ULTRA CP 4608 Syn PAO Air Compressor Fluid", "C", ("100",), "iso",
      performance=("NSF H1 (source-reported)", "32 CFR 178.3570 (as printed by source)"),
      flags=("source_prints_32_cfr_178_3570_not_silently_corrected",)),
    P("cp-9301-46-semi-syn-air-compressor-fluid",
      "ULTRA CP 9301 Semi-Syn Air Compressor Fluid", "C", ("46",), "iso"),
    P("np-soluble-oil-a", "ULTRA Soluble Oil A", "S"),
    P("platinum-2-in-1-fuel-injector-cleaner-cetane-booster",
      "Platinum 2 in 1 Fuel Injector Cleaner + Cetane Booster", "S"),
    P("platinum-2-in-1-fuel-injector-cleaner-octane-booster",
      "Platinum 2 in 1 Fuel Injector Cleaner + Octane Booster", "S"),
    P("super-duty-s3-30-40-50", "ULTRA Super Duty S3", "M",
      ("10W", "30", "40", "50"), "sae_engine", api=("CF",),
      required=("Super Duty S3", "API CF"),
      flags=("sae_10w_published_in_linked_pds_but_omitted_from_page_title",)),
    P("turbine-oil-r-o", "ULTRA Turbine Oil R&O", "U",
      ("32", "46", "68", "100", "150", "220", "320"), "iso"),
    P("turbo-4-32-68-syn-pag-turbine-centrifugal-fluid",
      "ULTRA Turbo 4 Syn PAG Turbine/Centrifugal Fluid", "U", ("32", "68"), "iso"),
    P("ultra-banana-spray-oil", "ULTRA Banana Spray Oil", "S"),
    P("ultra-bar-chain-oil", "ULTRA Bar & Chain Oil", "S"),
    P("ultra-bearing-grease-ht-2", "ULTRA Bearing Grease HT-2", "G", ("2",), "nlgi"),
    P("ultra-bearing-grease-htm", "ULTRA Bearing Grease HTM", "G", ("2",), "nlgi"),
    P("ultra-cng-15w-40", "ULTRA CNG", "M", ("15W-40",), "sae_engine",
      performance=("Cummins CES 20074", "Detroit Diesel DDC 93K216")),
    P("ultra-cvt-fluid", "ULTRA Full Synthetic CVT Fluid", "TF",
      performance=("Multi-vehicle CVT applicability (source-reported)",),
      flags=("oem_applicability_not_independent_approval",)),
    P("ultra-cylinder-oil-j", "ULTRA Cylinder Oil J", "I",
      ("220", "460", "680"), "iso"),
    P("ultra-diesel-plus-sae-30-40-50", "ULTRA Diesel Plus", "M",
      ("30", "40", "50"), "sae_engine", api=("CF", "CF-2")),
    P("ultra-diesel-special-40", "ULTRA Diesel Special", "M", ("40",), "sae_engine",
      performance=("LMOA Generation 5", "General Electric Generation 4")),
    P("ultra-diesel-tec-10w-30-5w-40", "ULTRA Diesel Tec", "M",
      ("10W-30", "5W-40"), "sae_engine",
      api=("CJ-4", "SN", "CI-4", "CH-4", "CG-4", "CF-4", "CF"),
      acea=("E7-04", "A5/B5", "A3/B4", "A3/B3"),
      performance=("CAT ECF-3", "CAT ECF-1", "CAT TO-2", "MB 228.5",
                   "Cummins CES 20081", "Cummins CES 20078", "Volvo VDS-4",
                   "Mack EO-O Premium Plus 2007", "Allison C-4")),
    P("ultra-dtv-20w-50", "ULTRA DTV", "M", ("20W-50",), "sae_engine", api=("CF",)),
    P("ultra-duty-15w-40", "ULTRA Duty", "M", ("15W-40",), "sae_engine",
      api=("CK-4", "SN"), acea=("E7-04", "A5/B5"),
      performance=("Detroit Diesel (source-reported approval)", "Renault (source-reported approval)",
                   "MTU (source-reported approval)", "Cummins (source-reported approval)",
                   "Mack (source-reported approval)", "Volvo (source-reported approval)")),
    P("ultra-form-oil", "ULTRA Form Oil", "S"),
    P("ultra-gear-oils-hd-lsd-80w-90-85w-140", "ULTRA Gear Oil HD & LSD", "T",
      ("80W-90", "85W-140"), "sae_gear", api_gl=("GL-5", "MT-1"),
      performance=("SAE J2360", "Mack GO-J")),
    P("ultra-heat-transfer-oil", "ULTRA Heat Transfer Oil", "I"),
    P("ultra-hydraulic-oil-hv", "ULTRA Hydraulic Oil HV", "H",
      ("32", "37", "46", "68", "100"), "iso"),
    P("ultra-hydraulic-oil", "ULTRA Hydraulic Oil", "H",
      ("32", "37", "46", "68", "100", "150", "220"), "iso",
      flags=("incorrect_turbine_pds_link_excluded_from_hydraulic_evidence",)),
    P("ultra-industrial-gas-engine-oil-2", "ULTRA Industrial Gas Engine Oil", "M",
      ("30", "40"), "sae_engine",
      aliases=("ultra-industrial-gas-engine-oil",),
      flags=("duplicate_page_collapsed", "alias_page_contains_unrelated_hybrid_oil_body")),
    P("ultra-industrial-gear-oil-tk-1000", "ULTRA Industrial Gear Oil TK", "I",
      ("800", "1000", "3200"), "iso", api_gl=("GL-4", "GL-5"),
      performance=("AIST 224", "AGMA 9005-E-02", "DIN 51517 Part 3")),
    P("ultra-industrial-gear-oil", "ULTRA Industrial Gear Oil", "I",
      ("68", "100", "150", "220", "320", "460", "680", "800"), "iso",
      api_gl=("GL-4", "GL-5"),
      performance=("AIST 224", "AGMA 9005-E-02", "DIN 51517 Part 3")),
    P("ultra-industrial-syn-tec-gear-oil", "ULTRA Industrial Syn-Tec Gear Oil", "I",
      ("68", "100", "150", "220", "320", "460", "680", "800", "1000", "1500"), "iso",
      api_gl=("GL-4", "GL-5"),
      performance=("AIST 224", "AGMA 9005-E-02", "DIN 51517 Part 3"),
      flags=("tk_1000_1500_variants_published_in_separate_linked_document",)),
    P("ultra-molylube-2", "ULTRA Molylube", "G", ("2",), "nlgi"),
    P("ultra-motor-oil-sae-30-40-50", "ULTRA Motor Oil", "M",
      ("30", "40", "50"), "sae_engine", api=("SL",)),
    P("ultra-multi-vehicle-atf-fully-synthetic-dexron-vi",
      "ULTRA Multi-Vehicle ATF Fully Synthetic", "TF",
      performance=("GM Dexron VI", "Ford Mercon LV", "SP")),
    P("ultra-multipurpose-ep-grease", "ULTRA Multipurpose EP Grease", "G",
      ("0", "1", "2", "3"), "nlgi", performance=("NLGI GC-LB",)),
    P("ultra-multipurpose-red-complex-ep-grease",
      "ULTRA Multiplex Red Complex EP Grease", "G", ("2",), "nlgi",
      performance=("NLGI GC-LB",)),
    P("ultra-open-gear-compound", "ULTRA Open Gear Compound", "I"),
    P("ultra-powermax-4t-10w-40", "ULTRA Powermax 4T", "M",
      ("10W-40",), "sae_engine", api=("SL",), performance=("JASO MA",)),
    P("ultra-premium-10w-30-10w-40-20w-50", "ULTRA Premium", "M",
      ("10W-30", "10W-40", "20W-50"), "sae_engine", api=("SN",), ilsac=("GF-5",)),
    P("ultra-process-oil", "ULTRA Process Oil", "I",
      ("22", "32", "37", "46", "68", "100", "150", "220", "320", "460", "680", "1000", "1500"), "iso"),
    P("ultra-radol-premium-long-life-coolant-concentrate",
      "ULTRA Radol Premium Long Life Coolant Concentrate", "TF",
      performance=("ASTM D6210", "ASTM D3306", "Caterpillar EC-1",
                   "Cummins 14603", "Cummins 3666286", "Detroit Diesel"),
      aliases=("ultra-radol-premium-long-life-coolant-concentrate-2",
               "ultra-radol-premium-long-life-coolant"),
      flags=("duplicate_concentrate_page_collapsed", "generic_page_used_as_shared_specification_evidence")),
    P("ultra-radol-premium-long-life-coolant-pre-mix",
      "ULTRA Radol Premium Long Life Coolant Premix", "TF",
      performance=("ASTM D6210", "ASTM D3306", "Caterpillar EC-1"),
      flags=("premix_kept_separate_from_concentrate",)),
    P("ultra-refcom", "ULTRA Refcom Oil", "I", ("32", "46", "68", "100"), "iso"),
    P("ultra-rock-drill-oil", "ULTRA Rock Drill Oil", "I",
      ("32", "68", "100", "150", "220", "320", "460"), "iso"),
    P("ultra-sewing-machine-oil", "ULTRA Sewing Machine Oil", "S", ("22",), "iso"),
    P("ultra-shock-absorber-oil", "ULTRA Shock Absorber Oil", "I"),
    P("ultra-spectrum", "ULTRA Spectrum Oil", "M",
      ("30", "40", "50"), "sae_engine",
      flags=("marine_crosshead_engine_oil_without_published_api_category",)),
    P("ultra-super-duty-2t-40", "ULTRA Super Duty 2T", "M",
      ("40",), "sae_engine", api=("CF-2",),
      performance=("Detroit Diesel Type 1", "Detroit Diesel Type 2")),
    P("ultra-super-tractor-universal-c", "ULTRA Super Tractor Oil Universal C", "TF",
      ("30", "50", "60"), "sae_engine", api=("CF", "CF-2"),
      performance=("Caterpillar TO-4", "Caterpillar FD-1", "Allison C-4",
                   "ZF TE-ML 01", "ZF TE-ML 03C", "ZF TE-ML 07F")),
    P("ultra-supermatic-automatic-transmission-and-power-steering-fluid",
      "ULTRA Supermatic ATF and Power Steering Fluid", "TF",
      performance=("GM Dexron III H", "Ford Mercon", "Allison C-4")),
    P("ultra-superstream", "ULTRA Superstream", "M",
      api=("TC",), performance=("NMMA TC-W3", "NMMA TC-WII", "NMMA TC-W")),
    P("ultra-tec-5w-30-5w-40-10w-30", "ULTRA Tec", "M",
      ("5W-30", "5W-40", "10W-30"), "sae_engine",
      api=("SN", "CF"), acea=("A5/B5",), ilsac=("GF-5",)),
    P("ultra-tec-hybrid-0w-20", "ULTRA Tec Hybrid", "M",
      ("0W-20",), "sae_engine", api=("SN-RC",), ilsac=("GF-5",),
      flags=("page_title_typo_ultra_ec_normalized_from_product_body",)),
    P("ultra-two-stroke", "ULTRA Two Stroke Motor Oil", "M",
      api=("TC",), aliases=("ultra-two-stroke-2",),
      flags=("duplicate_page_and_document_payload_collapsed",)),
    P("ultra-universal-tractor-transmission-oil-utto", "ULTRA Universal Tractor Transmission Oil", "TF",
      ("10W-30",), "sae_engine", api_gl=("GL-4",),
      performance=("Ford New Holland ESN-M2C134-D", "Massey-Ferguson M1145",
                   "John Deere J20C", "John Deere J20D", "Allison C-4", "Caterpillar TO-2")),
]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
        self.documents = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
        if tag == "a":
            href = attrs.get("href", "")
            if re.search(r"\.pdf(?:$|\?)", href, re.I):
                self.documents.append(href)

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def parse_page(value):
    parser = PageParser()
    parser.feed(value.decode("utf-8", "replace"))
    text = re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()
    return text, sorted(set(parser.documents))


def main():
    page_slugs = [slug for product in PRODUCTS for slug in (product["slug"], *product["aliases"])]
    if len(page_slugs) != 63 or len(set(page_slugs)) != 63:
        raise RuntimeError(f"NP current page audit must cover 63 unique pages, got {len(set(page_slugs))}")

    def fetch_page(slug):
        url = BASE + slug + "/"
        body = get(url)
        text, documents = parse_page(body)
        if "Most Recent News" not in text:
            raise RuntimeError(f"NP product page layout changed: {url}")
        return slug, {
            "url": url,
            "text": text,
            "normalized_text_sha256": digest(text.encode()),
            "document_urls": documents,
        }

    pages = {}
    document_urls = set()
    with ThreadPoolExecutor(max_workers=8) as pool:
        for slug, page in pool.map(fetch_page, page_slugs):
            pages[slug] = page
            document_urls.update(page["document_urls"])

    def fetch_document(url):
        payload = get(url)
        if not payload.startswith(b"%PDF"):
            raise RuntimeError(f"Linked NP document is no longer a PDF: {url}")
        return url, {"sha256": digest(payload), "bytes": len(payload)}

    document_payloads = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for url, facts in pool.map(fetch_document, sorted(document_urls)):
            document_payloads[url] = facts

    rows = []
    series_facts = []
    for product in PRODUCTS:
        evidence_slugs = (product["slug"], *product["aliases"])
        primary_text = pages[product["slug"]]["text"]
        missing = [token for token in product["required"] if token.casefold() not in primary_text.casefold()]
        if missing:
            raise RuntimeError(f"NP product facts changed for {product['slug']}: {missing}")
        evidence_urls = [BASE + slug + "/" for slug in evidence_slugs]
        linked_docs = sorted({url for slug in evidence_slugs for url in pages[slug]["document_urls"]})
        if product["slug"] == "ultra-hydraulic-oil":
            linked_docs = [url for url in linked_docs if "turbine" not in url.casefold()]
        series_facts.append({
            "slug": product["slug"], "name": product["name"], "grades": product["grades"],
            "evidence_urls": evidence_urls, "linked_documents": linked_docs,
        })
        for grade in product["grades"]:
            technical = {
                "sae_engine": grade if product["grade_type"] == "sae_engine" else "",
                "sae_gear": grade if product["grade_type"] == "sae_gear" else "",
                "api": list(product["api"]), "api_gl": list(product["api_gl"]),
                "acea": list(product["acea"]), "ilsac": list(product["ilsac"]),
                "iso_vg": grade if product["grade_type"] == "iso" else "",
                "nlgi": grade if product["grade_type"] == "nlgi" else "",
                "source_grade": grade if product["grade_type"] == "source" else "",
                "performance": list(product["performance"]),
            }
            suffix = f" {grade}" if grade else ""
            quality_flags = [
                "official_current_np_ultra_product_page",
                "official_linked_pds_msds_audited",
                "source_reported_performance_claims_not_independent_approvals",
                "marketing_prose_excluded",
                *product["flags"],
            ]
            key = f"{product['slug']}|{grade}"
            rows.append({
                "source_id": SOURCE_ID,
                "source_record_id": "NP-ULTRA-" + digest(key.encode())[:12],
                "market": "Trinidad and Tobago",
                "manufacturer": "Trinidad & Tobago National Petroleum Marketing Company Limited",
                "brand": "ULTRA",
                "product_name": product["name"] + suffix,
                "family_code": product["family"],
                "technical": technical,
                "lifecycle_status": "listed_on_current_official_manufacturer_site",
                "evidence_status": "official_current_product_page_and_linked_technical_documents",
                "snapshot_date": SNAPSHOT_DATE,
                "source_url": BASE + product["slug"] + "/",
                "source_urls": evidence_urls,
                "source_page_text_sha256": pages[product["slug"]]["normalized_text_sha256"],
                "source_document_urls": linked_docs,
                "source_document_sha256": {url: document_payloads[url]["sha256"] for url in linked_docs},
                "source_quality_flags": quality_flags,
            })

    facts_sha = digest(json.dumps(series_facts, ensure_ascii=False, sort_keys=True).encode())
    for row in rows:
        row["source_facts_sha256"] = facts_sha
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "current_product_pages_audited": len(pages),
        "normalized_series": len(PRODUCTS),
        "normalized_product_grade_identities": len(rows),
        "linked_document_urls_fetched": len(document_payloads),
        "unique_document_payloads": len({v["sha256"] for v in document_payloads.values()}),
        "linked_document_bytes": sum(v["bytes"] for v in document_payloads.values()),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "rows_with_sae": sum(bool(r["technical"]["sae_engine"] or r["technical"]["sae_gear"]) for r in rows),
        "rows_with_iso_vg": sum(bool(r["technical"]["iso_vg"]) for r in rows),
        "rows_with_nlgi": sum(bool(r["technical"]["nlgi"]) for r in rows),
        "duplicate_pages_collapsed": 3,
        "source_facts_sha256": facts_sha,
        "normalized_output_sha256": digest(OUT.read_bytes()),
        "catalog_2019_crosscheck": {
            "url": "https://np-ultra.com/wp-content/uploads/2020/05/NP-Catalogue-Ultra-Lubricants-HQ-FAW_compressed.pdf",
            "sha256": "201b8498372da788739fa1e1d236646847c9fe8c22268711cf75d9d8bfba1375",
            "role": "historical_secondary_crosscheck_only",
        },
        "document_payloads": document_payloads,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "document_payloads"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
