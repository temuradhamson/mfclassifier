#!/usr/bin/env python3
"""Ingest the complete live Galana Madagascar Mobil product endpoint."""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/madagascar-galana-mobil-products.jsonl"
REPORT = ROOT / "data/madagascar-galana-mobil-report.json"
SNAPSHOT_DATE = "2026-07-24"
SOURCE_ID = "MADAGASCAR_GALANA_COMPLETE_MOBIL_PRODUCT_API"
API = "https://galana.mg/wp-json/wp/v2/"

EXPECTED_IDS = {
    6999, 5806, 5803, 5801, 5800, 5797, 5793, 5790, 5788, 5786,
    5784, 5781, 5774, 5770, 5772, 5764, 5762, 5760, 5758, 5755,
    5750, 5747, 5746, 5743, 5733, 5729, 5727, 5725, 5723, 5716,
    5709, 5706, 5699, 5696, 5694, 5693, 5686, 5675, 5673, 5666,
    5664, 5494, 5492, 4638, 4414,
}

PACKAGE_TAGS = {
    19: "208 L", 24: "208 L", 25: "20 L", 35: "4 L", 39: "1 L",
    42: "5 L", 44: "0.25 L", 50: "16 kg", 51: "0.39 kg",
    52: "18 kg", 53: "180 kg",
}


def spec(
    family: str,
    *,
    sae_engine: str = "",
    sae_gear: str = "",
    iso_vg: str = "",
    nlgi: str = "",
    dot: str = "",
    source_grade: str = "",
    api: tuple[str, ...] = (),
    api_gl: tuple[str, ...] = (),
    acea: tuple[str, ...] = (),
    jaso: tuple[str, ...] = (),
    standards: tuple[str, ...] = (),
    flags: tuple[str, ...] = (),
    target: tuple[str, str] = ("", ""),
) -> dict:
    return {
        "family": family,
        "sae_engine": sae_engine,
        "sae_gear": sae_gear,
        "iso_vg": iso_vg,
        "nlgi": nlgi,
        "dot": dot,
        "source_grade": source_grade,
        "api": api,
        "api_gl": api_gl,
        "acea": acea,
        "jaso": jaso,
        "standards": standards,
        "flags": flags,
        "target": target,
    }


SPECS = {
    "Nuto H Series": spec("H", source_grade="H Series"),
    "Unirex N 2": spec("G", source_grade="N 2", target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-6492347001bc4c8c")),
    "Mobil Centaur XHP 462": spec("G", source_grade="XHP 462", target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-2c42b374d9d77672")),
    "Mobilux EP 3": spec("G", nlgi="3", flags=("nlgi_read_from_product_designation",), target=("EAEU_CONFORMITY_LUBRICANT_PRODUCTS", "EAEU-e64a57d4a008190a6119")),
    "Mobilux EP 2": spec("G", nlgi="2", flags=("nlgi_read_from_product_designation",), target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-0f1d2cfc2eca5e6c")),
    "Mobilgrease FM 222": spec("G", source_grade="FM 222", standards=("NSF H1", "DIN 51825 KPF2K-20", "Kosher/Parve", "Halal")),
    "Mobil Super 2T": spec("M", source_grade="two-stroke", api=("TC",), jaso=("FB",), target=("ANP_BRAZIL_LUBRICANT_REGISTRY", "ANP-2984-238e689597daccea")),
    "Mobil 1 Racing 2T": spec("M", source_grade="two-stroke", api=("TC",), jaso=("FC", "FD"), target=("ANP_BRAZIL_LUBRICANT_REGISTRY", "ANP-1952-9bdb315b78c69ec1")),
    "Mobil 1 Racing 4T 15W-50": spec("M", sae_engine="15W-50", api=("SM", "SN"), jaso=("MA2", "MA"), target=("DOMINICAN_REPUBLIC_IMCA_MOBIL_2025_CATALOG", "IMCA-MOBIL-2025-042")),
    "Mobil Brake Fluid Dot 4": spec("TF", dot="DOT 4", standards=("FMVSS 116 DOT 3", "FMVSS 116 DOT 4", "ISO 4925:2005 Class 4", "SAE J1704")),
    "Mobilube HD 80W-90": spec("T", sae_gear="80W-90", api_gl=("GL-5",), target=("ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP", "GEARPROS-PRODUCT-f67869ff3fcd87e3c57e")),
    "Mobil ATF 220": spec("T", source_grade="DEXRON IID", standards=("DEXRON IID", "Allison C-4", "Caterpillar TO-2", "Volvo 97340"), target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-2b36ae8658cdec07")),
    "Mobil ATF 320": spec("T", source_grade="DEXRON IIIG", standards=("DEXRON IIIG", "Allison C-4")),
    "Mobil Super 1000 20W-50": spec("M", sae_engine="20W-50", api=("SL",)),
    "Mobil Super 1000 X1 15W-40": spec("M", sae_engine="15W-40", api=("CF", "SL"), standards=("VW 505 00", "VW 501 01", "MB 229.1"), target=("ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP", "GEARPROS-PRODUCT-7b9687bf8d24edb2a7b5")),
    "Mobil Super 2000 X1 10W-40": spec("M", sae_engine="10W-40", api=("SN", "SM", "SL", "SJ", "CF"), acea=("A3/B3",), standards=("VW 505 00", "VW 501 01", "MB 229.1", "AVTOVAZ"), target=("ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP", "GEARPROS-PRODUCT-f02bf5881c64705d20fa")),
    "Mobil Super 3000 X1 5W-40": spec("M", sae_engine="5W-40", api=("SN", "SM", "SL", "SJ", "CF"), acea=("A3/B3", "A3/B4"), standards=("Renault RN0710", "VW 505 00", "MB 229.3", "PSA B71 2296", "Porsche A40", "Fiat 9.55535-M2"), target=("MERCEDES_BENZ_BEVO_APPROVED_FLUIDS", "MB-BEVO-12504c2148960976225a")),
    "Mobil 1 ESP 5W-30": spec("M", sae_engine="5W-30", api=("SN", "SM", "SL", "SJ", "CF"), acea=("C2", "C3"), target=("MERCEDES_BENZ_BEVO_APPROVED_FLUIDS", "MB-BEVO-95718ff1e652c4d1946f")),
    "Mobilfluid 426": spec("T", source_grade="UTTO", api_gl=("GL-4",), standards=("Caterpillar TO-2", "John Deere J20C", "Denison UTTO/THF", "Massey Ferguson M 1145"), target=("ANP_BRAZIL_LUBRICANT_REGISTRY", "ANP-16363-051a645e8132c70c")),
    "Mobil Agry Extra 10W-40": spec("T", sae_gear="10W-40", flags=("source_title_body_product_conflict_delvac_specs_excluded", "tractor_application_retained_from_card_category_and_application")),
    "Mobiltrans HD 30": spec("T", sae_gear="30", standards=("Caterpillar TO-4", "ZF TE-ML 07F", "Allison C-4")),
    "Mobiltrans HD 50": spec("T", sae_gear="50", standards=("Caterpillar TO-4",), target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-4432fe112998e55c")),
    "Mobilube HD 85W-140": spec("T", sae_gear="85W-140", api_gl=("GL-5",), target=("GRENADA_SOL_CURRENT_ECOMMERCE_CATALOG", "SOL-GD-PRODUCT-BB49D0FD17815CB4")),
    "Mobilube HD 75W-90": spec("T", sae_gear="75W-90", api_gl=("GL-5",), target=("EAEU_CONFORMITY_LUBRICANT_PRODUCTS", "EAEU-53e5d4118d17e0823788")),
    "Mobil Hydraulic 10W": spec("H", source_grade="SAE 10W"),
    "Mobil Delvac 1340": spec("M", sae_engine="40", api=("CF",), flags=("sae_read_from_product_designation_1340",), target=("ANP_BRAZIL_LUBRICANT_REGISTRY", "ANP-5881-3f0c445da7de9757")),
    "Mobil Delvac MX 15W-40": spec("M", sae_engine="15W-40", api=("CI-4", "CH-4", "CG-4"), acea=("E7", "E9"), standards=("Cummins CES 20086", "Volvo VDS-3", "Caterpillar ECF-2"), target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-7bea55407c19ba8a")),
    "Mobil Delvac XHP ESP 10W-40": spec("M", sae_engine="10W-40", api=("CK-4", "CJ-4", "CI-4 PLUS"), acea=("E7", "E9"), jaso=("DH-2",), standards=("Cummins CES 20086", "Caterpillar ECF-3", "Volvo VDS-4.5"), target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-bb1038f985f4ecb3")),
    "Mobiltherm 605": spec("I", source_grade="605", target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-5e3a24c4a38b6c2c")),
    "Mobil Velocite Oil No 6": spec("I", source_grade="No. 6"),
    "Mobilect 39": spec("I", source_grade="39"),
    "Mobil SHC CIbus 46": spec("I", iso_vg="46", standards=("NSF H1", "DIN 51506:2013-12 VDL", "Halal", "Kosher/Parve")),
    "Mobil Vacuoline": spec("I", source_grade="528", flags=("specific_variant_528_read_from_live_card_body",)),
    "Mobil DTE OIL": spec("I", source_grade="named series"),
    "Mobil Zerice S 100": spec("C", source_grade="S 100"),
    "Mobil EAL Arctic 68": spec("C", iso_vg="68", target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-ed46dc6eb3f52ff4")),
    "Mobil Rarus 420 Series": spec("C", source_grade="420 Series", flags=("card_body_mentions_rarus_427_without_expanding_local_series",)),
    "Mobil Rarus 829": spec("C", source_grade="829", target=("INDONESIA_NPT_LUBRICANT_REGISTRY", "ID-NPT-47f36de07e70db5d")),
    "Mobilgear 600 XP": spec("I", source_grade="600 XP Series"),
    "Mobil DTE 25": spec("H", source_grade="25", target=("EAEU_CONFORMITY_LUBRICANT_PRODUCTS", "EAEU-0813ef86b824f56f35c2")),
}


def fetch(url: str) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "mfclassifier-source-audit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read(), dict(response.headers.items())


def clean_markup(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<script.*?</script>|<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def identity(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode(
        "ascii", "ignore"
    ).decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def main() -> None:
    payload, headers = fetch(
        API
        + "upcp_product?per_page=100&_fields=id,slug,link,date,modified,"
        + "status,title,content,upcp-product-category,upcp-product-tag"
    )
    cards = json.loads(payload)
    if len(cards) != 45 or {row["id"] for row in cards} != EXPECTED_IDS:
        raise RuntimeError("Galana complete product endpoint denominator changed")
    if headers.get("X-WP-Total") != "45" or headers.get(
        "X-WP-TotalPages"
    ) != "1":
        raise RuntimeError("Galana endpoint pagination changed")
    if any(row["status"] != "publish" for row in cards):
        raise RuntimeError("Galana live-card status changed")

    tax_payload, _ = fetch(API + "upcp-product-category?per_page=100")
    tag_payload, _ = fetch(API + "upcp-product-tag?per_page=100")
    tax = {row["id"]: html.unescape(row["name"]) for row in json.loads(tax_payload)}
    tags = {row["id"]: html.unescape(row["name"]) for row in json.loads(tag_payload)}
    if any(
        re.sub(r"[^a-z0-9]+", "", tags.get(key, "").casefold())
        != re.sub(r"[^a-z0-9]+", "", value.casefold())
        for key, value in PACKAGE_TAGS.items()
    ):
        raise RuntimeError("Galana package-tag taxonomy changed")

    grouped = defaultdict(list)
    for card in cards:
        grouped[html.unescape(card["title"]["rendered"]).strip()].append(card)
    if set(grouped) != set(SPECS) or len(grouped) != 40:
        raise RuntimeError("Galana reviewed identity title set changed")
    duplicate_titles = {
        title: sorted(row["id"] for row in rows)
        for title, rows in grouped.items() if len(rows) > 1
    }
    if duplicate_titles != {
        "Mobil ATF 220": [5743, 5781],
        "Mobil ATF 320": [5733, 5774],
        "Mobilube HD 80W-90": [5727, 5784],
        "Mobilux EP 2": [5770, 5800],
        "Nuto H Series": [4638, 6999],
    }:
        raise RuntimeError("Galana reviewed duplicate-card set changed")

    records = []
    for sequence, title in enumerate(sorted(grouped, key=identity), 1):
        source_cards = sorted(grouped[title], key=lambda row: row["id"])
        reviewed = SPECS[title]
        card_facts = []
        package_names = set()
        categories = set()
        for card in source_cards:
            text = clean_markup(card["content"]["rendered"])
            package_names.update(
                PACKAGE_TAGS[tag_id]
                for tag_id in card.get("upcp-product-tag", [])
                if tag_id in PACKAGE_TAGS
            )
            categories.update(
                tax[category_id]
                for category_id in card.get("upcp-product-category", [])
                if category_id in tax
            )
            card_facts.append({
                "id": card["id"],
                "slug": card["slug"],
                "url": card["link"],
                "modified": card["modified"],
                "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "category_ids": card.get("upcp-product-category", []),
                "tag_ids": card.get("upcp-product-tag", []),
            })
        flags = [
            "complete_live_exclusive_distributor_product_api",
            "manufacturer_brand_mobil",
            "source_reported_specifications_not_independent_approvals",
            "duplicate_category_cards_collapsed_by_exact_product_title",
            "package_tags_retained_without_price_or_stock_inference",
            "no_offer_created",
            *reviewed["flags"],
        ]
        if title in {"Mobil 1 ESP 5W-30", "Mobil Super 3000 X1 5W-40"}:
            flags.append(
                "live_card_body_280_l_typo_not_promoted_package_tag_208_l_retained"
            )
        specifications = {
            key: reviewed[key] for key in (
                "sae_engine", "sae_gear", "iso_vg", "nlgi", "dot",
                "source_grade",
            ) if reviewed[key]
        }
        specifications.update({
            "api": list(reviewed["api"]),
            "api_gl": list(reviewed["api_gl"]),
            "acea": list(reviewed["acea"]),
            "jaso": list(reviewed["jaso"]),
            "standards_and_approvals_source_reported": list(
                reviewed["standards"]
            ),
            "source_categories": sorted(categories),
            "source_packages": sorted(package_names),
            "source_cards": card_facts,
            "source_occurrences": len(source_cards),
            "source_quality_flags": flags,
        })
        target_source_id, target_source_record_id = reviewed["target"]
        facts = {
            "title": title,
            "family": reviewed["family"],
            "specifications": specifications,
            "target": reviewed["target"],
        }
        records.append({
            "brand": "MOBIL",
            "evidence_status": "official_exclusive_country_distributor_live_product_api",
            "existing_target_source_id": target_source_id,
            "existing_target_source_record_id": target_source_record_id,
            "family_code": reviewed["family"],
            "lifecycle_status": "published_live_country_distributor_card",
            "manufacturer": "ExxonMobil",
            "market": "Madagascar",
            "product_name": (
                "Mobil Vacuoline 528" if title == "Mobil Vacuoline" else title
            ),
            "snapshot_date": SNAPSHOT_DATE,
            "source_facts_sha256": hashlib.sha256(
                json.dumps(facts, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "source_id": SOURCE_ID,
            "source_product_name": title,
            "source_record_id": f"GALANA-MG-{sequence:03d}",
            "source_url": source_cards[0]["link"],
            "specifications": specifications,
        })
    exact_matches = sum(bool(row["existing_target_source_id"]) for row in records)
    if exact_matches != 24:
        raise RuntimeError(f"Galana strict-match denominator changed: {exact_matches}")
    output = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output, encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "status": "ok",
        "source_id": SOURCE_ID,
        "source_url": "https://galana.mg/liste-lubrifiant/",
        "api_url": API + "upcp_product?per_page=100",
        "exclusive_distributor_claim_url": "https://galana.mg/lubrifiants/",
        "endpoint_rows": len(cards),
        "endpoint_pages": 1,
        "unique_product_identities": len(records),
        "duplicate_card_occurrences_collapsed": len(cards) - len(records),
        "duplicate_titles": duplicate_titles,
        "family_identity_counts": dict(sorted(Counter(
            row["family_code"] for row in records
        ).items())),
        "records_with_packages": sum(
            bool(row["specifications"]["source_packages"]) for row in records
        ),
        "exact_existing_identity_matches": exact_matches,
        "new_country_catalog_identities": len(records) - exact_matches,
        "title_body_conflicts_isolated": ["Mobil Agry Extra 10W-40"],
        "package_display_conflicts_isolated": [
            "Mobil 1 ESP 5W-30", "Mobil Super 3000 X1 5W-40",
        ],
        "offers_created": 0,
        "normalized_output_sha256": hashlib.sha256(output.encode()).hexdigest(),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "endpoint_rows": len(cards),
        "identities": len(records),
        "matched": exact_matches,
        "added": len(records) - exact_matches,
        "sha256": report["normalized_output_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
