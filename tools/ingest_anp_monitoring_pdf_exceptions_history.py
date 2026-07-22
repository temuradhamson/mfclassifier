#!/usr/bin/env python3
"""Normalize product exceptions published in ANP PML PDFs from 2007-2017.

Unlike the complete 2024 product tables, these appendices publish only samples
reported as nonconforming on registration, labelling or quality.  The scope is
therefore explicit on every row and must not be interpreted as a complete list
of products sampled by the programme.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import tempfile
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "anp-brazil-monitoring-pdf-exceptions.jsonl"
REPORT = ROOT / "data" / "anp-brazil-monitoring-pdf-exceptions-report.json"
SOURCE_PAGE = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/publicacoes/"
    "boletins-anp/boletins/boletim-de-monitoramento-de-lubrificantes"
)
TERMS_URL = "https://www.gov.br/pt-br/termos-de-uso"
USER_AGENT = "MFClassifierResearch/1.0 (open-government-data research)"
TARGET_YEARS = set(range(2007, 2018))

SECTION_FLAGS = {
    "registration": "source_reported_registration_nonconformity",
    "label": "source_reported_label_nonconformity",
    "quality": "source_reported_quality_nonconformity",
}
MISSING_VALUES = {"", "N A", "N.A", "N.A.", "NA", "NI", "NAO IDENTIFICADO", "NAO INFORMADO"}
SAE_RE = re.compile(r"^(?:\d{1,3}(?:W\d{0,3})?|\d{1,2}W)$", re.I)
API_RE = re.compile(
    r"^(?:ACEA|ND|(?:S[AEFGHJKLMNP]|C[ABCDFGHJK](?:-?\d)?|CI-4|CH-4|CG-4|CF-4|CF-2)"
    r"(?:/(?:S[AEFGHJKLMNP]|C[ABCDFGHJK](?:-?\d)?|CI-4|CH-4|CG-4|CF-4|CF-2))*)$",
    re.I,
)
COMPANY_MARKERS_RE = re.compile(
    r"\b(?:LTDA|S\.?A\.?|INDUSTR|COMERC|LUBRIFIC|PETROLEO|PRODUTOS|COMPANHIA|"
    r"DISTRIBUIDORA|FABRICA|COSAN|CASTROL|CHEVRON|IPIRANGA|RAIZEN|VIBRA|AGECOM|DUNAX)\b",
    re.I,
)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -")


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = text.encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9+./-]+", " ", text).strip()


def factual_value(value: str) -> str:
    value = clean(value)
    return "" if normalize(value) in MISSING_VALUES else value


def sample_id_normalization_method(sample_id: str, printed: str) -> str:
    printed_normalized = normalize(printed)
    if printed_normalized == sample_id:
        return "published_complete"
    if re.fullmatch(r"M\d{1,5}", printed_normalized, re.I):
        return "issue_year_appended_from_report_context"
    if re.fullmatch(r"M\d{1,5}/\d{2}", printed_normalized, re.I):
        return "two_digit_year_expanded_from_report_context"
    return "split_year_fragments_rejoined_from_same_pdf_cell"


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


class PdfLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        url = urljoin(SOURCE_PAGE, href)
        path = urlparse(url).path.lower()
        year_match = re.search(r"/(20\d{2})/", path)
        year = int(year_match.group(1)) if year_match else None
        if path.endswith(".pdf") and "boletim-pml" in path and year in TARGET_YEARS:
            self.urls.append(url)


def sample_pattern(year: int) -> re.Pattern:
    if year <= 2008:
        return re.compile(r"^\d{3,5}$")
    if year <= 2014:
        return re.compile(r"^M\d{1,5}(?:/(?:\d{2}|20\d{2}))?$", re.I)
    return re.compile(r"^CPT/ML\d{1,6}/20\d{2}$", re.I)


def section_from_text(text: str) -> str | None:
    lines = [normalize(line).replace("-", " ") for line in text.splitlines() if line.strip()]
    windows = lines + [f"{left} {right}" for left, right in zip(lines, lines[1:])]
    candidates = [
        line for line in windows
        if "LISTA" in line and re.search(r"NAO[^A-Z0-9]*CONFORM", line)
    ]
    for line in candidates:
        if "QUALIDADE" in line:
            return "quality"
    for line in candidates:
        if "ROTULO" in line:
            return "label"
    for line in candidates:
        if "REGISTRO" in line:
            return "registration"
    return None


def word_center(word: dict) -> float:
    return (word["x0"] + word["x1"]) / 2


def line_groups(words: list[dict]) -> list[tuple[float, list[dict]]]:
    groups: list[tuple[float, list[dict]]] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        if not groups or abs(groups[-1][0] - word["top"]) > 2.5:
            groups.append((word["top"], [word]))
        else:
            groups[-1][1].append(word)
    return groups


def words_text(words: list[dict]) -> str:
    ordered = sorted(words, key=lambda word: (round(word["top"], 1), word["x0"]))
    return clean(" ".join(word["text"] for word in ordered))


def anchors_on_page(words: list[dict], year: int) -> list[dict]:
    pattern = sample_pattern(year)
    if 2009 <= year <= 2014:
        candidates = []
        for index, word in enumerate(words):
            printed = normalize(word["text"])
            match = re.fullmatch(r"(M\d{1,5})(?:/(\d{2,4}))?/?", printed, re.I)
            if not match:
                continue
            stem, suffix = match.groups()
            anchor = dict(word)
            printed_parts = [clean(word["text"])]
            expected_tail = ""
            if printed.endswith("/") and suffix is None:
                expected_tail = str(year)
            elif suffix and str(year).startswith(suffix) and suffix != str(year):
                expected_tail = str(year)[len(suffix):]
            if expected_tail:
                # Some born-digital PDFs put the year on a second line inside
                # the same CPT cell (for example M1042/ + 2014 or
                # M0794/201 + 1).
                for following in words:
                    following_text = normalize(following["text"])
                    if (
                        following_text == expected_tail
                        and abs(word_center(following) - word_center(word)) <= 12
                        and 0 <= following["top"] - word["top"] <= 18
                    ):
                        suffix = (suffix or "") + following_text
                        printed_parts.append(clean(following["text"]))
                        anchor["x0"] = min(anchor["x0"], following["x0"])
                        anchor["x1"] = max(anchor["x1"], following["x1"])
                        anchor["bottom"] = max(anchor["bottom"], following["bottom"])
                        break
            if suffix and suffix not in {str(year), str(year)[-2:]}:
                continue
            anchor["text"] = f"{stem.upper()}/{year}"
            anchor["printed_text"] = " ".join(printed_parts)
            candidates.append(anchor)
    else:
        candidates = [word for word in words if pattern.fullmatch(normalize(word["text"]))]
        for candidate in candidates:
            candidate["printed_text"] = clean(candidate["text"])
    if year <= 2008:
        # Old reports use a bare numeric CPT.  The actual CPT column is the
        # narrowest repeated x-position among 3-5 digit tokens below the header.
        candidates = [word for word in candidates if word["top"] > 120]
        x_bins = Counter(round(word_center(word) / 4) * 4 for word in candidates)
        repeated = [x for x, count in x_bins.items() if count >= 2]
        if not repeated:
            return []
        cpt_x = max(repeated, key=lambda x: (x_bins[x], -x))
        candidates = [word for word in candidates if abs(word_center(word) - cpt_x) <= 8]
    return sorted(candidates, key=lambda word: word["top"])


def header_center(words: list[dict], token: str, before_top: float) -> float | None:
    matches = [
        word_center(word) for word in words
        if word["top"] < before_top - 12 and normalize(word["text"]).rstrip(".") == token
    ]
    return matches[-1] if matches else None


def derive_columns(words: list[dict], anchors: list[dict]) -> dict:
    first_top = anchors[0]["top"]
    sample_x = statistics.median(word_center(anchor) for anchor in anchors)
    company_x = header_center(words, "EMPRESA", first_top)
    product_x = header_center(words, "MARCA", first_top)
    sae_x = header_center(words, "SAE", first_top)
    api_x = header_center(words, "API", first_top)
    if product_x is None:
        product_x = max(65, sample_x - 90)
    product_left = 45 if company_x is None else (company_x + product_x) / 2
    product_right = (product_x + sample_x) / 2
    return {
        "sample_x": sample_x,
        "company_left": 35,
        "company_right": product_left,
        "product_left": product_left,
        "product_right": product_right,
        "sae_x": sae_x,
        "api_x": api_x,
        "has_company_column": company_x is not None,
    }


def cell_words(
    words: list[dict],
    rects: list[dict],
    anchor: dict,
    left: float,
    right: float,
    fallback_top: float,
    fallback_bottom: float,
) -> list[dict]:
    """Return words from the table cell containing an anchor.

    Newer reports use merged company/product cells spanning several CPT rows.
    Their horizontal borders are encoded as thin PDF rectangles; using those
    borders prevents a centred multi-line product name from being assigned to
    only one of the underlying sample rows.
    """
    center_x = (left + right) / 2
    anchor_y = (anchor["top"] + anchor["bottom"]) / 2
    borders = sorted({
        round((rect["top"] + rect["bottom"]) / 2, 2)
        for rect in rects
        if rect["bottom"] - rect["top"] <= 1.2
        and rect["x1"] - rect["x0"] >= 5
        and rect["x0"] - 1 <= center_x <= rect["x1"] + 1
    })
    above = [border for border in borders if border < anchor_y]
    below = [border for border in borders if border > anchor_y]
    if above and below:
        band_top, band_bottom = above[-1], below[0]
    else:
        band_top, band_bottom = fallback_top, fallback_bottom
    return [
        word for word in words
        if band_top <= (word["top"] + word["bottom"]) / 2 < band_bottom
        and left <= word_center(word) < right
    ]


def group_holder_between(words: list[dict], lower_top: float, anchor_top: float, sample_x: float) -> str:
    candidates = []
    for top, line_words in line_groups(words):
        if not (lower_top < top < anchor_top - 3):
            continue
        value = words_text(line_words)
        if min(word["x0"] for word in line_words) > sample_x + 5 and COMPANY_MARKERS_RE.search(normalize(value)):
            candidates.append(value)
    return candidates[-1] if candidates else ""


def extract_technical(words: list[dict], anchor: dict, columns: dict, section: str) -> tuple[str, str, str]:
    same_line = sorted(
        [word for word in words if abs(word["top"] - anchor["top"]) < 3 and word["x0"] > anchor["x1"]],
        key=lambda word: word["x0"],
    )
    sae_candidates = [word for word in same_line if SAE_RE.fullmatch(normalize(word["text"]))]
    if columns["sae_x"] is not None and sae_candidates:
        sae_word = min(sae_candidates, key=lambda word: abs(word_center(word) - columns["sae_x"]))
    else:
        sae_word = sae_candidates[-1] if sae_candidates else None
    sae = factual_value(sae_word["text"] if sae_word else "")
    registration = ""
    if sae_word is not None:
        reg_candidates = [
            word for word in same_line
            if word["x1"] <= sae_word["x0"] + 1
            and re.fullmatch(r"(?:\d{1,6}|N\.?A\.?)", normalize(word["text"]), re.I)
        ]
        if reg_candidates:
            registration = factual_value(reg_candidates[-1]["text"])
    performance = ""
    api_candidates = [word for word in same_line if API_RE.fullmatch(normalize(word["text"]))]
    if api_candidates:
        if columns["api_x"] is not None:
            performance = min(api_candidates, key=lambda word: abs(word_center(word) - columns["api_x"]))["text"]
        else:
            performance = api_candidates[0]["text"]
    # Older label/quality appendices do not publish an API column.  Avoid
    # interpreting API-looking fragments in narrative nonconformity text.
    if section in {"label", "quality"} and columns["api_x"] is None:
        performance = ""
    return registration, sae, factual_value(performance)


def parse_pdf(path: Path, url: str, source_sha256: str, year: int) -> tuple[list[dict], dict]:
    appendix_rows = []
    active_section = None
    active_columns = None
    last_holder = ""
    last_product = ""
    last_registration = ""
    last_sae = ""
    last_performance = ""
    section_occurrences = Counter()
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            words = page.extract_words(x_tolerance=1, y_tolerance=3)
            rects = page.rects
            anchors = anchors_on_page(words, year)
            detected_section = section_from_text(text) if page_number >= 8 else None
            if detected_section and anchors:
                active_section = detected_section
                active_columns = derive_columns(words, anchors)
                last_holder = ""
                last_product = ""
                last_registration = ""
                last_sae = ""
                last_performance = ""
            elif "ANEXO 1" in normalize(text[:800]) and active_section == "quality":
                active_section = None
                active_columns = None
            if not active_section or not anchors:
                continue
            if active_columns is None:
                active_columns = derive_columns(words, anchors)
            tops = [anchor["top"] for anchor in anchors]
            gaps = [right - left for left, right in zip(tops, tops[1:])]
            median_gap = statistics.median(gaps) if gaps else 35
            for page_row, anchor in enumerate(anchors, start=1):
                if page_row == 1:
                    band_top = max(80, anchor["top"] - (gaps[0] * 0.65 if gaps else median_gap * 0.65))
                    holder_lower_top = 90
                else:
                    band_top = (tops[page_row - 2] + anchor["top"]) / 2
                    holder_lower_top = tops[page_row - 2] + 3
                if page_row < len(anchors):
                    band_bottom = (anchor["top"] + tops[page_row]) / 2
                else:
                    band_bottom = min(page.height - 30, anchor["top"] + median_gap * 0.6)
                band = [
                    word for word in words
                    if band_top <= (word["top"] + word["bottom"]) / 2 < band_bottom
                ]
                if year >= 2016:
                    product_words = cell_words(
                        words,
                        rects,
                        anchor,
                        active_columns["product_left"],
                        active_columns["product_right"],
                        band_top,
                        band_bottom,
                    )
                else:
                    product_words = [
                        word for word in band
                        if active_columns["product_left"]
                        <= word_center(word)
                        < active_columns["product_right"]
                    ]
                product_name = words_text(product_words)
                holder = ""
                if active_columns["has_company_column"]:
                    if year >= 2016:
                        holder_words = cell_words(
                            words,
                            rects,
                            anchor,
                            active_columns["company_left"],
                            active_columns["company_right"],
                            band_top,
                            band_bottom,
                        )
                    else:
                        holder_words = [
                            word for word in band
                            if active_columns["company_left"]
                            <= word_center(word)
                            < active_columns["company_right"]
                        ]
                    holder = words_text(holder_words)
                else:
                    holder = group_holder_between(
                        words, holder_lower_top, anchor["top"], active_columns["sample_x"]
                    )
                holder = factual_value(holder)
                if holder:
                    last_holder = holder
                else:
                    holder = last_holder
                registration, sae, performance = extract_technical(words, anchor, active_columns, active_section)
                product_name = factual_value(product_name)
                inherited_product = False
                if not product_name and last_product:
                    product_name = last_product
                    inherited_product = True
                if inherited_product:
                    registration = registration or last_registration
                    sae = sae or last_sae
                    performance = performance or last_performance
                if not product_name:
                    raise ValueError(
                        f"{path.name} page {page_number} row {page_row}: incomplete row "
                        f"{(active_section, product_name, holder, registration, sae, performance)}"
                    )
                last_product = product_name
                last_registration = registration
                last_sae = sae
                last_performance = performance
                sample_id = normalize(anchor["text"])
                sample_id_printed = anchor.get("printed_text", clean(anchor["text"]))
                locator = f"{source_sha256}:{page_number}:{page_row}:{active_section}:{sample_id}"
                appendix_rows.append({
                    "source_id": "ANP_BRAZIL_LUBRICANT_MONITORING_PDF_EXCEPTIONS",
                    "source_record_id": f"ANP-PML-PDF-EX-{hashlib.sha256(locator.encode()).hexdigest()[:18]}",
                    "source_page_url": SOURCE_PAGE,
                    "source_url": url,
                    "source_file_sha256": source_sha256,
                    "source_file_name": path.name,
                    "source_page": page_number,
                    "source_page_row": page_row,
                    "issue_year": year,
                    "market": "Brazil",
                    "sample_id": sample_id,
                    "sample_id_printed": sample_id_printed,
                    "sample_id_normalization_method": sample_id_normalization_method(
                        sample_id, sample_id_printed
                    ),
                    "product_name": product_name,
                    "registration_holder": holder,
                    "registration_number": registration,
                    "sae": sae,
                    "performance_level": performance,
                    "appendix_section": active_section,
                    "quality_flags": [SECTION_FLAGS[active_section]],
                })
                section_occurrences[active_section] += 1

    by_sample = defaultdict(list)
    for row in appendix_rows:
        by_sample[row["sample_id"]].append(row)
    merged_rows = []
    for sample_id, occurrences in sorted(by_sample.items()):
        best = max(
            occurrences,
            key=lambda row: sum(bool(row[field]) for field in (
                "registration_holder", "registration_number", "sae", "performance_level"
            )),
        )
        merged = dict(best)
        merged["source_record_id"] = f"ANP-PML-PDF-EX-{hashlib.sha256((source_sha256 + ':' + sample_id).encode()).hexdigest()[:18]}"
        merged["source_pages"] = sorted({row["source_page"] for row in occurrences})
        merged["appendix_sections"] = sorted({row["appendix_section"] for row in occurrences})
        merged["quality_flags"] = sorted({flag for row in occurrences for flag in row["quality_flags"]})
        merged["appendix_occurrence_count"] = len(occurrences)
        merged["published_scope"] = "published_nonconforming_product_appendices_only"
        merged["snapshot_date"] = date.today().isoformat()
        merged["lifecycle_status"] = "historical_market_sample_nonconformity_observation"
        del merged["appendix_section"]
        merged_rows.append(merged)
    return merged_rows, {
        "appendix_row_occurrences": len(appendix_rows),
        "sample_observations": len(merged_rows),
        "section_occurrences": dict(sorted(section_occurrences.items())),
    }


def parse_downloaded_source(source: dict) -> tuple[list[dict], dict]:
    rows, metrics = parse_pdf(
        Path(source["path"]),
        source["source_url"],
        source["source_sha256"],
        source["issue_year"],
    )
    expected_sections = {"registration", "quality"}
    if source["issue_year"] <= 2014:
        expected_sections.add("label")
    actual_sections = set(metrics["section_occurrences"])
    if not rows or not expected_sections.issubset(actual_sections):
        raise RuntimeError(
            f"Incomplete appendix coverage for {source['source_url']}: rows={len(rows)}, "
            f"expected={sorted(expected_sections)}, actual={sorted(actual_sections)}"
        )
    overlong_products = [row for row in rows if len(row["product_name"]) > 100]
    if overlong_products:
        raise RuntimeError(
            f"Probable merged-column extraction in {source['source_url']}: "
            f"{len(overlong_products)} product names exceed 100 characters"
        )
    return rows, {
        "source_url": source["source_url"],
        "source_file_name": source["source_file_name"],
        "source_sha256": source["source_sha256"],
        "issue_year": source["issue_year"],
        **metrics,
    }


def download_official_source(source: dict) -> dict:
    payload = download(source["source_url"])
    path = Path(source["path"])
    path.write_bytes(payload)
    return {
        **source,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
    }


def main() -> None:
    source_page = download(SOURCE_PAGE)
    parser = PdfLinkParser()
    parser.feed(source_page.decode("utf-8", errors="replace"))
    urls = list(dict.fromkeys(parser.urls))
    if len(urls) != 73:
        raise RuntimeError(f"Expected 73 official PDF bulletins from 2007-2017, found {len(urls)}")

    all_rows = []
    files = []
    with tempfile.TemporaryDirectory(prefix="anp-pml-pdf-exceptions-") as temporary:
        directory = Path(temporary)
        source_requests = []
        for index, url in enumerate(urls, start=1):
            year_match = re.search(r"/(20\d{2})/", url)
            if not year_match:
                raise ValueError(f"No issue year in {url}")
            year = int(year_match.group(1))
            path = directory / f"{year}-{index:02d}-{Path(urlparse(url).path).name}"
            source_requests.append({
                "path": str(path),
                "source_url": url,
                "source_file_name": Path(urlparse(url).path).name,
                "issue_year": year,
            })
        with ThreadPoolExecutor(max_workers=4) as pool:
            downloaded_sources = list(pool.map(download_official_source, source_requests))
        workers = min(8, os.cpu_count() or 1)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            parsed_sources = pool.map(parse_downloaded_source, downloaded_sources)
            for rows, file_metrics in parsed_sources:
                all_rows.extend(rows)
                files.append(file_metrics)

    all_rows.sort(key=lambda row: (row["issue_year"], row["source_url"], row["sample_id"]))
    record_ids = [row["source_record_id"] for row in all_rows]
    if len(record_ids) != len(set(record_ids)):
        raise RuntimeError("Duplicate source_record_id values in normalized exception history")
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_rows)
    OUTPUT.write_text(output_text, encoding="utf-8")
    identity_fields = ("registration_number", "product_name", "sae", "performance_level", "registration_holder")
    identities = {tuple(normalize(row[field]) for field in identity_fields) for row in all_rows}
    report = {
        "schema_version": 1,
        "status": "official_open_government_pdf_nonconformity_appendices_normalized",
        "snapshot_date": date.today().isoformat(),
        "source_page_url": SOURCE_PAGE,
        "terms_url": TERMS_URL,
        "source_page_sha256": hashlib.sha256(source_page).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "official_pdf_files": len(files),
        "files": files,
        "source_observations": len(all_rows),
        "appendix_row_occurrences": sum(row["appendix_occurrence_count"] for row in all_rows),
        "normalized_product_grade_holder_identities": len(identities),
        "observations_by_issue_year": dict(sorted(Counter(str(row["issue_year"]) for row in all_rows).items())),
        "quality_flags": dict(sorted(Counter(flag for row in all_rows for flag in row["quality_flags"]).items())),
        "sample_id_normalization_methods": dict(sorted(Counter(
            row["sample_id_normalization_method"] for row in all_rows
        ).items())),
        "rights_note": "ANP publishes the reports on gov.br. Only normalized factual fields and provenance are republished; PDF layout, narrative, CNPJ and collection-location fields are omitted.",
        "scope_note": "The 2007-2017 PDF appendices publish products reported as nonconforming for registration, labelling or quality. They are an exception history, not the complete population sampled by PML.",
        "lifecycle_note": "A row proves a historical sample and a source-reported nonconformity. It is not proof of current registration, current nonconformity or market availability.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
