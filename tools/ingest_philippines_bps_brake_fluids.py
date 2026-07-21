#!/usr/bin/env python3
"""Normalize Philippine BPS PS/ICC motor-vehicle brake-fluid evidence.

The official Bureau of Philippine Standards page links two live public Google
Sheets: PS licensees and ICC certificate holders.  This loader retains only the
exact Motor Vehicle Brake Fluid scope, separates DOT grades from packaging,
merges repeated ICC sticker ranges, and preserves source-data inconsistencies.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "philippines-bps-brake-fluid-products.jsonl"
REPORT = ROOT / "data" / "philippines-bps-brake-fluid-products-report.json"
LANDING_URL = "https://bps.dti.gov.ph/product-certification/certified-products"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-data)"

SHEETS = {
    "PHILIPPINES_BPS_PS_BRAKE_FLUID_LICENCES": {
        "sheet_id": "1DSg7CcAPt6c35s4YVj1gF3fpG8nGrwpG",
        "gid": "1052759647",
        "source_snapshot_date": "2026-05-31",
        "scheme": "PS",
    },
    "PHILIPPINES_BPS_ICC_BRAKE_FLUID_CERTIFICATES": {
        "sheet_id": "1QSy99bJgQi9TERnk2S_6ZZroPF2-ktfO",
        "gid": "980728304",
        "source_snapshot_date": "2026-04-30",
        "scheme": "ICC",
    },
}

# The PS sheet mixes brand lists with grade-to-brand mappings.  Manual mappings
# are deliberate and audited: they prevent a loose comma parser from assigning
# every listed brand to every grade when the source says otherwise.
PS_GRADE_LABELS = {
    "Q-6441": {
        "DOT 3": ["PLATINUM", "COMET", "CENTRUM", "GT OIL", "NOVA PRIME", "Q-MI", "ROTELOS", "RUSI", "SILVESTRE", "SYM", "ATLAS", "KEVLON LUBRICANTS", "REV-1", "NIMIHITSU", "WÜRTH", "LEVITRONN", "BAGANI LUMAWIG"],
        "DOT 4": ["PLATINUM", "CENTRUM FUEL", "GT OIL", "NOVA PRIME", "Q-MI", "ROTELOS", "RUSI", "SILVESTRE", "SYM", "ATLAS", "KEVLON LUBRICANTS", "REV-1", "NIMIHITSU", "WÜRTH", "LEVITRONN", "BAGANI LUMAWIG"],
    },
    "Q-1647": {"DOT 3": ["USA 88", "FILOIL"]},
    "Q-2099": {
        "DOT 3": ["FUSION", "PETROMATE", "PETRON", "UNIOIL BRAKE & CLUTCH FLUID", "TOTAL HBF 3", "MOTOTEK", "PLATINUM", "CENTRUM", "COMET", "REV-1", "YAMALUBE"],
        "DOT 4": ["PETRON"],
    },
    "Q-0608": {"DOT 3": ["PRESTONE"]},
    "Q-2251": {"DOT 3": ["LANDEX", "SHELL"], "DOT 4": ["LANDEX", "SHELL"]},
    "Q-0288": {"DOT 3": ["SURE BRAKE"], "DOT 4": ["SURE BRAKE"]},
    # Source conflict: Brand Name says PETROMATE while Model/Type says PETRON.
    # Keep one visibly conflicted label instead of silently choosing either.
    "Q-1011": {
        "DOT 3": ["PETROMATE / PETRON (SOURCE CONFLICT)", "SEAOIL", "BENDIX", "ROTELOS"],
        "DOT 4": ["SEAOIL", "BENDIX", "ROTELOS", "TROFEO"],
    },
    "Q-4799": {"DOT 3": ["PETRON"], "DOT 4": ["PETRON"]},
    "Q-2509": {
        "DOT 3": ["PISCC BRAKE FLUID", "TOYOTA BRAKE FLUID", "MAZDA BRAKE FLUID", "MOTORCRAFT BRAKE FLUID", "SUZUKI GENUINE BRAKE FLUID", "HONDA BRAKE FLUID"],
        "DOT 4": ["MITSUBISHI MOTORS GENUINE BRAKE FLUID", "GEELY GENUINE BRAKE FLUID", "PISCC BRAKE FLUID"],
    },
    "Q-0607": {"DOT 3": ["NATIONAL", "OMEGA"], "DOT 4": ["NATIONAL"]},
    "Q-2356": {
        "DOT 3": ["OPTIMAX", "PHOENIX", "PLATINUM", "AKRON", "PETRON"],
        "DOT 4": ["OPTIMAX", "PHOENIX", "PLATINUM", "HFT", "PETRON"],
    },
    "Q-5171": {"DOT 3": ["VOLGA"], "DOT 4": ["VOLGA"]},
    "Q-7061": {"DOT 4": ["TEEC"]},
}


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" \t\r\n,;.")


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def source_url(config: dict) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{config['sheet_id']}/gviz/tq"
        f"?tqx=out:csv&gid={config['gid']}"
    )


def fetch(config: dict) -> bytes:
    request = urllib.request.Request(source_url(config), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError("BPS sheet returned an empty response")
    return payload


def read_csv(payload: bytes) -> list[list[str]]:
    csv.field_size_limit(sys.maxsize)
    return list(csv.reader(io.StringIO(payload.decode("utf-8-sig"))))


def is_brake_fluid(value: str) -> bool:
    return normalize(value) in {"motor vehicle brake fluid", "motor vehichle brake fluid"}


def dot_grades(*values: str) -> list[str]:
    text = " ".join(values).upper().replace("D0T", "DOT")
    return sorted({f"DOT {value}" for value in re.findall(r"\bDOT\s*([3456])\b", text)})


def canonical_holder(value: str) -> str:
    key = normalize(value)
    aliases = {
        "clorox int phil inc": "Clorox International Philippines, Inc.",
        "clorox international phil inc": "Clorox International Philippines, Inc.",
        "clorox international philippines inc": "Clorox International Philippines, Inc.",
        "smc asia car distributors corp": "SMC Asia Car Distributors Corp.",
        "total philippines corp": "Total (Philippines) Corporation",
        "total philippines corporation": "Total (Philippines) Corporation",
        "wuerth philippines inc": "Würth Philippines Inc.",
    }
    return aliases.get(key, clean(value))


def canonical_label(value: str) -> str:
    key = normalize(value)
    aliases = {
        "wuerth": "Würth",
        "wurth": "Würth",
        "bmw brake fluid": "BMW",
        "bmw": "BMW",
        "mercedes benz": "Mercedes-Benz",
        "acdelco": "ACDelco",
        "bosch": "Bosch",
        "prestone": "Prestone",
        "hbf 3": "HBF 3",
    }
    return aliases.get(key, clean(value))


def product_name(label: str, brake_class: str) -> str:
    suffix = brake_class if brake_class != "GRADE NOT REPORTED" else "grade not reported"
    if "brake" in normalize(label):
        return clean(f"{label} {suffix}")
    return clean(f"{label} Brake Fluid {suffix}")


def record_hash(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def ps_records(rows: list[list[str]], config: dict) -> tuple[list[dict], dict]:
    if not rows or "List of PS Licensee as of 31 May 2026" not in rows[0][0]:
        raise RuntimeError("BPS PS sheet title/date changed")
    relevant = {clean(row[0]): row for row in rows[1:] if len(row) >= 10 and is_brake_fluid(row[4])}
    if set(relevant) != set(PS_GRADE_LABELS):
        raise RuntimeError(f"BPS PS brake-fluid licence set changed: {sorted(relevant)}")
    records = []
    for licence, grade_labels in PS_GRADE_LABELS.items():
        row = relevant[licence]
        for grade, labels in grade_labels.items():
            for label in labels:
                flags = []
                if "SOURCE CONFLICT" in label:
                    flags.append("source_brand_name_and_model_type_fields_conflict")
                facts = {
                    "licence_number": licence,
                    "company": clean(row[1]),
                    "product": clean(row[4]),
                    "brand_name_field": clean(row[5]),
                    "model_type_field": clean(row[6]),
                    "product_standard": clean(row[9]),
                    "mapped_product_label": label,
                    "mapped_grade": grade,
                }
                source_record_id = f"BPS-PS-{licence}-{record_hash({'label': label, 'grade': grade})[:12].upper()}"
                records.append({
                    "source_id": "PHILIPPINES_BPS_PS_BRAKE_FLUID_LICENCES",
                    "source_record_id": source_record_id,
                    "source_url": source_url(config),
                    "source_landing_url": LANDING_URL,
                    "source_snapshot_date": config["source_snapshot_date"],
                    "dataset_snapshot_date": SNAPSHOT_DATE,
                    "market": "Philippines",
                    "scheme": "PS",
                    "manufacturer_or_certificate_holder": canonical_holder(row[1]),
                    "manufacturer_or_certificate_holder_source_reported": clean(row[1]),
                    "brand": label.replace(" (SOURCE CONFLICT)", ""),
                    "brand_basis": "source_reported_certified_brand_or_product_label",
                    "product_name": product_name(label.replace(" (SOURCE CONFLICT)", ""), grade),
                    "family_code": "TF",
                    "technical": {"brake_fluid_class": [grade], "certified_standard": [clean(row[9])]},
                    "licence_number": licence,
                    "certificate_entries": [{"number": licence, "scheme": "PS"}],
                    "source_brand_name_field": clean(row[5]),
                    "source_model_type_field": clean(row[6]),
                    "source_product_field": clean(row[4]),
                    "source_quality_flags": flags,
                    "source_facts_sha256": record_hash(facts),
                    "evidence_status": "official_government_product_certification_brand_grade_scope",
                    "lifecycle_status": "listed_in_current_ps_licensee_snapshot",
                })
    return records, {"source_rows": len(rows) - 1, "relevant_source_rows": len(relevant)}


def icc_records(rows: list[list[str]], config: dict) -> tuple[list[dict], dict]:
    if not rows or "List of ICC Certificate Holders as of 30 April 2026" not in rows[0][0]:
        raise RuntimeError("BPS ICC sheet title/date changed")
    relevant = [row for row in rows[1:] if len(row) >= 9 and is_brake_fluid(row[1])]
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    false_positive_rows = sum(
        "brake fluid" in normalize(" ".join(row)) and not is_brake_fluid(row[1])
        for row in rows[1:] if len(row) >= 9
    )
    for index, row in enumerate(relevant, 2):
        holder = canonical_holder(row[0])
        label = canonical_label(row[3])
        grades = dot_grades(row[3], row[4], row[5])
        source_text = " ".join([row[4], row[5]]).upper()
        if not grades and "ENV6" in source_text:
            grades = ["ENV6"]
        if not grades:
            grades = ["GRADE NOT REPORTED"]
        flags = []
        if grades == ["GRADE NOT REPORTED"]:
            flags.append("brake_fluid_class_not_reported")
        if grades == ["ENV6"]:
            flags.append("source_reports_env6_without_dot_class")
        if normalize(row[1]) == "motor vehichle brake fluid":
            flags.append("source_product_category_typo_retained")
        if "239" not in clean(row[2]):
            flags.append("source_standard_inconsistent_with_brake_fluid_category")
        if re.search(r"\b(?:1000|1100)-20", source_text):
            flags.append("source_type_appears_to_contain_tyre_size")
        for grade in grades:
            groups[(normalize(holder), normalize(label), grade)].append({
                "source_row": index,
                "holder_source_reported": clean(row[0]),
                "product_source_reported": clean(row[1]),
                "standard_source_reported": clean(row[2]),
                "brand_source_reported": clean(row[3]),
                "type_source_reported": clean(row[4]),
                "model_source_reported": clean(row[5]),
                "certificate_number": clean(row[6]),
                "icc_sticker_serial_start": clean(row[7]),
                "icc_sticker_serial_end": clean(row[8]),
                "flags": flags,
                "holder": holder,
                "label": label,
                "grade": grade,
            })

    records = []
    for (_, _, grade), occurrences in sorted(groups.items()):
        first = occurrences[0]
        certificates = []
        seen = set()
        for occurrence in occurrences:
            identity = (
                occurrence["certificate_number"],
                occurrence["icc_sticker_serial_start"],
                occurrence["icc_sticker_serial_end"],
            )
            if identity in seen:
                continue
            seen.add(identity)
            certificates.append({
                "number": occurrence["certificate_number"],
                "scheme": "ICC",
                "sticker_serial_start": occurrence["icc_sticker_serial_start"],
                "sticker_serial_end": occurrence["icc_sticker_serial_end"],
            })
        standards = sorted({o["standard_source_reported"] for o in occurrences if o["standard_source_reported"]})
        flags = sorted({flag for occurrence in occurrences for flag in occurrence["flags"]})
        facts = {
            "holder": first["holder"],
            "label": first["label"],
            "grade": grade,
            "occurrences": [{key: value for key, value in row.items() if key not in {"holder", "label", "grade"}} for row in occurrences],
        }
        source_record_id = f"BPS-ICC-{record_hash({'holder': first['holder'], 'label': first['label'], 'grade': grade})[:16].upper()}"
        records.append({
            "source_id": "PHILIPPINES_BPS_ICC_BRAKE_FLUID_CERTIFICATES",
            "source_record_id": source_record_id,
            "source_url": source_url(config),
            "source_landing_url": LANDING_URL,
            "source_snapshot_date": config["source_snapshot_date"],
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "market": "Philippines",
            "scheme": "ICC",
            "manufacturer_or_certificate_holder": first["holder"],
            "manufacturer_or_certificate_holder_source_reported": sorted({o["holder_source_reported"] for o in occurrences}),
            "brand": first["label"],
            "brand_basis": "source_reported_certified_brand_or_product_label",
            "product_name": product_name(first["label"], grade),
            "family_code": "TF",
            "technical": {
                "brake_fluid_class": [] if grade == "GRADE NOT REPORTED" else [grade],
                "certified_standard_source_reported": standards,
            },
            "certificate_entries": certificates,
            "source_occurrence_count": len(occurrences),
            "source_occurrences": [{key: value for key, value in row.items() if key not in {"holder", "label", "grade", "flags"}} for row in occurrences],
            "source_quality_flags": flags,
            "source_facts_sha256": record_hash(facts),
            "evidence_status": "official_government_import_certificate_product_evidence",
            "lifecycle_status": "listed_in_icc_certificate_holder_snapshot_status_not_individually_verified",
        })
    return records, {
        "source_rows": len(rows) - 1,
        "relevant_source_rows": len(relevant),
        "false_positive_rows_excluded": false_positive_rows,
        "expanded_grade_occurrences": sum(row["source_occurrence_count"] for row in records),
    }


def main() -> None:
    all_records = []
    source_reports = {}
    raw_sha = {}
    for source_id, config in SHEETS.items():
        payload = fetch(config)
        raw_sha[source_id] = hashlib.sha256(payload).hexdigest()
        rows = read_csv(payload)
        if config["scheme"] == "PS":
            records, source_report = ps_records(rows, config)
        else:
            records, source_report = icc_records(rows, config)
        all_records.extend(records)
        source_reports[source_id] = {**source_report, "normalized_rows": len(records)}

    all_records.sort(key=lambda row: (row["source_id"], row["source_record_id"]))
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_philippines_bps_brake_fluid_certification_evidence_normalized",
        "source_landing_url": LANDING_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "source_sheet_urls": {source_id: source_url(config) for source_id, config in SHEETS.items()},
        "source_snapshot_dates": {source_id: config["source_snapshot_date"] for source_id, config in SHEETS.items()},
        "source_csv_sha256": raw_sha,
        "source_reports": source_reports,
        "normalized_products_or_brand_grade_scopes": len(all_records),
        "rows_by_source": dict(sorted(Counter(row["source_id"] for row in all_records).items())),
        "brake_fluid_classes": dict(sorted(Counter(value for row in all_records for value in row["technical"]["brake_fluid_class"]).items())),
        "source_quality_flags": dict(sorted(Counter(flag for row in all_records for flag in row["source_quality_flags"]).items())),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "PS rows are licence + source-reported brand/product label + DOT grade scopes. ICC rows are certificate-holder + source-reported brand/product label + brake-fluid class identities with repeated sticker ranges merged.",
        "market_note": "Neither PS nor ICC certification evidence is treated as a current commercial offer or price observation.",
        "privacy_note": "Region, addresses, contacts and personal data are excluded. ICC sticker serial ranges are retained as non-personal certificate evidence.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
