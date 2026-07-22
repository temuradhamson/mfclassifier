#!/usr/bin/env python3
"""Normalize the complete product tables in ANP's three 2024 PDF reports.

The reports are born-digital PDFs. Their product tables have no sample-ID
column, so records are anchored on the registration column and reconstructed
from PDF word coordinates. CNPJ, retailer and collection-location columns are
intentionally discarded.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unicodedata
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "anp-brazil-monitoring-pdf-observations.jsonl"
REPORT = ROOT / "data" / "anp-brazil-monitoring-pdf-report.json"
SOURCE_PAGE = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/publicacoes/"
    "boletins-anp/boletins/boletim-de-monitoramento-de-lubrificantes"
)
TERMS_URL = "https://www.gov.br/pt-br/termos-de-uso"
USER_AGENT = "MFClassifierResearch/1.0 (open-government-data research)"


@dataclass(frozen=True)
class ReportProfile:
    key: str
    url: str
    first_page: int
    last_page: int
    expected_published_rows: int
    reported_samples_analyzed: int
    family_hint: str
    product_x0: float
    product_x1: float
    holder_x1: float
    registration_x0: float
    registration_x1: float
    grade_x0: float
    grade_x1: float
    performance_x0: float
    performance_x1: float


PROFILES = (
    ReportProfile(
        key="PML-2024-2",
        url="https://www.gov.br/anp/pt-br/centrais-de-conteudo/publicacoes/boletins-anp/boletim-monitoramento-lubrificantes/2024/boletim-pml-2-2024.pdf",
        first_page=32, last_page=97,
        expected_published_rows=782, reported_samples_analyzed=782,
        family_hint="M", product_x0=55, product_x1=157, holder_x1=258,
        registration_x0=340, registration_x1=385,
        grade_x0=390, grade_x1=440, performance_x0=440, performance_x1=505,
    ),
    ReportProfile(
        key="PML-2024-1",
        url="https://www.gov.br/anp/pt-br/centrais-de-conteudo/publicacoes/boletins-anp/boletim-monitoramento-lubrificantes/2024/boletim-pml-1-2024-v2.pdf",
        first_page=31, last_page=66,
        expected_published_rows=462, reported_samples_analyzed=462,
        family_hint="M", product_x0=55, product_x1=170, holder_x1=289,
        registration_x0=375, registration_x1=410,
        grade_x0=410, grade_x1=450, performance_x0=450, performance_x1=518,
    ),
    ReportProfile(
        key="TRANSMISSION-2024-1",
        url="https://www.gov.br/anp/pt-br/assuntos/qualidade-de-produtos/arquivos-cpt/relatorio-n-1-24-panorama-transmissao.pdf",
        first_page=29, last_page=42,
        expected_published_rows=181, reported_samples_analyzed=190,
        family_hint="T", product_x0=55, product_x1=148, holder_x1=289,
        registration_x0=370, registration_x1=410,
        grade_x0=415, grade_x1=455, performance_x0=453, performance_x1=512,
    ),
)

REGISTRATION_RE = re.compile(r"^(?:\d{1,6}|N\.A\.)$", re.I)
GRADE_RE = re.compile(r"^(?:N\.A\.|\d{1,3}(?:W\d{0,3})?|\d{1,2}W)$", re.I)
MISSING_VALUES = {"", "N A", "N.A", "N.A.", "NA", "NAO IDENTIFICADO", "NAO INFORMADO"}


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -")


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = text.encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9+.-]+", " ", text).strip()


def factual_value(value: str) -> str:
    value = clean(value)
    return "" if normalize(value) in MISSING_VALUES else value


def words_text(words: list[dict]) -> str:
    ordered = sorted(words, key=lambda word: (round(word["top"], 1), word["x0"]))
    return clean(" ".join(word["text"] for word in ordered))


def registration_anchors(words: list[dict], profile: ReportProfile) -> list[dict]:
    anchors = []
    for word in words:
        if not (profile.registration_x0 < word["x0"] < profile.registration_x1):
            continue
        if not REGISTRATION_RE.fullmatch(word["text"]):
            continue
        same_line = [
            candidate for candidate in words
            if abs(candidate["top"] - word["top"]) < 3
            and profile.grade_x0 < candidate["x0"] < profile.grade_x1
            and GRADE_RE.fullmatch(candidate["text"])
        ]
        if same_line:
            anchors.append(word)
    return sorted(anchors, key=lambda word: word["top"])


def extract_performance(words: list[dict], profile: ReportProfile) -> str:
    """Recover the specification while rejecting lot text overprinted on it."""
    raw = normalize(words_text([
        word for word in words
        if profile.performance_x0 <= word["x0"] < profile.performance_x1
    ]))
    if profile.family_hint == "M":
        matches = re.findall(r"(?<![A-Z0-9])(?:CI-4|CH-4|CG-4|CF-4|SL|SN|SM|SP|SJ|ACEA)(?![A-Z0-9])", raw)
        return matches[0] if matches else ""
    if re.search(r"API\s+GL-?4", raw):
        return "API GL-4"
    if re.search(r"API\s+GL-?5", raw):
        return "API GL-5"
    if "ALLISON" in raw and "C4" in raw:
        return "ALLISON C4"
    if re.search(r"MB\s+236[ .]2", raw):
        return "MB 236.2"
    if "TASA" in raw and "SUFIXO A" in raw:
        return "TASA (TIPO A SUFIXO A)"
    if "DEXRON VI" in raw:
        return "DEXRON VI"
    if "DEXRON III" in raw:
        return "DEXRON III H" if re.search(r"(?:^|\s)H(?:\s|$)", raw) else "DEXRON III"
    if "DEXRON II" in raw:
        return "DEXRON II D" if re.search(r"(?:^|\s)D(?:\s|$)", raw) else "DEXRON II"
    return ""


def parse_report(path: Path, profile: ReportProfile, source_sha256: str) -> list[dict]:
    rows = []
    with pdfplumber.open(path) as pdf:
        for page_number in range(profile.first_page, profile.last_page + 1):
            page = pdf.pages[page_number - 1]
            words = page.extract_words(x_tolerance=1, y_tolerance=3)
            anchors = registration_anchors(words, profile)
            tops = [anchor["top"] for anchor in anchors]
            gaps = [right - left for left, right in zip(tops, tops[1:])]
            for page_row, anchor in enumerate(anchors, start=1):
                if page_row == 1:
                    half_gap = gaps[0] / 2 if gaps else 20
                    band_top = max(65, anchor["top"] - half_gap)
                else:
                    band_top = (tops[page_row - 2] + anchor["top"]) / 2
                if page_row < len(anchors):
                    band_bottom = (anchor["top"] + tops[page_row]) / 2
                else:
                    half_gap = gaps[-1] / 2 if gaps else 20
                    band_bottom = anchor["top"] + half_gap
                band = [
                    word for word in words
                    if band_top <= (word["top"] + word["bottom"]) / 2 < band_bottom
                ]
                product_name = words_text([
                    word for word in band
                    if profile.product_x0 <= word["x0"] < profile.product_x1
                ])
                holder = words_text([
                    word for word in band
                    if profile.product_x1 <= word["x0"] < profile.holder_x1
                ])
                same_line = sorted(
                    [word for word in words if abs(word["top"] - anchor["top"]) < 3],
                    key=lambda word: word["x0"],
                )
                grades = [
                    word for word in same_line
                    if profile.grade_x0 < word["x0"] < profile.grade_x1
                    and GRADE_RE.fullmatch(word["text"])
                ]
                if len(grades) != 1:
                    raise ValueError(f"{profile.key} page {page_number}: expected one SAE anchor, found {grades}")
                performance = extract_performance(band, profile)
                registration = factual_value(anchor["text"])
                grade = factual_value(grades[0]["text"])
                product_name = factual_value(product_name)
                holder = factual_value(holder)
                performance = factual_value(performance)
                if not product_name or not holder or not (registration or grade or performance):
                    raise ValueError(
                        f"{profile.key} page {page_number} row {page_row}: incomplete factual row "
                        f"{(product_name, holder, registration, grade, performance)}"
                    )
                locator = f"{source_sha256}:{page_number}:{page_row}"
                rows.append({
                    "source_id": "ANP_BRAZIL_LUBRICANT_MONITORING_PDF_HISTORY",
                    "source_record_id": f"ANP-PML-PDF-{hashlib.sha256(locator.encode()).hexdigest()[:18]}",
                    "source_page_url": SOURCE_PAGE,
                    "source_url": profile.url,
                    "source_file_sha256": source_sha256,
                    "source_file_name": path.name,
                    "source_page": page_number,
                    "source_page_row": page_row,
                    "snapshot_date": date.today().isoformat(),
                    "issue_year": 2024,
                    "market": "Brazil",
                    "sample_id": "",
                    "product_name": product_name,
                    "registration_holder": holder,
                    "registration_number": registration,
                    "sae": grade,
                    "performance_level": performance,
                    "family_hint": profile.family_hint,
                    "published_scope": "complete_analyzed_products_list",
                    "quality_flags": [],
                    "lifecycle_status": "historical_market_sample_observation",
                })
    if len(rows) != profile.expected_published_rows:
        raise ValueError(f"{profile.key}: parsed {len(rows)} rows, expected {profile.expected_published_rows}")
    return rows


def main() -> None:
    all_rows = []
    files = []
    with tempfile.TemporaryDirectory(prefix="anp-pml-pdf-") as temporary:
        directory = Path(temporary)
        for profile in PROFILES:
            payload = download(profile.url)
            source_sha256 = hashlib.sha256(payload).hexdigest()
            path = directory / f"{profile.key}.pdf"
            path.write_bytes(payload)
            rows = parse_report(path, profile, source_sha256)
            all_rows.extend(rows)
            files.append({
                "report_key": profile.key,
                "source_url": profile.url,
                "source_sha256": source_sha256,
                "published_product_rows": len(rows),
                "reported_samples_analyzed": profile.reported_samples_analyzed,
                "published_minus_reported": len(rows) - profile.reported_samples_analyzed,
                "product_table_pages": [profile.first_page, profile.last_page],
            })

    all_rows.sort(key=lambda row: (row["source_url"], row["source_page"], row["source_page_row"]))
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_rows)
    OUTPUT.write_text(output_text, encoding="utf-8")
    identity_fields = ("registration_number", "product_name", "sae", "performance_level", "registration_holder")
    identities = {tuple(normalize(row[field]) for field in identity_fields) for row in all_rows}
    report = {
        "schema_version": 1,
        "status": "official_open_government_pdf_monitoring_tables_normalized",
        "snapshot_date": date.today().isoformat(),
        "source_page_url": SOURCE_PAGE,
        "terms_url": TERMS_URL,
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "official_pdf_files": len(files),
        "files": files,
        "source_observations": len(all_rows),
        "normalized_product_grade_holder_identities": len(identities),
        "observations_by_family_hint": dict(sorted(Counter(row["family_hint"] for row in all_rows).items())),
        "rights_note": "ANP publishes the reports on gov.br. Only normalized factual fields and provenance are republished; PDF layout, narrative, CNPJ and collection-location fields are omitted.",
        "scope_note": "Complete product tables published in the two 2024 PML motor-oil bulletins and the 2024 automotive-transmission panorama. The transmission report states 190 analyzed samples but publishes 181 machine-extractable product rows; the nine-row source discrepancy is retained and no rows are invented.",
        "correction_note": "The second-version transmission PDF contains ANP-issued corrections. This ingest reads the corrected document as published, including DULUB HIPOIDE registration 12340; it does not reconstruct superseded values.",
        "lifecycle_note": "A monitoring observation proves that a labelled sample existed and was analysed. It is historical evidence, not proof of current registration or market availability.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
