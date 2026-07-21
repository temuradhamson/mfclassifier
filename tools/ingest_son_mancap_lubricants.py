#!/usr/bin/env python3
"""Normalize lubricant-scope products from Nigeria SON's public MANCAP PDF."""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "son-mancap-chemical-lubricant-products.jsonl"
REPORT = ROOT / "data" / "son-mancap-chemical-lubricant-products-report.json"
CACHE = ROOT / ".cache" / "son-mancap-chemical"
PDF_CACHE = CACHE / "chemical-products-sector-2024-2029.pdf"
SOURCE_ID = "SON_MANCAP_CHEMICAL_LUBRICANT_PRODUCTS"
SOURCE_URL = "https://son.gov.ng/wp-content/uploads/2026/07/CHEMICAL-PRODUCTS-SECTOR_compressed.pdf"
SOURCE_CONTEXT_URL = "https://son.gov.ng/mancapservice/"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-certification-directory)"


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


def product_identity_name(value: str) -> str:
    """Normalize harmless notation variants without merging technical grades."""
    value = normalize(value)
    value = re.sub(r"\bengineoil\b", "engine oil", value)
    value = re.sub(r"\boilapi\b", "oil api", value)
    value = re.sub(r"\boil(?=\d)", "oil ", value)
    value = re.sub(r"\b(\d+)w\s+(\d+)\b", r"\1w\2", value)
    value = re.sub(r"\b(c[ijkhgf]|fa|gl)\s+4\b", r"\g<1>4", value)
    value = re.sub(r"\bdextron\b", "dexron", value)
    value = re.sub(r"\bapi\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def canonical_company(value: str) -> str:
    value = clean(value)
    value = re.sub(r"\bNigerA\b", "NIGERIA", value, flags=re.I)
    replacements = {
        "INTERNATIO NAL": "INTERNATIONAL",
        "INTERNATI ONAL": "INTERNATIONAL",
        "INTERNATIONA L": "INTERNATIONAL",
        "PETROCHEM ICALS": "PETROCHEMICALS",
        "PETROCHEMI CALS": "PETROCHEMICALS",
        "PETROCHE MICALS": "PETROCHEMICALS",
        "PETROCHEMICA LS": "PETROCHEMICALS",
        "CHYKKASO N": "CHYKKASON",
        "ENTERPRIS ES": "ENTERPRISES",
        "EPO XY": "EPOXY",
        "MANUFACTU RING": "MANUFACTURING",
        "LUBE AFRI": "LUBEAFRI",
        "POLAR PETROCHE MICALS": "POLAR PETROCHEMICALS",
        "POLAR PETROCHEMI CALS": "POLAR PETROCHEMICALS",
        "POLAR PETROCHEMICA LS": "POLAR PETROCHEMICALS",
    }
    for old, new in replacements.items():
        value = re.sub(re.escape(old), new, value, flags=re.I)
    value = re.sub(r"\bAUTO SHECK\b", "AUTOSHECK", value, flags=re.I)
    value = re.sub(r"^MIGHTY HERCULES MANUFACTURING\s*&\s*SU(?:P)?$", "MIGHTY HERCULES MANUFACTURING & SUP", value, flags=re.I)
    value = re.sub(r"^MASTER ENERGY OIL AND GAS\b", "MASTERS ENERGY OIL AND GAS", value, flags=re.I)
    value = re.sub(r"^TWIN SUPER ENTERPRISES\b", "TWINS SUPER ENTERPRISES", value, flags=re.I)
    value = re.sub(r"\s+[–-]\s+", " ", value)
    value = re.sub(r"\s+&\s+", " AND ", value)
    value = re.sub(r"\bNIG\b\.?", "NIGERIA", value, flags=re.I)
    value = re.sub(r"\bLTD\b\.?", "LIMITED", value, flags=re.I)
    value = re.sub(r"\bCO\b\.?", "COMPANY", value, flags=re.I)
    value = re.sub(r"\bLIMTED\b|\bLIMITE\b|\bLIMIT\b$|\bLIM\b$", "LIMITED", value, flags=re.I)
    value = re.sub(r"\b(LIMITED)\s+NO\s+\d+.*$", r"\1", value, flags=re.I)
    aliases = {
        "AMMASCO INTERNATIONAL LIMITED": "AMMASCO INTERNATIONAL LIMITED",
        "BOVAS LUBES AND PETROCHEMICALS LIMITED": "BOVAS LUBES AND PETROCHEMICALS LIMITED",
        "BOUTON PANACHE LIMITED": "BOUTON PANACHE LIMITED",
        "CHYKKASON INTERNATIONAL COMPANY LIMITED": "CHYKKASON INTERNATIONAL COMPANY LIMITED",
        "CHYKKASON INTERNATIONAL COMPANY": "CHYKKASON INTERNATIONAL COMPANY LIMITED",
        "EPOXY OILSERV NIGERIA LIMITED": "EPOXY OILSERV NIGERIA LIMITED",
        "IBETO PETROCHEMICAL INDUSTRY LIMITED": "IBETO PETROCHEMICAL INDUSTRIES LIMITED",
        "PETROCAM TRADING NIGERIA LIMITED": "PETROCAM TRADING NIGERIA LIMITED",
        "SEGMAX OIL NIGERIA LIMITED": "SEGMAX OIL NIGERIA LIMITED",
    }
    value = aliases.get(value.upper(), value)
    return value.upper()


def fetch_pdf() -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    if PDF_CACHE.exists():
        return PDF_CACHE.read_bytes()
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    error = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read()
            if not body.startswith(b"%PDF") or len(body) < 500_000:
                raise RuntimeError("unexpected SON PDF response")
            PDF_CACHE.write_bytes(body)
            return body
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            error = exc
            time.sleep(min(10, attempt + 1))
    raise RuntimeError(f"Failed to fetch SON MANCAP PDF: {error}")


def extract_certificate_rows() -> tuple[list[dict], int]:
    rows = []
    with pdfplumber.open(PDF_CACHE) as pdf:
        page_count = len(pdf.pages)
        for page_number, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables():
                for cells in table:
                    if len(cells) != 5:
                        continue
                    source_number = clean(cells[0])
                    if not source_number.isdigit():
                        continue
                    rows.append({
                        "source_number": int(source_number),
                        "source_page": page_number,
                        "company_raw": clean(cells[1]),
                        "company": canonical_company(cells[1]),
                        "product_cell": clean(cells[3]),
                    })
    source_numbers = [row["source_number"] for row in rows]
    if page_count != 233 or source_numbers != list(range(1, 2012)):
        raise RuntimeError(f"Unexpected SON extraction: pages={page_count} rows={len(rows)}")
    return rows, page_count


def split_designations(value: str) -> list[str]:
    value = re.sub(r"(?i)(?<=ENGINE OIL)\.\s+(?=[A-Z])", "; ", clean(value))
    raw_parts = [clean(part).strip(" .;'\"") for part in value.split(";") if clean(part).strip(" .;'\"")]
    parts = []
    for part in raw_parts:
        normalized = normalize(part)
        is_spec_continuation = bool(
            re.match(r"^(?:api|acea|ilsac|jaso)\b", normalized)
            or (len(part) < 40 and re.match(r"^(?:s[almnhgfdce]|c[ikjhgfdce](?:\s*4)?|fa\s*4)\s*(?:/|\s)", part, re.I))
        )
        if parts and is_spec_continuation:
            parts[-1] = clean(parts[-1] + " " + part)
        else:
            parts.append(part)
    return parts


def family_for(product_name: str) -> tuple[str, str] | None:
    normalized = normalize(product_name)
    normalized = re.sub(r"\bengineoil\b", "engine oil", normalized)
    normalized = re.sub(r"\boilapi\b", "oil api", normalized)
    normalized = re.sub(r"\boil(?=\d)", "oil ", normalized)
    normalized = normalized.replace("lbricant", "lubricant")
    value = f" {normalized} "
    exclusions = (
        " edible ", " cooking ", " vegetable ", " palm oil ", " soybean oil ",
        " soya oil ", " groundnut oil ", " coconut oil ", " hair oil ",
        " body oil ", " baby oil ", " essential oil ", " monoi oil ",
        " oil paint ", " oil based paint ", " alkyd resin ", " petroleum jelly ",
        " oil filter ", " grease remover ", " grease trap ", " degreaser ",
        " dishwash ", " dish wash ", " handwash ", " shampoo ", " bodycare ",
        " soap ", " lotion ", " cream ", " moisturiser ", " conditioner ",
    )
    if any(token in value for token in exclusions):
        return None
    rules = [
        ("TF", "explicit_brake_or_coolant_product_name", (" brake fluid ", " brake oil ", " break and clutch fluid ", " clutch fluid ", " coolant ", " antifreeze ", " anti freeze ", " radiator ", " screen wash ", " windscreen washer ", " adblue ", " diesel exhaust fluid ")),
        ("T", "explicit_transmission_or_gear_product_name", (" automatic transmission ", " transmission fluid ", " transmission oil ", " atf ", " dexron ", " dextron ", " gear oil ", " gear box oil ", " gearbox oil ", " gear lubricating oil ", " differential oil ", " axle oil ")),
        ("H", "explicit_hydraulic_product_name", (" hydraulic ", " hydraulube ", " hydrulic ")),
        ("C", "explicit_compressor_or_refrigeration_oil_name", (" compressor oil ", " refrigeration oil ")),
        ("U", "explicit_turbine_oil_name", (" turbine oil ",)),
        ("E", "explicit_transformer_or_insulating_oil_name", (" transformer oil ", " insulating oil ", " dielectric oil ")),
        ("G", "explicit_grease_product_name", (" grease ",)),
        ("M", "explicit_engine_oil_product_name", (" engine oil ", " engie oil ", " motor oil ", " motorcycle oil ", " generator oil ", " crankcase oil ", " two stroke oil ", " two cycle oil ", " 2t oil ", " 4t oil ")),
        ("I", "explicit_industrial_or_process_oil_name", (" cutting oil ", " cutting fluid ", " soluble oil ", " metalworking ", " heat transfer oil ", " quenching oil ", " machine oil ", " spindle oil ", " slideway oil ", " mould oil ", " mold oil ", " chain oil ", " circulating oil ", " industrial oil ", " process oil ", " base oil ")),
    ]
    for family, basis, tokens in rules:
        if any(token in value for token in tokens):
            return family, basis
    has_sae_multigrade = bool(re.search(r"\b(?:0|5|10|15|20|25)w[- /]?\d{2}\b", value))
    has_sae_mono = bool(re.search(r"\bsae\s*\d{2}\b", value))
    has_api_literal = " api " in value
    has_api_pair = bool(re.search(r"\b(?:sp|sn|sm|sl|sj|sh|sg|sf|se|sd|cf|cd|cc|ci 4|ch 4|cf 4)\s+(?:cf|cd|cc|sf|sg|sj|sl|ch 4|cf 4)\b", value))
    if (has_sae_multigrade or has_sae_mono) and (has_api_literal or has_api_pair):
        return "M", "sae_grade_plus_performance_class_in_certified_product_name"
    if (has_sae_multigrade or has_sae_mono) and (" oil " in value or " lube " in value or " lubricant " in value):
        return "M", "sae_grade_plus_oil_or_lube_in_certified_product_name"
    if has_api_literal and re.search(r"\b(?:hd|super)\s*[- ]?(?:30|40|50)\b", value):
        return "M", "api_class_plus_engine_grade_designation_in_certified_product_name"
    if " api " in value and (" oil " in value or " lube " in value or " lubricant " in value):
        return "M", "api_class_plus_oil_or_lube_in_certified_product_name"
    if " gear " in value and (" oil " in value or re.search(r"\b(?:75|80|85)w[- /]?\d{2,3}\b", value) or " gl 4 " in value or " gl 5 " in value):
        return "T", "gear_designation_plus_grade_or_oil_in_certified_product_name"
    if any(token in value for token in (" lubricant ", " lubricating oil ", " penetrating oil ", " white oil ", " rust preventive oil ")):
        return "S", "explicit_specialty_lubricant_product_name"
    return None


def technical(product_name: str, family: str) -> dict:
    upper = clean(product_name).upper().replace("–", "-").replace("—", "-")
    upper = re.sub(r"\bENGINEOIL\b", "ENGINE OIL", upper)
    upper = re.sub(r"\bOILAPI\b", "OIL API", upper)
    upper = re.sub(r"\bOIL(?=\d)", "OIL ", upper)
    upper = upper.replace("LBRICANT", "LUBRICANT")
    sae = sorted({f"{a}W-{b}" for a, b in re.findall(r"(?<!\d)(0|5|10|15|20|25)W[- /]?([2345]0)(?!\d)", upper)})
    sae_monograde = sorted(set(re.findall(r"\bSAE\s*(20W|15W|10W|5W|20|30|40|50|60)\b", upper)))
    sae_monograde = [value for value in sae_monograde if not any(grade.startswith(value + "-") for grade in sae)]
    sae_gear = sorted({f"{a}W-{b}" for a, b in re.findall(r"(?<!\d)(70|75|80|85)W[- /]?(90|110|140|190|250)(?!\d)", upper)})
    sae_gear.extend(f"SAE {value}" for value in re.findall(r"\b(?:SAE\s*)?(?:EP[- ]?)?(90|110|140|190|250)\b", upper) if family == "T")
    api = []
    for match in re.finditer(r"\bAPI\s*[:,]?\s*([^;()]{1,30})", upper):
        api.extend(re.findall(r"\b(SP|SN(?:\s+PLUS)?|SM|SL|SJ|SH|SG|SF|SE|SD|SC|SB|SA|CK[- ]?4|CJ[- ]?4|CI[- ]?4\+?|CH[- ]?4|CG[- ]?4|CF[- ]?4|CF|CE|CD|CC|FA[- ]?4|TD|TC|TB|TA)\b", match.group(1)))
    normalized_api = []
    for value in api:
        value = re.sub(r"^(C(?:I|J|K|H|G|F)|FA)[- ]?4", r"\1-4", value)
        value = value.replace("+", " PLUS")
        normalized_api.append(value)
    api_gl = sorted({f"GL-{value}" for value in re.findall(r"\bGL\s*[- ]?\s*([1-6])\b", upper)})
    acea = sorted(set(re.findall(r"\b(?:ACEA\s*)?([ACE][0-9](?:/[BCE][0-9])?(?:-[0-9]{2})?|A[0-9]/B[0-9])\b", upper)))
    ilsac = sorted({f"GF-{value}" for value in re.findall(r"\b(?:ILSAC\s*)?GF[- ]?([1-7])\b", upper)})
    jaso = sorted(set(re.findall(r"\bJASO\s*(MA2|MA|MB|FD|FC|FB|FA|DL-1|DH-2|DH-1)\b", upper)))
    iso_explicit = sorted(set(re.findall(r"\bISO\s*(?:VG)?\s*(15|22|32|46|68|100|150|220|320|460|680|1000|1500)\b", upper)))
    iso_inferred = []
    if family in {"H", "I", "C", "U", "E"} and not iso_explicit:
        match = re.search(r"(?:^|\D)(15|22|32|46|68|100|150|220|320|460|680|1000|1500)\s*$", upper)
        if match:
            iso_inferred = [match.group(1)]
    nlgi_explicit = sorted(set(re.findall(r"\bNLG[IT]\s*(?:GRADE\s*)?(000|00|0|1|2|3|4|5|6)\b", upper)))
    nlgi_inferred = []
    if family == "G" and not nlgi_explicit:
        match = re.search(r"\b(?:EP|GRADE)\s*[- ]?(00|0|[1-6])\b", upper)
        if match:
            nlgi_inferred = [match.group(1)]
    thickeners = sorted({token for token in ("LITHIUM", "SODIUM", "CALCIUM") if token in upper})
    dot = sorted({f"DOT {value}" for value in re.findall(r"\bDOT[- ]*([345])\b", upper)})
    dexron = sorted({f"DEXRON {value}" for value in re.findall(r"\bDEXT?RON\s*(II|III|VI)\b", upper)})
    temperature_c = sorted({int(value) for value in re.findall(r"(-?\d{1,2})\s*°?C\b", upper)})
    base_oil_grade = sorted(set(re.findall(r"\b(?:SN|BS)\s*(70|100|150|500)\b", upper))) if family == "I" else []
    return {
        "sae": sorted(set(sae)),
        "sae_monograde": sorted(set(sae_monograde)),
        "sae_gear": sorted(set(sae_gear)),
        "api": sorted(set(normalized_api)),
        "api_gl": api_gl,
        "acea": acea,
        "ilsac": ilsac,
        "jaso": jaso,
        "iso_vg_explicit": iso_explicit,
        "iso_vg_designation_inferred": iso_inferred,
        "nlgi_explicit": nlgi_explicit,
        "nlgi_designation_inferred": nlgi_inferred,
        "grease_thickener_source_reported": thickeners,
        "dot": dot,
        "dexron": dexron,
        "temperature_c": temperature_c,
        "base_oil_grade": base_oil_grade,
    }


def merged_technical(rows: list[dict]) -> dict:
    merged: dict[str, list] = {}
    for row in rows:
        for key, values in technical(row["product_name"], row["family_code"]).items():
            merged.setdefault(key, []).extend(values)
    return {key: sorted(set(values)) for key, values in merged.items()}


def main() -> None:
    source_pdf = fetch_pdf()
    certificate_rows, page_count = extract_certificate_rows()
    occurrences = []
    for row in certificate_rows:
        for ordinal, designation in enumerate(split_designations(row["product_cell"]), 1):
            classified = family_for(designation)
            if not classified:
                continue
            family, basis = classified
            occurrences.append({
                **row,
                "product_ordinal": ordinal,
                "product_name": designation,
                "family_code": family,
                "classification_basis": basis,
            })

    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in occurrences:
        grouped[(normalize(row["company"]), product_identity_name(row["product_name"]), row["family_code"])].append(row)

    records = []
    for key, rows in sorted(grouped.items()):
        first = min(rows, key=lambda row: (row["source_number"], row["product_ordinal"]))
        identity = "|".join(key)
        records.append({
            "source_id": SOURCE_ID,
            "source_record_id": "SON-MANCAP-CHEM-" + hashlib.sha256(identity.encode()).hexdigest()[:16].upper(),
            "source_url": SOURCE_URL,
            "source_context_url": SOURCE_CONTEXT_URL,
            "dataset_snapshot_date": SNAPSHOT_DATE,
            "source_list_period": "2024-2029",
            "market": "NG",
            "certification_authority": "Standards Organisation of Nigeria (SON)",
            "manufacturer": first["company"],
            "brand": first["company"],
            "source_company_raw": first["company_raw"],
            "product_name": first["product_name"],
            "family_code": first["family_code"],
            "classification_basis": first["classification_basis"],
            "technical": merged_technical(rows),
            "source_entries": [{
                "source_number": row["source_number"],
                "source_page": row["source_page"],
                "product_ordinal": row["product_ordinal"],
            } for row in sorted(rows, key=lambda item: (item["source_number"], item["product_ordinal"]))],
            "source_occurrence_count": len(rows),
            "lifecycle_status": "listed_in_current_2024_2029_certified_products_pdf",
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "status": "official_public_government_mandatory_product_certification_list_normalized",
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_context_url": SOURCE_CONTEXT_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "source_list_period": "2024-2029",
        "source_pdf_pages": page_count,
        "source_pdf_sha256": hashlib.sha256(source_pdf).hexdigest(),
        "source_certificate_rows": len(certificate_rows),
        "lubricant_scope_certificate_rows": len({row["source_number"] for row in occurrences}),
        "product_designation_occurrences": len(occurrences),
        "normalized_products": len(records),
        "duplicate_product_occurrences_merged": len(occurrences) - len(records),
        "manufacturers": len({row["manufacturer"] for row in records}),
        "lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "technical_coverage": dict(sorted(Counter(key for row in records for key, value in row["technical"].items() if value).items())),
        "normalized_output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "rights_note": "Public MANCAP certification facts only. Company address, state and certification-mark artwork are excluded; the PDF itself and non-scope chemical products are not republished.",
        "excluded_fields": ["company_address", "state", "contacts", "certification_mark_artwork", "non_scope_chemical_products"],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
