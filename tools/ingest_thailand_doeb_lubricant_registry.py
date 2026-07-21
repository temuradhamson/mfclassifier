#!/usr/bin/env python3
"""Normalize Thailand DOEB's public motor-lubricant registration snapshot."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "thailand-doeb-lubricant-products.jsonl"
REPORT = ROOT / "data" / "thailand-doeb-lubricant-products-report.json"
SOURCE_ID = "THAILAND_DOEB_LUBRICANT_REGISTRY"
RESOURCE_ID = "fe63ef44-c9fa-4987-b205-46d714d762ae"
SOURCE_DATASET_URL = "https://data.doeb.go.th/dataset/e8179a95-18f9-489f-b636-43407e8bb172"
MIRROR_DATASET_URL = "https://gdcatalognhic.nha.co.th/dataset/lubricant_data"
MIRROR_API_BASE = "https://gdcatalognhic.nha.co.th/api/3/action/datastore_search"
SNAPSHOT_DATE = "2026-07-21"
SOURCE_SNAPSHOT_MONTH = "2024-03"
USER_AGENT = "MFClassifier research catalog/1.0 (government classification research)"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_sae(value: object) -> str:
    result = clean(value).upper()
    result = re.sub(r"^SAE\s+", "", result)
    if re.fullmatch(r"(?:0|5|10|15|20|25)W\d{2,3}", result):
        result = result.replace("W", "W-")
    return result


def fetch() -> tuple[bytes, dict]:
    url = MIRROR_API_BASE + "?" + urllib.parse.urlencode({
        "resource_id": RESOURCE_ID,
        "limit": 10000,
    })
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    document = json.loads(payload)
    assert document["success"] is True
    return payload, document["result"]


def lifecycle(end_date: str) -> str:
    valid_through = date.fromisoformat(end_date[:10])
    return (
        "not_expired_by_published_end_date_as_of_catalog_snapshot"
        if valid_through >= date.fromisoformat(SNAPSHOT_DATE)
        else "expired_by_published_end_date"
    )


def main() -> None:
    payload, result = fetch()
    rows = result["records"]
    assert result["total"] == len(rows) == 6213
    required = {"_id", "COMPANY_NAME", "PRODUCT_NAME", "NEW_REGIST_NUMBER", "SAE", "END_DATE"}
    assert all(required <= set(row) for row in rows)
    assert all(clean(row["COMPANY_NAME"]) and clean(row["PRODUCT_NAME"]) for row in rows)
    assert all(clean(row["NEW_REGIST_NUMBER"]) and clean(row["END_DATE"]) for row in rows)

    occurrences = []
    registrations: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        standards = []
        technical = {"sae": [normalize_sae(row["SAE"])], "api": [], "acea": [], "jaso": [], "ilsac": [], "oem": [], "nmma": []}
        for index in range(1, 4):
            system = clean(row.get(f"STANDARD_{index}")).upper()
            value = clean(row.get(f"LEVEL_{index}"))
            if not system and not value:
                continue
            standards.append({"system": system or "SOURCE_UNSPECIFIED", "value": value})
            key = system.casefold()
            if key in technical and value:
                technical[key].append(value)
        for key in technical:
            technical[key] = sorted(set(technical[key]))

        registration_raw = clean(row["NEW_REGIST_NUMBER"])
        registration = re.sub(r"\s+", "", registration_raw).upper()
        source_row = int(row["_id"])
        end_date = clean(row["END_DATE"])[:10]
        occurrence = {
            "source_row": source_row,
            "registration_holder": clean(row["COMPANY_NAME"]),
            "product_name": clean(row["PRODUCT_NAME"]),
            "registration_number": registration,
            "registration_number_raw": registration_raw,
            "sae_source_raw": clean(row["SAE"]),
            "technical": technical,
            "standards": standards,
            "valid_through": end_date,
            "lifecycle_status": lifecycle(end_date),
        }
        occurrences.append(occurrence)
        registrations[registration].append(occurrence)

    collisions = {
        number: [f"TH-DOEB-2024M03-{row['source_row']:06d}" for row in collision_rows]
        for number, collision_rows in registrations.items()
        if len(collision_rows) > 1
    }
    identity_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in occurrences:
        identity_key = (
            row["registration_holder"].casefold(),
            row["product_name"].casefold(),
            row["technical"]["sae"][0],
            tuple(sorted((item["system"].casefold(), item["value"].casefold()) for item in row["standards"])),
        )
        identity_groups[identity_key].append(row)

    records = []
    for identity_key, identity_rows in identity_groups.items():
        identity_rows.sort(key=lambda row: row["source_row"])
        primary = identity_rows[0]
        identity_hash = hashlib.sha256(json.dumps(identity_key, ensure_ascii=False).encode()).hexdigest()[:20]
        registration_numbers = sorted({row["registration_number"] for row in identity_rows})
        source_quality_flags = []
        if primary["technical"]["sae"] == ["13W-30"]:
            source_quality_flags.append("nonstandard_sae_notation")
        if any(number in collisions for number in registration_numbers):
            source_quality_flags.append("registration_number_collision")
        valid_through = max(row["valid_through"] for row in identity_rows)
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"TH-DOEB-IDENTITY-{identity_hash}",
            "source_row": primary["source_row"],
            "source_rows": [row["source_row"] for row in identity_rows],
            "source_occurrences": [{
                "source_row": row["source_row"],
                "registration_number": row["registration_number"],
                "registration_number_raw": row["registration_number_raw"],
                "valid_through": row["valid_through"],
                "lifecycle_status": row["lifecycle_status"],
            } for row in identity_rows],
            "source_occurrence_count": len(identity_rows),
            "source_dataset_url": SOURCE_DATASET_URL,
            "source_mirror_url": MIRROR_DATASET_URL,
            "source_resource_id": RESOURCE_ID,
            "source_snapshot_month": SOURCE_SNAPSHOT_MONTH,
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Thailand",
            "registration_holder": primary["registration_holder"],
            "product_name": primary["product_name"],
            "registration_numbers": registration_numbers,
            "registration_number_raw_values": sorted({row["registration_number_raw"] for row in identity_rows}),
            "family_code": "M",
            "classification_basis": "doeb_engine_lubricant_registration_dataset",
            "sae_source_raw_values": sorted({row["sae_source_raw"] for row in identity_rows}),
            "technical": primary["technical"],
            "standards": sorted(primary["standards"], key=lambda item: (item["system"], item["value"])),
            "valid_through": valid_through,
            "lifecycle_status": lifecycle(valid_through),
            "lifecycle_basis": (
                "computed from the latest published end date among merged registration occurrences "
                "against the catalog snapshot; the source is a March 2024 full registry snapshot, "
                "not live status confirmation"
            ),
            "source_quality_flags": source_quality_flags,
        })

    records.sort(key=lambda row: (row["source_row"], row["source_record_id"]))
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "official_public_government_registry_snapshot_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_snapshot_month": SOURCE_SNAPSHOT_MONTH,
        "source_id": SOURCE_ID,
        "source_dataset_url": SOURCE_DATASET_URL,
        "source_mirror_url": MIRROR_DATASET_URL,
        "source_resource_id": RESOURCE_ID,
        "source_api_response_sha256": hashlib.sha256(payload).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "published_source_rows": len(occurrences),
        "normalized_products": len(records),
        "duplicate_registration_occurrences_merged": len(occurrences) - len(records),
        "unique_registration_numbers": len(registrations),
        "registration_number_collision_groups": len(collisions),
        "registration_number_collision_source_rows": sum(len(rows) for rows in collisions.values()),
        "registration_number_collision_products": sum("registration_number_collision" in row["source_quality_flags"] for row in records),
        "registration_number_collision_details": collisions,
        "registration_holders": len({row["registration_holder"] for row in records}),
        "product_names": len({row["product_name"] for row in records}),
        "sae_values": dict(sorted(Counter(row["technical"]["sae"][0] for row in records).items())),
        "standards": dict(sorted(Counter(item["system"] for row in occurrences for item in row["standards"]).items())),
        "lifecycle_assessments": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "families": {"M": len(records)},
        "source_quality_flags": dict(sorted(Counter(flag for row in records for flag in row["source_quality_flags"]).items())),
        "rights_note": (
            "The Thai government catalog classifies the dataset as public and licenses it under "
            "Open Data Common. Only normalized factual registration fields are republished with attribution."
        ),
        "grain_note": (
            "Published registration occurrences are consolidated only when holder, normalized product name, "
            "SAE and the complete professional-standard set are identical. All registration numbers and source "
            "rows remain attached. Three numbers collide across conflicting identities and remain separate."
        ),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
