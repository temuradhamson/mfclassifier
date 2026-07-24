#!/usr/bin/env python3
"""Normalize 325 current Rymax Belize cards into product identities."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARD_INPUT = ROOT / "data/belize-rymax-current-product-cards.jsonl"
ASSET_INPUT = ROOT / "data/belize-rymax-current-asset-facts.jsonl"
PRODUCT_OUT = ROOT / "data/belize-rymax-current-products.jsonl"
REPORT_OUT = ROOT / "data/belize-rymax-current-products-report.json"
SOURCE_ID = "BELIZE_RYMAX_CURRENT_PRODUCT_CATALOG"
SNAPSHOT_DATE = "2026-07-24"
EXPECTED_IDENTITIES = 313
EXPECTED_OUTPUT_SHA256 = (
    "6ba88fb1fe6eb963690465d2be385fa3bf3834511fdcde7186293c021b12f317"
)


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def identity_key(row):
    name = row["product_name"].casefold()
    if name == "motrax 2t":
        tsc = next(
            (
                match.group(1)
                for value in row["specifications_source_reported"]
                if (match := re.search(r"TSC-([123])", value, re.I))
            ),
            normalize(row["source_url"]),
        )
        return f"{name}|tsc-{tsc}"
    return name


def family_for(segments, name, subtitle):
    values = set(segments)
    text = f"{name} {subtitle}".casefold()
    if "Greases" in values or "grease" in text:
        return "G"
    if "Hydraulic Oils" in values or "Fork Oils" in values or "hydraulic" in text:
        return "H"
    if "Compressor Oils" in values or "compressor" in text or "vacuum pump" in text:
        return "C"
    if "Turbine Oils" in values or "turbine oil" in text:
        return "U"
    if "Gear Oils" in values or "gear oil" in text:
        return "T"
    if "Industrial Gear Oils" in values:
        return "I"
    if values & {
        "Passenger Car Engine Oils", "Truck Engine Oils",
        "Motorcycle Engine Oils", "Marine Oils", "Railway Engine Oils",
        "Racing Oils",
    } or "engine oil" in text or "motor oil" in text:
        return "M"
    if values & {"ATFs", "Fluids", "Agricultural Oils"} or "transmission fluid" in text:
        return "TF"
    if "AntiFreeze & Coolants" in values or "coolant" in text or "antifreeze" in text:
        return "TF"
    if values & {"Spray Cans", "Additives"}:
        return "S"
    return "I"


def split_standard_tokens(value, prefix):
    match = re.search(rf"\b{prefix}\s+(.+)", value, re.I)
    if not match:
        return []
    body = re.split(r"\s*[,;]\s*", match.group(1))[0]
    return [
        token.strip()
        for token in re.split(r"/", body)
        if token.strip()
    ]


def technical(name, family, viscosities, specifications):
    result = {
        "sae_engine": "",
        "sae_gear": "",
        "iso_vg": "",
        "nlgi": "",
        "source_grade": "",
        "api": [],
        "api_gl": [],
        "acea": [],
        "ilsac": [],
        "jaso": [],
        "dot": "",
        "coolant_class": "",
        "performance": list(specifications),
    }
    for grade in viscosities:
        if match := re.fullmatch(r"SAE\s+(.+)", grade, re.I):
            if family == "T":
                result["sae_gear"] = match.group(1).upper()
            else:
                result["sae_engine"] = match.group(1).upper()
        elif match := re.fullmatch(r"ISO\s+VG\s+(\d+)", grade, re.I):
            result["iso_vg"] = match.group(1)
        elif match := re.fullmatch(r"NLGI\s+(.+)", grade, re.I):
            result["nlgi"] = match.group(1)
    if not result["sae_engine"] and not result["sae_gear"]:
        if match := re.search(r"\b(\d{1,2}W-\d{2,3})\b", name, re.I):
            field = "sae_gear" if family == "T" else "sae_engine"
            result[field] = match.group(1).upper()
    if not result["iso_vg"] and family in {"C", "H", "I", "U"}:
        if match := re.search(r"\b(?:ISO(?:\s+VG)?[- ]?)?(\d{2,4})\b$", name, re.I):
            result["iso_vg"] = match.group(1)
    for value in specifications:
        if re.match(r"API\s+GL-", value, re.I):
            result["api_gl"].extend(
                re.findall(r"GL-[1-6](?:\s*\(LS\))?", value, re.I)
            )
        elif re.match(r"API\s+", value, re.I):
            result["api"].extend(re.findall(
                r"\b(?:SQ|SP|SN(?:\s+PLUS)?|SM|SL|SJ|SH|SG|SF|"
                r"CK-4|CJ-4|CI-4(?:\s+PLUS)?|CH-4|CG-4|CF-4|"
                r"CF-2|CF|CE|CD|CC|TC|TB|TA)\b",
                value,
                flags=re.I,
            ))
        if re.match(r"ACEA\s+", value, re.I):
            body = re.sub(r"^ACEA\s+", "", value, flags=re.I).strip()
            result["acea"].append(body)
        if re.match(r"ILSAC\s+", value, re.I):
            result["ilsac"].extend(split_standard_tokens(value, "ILSAC"))
        if re.match(r"JASO\s+", value, re.I):
            result["jaso"].extend(split_standard_tokens(value, "JASO"))
    for field in ("api", "api_gl", "acea", "ilsac", "jaso"):
        result[field] = sorted(set(result[field]))
    if "ready-to-use" in name.casefold():
        result["coolant_class"] = "Ready-to-use"
    elif "concentrat" in name.casefold():
        result["coolant_class"] = "Concentrate"
    return result


def main():
    cards = [
        json.loads(line)
        for line in CARD_INPUT.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assets = {
        row["url"]: row
        for line in ASSET_INPUT.read_text(encoding="utf-8").splitlines()
        if line
        for row in [json.loads(line)]
    }
    groups = defaultdict(list)
    for row in cards:
        groups[identity_key(row)].append(row)
    if len(groups) != EXPECTED_IDENTITIES:
        raise RuntimeError(f"Rymax identity denominator changed: {len(groups)}")

    output = []
    for key, rows in sorted(groups.items()):
        rows.sort(
            key=lambda row: (
                len(row["specifications_source_reported"])
                + len(row["segments"])
                + len(row["viscosity_grades"]),
                row["source_url"],
            ),
            reverse=True,
        )
        lead = rows[0]
        specs = sorted({
            value for row in rows for value in row["specifications_source_reported"]
        })
        segments = sorted({value for row in rows for value in row["segments"]})
        viscosities = sorted({value for row in rows for value in row["viscosity_grades"]})
        documents = sorted({value for row in rows for value in row["document_urls"]})
        images = sorted({row["product_image_url"] for row in rows if row["product_image_url"]})
        family = family_for(
            segments, lead["product_name"], lead["product_subtitle"]
        )
        source_record_id = (
            "RYMAX-BZ-"
            + hashlib.sha256(key.encode()).hexdigest()[:12].upper()
        )
        output.append({
            "source_record_id": source_record_id,
            "source_id": SOURCE_ID,
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Belize",
            "brand": "RYMAX",
            "product_name": lead["product_name"],
            "product_subtitle": lead["product_subtitle"],
            "family_code": family,
            "technical": technical(
                lead["product_name"], family, viscosities, specs
            ),
            "segments": segments,
            "source_card_urls": sorted(row["source_url"] for row in rows),
            "source_page_sha256": sorted({row["page_sha256"] for row in rows}),
            "source_image_urls": images,
            "source_image_sha256": sorted({
                assets[url]["sha256"] for url in images
            }),
            "document_urls": documents,
            "document_sha256": sorted({
                assets[url]["sha256"] for url in documents
            }),
            "description_factual_excerpt": lead["description_factual_excerpt"],
            "source_quality_flags": [
                "complete_current_manufacturer_country_catalog",
                "page_image_tds_sds_payload_sha256_audited",
                "source_reported_specifications_not_independent_approvals",
            ] + (
                ["duplicate_current_urls_merged_by_product_identity"]
                if len(rows) > 1 else []
            ),
        })

    normalized = "\n".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) for row in output
    ) + "\n"
    normalized_hash = hashlib.sha256(normalized.encode()).hexdigest()
    if normalized_hash != EXPECTED_OUTPUT_SHA256:
        raise RuntimeError(f"Rymax normalized product facts changed: {normalized_hash}")
    PRODUCT_OUT.write_text(normalized, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "source_cards": len(cards),
        "normalized_product_identities": len(output),
        "duplicate_url_occurrences_collapsed": len(cards) - len(output),
        "multi_url_identity_groups": sum(len(rows) > 1 for rows in groups.values()),
        "brands": dict(Counter(row["brand"] for row in output)),
        "families": dict(sorted(Counter(row["family_code"] for row in output).items())),
        "rows_with_sae": sum(
            bool(row["technical"]["sae_engine"] or row["technical"]["sae_gear"])
            for row in output
        ),
        "rows_with_iso_vg": sum(bool(row["technical"]["iso_vg"]) for row in output),
        "rows_with_nlgi": sum(bool(row["technical"]["nlgi"]) for row in output),
        "rows_with_api": sum(bool(row["technical"]["api"]) for row in output),
        "rows_with_api_gl": sum(bool(row["technical"]["api_gl"]) for row in output),
        "rows_with_acea": sum(bool(row["technical"]["acea"]) for row in output),
        "rows_with_jaso": sum(bool(row["technical"]["jaso"]) for row in output),
        "normalized_output_sha256": normalized_hash,
    }
    REPORT_OUT.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
