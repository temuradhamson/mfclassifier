#!/usr/bin/env python3
"""Build the normalized, provenance-aware seed for the worldwide product catalog."""

from __future__ import annotations

import hashlib
import gzip
import json
import re
import shutil
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog-v3.json"
POLICY = ROOT / "data" / "global-source-policy.json"
JSONL_OUT = ROOT / "data" / "world-catalog-products.jsonl"
JSONL_GZ_OUT = ROOT / "data" / "world-catalog-products.jsonl.gz"
REPORT_OUT = ROOT / "data" / "world-catalog-report.json"
SQLITE_OUT = ROOT / "data" / "world-catalog.sqlite3"
SQLITE_GZ_OUT = ROOT / "data" / "world-catalog.sqlite3.gz"
XLSX_OUT = ROOT / "deliverables" / "World_lubricants_catalog_seed.xlsx"
AICHILON_DB = Path("/workspace/chilon/aichilon/var/chilon_seed.sqlite")
JASO_JSONL = ROOT / "data" / "jaso-filed-oils.jsonl"
LICENSED_JSONL = ROOT / "data" / "official-licensed-products.jsonl"
USDA_BIOPREFERRED_JSONL = ROOT / "data" / "usda-biopreferred-products.jsonl"
ZF_TE_ML_JSONL = ROOT / "data" / "zf-te-ml-approved-products.jsonl"
ALLISON_JSONL = ROOT / "data" / "allison-approved-fluids.jsonl"
DRIVENTIC_DIWA_JSONL = ROOT / "data" / "driventic-diwa-approved-oils.jsonl"
MERCEDES_DTFR_JSONL = ROOT / "data" / "mercedes-dtfr-approved-fluids.jsonl"
MERCEDES_BEVO_JSONL = ROOT / "data" / "mercedes-bevo-approved-fluids.jsonl"
VOLVO_GENUINE_JSONL = ROOT / "data" / "volvo-genuine-fluids.jsonl"
MAN_SERVICE_JSONL = ROOT / "data" / "man-service-products.jsonl"
LIQUI_MOLY_2020_JSONL = ROOT / "data" / "liqui-moly-2020-products.jsonl"
LIQUI_MOLY_CURRENT_JSONL = ROOT / "data" / "liqui-moly-current-products.jsonl"
ANP_BRAZIL_JSONL = ROOT / "data" / "anp-brazil-lubricant-products.jsonl"
INDONESIA_NPT_JSONL = ROOT / "data" / "indonesia-npt-lubricant-products.jsonl"
DLA_QPD_JSONL = ROOT / "data" / "dla-qpd-lubricant-products.jsonl"
BLUE_ANGEL_JSONL = ROOT / "data" / "blue-angel-de-uz-178-products.jsonl"
FUCHS_INDIA_JSONL = ROOT / "data" / "fuchs-india-products.jsonl"
FUCHS_US_JSONL = ROOT / "data" / "fuchs-us-products.jsonl"
FUCHS_GERMANY_JSONL = ROOT / "data" / "fuchs-germany-products.jsonl"
FUCHS_POLAND_JSONL = ROOT / "data" / "fuchs-poland-products.jsonl"
FUCHS_ITALY_JSONL = ROOT / "data" / "fuchs-italy-products.jsonl"
FUCHS_SWEDEN_JSONL = ROOT / "data" / "fuchs-sweden-products.jsonl"
FUCHS_SPAIN_JSONL = ROOT / "data" / "fuchs-spain-products.jsonl"
FUCHS_FRANCE_JSONL = ROOT / "data" / "fuchs-france-products.jsonl"
FUCHS_TURKEY_JSONL = ROOT / "data" / "fuchs-turkey-products.jsonl"
FUCHS_CANADA_JSONL = ROOT / "data" / "fuchs-canada-products.jsonl"
FUCHS_CHINA_JSONL = ROOT / "data" / "fuchs-china-products.jsonl"
FUCHS_CZECH_JSONL = ROOT / "data" / "fuchs-czech-products.jsonl"
FUCHS_MEXICO_JSONL = ROOT / "data" / "fuchs-mexico-products.jsonl"
FUCHS_SOUTH_AFRICA_JSONL = ROOT / "data" / "fuchs-south-africa-products.jsonl"
SCHEMA_VERSION = 1
SNAPSHOT_DATE = "2026-07-21"

FAMILY_NAMES = {
    "M": "Моторные масла",
    "T": "Трансмиссионные масла",
    "H": "Гидравлические масла",
    "I": "Индустриальные масла",
    "C": "Компрессорные масла",
    "U": "Турбинные масла",
    "E": "Электроизоляционные масла",
    "G": "Пластичные смазки",
    "TF": "Охлаждающие и технические жидкости",
    "S": "Специальные продукты",
}

EXPECTED_ENKT_BASE = {
    "M": "19.20.29.110",
    "T": "19.20.29.120",
    "H": "19.20.29.130",
    "I": "19.20.29.140",
    "C": "19.20.29.150",
    "U": "19.20.29.160",
    "E": "19.20.29.172",
    "G": "19.20.29.210",
}


def text(value) -> str:
    return str(value or "").strip()


def normalize(value) -> str:
    value = unicodedata.normalize("NFKC", text(value)).casefold().replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я]+", " ", value).strip()


def source_for(row: dict) -> str:
    source = text(row.get("source"))
    if source == "products_classified_2026":
        return "user-supplied-chilon-2026"
    if source == "legacy_mfclassifier":
        return "legacy-mfclassifier"
    if source == "aichilon_internal":
        return "aichilon-internal"
    if source.startswith("JASO_"):
        return source
    if "+" in source:
        return "user-supplied-chilon-2026"
    return "legacy-mfclassifier"


def extract_sae(row: dict) -> tuple[str, str]:
    raw = " ".join([text(row.get("sae_class")), text(row.get("name"))]).upper()
    engine = re.search(r"(?<![0-9])((?:0|5|10|15|20|25)W)[-\s]?([0-9]{2})(?![0-9])", raw)
    if engine:
        return f"{engine.group(1)}-{engine.group(2)}", ""
    gear = re.search(r"(?<![0-9])(70W|75W|80W|85W)(?:[-\s]?([0-9]{2,3}))?(?![0-9])", raw)
    if gear:
        return "", gear.group(1) + (f"-{gear.group(2)}" if gear.group(2) else "")
    mono = re.fullmatch(r"(?:SAE\s*)?([0-9]{2,3})", text(row.get("sae_class")).upper())
    if mono:
        return (f"SAE {mono.group(1)}", "") if row.get("category_code") == "M" else ("", f"SAE {mono.group(1)}")
    return "", ""


def extract_performance(row: dict) -> dict:
    raw = " ".join([text(row.get("api_class")), text(row.get("technical_document"))]).upper()
    api_patterns = [
        r"\bAPI\s+(SP|SN\s+PLUS|SN|SM|SL|SJ|SH|SG|CK-4|CJ-4|CI-4\s+PLUS|CI-4|CH-4|CG-4|CF-4|CF|FA-4)(?:\s*[/,]\s*(CF|SN|SM|SL|SJ))?",
        r"\b(GL-[1-6])\b",
    ]
    api = []
    api_gl = []
    for index, pattern in enumerate(api_patterns):
        for match in re.finditer(pattern, raw):
            values = [v.replace("  ", " ") for v in match.groups() if v]
            (api_gl if index else api).extend(values)
    acea = []
    for match in re.finditer(r"\b(?:ACEA\s*)?([ACE][0-9](?:/[BCE][0-9])?(?:-[0-9]{2})?|A[0-9]/B[0-9])\b", raw):
        acea.append(match.group(1))
    ilsac = []
    for match in re.finditer(r"\b(?:ILSAC\s*)?(GF-[1-7])\b", raw):
        ilsac.append(match.group(1))
    return {
        "api": sorted(set(api)),
        "api_gl": sorted(set(api_gl)),
        "acea": sorted(set(acea)),
        "ilsac": sorted(set(ilsac)),
        "performance_raw": text(row.get("api_class")) or text(row.get("technical_document")),
    }


def canonical_record(row: dict) -> dict:
    sae_engine, sae_gear = extract_sae(row)
    performance = extract_performance(row)
    family_code = text(row.get("category_code"))
    iso_vg = ""
    if family_code in {"H", "I", "C", "U", "E"} and row.get("viscosity") not in (None, ""):
        iso_vg = text(row.get("viscosity"))
    nlgi = text(row.get("grease_class"))
    if family_code == "G" and not nlgi:
        match = re.search(r"\bNLGI\s*(00|0|[1-6])\b|\bEP\s*(00|0|[1-6])\b", text(row.get("name")), re.I)
        if match:
            nlgi = next(value for value in match.groups() if value is not None)
    class_match = row.get("class_match") or {}
    source_id = source_for(row)
    source_record_id = text(row.get("legacy_id") or row.get("source_number") or row.get("id"))
    specs = {
        **performance,
        "sae_engine": sae_engine,
        "sae_gear": sae_gear,
        "iso_vg": iso_vg,
        "din_gost_class": text(row.get("din_gost_class")),
        "gost_name": text(row.get("gost_name")),
        "coolant_class": text(row.get("coolant_class")),
        "grease_class": text(row.get("grease_class")),
        "nlgi": nlgi,
    }
    signature_parts = [
        normalize(row.get("brand")), normalize(row.get("name")), normalize(sae_engine),
        normalize(sae_gear), normalize(iso_vg), normalize("|".join(performance["api"])),
        normalize("|".join(performance["api_gl"])), normalize("|".join(performance["acea"])),
        normalize("|".join(performance["ilsac"])), normalize(row.get("din_gost_class")),
        normalize(row.get("coolant_class")), normalize(row.get("grease_class")),
        normalize(nlgi),
    ]
    canonical_key = "|".join(signature_parts)
    canonical_hash = hashlib.sha256(canonical_key.encode()).hexdigest()[:20]
    record = {
        "product_id": f"WC-{canonical_hash}",
        "canonical_key": canonical_key,
        "manufacturer": text(row.get("brand")),
        "brand": text(row.get("brand")),
        "product_name_raw": text(row.get("name")),
        "product_name_normalized": normalize(row.get("name")),
        "market": "UZ",
        "family_code": family_code,
        "family": FAMILY_NAMES.get(family_code, text(row.get("family"))),
        "category": text(row.get("category")),
        "specifications": specs,
        "candidate_technical_profile_id": text(class_match.get("class_id")),
        "profile_match_confidence": class_match.get("confidence"),
        "profile_match_status": text(class_match.get("status")),
        "profile_match_basis": class_match.get("basis") or [],
        "source_id": source_id,
        "source_record_id": source_record_id,
        "source_row": row.get("source_row"),
        "evidence_status": (
            "project_source_row" if source_id == "user-supplied-chilon-2026"
            else "internal_product_master" if source_id == "aichilon-internal"
            else "legacy_needs_official_tds"
        ),
        "lifecycle_status": "active_or_unknown",
        "certificate_status": text(row.get("certificate_status")),
        "codes": {
            k: {
                "value": text(row.get(k)),
                "source_id": (
                    "legacy-mfclassifier" if k in {"ikpu", "enkt", "skp"}
                    else source_id
                ),
                "status": "source_reported_unverified",
            }
            for k in ["tnved_code", "ikpu", "enkt", "skp"] if text(row.get(k))
        },
        "certificate": {
            "number": text(row.get("certificate_number")),
            "issued_at": text(row.get("certificate_issued_at")),
            "expires_at": text(row.get("certificate_expires_at")),
            "local_producer_certificate": text(row.get("local_producer_certificate")),
            "technical_document": text(row.get("technical_document")),
        },
        "snapshot_date": SNAPSHOT_DATE,
    }
    return record


def aichilon_family(category: str, name: str) -> str:
    value = normalize(name)
    if "смазк" in value or "grease" in value:
        return "G"
    if any(token in value for token in ["сож", "антифриз", "coolant", "тормозн", "теплоносител"]):
        return "TF"
    if any(token in value for token in ["трансмис", "редуктор", "gear", " atf "]):
        return "T"
    if "гидрав" in value:
        return "H"
    if "компресс" in value:
        return "C"
    if "турбин" in value:
        return "U"
    if "трансформ" in value or "электроизоля" in value:
        return "E"
    if "мотор" in value or re.search(r"\b(?:0|5|10|15|20|25)w[ -]?[0-9]{2}\b", value):
        return "M"
    if normalize(category) == "масла":
        return "I"
    return "S"


def aichilon_seed() -> tuple[list[dict], list[dict], list[dict]]:
    db = sqlite3.connect(f"file:{AICHILON_DB}?mode=ro", uri=True)
    products = []
    exclusions = []
    for product_id, brand, category, name, is_active, archive_type, archive_reason in db.execute("""
        SELECT p.id, b.code, p.category, p.name, p.is_active, p.archive_type, p.archive_reason
        FROM products p JOIN brands b ON b.id=p.brand_id ORDER BY p.id
    """):
        if normalize(name) in {"в литрах", "мой тестовый товар"}:
            exclusions.append({"source_record_id": product_id, "name": name, "reason": "non_product_service_or_test_row"})
            continue
        family_code = aichilon_family(category or "", name)
        viscosity = ""
        match = re.search(r"\b(?:ISO\s*)?VG\s*([0-9]{1,4})\b", name, re.I)
        if not match and family_code in {"H", "I", "C", "U"}:
            match = re.search(r"\b([0-9]{1,4})\s*$", name)
        if match:
            viscosity = match.group(1)
        api_match = re.search(r"\bAPI\s+(.+)$", name, re.I)
        products.append({
            "id": f"AICHILON-{product_id}",
            "source_number": product_id,
            "source_row": None,
            "brand": brand,
            "name": name,
            "category": category or FAMILY_NAMES.get(family_code, ""),
            "category_code": family_code,
            "family": FAMILY_NAMES.get(family_code, ""),
            "viscosity": viscosity,
            "api_class": api_match.group(1) if api_match else "",
            "source": "aichilon_internal",
            "is_active": bool(is_active),
            "archive_type": archive_type,
            "archive_reason": archive_reason,
        })
    packages = [dict(zip(
        ["package_id", "source_product_id", "package_name", "unit", "quantity_per_package", "is_active", "weight_kg", "density_kg_per_l", "archive_type", "archive_reason"], row
    )) for row in db.execute("""
        SELECT id, product_id, package_name, unit, quantity_per_package, is_active,
               weight_kg, density_kg_per_l, archive_type, archive_reason
        FROM product_packages ORDER BY id
    """)]
    db.close()
    return products, packages, exclusions


def jaso_record(row: dict) -> dict:
    generic = {
        "id": f"{row['source_id']}-{row['source_row_number']}",
        "source_number": row["source_row_number"],
        "brand": row["submitter"],
        "name": row["product_name"],
        "category": {
            "JASO_4T": "Моторные масла для четырёхтактных мотоциклов",
            "JASO_DEO": "Дизельные моторные масла",
            "JASO_2T": "Масла для двухтактных двигателей",
        }[row["source_id"]],
        "category_code": "M",
        "family": "Моторные масла",
        "sae_class": row.get("sae_viscosity", ""),
        "source": row["source_id"],
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["submitter"]
    record["brand"] = row["submitter"]
    record["market"] = "GLOBAL_JASO_FILED"
    record["evidence_status"] = "official_filed_registry"
    record["lifecycle_status"] = "filed_as_of_list_date"
    record["snapshot_date"] = row["list_date"]
    record["specifications"]["jaso"] = row["jaso_classification"].split(",")
    record["specifications"]["jaso_family_detail"] = row["family_detail"]
    record["canonical_key"] += f"|jaso_oil_code:{normalize(row['oil_code'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    record["codes"]["jaso_oil_code"] = {
        "value": row["oil_code"],
        "source_id": row["source_id"],
        "status": "official_filed_registry",
    }
    return record


def licensed_record(row: dict) -> dict:
    generic = {
        "id": f"{row['source_id']}-{row['source_record_id']}",
        "source_number": row["source_record_id"],
        "brand": row["manufacturer"],
        "name": row["product_name"],
        "category": row["category"],
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": row.get("viscosity", ""),
        "source": row["source_id"],
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["manufacturer"]
    record["brand"] = row["manufacturer"]
    record["market"] = "EU_ECOLABEL" if row["source_id"] == "EU_ECOLABEL_LUBRICANTS" else "GLOBAL_OFFICIAL_LICENSED"
    record["source_id"] = row["source_id"]
    record["source_record_id"] = row["source_record_id"]
    record["source_row"] = row["source_row_number"]
    record["evidence_status"] = "official_licensed_registry"
    record["lifecycle_status"] = "listed_as_of_snapshot"
    record["snapshot_date"] = row["snapshot_date"]
    record["specifications"]["licensed_standard"] = row["specification"]
    record["specifications"]["certification_tags"] = row.get("certification_tags", [])
    if row.get("available_in"):
        record["specifications"]["available_in"] = row["available_in"]
    record["canonical_key"] += f"|official_registry:{normalize(row['source_id'])}:{normalize(row['source_record_id'])}:{normalize(row['product_name'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    if row.get("license_number"):
        system = (
            "GM_DEXOS_LICENSE" if row["source_id"].startswith("GM_")
            else "EU_ECOLABEL_LICENSE" if row["source_id"] == "EU_ECOLABEL_LUBRICANTS"
            else "NMMA_REGISTRATION"
        )
        record["codes"][system.lower()] = {
            "value": row["license_number"],
            "source_id": row["source_id"],
            "status": "official_licensed_registry",
        }
        record["certificate"]["number"] = row["license_number"]
        record["certificate"]["expires_at"] = row.get("expiration_date", "")
    for system, value in row.get("external_codes", {}).items():
        if value:
            record["codes"][system.lower()] = {
                "value": value,
                "source_id": row["source_id"],
                "status": "official_licensed_registry",
            }
    return record


def biopreferred_record(row: dict) -> dict:
    categories = row.get("categories", [])
    generic = {
        "id": f"USDA-BIOPREFERRED-{row['product_id']}",
        "source_number": row["product_id"],
        "brand": row["company"],
        "name": row["product_name"],
        "category": "; ".join(categories),
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "source": "usda-biopreferred",
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["company"]
    record["brand"] = row["company"]
    record["market"] = "US"
    record["source_id"] = "usda-biopreferred"
    record["source_record_id"] = row["product_id"]
    record["source_row"] = None
    record["evidence_status"] = "official_government_program_catalog"
    record["lifecycle_status"] = "listed_as_of_snapshot"
    record["snapshot_date"] = row["snapshot_date"]
    record["specifications"]["usda_biopreferred_categories"] = categories
    statuses = []
    if row.get("usda_certified_biobased"):
        statuses.append("USDA Certified Biobased")
    if row.get("mandatory_federal_purchasing"):
        statuses.append("USDA Mandatory Federal Purchasing category")
    record["specifications"]["usda_biopreferred_status"] = statuses
    record["canonical_key"] += f"|usda_biopreferred_product_id:{normalize(row['product_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    record["codes"]["usda_biopreferred_product_id"] = {
        "value": row["product_id"],
        "source_id": "usda-biopreferred",
        "status": "official_government_program_catalog",
    }
    return record


def zf_te_ml_record(row: dict) -> dict:
    viscosity = ""
    if row["family_code"] == "H":
        match = re.search(r"\b(?:ISO\s*)?(?:VG\s*)?([0-9]{2,3})\b", row["product_name"], re.I)
        if match:
            viscosity = match.group(1)
    generic = {
        "id": f"ZF-TE-ML-{row['approval_number']}",
        "source_number": row["approval_number"],
        "brand": row["manufacturer"],
        "name": row["product_name"],
        "category": "Смазочные материалы, одобренные ZF TE-ML",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "viscosity": viscosity,
        "source": "ZF_TE_ML",
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["manufacturer"]
    record["brand"] = row["manufacturer"]
    record["market"] = "GLOBAL_ZF_APPROVED"
    record["source_id"] = "ZF_TE_ML"
    record["source_record_id"] = row["approval_number"]
    record["source_row"] = None
    record["evidence_status"] = "official_oem_approval_registry"
    record["lifecycle_status"] = "approved_as_of_list_date"
    record["snapshot_date"] = row["list_date"]
    record["specifications"]["oem_approvals"] = [
        f"ZF {item['te_ml_sheet']} class {item['lubricant_class']}"
        for item in row["approval_occurrences"]
    ]
    record["specifications"]["zf_te_ml_sheets"] = row["te_ml_sheets"]
    record["specifications"]["zf_lubricant_classes"] = row["lubricant_classes"]
    record["specifications"]["product_name_aliases"] = row["product_name_aliases"]
    record["specifications"]["manufacturer_country"] = row["manufacturer_country"]
    record["specifications"]["licensed_standard"] = "ZF TE-ML"
    record["canonical_key"] += f"|zf_approval_number:{normalize(row['approval_number'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    record["codes"]["zf_approval_number"] = {
        "value": row["approval_number"],
        "source_id": "ZF_TE_ML",
        "status": "official_oem_approval_registry",
    }
    return record


def allison_record(row: dict) -> dict:
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["marketer_brand"],
        "name": row["product_name"],
        "category": "Жидкости, одобренные Allison Transmission",
        "category_code": "T",
        "family": FAMILY_NAMES["T"],
        "sae_class": row["product_name"],
        "source": "ALLISON_APPROVED_FLUIDS",
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["marketer_brand"]
    record["brand"] = row["marketer_brand"]
    record["market"] = "GLOBAL_ALLISON_APPROVED"
    record["source_id"] = "ALLISON_APPROVED_FLUIDS"
    record["source_record_id"] = row["source_record_id"]
    record["source_row"] = None
    record["evidence_status"] = "official_oem_approval_registry"
    record["lifecycle_status"] = "approved_as_of_list_date"
    record["snapshot_date"] = row["list_date"]
    record["specifications"]["oem_approvals"] = row["specifications"]
    record["specifications"]["allison_approval_numbers"] = row["approval_numbers"]
    record["specifications"]["licensed_standard"] = "Allison TES"
    record["canonical_key"] += f"|allison_registry_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    for index, approval_number in enumerate(row["approval_numbers"], 1):
        record["codes"][f"allison_approval_number_{index}"] = {
            "system": "ALLISON_APPROVAL_NUMBER",
            "value": approval_number,
            "source_id": "ALLISON_APPROVED_FLUIDS",
            "status": "official_oem_approval_registry",
        }
    return record


def driventic_diwa_record(row: dict) -> dict:
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["marketer_brand"],
        "name": row["product_name"],
        "category": "Масла, одобренные для автоматических трансмиссий DIWA",
        "category_code": "T",
        "family": FAMILY_NAMES["T"],
        "source": "DRIVENTIC_DIWA_APPROVED_OILS",
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["marketer_brand"]
    record["brand"] = row["marketer_brand"]
    record["market"] = "GLOBAL_DRIVENTIC_DIWA_APPROVED"
    record["source_id"] = "DRIVENTIC_DIWA_APPROVED_OILS"
    record["source_record_id"] = row["source_record_id"]
    record["source_row"] = None
    record["evidence_status"] = "official_oem_approval_registry"
    record["lifecycle_status"] = "approved_as_of_current_published_list"
    record["snapshot_date"] = row["snapshot_date"]
    record["specifications"]["oem_approvals"] = ["Driventic DIWA approved oil"]
    record["specifications"]["diwa_oil_change_intervals_km"] = [str(value) for value in row["oil_change_intervals_km"]]
    record["specifications"]["driventic_publication_numbers"] = sorted({
        item["publication_number"] for item in row["approval_occurrences"]
    })
    record["specifications"]["licensed_standard"] = "Driventic DIWA"
    record["canonical_key"] += f"|driventic_diwa_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    return record


def mercedes_dtfr_record(row: dict) -> dict:
    sae_class = row["sae_grades"][0] if row["sae_grades"] else ""
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["company"],
        "name": row["product_name"],
        "category": "Эксплуатационные жидкости с допуском Mercedes-Benz Trucks DTFR",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": sae_class,
        "source": "MERCEDES_DTFR_APPROVED_FLUIDS",
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["company"]
    record["brand"] = row["company"]
    record["market"] = "GLOBAL_MERCEDES_DTFR_APPROVED"
    record["source_id"] = "MERCEDES_DTFR_APPROVED_FLUIDS"
    record["source_record_id"] = row["source_record_id"]
    record["source_row"] = None
    record["evidence_status"] = "official_oem_approval_registry"
    record["lifecycle_status"] = "historical_approval" if row["historical_only"] else "approved_as_of_current_registry"
    record["snapshot_date"] = row["snapshot_date"]
    record["specifications"]["oem_approvals"] = [
        f"Mercedes-Benz Trucks {sheet}" for sheet in row["dtfr_sheets"]
    ]
    record["specifications"]["mercedes_dtfr_sheets"] = row["dtfr_sheets"]
    record["specifications"]["sae_grades_source_reported"] = row["sae_grades"]
    record["specifications"]["licensed_standard"] = "Mercedes-Benz Trucks DTFR"
    record["canonical_key"] += f"|mercedes_dtfr_product_id:{normalize(row['dtfr_product_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    record["codes"]["mercedes_dtfr_product_id"] = {
        "system": "MERCEDES_DTFR_PRODUCT_ID",
        "value": row["dtfr_product_id"],
        "source_id": "MERCEDES_DTFR_APPROVED_FLUIDS",
        "status": "official_oem_approval_registry",
    }
    return record


def mercedes_bevo_record(row: dict) -> dict:
    sae_class = row["sae_grades"][0] if row["sae_grades"] else ""
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["company"],
        "name": row["product_name"],
        "category": "Эксплуатационные жидкости с допуском Mercedes-Benz BeVo",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": sae_class,
        "source": "MERCEDES_BENZ_BEVO_APPROVED_FLUIDS",
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["company"]
    record["brand"] = row["company"]
    record["market"] = "GLOBAL_MERCEDES_BEVO_APPROVED"
    record["source_id"] = "MERCEDES_BENZ_BEVO_APPROVED_FLUIDS"
    record["source_record_id"] = row["source_record_id"]
    record["source_row"] = None
    record["evidence_status"] = "official_oem_approval_registry"
    record["lifecycle_status"] = "historical_approval" if row["historical_only"] else "approved_as_of_current_registry"
    record["snapshot_date"] = row["snapshot_date"]
    record["specifications"]["oem_approvals"] = [
        f"Mercedes-Benz BeVo {sheet}" for sheet in row["bevo_sheets"]
    ]
    record["specifications"]["mercedes_bevo_sheets"] = row["bevo_sheets"]
    record["specifications"]["sae_grades_source_reported"] = row["sae_grades"]
    record["specifications"]["licensed_standard"] = "Mercedes-Benz BeVo"
    record["canonical_key"] += f"|mercedes_bevo_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    for index, product_id in enumerate(row["bevo_product_ids"], 1):
        record["codes"][f"mercedes_bevo_product_id_{index}"] = {
            "system": "MERCEDES_BEVO_PRODUCT_ID",
            "value": product_id,
            "source_id": "MERCEDES_BENZ_BEVO_APPROVED_FLUIDS",
            "status": "official_oem_approval_registry",
        }
    return record


def merge_mercedes_bevo_evidence(target: dict, source_record: dict, raw: dict) -> None:
    specs = target["specifications"]
    specs["oem_approvals"] = sorted(set(specs.get("oem_approvals", [])) | {
        f"Mercedes-Benz BeVo {sheet}" for sheet in raw["bevo_sheets"]
    })
    specs["mercedes_bevo_sheets"] = sorted(
        set(specs.get("mercedes_bevo_sheets", [])) | set(raw["bevo_sheets"])
    )
    specs["sae_grades_source_reported"] = sorted(
        set(specs.get("sae_grades_source_reported", [])) | set(raw["sae_grades"])
    )
    for key, code in source_record["codes"].items():
        target["codes"][f"bevo_{raw['source_record_id']}_{key}"] = code
    if not raw["historical_only"]:
        target["lifecycle_status"] = "approved_as_of_current_registry"


def volvo_genuine_record(row: dict) -> dict:
    specs = row["specifications"]
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["brand"],
        "name": row["product_name"],
        "category": "Оригинальные эксплуатационные жидкости Volvo",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": specs.get("sae_engine") or specs.get("sae_gear") or "",
        "api_class": f"API {specs['api_gl']}" if specs.get("api_gl") else "",
        "grease_class": specs.get("nlgi", ""),
        "source": "VOLVO_GENUINE_FLUIDS",
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["manufacturer"]
    record["brand"] = row["brand"]
    record["market"] = row["market"]
    record["source_id"] = "VOLVO_GENUINE_FLUIDS"
    record["source_record_id"] = row["source_record_id"]
    record["source_row"] = None
    record["evidence_status"] = "official_manufacturer_product_catalog"
    record["lifecycle_status"] = "current_official_catalog"
    record["snapshot_date"] = row["snapshot_date"]
    record["specifications"].update(specs)
    record["specifications"]["source_url"] = row["source_url"]
    record["canonical_key"] += f"|volvo_genuine_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    for index, part_number in enumerate(specs.get("part_numbers", []), 1):
        record["codes"][f"volvo_part_number_{index}"] = {
            "system": "VOLVO_PART_NUMBER",
            "value": part_number,
            "source_id": "VOLVO_GENUINE_FLUIDS",
            "status": "official_manufacturer_product_catalog",
        }
    return record


def man_service_record(row: dict) -> dict:
    specs = row["specifications"]
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["brand"],
        "name": row["product_name"],
        "category": "Продукты из действующих рекомендаций MAN по эксплуатационным материалам",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": specs.get("sae_engine") or specs.get("sae_gear") or "",
        "viscosity": specs.get("iso_vg", ""),
        "grease_class": specs.get("nlgi", ""),
        "source": "MAN_CURRENT_SERVICE_PRODUCTS",
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["manufacturer"]
    record["brand"] = row["brand"]
    record["market"] = row["market"]
    record["source_id"] = "MAN_CURRENT_SERVICE_PRODUCTS"
    record["source_record_id"] = row["source_record_id"]
    record["source_row"] = None
    record["evidence_status"] = "official_oem_service_recommendation"
    record["lifecycle_status"] = "recommended_as_of_current_document"
    record["snapshot_date"] = row["snapshot_date"]
    record["specifications"].update(specs)
    record["specifications"]["application"] = row["application"]
    record["specifications"]["man_recommendation_document_date"] = row["document_date"]
    record["specifications"]["man_recommendation_pages"] = row["source_pages"]
    record["specifications"]["source_url"] = row["source_url"]
    record["canonical_key"] += f"|man_service_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    return record


def liqui_moly_catalog_record(row: dict) -> dict:
    technical = row["technical"]
    generic = {
        "id": row["source_record_id"], "source_number": row["source_record_id"],
        "brand": row["brand"], "name": row["product_name"],
        "category": "Исторический официальный каталог LIQUI MOLY 2020",
        "category_code": row["family_code"], "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": (technical.get("sae_grades") or [""])[0],
        "api_class": "; ".join(technical.get("api", []) + technical.get("acea", [])),
        "viscosity": (technical.get("iso_vg") or [""])[0],
        "source": "LIQUI_MOLY_2020_PRODUCT_CATALOG",
    }
    record = canonical_record(generic)
    record.update({
        "manufacturer": row["manufacturer"], "brand": row["brand"], "market": row["market"],
        "source_id": "LIQUI_MOLY_2020_PRODUCT_CATALOG", "source_record_id": row["source_record_id"],
        "source_row": None, "evidence_status": "official_manufacturer_product_catalog",
        "lifecycle_status": row["lifecycle_status"], "snapshot_date": row["snapshot_date"],
    })
    record["specifications"].update({
        "technical": technical, "document_date": row["document_date"], "source_pages": row["source_pages"],
        "part_numbers": row["part_numbers"], "package_rows": row["package_rows"],
        "source_url": row["source_url"], "catalog_page_url": row["catalog_page_url"],
    })
    record["canonical_key"] += f"|liqui_moly_2020_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    for index, part_number in enumerate(row["part_numbers"], 1):
        record["codes"][f"liqui_moly_part_number_{index}"] = {"system": "LIQUI_MOLY_PART_NUMBER", "value": part_number, "source_id": "LIQUI_MOLY_2020_PRODUCT_CATALOG", "status": "historical_official_catalog"}
    return record


def merge_liqui_moly_evidence(target: dict, source_record: dict, raw: dict) -> None:
    target["specifications"].setdefault("liqui_moly_historical_catalog_entries", []).append({
        "document_date": raw["document_date"], "pages": raw["source_pages"], "technical": raw["technical"],
        "part_numbers": raw["part_numbers"], "package_rows": raw["package_rows"], "source_url": raw["source_url"],
    })
    for key, code in source_record["codes"].items():
        target["codes"][f"liqui_moly_{raw['source_record_id']}_{key}"] = code


def liqui_moly_current_record(row: dict) -> dict:
    technical = row["technical"]
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["brand"],
        "name": row["product_name"],
        "category": "Текущий официальный каталог LIQUI MOLY 2026",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": (technical.get("sae_grades") or [""])[0],
        "api_class": "; ".join(row["specifications"] + row["approvals"] + row["recommendations"]),
        "viscosity": (technical.get("iso_vg") or [""])[0],
        "source": "LIQUI_MOLY_CURRENT_OPENAPI",
    }
    record = canonical_record(generic)
    record.update({
        "manufacturer": row["manufacturer"],
        "brand": row["brand"],
        "market": row["market"],
        "source_id": "LIQUI_MOLY_CURRENT_OPENAPI",
        "source_record_id": row["source_record_id"],
        "source_row": None,
        "evidence_status": "official_manufacturer_product_catalog",
        "lifecycle_status": row["lifecycle_status"],
        "snapshot_date": row["snapshot_date"],
    })
    record["specifications"].update({
        "technical": technical,
        "source_specifications": row["specifications"],
        "source_approvals": row["approvals"],
        "source_recommendations": row["recommendations"],
        "liqui_moly_master_sku": row["master_sku"],
        "liqui_moly_articles": row["articles"],
        "classification_basis": row["classification_basis"],
        "lifecycle_assessment": row["lifecycle_assessment"],
        "historical_candidates": row["historical_candidates"],
        "source_url": row["source_url"],
        "sitemap_url": row["sitemap_url"],
        "api_base_url": row["api_base_url"],
    })
    record["canonical_key"] += f"|liqui_moly_current_master:{normalize(row['master_sku'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    record["codes"]["liqui_moly_master_sku"] = {
        "system": "LIQUI_MOLY_MASTER_SKU",
        "value": row["master_sku"],
        "source_id": "LIQUI_MOLY_CURRENT_OPENAPI",
        "status": "current_official_catalog",
    }
    for index, article in enumerate(row["articles"], 1):
        record["codes"][f"liqui_moly_article_sku_{index}"] = {
            "system": "LIQUI_MOLY_ARTICLE_SKU",
            "value": article["sku"],
            "source_id": "LIQUI_MOLY_CURRENT_OPENAPI",
            "status": "current_official_catalog",
        }
    return record


def merge_liqui_moly_current_evidence(target: dict, source_record: dict, raw: dict) -> None:
    target["specifications"].setdefault("liqui_moly_current_catalog_entries", []).append({
        "master_sku": raw["master_sku"],
        "product_name": raw["product_name"],
        "market": raw["market"],
        "technical": raw["technical"],
        "specifications": raw["specifications"],
        "approvals": raw["approvals"],
        "recommendations": raw["recommendations"],
        "articles": raw["articles"],
        "lifecycle_assessment": raw["lifecycle_assessment"],
        "source_url": raw["source_url"],
    })
    target["lifecycle_status"] = "listed_as_of_current_official_catalog"
    target["snapshot_date"] = raw["snapshot_date"]
    existing_codes = {
        (code.get("system", key).upper(), code["value"])
        for key, code in target["codes"].items()
    }
    for key, code in source_record["codes"].items():
        if (code["system"], code["value"]) not in existing_codes:
            target["codes"][f"liqui_moly_current_{raw['master_sku']}_{key}"] = code
            existing_codes.add((code["system"], code["value"]))


def anp_brazil_record(row: dict) -> dict:
    """Convert one normalized ANP regulatory product-grade row to catalog form."""
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["registration_holder"],
        "name": row["product_name"],
        "category": "Действующий государственный реестр масел и смазок ANP Бразилии",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": row["sae"],
        "api_class": row["performance_level"],
        "viscosity": row["iso_vg"],
        "grease_class": row["nlgi"],
        "source": "ANP_BRAZIL_LUBRICANT_REGISTRY",
    }
    record = canonical_record(generic)
    record.update({
        "manufacturer": row["producer"] or row["registration_holder"],
        "brand": row["registration_holder"],
        "market": row["market"],
        "source_id": "ANP_BRAZIL_LUBRICANT_REGISTRY",
        "source_record_id": row["source_record_id"],
        "source_row": row["source_row_numbers"][0],
        "evidence_status": "official_government_regulatory_registry",
        "lifecycle_status": row["lifecycle_status"],
        "snapshot_date": row["snapshot_date"],
    })
    record["specifications"].update({
        "anp_registration_status": row["registration_status"],
        "anp_registration_holder": row["registration_holder"],
        "anp_registration_holder_cnpj": row["registration_holder_cnpj"],
        "anp_company_type": row["company_type"],
        "anp_producer": row["producer"],
        "anp_origin": row["origin"],
        "anp_product_type": row["product_type"],
        "anp_regulatory_purpose": row["regulatory_purpose"],
        "application": row["application"],
        "base_oil_composition": row["base_oil_composition"],
        "performance_raw": row["performance_level"],
        "anp_process_numbers": row["process_numbers"],
        "anp_registration_years": row["registration_years"],
        "packages": row["packages"],
        "classification_basis": row["classification_basis"],
        "source_occurrence_count": row["source_occurrence_count"],
        "source_row_numbers": row["source_row_numbers"],
        "source_url": row["source_url"],
        "metadata_url": row["metadata_url"],
    })
    record["canonical_key"] += f"|anp_brazil_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    record["codes"]["anp_registration_number"] = {
        "system": "ANP_BRAZIL_REGISTRATION_NUMBER",
        "value": row["registration_number"],
        "source_id": "ANP_BRAZIL_LUBRICANT_REGISTRY",
        "status": "active_in_current_anp_snapshot",
    }
    return record


def indonesia_npt_record(row: dict) -> dict:
    """Convert one published Indonesian NPT table row to catalog form."""
    technical = row["technical"]
    performance = "; ".join(
        f"{system.upper()} {value}"
        for system in ("api", "acea", "jaso")
        for value in technical[system]
    )
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["company"],
        "name": row["product_name"],
        "category": "Государственный перечень смазочных материалов NPT Индонезии 2021–2025",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": technical["sae"][0] if technical["sae"] else "",
        "api_class": performance,
        "viscosity": technical["iso_vg"][0] if technical["iso_vg"] else "",
        "grease_class": technical["nlgi"][0] if technical["nlgi"] else "",
        "source": "INDONESIA_NPT_LUBRICANT_REGISTRY",
    }
    record = canonical_record(generic)
    record.update({
        "manufacturer": row["company"],
        "brand": row["company"],
        "market": row["market"],
        "source_id": "INDONESIA_NPT_LUBRICANT_REGISTRY",
        "source_record_id": row["source_record_id"],
        "source_row": row["source_pdf_page"],
        "evidence_status": (
            "official_government_regulatory_registry"
            if row["registration_number"]
            else "official_government_registry_source_data_issue"
        ),
        "lifecycle_status": row["lifecycle_status"],
        "snapshot_date": row["snapshot_date"],
    })
    record["specifications"].update({
        "indonesia_npt_class_code": row["npt_class_code"],
        "indonesia_npt_registration_number_raw": row["registration_number_raw"],
        "indonesia_npt_registration_number_status": row["registration_number_status"],
        "indonesia_npt_expiry_raw": row["expiry_raw"],
        "valid_through": row["valid_through"],
        "lifecycle_basis": row["lifecycle_basis"],
        "classification_basis": row["classification_basis"],
        "sae_source_reported": technical["sae"],
        "iso_vg_source_reported": technical["iso_vg"],
        "nlgi_source_reported": technical["nlgi"],
        "api_source_reported": technical["api"],
        "acea_source_reported": technical["acea"],
        "jaso_source_reported": technical["jaso"],
        "source_document_date": row["source_document_date"],
        "source_pdf_page": row["source_pdf_page"],
        "source_url": row["source_url"],
    })
    record["canonical_key"] += f"|indonesia_npt_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    if row["registration_number"]:
        record["codes"]["indonesia_npt_registration_number"] = {
            "system": "INDONESIA_NPT_REGISTRATION_NUMBER",
            "value": row["registration_number"],
            "source_id": "INDONESIA_NPT_LUBRICANT_REGISTRY",
            "status": row["lifecycle_status"],
        }
    return record


def dla_qpd_record(row: dict) -> dict:
    """Convert one normalized DLA qualification identity to catalog form."""
    source_id = row["source_id"]
    technical = row["technical"]
    qualification_names = sorted({
        value
        for approval in row["qualifications"]
        for value in (approval["qpl_number"], approval["document_id"], approval["government_designation"])
        if value
    })
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["company"],
        "name": row["product_name"],
        "category": "Официальный реестр квалифицированной продукции DLA, FSC 9150",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": technical["sae"][0] if technical["sae"] else "",
        "viscosity": technical["iso_vg"][0] if technical["iso_vg"] else "",
        "grease_class": technical["nlgi"][0] if technical["nlgi"] else "",
        "source": source_id,
    }
    record = canonical_record(generic)
    record.update({
        "manufacturer": row["company"],
        "brand": row["company"],
        "market": row["market"],
        "source_id": source_id,
        "source_record_id": row["source_record_id"],
        "source_row": None,
        "evidence_status": "official_government_qualified_product_registry",
        "lifecycle_status": row["lifecycle_status"],
        "snapshot_date": row["snapshot_date"],
    })
    record["specifications"].update({
        "dla_qpd_qualifications": qualification_names,
        "dla_qpd_qualification_records": row["qualifications"],
        "dla_qpd_certified_statuses": row["certified_statuses"],
        "dla_qpd_sam_statuses": row["sam_statuses"],
        "dla_qpd_stop_ship_values": row["stop_ship_values"],
        "dla_qpd_source_types": row["source_types"],
        "dla_qpd_manufacturer_designations_raw": row.get("manufacturer_designations_raw", [row["product_name"]]),
        "dla_qpd_designation_qualifiers": row.get("designation_qualifiers", []),
        "cage_codes": row["cage_codes"],
        "nato_codes": technical["nato_codes"],
        "sae_source_reported": technical["sae"],
        "iso_vg_source_reported": technical["iso_vg"],
        "nlgi_source_reported": technical["nlgi"],
        "source_occurrence_count": row["source_occurrence_count"],
        "source_url": row["source_url"],
        "help_url": row["help_url"],
    })
    record["canonical_key"] += f"|dla_qpd_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    for index, qpl_number in enumerate(sorted({qualification["qpl_number"] for qualification in row["qualifications"]})):
        record["codes"][f"dla_qpl_{index}"] = {
            "system": "DLA_QPL_NUMBER",
            "value": qpl_number,
            "source_id": source_id,
            "status": row["lifecycle_status"],
        }
    return record


def blue_angel_record(row: dict) -> dict:
    """Convert one current Blue Angel DE-UZ 178 product to catalog form."""
    technical = row["technical"]
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": row["manufacturer"],
        "name": row["product_name"],
        "category": "Blue Angel DE-UZ 178: " + "; ".join(row["official_categories"]),
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": technical["sae"][0] if technical["sae"] else "",
        "viscosity": technical["iso_vg"][0] if technical["iso_vg"] else "",
        "grease_class": technical["nlgi"][0] if technical["nlgi"] else "",
        "source": "BLUE_ANGEL_DE_UZ_178",
    }
    record = canonical_record(generic)
    record.update({
        "manufacturer": row["manufacturer"],
        "brand": row["manufacturer"],
        "market": row["market"],
        "source_id": "BLUE_ANGEL_DE_UZ_178",
        "source_record_id": row["source_record_id"],
        "source_row": row["source_row_numbers"][0],
        "evidence_status": "official_ecolabel_product_registry",
        "lifecycle_status": row["lifecycle_status"],
        "snapshot_date": row["snapshot_date"],
    })
    record["specifications"].update({
        "blue_angel_standard": row["certification_standard"],
        "blue_angel_categories": row["official_categories"],
        "blue_angel_product_page_urls": row["product_page_urls"],
        "product_external_urls": row["product_external_urls"],
        "classification_basis": row["classification_basis"],
        "iso_vg_source_reported": technical["iso_vg"],
        "nlgi_source_reported": technical["nlgi"],
        "sae_source_reported": technical["sae"],
        "source_occurrence_count": row["source_occurrence_count"],
        "source_row_numbers": row["source_row_numbers"],
        "source_export_facts_sha256": row["source_export_facts_sha256"],
        "source_page_facts_sha256": row["source_page_facts_sha256"],
        "category_page_sha256": row["category_page_sha256"],
        "criteria_url": row["criteria_url"],
    })
    record["canonical_key"] += f"|blue_angel_record:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    for index, url in enumerate(row["product_page_urls"]):
        record["codes"][f"blue_angel_product_{index}"] = {
            "system": "BLUE_ANGEL_PRODUCT_PAGE",
            "value": url,
            "source_id": "BLUE_ANGEL_DE_UZ_178",
            "status": row["lifecycle_status"],
        }
    return record


def merge_blue_angel_evidence(target: dict, source_record: dict, raw: dict) -> None:
    target["specifications"].setdefault("blue_angel_de_uz_178", []).append({
        "source_record_id": raw["source_record_id"],
        "categories": raw["official_categories"],
        "product_page_urls": raw["product_page_urls"],
        "snapshot_date": raw["snapshot_date"],
    })
    existing_codes = {(code.get("system", key).upper(), code["value"]) for key, code in target["codes"].items()}
    for key, code in source_record["codes"].items():
        identity = (code.get("system", key).upper(), code["value"])
        if identity not in existing_codes:
            target["codes"][f"blue_angel_{raw['source_record_id']}_{key}"] = code
            existing_codes.add(identity)


def liqui_moly_identity_name(value: str) -> str:
    return re.sub(r"^liqui moly(?: gmbh)?\s+", "", normalize(value)).strip()


def brand_tokens_overlap(left: str, right: str) -> bool:
    left_tokens = set(normalize(left).split())
    right_tokens = set(normalize(right).split())
    return bool(left_tokens & right_tokens)


def merge_man_recommendation_evidence(target: dict, raw: dict) -> None:
    target["specifications"].setdefault("man_service_recommendations", []).append({
        "application": raw["application"],
        "document_date": raw["document_date"],
        "pages": raw["source_pages"],
        "source_url": raw["source_url"],
        "specifications": raw["specifications"],
    })


def fuchs_catalog_record(row: dict, source_id: str, market_name: str) -> dict:
    technical = row["technical"]
    raw_performance = "; ".join(row["specifications"] + row["approvals"] + row["fuchs_recommendations"])
    generic = {
        "id": row["source_record_id"],
        "source_number": row["source_record_id"],
        "brand": "FUCHS",
        "name": row["product_name"],
        "category": f"Официальный каталог FUCHS {market_name}",
        "category_code": row["family_code"],
        "family": FAMILY_NAMES[row["family_code"]],
        "sae_class": technical["sae_grades"][0] if technical["sae_grades"] else "",
        "api_class": raw_performance,
        "viscosity": technical["iso_vg"][0] if technical["iso_vg"] else "",
        "grease_class": technical["nlgi"][0] if technical["nlgi"] else "",
        "source": source_id,
    }
    record = canonical_record(generic)
    record["manufacturer"] = row["manufacturer"]
    record["brand"] = "FUCHS"
    record["market"] = row["market"]
    record["source_id"] = source_id
    record["source_record_id"] = row["source_record_id"]
    record["source_row"] = None
    record["evidence_status"] = "official_manufacturer_product_catalog"
    record["lifecycle_status"] = "listed_as_of_current_product_finder"
    record["snapshot_date"] = row["snapshot_date"]
    record["specifications"].update({
        key: value for key, value in technical.items()
        if key not in {"sae_grades", "iso_vg", "nlgi"}
    })
    record["specifications"].update({
        "sae_grades_source_reported": technical["sae_grades"],
        "iso_vg_source_reported": technical["iso_vg"],
        "nlgi_source_reported": technical["nlgi"],
        "source_specifications": row["specifications"],
        "source_approvals": row["approvals"],
        "fuchs_recommendations": row["fuchs_recommendations"],
        "fuchs_brand_lines": row["brand_lines"],
        "product_group_paths": row["product_group_paths"],
        "industries": row["industries"],
        "classification_basis": row["classification_basis"],
        "source_product_dates": row["source_product_dates"],
        "source_urls": row["source_urls"],
        "grain_warning": row["grain_warning"],
    })
    source_key = {
        "FUCHS_INDIA_PRODUCT_FINDER": "fuchs_india_record",
        "FUCHS_US_PRODUCT_FINDER": "fuchs_us_record",
        "FUCHS_GERMANY_PRODUCT_FINDER": "fuchs_germany_record",
        "FUCHS_POLAND_PRODUCT_FINDER": "fuchs_poland_record",
        "FUCHS_ITALY_PRODUCT_FINDER": "fuchs_italy_record",
        "FUCHS_SWEDEN_PRODUCT_FINDER": "fuchs_sweden_record",
        "FUCHS_SPAIN_PRODUCT_FINDER": "fuchs_spain_record",
        "FUCHS_FRANCE_PRODUCT_FINDER": "fuchs_france_record",
        "FUCHS_TURKEY_PRODUCT_FINDER": "fuchs_turkey_record",
        "FUCHS_CANADA_PRODUCT_FINDER": "fuchs_canada_record",
        "FUCHS_CHINA_PRODUCT_FINDER": "fuchs_china_record",
        "FUCHS_CZECH_PRODUCT_FINDER": "fuchs_czech_record",
        "FUCHS_MEXICO_PRODUCT_FINDER": "fuchs_mexico_record",
        "FUCHS_SOUTH_AFRICA_PRODUCT_FINDER": "fuchs_south_africa_record",
    }[source_id]
    record["canonical_key"] += f"|{source_key}:{normalize(row['source_record_id'])}"
    record["product_id"] = "WC-" + hashlib.sha256(record["canonical_key"].encode()).hexdigest()[:20]
    for index, uid in enumerate(row["source_uids"], 1):
        record["codes"][f"fuchs_product_uid_{index}"] = {
            "system": "FUCHS_PRODUCT_UID",
            "value": str(uid),
            "source_id": source_id,
            "status": "official_manufacturer_product_catalog",
        }
    return record


def merge_fuchs_catalog_evidence(target: dict, source_record: dict, raw: dict) -> None:
    target["specifications"].setdefault("fuchs_catalog_entries", []).append({
        "source_id": raw["source_id"],
        "brand_lines": raw["brand_lines"],
        "market": raw["market"],
        "product_group_paths": raw["product_group_paths"],
        "specifications": raw["specifications"],
        "approvals": raw["approvals"],
        "recommendations": raw["fuchs_recommendations"],
        "technical": raw["technical"],
        "source_urls": raw["source_urls"],
    })
    for key, code in source_record["codes"].items():
        target["codes"][f"fuchs_{raw['source_id']}_{raw['source_record_id']}_{key}"] = code


def integrate_fuchs_market(input_records: list[dict], source_rows: list[dict], source_id: str, market_name: str, prior_market_rows: list[dict]) -> dict:
    """Attach one official FUCHS market while preserving ambiguous identities for review."""
    source_records = [fuchs_catalog_record(row, source_id, market_name) for row in source_rows]
    prior_name_families = defaultdict(set)
    for row in prior_market_rows:
        prior_name_families[normalize(row["product_name"])].add(row["family_code"])
    exact_rows = sum(row["family_code"] in prior_name_families[normalize(row["product_name"])] for row in source_rows)
    conflict_rows = sum(bool(prior_name_families[normalize(row["product_name"])]) and row["family_code"] not in prior_name_families[normalize(row["product_name"])] for row in source_rows)
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    product_key, review_keys, family_conflict_keys = {}, [], []
    added_rows = matched_rows = 0
    for raw, source_record in zip(source_rows, source_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            added_rows += 1
            if len(matches) > 1:
                review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        product_key[raw["source_record_id"]] = target["canonical_key"]
    return {"product_key": product_key, "added": added_rows, "matched": matched_rows, "review_keys": review_keys, "family_conflict_keys": family_conflict_keys, "exact": exact_rows, "conflicts": conflict_rows}


def deduplicate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    by_key = defaultdict(list)
    for record in records:
        by_key[record["canonical_key"]].append(record)
    canonical = []
    candidates = []
    for group in by_key.values():
        canonical.append(group[0])
        for duplicate in group[1:]:
            candidates.append({
                "product_id_a": group[0]["product_id"],
                "product_id_b": duplicate["product_id"],
                "reason": "identical_normalized_identity_and_professional_signature",
                "score": 1.0,
                "decision": "merged",
            })
    by_name = defaultdict(list)
    for record in canonical:
        by_name[(normalize(record["brand"]), record["product_name_normalized"], record["family_code"])].append(record)
    for group in by_name.values():
        if len(group) < 2:
            continue
        by_source = defaultdict(list)
        for record in group:
            by_source[record["source_id"]].append(record)
        for source_group in by_source.values():
            for left, right in zip(source_group, source_group[1:]):
                candidates.append({
                    "product_id_a": left["product_id"],
                    "product_id_b": right["product_id"],
                    "reason": "same_brand_name_family_but_different_professional_signature_within_source",
                    "score": 0.7,
                    "decision": "keep_separate_specification_conflict",
                })
        for left, right in combinations(group, 2):
            if left["source_id"] == right["source_id"]:
                continue
            candidates.append({
                "product_id_a": left["product_id"],
                "product_id_b": right["product_id"],
                "reason": "same_company_name_family_across_sources_requires_specification_review",
                "score": 0.9,
                "decision": "review_cross_source_identity",
            })
    return canonical, candidates


def quality_issues(records: list[dict]) -> list[dict]:
    issues = []
    for row in records:
        expected = EXPECTED_ENKT_BASE.get(row["family_code"])
        for system in ["enkt", "skp"]:
            code = row["codes"].get(system, {}).get("value", "")
            if expected and code and not code.startswith(expected):
                issues.append({
                    "product_id": row["product_id"],
                    "issue_code": "classification_family_conflict",
                    "severity": "high",
                    "field": system.upper(),
                    "value": code,
                    "expected": expected,
                    "action": "Do not use for analytics; remap against current ENKT/SKP and retain legacy value as evidence.",
                })
        specs = row["specifications"]
        missing = []
        has_government_qualification = bool(specs.get("dla_qpd_qualifications"))
        if row["family_code"] == "M":
            is_jaso_two_cycle = specs.get("jaso_family_detail") == "two_cycle_gasoline_engine_oil"
            is_nmma_two_cycle = specs.get("licensed_standard") == "NMMA TC-W3"
            if not specs["sae_engine"] and not is_jaso_two_cycle and not is_nmma_two_cycle and not has_government_qualification:
                missing.append("SAE")
            if not specs["api"] and not specs["acea"] and not specs["ilsac"] and not specs.get("jaso") and not specs.get("licensed_standard") and not has_government_qualification:
                missing.append("API/ACEA/ILSAC/JASO/OEM licence")
        elif row["family_code"] in {"H", "I", "C", "U"} and not specs["iso_vg"] and not has_government_qualification:
            missing.append("ISO VG")
        if missing:
            issues.append({
                "product_id": row["product_id"],
                "issue_code": "professional_key_incomplete",
                "severity": "medium",
                "field": "professional_key",
                "value": "",
                "expected": "; ".join(missing),
                "action": "Obtain an official TDS/PDS or certificate before strict equivalence matching.",
            })
    return issues


def build_sqlite(records: list[dict], candidates: list[dict], issues: list[dict], source_links: list[dict], offers: list[dict], policies: dict, run_id: str) -> None:
    if SQLITE_OUT.exists():
        SQLITE_OUT.unlink()
    db = sqlite3.connect(SQLITE_OUT)
    db.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE ingest_runs(run_id TEXT PRIMARY KEY, snapshot_date TEXT NOT NULL, generated_at TEXT NOT NULL, input_rows INTEGER NOT NULL, canonical_rows INTEGER NOT NULL);
    CREATE TABLE sources(source_id TEXT PRIMARY KEY, title TEXT NOT NULL, owner TEXT, source_type TEXT, source_locator TEXT, source_sha256 TEXT, source_url TEXT, terms_url TEXT, access_status TEXT NOT NULL, bulk_ingest_allowed INTEGER NOT NULL, publication_status TEXT, observed_count INTEGER, notes TEXT);
    CREATE TABLE products(product_id TEXT PRIMARY KEY, canonical_key TEXT UNIQUE NOT NULL, manufacturer TEXT, brand TEXT NOT NULL, product_name_raw TEXT NOT NULL, product_name_normalized TEXT NOT NULL, market TEXT, family_code TEXT, family TEXT, category TEXT, candidate_technical_profile_id TEXT, profile_match_confidence REAL, profile_match_status TEXT, profile_match_basis_json TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES sources(source_id), source_record_id TEXT, source_row INTEGER, evidence_status TEXT NOT NULL, lifecycle_status TEXT NOT NULL, snapshot_date TEXT NOT NULL);
    CREATE TABLE product_sources(product_id TEXT NOT NULL REFERENCES products(product_id), source_id TEXT NOT NULL REFERENCES sources(source_id), source_record_id TEXT NOT NULL, source_row INTEGER, relation TEXT NOT NULL, PRIMARY KEY(product_id, source_id, source_record_id));
    CREATE TABLE specifications(product_id TEXT NOT NULL REFERENCES products(product_id), spec_type TEXT NOT NULL, spec_value TEXT NOT NULL, is_parsed INTEGER NOT NULL, PRIMARY KEY(product_id, spec_type, spec_value));
    CREATE TABLE external_codes(product_id TEXT NOT NULL REFERENCES products(product_id), code_system TEXT NOT NULL, code_value TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES sources(source_id), status TEXT NOT NULL, PRIMARY KEY(product_id, code_system, code_value));
    CREATE TABLE certificates(product_id TEXT NOT NULL REFERENCES products(product_id), certificate_number TEXT, issued_at TEXT, expires_at TEXT, local_producer_certificate TEXT, technical_document TEXT, certificate_status TEXT);
    CREATE TABLE duplicate_decisions(product_id_a TEXT NOT NULL, product_id_b TEXT NOT NULL, reason TEXT NOT NULL, score REAL NOT NULL, decision TEXT NOT NULL);
    CREATE TABLE quality_issues(product_id TEXT NOT NULL REFERENCES products(product_id), issue_code TEXT NOT NULL, severity TEXT NOT NULL, field TEXT NOT NULL, value TEXT, expected TEXT, action TEXT NOT NULL);
    CREATE TABLE product_offers(offer_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(product_id), market TEXT NOT NULL, package_name TEXT NOT NULL, unit TEXT NOT NULL, quantity_per_package REAL, weight_kg REAL, density_kg_per_l REAL, lifecycle_status TEXT NOT NULL, archive_type TEXT, archive_reason TEXT, source_id TEXT NOT NULL REFERENCES sources(source_id), source_record_id TEXT NOT NULL);
    CREATE INDEX products_brand_name_idx ON products(brand, product_name_normalized);
    CREATE INDEX products_family_idx ON products(family_code);
    CREATE INDEX specs_type_value_idx ON specifications(spec_type, spec_value);
    CREATE INDEX codes_system_value_idx ON external_codes(code_system, code_value);
    CREATE INDEX offers_product_idx ON product_offers(product_id);
    """)
    db.execute("INSERT INTO ingest_runs VALUES (?,?,?,?,?)", (run_id, SNAPSHOT_DATE, f"{SNAPSHOT_DATE}T00:00:00+00:00", len(records), len(records)))
    for source in policies["sources"]:
        db.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            source["source_id"], source["title"], source.get("owner"), source.get("source_type"),
            source.get("source_locator"), source.get("source_sha256"), source.get("source_url"), source.get("terms_url"),
            source["access_status"], int(source["bulk_ingest_allowed"]), source.get("publication_status"),
            source.get("observed_count"), source.get("notes"),
        ))
    for row in records:
        db.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            row["product_id"], row["canonical_key"], row["manufacturer"], row["brand"],
            row["product_name_raw"], row["product_name_normalized"], row["market"], row["family_code"],
            row["family"], row["category"], row["candidate_technical_profile_id"],
            row["profile_match_confidence"], row["profile_match_status"],
            json.dumps(row["profile_match_basis"], ensure_ascii=False), row["source_id"],
            row["source_record_id"], row["source_row"], row["evidence_status"], row["lifecycle_status"],
            row["snapshot_date"],
        ))
        for spec_type, value in row["specifications"].items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                if text(item):
                    db.execute("INSERT OR IGNORE INTO specifications VALUES (?,?,?,?)", (row["product_id"], spec_type, text(item), int(spec_type != "performance_raw")))
        for system, code in row["codes"].items():
            db.execute("INSERT INTO external_codes VALUES (?,?,?,?,?)", (row["product_id"], code.get("system", system).upper(), code["value"], code["source_id"], code["status"]))
        cert = row["certificate"]
        if any(cert.values()):
            db.execute("INSERT INTO certificates VALUES (?,?,?,?,?,?,?)", (
                row["product_id"], cert["number"], cert["issued_at"], cert["expires_at"],
                cert["local_producer_certificate"], cert["technical_document"], row["certificate_status"],
            ))
    db.executemany("INSERT INTO duplicate_decisions VALUES (:product_id_a,:product_id_b,:reason,:score,:decision)", candidates)
    db.executemany("INSERT INTO quality_issues VALUES (:product_id,:issue_code,:severity,:field,:value,:expected,:action)", issues)
    db.executemany("INSERT INTO product_sources VALUES (:product_id,:source_id,:source_record_id,:source_row,:relation)", source_links)
    db.executemany("INSERT INTO product_offers VALUES (:offer_id,:product_id,:market,:package_name,:unit,:quantity_per_package,:weight_kg,:density_kg_per_l,:lifecycle_status,:archive_type,:archive_reason,:source_id,:source_record_id)", offers)
    db.commit()
    db.close()


def compress_sqlite() -> None:
    """Create a deterministic repository-safe copy of the generated SQLite database."""
    with SQLITE_OUT.open("rb") as source, SQLITE_GZ_OUT.open("wb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, compresslevel=9, mtime=0) as archive:
            shutil.copyfileobj(source, archive, length=1024 * 1024)


def compress_jsonl() -> None:
    """Create a deterministic compressed copy of the generated JSONL aggregate."""
    with JSONL_OUT.open("rb") as source, JSONL_GZ_OUT.open("wb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, compresslevel=9, mtime=0) as archive:
            shutil.copyfileobj(source, archive, length=1024 * 1024)


def style_sheet(ws) -> None:
    fill = PatternFill("solid", fgColor="17365D")
    for cell in ws[1]:
        cell.fill = fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for column in ws.columns:
        letter = get_column_letter(column[0].column)
        ws.column_dimensions[letter].width = min(55, max(11, max(len(text(c.value)) for c in column) + 2))
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def add_sheet(wb, title, headers, rows):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for row in rows:
        ws.append(row)
    style_sheet(ws)


def build_workbook(records: list[dict], candidates: list[dict], issues: list[dict], offers: list[dict], exclusions: list[dict], policies: dict, report: dict) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    add_sheet(wb, "01_Паспорт", ["Показатель", "Значение"], [
        ("Статус", "Проверенный seed; мировой каталог ещё не завершён"),
        ("Дата среза", SNAPSHOT_DATE),
        ("Входных строк", report["input_rows"]),
        ("Канонических строк", report["canonical_rows"]),
        ("Брендов", report["brands"]),
        ("Строк с проектным первичным источником", report["project_source_rows"]),
        ("Legacy-строк, ожидающих официальный TDS/PDS", report["legacy_rows_needing_evidence"]),
        ("Активных offer/SKU упаковок", report["active_offers"]),
        ("Подтверждённый мировой итог", "НЕ ОПРЕДЕЛЁН: подключён только проектный seed"),
    ])
    headers = ["Product ID", "Производитель/заявитель", "Бренд", "Исходное название", "Рынок", "Семейство", "Категория", "SAE", "SAE Gear", "ISO VG", "API", "API GL", "ACEA", "ILSAC", "JASO", "Кандидат техпрофиля", "Уверенность", "Источник", "Строка источника", "Статус доказательства"]
    add_sheet(wb, "02_Продукты", headers, [[
        r["product_id"], r["manufacturer"], r["brand"], r["product_name_raw"], r["market"], r["family"], r["category"],
        r["specifications"]["sae_engine"], r["specifications"]["sae_gear"], r["specifications"]["iso_vg"],
        "; ".join(r["specifications"]["api"]), "; ".join(r["specifications"]["api_gl"]),
        "; ".join(r["specifications"]["acea"]), "; ".join(r["specifications"]["ilsac"]), "; ".join(r["specifications"].get("jaso", [])),
        r["candidate_technical_profile_id"], r["profile_match_confidence"], r["source_id"], r["source_row"], r["evidence_status"],
    ] for r in records])
    add_sheet(wb, "03_Источники_и_права", ["Source ID", "Название", "Владелец", "URL/файл", "SHA-256", "Статус доступа", "Bulk ingest", "Публикация", "Примечание"], [[
        s["source_id"], s["title"], s.get("owner"), s.get("source_url") or s.get("source_locator"), s.get("source_sha256"), s["access_status"],
        "да" if s["bulk_ingest_allowed"] else "нет", s.get("publication_status"), s.get("notes"),
    ] for s in policies["sources"]])
    add_sheet(wb, "04_Дедупликация", ["Product A", "Product B", "Причина", "Score", "Решение"], [[
        c["product_id_a"], c["product_id_b"], c["reason"], c["score"], c["decision"]
    ] for c in candidates])
    add_sheet(wb, "05_По_брендам", ["Бренд", "Канонических строк"], sorted(Counter(r["brand"] for r in records).items(), key=lambda x: (-x[1], x[0])))
    add_sheet(wb, "06_По_семействам", ["Код", "Семейство", "Канонических строк"], [[code, FAMILY_NAMES.get(code, code), count] for code, count in sorted(Counter(r["family_code"] for r in records).items())])
    add_sheet(wb, "07_Запрос_прав", ["Поле", "Текст"], [
        ("Тема", "Request for permission / machine-readable lubricant product data for Uzbekistan classification project"),
        ("Цель", "Создание государственного профессионального классификатора смазочных материалов и сопоставления ENKT–SKP–IKPU–HS/TN VED."),
        ("Запрашиваемые данные", "Product ID, brand, product/grade name, market, lifecycle, viscosity, standards, OEM approvals, application, TDS/PDS/SDS links and update date."),
        ("Запрашиваемое право", "Непосредственная машинная выгрузка или API/feed; хранение фактических характеристик и ссылок; регулярное обновление; публикация производных классификационных соответствий."),
        ("Что не требуется", "Не требуется право переиздавать фотографии, фирменное оформление или полный текст технических документов."),
        ("Формат", "CSV/JSON/XML/API/SFTP или периодический архив; предпочтительно стабильный manufacturer product ID."),
        ("Контроль происхождения", "Для каждой строки сохраняются владелец, URL/идентификатор, рынок, дата получения, версия и хэш источника."),
        ("Контактный вопрос", "Просим подтвердить допустимый объём использования, атрибуцию, частоту обновления и ограничения на публикацию."),
    ])
    by_id = {row["product_id"]: row for row in records}
    add_sheet(wb, "08_Проблемы_качества", ["Product ID", "Бренд", "Продукт", "Код проблемы", "Уровень", "Поле", "Значение", "Ожидалось", "Действие"], [[
        issue["product_id"], by_id[issue["product_id"]]["brand"], by_id[issue["product_id"]]["product_name_raw"],
        issue["issue_code"], issue["severity"], issue["field"], issue["value"], issue["expected"], issue["action"],
    ] for issue in issues])
    add_sheet(wb, "09_Упаковки_SKU", ["Offer ID", "Product ID", "Рынок", "Упаковка", "Единица", "Количество", "Вес, кг", "Плотность, кг/л", "Статус", "Архив", "Причина", "Source record"], [[
        o["offer_id"], o["product_id"], o["market"], o["package_name"], o["unit"], o["quantity_per_package"],
        o["weight_kg"], o["density_kg_per_l"], o["lifecycle_status"], o["archive_type"], o["archive_reason"], o["source_record_id"],
    ] for o in offers])
    add_sheet(wb, "10_Исключённые_строки", ["Source record", "Название", "Причина"], [[
        e["source_record_id"], e["name"], e["reason"]
    ] for e in exclusions])
    XLSX_OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX_OUT)


def main() -> None:
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    policies = json.loads(POLICY.read_text(encoding="utf-8"))
    input_records = [canonical_record(row) for row in source["products"]]
    jaso_source_rows = [json.loads(line) for line in JASO_JSONL.read_text(encoding="utf-8").splitlines() if line]
    jaso_records = [jaso_record(row) for row in jaso_source_rows]
    input_records.extend(jaso_records)
    licensed_source_rows = [json.loads(line) for line in LICENSED_JSONL.read_text(encoding="utf-8").splitlines() if line]
    licensed_records = [licensed_record(row) for row in licensed_source_rows]
    input_records.extend(licensed_records)
    blue_angel_source_rows = [json.loads(line) for line in BLUE_ANGEL_JSONL.read_text(encoding="utf-8").splitlines() if line]
    blue_angel_records = [blue_angel_record(row) for row in blue_angel_source_rows]
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
        existing_by_name[row["product_name_normalized"]].append(row)
    blue_angel_product_key = {}
    blue_angel_added_rows = 0
    blue_angel_matched_rows = 0
    blue_angel_review_keys = []
    blue_angel_family_conflict_keys = []
    for raw, source_record in zip(blue_angel_source_rows, blue_angel_records):
        name = normalize(raw["product_name"])
        matches = [
            row for row in existing_by_name_family[(name, raw["family_code"])]
            if brand_tokens_overlap(raw["manufacturer"], row["brand"])
        ]
        if len(matches) == 1:
            target = matches[0]
            merge_blue_angel_evidence(target, source_record, raw)
            blue_angel_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [
                row for row in existing_by_name[name]
                if row["family_code"] != raw["family_code"] and brand_tokens_overlap(raw["manufacturer"], row["brand"])
            ]
            existing_by_name[name].append(target)
            blue_angel_added_rows += 1
            if len(matches) > 1:
                blue_angel_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                blue_angel_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        blue_angel_product_key[raw["source_record_id"]] = target["canonical_key"]
    biopreferred_source_rows = [json.loads(line) for line in USDA_BIOPREFERRED_JSONL.read_text(encoding="utf-8").splitlines() if line]
    biopreferred_records = [biopreferred_record(row) for row in biopreferred_source_rows]
    input_records.extend(biopreferred_records)
    zf_source_rows = [json.loads(line) for line in ZF_TE_ML_JSONL.read_text(encoding="utf-8").splitlines() if line]
    zf_records = [zf_te_ml_record(row) for row in zf_source_rows]
    input_records.extend(zf_records)
    allison_source_rows = [json.loads(line) for line in ALLISON_JSONL.read_text(encoding="utf-8").splitlines() if line]
    allison_records = [allison_record(row) for row in allison_source_rows]
    input_records.extend(allison_records)
    driventic_source_rows = [json.loads(line) for line in DRIVENTIC_DIWA_JSONL.read_text(encoding="utf-8").splitlines() if line]
    driventic_records = [driventic_diwa_record(row) for row in driventic_source_rows]
    input_records.extend(driventic_records)
    mercedes_dtfr_source_rows = [json.loads(line) for line in MERCEDES_DTFR_JSONL.read_text(encoding="utf-8").splitlines() if line]
    mercedes_dtfr_records = [mercedes_dtfr_record(row) for row in mercedes_dtfr_source_rows]
    input_records.extend(mercedes_dtfr_records)
    mercedes_bevo_source_rows = [json.loads(line) for line in MERCEDES_BEVO_JSONL.read_text(encoding="utf-8").splitlines() if line]
    mercedes_bevo_records = [mercedes_bevo_record(row) for row in mercedes_bevo_source_rows]
    existing_by_name = defaultdict(list)
    for row in input_records:
        existing_by_name[(normalize(row["brand"]), row["product_name_normalized"], row["family_code"])].append(row)
    mercedes_bevo_product_key = {}
    mercedes_bevo_added_rows = 0
    mercedes_bevo_matched_rows = 0
    for raw, source_record in zip(mercedes_bevo_source_rows, mercedes_bevo_records):
        key = (normalize(raw["company"]), normalize(raw["product_name"]), raw["family_code"])
        matches = existing_by_name.get(key, [])
        if matches:
            target = matches[0]
            merge_mercedes_bevo_evidence(target, source_record, raw)
            mercedes_bevo_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name[key].append(target)
            mercedes_bevo_added_rows += 1
        mercedes_bevo_product_key[raw["source_record_id"]] = target["canonical_key"]
    volvo_genuine_source_rows = [json.loads(line) for line in VOLVO_GENUINE_JSONL.read_text(encoding="utf-8").splitlines() if line]
    volvo_genuine_records = [volvo_genuine_record(row) for row in volvo_genuine_source_rows]
    input_records.extend(volvo_genuine_records)
    man_service_source_rows = [json.loads(line) for line in MAN_SERVICE_JSONL.read_text(encoding="utf-8").splitlines() if line]
    man_service_records = [man_service_record(row) for row in man_service_source_rows]
    existing_by_name_family = defaultdict(list)
    for row in input_records:
        existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
    man_service_product_key = {}
    man_service_added_rows = 0
    man_service_matched_rows = 0
    man_service_review_keys = []
    for raw, source_record in zip(man_service_source_rows, man_service_records):
        matches = [
            row for row in existing_by_name_family[(normalize(raw["product_name"]), raw["family_code"])]
            if brand_tokens_overlap(raw["brand"], row["brand"])
        ]
        if len(matches) == 1:
            target = matches[0]
            merge_man_recommendation_evidence(target, raw)
            man_service_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(target["product_name_normalized"], target["family_code"])].append(target)
            man_service_added_rows += 1
            if len(matches) > 1:
                man_service_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
        man_service_product_key[raw["source_record_id"]] = target["canonical_key"]
    liqui_moly_source_rows = [json.loads(line) for line in LIQUI_MOLY_2020_JSONL.read_text(encoding="utf-8").splitlines() if line]
    liqui_moly_records = [liqui_moly_catalog_record(row) for row in liqui_moly_source_rows]
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("LIQUI MOLY", row["brand"]):
            identity_name = liqui_moly_identity_name(row["product_name_raw"])
            existing_by_name_family[(identity_name, row["family_code"])].append(row)
            existing_by_name[identity_name].append(row)
    liqui_moly_product_key = {}
    liqui_moly_added_rows = liqui_moly_matched_rows = 0
    liqui_moly_review_keys, liqui_moly_family_conflict_keys = [], []
    for raw, source_record in zip(liqui_moly_source_rows, liqui_moly_records):
        name = liqui_moly_identity_name(raw["product_name"])
        matches = [row for row in existing_by_name_family[(name, raw["family_code"])] if brand_tokens_overlap("LIQUI MOLY", row["brand"])]
        if len(matches) == 1:
            target = matches[0]
            merge_liqui_moly_evidence(target, source_record, raw)
            liqui_moly_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if brand_tokens_overlap("LIQUI MOLY", row["brand"]) and row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            liqui_moly_added_rows += 1
            if len(matches) > 1:
                liqui_moly_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                liqui_moly_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        liqui_moly_product_key[raw["source_record_id"]] = target["canonical_key"]
    liqui_moly_current_source_rows = [json.loads(line) for line in LIQUI_MOLY_CURRENT_JSONL.read_text(encoding="utf-8").splitlines() if line]
    liqui_moly_current_records = [liqui_moly_current_record(row) for row in liqui_moly_current_source_rows]
    input_by_key = {row["canonical_key"]: row for row in input_records}
    liqui_moly_current_product_key = {}
    liqui_moly_current_added_rows = 0
    liqui_moly_current_matched_rows = 0
    liqui_moly_current_review_keys = []
    for raw, source_record in zip(liqui_moly_current_source_rows, liqui_moly_current_records):
        candidate_keys = sorted({
            liqui_moly_product_key[candidate["source_record_id"]]
            for candidate in raw["historical_candidates"]
            if candidate["source_record_id"] in liqui_moly_product_key
        })
        if len(candidate_keys) == 1 and input_by_key[candidate_keys[0]]["family_code"] == raw["family_code"]:
            target = input_by_key[candidate_keys[0]]
            merge_liqui_moly_current_evidence(target, source_record, raw)
            liqui_moly_current_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            input_by_key[target["canonical_key"]] = target
            liqui_moly_current_added_rows += 1
            if candidate_keys:
                liqui_moly_current_review_keys.append((target["canonical_key"], candidate_keys))
        liqui_moly_current_product_key[raw["source_record_id"]] = target["canonical_key"]
    anp_brazil_source_rows = [json.loads(line) for line in ANP_BRAZIL_JSONL.read_text(encoding="utf-8").splitlines() if line]
    anp_brazil_records = [anp_brazil_record(row) for row in anp_brazil_source_rows]
    input_records.extend(anp_brazil_records)
    indonesia_npt_source_rows = [json.loads(line) for line in INDONESIA_NPT_JSONL.read_text(encoding="utf-8").splitlines() if line]
    indonesia_npt_records = [indonesia_npt_record(row) for row in indonesia_npt_source_rows]
    dla_qpd_source_rows = [json.loads(line) for line in DLA_QPD_JSONL.read_text(encoding="utf-8").splitlines() if line]
    dla_qpd_records = [dla_qpd_record(row) for row in dla_qpd_source_rows]
    fuchs_india_source_rows = [json.loads(line) for line in FUCHS_INDIA_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_india_records = [fuchs_catalog_record(row, "FUCHS_INDIA_PRODUCT_FINDER", "India") for row in fuchs_india_source_rows]
    existing_by_name_family = defaultdict(list)
    for row in input_records:
        existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
    fuchs_india_product_key = {}
    fuchs_india_added_rows = 0
    fuchs_india_matched_rows = 0
    fuchs_india_review_keys = []
    for raw, source_record in zip(fuchs_india_source_rows, fuchs_india_records):
        matches = [
            row for row in existing_by_name_family[(normalize(raw["product_name"]), raw["family_code"])]
            if brand_tokens_overlap("FUCHS", row["brand"])
        ]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_india_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(target["product_name_normalized"], target["family_code"])].append(target)
            fuchs_india_added_rows += 1
            if len(matches) > 1:
                fuchs_india_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
        fuchs_india_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_us_source_rows = [json.loads(line) for line in FUCHS_US_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_us_records = [fuchs_catalog_record(row, "FUCHS_US_PRODUCT_FINDER", "USA") for row in fuchs_us_source_rows]
    india_name_families = defaultdict(set)
    for row in fuchs_india_source_rows:
        india_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_cross_market_exact_name_family_rows = sum(
        row["family_code"] in india_name_families[normalize(row["product_name"])]
        for row in fuchs_us_source_rows
    )
    fuchs_cross_market_family_conflict_rows = sum(
        bool(india_name_families[normalize(row["product_name"])])
        and row["family_code"] not in india_name_families[normalize(row["product_name"])]
        for row in fuchs_us_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_us_product_key = {}
    fuchs_us_added_rows = 0
    fuchs_us_matched_rows = 0
    fuchs_us_review_keys = []
    fuchs_us_family_conflict_keys = []
    for raw, source_record in zip(fuchs_us_source_rows, fuchs_us_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_us_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_us_added_rows += 1
            if len(matches) > 1:
                fuchs_us_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_us_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_us_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_germany_source_rows = [json.loads(line) for line in FUCHS_GERMANY_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_germany_records = [fuchs_catalog_record(row, "FUCHS_GERMANY_PRODUCT_FINDER", "Germany") for row in fuchs_germany_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_germany_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_germany_source_rows
    )
    fuchs_germany_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_germany_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_germany_product_key = {}
    fuchs_germany_added_rows = 0
    fuchs_germany_matched_rows = 0
    fuchs_germany_review_keys = []
    fuchs_germany_family_conflict_keys = []
    for raw, source_record in zip(fuchs_germany_source_rows, fuchs_germany_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_germany_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_germany_added_rows += 1
            if len(matches) > 1:
                fuchs_germany_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_germany_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_germany_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_poland_source_rows = [json.loads(line) for line in FUCHS_POLAND_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_poland_records = [fuchs_catalog_record(row, "FUCHS_POLAND_PRODUCT_FINDER", "Poland") for row in fuchs_poland_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_poland_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_poland_source_rows
    )
    fuchs_poland_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_poland_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_poland_product_key = {}
    fuchs_poland_added_rows = 0
    fuchs_poland_matched_rows = 0
    fuchs_poland_review_keys = []
    fuchs_poland_family_conflict_keys = []
    for raw, source_record in zip(fuchs_poland_source_rows, fuchs_poland_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_poland_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_poland_added_rows += 1
            if len(matches) > 1:
                fuchs_poland_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_poland_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_poland_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_italy_source_rows = [json.loads(line) for line in FUCHS_ITALY_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_italy_records = [fuchs_catalog_record(row, "FUCHS_ITALY_PRODUCT_FINDER", "Italy") for row in fuchs_italy_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_italy_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_italy_source_rows
    )
    fuchs_italy_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_italy_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_italy_product_key = {}
    fuchs_italy_added_rows = 0
    fuchs_italy_matched_rows = 0
    fuchs_italy_review_keys = []
    fuchs_italy_family_conflict_keys = []
    for raw, source_record in zip(fuchs_italy_source_rows, fuchs_italy_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_italy_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_italy_added_rows += 1
            if len(matches) > 1:
                fuchs_italy_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_italy_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_italy_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_sweden_source_rows = [json.loads(line) for line in FUCHS_SWEDEN_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_sweden_records = [fuchs_catalog_record(row, "FUCHS_SWEDEN_PRODUCT_FINDER", "Sweden") for row in fuchs_sweden_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows + fuchs_italy_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_sweden_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])] for row in fuchs_sweden_source_rows
    )
    fuchs_sweden_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_sweden_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_sweden_product_key = {}
    fuchs_sweden_added_rows = 0
    fuchs_sweden_matched_rows = 0
    fuchs_sweden_review_keys = []
    fuchs_sweden_family_conflict_keys = []
    for raw, source_record in zip(fuchs_sweden_source_rows, fuchs_sweden_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_sweden_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_sweden_added_rows += 1
            if len(matches) > 1:
                fuchs_sweden_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_sweden_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_sweden_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_spain_source_rows = [json.loads(line) for line in FUCHS_SPAIN_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_spain_records = [fuchs_catalog_record(row, "FUCHS_SPAIN_PRODUCT_FINDER", "Spain") for row in fuchs_spain_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows + fuchs_italy_source_rows + fuchs_sweden_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_spain_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])] for row in fuchs_spain_source_rows
    )
    fuchs_spain_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_spain_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_spain_product_key = {}
    fuchs_spain_added_rows = 0
    fuchs_spain_matched_rows = 0
    fuchs_spain_review_keys = []
    fuchs_spain_family_conflict_keys = []
    for raw, source_record in zip(fuchs_spain_source_rows, fuchs_spain_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_spain_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_spain_added_rows += 1
            if len(matches) > 1:
                fuchs_spain_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_spain_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_spain_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_france_source_rows = [json.loads(line) for line in FUCHS_FRANCE_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_france_records = [fuchs_catalog_record(row, "FUCHS_FRANCE_PRODUCT_FINDER", "France") for row in fuchs_france_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows + fuchs_italy_source_rows + fuchs_sweden_source_rows + fuchs_spain_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_france_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])] for row in fuchs_france_source_rows
    )
    fuchs_france_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_france_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_france_product_key = {}
    fuchs_france_added_rows = 0
    fuchs_france_matched_rows = 0
    fuchs_france_review_keys = []
    fuchs_france_family_conflict_keys = []
    for raw, source_record in zip(fuchs_france_source_rows, fuchs_france_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_france_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_france_added_rows += 1
            if len(matches) > 1:
                fuchs_france_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_france_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_france_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_turkey_source_rows = [json.loads(line) for line in FUCHS_TURKEY_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_turkey_records = [fuchs_catalog_record(row, "FUCHS_TURKEY_PRODUCT_FINDER", "Turkey") for row in fuchs_turkey_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows + fuchs_italy_source_rows + fuchs_sweden_source_rows + fuchs_spain_source_rows + fuchs_france_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_turkey_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])] for row in fuchs_turkey_source_rows
    )
    fuchs_turkey_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_turkey_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_turkey_product_key = {}
    fuchs_turkey_added_rows = 0
    fuchs_turkey_matched_rows = 0
    fuchs_turkey_review_keys = []
    fuchs_turkey_family_conflict_keys = []
    for raw, source_record in zip(fuchs_turkey_source_rows, fuchs_turkey_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_turkey_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_turkey_added_rows += 1
            if len(matches) > 1:
                fuchs_turkey_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_turkey_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_turkey_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_canada_source_rows = [json.loads(line) for line in FUCHS_CANADA_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_canada_records = [fuchs_catalog_record(row, "FUCHS_CANADA_PRODUCT_FINDER", "Canada") for row in fuchs_canada_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows + fuchs_italy_source_rows + fuchs_sweden_source_rows + fuchs_spain_source_rows + fuchs_france_source_rows + fuchs_turkey_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_canada_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])] for row in fuchs_canada_source_rows
    )
    fuchs_canada_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_canada_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_canada_product_key = {}
    fuchs_canada_added_rows = 0
    fuchs_canada_matched_rows = 0
    fuchs_canada_review_keys = []
    fuchs_canada_family_conflict_keys = []
    for raw, source_record in zip(fuchs_canada_source_rows, fuchs_canada_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_canada_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_canada_added_rows += 1
            if len(matches) > 1:
                fuchs_canada_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_canada_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_canada_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_china_source_rows = [json.loads(line) for line in FUCHS_CHINA_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_china_records = [fuchs_catalog_record(row, "FUCHS_CHINA_PRODUCT_FINDER", "China") for row in fuchs_china_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows + fuchs_italy_source_rows + fuchs_sweden_source_rows + fuchs_spain_source_rows + fuchs_france_source_rows + fuchs_turkey_source_rows + fuchs_canada_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_china_cross_market_exact_name_family_rows = sum(
        row["family_code"] in prior_market_name_families[normalize(row["product_name"])] for row in fuchs_china_source_rows
    )
    fuchs_china_cross_market_family_conflict_rows = sum(
        bool(prior_market_name_families[normalize(row["product_name"])])
        and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])]
        for row in fuchs_china_source_rows
    )
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_china_product_key = {}
    fuchs_china_added_rows = 0
    fuchs_china_matched_rows = 0
    fuchs_china_review_keys = []
    fuchs_china_family_conflict_keys = []
    for raw, source_record in zip(fuchs_china_source_rows, fuchs_china_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_china_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_china_added_rows += 1
            if len(matches) > 1:
                fuchs_china_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_china_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_china_product_key[raw["source_record_id"]] = target["canonical_key"]
    fuchs_czech_source_rows = [json.loads(line) for line in FUCHS_CZECH_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_czech_records = [fuchs_catalog_record(row, "FUCHS_CZECH_PRODUCT_FINDER", "Czech Republic") for row in fuchs_czech_source_rows]
    prior_market_name_families = defaultdict(set)
    for row in fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows + fuchs_italy_source_rows + fuchs_sweden_source_rows + fuchs_spain_source_rows + fuchs_france_source_rows + fuchs_turkey_source_rows + fuchs_canada_source_rows + fuchs_china_source_rows:
        prior_market_name_families[normalize(row["product_name"])].add(row["family_code"])
    fuchs_czech_cross_market_exact_name_family_rows = sum(row["family_code"] in prior_market_name_families[normalize(row["product_name"])] for row in fuchs_czech_source_rows)
    fuchs_czech_cross_market_family_conflict_rows = sum(bool(prior_market_name_families[normalize(row["product_name"])]) and row["family_code"] not in prior_market_name_families[normalize(row["product_name"])] for row in fuchs_czech_source_rows)
    existing_by_name_family = defaultdict(list)
    existing_by_name = defaultdict(list)
    for row in input_records:
        if brand_tokens_overlap("FUCHS", row["brand"]):
            existing_by_name_family[(row["product_name_normalized"], row["family_code"])].append(row)
            existing_by_name[row["product_name_normalized"]].append(row)
    fuchs_czech_product_key = {}
    fuchs_czech_added_rows = fuchs_czech_matched_rows = 0
    fuchs_czech_review_keys, fuchs_czech_family_conflict_keys = [], []
    for raw, source_record in zip(fuchs_czech_source_rows, fuchs_czech_records):
        name = normalize(raw["product_name"])
        matches = existing_by_name_family[(name, raw["family_code"])]
        if len(matches) == 1:
            target = matches[0]
            merge_fuchs_catalog_evidence(target, source_record, raw)
            fuchs_czech_matched_rows += 1
        else:
            target = source_record
            input_records.append(target)
            existing_by_name_family[(name, raw["family_code"])].append(target)
            other_family_matches = [row for row in existing_by_name[name] if row["family_code"] != raw["family_code"]]
            existing_by_name[name].append(target)
            fuchs_czech_added_rows += 1
            if len(matches) > 1:
                fuchs_czech_review_keys.append((target["canonical_key"], [row["canonical_key"] for row in matches]))
            if other_family_matches:
                fuchs_czech_family_conflict_keys.append((target["canonical_key"], [row["canonical_key"] for row in other_family_matches]))
        fuchs_czech_product_key[raw["source_record_id"]] = target["canonical_key"]
    prior_fuchs_rows = fuchs_india_source_rows + fuchs_us_source_rows + fuchs_germany_source_rows + fuchs_poland_source_rows + fuchs_italy_source_rows + fuchs_sweden_source_rows + fuchs_spain_source_rows + fuchs_france_source_rows + fuchs_turkey_source_rows + fuchs_canada_source_rows + fuchs_china_source_rows + fuchs_czech_source_rows
    fuchs_mexico_source_rows = [json.loads(line) for line in FUCHS_MEXICO_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_mexico = integrate_fuchs_market(input_records, fuchs_mexico_source_rows, "FUCHS_MEXICO_PRODUCT_FINDER", "Mexico", prior_fuchs_rows)
    fuchs_mexico_product_key = fuchs_mexico["product_key"]
    fuchs_mexico_added_rows, fuchs_mexico_matched_rows = fuchs_mexico["added"], fuchs_mexico["matched"]
    fuchs_mexico_review_keys, fuchs_mexico_family_conflict_keys = fuchs_mexico["review_keys"], fuchs_mexico["family_conflict_keys"]
    fuchs_mexico_cross_market_exact_name_family_rows, fuchs_mexico_cross_market_family_conflict_rows = fuchs_mexico["exact"], fuchs_mexico["conflicts"]
    fuchs_south_africa_source_rows = [json.loads(line) for line in FUCHS_SOUTH_AFRICA_JSONL.read_text(encoding="utf-8").splitlines() if line]
    fuchs_south_africa = integrate_fuchs_market(input_records, fuchs_south_africa_source_rows, "FUCHS_SOUTH_AFRICA_PRODUCT_FINDER", "South Africa", prior_fuchs_rows + fuchs_mexico_source_rows)
    fuchs_south_africa_product_key = fuchs_south_africa["product_key"]
    fuchs_south_africa_added_rows, fuchs_south_africa_matched_rows = fuchs_south_africa["added"], fuchs_south_africa["matched"]
    fuchs_south_africa_review_keys, fuchs_south_africa_family_conflict_keys = fuchs_south_africa["review_keys"], fuchs_south_africa["family_conflict_keys"]
    fuchs_south_africa_cross_market_exact_name_family_rows, fuchs_south_africa_cross_market_family_conflict_rows = fuchs_south_africa["exact"], fuchs_south_africa["conflicts"]
    aichilon_products, aichilon_packages, exclusions = aichilon_seed()
    existing_by_name = defaultdict(list)
    for row in input_records:
        existing_by_name[(normalize(row["brand"]), row["product_name_normalized"])].append(row)
    aichilon_product_key = {}
    aichilon_new_rows = 0
    aichilon_matched_rows = 0
    for raw in aichilon_products:
        key = (normalize(raw["brand"]), normalize(raw["name"]))
        matches = existing_by_name.get(key, [])
        if matches:
            target = matches[0]
            aichilon_matched_rows += 1
        else:
            target = canonical_record(raw)
            target["lifecycle_status"] = "active" if raw["is_active"] else "archived"
            input_records.append(target)
            existing_by_name[key].append(target)
            aichilon_new_rows += 1
        aichilon_product_key[int(raw["source_number"])] = target["canonical_key"]
    # Keep regulatory registry rows independent from the sequential FUCHS market
    # consolidation. Cross-source identities remain review candidates and cannot
    # perturb already established manufacturer-market deduplication decisions.
    input_records.extend(indonesia_npt_records)
    input_records.extend(dla_qpd_records)
    records, candidates = deduplicate(input_records)
    canonical_by_key = {row["canonical_key"]: row for row in records}
    for source_key, match_keys in blue_angel_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "blue_angel_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995, "decision": "review_blue_angel_multi_registry_identity",
            })
    for source_key, match_keys in blue_angel_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "same_blue_angel_product_name_but_conflicting_professional_family_across_registries",
                "score": 0.75, "decision": "keep_separate_blue_angel_family_conflict",
            })
    for source_key, match_keys in man_service_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "exact_product_name_and_family_with_probable_brand_owner_alias",
                "score": 0.99,
                "decision": "review_brand_alias_identity",
            })
    for source_key, match_keys in liqui_moly_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({"product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"], "reason": "liqui_moly_2020_exact_product_name_and_family_with_multiple_existing_registry_records", "score": 0.995, "decision": "review_liqui_moly_multi_registry_identity"})
    for source_key, match_keys in liqui_moly_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({"product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"], "reason": "same_liqui_moly_product_name_but_conflicting_professional_family", "score": 0.70, "decision": "keep_separate_liqui_moly_family_conflict"})
    for source_key, match_keys in liqui_moly_current_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "current_liqui_moly_product_links_to_multiple_2020_catalog_identities_by_name_or_article_sku",
                "score": 0.98,
                "decision": "review_liqui_moly_current_multiple_historical_candidates",
            })
    for source_key, match_keys in fuchs_india_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "fuchs_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995,
                "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_us_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "fuchs_us_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995,
                "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_us_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70,
                "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_germany_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "fuchs_germany_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995,
                "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_germany_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70,
                "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_poland_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "fuchs_poland_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995,
                "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_poland_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70,
                "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_italy_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "fuchs_italy_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995,
                "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_italy_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"],
                "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70,
                "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_sweden_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "fuchs_sweden_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995, "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_sweden_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70, "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_spain_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "fuchs_spain_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995, "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_spain_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70, "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_france_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "fuchs_france_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995, "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_france_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70, "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_turkey_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "fuchs_turkey_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995, "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_turkey_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70, "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_canada_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "fuchs_canada_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995, "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_canada_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70, "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_china_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "fuchs_china_exact_product_name_and_family_with_multiple_existing_registry_records",
                "score": 0.995, "decision": "review_fuchs_multi_registry_identity",
            })
    for source_key, match_keys in fuchs_china_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({
                "product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"],
                "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets",
                "score": 0.70, "decision": "keep_separate_fuchs_market_family_conflict",
            })
    for source_key, match_keys in fuchs_czech_review_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({"product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"], "reason": "fuchs_czech_exact_product_name_and_family_with_multiple_existing_registry_records", "score": 0.995, "decision": "review_fuchs_multi_registry_identity"})
    for source_key, match_keys in fuchs_czech_family_conflict_keys:
        source_product = canonical_by_key[source_key]
        for match_key in match_keys:
            match_product = canonical_by_key[match_key]
            candidates.append({"product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"], "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets", "score": 0.70, "decision": "keep_separate_fuchs_market_family_conflict"})
    for market_slug, review_keys, conflict_keys in [
        ("mexico", fuchs_mexico_review_keys, fuchs_mexico_family_conflict_keys),
        ("south_africa", fuchs_south_africa_review_keys, fuchs_south_africa_family_conflict_keys),
    ]:
        for source_key, match_keys in review_keys:
            source_product = canonical_by_key[source_key]
            for match_key in match_keys:
                match_product = canonical_by_key[match_key]
                candidates.append({"product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"], "reason": f"fuchs_{market_slug}_exact_product_name_and_family_with_multiple_existing_registry_records", "score": 0.995, "decision": "review_fuchs_multi_registry_identity"})
        for source_key, match_keys in conflict_keys:
            source_product = canonical_by_key[source_key]
            for match_key in match_keys:
                match_product = canonical_by_key[match_key]
                candidates.append({"product_id_a": match_product["product_id"], "product_id_b": source_product["product_id"], "reason": "same_fuchs_product_name_but_conflicting_professional_family_across_markets", "score": 0.70, "decision": "keep_separate_fuchs_market_family_conflict"})
    source_links = [{
        "product_id": row["product_id"], "source_id": row["source_id"], "source_record_id": row["source_record_id"],
        "source_row": row["source_row"], "relation": "primary_seed_record",
    } for row in records]
    source_link_keys = {(link["product_id"], link["source_id"], link["source_record_id"]) for link in source_links}
    for raw in aichilon_products:
        target = canonical_by_key[aichilon_product_key[int(raw["source_number"])]]
        link = {
            "product_id": target["product_id"], "source_id": "aichilon-internal", "source_record_id": text(raw["source_number"]),
            "source_row": None, "relation": "internal_product_master",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw, normalized_row in zip(jaso_source_rows, jaso_records):
        target = canonical_by_key[normalized_row["canonical_key"]]
        link = {
            "product_id": target["product_id"], "source_id": raw["source_id"],
            "source_record_id": text(raw["source_row_number"]), "source_row": raw["source_row_number"],
            "relation": "official_filed_registry",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw, normalized_row in zip(licensed_source_rows, licensed_records):
        target = canonical_by_key[normalized_row["canonical_key"]]
        link = {
            "product_id": target["product_id"], "source_id": raw["source_id"],
            "source_record_id": text(raw["source_record_id"]), "source_row": raw["source_row_number"],
            "relation": "official_licensed_registry",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in blue_angel_source_rows:
        target = canonical_by_key[blue_angel_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "BLUE_ANGEL_DE_UZ_178",
            "source_record_id": raw["source_record_id"], "source_row": raw["source_row_numbers"][0],
            "relation": "official_ecolabel_product_registry",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw, normalized_row in zip(biopreferred_source_rows, biopreferred_records):
        target = canonical_by_key[normalized_row["canonical_key"]]
        link = {
            "product_id": target["product_id"], "source_id": "usda-biopreferred",
            "source_record_id": text(raw["product_id"]), "source_row": None,
            "relation": "official_government_program_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw, normalized_row in zip(zf_source_rows, zf_records):
        target = canonical_by_key[normalized_row["canonical_key"]]
        link = {
            "product_id": target["product_id"], "source_id": "ZF_TE_ML",
            "source_record_id": text(raw["approval_number"]), "source_row": None,
            "relation": "official_oem_approval_registry",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw, normalized_row in zip(allison_source_rows, allison_records):
        target = canonical_by_key[normalized_row["canonical_key"]]
        link = {
            "product_id": target["product_id"], "source_id": "ALLISON_APPROVED_FLUIDS",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_oem_approval_registry",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw, normalized_row in zip(driventic_source_rows, driventic_records):
        target = canonical_by_key[normalized_row["canonical_key"]]
        link = {
            "product_id": target["product_id"], "source_id": "DRIVENTIC_DIWA_APPROVED_OILS",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_oem_approval_registry",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw, normalized_row in zip(mercedes_dtfr_source_rows, mercedes_dtfr_records):
        target = canonical_by_key[normalized_row["canonical_key"]]
        link = {
            "product_id": target["product_id"], "source_id": "MERCEDES_DTFR_APPROVED_FLUIDS",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_oem_approval_registry",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in mercedes_bevo_source_rows:
        target = canonical_by_key[mercedes_bevo_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "MERCEDES_BENZ_BEVO_APPROVED_FLUIDS",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_oem_approval_registry",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw, normalized_row in zip(volvo_genuine_source_rows, volvo_genuine_records):
        target = canonical_by_key[normalized_row["canonical_key"]]
        link = {
            "product_id": target["product_id"], "source_id": "VOLVO_GENUINE_FLUIDS",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in man_service_source_rows:
        target = canonical_by_key[man_service_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "MAN_CURRENT_SERVICE_PRODUCTS",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_oem_service_recommendation",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in liqui_moly_source_rows:
        target = canonical_by_key[liqui_moly_product_key[raw["source_record_id"]]]
        link = {"product_id": target["product_id"], "source_id": "LIQUI_MOLY_2020_PRODUCT_CATALOG", "source_record_id": raw["source_record_id"], "source_row": None, "relation": "historical_official_manufacturer_product_catalog"}
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in liqui_moly_current_source_rows:
        target = canonical_by_key[liqui_moly_current_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"],
            "source_id": "LIQUI_MOLY_CURRENT_OPENAPI",
            "source_record_id": raw["source_record_id"],
            "source_row": None,
            "relation": "current_official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_india_source_rows:
        target = canonical_by_key[fuchs_india_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_INDIA_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_us_source_rows:
        target = canonical_by_key[fuchs_us_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_US_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_germany_source_rows:
        target = canonical_by_key[fuchs_germany_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_GERMANY_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_poland_source_rows:
        target = canonical_by_key[fuchs_poland_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_POLAND_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_italy_source_rows:
        target = canonical_by_key[fuchs_italy_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_ITALY_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_sweden_source_rows:
        target = canonical_by_key[fuchs_sweden_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_SWEDEN_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_spain_source_rows:
        target = canonical_by_key[fuchs_spain_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_SPAIN_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_france_source_rows:
        target = canonical_by_key[fuchs_france_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_FRANCE_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_turkey_source_rows:
        target = canonical_by_key[fuchs_turkey_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_TURKEY_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_canada_source_rows:
        target = canonical_by_key[fuchs_canada_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_CANADA_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_china_source_rows:
        target = canonical_by_key[fuchs_china_product_key[raw["source_record_id"]]]
        link = {
            "product_id": target["product_id"], "source_id": "FUCHS_CHINA_PRODUCT_FINDER",
            "source_record_id": raw["source_record_id"], "source_row": None,
            "relation": "official_manufacturer_product_catalog",
        }
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for raw in fuchs_czech_source_rows:
        target = canonical_by_key[fuchs_czech_product_key[raw["source_record_id"]]]
        link = {"product_id": target["product_id"], "source_id": "FUCHS_CZECH_PRODUCT_FINDER", "source_record_id": raw["source_record_id"], "source_row": None, "relation": "official_manufacturer_product_catalog"}
        link_key = (link["product_id"], link["source_id"], link["source_record_id"])
        if link_key not in source_link_keys:
            source_links.append(link)
            source_link_keys.add(link_key)
    for source_rows, product_key, source_id in [
        (fuchs_mexico_source_rows, fuchs_mexico_product_key, "FUCHS_MEXICO_PRODUCT_FINDER"),
        (fuchs_south_africa_source_rows, fuchs_south_africa_product_key, "FUCHS_SOUTH_AFRICA_PRODUCT_FINDER"),
    ]:
        for raw in source_rows:
            target = canonical_by_key[product_key[raw["source_record_id"]]]
            link = {"product_id": target["product_id"], "source_id": source_id, "source_record_id": raw["source_record_id"], "source_row": None, "relation": "official_manufacturer_product_catalog"}
            link_key = (link["product_id"], link["source_id"], link["source_record_id"])
            if link_key not in source_link_keys:
                source_links.append(link)
                source_link_keys.add(link_key)
    offers = []
    for package in aichilon_packages:
        canonical_key = aichilon_product_key.get(int(package["source_product_id"]))
        if not canonical_key:
            continue
        target = canonical_by_key[canonical_key]
        offers.append({
            "offer_id": f"AICHILON-PACKAGE-{package['package_id']}",
            "product_id": target["product_id"],
            "market": "UZ",
            "package_name": text(package["package_name"]),
            "unit": text(package["unit"]),
            "quantity_per_package": package["quantity_per_package"],
            "weight_kg": package["weight_kg"],
            "density_kg_per_l": package["density_kg_per_l"],
            "lifecycle_status": "active" if package["is_active"] else "archived",
            "archive_type": text(package["archive_type"]),
            "archive_reason": text(package["archive_reason"]),
            "source_id": "aichilon-internal",
            "source_record_id": text(package["package_id"]),
        })
    for raw in liqui_moly_current_source_rows:
        target = canonical_by_key[liqui_moly_current_product_key[raw["source_record_id"]]]
        for article in raw["articles"]:
            package_match = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)\s*([A-Za-z]+)", article["content"])
            quantity = float(package_match.group(1).replace(",", ".")) if package_match else None
            unit = package_match.group(2).lower() if package_match else article["content"]
            weight_kg = None
            if quantity is not None and unit == "kg":
                weight_kg = quantity
            elif quantity is not None and unit == "g":
                weight_kg = quantity / 1000
            offers.append({
                "offer_id": f"LIQUI-MOLY-GB-{article['sku']}",
                "product_id": target["product_id"],
                "market": "GB",
                "package_name": " / ".join(value for value in [article["content"], article["container_type"]] if value),
                "unit": unit,
                "quantity_per_package": quantity,
                "weight_kg": weight_kg,
                "density_kg_per_l": None,
                "lifecycle_status": "listed_current_catalog",
                "archive_type": "",
                "archive_reason": "",
                "source_id": "LIQUI_MOLY_CURRENT_OPENAPI",
                "source_record_id": article["sku"],
            })
    issues = quality_issues(records)
    issues.extend({
        "product_id": row["product_id"],
        "issue_code": "source_registration_number_missing",
        "severity": "high",
        "field": "INDONESIA_NPT_REGISTRATION_NUMBER",
        "value": row["specifications"]["indonesia_npt_registration_number_raw"],
        "expected": "Published NPT registration number",
        "action": "Retain as product-name evidence, but do not treat it as a verified registered product until the authority corrects the source row.",
    } for row in records if row["evidence_status"] == "official_government_registry_source_data_issue")
    issues.extend({
        "product_id": row["product_id"],
        "issue_code": "dla_qpd_lifecycle_restriction",
        "severity": "high" if row["lifecycle_status"] in {"stop_ship", "sam_inactive_source_review"} else "medium",
        "field": "DLA_QPD_QUALIFICATION_STATUS",
        "value": row["lifecycle_status"],
        "expected": "qualified_source_certified",
        "action": "Retain as official qualification history, but review the live QPD status before sourcing or declaring current equivalence.",
    } for row in records if row["evidence_status"] == "official_government_qualified_product_registry" and row["lifecycle_status"] != "qualified_source_certified")
    run_id = f"seed-{SNAPSHOT_DATE}"
    JSONL_OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    compress_jsonl()
    report = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "snapshot_date": SNAPSHOT_DATE,
        "status": "seed_only_world_catalog_incomplete",
        "input_rows": len(input_records),
        "normalized_input_sha256": hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        "jaso_normalized_input_sha256": hashlib.sha256(JASO_JSONL.read_bytes()).hexdigest(),
        "official_licensed_input_sha256": hashlib.sha256(LICENSED_JSONL.read_bytes()).hexdigest(),
        "blue_angel_input_sha256": hashlib.sha256(BLUE_ANGEL_JSONL.read_bytes()).hexdigest(),
        "usda_biopreferred_input_sha256": hashlib.sha256(USDA_BIOPREFERRED_JSONL.read_bytes()).hexdigest(),
        "zf_te_ml_input_sha256": hashlib.sha256(ZF_TE_ML_JSONL.read_bytes()).hexdigest(),
        "allison_input_sha256": hashlib.sha256(ALLISON_JSONL.read_bytes()).hexdigest(),
        "driventic_diwa_input_sha256": hashlib.sha256(DRIVENTIC_DIWA_JSONL.read_bytes()).hexdigest(),
        "mercedes_dtfr_input_sha256": hashlib.sha256(MERCEDES_DTFR_JSONL.read_bytes()).hexdigest(),
        "mercedes_bevo_input_sha256": hashlib.sha256(MERCEDES_BEVO_JSONL.read_bytes()).hexdigest(),
        "volvo_genuine_input_sha256": hashlib.sha256(VOLVO_GENUINE_JSONL.read_bytes()).hexdigest(),
        "man_service_input_sha256": hashlib.sha256(MAN_SERVICE_JSONL.read_bytes()).hexdigest(),
        "liqui_moly_2020_input_sha256": hashlib.sha256(LIQUI_MOLY_2020_JSONL.read_bytes()).hexdigest(),
        "liqui_moly_current_input_sha256": hashlib.sha256(LIQUI_MOLY_CURRENT_JSONL.read_bytes()).hexdigest(),
        "anp_brazil_input_sha256": hashlib.sha256(ANP_BRAZIL_JSONL.read_bytes()).hexdigest(),
        "indonesia_npt_input_sha256": hashlib.sha256(INDONESIA_NPT_JSONL.read_bytes()).hexdigest(),
        "dla_qpd_input_sha256": hashlib.sha256(DLA_QPD_JSONL.read_bytes()).hexdigest(),
        "fuchs_india_input_sha256": hashlib.sha256(FUCHS_INDIA_JSONL.read_bytes()).hexdigest(),
        "fuchs_us_input_sha256": hashlib.sha256(FUCHS_US_JSONL.read_bytes()).hexdigest(),
        "fuchs_germany_input_sha256": hashlib.sha256(FUCHS_GERMANY_JSONL.read_bytes()).hexdigest(),
        "fuchs_poland_input_sha256": hashlib.sha256(FUCHS_POLAND_JSONL.read_bytes()).hexdigest(),
        "fuchs_italy_input_sha256": hashlib.sha256(FUCHS_ITALY_JSONL.read_bytes()).hexdigest(),
        "fuchs_sweden_input_sha256": hashlib.sha256(FUCHS_SWEDEN_JSONL.read_bytes()).hexdigest(),
        "fuchs_spain_input_sha256": hashlib.sha256(FUCHS_SPAIN_JSONL.read_bytes()).hexdigest(),
        "fuchs_france_input_sha256": hashlib.sha256(FUCHS_FRANCE_JSONL.read_bytes()).hexdigest(),
        "fuchs_turkey_input_sha256": hashlib.sha256(FUCHS_TURKEY_JSONL.read_bytes()).hexdigest(),
        "fuchs_canada_input_sha256": hashlib.sha256(FUCHS_CANADA_JSONL.read_bytes()).hexdigest(),
        "fuchs_china_input_sha256": hashlib.sha256(FUCHS_CHINA_JSONL.read_bytes()).hexdigest(),
        "fuchs_czech_input_sha256": hashlib.sha256(FUCHS_CZECH_JSONL.read_bytes()).hexdigest(),
        "fuchs_mexico_input_sha256": hashlib.sha256(FUCHS_MEXICO_JSONL.read_bytes()).hexdigest(),
        "fuchs_south_africa_input_sha256": hashlib.sha256(FUCHS_SOUTH_AFRICA_JSONL.read_bytes()).hexdigest(),
        "canonical_rows": len(records),
        "brands": len({r["brand"] for r in records}),
        "families": dict(sorted(Counter(r["family_code"] for r in records).items())),
        "project_source_rows": sum(r["evidence_status"] == "project_source_row" for r in records),
        "legacy_rows_needing_evidence": sum(r["evidence_status"] == "legacy_needs_official_tds" for r in records),
        "internal_master_rows": sum(r["evidence_status"] == "internal_product_master" for r in records),
        "official_filed_registry_rows": sum(r["evidence_status"] == "official_filed_registry" for r in records),
        "official_licensed_registry_rows": sum(r["evidence_status"] == "official_licensed_registry" for r in records),
        "official_licensed_source_rows": len(licensed_source_rows),
        "blue_angel_source_rows": len(blue_angel_source_rows),
        "blue_angel_products_matched_to_existing": blue_angel_matched_rows,
        "blue_angel_products_added": blue_angel_added_rows,
        "official_ecolabel_product_registry_rows": sum(r["evidence_status"] == "official_ecolabel_product_registry" for r in records),
        "official_government_program_rows": sum(r["evidence_status"] == "official_government_program_catalog" for r in records),
        "official_government_regulatory_registry_rows": sum(r["evidence_status"] == "official_government_regulatory_registry" for r in records),
        "official_government_qualified_product_registry_rows": sum(r["evidence_status"] == "official_government_qualified_product_registry" for r in records),
        "usda_biopreferred_source_rows": len(biopreferred_source_rows),
        "anp_brazil_source_rows": len(anp_brazil_source_rows),
        "indonesia_npt_source_rows": len(indonesia_npt_source_rows),
        "indonesia_npt_rows_with_registration_value": sum(bool(row["registration_number"]) for row in indonesia_npt_source_rows),
        "indonesia_npt_rows_with_source_data_issue": sum(not row["registration_number"] for row in indonesia_npt_source_rows),
        "dla_qpd_source_rows": len(dla_qpd_source_rows),
        "dla_qpd_source_rows_by_source": dict(sorted(Counter(row["source_id"] for row in dla_qpd_source_rows).items())),
        "dla_qpd_lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in dla_qpd_source_rows).items())),
        "official_government_registry_source_data_issue_rows": sum(r["evidence_status"] == "official_government_registry_source_data_issue" for r in records),
        "official_oem_approval_rows": sum(r["evidence_status"] == "official_oem_approval_registry" for r in records),
        "official_manufacturer_catalog_rows": sum(r["evidence_status"] == "official_manufacturer_product_catalog" for r in records),
        "official_oem_service_recommendation_rows": sum(r["evidence_status"] == "official_oem_service_recommendation" for r in records),
        "zf_te_ml_source_rows": len(zf_source_rows),
        "allison_source_rows": len(allison_source_rows),
        "driventic_diwa_source_rows": len(driventic_source_rows),
        "mercedes_dtfr_source_rows": len(mercedes_dtfr_source_rows),
        "mercedes_bevo_source_rows": len(mercedes_bevo_source_rows),
        "mercedes_bevo_products_matched_to_existing": mercedes_bevo_matched_rows,
        "mercedes_bevo_products_added": mercedes_bevo_added_rows,
        "volvo_genuine_source_rows": len(volvo_genuine_source_rows),
        "man_service_source_rows": len(man_service_source_rows),
        "man_service_products_matched_to_existing": man_service_matched_rows,
        "man_service_products_added": man_service_added_rows,
        "liqui_moly_2020_source_rows": len(liqui_moly_source_rows),
        "liqui_moly_2020_products_matched_to_existing": liqui_moly_matched_rows,
        "liqui_moly_2020_products_added": liqui_moly_added_rows,
        "liqui_moly_current_source_rows": len(liqui_moly_current_source_rows),
        "liqui_moly_current_products_matched_to_2020": liqui_moly_current_matched_rows,
        "liqui_moly_current_products_added": liqui_moly_current_added_rows,
        "liqui_moly_current_article_skus": len({article["sku"] for row in liqui_moly_current_source_rows for article in row["articles"]}),
        "liqui_moly_current_lifecycle_assessments": dict(Counter(row["lifecycle_assessment"] for row in liqui_moly_current_source_rows)),
        "fuchs_india_source_rows": len(fuchs_india_source_rows),
        "fuchs_india_products_matched_to_existing": fuchs_india_matched_rows,
        "fuchs_india_products_added": fuchs_india_added_rows,
        "fuchs_us_source_rows": len(fuchs_us_source_rows),
        "fuchs_us_products_matched_to_existing": fuchs_us_matched_rows,
        "fuchs_us_products_added": fuchs_us_added_rows,
        "fuchs_cross_market_exact_name_family_rows": fuchs_cross_market_exact_name_family_rows,
        "fuchs_cross_market_family_conflict_rows": fuchs_cross_market_family_conflict_rows,
        "fuchs_germany_source_rows": len(fuchs_germany_source_rows),
        "fuchs_germany_products_matched_to_existing": fuchs_germany_matched_rows,
        "fuchs_germany_products_added": fuchs_germany_added_rows,
        "fuchs_germany_cross_market_exact_name_family_rows": fuchs_germany_cross_market_exact_name_family_rows,
        "fuchs_germany_cross_market_family_conflict_rows": fuchs_germany_cross_market_family_conflict_rows,
        "fuchs_poland_source_rows": len(fuchs_poland_source_rows),
        "fuchs_poland_products_matched_to_existing": fuchs_poland_matched_rows,
        "fuchs_poland_products_added": fuchs_poland_added_rows,
        "fuchs_poland_cross_market_exact_name_family_rows": fuchs_poland_cross_market_exact_name_family_rows,
        "fuchs_poland_cross_market_family_conflict_rows": fuchs_poland_cross_market_family_conflict_rows,
        "fuchs_italy_source_rows": len(fuchs_italy_source_rows),
        "fuchs_italy_products_matched_to_existing": fuchs_italy_matched_rows,
        "fuchs_italy_products_added": fuchs_italy_added_rows,
        "fuchs_italy_cross_market_exact_name_family_rows": fuchs_italy_cross_market_exact_name_family_rows,
        "fuchs_italy_cross_market_family_conflict_rows": fuchs_italy_cross_market_family_conflict_rows,
        "fuchs_sweden_source_rows": len(fuchs_sweden_source_rows),
        "fuchs_sweden_products_matched_to_existing": fuchs_sweden_matched_rows,
        "fuchs_sweden_products_added": fuchs_sweden_added_rows,
        "fuchs_sweden_cross_market_exact_name_family_rows": fuchs_sweden_cross_market_exact_name_family_rows,
        "fuchs_sweden_cross_market_family_conflict_rows": fuchs_sweden_cross_market_family_conflict_rows,
        "fuchs_spain_source_rows": len(fuchs_spain_source_rows),
        "fuchs_spain_products_matched_to_existing": fuchs_spain_matched_rows,
        "fuchs_spain_products_added": fuchs_spain_added_rows,
        "fuchs_spain_cross_market_exact_name_family_rows": fuchs_spain_cross_market_exact_name_family_rows,
        "fuchs_spain_cross_market_family_conflict_rows": fuchs_spain_cross_market_family_conflict_rows,
        "fuchs_france_source_rows": len(fuchs_france_source_rows),
        "fuchs_france_products_matched_to_existing": fuchs_france_matched_rows,
        "fuchs_france_products_added": fuchs_france_added_rows,
        "fuchs_france_cross_market_exact_name_family_rows": fuchs_france_cross_market_exact_name_family_rows,
        "fuchs_france_cross_market_family_conflict_rows": fuchs_france_cross_market_family_conflict_rows,
        "fuchs_turkey_source_rows": len(fuchs_turkey_source_rows),
        "fuchs_turkey_products_matched_to_existing": fuchs_turkey_matched_rows,
        "fuchs_turkey_products_added": fuchs_turkey_added_rows,
        "fuchs_turkey_cross_market_exact_name_family_rows": fuchs_turkey_cross_market_exact_name_family_rows,
        "fuchs_turkey_cross_market_family_conflict_rows": fuchs_turkey_cross_market_family_conflict_rows,
        "fuchs_canada_source_rows": len(fuchs_canada_source_rows),
        "fuchs_canada_products_matched_to_existing": fuchs_canada_matched_rows,
        "fuchs_canada_products_added": fuchs_canada_added_rows,
        "fuchs_canada_cross_market_exact_name_family_rows": fuchs_canada_cross_market_exact_name_family_rows,
        "fuchs_canada_cross_market_family_conflict_rows": fuchs_canada_cross_market_family_conflict_rows,
        "fuchs_china_source_rows": len(fuchs_china_source_rows),
        "fuchs_china_products_matched_to_existing": fuchs_china_matched_rows,
        "fuchs_china_products_added": fuchs_china_added_rows,
        "fuchs_china_cross_market_exact_name_family_rows": fuchs_china_cross_market_exact_name_family_rows,
        "fuchs_china_cross_market_family_conflict_rows": fuchs_china_cross_market_family_conflict_rows,
        "fuchs_czech_source_rows": len(fuchs_czech_source_rows),
        "fuchs_czech_products_matched_to_existing": fuchs_czech_matched_rows,
        "fuchs_czech_products_added": fuchs_czech_added_rows,
        "fuchs_czech_cross_market_exact_name_family_rows": fuchs_czech_cross_market_exact_name_family_rows,
        "fuchs_czech_cross_market_family_conflict_rows": fuchs_czech_cross_market_family_conflict_rows,
        "fuchs_mexico_source_rows": len(fuchs_mexico_source_rows),
        "fuchs_mexico_products_matched_to_existing": fuchs_mexico_matched_rows,
        "fuchs_mexico_products_added": fuchs_mexico_added_rows,
        "fuchs_mexico_cross_market_exact_name_family_rows": fuchs_mexico_cross_market_exact_name_family_rows,
        "fuchs_mexico_cross_market_family_conflict_rows": fuchs_mexico_cross_market_family_conflict_rows,
        "fuchs_south_africa_source_rows": len(fuchs_south_africa_source_rows),
        "fuchs_south_africa_products_matched_to_existing": fuchs_south_africa_matched_rows,
        "fuchs_south_africa_products_added": fuchs_south_africa_added_rows,
        "fuchs_south_africa_cross_market_exact_name_family_rows": fuchs_south_africa_cross_market_exact_name_family_rows,
        "fuchs_south_africa_cross_market_family_conflict_rows": fuchs_south_africa_cross_market_family_conflict_rows,
        "jaso_source_rows": len(jaso_source_rows),
        "jaso_unique_oil_codes": len({r["oil_code"] for r in jaso_source_rows}),
        "aichilon_source_products": len(aichilon_products) + len(exclusions),
        "aichilon_products_matched_to_existing": aichilon_matched_rows,
        "aichilon_products_added": aichilon_new_rows,
        "aichilon_rows_excluded": len(exclusions),
        "offers": len(offers),
        "active_offers": sum(o["lifecycle_status"] == "active" for o in offers),
        "archived_offers": sum(o["lifecycle_status"] == "archived" for o in offers),
        "duplicate_decisions": dict(Counter(c["decision"] for c in candidates)),
        "quality_issues": dict(Counter(i["issue_code"] for i in issues)),
        "bulk_sources_allowed": [s["source_id"] for s in policies["sources"] if s["bulk_ingest_allowed"]],
        "bulk_sources_blocked": [s["source_id"] for s in policies["sources"] if not s["bulk_ingest_allowed"]],
        "confirmed_world_total": None,
        "completion_note": "The seed proves the pipeline, not worldwide coverage. Exact worldwide count remains pending licensed/authorized source ingestion.",
    }
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_sqlite(records, candidates, issues, source_links, offers, policies, run_id)
    compress_sqlite()
    build_workbook(records, candidates, issues, offers, exclusions, policies, report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
