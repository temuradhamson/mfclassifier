#!/usr/bin/env python3
"""Normalize the current lubricant catalog of Ceylon Petroleum Corporation.

Only factual product/grade identifiers and technical fields are retained.  The
official landing page is used for the complete product-line inventory; current
TDS files are used where the site publishes one.  Marketing prose and document
layout are not republished.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ceypetco-lubricant-products.jsonl"
REPORT = ROOT / "data" / "ceypetco-lubricant-products-report.json"
SOURCE_ID = "CEYPETCO_OFFICIAL_LUBRICANT_CATALOG"
LANDING_URL = "https://ceypetco.gov.lk/ceypetco-lubricants/"
TDS_BASE = "https://ceypetco.gov.lk/wp-content/uploads/2025/11/"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def pdf_text(payload: bytes) -> str:
    return clean(" ".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(payload)).pages))


def row(name: str, family: str, tds: str | None = None, **specifications) -> dict:
    return {
        "product_name": name,
        "family_code": family,
        "tds_filename": tds,
        "specifications": specifications,
    }


PRODUCTS = [
    row("Ceypetco 2T JASO FC", "M", "TDS-Ceypetco-2T-JASO-FC.pdf", jaso=["FC"], engine_cycle="2T", base_oil="mineral", application="air-cooled two-stroke engines"),
    row("Ceypetco 4T JASO MA2 SAE 20W-40", "M", "TDS-Ceypetco-4T-JASO-MA2.pdf", sae_engine="20W-40", api=["SL"], jaso=["MA2"], base_oil="mineral", application="four-stroke motorcycle engines"),
    row("Ceypetco 4T JASO MA2 SAE 20W-50", "M", "TDS-Ceypetco-4T-JASO-MA2.pdf", sae_engine="20W-50", api=["SL"], jaso=["MA2"], base_oil="mineral", application="four-stroke motorcycle engines"),
    row("Ceypetco 4T Scooter JASO MB", "M", "TDS-Ceypetco-4T-Scooter-JASO-MB.pdf", api=["SL"], jaso=["MB"], base_oil="synthetic blend", application="four-stroke scooters and motorcycles with automatic transmission", source_reported_sae_values=["10W-30", "10W-40"], source_quality_flags=["conflicting_sae_within_current_tds"], source_conflict_note="Description states SAE 10W-40 while the typical-characteristics table states SAE 10W-30; no SAE is promoted to the strict equivalence key."),
    row("Ceypetco ATF Dexron III D", "T", "TDS-Ceypetco-ATF-Dexron-III.pdf", atf_specifications=["GM Dexron III D", "Allison C-4"], application="automatic transmissions and compatible power-steering/hydraulic systems"),
    row("Ceypetco Brake Fluid DOT 3", "TF", "TDS-Ceypetco-Brake-Fluid-DOT3.pdf", brake_fluid_class="DOT 3", standards=["SAE J1703 F", "FMVSS No. 116 DOT 3"], application="hydraulic brake and clutch systems"),
    row("Ceypetco Brake Fluid DOT 4", "TF", "TDS-Ceypetco-Brake-Fluid-DOT4.pdf", brake_fluid_class="DOT 4", standards=["SAE J1703 F", "FMVSS No. 116 DOT 4"], application="hydraulic brake and clutch systems"),
]

for nlgi in ["000", "00", "0", "1", "2", "3"]:
    PRODUCTS.append(row(f"Ceypetco EP Grease NLGI {nlgi}", "G", "TDS-Ceypetco-EP-Grease.pdf", nlgi=nlgi, thickener="lithium 12-hydroxystearate", grease_type="EP", application="automotive and industrial extreme-pressure grease"))

PRODUCTS.extend([
    row("Ceypetco Enduro SAE 10W-30", "M", sae_engine="10W-30", application="diesel engines", evidence_level="official_landing_page_grade_only"),
    row("Ceypetco Enduro SAE 15W-40", "M", "TDS-Ceypetco-Enduro-15W40.pdf", sae_engine="15W-40", api=["CI-4", "SL"], oem_specifications=["Cummins CES 20078"], application="heavy-duty diesel engines"),
    row("Ceypetco Enduro SAE 20W-50", "M", sae_engine="20W-50", application="diesel engines", evidence_level="official_landing_page_grade_only"),
    row("Ceypetco Power Steering Fluid", "TF", "TDS-Ceypetco-Power-Steering-Oil.pdf", standards=["GM 9985010", "Ford M2CI28D"], compatible_specifications=["Dexron III", "Mercon"], application="hydraulic power-steering systems", source_quality_flags=["nonstandard_oem_notation_retained_verbatim"]),
    row("Ceypetco Circulation Oil ISO VG 150", "I", iso_vg="150", application="circulating lubrication systems", evidence_level="official_landing_page_grade_only"),
    row("Ceypetco Coolant Green", "TF", coolant_color="green", application="engine cooling systems", evidence_level="official_landing_page_variant_only"),
    row("Ceypetco Coolant Red 50/50 Premix", "TF", "TDS-Ceypetco-Radiator-Coolant-Red.pdf", coolant_color="red", product_form="premix 50/50", coolant_chemistry="ethylene glycol hybrid organic/inorganic inhibitor", standards=["ASTM D3306", "ASTM D4985"], application="automotive and heavy-duty diesel cooling systems", source_quality_flags=["tds_color_table_conflicts_with_product_variant"], source_conflict_note="The TDS title and description identify Red, while its typical-characteristics color row says Green; canonical color follows the title and product variant."),
])

for nlgi in ["00", "1", "2", "3"]:
    PRODUCTS.append(row(f"Ceypetco Lithium MP Grease NLGI {nlgi}", "G", "TDS-Ceypetco-MP-Grease.pdf", nlgi=nlgi, thickener="lithium 12-hydroxystearate", grease_type="multipurpose", application="general-purpose plain and rolling bearings"))

for grade in ["32", "46", "68", "100"]:
    PRODUCTS.append(row(f"Ceypetco Hydra ISO VG {grade}", "H", "TDS-Ceypetco-Hydra.pdf", iso_vg=grade, din=["DIN 51524-3 HVLP"], oem_specifications=["Denison HF-0/HF-1/HF-2", "Eaton Vickers I-286-S", "Eaton Vickers M-2950-S", "US Steel 127", "US Steel 136"], application="industrial hydraulic and power-transmission systems"))

PRODUCTS.extend([
    row("Ceypetco Hypertrans Transformer Oil", "E", "TDS-Ceypetco-Hypertrans-IEC-60296.pdf", standards=["IEC 60296:2020 Edition 5 Table B", "TNB-KEJ 04405-2016"], base_oil="uninhibited naphthenic mineral insulating oil", packages=["bulk", "209 L steel drum"], application="transformers, switchgear and liquid-filled electrical equipment"),
    row("Ceypetco Penetrating Oil", "S", "TDS-Ceypetco-Penetrating-Oil.pdf", application="rust release and general-purpose penetrating lubrication", silicone_free=True),
    row("Ceypetco Supra SAE 10W-30", "M", "TDS-Ceypetco-Supra.pdf", sae_engine="10W-30", api=["SL", "CF"], base_oil="mineral"),
    row("Ceypetco Supra SAE 15W-40", "M", "TDS-Ceypetco-Supra.pdf", sae_engine="15W-40", api=["SL", "CF"], base_oil="mineral"),
    row("Ceypetco Supra SAE 20W-50", "M", "TDS-Ceypetco-Supra.pdf", sae_engine="20W-50", api=["SL", "CF"], base_oil="mineral"),
    row("Ceypetco Supra SAE 40", "M", "TDS-Ceypetco-Supra.pdf", sae_engine="40", api=["SL", "CF"], base_oil="mineral"),
    row("Ceypetco Supra SAE 50", "M", "TDS-Ceypetco-Supra.pdf", sae_engine="50", api=["SL", "CF"], base_oil="mineral"),
    row("Ceypetco Supreme XHD SAE 15W-40", "M", "TDS-Ceypetco-Supreme-XHD.pdf", sae_engine="15W-40", api=["CH-4"], application="heavy-duty diesel engines"),
    row("Ceypetco Supreme XHD SAE 20W-50", "M", "TDS-Ceypetco-Supreme-XHD.pdf", sae_engine="20W-50", api=["CH-4"], application="heavy-duty diesel engines"),
])

for api_gl in ["GL-4", "GL-5"]:
    filename = f"TDS-Ceypetco-Gear-Oil-{api_gl}.pdf"
    for grade in ["90", "140"]:
        PRODUCTS.append(row(f"Ceypetco HPGO SAE {grade} API {api_gl}", "T", filename, sae_gear=grade, api_gl=[api_gl], application="manual transmissions, differentials and final drives"))

PRODUCTS.extend([
    row("Ceypetco Universal Tractor Fluid SAE 10W-30", "T", "TDS-Ceypetco-Universal-Tractor-Fluid.pdf", sae_engine="10W-30", api=["CI-4", "CF-4", "CF", "SF"], api_gl=["GL-4"], acea=["E2", "E7"], oem_specifications=["MAN 271", "Allison C-4", "John Deere JDM J27", "Massey Ferguson CMS M 1145", "Caterpillar TO-2", "MIL-L-210D"], application="STOU engine, transmission, hydraulic, final-drive and wet-brake service"),
    row("Ceypetco Universal Tractor Fluid SAE 15W-40", "T", "TDS-Ceypetco-Universal-Tractor-Fluid.pdf", sae_engine="15W-40", api=["CI-4", "CF-4", "CF", "SF"], api_gl=["GL-4"], acea=["E2", "E7"], oem_specifications=["MAN 271", "Allison C-4", "John Deere JDM J27", "Massey Ferguson CMS M 1145", "Caterpillar TO-2", "MIL-L-210D"], application="STOU engine, transmission, hydraulic, final-drive and wet-brake service"),
    row("Ceypetco Rodeo Xtra SAE 10W-30", "M", "TDS-Ceypetco-Rodeo-Xtra.pdf", sae_engine="10W-30", api=["SN", "CF"], ilsac=["GF-5"], base_oil="mineral"),
    row("Ceypetco Rodeo Xtra SAE 15W-40", "M", "TDS-Ceypetco-Rodeo-Xtra.pdf", sae_engine="15W-40", api=["SN", "CF"], base_oil="mineral"),
    row("Ceypetco Platineum SAE 0W-20", "M", "TDS-Ceypetco-Platineum-0W-20-1.pdf", sae_engine="0W-20", api=["SN"], ilsac=["GF-5"], base_oil="fully synthetic"),
    row("Ceypetco MTF SAE 80W-90 API GL-4", "T", "TDS-Ceypetco-MTF-80W-90-GL-4.pdf", sae_gear="80W-90", api_gl=["GL-4"], application="manual transmissions, differentials and final drives"),
])


TDS_VALIDATION_TOKENS = {
    "TDS-Ceypetco-2T-JASO-FC.pdf": ["Ceypetco 2T- JASO FC", "Viscosity Index"],
    "TDS-Ceypetco-4T-JASO-MA2.pdf": ["20W-40", "20W-50", "JASO MA2"],
    "TDS-Ceypetco-4T-Scooter-JASO-MB.pdf": ["SAE 10W-40", "SAE 10W-30", "JASO MB"],
    "TDS-Ceypetco-ATF-Dexron-III.pdf": ["Dexron III D", "Allison C-4"],
    "TDS-Ceypetco-Brake-Fluid-DOT3.pdf": ["DOT 3", "FMVSS No.116"],
    "TDS-Ceypetco-Brake-Fluid-DOT4.pdf": ["DOT 4", "FMVSS No.116"],
    "TDS-Ceypetco-EP-Grease.pdf": ["EP 000", "EP 00", "EP 3"],
    "TDS-Ceypetco-Enduro-15W40.pdf": ["15W-40", "API CI-4/SL", "CES 20078"],
    "TDS-Ceypetco-Gear-Oil-GL-4.pdf": ["SAE 90", "SAE 140", "GL-4"],
    "TDS-Ceypetco-Gear-Oil-GL-5.pdf": ["SAE 90", "SAE 140", "GL-5"],
    "TDS-Ceypetco-Hydra.pdf": ["ISO 32", "ISO 46", "ISO 68", "ISO 100"],
    "TDS-Ceypetco-Hypertrans-IEC-60296.pdf": ["IEC 60296 : 2020", "TNB-KEJ 04405-2016"],
    "TDS-Ceypetco-MP-Grease.pdf": ["NLGI 00", "NLGI 1", "NLGI 2", "NLGI 3"],
    "TDS-Ceypetco-MTF-80W-90-GL-4.pdf": ["SAE 80W-90", "GL-4"],
    "TDS-Ceypetco-Penetrating-Oil.pdf": ["Ceypetco Penetrating Oil", "does not contain CFC"],
    "TDS-Ceypetco-Platineum-0W-20-1.pdf": ["0W-20", "API SN", "GF -5"],
    "TDS-Ceypetco-Power-Steering-Oil.pdf": ["Power Steering Fluid", "Ford M2CI28D"],
    "TDS-Ceypetco-Radiator-Coolant-Red.pdf": ["Coolant (Red)", "ASTM D 3306", "Color Visual Green"],
    "TDS-Ceypetco-Rodeo-Xtra.pdf": ["10W-30", "15W-40", "API SN/CF"],
    "TDS-Ceypetco-Supra.pdf": ["10W-30", "20W-50", "API SL/CF"],
    "TDS-Ceypetco-Supreme-XHD.pdf": ["15W-40", "20W-50", "API CH-4"],
    "TDS-Ceypetco-Universal-Tractor-Fluid.pdf": ["10W-30", "15W-40", "John Deere JDM J27"],
}


def main() -> None:
    landing_payload = fetch(LANDING_URL)
    landing_text = clean(re.sub(r"<[^>]+>", " ", landing_payload.decode(errors="replace")))
    for token in ["Ceypetco 2T JASO FC", "Ceypetco Enduro SAE 10W30, 15W40, 20W50", "Ceypetco Universal Tractor Fluid", "Ceypetco-MTF-80W-90-GL-4"]:
        assert token in landing_text, token

    documents = {}
    for filename, tokens in TDS_VALIDATION_TOKENS.items():
        url = TDS_BASE + filename
        payload = fetch(url)
        text = pdf_text(payload)
        for token in tokens:
            assert token.casefold() in text.casefold(), (filename, token)
        documents[filename] = {
            "url": url,
            "source_sha256": hashlib.sha256(payload).hexdigest(),
            "text": text,
        }

    records = []
    for index, source in enumerate(PRODUCTS, 1):
        specs = dict(source["specifications"])
        lifecycle_status = specs.pop("lifecycle_status", "current_official_catalog")
        tds = source["tds_filename"]
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"CEYPETCO-{index:03d}",
            "source_url": LANDING_URL,
            "technical_document_url": documents[tds]["url"] if tds else "",
            "technical_document_sha256": documents[tds]["source_sha256"] if tds else "",
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Sri Lanka",
            "manufacturer": "Ceylon Petroleum Corporation",
            "technical_document_issuer": "Hyrax Oil Sdn Bhd" if tds else "",
            "brand": "Ceypetco",
            "product_name": source["product_name"],
            "family_code": source["family_code"],
            "lifecycle_status": lifecycle_status,
            "specifications": specs,
        })

    assert len(records) == 47
    assert len({row["product_name"].casefold() for row in records}) == len(records)
    output_text = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    OUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "official_state_owned_supplier_catalog_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "source_url": LANDING_URL,
        "source_page_sha256": hashlib.sha256(landing_payload).hexdigest(),
        "source_product_lines": 23,
        "normalized_product_grade_rows": len(records),
        "technical_documents": len(documents),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "quality_flags": dict(sorted(Counter(flag for row in records for flag in row["specifications"].get("source_quality_flags", [])).items())),
        "documents": [{"filename": name, "source_url": data["url"], "source_sha256": data["source_sha256"]} for name, data in sorted(documents.items())],
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "grain_note": "One row is a factual product-grade or explicitly marketed color variant. Package-only variants are not separate rows.",
        "publication_scope": "Factual product names, grade/specification fields, evidence URLs and hashes only; document prose, layout and artwork are excluded.",
        "known_source_conflicts": [
            "The current 4T Scooter TDS says SAE 10W-40 in the description and SAE 10W-30 in the property table.",
            "The current Red coolant TDS identifies Red in its title/description but Green in the color property row.",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
