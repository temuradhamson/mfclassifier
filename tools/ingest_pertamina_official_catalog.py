#!/usr/bin/env python3
"""Normalize current factual product-grade rows from Pertamina Lubricants."""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "pertamina-official-lubricant-products.jsonl"
REPORT = ROOT / "data" / "pertamina-official-lubricant-products-report.json"
SOURCE_ID = "PERTAMINA_LUBRICANTS_OFFICIAL_CATALOG"
BASE_URL = "https://www.pertaminalubricants.com"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
PRIVACY_URL = f"{BASE_URL}/page/detail/policy"
INDUSTRY_URL = f"{BASE_URL}/industry/industry_produk"
PDS_BASE_URL = f"{BASE_URL}/assets/uploads/industry/pdf/"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (government product-classification research)"

INDUSTRY_FAMILIES = {
    8: "M", 9: "M", 10: "M", 11: "T", 12: "C", 13: "H", 14: "T",
    15: "U", 16: "C", 17: "I", 18: "I", 19: "G",
}
SPECIALTY_FAMILIES = {
    **{product_id: "I" for product_id in range(85, 97)},
    97: "TF", 98: "S", 99: "S", 101: "TF", 102: "E", 103: "E",
    104: "TF", 105: "TF", 106: "TF", 107: "TF", 108: "TF", 109: "TF",
}
AUTOMOTIVE_FAMILIES = {1: "M", 2: "M", 5: "M", 6: "T"}
EXACT_NAME_PREFIX_IDS = set(range(18, 37)) | {69, 70, 72, 74}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def clean(fragment: str) -> str:
    without_scripts = re.sub(r"<(?:script|style)\b.*?</(?:script|style)>", " ", fragment, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", without_scripts))).strip()


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.casefold())).strip()


def pdf_text(payload: bytes) -> str:
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        return "\n".join(page.extract_text(x_tolerance=1, y_tolerance=3) or "" for page in pdf.pages)


def grade_tokens(value: str) -> list[str]:
    value = re.sub(r"(\d{1,2}W)\s*-\s*(\d{2})", r"\1-\2", value.upper())
    values = []
    for token in value.split():
        token = token.strip(" ,;:")
        if re.fullmatch(r"(?:\d{1,2}W(?:-\d{2})?|\d{1,4})", token):
            values.append(token)
        else:
            break
    return values


def pds_grades(source_id: int, text: str) -> tuple[str, list[str]]:
    matches: list[tuple[str, list[str]]] = []
    for kind, label in (("sae_engine", "SAE Viscosity Grade"), ("iso_vg", "ISO Viscosity Grade"), ("nlgi", "NLGI Number")):
        for match in re.finditer(rf"{re.escape(label)}\s*-\s*([^\n]+)", text, flags=re.I):
            values = grade_tokens(match.group(1))
            if values:
                matches.append((kind, values))
    if source_id == 60:
        match = re.search(r"Series\s*-\s*([^\n]+)", text, flags=re.I)
        assert match
        return "source_variant", grade_tokens(match.group(1))
    if not matches:
        return "", [""]
    kinds = {kind for kind, _ in matches}
    assert len(kinds) == 1, (source_id, kinds)
    values = []
    for _, group in matches:
        values.extend(group)
    return matches[0][0], list(dict.fromkeys(values))


def pds_header(text: str) -> str:
    match = re.search(r"^Characteristics Test Method\s+(.+)$", text, flags=re.M)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def exact_names(source_id: int, header: str, grades: list[str]) -> list[str] | None:
    if source_id not in EXACT_NAME_PREFIX_IDS:
        return None
    if 18 <= source_id <= 27:
        values = re.findall(r"MED(?:RIP|IPR)AL\s+[A-Z0-9]+", header, flags=re.I)
    elif 28 <= source_id <= 35:
        values = re.findall(r"SALYX\s+[A-Z0-9]+", header, flags=re.I)
    elif source_id == 36:
        values = re.findall(r"DILOKA\s+[A-Z0-9]+", header, flags=re.I)
    elif source_id == 69:
        values = re.findall(r"SEBANA\s+[A-Z0-9]+", header, flags=re.I)
    elif source_id == 70:
        values = re.findall(r"MEDRIPAL\s+[A-Z0-9]+", header, flags=re.I)
    elif source_id == 72:
        values = re.findall(r"SILINAP\s+[A-Z0-9]+", header, flags=re.I)
    else:
        values = re.findall(r"TERMO\s+[A-Z0-9]+", header, flags=re.I)
    values = [re.sub(r"\s+", " ", value).strip() for value in values]
    assert len(values) == len(grades), (source_id, values, grades, header)
    return values


def base_product_name(source: dict, header: str) -> str:
    source_id = int(source["id"])
    if source_id == 55:
        return "TURALIK"
    if header and len(set(header.split())) > 1:
        return re.sub(r"\s+SERIES$", "", header, flags=re.I).strip()
    value = source.get("series_name") or source["product_name"]
    return re.sub(r"\s+SERIES$", "", value, flags=re.I).strip()


def product_name(source: dict, header: str, kind: str, grade: str, exact: str | None) -> str:
    if exact:
        return exact
    if not grade:
        return re.sub(r"\s+", " ", source["product_name"]).strip()
    base = base_product_name(source, header)
    if not grade:
        return base
    label = {
        "sae_engine": "SAE",
        "sae_gear": "SAE",
        "iso_vg": "ISO VG",
        "nlgi": "NLGI",
        "source_variant": "",
    }[kind]
    return " ".join(value for value in (base, label, grade) if value)


API_CLASS = re.compile(
    r"\b(?:C(?:A|B|C|D(?:-II)?|E|F(?:-[24])?|G-4|H-4|I-4(?:\s*PLUS)?|J-4|K-4)|"
    r"FA-4|S[ABCDEFGHJKLMNPR](?:\s*PLUS|-RC)?|TC)\b",
    flags=re.I,
)


def normalized_specs(text: str, grade_kind: str, grade: str, source_claim: str = "") -> dict:
    upper = text.upper()
    api: set[str] = set()
    for match in re.finditer(r"\bAPI\s+([^\n•|]{1,80})", upper):
        for value in API_CLASS.findall(match.group(1)):
            api.add(re.sub(r"\s+", " ", value.upper()).replace("CI-4PLUS", "CI-4 PLUS"))
    specs: dict[str, object] = {
        "api": sorted(api),
        "api_gl": sorted(set(re.findall(r"\bGL-[45]\b", upper))),
        "acea": sorted(set(re.findall(r"\b(?:E[2-9](?:-\d{2})?|A[1-5]/B[1-5])\b", upper))),
        "jaso": sorted(set(re.findall(r"\b(?:MA2|MA|MB|DH-1|DL-1|FB|FC|FD)\b", upper))),
        "ilsac": sorted(set(re.findall(r"\bGF-[0-9][A-Z]?\b", upper))),
    }
    if source_claim and source_claim not in {"-", "Meets below performance level of :"}:
        specs["standards_and_approvals_source_reported"] = [source_claim]
    if grade_kind and grade:
        specs[grade_kind] = grade
    return specs


def factual_page_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def industrial_occurrences() -> tuple[list[dict], dict]:
    occurrences = []
    endpoint_hashes = []
    document_hashes = []
    for category_id in range(8, 21):
        endpoint = f"{BASE_URL}/industry/getSupportDataProduk/{category_id}"
        payload = fetch(endpoint)
        source_rows = json.loads(payload)["data"]
        endpoint_projection = [{
            key: row.get(key) for key in (
                "id", "product_name", "subcategory_id", "series_id", "files",
                "subcategory_name", "series_group_name", "series_name", "sertifikasi_en",
            )
        } for row in source_rows]
        endpoint_hashes.append(f"{endpoint}|{factual_page_hash(endpoint_projection)}")
        for source in source_rows:
            source_id = int(source["id"])
            assert int(source["subcategory_id"]) == category_id
            pds_url = PDS_BASE_URL + urllib.parse.quote(source["files"])
            pds_payload = fetch(pds_url)
            assert pds_payload.startswith(b"%PDF"), pds_url
            pds_sha = hashlib.sha256(pds_payload).hexdigest()
            document_hashes.append(f"{pds_url}|{pds_sha}")
            text = pdf_text(pds_payload)
            kind, grades = pds_grades(source_id, text)
            if category_id == 11 and kind == "sae_engine":
                kind = "sae_gear"
            header = pds_header(text)
            names = exact_names(source_id, header, grades)
            family = INDUSTRY_FAMILIES.get(category_id) or SPECIALTY_FAMILIES[source_id]
            claim = clean(source.get("sertifikasi_en") or "")
            pds_title_mismatch = source_id == 99 and normalize(header) == "rusguard lube x"
            for index, grade in enumerate(grades):
                name = product_name(source, header, kind, grade, names[index] if names else None)
                specs = normalized_specs("" if pds_title_mismatch else text, kind, grade, claim)
                if source_id == 97:
                    specs["brake_fluid_class"] = "DOT 3"
                occurrence_id = f"industry:{source_id}:{kind}:{grade or 'ungraded'}"
                occurrences.append({
                    "occurrence_id": occurrence_id,
                    "source_channel": "current_industrial_catalog_api_and_linked_pds",
                    "source_card_id": str(source_id),
                    "source_series_id": source["series_id"],
                    "source_url": INDUSTRY_URL,
                    "source_api_url": endpoint,
                    "technical_document_url": pds_url,
                    "technical_document_sha256": pds_sha,
                    "technical_document_evidence_status": "linked_document_title_mismatch_not_used_as_technical_evidence" if pds_title_mismatch else "linked_current_pds",
                    "product_name": name,
                    "source_product_name": source["product_name"],
                    "family_code": family,
                    "source_grade_kind": kind,
                    "source_grade": grade,
                    "specifications": specs,
                    "source_quality_flags": ["linked_pds_title_conflicts_with_current_product_card"] if pds_title_mismatch else [],
                })
    return occurrences, {
        "source_industrial_cards": len({row["source_card_id"] for row in occurrences}),
        "source_industrial_pds_documents": len(document_hashes),
        "industrial_endpoint_factual_projection_sha256": hashlib.sha256("\n".join(sorted(endpoint_hashes)).encode()).hexdigest(),
        "industrial_pds_aggregate_sha256": hashlib.sha256("\n".join(sorted(document_hashes)).encode()).hexdigest(),
        "industrial_product_grade_occurrences": len(occurrences),
    }


def automotive_values(page_html: str, label: str) -> list[str]:
    return [
        clean(value) for value in re.findall(
            rf"<span>{re.escape(label)}</span>.*?<p><b>(.*?)</b></p>", page_html, flags=re.I | re.S,
        )
    ]


def automotive_occurrences() -> tuple[list[dict], dict]:
    occurrences = []
    page_hashes = []
    source_cards = 0
    excluded = []
    for category_id in (1, 2, 5, 6):
        page_url = f"{BASE_URL}/automotive/detail_pelumas/{category_id}"
        page_html = fetch(page_url).decode(errors="replace")
        names = [
            clean(value) for value in re.findall(
                r'<p style="font-size:14px.*?">(.*?)</p>', page_html, flags=re.I | re.S,
            )
        ]
        grades = automotive_values(page_html, "Consistency/SAE")
        base_oils = automotive_values(page_html, "Base Oil")
        claims = automotive_values(page_html, "Spesifikasi")
        assert len(names) == len(grades) == len(base_oils) == len(claims), (category_id, len(names), len(grades), len(base_oils), len(claims))
        source_cards += len(names)
        projection = list(zip(names, grades, base_oils, claims))
        page_hashes.append(f"{page_url}|{factual_page_hash(projection)}")
        for index, (name, grade, base_oil, claim) in enumerate(projection, 1):
            if category_id == 5 and normalize(name) == "meditran sx" and grade == "-":
                excluded.append({"source_url": page_url, "product_name": name, "reason": "ungraded_series_card_with_current_graded_industrial_products"})
                continue
            kind = "sae_engine" if grade != "-" else ""
            grade = "" if grade == "-" else grade.upper()
            specs = normalized_specs(claim, kind, grade, claim)
            if base_oil != "-":
                specs["base_oil_source_reported"] = base_oil
            occurrences.append({
                "occurrence_id": f"automotive:{category_id}:{index}",
                "source_channel": "current_automotive_product_page",
                "source_card_id": f"automotive-{category_id}-{index}",
                "source_series_id": "",
                "source_url": page_url,
                "source_api_url": "",
                "technical_document_url": "",
                "technical_document_sha256": "",
                "technical_document_evidence_status": "not_linked_on_current_automotive_product_page",
                "product_name": name,
                "source_product_name": name,
                "family_code": "T" if normalize(name) == "enduro gear matic" else AUTOMOTIVE_FAMILIES[category_id],
                "source_grade_kind": kind,
                "source_grade": grade,
                "specifications": specs,
                "source_quality_flags": [],
            })
    return occurrences, {
        "source_automotive_cards": source_cards,
        "automotive_product_occurrences_retained": len(occurrences),
        "automotive_series_cards_excluded": excluded,
        "automotive_page_factual_projection_sha256": hashlib.sha256("\n".join(sorted(page_hashes)).encode()).hexdigest(),
    }


def identity_name(row: dict) -> str:
    value = normalize(row["product_name"])
    value = re.sub(r"\b(?:sae|iso vg|nlgi)\b", " ", value)
    grade = normalize(row["source_grade"])
    if grade:
        value = re.sub(rf"\b{re.escape(grade)}\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def merge_occurrences(occurrences: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for row in occurrences:
        key = (
            identity_name(row), row["family_code"], row["source_grade_kind"], normalize(row["source_grade"]),
        )
        grouped.setdefault(key, []).append(row)
    result = []
    for key, values in grouped.items():
        preferred = next((row for row in values if row["source_channel"].startswith("current_industrial")), values[0])
        specs: dict[str, object] = {}
        for row in values:
            for spec_key, spec_value in row["specifications"].items():
                if isinstance(spec_value, list):
                    specs[spec_key] = sorted(set(specs.get(spec_key, [])) | set(spec_value))
                elif spec_value and not specs.get(spec_key):
                    specs[spec_key] = spec_value
        record_key = "|".join(str(value) for value in key)
        result.append({
            "source_id": SOURCE_ID,
            "source_record_id": "PERTAMINA-" + hashlib.sha256(record_key.encode()).hexdigest()[:16].upper(),
            "brand": "PERTAMINA",
            "manufacturer": "PT Pertamina Lubricants",
            "market": "ID",
            "family_code": preferred["family_code"],
            "product_name": preferred["product_name"],
            "source_product_names": sorted({row["source_product_name"] for row in values}, key=str.casefold),
            "source_grade": preferred["source_grade"],
            "source_grade_kind": preferred["source_grade_kind"],
            "source_occurrence_count": len(values),
            "source_occurrences": sorted(({
                key: row[key] for key in (
                    "occurrence_id", "source_channel", "source_card_id", "source_series_id",
                    "source_url", "source_api_url", "technical_document_url", "technical_document_sha256",
                    "technical_document_evidence_status",
                )
            } for row in values), key=lambda row: row["occurrence_id"]),
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_current_official_catalog",
            "access_status": "public_official_catalog_attributed_nonexpressive_factual_fields_only",
            "specifications": specs,
            "source_quality_flags": sorted({flag for row in values for flag in row["source_quality_flags"]}),
        })
    return sorted(result, key=lambda row: (row["family_code"], normalize(row["product_name"]), row["source_record_id"]))


def main() -> None:
    robots_payload = fetch(ROBOTS_URL)
    privacy_payload = fetch(PRIVACY_URL)
    industry_page = fetch(INDUSTRY_URL)
    robots = robots_payload.decode(errors="replace")
    assert "User-agent: *" in robots and re.search(r"User-agent:\s*\*\s*Disallow:\s*(?:\r?\n|$)", robots)
    assert "Kebijakan & Privasi" in clean(privacy_payload.decode(errors="replace"))
    assert "getSupportDataProduk" in industry_page.decode(errors="replace")

    industrial, industrial_report = industrial_occurrences()
    automotive, automotive_report = automotive_occurrences()
    assert industrial_report["source_industrial_cards"] == 104
    assert industrial_report["source_industrial_pds_documents"] == 104
    assert industrial_report["industrial_product_grade_occurrences"] == 231
    assert automotive_report["source_automotive_cards"] == 22
    assert automotive_report["automotive_product_occurrences_retained"] == 21
    occurrences = industrial + automotive
    rows = merge_occurrences(occurrences)
    assert len(occurrences) == 252
    assert len(rows) == 250, len(rows)
    assert Counter(row["source_occurrence_count"] for row in rows) == {1: 248, 2: 2}
    assert len({row["source_record_id"] for row in rows}) == len(rows)
    assert sum(row["source_occurrence_count"] for row in rows) == len(occurrences)
    assert all(not ({"description", "marketing_text", "image", "artwork", "document_text"} & set(row)) for row in rows)

    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "robots_url": ROBOTS_URL,
        "privacy_url": PRIVACY_URL,
        "industry_url": INDUSTRY_URL,
        "robots_text_sha256": hashlib.sha256(clean(robots).encode()).hexdigest(),
        "privacy_text_sha256": hashlib.sha256(clean(privacy_payload.decode(errors="replace")).encode()).hexdigest(),
        **industrial_report,
        **automotive_report,
        "source_product_occurrences_retained": len(occurrences),
        "normalized_product_grade_rows": len(rows),
        "within_source_repeat_occurrences_merged": len(occurrences) - len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "grade_kinds": dict(sorted(Counter(row["source_grade_kind"] or "ungraded" for row in rows).items())),
        "output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "rights_posture": "public_official_catalog_no_product_data_reuse_terms_located_at_snapshot_attributed_nonexpressive_factual_fields_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
