#!/usr/bin/env python3
"""Download and normalize Indonesia's public 2021-2025 NPT lubricant list."""

from __future__ import annotations

import calendar
import hashlib
import io
import json
import re
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "indonesia-npt-lubricant-products.jsonl"
REPORT = ROOT / "data" / "indonesia-npt-lubricant-products-report.json"
SOURCE_PAGE = "https://migas.esdm.go.id/daftar-umum-pelumas"
SOURCE_URL = "https://migas.esdm.go.id/cms/uploads/informasi-publik/Daftar%20Umum%20Pelumas/Daftar%20Umum%20Pelumas%202021%20-%202025.pdf"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-information research)"
SNAPSHOT_DATE = date.today().isoformat()
DOCUMENT_DATE = "2025-08-07"

MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
}
EXPIRY_RE = re.compile(
    r"\b(" + "|".join(month.title() for month in MONTHS) + r")\s+(20\d{2})\s*$|#VALUE!\s*$",
    re.IGNORECASE,
)
NPT_CLASS_RE = re.compile(r"^[A-Z]{2,4}\d{3}([A-Z])")
PLACEHOLDER = "CEK INPUTAN DATA"


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def extract_rows(content: bytes) -> list[dict]:
    reader = PdfReader(io.BytesIO(content))
    rows: list[dict] = []
    current: dict | None = None
    for page_number, page in enumerate(reader.pages, 1):
        layout = page.extract_text(extraction_mode="layout") or ""
        for source_line, line in enumerate(layout.splitlines(), 1):
            expiry = EXPIRY_RE.search(line)
            if expiry:
                current = {
                    "source_pdf_page": page_number,
                    "source_line": source_line,
                    "company": clean(line[:50]),
                    "product_name": clean(line[50:105]),
                    "registration_number_raw": clean(line[105:expiry.start()]),
                    "expiry_raw": clean(expiry.group(0)),
                }
                rows.append(current)
                continue
            if current is None or not clean(line):
                continue
            upper = clean(line).upper()
            if upper.startswith("DAFTAR UMUM") or "NAMA PERUSAHAAN" in upper:
                continue
            company_tail = clean(line[:50])
            product_tail = clean(line[50:])
            if company_tail:
                current["company"] = clean(current["company"] + " " + company_tail)
            if product_tail:
                current["product_name"] = clean(current["product_name"] + " " + product_tail)
    return rows


def expiry_fields(raw: str) -> tuple[str, str]:
    if raw == "#VALUE!":
        return "", "source_expiry_error"
    month_name, year_text = clean(raw).casefold().split()
    month = MONTHS[month_name]
    last_day = calendar.monthrange(int(year_text), month)[1]
    valid_through = date(int(year_text), month, last_day)
    status = "potentially_active_by_expiry_date" if valid_through >= date.today() else "expired_by_expiry_date"
    return valid_through.isoformat(), status


def technical(product_name: str) -> dict[str, list[str]]:
    upper = product_name.upper()
    sae = sorted(set(re.findall(r"(?<!\d)(?:0W|5W|10W|15W|20W|25W)(?:[- ]?\d{2,3})?(?!\d)|(?<=SAE\s)\d{2,3}(?!\d)", upper)))
    sae = [value.replace(" ", "-") for value in sae]
    iso_vg = sorted(set(re.findall(r"\bISO\s*(?:VG\s*)?(\d{1,4})\b", upper)), key=lambda value: int(value))
    nlgi = sorted(set(re.findall(r"\bNLGI\s*(?:GRADE\s*)?([0-6](?:\.5)?)\b", upper)))
    api = sorted(set(re.findall(r"\bAPI\s+((?:SP|SN\+?|SM|SL|SJ|SG|SH|CK-4|CJ-4|CI-4(?:\s+PLUS)?|CH-4|CG-4|CF-4|CF|GL-[1-6])(?:\s*[/,]\s*(?:SP|SN|SM|SL|SJ|CK-4|CJ-4|CI-4|CH-4|CG-4|CF-4|CF|GL-[1-6]))*)", upper)))
    acea = sorted(set(re.findall(r"\bACEA\s+([A-Z]\d(?:[-/]\d{2,4})?(?:\s*[/,]\s*[A-Z]\d(?:[-/]\d{2,4})?)*)", upper)))
    jaso = sorted(set(re.findall(r"\bJASO\s+([A-Z]{1,3}(?:[- ]?\d+)?)", upper)))
    return {"sae": sae, "iso_vg": iso_vg, "nlgi": nlgi, "api": api, "acea": acea, "jaso": jaso}


def family_for(product_name: str, npt_class: str) -> tuple[str, str]:
    name = product_name.upper()
    keyword_rules = [
        ("TF", r"\b(COOLANT|ANTIFREEZE|RADIATOR|BRAKE FLUID|ADBLUE|DEF)\b", "product_keyword_technical_fluid"),
        ("E", r"\b(TRANSFORMER|INSULATING|DIELECTRIC)\b", "product_keyword_electrical_insulating"),
        ("U", r"\bTURBINE\b", "product_keyword_turbine"),
        ("G", r"\b(GREASE|GEMUK)\b", "product_keyword_grease"),
        ("H", r"\b(HYDRAULIC|HYDRAULIK|HIDRAULIK|HLP|HVLP)\b", "product_keyword_hydraulic"),
        ("C", r"\b(COMPRESSOR|KOMPRESOR|REFRIGERATION|REFRIGERANT)\b", "product_keyword_compressor_or_refrigeration"),
        ("T", r"\b(TRANSMISSION|TRANSMISI|GEAR|GEARBOX|ATF|CVTF|DCTF|UTTO|STOU|AXLE)\b", "product_keyword_transmission"),
        ("M", r"\b(ENGINE|MOTOR|DIESEL|GASOLINE|2T|4T)\b", "product_keyword_engine"),
    ]
    for family, pattern, basis in keyword_rules:
        if re.search(pattern, name):
            return family, basis
    class_map = {
        "E": "M", "R": "T", "G": "G", "H": "H", "C": "C", "F": "C",
        "T": "U", "W": "M", "I": "I", "M": "I", "P": "I", "S": "I",
        "A": "S", "K": "S", "D": "S", "X": "S",
    }
    if npt_class in class_map:
        return class_map[npt_class], f"npt_class_{npt_class}"
    return "S", "unresolved_name_and_npt_class"


def main() -> None:
    content = download(SOURCE_URL)
    source_hash = hashlib.sha256(content).hexdigest()
    raw_rows = extract_rows(content)
    assert len(raw_rows) == 12626, len(raw_rows)
    assert all(row["company"] and row["product_name"] for row in raw_rows)

    records = []
    for row in raw_rows:
        registration_raw = row["registration_number_raw"]
        registration = re.sub(r"\s+", "", registration_raw).upper()
        placeholder = registration == PLACEHOLDER.replace(" ", "")
        registration_status = "source_placeholder_no_registration_number" if placeholder else "registration_value_published"
        npt_match = NPT_CLASS_RE.match(registration) if not placeholder else None
        npt_class = npt_match.group(1) if npt_match else ""
        family_code, classification_basis = family_for(row["product_name"], npt_class)
        valid_through, lifecycle_status = expiry_fields(row["expiry_raw"])
        if placeholder:
            lifecycle_status = "source_placeholder_registration_unverified"
        fingerprint = hashlib.sha256(
            "|".join([
                registration, str(row["source_pdf_page"]), normalize(row["company"]), normalize(row["product_name"]),
            ]).encode()
        ).hexdigest()[:16]
        records.append({
            "source_id": "INDONESIA_NPT_LUBRICANT_REGISTRY",
            "source_record_id": f"ID-NPT-{fingerprint}",
            "source_url": SOURCE_URL,
            "source_page_url": SOURCE_PAGE,
            "source_sha256": source_hash,
            "source_document_date": DOCUMENT_DATE,
            "source_pdf_page": row["source_pdf_page"],
            "source_line": row["source_line"],
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Indonesia",
            "company": row["company"],
            "product_name": row["product_name"],
            "registration_number": "" if placeholder else registration,
            "registration_number_raw": registration_raw,
            "registration_number_status": registration_status,
            "npt_class_code": npt_class,
            "expiry_raw": row["expiry_raw"],
            "valid_through": valid_through,
            "lifecycle_status": lifecycle_status,
            "lifecycle_basis": "computed_from_published_expiry_month; not a live registry verification",
            "family_code": family_code,
            "classification_basis": classification_basis,
            "technical": technical(row["product_name"]),
        })

    registration_groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if record["registration_number"]:
            registration_groups[record["registration_number"]].append(record)
    collisions = {
        number: [{"company": row["company"], "product_name": row["product_name"], "source_pdf_page": row["source_pdf_page"]} for row in rows]
        for number, rows in registration_groups.items() if len(rows) > 1
    }
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    statuses = Counter(row["lifecycle_status"] for row in records)
    report = {
        "schema_version": 1,
        "status": "official_public_government_registry_snapshot_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_document_date": DOCUMENT_DATE,
        "source_page_url": SOURCE_PAGE,
        "source_url": SOURCE_URL,
        "source_sha256": source_hash,
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "source_pdf_pages": 211,
        "published_product_rows": len(records),
        "rows_with_registration_value": sum(bool(row["registration_number"]) for row in records),
        "rows_with_source_placeholder_no_registration_number": sum(not row["registration_number"] for row in records),
        "unique_registration_numbers": len(registration_groups),
        "registration_number_collisions": len(collisions),
        "registration_number_collision_details": collisions,
        "lifecycle_assessments": dict(sorted(statuses.items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "npt_class_codes": dict(sorted(Counter(row["npt_class_code"] or "unparsed" for row in records if row["registration_number"]).items())),
        "classification_basis": dict(sorted(Counter(row["classification_basis"] for row in records).items())),
        "rights_note": "The Ministry publishes the PDF under Informasi Publik. Only normalized factual table fields are republished with attribution; document layout and narrative expression are omitted.",
        "lifecycle_note": "Potentially active/expired is an inference from the published expiry month against the snapshot date, not confirmation from the live search form. Expired rows remain as historical product evidence.",
        "quality_note": "All named product rows are retained. Rows whose NPT cell says CEK INPUTAN DATA have no external NPT code and carry an explicit source-data-quality status.",
        "grain_note": "One output row is one company + product name + published NPT cell + PDF position. Colliding NPT values are intentionally kept separate for review.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
