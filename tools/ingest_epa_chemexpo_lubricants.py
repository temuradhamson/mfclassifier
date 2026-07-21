#!/usr/bin/env python3
"""Normalize lubricant and technical-fluid products from US EPA ChemExpo/CPDat.

ChemExpo exposes a public product table for each Product Use Category (PUC).
This loader uses those product identities rather than treating a keyword hit in
the one-gigabyte composition export as proof of product scope.  Broad PUCs are
filtered conservatively and package-only suffixes are merged while every EPA
product ID and source spelling is retained.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "epa-chemexpo-lubricants.jsonl"
REPORT = ROOT / "data" / "epa-chemexpo-lubricants-report.json"
SOURCE_ID = "EPA_CHEMEXPO_CPDAT_LUBRICANTS"
SOURCE_PAGE_URL = "https://comptox.epa.gov/chemexpo/"
GET_DATA_URL = "https://comptox.epa.gov/chemexpo/get_data/"
PUC_CSV_URL = "https://comptox.epa.gov/chemexpo/dl_pucs/"
PRODUCT_API_URL = "https://comptox.epa.gov/chemexpo/p_json/"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (official-open-government-data)"
PAGE_SIZE = 100  # The public endpoint caps responses at 100 rows.


# direct: the PUC itself establishes the relevant professional scope.
# filtered_*: the PUC is intentionally broader than this catalog.
PUC_RULES = {
    91: "direct",      # Home maintenance / lock deicer
    92: "direct",      # Home maintenance / lubricant
    123: "direct",     # Landscape / lawnmower fluids
    238: "filtered_clipper",
    277: "filtered_windshield",
    282: "filtered_boat",
    291: "direct",     # Vehicle / antifreeze
    292: "filtered_auto_fluids",
    293: "direct",     # Vehicle / auto lubricant
    295: "direct",     # Vehicle / motor oil
    358: "filtered_metalworking_quality",
    378: "filtered_aviation",
    379: "direct",     # Industrial lubricants
    380: "filtered_mold_release",
    381: "direct",     # Hydraulic fluid
    385: "direct",     # Tractor hydraulic fluid
    386: "direct",     # Penetrating oil
    396: "direct",     # Aircraft deicer
    398: "direct",     # Anti-seize
}


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


def strip_html(value: str | None) -> str:
    return clean(re.sub(r"<[^>]+>", "", str(value or "")))


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError(f"Empty response from {url}")
    return payload


def fetch_puc_products(puc_id: int) -> tuple[list[list[str]], list[str], int]:
    rows: list[list[str]] = []
    page_hashes: list[str] = []
    total: int | None = None
    for start in range(0, 1_000_000, PAGE_SIZE):
        query = urllib.parse.urlencode({"puc": puc_id, "start": start, "length": PAGE_SIZE})
        payload = fetch(f"{PRODUCT_API_URL}?{query}")
        page_hashes.append(hashlib.sha256(payload).hexdigest())
        page = json.loads(payload)
        page_total = int(page["recordsTotal"])
        if total is None:
            total = page_total
        elif page_total != total:
            raise RuntimeError(f"PUC {puc_id} total changed during pagination: {total} -> {page_total}")
        page_rows = page.get("data", [])
        rows.extend(page_rows)
        if len(rows) >= total or not page_rows:
            break
        time.sleep(0.03)
    if total is None or len(rows) != total:
        raise RuntimeError(f"PUC {puc_id} pagination incomplete: expected {total}, got {len(rows)}")
    return rows, page_hashes, total


def scoped(
    rule: str,
    product_name: str,
    manufacturer: str = "",
    classification_method: str = "",
) -> tuple[bool, str]:
    value = normalize(product_name)
    if rule == "direct":
        return True, "exact_relevant_puc"
    if rule == "filtered_metalworking_quality":
        explicit = re.search(
            r"\b(?:(?:cutting|tapping|grinding|machining|metalworking|stamping|drawing|forming|"
            r"quench(?:ing)?)\s+(?:oil|oils|fluid|fluids|coolant|lubricant|lube)|"
            r"coolant|lubricant|lubricants|lube|grease|metalworking fluid)\b",
            value,
        )
        obvious_misclassification = re.search(
            r"\b(?:electrode|electrodes|welding|polyurethane|polyurithane|polyrethane|polurethane|"
            r"fluoroelastomer|topcoat|coating|curing agent|accelerator|catalyst|primer|paint|"
            r"adhesive|sealant)\b",
            value,
        )
        caap_coating_cluster = normalize(manufacturer) == "caap co inc"
        include = not caap_coating_cluster and (not obvious_misclassification or bool(explicit))
        return include, (
            "metalworking_puc_with_explicit_name_support" if explicit else "metalworking_puc_opaque_name"
        )
    if rule == "filtered_mold_release":
        explicit = re.search(
            r"\b(?:mould|mold|release|mold rel|mold re|epoxease|plastilease|freekote|"
            r"mold wiz|moldwax|mold wax|mold ease|moldaway|formkote|eject|pull ease|"
            r"partall|silicone spray|grease|lubricant|lubricating|lube|oil|wax)\b",
            value,
        )
        obvious_misclassification = re.search(
            r"\b(?:mildewcide|epoxy resin|resin thinner|phenolic powder|gasketing|"
            r"welding rod|solder|flux|etch|paint|reducer|abrasive|compressed asbestos|"
            r"acid|toluenediamine|fluorescene|pigment|accelerator|brazing alloy)\b",
            value,
        )
        reviewed_assignment = normalize(classification_method) in {
            "manual", "manual batch", "bulk assignment",
        }
        include = bool(explicit or (reviewed_assignment and not obvious_misclassification))
        if explicit:
            return include, "mold_release_puc_with_explicit_name_support"
        if include:
            return include, "reviewed_mold_release_puc_assignment"
        return include, "strict_mold_release_name_or_reviewed_assignment_filter"
    if rule == "filtered_boat":
        positive = re.search(
            r"\b(?:oil|oils|lube|lubricant|lubricants|lubricating|grease|greases|"
            r"transmission fluid|steering fluid|hydraulic fluid|antifreeze|coolant)\b",
            value,
        )
        negative = re.search(
            r"\b(?:fuel stabilizer|octane boost|carb|choke cleaner|decarbonizer|motor treatment|fuel treatment)\b",
            value,
        )
        return bool(positive and not negative), "strict_name_filter_within_broad_boat_fluids_puc"
    if rule == "filtered_auto_fluids":
        positive = re.search(
            r"\b(?:automatic transmission fluid|transmission fluid|transmax|atf|dexron|mercon|dex merc|"
            r"cvt fluid|dct fluid|brake fluid|power steering fluid|hydraulic fluid|gear oil|"
            r"differential fluid|antifreeze|coolant|radiator stop leak|coolant stop leak)\b",
            value,
        )
        negative = re.search(r"\b(?:cleaner|cleaning|flush|engine stop leak|fuel|injector|octane)\b", value)
        return bool(positive and not negative), "strict_name_filter_within_broad_auto_fluids_and_additives_puc"
    if rule == "filtered_windshield":
        positive = re.search(r"\b(?:washer|wash|fluid|deicer|de icer)\b", value)
        return bool(positive), "strict_name_filter_within_windshield_products_puc"
    if rule == "filtered_clipper":
        positive = re.search(r"\b(?:clipper oil|lubricant|lubricating|lube)\b", value)
        return bool(positive), "strict_name_filter_within_clipper_cleaner_lubricant_puc"
    if rule == "filtered_aviation":
        positive = re.search(
            r"\b(?:oil|oils|lube|lubricant|lubricants|lubricating|grease|greases|hydraulic fluid)\b",
            value,
        )
        fuel = re.search(r"\b(?:jet a|avgas|avcat|kerosene|fuel oil|gasoline|fsii|jp 8|ts 1)\b", value)
        return bool(positive and not fuel), "strict_name_filter_excluding_fuels_from_aviation_fluids_puc"
    raise ValueError(f"Unknown scope rule: {rule}")


def strip_package(product_name: str) -> str:
    value = re.sub(r"\s*\((?:discontinued|obsolete)\)\s*$", "", clean(product_name), flags=re.I)
    units = (
        r"(?:fl\.?\s*oz|wt\.?\s*oz|ounces?|oz|gallons?|gal|quarts?|qt|pints?|pt|"
        r"pounds?|lbs?|kilograms?|kg|grams?|g|milliliters?|ml|lit(?:er|re)s?|l)"
    )
    value = re.sub(
        rf"(?:\s*[,;/-]\s*|\s+)\d+(?:\.\d+)?\s*{units}"
        r"(?:\s*(?:bottle|can|pail|drum|case|pack|pk))?\s*$",
        "",
        value,
        flags=re.I,
    )
    value = re.sub(r"\s*[,;-]?\s*\d+\s*(?:pk|pack)\s*$", "", value, flags=re.I)
    value = re.sub(r"\s*[-,;]?\s*(?:bottle|can|pail|drum)\s*$", "", value, flags=re.I)
    return clean(value).strip(" ,-;")


def family_for(puc_id: int, product_name: str) -> str:
    value = normalize(product_name)
    if puc_id == 295:
        return "M"
    if puc_id in {381, 385}:
        return "H"
    if puc_id == 358:
        return "I"
    if puc_id in {91, 277, 291, 396}:
        return "TF"
    if puc_id == 398:
        return "S"
    if re.search(r"\b(?:antifreeze|coolant|deicer|de icer|brake fluid|power steering fluid|windshield|washer fluid)\b", value):
        return "TF"
    if re.search(r"\b(?:motor oil|engine oil|two cycle oil|2 cycle oil|four cycle oil|4 cycle oil)\b", value):
        return "M"
    if re.search(r"\b(?:automatic transmission fluid|transmission fluid|transmax|atf|dexron|mercon|"
                 r"cvt fluid|dct fluid|gear oil|differential fluid|tractor fluid)\b", value):
        return "T"
    if re.search(r"\bhydraulic\b", value):
        return "H"
    if re.search(r"\b(?:compressor oil|refrigeration oil)\b", value):
        return "C"
    if re.search(r"\bturbine oil\b", value):
        return "U"
    if re.search(r"\b(?:transformer oil|dielectric oil|insulating oil)\b", value):
        return "E"
    if re.search(r"\b(?:grease|greases)\b", value):
        return "G"
    if puc_id == 358 or re.search(r"\b(?:cutting|tapping|grinding|metalworking|stamping|drawing|quenching)\b", value):
        return "I"
    return "S"


def technical(product_name: str) -> dict[str, list[str]]:
    upper = unicodedata.normalize("NFKC", product_name).upper().replace("–", "-").replace("—", "-")
    sae = sorted({f"{a}W-{b}" for a, b in re.findall(r"(?<!\d)(0|5|10|15|20|25)W[-\s]?([0-9]{2})(?!\d)", upper)})
    sae += sorted({f"SAE {v}" for v in re.findall(r"\bSAE\s*([0-9]{2,3})\b", upper) if f"SAE {v}" not in sae})
    iso_vg = sorted(set(re.findall(r"\bISO(?:\s*VG)?\s*([0-9]{1,4})\b", upper)))
    nlgi = sorted(set(re.findall(r"\bNLGI\s*(000|00|0|[1-6])\b", upper)))
    api = sorted(set(re.findall(r"\bAPI\s+((?:SP|SN\+?|SM|SL|SJ|SH|CK-4|CJ-4|CI-4|CH-4|CF-4|FA-4)(?:\s*/\s*(?:SP|SN|SM|SL|SJ|CK-4|CJ-4|CI-4|CH-4|CF-4))?)\b", upper)))
    brake = sorted({f"DOT {v}" for v in re.findall(r"\bDOT\s*(3|4|5(?:\.1)?)\b", upper)})
    atf = sorted(set(re.findall(r"\b(?:DEXRON\s*[A-Z0-9-]+|MERCON\s*[A-Z0-9-]+|ATF\+?4|TYPE\s+F)\b", upper)))
    return {"sae": sae, "api": api, "iso_vg": iso_vg, "nlgi": nlgi, "brake_fluid_class": brake, "atf": atf}


def preferred(values: list[str]) -> str:
    counts = Counter(clean(value) for value in values if clean(value))
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-item[1], normalize(item[0]), item[0]))[0][0]


def main() -> None:
    puc_payload = fetch(PUC_CSV_URL)
    puc_rows = list(csv.DictReader(io.StringIO(puc_payload.decode("utf-8-sig"))))
    metadata = {int(row["PUC ID"]): row for row in puc_rows}
    if not set(PUC_RULES).issubset(metadata):
        raise RuntimeError("ChemExpo PUC metadata is missing required categories")

    raw_occurrences: list[dict] = []
    exclusions: Counter[str] = Counter()
    category_report: dict[str, dict] = {}
    aggregate_page_hashes: list[str] = []
    for puc_id, rule in sorted(PUC_RULES.items()):
        source_rows, page_hashes, total = fetch_puc_products(puc_id)
        aggregate_page_hashes.extend(f"{puc_id}:{value}" for value in page_hashes)
        kept = 0
        for source_row in source_rows:
            if len(source_row) < 4:
                raise RuntimeError(f"Unexpected ChemExpo product row for PUC {puc_id}: {source_row!r}")
            link_html, brand_html, manufacturer_html, method_html = source_row[:4]
            product_name = strip_html(link_html)
            match = re.search(r"/chemexpo/product/(\d+)/", link_html)
            if not match:
                raise RuntimeError(f"Missing ChemExpo product ID in {link_html!r}")
            brand = strip_html(brand_html)
            manufacturer = strip_html(manufacturer_html)
            classification_method = strip_html(method_html)
            include, basis = scoped(rule, product_name, manufacturer, classification_method)
            normalized_name = normalize(product_name)
            cleaner_only = re.search(
                r"\b(?:cleaner|degreaser|grease cutter|parts cleaner|carburetor cleaner|choke cleaner)\b",
                normalized_name,
            )
            cleaner_lubricant_context = re.search(
                r"\b(?:lubricant|lubricating|lube|oil|antifreeze|coolant|washer|wash|deicer|de icer)\b",
                normalized_name,
            )
            if include and cleaner_only and not cleaner_lubricant_context:
                include = False
                basis = "cleaner_without_lubricant_or_technical_fluid_context_excluded"
            if include and puc_id == 358 and re.search(
                r"\b(?:urethane reducer|reducer(?: number| no)?|reducing compound)\b",
                normalized_name,
            ):
                include = False
                basis = "metalworking_puc_paint_reducer_misclassification_excluded"
            if include and re.search(r"\bbattery(?: terminal)? coating\b", normalized_name):
                include = False
                basis = "battery_terminal_coating_not_lubricant_excluded"
            if include and re.search(r"\bgasoline (?:dryer )?(?:and )?antifreeze\b", normalized_name):
                include = False
                basis = "gasoline_fuel_additive_not_coolant_excluded"
            obvious_fuel = re.search(r"\b(?:fuel oil|oil fuel)\b", normalized_name)
            lubricant_context = re.search(r"\b(?:engine|motor|lubricant|lubricating|lube|grease)\b", normalized_name)
            if include and obvious_fuel and not lubricant_context:
                include = False
                basis = "obvious_fuel_product_excluded_despite_puc_assignment"
            non_lubricant_material = re.search(r"\b(?:adhesive|sealant|thinner)\b", normalized_name)
            broader_relevant_context = re.search(
                r"\b(?:oil|lubricant|lubricating|lube|grease|anti seize|cutting|hydraulic|coolant|"
                r"antifreeze|deicer|de icing|anti icing|heat transfer fluid)\b",
                normalized_name,
            )
            if include and non_lubricant_material and not broader_relevant_context:
                include = False
                basis = "obvious_non_lubricant_material_excluded_despite_puc_assignment"
            if not include:
                exclusions[f"puc_{puc_id}_{basis}"] += 1
                continue
            kept += 1
            raw_occurrences.append({
                "puc_id": puc_id,
                "puc_kind": clean(metadata[puc_id]["PUC kind"]),
                "puc_general_category": clean(metadata[puc_id]["General category"]),
                "puc_product_family": clean(metadata[puc_id]["Product family"]),
                "puc_product_type": clean(metadata[puc_id]["Product type"]),
                "puc_definition": clean(metadata[puc_id]["Definition"]),
                "source_product_id": match.group(1),
                "source_product_url": f"https://comptox.epa.gov/chemexpo/product/{match.group(1)}/",
                "source_product_name": product_name,
                "canonical_product_name": strip_package(product_name),
                "brand": brand,
                "manufacturer": manufacturer,
                "classification_method": strip_html(method_html),
                "classification_basis": basis,
            })
        category_report[str(puc_id)] = {
            "general_category": clean(metadata[puc_id]["General category"]),
            "product_family": clean(metadata[puc_id]["Product family"]),
            "product_type": clean(metadata[puc_id]["Product type"]),
            "scope_rule": rule,
            "source_products": total,
            "kept_occurrences": kept,
            "excluded_occurrences": total - kept,
            "api_page_sha256": page_hashes,
        }

    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in raw_occurrences:
        family = family_for(row["puc_id"], row["canonical_product_name"])
        owner = normalize(row["manufacturer"] or row["brand"])
        identity: tuple = (family, normalize(row["manufacturer"]), normalize(row["brand"]), normalize(row["canonical_product_name"]))
        if not owner:
            # A generic name with no owner is not sufficient to merge two EPA
            # identities safely (for example, "Motor Oil SAE 30").
            identity += (row["source_product_id"],)
        grouped[identity].append(row)

    records: list[dict] = []
    for identity, rows in sorted(grouped.items(), key=lambda item: item[0]):
        canonical_name = preferred([row["canonical_product_name"] for row in rows])
        manufacturer = preferred([row["manufacturer"] for row in rows])
        source_brand = preferred([row["brand"] for row in rows])
        brand = source_brand or manufacturer or "EPA ChemExpo — owner not reported"
        family = family_for(rows[0]["puc_id"], canonical_name)
        source_product_ids = sorted({row["source_product_id"] for row in rows}, key=int)
        source_names = sorted({row["source_product_name"] for row in rows}, key=lambda value: (normalize(value), value))
        pucs = []
        for row in sorted(rows, key=lambda value: value["puc_id"]):
            fact = {
                "puc_id": row["puc_id"],
                "kind": row["puc_kind"],
                "general_category": row["puc_general_category"],
                "product_family": row["puc_product_family"],
                "product_type": row["puc_product_type"],
                "definition": row["puc_definition"],
                "classification_method": row["classification_method"],
                "classification_basis": row["classification_basis"],
            }
            if fact not in pucs:
                pucs.append(fact)
        record_identity = "|".join([family, normalize(manufacturer), normalize(source_brand), normalize(canonical_name), ",".join(source_product_ids)])
        source_record_id = "EPA-CHEMEXPO-" + hashlib.sha256(record_identity.encode()).hexdigest()[:16].upper()
        flags = ["cpdat_data_not_reviewed_by_epa_use_judgment", "lifecycle_not_reported"]
        if any(fact["classification_basis"].endswith("opaque_name") for fact in pucs):
            flags.append("professional_puc_with_opaque_product_name")
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": source_record_id,
            "source_page_url": SOURCE_PAGE_URL,
            "source_get_data_url": GET_DATA_URL,
            "source_puc_urls": [f"https://comptox.epa.gov/chemexpo/puc/{fact['puc_id']}/" for fact in pucs],
            "source_product_ids": source_product_ids,
            "source_product_urls": [f"https://comptox.epa.gov/chemexpo/product/{value}/" for value in source_product_ids],
            "source_product_names": source_names,
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "manufacturer": manufacturer,
            "brand": brand,
            "brand_source_reported": source_brand,
            "brand_basis": "source_reported" if source_brand else "manufacturer_fallback" if manufacturer else "owner_not_reported",
            "product_name": canonical_name,
            "family_code": family,
            "market": "US / EPA CPDat source records",
            "puc_evidence": pucs,
            "technical": technical(canonical_name),
            "source_occurrence_count": len(rows),
            "package_and_source_name_variants": source_names,
            "source_quality_flags": flags,
            "lifecycle_status": "historical_or_current_status_not_reported",
            "evidence_status": "official_government_compiled_product_database",
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_us_epa_chemexpo_cpdat_lubricants_normalized",
        "source_id": SOURCE_ID,
        "source_page_url": SOURCE_PAGE_URL,
        "source_get_data_url": GET_DATA_URL,
        "source_puc_csv_url": PUC_CSV_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "cpdat_release": "4.1 (May 2025)",
        "licence": "CC0",
        "puc_metadata_sha256": hashlib.sha256(puc_payload).hexdigest(),
        "api_pages_manifest_sha256": hashlib.sha256("\n".join(aggregate_page_hashes).encode()).hexdigest(),
        "source_category_product_occurrences": sum(item["source_products"] for item in category_report.values()),
        "kept_product_occurrences": len(raw_occurrences),
        "excluded_product_occurrences": sum(exclusions.values()),
        "normalized_products": len(records),
        "within_source_occurrences_merged": len(raw_occurrences) - len(records),
        "manufacturers_reported": len({row["manufacturer"] for row in records if row["manufacturer"]}),
        "brands_reported": len({row["brand_source_reported"] for row in records if row["brand_source_reported"]}),
        "owner_not_reported_products": sum(not row["manufacturer"] and not row["brand_source_reported"] for row in records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "categories": category_report,
        "exclusions": dict(sorted(exclusions.items())),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "grain_note": "One row is a conservative manufacturer/brand + formulation name + professional family identity; package suffixes and exact repeated EPA product records are merged with all EPA product IDs retained.",
        "lifecycle_note": "CPDat mixes historical and current source documents and does not assert current market availability. No row is promoted to an active offer.",
        "quality_note": "EPA states that ChemExpo data are compiled from public sources and are not reviewed by EPA. Exact PUC evidence, curation method and direct product cards are retained; broad categories use explicit inclusion filters.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
