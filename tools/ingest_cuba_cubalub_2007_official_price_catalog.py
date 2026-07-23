#!/usr/bin/env python3
"""Build the historical CUBALUB product layer from Cuba's 2007 official gazette.

Resolution 122 attributes the four annexes to Empresa Cubana de Lubricantes
(CUBALUB), part of CUPET.  Annex 1 is the technical denominator: later annexes
repeat the same liquids in different packages, while Annex 4 lists grease
packages.  Numeric product grades are retained as source grades unless the
document explicitly prints a performance system such as API SJ, GL-4 or GL-5.
The 2007 publication proves historical product identities, not current offers.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/cuba-cubalub-2007-official-products.jsonl"
REPORT = ROOT / "data/cuba-cubalub-2007-official-products-report.json"
SOURCE_ID = "CUBA_CUBALUB_2007_OFFICIAL_PRICE_CATALOG"
SOURCE_URL = "https://www.cibercuba.com/s/gacetaoficial/pdf/go_o_039_2007.pdf"
SOURCE_SHA256 = "e719cd5794badcb05d08f5404c34e642e712e4379548cf457642ff9036bbf22c"
DOCUMENT_DATE = "2007-05-18"
RESOLUTION_DATE = "2007-04-30"
SNAPSHOT_DATE = "2026-07-23"
UA = "MFClassifier evidence catalog/1.0"


def item(name: str, family: str, *, source_grade: str = "", api=(), api_gl=(),
         package_rows=(), flags=()):
    return {
        "name": name,
        "family_code": family,
        "technical": {
            "sae_engine": "",
            "sae_gear": "",
            "api": list(api),
            "api_gl": list(api_gl),
            "acea": [],
            "ilsac": [],
            "iso_vg": "",
            "nlgi": "",
            "source_grade": source_grade,
            "performance": [],
        },
        "package_rows": list(package_rows),
        "flags": list(flags),
    }


LIQUID_PACKAGES = (
    "bulk",
    "208 L",
    "1 L",
    "5 L",
    "20 L",
    "1000 L",
)


PRODUCTS = [
    # Annex 1: engine oils.
    *[item(f"CUBALUB Aceite Motor Regular Grado {grade}", "M", source_grade=grade)
      for grade in ("30", "40", "50")],
    item("CUBALUB Aceite SUP.1 Grado 50", "M", source_grade="SUP.1 / 50"),
    *[item(f"CUBALUB Aceite Motor Serie 3 Grado {grade}", "M", source_grade=grade)
      for grade in ("30", "40", "50")],
    *[item(f"CUBALUB Super Caribe CD {grade}", "M", source_grade=grade, api=("CD",))
      for grade in ("40", "50")],
    item("CUBALUB Motolub 2TS", "M", source_grade="2TS"),
    item("CUBALUB Aceite Super Diesel DB-40", "M", source_grade="DB-40"),
    item("CUBALUB Aceite Super Diesel Especial 40", "M", source_grade="40"),
    item("CUBALUB Aceite Super Multi 15W40", "M", source_grade="15W40"),
    item("CUBALUB Aceite Motor Super Multi 20W50", "M", source_grade="20W50"),
    item("CUBALUB Aceite Motor Super Ligero SJ 15W40", "M",
         source_grade="15W40", api=("SJ",)),
    item("CUBALUB Aceite Motor Super Ligero SJ 20W50", "M",
         source_grade="20W50", api=("SJ",)),
    item("CUBALUB Aceite Motor Semisintético 10W40", "M", source_grade="10W40"),
    item("CUBALUB Aceite Motor Extra Diesel", "M"),
    item("CUBALUB Aceite Ferrocarril Grado 40", "M", source_grade="40"),
    item("CUBALUB Aceite Multipropósito A", "M", source_grade="A"),
    item("CUBALUB Aceite Multipropósito B", "M", source_grade="B"),
    item("CUBALUB Multi A Grado 50", "M", source_grade="A / 50"),
    item("CUBALUB Multi B Grado 50", "M", source_grade="B / 50"),
    item("CUBALUB Multi B Grado 60", "M", source_grade="B / 60"),
    item("CUBALUB Aceite Marsistron 10E12", "M", source_grade="10E12"),
    item("CUBALUB Marsistron 16E12", "M", source_grade="16E12"),
    item("CUBALUB Aceite Marsistron 20E12", "M", source_grade="20E12"),
    item("CUBALUB Martron 16F40", "M", source_grade="16F40"),
    item("CUBALUB AM-20-FAR", "M", source_grade="AM-20-FAR"),

    # Annex 1: transmission oils and tractor fluid.
    item("CUBALUB Transmisión DZ II", "T", source_grade="DZ II"),
    item("CUBALUB Transmisión Grado 90", "T", source_grade="90"),
    item("CUBALUB Aceite Transmisión MP Grado 140", "T", source_grade="MP / 140"),
    item("CUBALUB MP Grado 250", "T", source_grade="MP / 250"),
    item("CUBALUB Aceite Transmisión GL-4 Grado 90", "T",
         source_grade="90", api_gl=("GL-4",)),
    item("CUBALUB Aceite Transmisión GL-4 140", "T",
         source_grade="140", api_gl=("GL-4",)),
    item("CUBALUB EP GL-5 Grado 90", "T", source_grade="90", api_gl=("GL-5",)),
    item("CUBALUB EP GL-5 Grado 140", "T", source_grade="140", api_gl=("GL-5",)),
    item("CUBALUB THF", "TF", source_grade="THF"),

    # Annex 1: industrial oils.
    *[item(f"CUBALUB Aceite Industrial Turbo {grade}", "U", source_grade=grade)
      for grade in ("32", "46", "68")],
    item("CUBALUB Aceite Alzadora 100", "U", source_grade="100"),
    *[item(f"CUBALUB Circulación {grade}", "U", source_grade=grade)
      for grade in ("32", "46", "68", "100", "150", "220")],
    item("CUBALUB Circulación Especial 150", "U", source_grade="Especial / 150"),
    *[item(f"CUBALUB Aceite Industrial Hidráulico {grade}", "H", source_grade=grade)
      for grade in ("32", "46", "68", "100", "150")],
    *[item(f"CUBALUB Aceite Compresor D-{grade}", "C", source_grade=f"D-{grade}")
      for grade in ("68", "100", "150", "220")],
    *[item(f"CUBALUB Reductor {grade}", "T", source_grade=grade)
      for grade in ("150", "220", "320", "460", "680")],
    item("CUBALUB Aceite Industrial Guijos A", "U", source_grade="A"),
    item("CUBALUB Industrial Guijos BM", "U", source_grade="BM"),
    item("CUBALUB Guijos C", "U", source_grade="C"),
    item("CUBALUB Guijos 3000 S", "U", source_grade="3000 S"),
    item("CUBALUB Viscopren 1002", "U", source_grade="1002"),
    *[item(f"CUBALUB Husillo {grade}", "U", source_grade=grade)
      for grade in ("5", "15", "22", "32")],
    item("CUBALUB Aceite Máquina Especial", "U", source_grade="Especial"),
    *[item(f"CUBALUB Aceite Máquina {grade}", "U", source_grade=grade)
      for grade in ("100", "150", "220")],
    *[item(f"CUBALUB Telar {grade}", "U", source_grade=grade)
      for grade in ("150", "220")],
    item("CUBALUB Cilindro H", "U", source_grade="H"),
    item("CUBALUB Cilindro S", "U", source_grade="S"),
    item("CUBALUB Aceite Cilindro SC", "U", source_grade="SC"),
    *[item(f"CUBALUB Herramienta Neumática {grade}", "U", source_grade=grade)
      for grade in ("100", "150", "220")],
    item("CUBALUB Refrigeración 32", "C", source_grade="32"),
    item("CUBALUB Refrigeración 68", "C", source_grade="68"),
    item("CUBALUB Refrigeración R-368", "C", source_grade="R-368"),

    # Annex 1: other lubricating oils.
    item("CUBALUB Aceite Carro", "U"),
    item("CUBALUB Aceite Fibra 15", "U", source_grade="15"),
    item("CUBALUB Aceite Fibra 22", "U", source_grade="22"),
    item("CUBALUB Bomba de Vacío", "C"),
    item("CUBALUB Corte Ferroso B", "S", source_grade="B"),
    item("CUBALUB Corte No Ferroso 22", "S", source_grade="22"),
    item("CUBALUB Corte No Ferroso A", "S", source_grade="A"),
    item("CUBALUB Aceite Soluble", "S"),
    item("CUBALUB Aceite Tres Gotas", "S"),
    item("CUBALUB Ferroso Especial", "S", source_grade="Especial"),

    # Annex 4: grease identities.  Source numerals are not silently promoted
    # to NLGI because the gazette never labels the classification system.
    item("CUBALUB Copilla 00", "G", source_grade="00",
         package_rows=("8 kg", "16 kg", "172.5 kg"),
         flags=("source_grade_not_silently_interpreted_as_nlgi",)),
    item("CUBALUB Copilla 2", "G", source_grade="2",
         package_rows=("8 kg", "16 kg", "172.5 kg"),
         flags=("source_grade_not_silently_interpreted_as_nlgi",)),
    *[
        item(f"CUBALUB Lisan {grade}", "G", source_grade=grade,
             package_rows=("8 kg", "16 kg", "17 kg", "180 kg"),
             flags=("source_grade_not_silently_interpreted_as_nlgi",))
        for grade in ("0", "2", "2M", "3", "3M")
    ],
    item("CUBALUB Cardrexa GP 00", "G", source_grade="GP 00",
         package_rows=("180 kg",),
         flags=("source_grade_not_silently_interpreted_as_nlgi",)),
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def main() -> None:
    payload = fetch(SOURCE_URL)
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != SOURCE_SHA256:
        raise RuntimeError(f"gazette payload changed: {actual_sha}")
    # This repository intentionally avoids a runtime PDF dependency.  The
    # pinned payload was independently text-audited; its root page-tree count
    # is retained as a cheap structural guard in addition to the full SHA.
    if not re.search(rb"/Count\s+17\b.{0,200}?/Type\s*/Pages\b", payload, re.S):
        raise RuntimeError("unexpected PDF page tree")

    records = []
    for number, product in enumerate(PRODUCTS, start=1):
        packages = product["package_rows"] or list(LIQUID_PACKAGES)
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"CUBALUB-2007-{number:03d}-{normalize(product['name'])}",
            "manufacturer": "Empresa Cubana de Lubricantes (CUBALUB)",
            "brand": "CUBALUB",
            "product_name": product["name"],
            "source_product_name": product["name"].removeprefix("CUBALUB "),
            "family_code": product["family_code"],
            "market": "CUBA",
            "lifecycle_status": "historical_official_price_catalog_current_status_unverified",
            "document_date": DOCUMENT_DATE,
            "resolution_date": RESOLUTION_DATE,
            "technical": product["technical"],
            "package_rows": packages,
            "source_pages": [615] if product["family_code"] == "G" else [607, 608, 609],
            "source_url": SOURCE_URL,
            "source_pdf_sha256": actual_sha,
            "snapshot_date": SNAPSHOT_DATE,
            "flags": product["flags"],
        })

    ids = [row["source_record_id"] for row in records]
    assert len(records) == 105
    assert len(ids) == len(set(ids))
    assert Counter(row["family_code"] for row in records) == {
        "U": 35, "M": 29, "T": 13, "C": 8, "G": 8, "S": 6, "H": 5, "TF": 1,
    }
    assert sum(bool(row["technical"]["api"]) for row in records) == 4
    assert sum(bool(row["technical"]["api_gl"]) for row in records) == 4
    assert not any(row["technical"]["sae_engine"] or row["technical"]["sae_gear"]
                   or row["technical"]["iso_vg"] or row["technical"]["nlgi"]
                   for row in records)

    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                for row in records),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_pdf_sha256": actual_sha,
        "pdf_pages": 17,
        "resolution_number": "122",
        "resolution_date": RESOLUTION_DATE,
        "publication_date": DOCUMENT_DATE,
        "manufacturer": "Empresa Cubana de Lubricantes (CUBALUB)",
        "parent_entity": "Unión Cubapetróleo (CUPET)",
        "records": len(records),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "rows_with_api": sum(bool(row["technical"]["api"]) for row in records),
        "rows_with_api_gl": sum(bool(row["technical"]["api_gl"]) for row in records),
        "explicitly_excluded_non_lubricants": [
            "Caucho 32",
            "Aceite Caucho 68",
            "Caucho 100",
            "Aceite Sigatoka",
        ],
        "lifecycle_note": (
            "The official 2007 price catalog proves historical product identities "
            "and packages. It does not prove current production, current sale, "
            "current specifications or current regulatory approval."
        ),
        "classification_note": (
            "Unlabelled numeric grades remain source_grade. They are not silently "
            "converted into SAE, ISO VG or NLGI classifications."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
