#!/usr/bin/env python3
"""Build current Jamaican FUTROIL and TEK/TEKSTAR lubricant portfolios.

FESCO publishes six current product cards.  Two cards explicitly contain
multiple product grades, so they expand to eight product-grade identities.
Lubit Limited publishes fifteen relevant TEK/TEKSTAR cards; multi-grade cards
expand to twenty-one identities.  Several exact grades are printed in the
official card artwork rather than repeated in surrounding prose, therefore
the extractor pins every relevant image payload by SHA-256.
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


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/jamaica-futroil-tek-current-lubricants.jsonl"
REPORT = ROOT / "data/jamaica-futroil-tek-current-lubricants-report.json"
SNAPSHOT_DATE = "2026-07-23"
UA = "MFClassifier evidence catalog/1.0"

FUTROIL_SOURCE_ID = "JAMAICA_FESCO_FUTROIL_CURRENT_LUBRICANT_CATALOG"
FUTROIL_PAGE = "https://www.fescoja.com/lubricants"
FUTROIL_IMAGE_BASE = "https://www.fescoja.com/images/lubricants/"

TEK_SOURCE_ID = "JAMAICA_LUBIT_TEK_CURRENT_LUBRICANT_CATALOG"
TEK_PAGE = "https://www.lubitltd.com/"
TEK_IMAGE_BASE = "https://static.wixstatic.com/media/"


def product(name, family, image, *, sae_engine="", sae_gear="", iso_vg="",
            source_grade="", api=(), api_gl=(), ilsac=(), performance=(),
            flags=()):
    return {
        "name": name,
        "family_code": family,
        "image": image,
        "technical": {
            "sae_engine": sae_engine,
            "sae_gear": sae_gear,
            "api": list(api),
            "api_gl": list(api_gl),
            "acea": [],
            "ilsac": list(ilsac),
            "iso_vg": iso_vg,
            "nlgi": "",
            "source_grade": source_grade,
            "performance": list(performance),
        },
        "flags": list(flags),
    }


FUTROIL_IMAGES = {
    "SAE_140_GEAR.jpg": "7e36c5594f881d8bcaf78c6b6a80ce6f2074157b2f39f784ec09bc5b63b8e025",
    "DEX3.jpg": "8ea2ee8a2539d09b3a5eece0426bd176a992667da8336c9ac18bd8ca55410711",
    "TC3-RED.jpg": "79d8e8122c549005f51d4d7d0870fdc55a07e22b5514f218ea448455a60ebcf0",
    "2_stroke_marine.jpg": "da89545e3e16d26aa2c8a943a7b96c9355722c4034621d29d1f3d44b1be8214f",
    "SAE_20W-50_SN_GF-5_GE.jpg": "42cbc44ebb18b83561e247f37957c8f40ec55c902d17fde24517c3be6bc338f8",
    "5W30_Fully_Synthetic.jpg": "d53d5c0baca5360150f83989314b55dfa612423bdc982689f1b99646a1bec245",
}

FUTROIL_PRODUCTS = [
    product("FUTROIL Gear Oil SAE 90", "T", "SAE_140_GEAR.jpg", sae_gear="90"),
    product("FUTROIL Gear Oil SAE 140", "T", "SAE_140_GEAR.jpg", sae_gear="140"),
    product("FUTROIL Automatic Transmission Fluid DEX 3", "TF", "DEX3.jpg",
            source_grade="DEX 3", performance=("DEX 3 (source label; not represented as an independent OEM approval)",)),
    product('FUTROIL Two Cycle Land Oil TC3 "RED"', "M", "TC3-RED.jpg",
            source_grade='TC3 "RED"'),
    product("FUTROIL Two Cycle Marine Oil", "M", "2_stroke_marine.jpg"),
    product("FUTROIL Mineral Motor Oil 20W-50 SN/GF-5", "M",
            "SAE_20W-50_SN_GF-5_GE.jpg", sae_engine="20W-50",
            api=("SN",), ilsac=("GF-5",)),
    product("FUTROIL Full Synthetic Motor Oil 5W-30 SN Plus/GF-5", "M",
            "5W30_Fully_Synthetic.jpg", sae_engine="5W-30",
            api=("SN Plus",), ilsac=("GF-5",)),
    product("FUTROIL Full Synthetic Motor Oil 5W-40 CK-4", "M",
            "5W30_Fully_Synthetic.jpg", sae_engine="5W-40", api=("CK-4",)),
]


TEK_IMAGES = {
    "5ac22f_9abc2ffc846c49dd9d76685202ea2e89~mv2.jpg": "23f0a97d09fe842389e513f70746dde011ba156a1e7d33eec4db0b8c55bd533f",
    "5ac22f_43949aa52c8b465783ba8d3b54cbde87~mv2.jpg": "6614286cf54d4b2c2ff0d6f31dc9c714cbb17bcd327b65f54c3cee7494ae54f4",
    "5ac22f_abbcf51aff6244a2b3d639ad235712f2~mv2.jpg": "35e891ebe8f9464b57871dd228fe2c4262e7bf3867611ca4177217b21ccdc8e6",
    "5ac22f_c49b81775755420aa14f2b2225d3a44c~mv2.jpg": "02aef1c2d9d1b0756768d18f74bfd47fd5a6f8abd05db39c99742e0bcb4fa2fc",
    "5ac22f_54c8f3ec490e46188685154b7fc14fe1~mv2.jpg": "0a74e7ef838127cffbf5871b1c307275951b869489f19d627c710b639de8d643",
    "5ac22f_8e44988c150f41ba8d0fd1be63be5245~mv2.jpg": "dff1157dc06f62e7bcc643d6928044b381b2ceddc82d1703737bd8a6ecdad632",
    "5ac22f_525839f68d6d4b9bb912aa9e42223d6d~mv2.jpg": "7f5bf33241322e4d788bdaa3c2895be7679b5157ccd4ceac8d9058f11f6fd98a",
    "5ac22f_b4b6682018f144a4a020bb7cd5361e79~mv2.jpg": "1913e8f56471c4e8c67057397c6573ebb1f863323bc9fa8ac20a411c438308f7",
    "5ac22f_6a2d9a458c664066a916f2724d567653~mv2.jpg": "02514f3a86c39031a9f3a44a5d098010a8aeac80309da84a92fb201fc455e470",
    "5ac22f_8da100c6707d457781e871a2cffcb0cc~mv2.jpg": "fb402f29854c9399136f622fcbdb2cda802377d78be163eb3c1cbb19dc9fc6c8",
    "5ac22f_aae15b506f224405a519a50f9b8ac589~mv2.jpg": "68bc9f45684a9c9e180e2a6eec8e055efdff9e47fe09e2cff8383307a1a97797",
    "5ac22f_0343374184164682b838619a9b53b20d~mv2.jpg": "e4da073c5becc40909a7ca4235de3ccf7e25b3e2357508c6537872bf2285553c",
    "5ac22f_5a20518e0040462db04e8a3063a60bd5~mv2.jpg": "b26e6f8b8e02345c36d0647d206e2a2451cc5a96f566bafceb1fb0014d1e35db",
    "5ac22f_0a4937028d814507847d7e9353bae720~mv2.jpg": "e313c464dbe8793587311819cea9904a7e7ecd1a315220ec7ce9c7f43f844f4e",
}

TEK_PRODUCTS = [
    product("TEK ELC Coolant 50/50", "TF",
            "5ac22f_9abc2ffc846c49dd9d76685202ea2e89~mv2.jpg",
            source_grade="50/50"),
    *[
        product(f"TEK Premium AW Hydraulic Oil ISO VG {grade}", "H",
                "5ac22f_43949aa52c8b465783ba8d3b54cbde87~mv2.jpg",
                iso_vg=grade, source_grade=f"AW {grade}")
        for grade in ("32", "46", "68", "100")
    ],
    *[
        product(f"TEK Lube SAE {grade}", "M",
                "5ac22f_abbcf51aff6244a2b3d639ad235712f2~mv2.jpg",
                sae_engine=grade)
        for grade in ("40", "50")
    ],
    product("TEK SAE 40 ND", "M",
            "5ac22f_c49b81775755420aa14f2b2225d3a44c~mv2.jpg",
            sae_engine="40", source_grade="ND"),
    product("TEK Red Ultra HD EP2 Grease", "G",
            "5ac22f_54c8f3ec490e46188685154b7fc14fe1~mv2.jpg",
            source_grade="EP2",
            flags=("ep2_product_label_not_silently_interpreted_as_nlgi_2",)),
    product("TEK MP Automatic Transmission Fluid MD-3", "TF",
            "5ac22f_8e44988c150f41ba8d0fd1be63be5245~mv2.jpg",
            source_grade="MD-3"),
    *[
        product(f"TEK Refrigeration WF Oil ISO VG {grade}", "C",
                "5ac22f_525839f68d6d4b9bb912aa9e42223d6d~mv2.jpg",
                iso_vg=grade, source_grade=f"WF {grade}")
        for grade in ("32", "68")
    ],
    product("TEK Soluble Cutting Oil BT", "S",
            "5ac22f_b4b6682018f144a4a020bb7cd5361e79~mv2.jpg",
            source_grade="BT"),
    product("TEK SYN-BLEND 15W-40 LE CK-4/SN", "M",
            "5ac22f_6a2d9a458c664066a916f2724d567653~mv2.jpg",
            sae_engine="15W-40", api=("CK-4", "SN", "CJ-4"),
            performance=("LE (source label)",),
            flags=("cj_4_is_source_reported_meets_claim_in_page_text",)),
    *[
        product(f"TEK SYN-BLEND Motor Oil {grade}", "M",
                "5ac22f_8da100c6707d457781e871a2cffcb0cc~mv2.jpg",
                sae_engine=grade)
        for grade in ("10W-30", "20W-50")
    ],
    *[
        product(f"TEK Universal Gear Oil {grade} GL-5", "T",
                "5ac22f_aae15b506f224405a519a50f9b8ac589~mv2.jpg",
                sae_gear=grade, api_gl=("GL-5", "MT-1"),
                performance=("Source also claims suitability where API GL-4, GL-3 or EP is required",))
        for grade in ("80W-90", "85W-140")
    ],
    product("TEK HD 3% Moly Grease", "G",
            "5ac22f_0343374184164682b838619a9b53b20d~mv2.jpg",
            source_grade="3% Moly",
            flags=("no_nlgi_grade_published",)),
    product("TEK Drive Train Fluid SAE 10W", "TF",
            "5ac22f_5a20518e0040462db04e8a3063a60bd5~mv2.jpg",
            sae_engine="10W", performance=("Caterpillar TO-4", "Allison C-4")),
    product("TEK Turbine Oil", "U",
            "5ac22f_0a4937028d814507847d7e9353bae720~mv2.jpg",
            flags=("current_named_series_without_published_viscosity_grade",)),
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip += 1

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


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def text_from_html(value):
    parser = TextExtractor()
    parser.feed(value.decode("utf-8", "replace"))
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()


def verify_page(page_bytes, required, label):
    page_text = text_from_html(page_bytes)
    missing = [token for token in required if token.casefold() not in page_text.casefold()]
    if missing:
        raise RuntimeError(f"{label} page facts changed: {missing}")
    return page_text


def fetch_and_verify_images(base, expected):
    facts = {}
    for filename, expected_sha in expected.items():
        payload = get(base + filename)
        actual = sha256(payload)
        if actual != expected_sha:
            raise RuntimeError(f"official product-card image changed: {filename} {actual}")
        facts[filename] = {
            "url": base + filename,
            "sha256": actual,
            "bytes": len(payload),
        }
    return facts


def main():
    futroil_page_bytes = get(FUTROIL_PAGE)
    futroil_text = verify_page(
        futroil_page_bytes,
        (
            "Gear Oils SAE 90/140",
            "Automatic Transmission Fluid (ATF) DEX 3",
            'Two Cycle Land Oil TC3 "RED"',
            "Two Cycle Marine Oil",
            "Mineral Oil",
            "Synthetic Oil",
        ),
        "FUTROIL",
    )
    tek_page_bytes = get(TEK_PAGE)
    tek_text = verify_page(
        tek_page_bytes,
        (
            "TEK ELC",
            "TEK Premium AW Hydraulic Oils",
            "TEK LUBE monograde motor oils",
            "TEK SAE ND",
            "TEK RED ULTRA HD EP2 GREASE",
            "TEK MP ATF MD-3 OIL",
            "TEK Refrigeration",
            "TEK SYN- BLEND 15W-40 LE/ CK4/ SN",
            "TEK UNIVERSAL GEAR GL-5",
            "TEK HD 3% MOLY GREASE",
            "Catterpillar TO-4 or Allison C4",
            "TEK TURBINE OILS",
        ),
        "TEK",
    )
    futroil_image_facts = fetch_and_verify_images(FUTROIL_IMAGE_BASE, FUTROIL_IMAGES)
    tek_image_facts = fetch_and_verify_images(TEK_IMAGE_BASE, TEK_IMAGES)

    rows = []
    source_specs = [
        (
            FUTROIL_SOURCE_ID, FUTROIL_PRODUCTS, "FUTROIL-JM",
            "FUTROIL", "Future Energy Source Company Limited (FESCO)",
            FUTROIL_PAGE, futroil_text, futroil_image_facts,
            "official_jamaican_brand_product_card",
        ),
        (
            TEK_SOURCE_ID, TEK_PRODUCTS, "TEK-JM",
            "TEK", "Lubit Limited / Tekstar Lubricants",
            TEK_PAGE, tek_text, tek_image_facts,
            "official_jamaican_authorized_distributor_product_card",
        ),
    ]
    facts = []
    for (source_id, products, prefix, brand, owner, page_url, page_text,
         image_facts, evidence_status) in source_specs:
        for index, item in enumerate(products, 1):
            image = image_facts[item["image"]]
            quality_flags = [
                evidence_status,
                "official_product_card_artwork_sha256_verified",
                "source_reported_performance_claims_not_independent_approvals",
                "marketing_prose_excluded",
            ] + item["flags"]
            row = {
                "source_id": source_id,
                "source_record_id": f"{prefix}-{index:02d}",
                "market": "Jamaica",
                "manufacturer": "",
                "brand_owner_and_distributor": owner,
                "brand": brand,
                "product_name": item["name"],
                "family_code": item["family_code"],
                "technical": item["technical"],
                "lifecycle_status": "listed_on_current_official_jamaican_site",
                "evidence_status": evidence_status,
                "snapshot_date": SNAPSHOT_DATE,
                "source_url": page_url,
                "source_page_text_sha256": sha256(page_text.encode()),
                "source_image_url": image["url"],
                "source_image_sha256": image["sha256"],
                "source_quality_flags": quality_flags,
            }
            rows.append(row)
            facts.append({
                "source_id": source_id,
                "name": item["name"],
                "technical": item["technical"],
                "source_image_sha256": image["sha256"],
            })

    if len(FUTROIL_PRODUCTS) != 8 or len(TEK_PRODUCTS) != 21 or len(rows) != 29:
        raise RuntimeError("Jamaica audit matrix drift")
    facts_sha = sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True).encode())
    for row in rows:
        row["source_facts_sha256"] = facts_sha

    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "source_ids": [FUTROIL_SOURCE_ID, TEK_SOURCE_ID],
        "snapshot_date": SNAPSHOT_DATE,
        "official_pages_audited": 2,
        "official_product_card_images_audited": len(FUTROIL_IMAGES) + len(TEK_IMAGES),
        "official_product_card_image_bytes": sum(
            image["bytes"]
            for image in [*futroil_image_facts.values(), *tek_image_facts.values()]
        ),
        "futroil_normalized_product_grades": len(FUTROIL_PRODUCTS),
        "tek_normalized_product_grades": len(TEK_PRODUCTS),
        "normalized_product_grade_identities": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "rows_with_sae": sum(bool(
            row["technical"]["sae_engine"] or row["technical"]["sae_gear"]
        ) for row in rows),
        "rows_with_api_or_api_gl": sum(bool(
            row["technical"]["api"] or row["technical"]["api_gl"]
        ) for row in rows),
        "rows_with_iso_vg": sum(bool(row["technical"]["iso_vg"]) for row in rows),
        "source_facts_sha256": facts_sha,
        "source_page_text_sha256": {
            FUTROIL_PAGE: sha256(futroil_text.encode()),
            TEK_PAGE: sha256(tek_text.encode()),
        },
        "source_image_facts": {
            FUTROIL_SOURCE_ID: futroil_image_facts,
            TEK_SOURCE_ID: tek_image_facts,
        },
        "normalized_output_sha256": sha256(OUT.read_bytes()),
        "deferred_jamaica_layers": {
            "RYMAX_JAMAICA": (
                "Large official distributor catalog discovered; defer to the global Rymax "
                "identity pass so Jamaica availability does not create duplicate product truth."
            ),
            "ATLANTIC_LUBRICANTS_JAMAICA": (
                "Large official distributor catalog discovered; defer to the global Atlantic "
                "manufacturer pass and keep Jamaica as an availability/source occurrence."
            ),
        },
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
