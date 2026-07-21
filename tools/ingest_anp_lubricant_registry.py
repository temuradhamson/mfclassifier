#!/usr/bin/env python3
"""Download and normalize Brazil ANP's weekly open lubricant registry."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "anp-brazil-lubricant-products.jsonl"
REPORT = ROOT / "data" / "anp-brazil-lubricant-products-report.json"
SOURCE_PAGE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/registro-de-oleos-e-graxas-lubrificantes"
SOURCE_URL = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/arquivos-registro/dados-abertos-registro-produtos.csv"
METADATA_URL = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/arquivos-registro/metadados-registro-produtos.pdf"
TERMS_URL = "https://www.gov.br/pt-br/termos-de-uso"
USER_AGENT = "MFClassifierResearch/1.0 (open-government-data research)"

EXPECTED_COLUMNS = [
    "REG", "SITUACAO", "PROCESSO", "ANO", "MARCA_COMERCIAL", "DETENTOR",
    "CNPJ_DETENTOR", "TIPO_EMPRESA", "TIPO_PRODUTO", "FINALIDADE", "APLICACAO",
    "PRODUTOR", "ORIGEM", "SAE", "ISO", "NLGI", "ND", "COMPOSICAO",
    "ACONDICIONAMENTO", "OBS.",
]

IDENTITY_COLUMNS = [
    "REG", "MARCA_COMERCIAL", "DETENTOR", "TIPO_PRODUTO", "FINALIDADE",
    "APLICACAO", "PRODUTOR", "ORIGEM", "SAE", "ISO", "NLGI", "ND", "COMPOSICAO",
]


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-záàâãéêíóôõúç]+", " ", value).strip()


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def family_for(row: dict[str, str]) -> tuple[str, str]:
    product_type = row["TIPO_PRODUTO"].upper()
    purpose = row["FINALIDADE"].upper()
    application = row["APLICACAO"].upper()
    if "GRAXA" in product_type:
        return "G", "source_product_type_grease"
    if "INCISO I," in purpose or "INCISO V," in purpose or "INCISO VI," in purpose:
        return "M", "anp_regulatory_purpose_engine"
    if "INCISO II," in purpose or "INCISO III," in purpose:
        return "T", "anp_regulatory_purpose_transmission_or_multifunctional_drivetrain"
    if "INCISO VII," in purpose:
        return "H", "anp_regulatory_purpose_power_steering_hydraulic"
    if "INCISO IV," in purpose:
        if "PISTÃO" in application:
            return "M", "anp_aviation_piston_engine_application"
        if "ENGRENAGENS" in application or "TRANSMISSÕES" in application:
            return "T", "anp_aviation_gear_or_transmission_application"
        return "S", "anp_mixed_aviation_hydraulic_turbine_application"
    if "INCISO IX," in purpose:
        return "I", "anp_incidental_food_contact_industrial_oil"
    return "S", "anp_biodegradable_or_unresolved_special_oil"


def parse_packages(value: str) -> list[str]:
    return sorted({clean(item) for item in value.split(";") if clean(item)}, key=str.casefold)


def main() -> None:
    content = download(SOURCE_URL)
    source_hash = hashlib.sha256(content).hexdigest()
    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded), delimiter=";")
    assert reader.fieldnames == EXPECTED_COLUMNS, reader.fieldnames
    raw_rows = []
    for source_row, row in enumerate(reader, start=2):
        cleaned = {key: clean(value) for key, value in row.items()}
        cleaned["_source_row"] = source_row
        raw_rows.append(cleaned)
    assert raw_rows
    assert all(row["REG"] and row["MARCA_COMERCIAL"] and row["DETENTOR"] for row in raw_rows)

    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        grouped[tuple(normalize(row[column]) for column in IDENTITY_COLUMNS)].append(row)

    records = []
    for key, occurrences in sorted(grouped.items(), key=lambda item: (int(item[1][0]["REG"]), item[0])):
        row = occurrences[0]
        family_code, classification_basis = family_for(row)
        fingerprint = hashlib.sha256("|".join(key).encode()).hexdigest()[:16]
        packages = sorted({package for item in occurrences for package in parse_packages(item["ACONDICIONAMENTO"])}, key=str.casefold)
        processes = sorted({item["PROCESSO"] for item in occurrences if item["PROCESSO"]}, key=str.casefold)
        years = sorted({item["ANO"] for item in occurrences if item["ANO"]})
        source_rows = [int(item["_source_row"]) for item in occurrences]
        records.append({
            "source_id": "ANP_BRAZIL_LUBRICANT_REGISTRY",
            "source_record_id": f"ANP-{row['REG']}-{fingerprint}",
            "source_url": SOURCE_URL,
            "source_page_url": SOURCE_PAGE,
            "metadata_url": METADATA_URL,
            "source_sha256": source_hash,
            "snapshot_date": date.today().isoformat(),
            "market": "Brazil",
            "lifecycle_status": "active_in_current_anp_snapshot",
            "registration_number": row["REG"],
            "registration_status": row["SITUACAO"],
            "process_numbers": processes,
            "registration_years": years,
            "product_name": row["MARCA_COMERCIAL"],
            "registration_holder": row["DETENTOR"],
            "registration_holder_cnpj": row["CNPJ_DETENTOR"],
            "company_type": row["TIPO_EMPRESA"],
            "producer": row["PRODUTOR"],
            "origin": row["ORIGEM"],
            "product_type": row["TIPO_PRODUTO"],
            "regulatory_purpose": row["FINALIDADE"],
            "application": row["APLICACAO"],
            "family_code": family_code,
            "classification_basis": classification_basis,
            "sae": "" if row["SAE"] in {"N.A.", "N.A"} else row["SAE"],
            "iso_vg": "" if row["ISO"] in {"N.A.", "N.A"} else row["ISO"],
            "nlgi": "" if row["NLGI"] in {"N.A.", "N.A"} else row["NLGI"],
            "performance_level": "" if row["ND"] in {"N.A.", "N.A"} else row["ND"],
            "base_oil_composition": row["COMPOSICAO"],
            "packages": packages,
            "source_occurrence_count": len(occurrences),
            "source_row_numbers": source_rows,
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "official_open_government_registry_normalized",
        "snapshot_date": date.today().isoformat(),
        "source_page_url": SOURCE_PAGE,
        "source_url": SOURCE_URL,
        "metadata_url": METADATA_URL,
        "terms_url": TERMS_URL,
        "source_sha256": source_hash,
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "csv_rows": len(raw_rows),
        "normalized_product_grade_rows": len(records),
        "duplicate_source_occurrences_merged": len(raw_rows) - len(records),
        "unique_registration_numbers": len({row["registration_number"] for row in records}),
        "unique_commercial_names": len({normalize(row["product_name"]) for row in records}),
        "registration_holders": len({row["registration_holder_cnpj"] for row in records}),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "product_types": dict(sorted(Counter(row["product_type"] for row in records).items())),
        "classification_basis": dict(sorted(Counter(row["classification_basis"] for row in records).items())),
        "rights_note": "ANP publishes this weekly file as open data. Only normalized factual fields are republished with attribution; narrative observations and source document layout are omitted.",
        "grain_note": "One row is a distinct ANP registration + commercial name + holder + application + technical grade/performance combination. Package-only and exact repeated occurrences are merged.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
