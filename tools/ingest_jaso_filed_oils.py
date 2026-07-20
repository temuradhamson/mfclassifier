#!/usr/bin/env python3
"""Download and parse JASO public filed-oil lists into attributed factual records."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "jaso-filed-oils.jsonl"
REPORT = ROOT / "data" / "jaso-filed-oils-report.json"
USER_AGENT = "MFClassifierResearch/1.0 (public classification research)"

LISTS = {
    "JASO_4T": {
        "url": "https://www.jalos.or.jp/onfile/pdf/4T_EV_LIST.pdf",
        "code_pattern": r"M\d{3}[A-Z0-9]{3}\d{3}",
        "expected_rows": 2612,
        "tail_fields": ["jaso_classification", "sae_viscosity"],
        "family_detail": "motorcycle_four_cycle_gasoline_engine_oil",
        "submitter_header_offset": 11,
        "code_header_offset": 3,
    },
    "JASO_DEO": {
        "url": "https://www.jalos.or.jp/onfile/pdf/DEO_EV_LIST.pdf",
        "code_pattern": r"D\d{3}[A-Z0-9]{3}\d{3}",
        "expected_rows": 419,
        "tail_fields": ["jaso_classification", "sae_viscosity"],
        "family_detail": "automotive_diesel_engine_oil",
        "submitter_header_offset": 13,
        "code_header_offset": 3,
    },
    "JASO_2T": {
        "url": "https://www.jalos.or.jp/onfile/pdf/2T_EV_LIST.pdf",
        "code_pattern": r"\d{3}[A-Z0-9]{3}\d{3}",
        "expected_rows": 599,
        "tail_fields": ["jaso_classification"],
        "family_detail": "two_cycle_gasoline_engine_oil",
        "submitter_header_offset": 17,
        "code_header_offset": 2,
    },
}

def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def parse_pdf(path: Path, source_id: str, config: dict, source_hash: str, retrieved_at: str) -> list[dict]:
    records = []
    list_date = ""
    code_re = re.compile(config["code_pattern"])
    for page_number, page in enumerate(PdfReader(path).pages, start=1):
        plain_text = page.extract_text() or ""
        layout_lines = (page.extract_text(extraction_mode="layout") or "").splitlines()
        if not list_date:
            for line in plain_text.splitlines():
                match = re.search(r"\b([0-9]{1,2}\s+[A-Z][a-z]+\s+20[0-9]{2})\b", line)
                if match:
                    list_date = match.group(1)
                    break
        tail_by_row = {}
        for line in layout_lines:
            number_match = re.match(r"^\s*(\d+)\*?\s+", line)
            code_match = code_re.search(line)
            if number_match and code_match:
                tail_by_row[int(number_match.group(1))] = line[code_match.end():].split()
        fragments = []

        def visitor(fragment, _cm, tm, _font, _size):
            value = fragment.strip()
            if value:
                fragments.append((value, float(tm[4]), float(tm[5])))

        page.extract_text(visitor_text=visitor)
        starts = [
            index for index, item in enumerate(fragments)
            if re.fullmatch(r"\d+\*?", item[0]) and 20 < item[1] < 55
        ]
        for position, start in enumerate(starts):
            segment = fragments[start:(starts[position + 1] if position + 1 < len(starts) else len(fragments))]
            code_index = next((index for index, item in enumerate(segment) if code_re.fullmatch(item[0])), None)
            if code_index is None:
                continue
            number_text = segment[0][0]
            row_number = int(number_text.rstrip("*"))
            prefix = segment[1:code_index]
            product_parts = []
            submitter_parts = []
            zero_position = 0
            for value, x, _y in prefix:
                if abs(x) < 0.001:
                    zero_position += 1
                    (product_parts if zero_position == 1 else submitter_parts).append(value)
                elif x < 180:
                    product_parts.append(value)
                else:
                    submitter_parts.append(value)
            tail = tail_by_row.get(
                row_number,
                [item[0] for item in segment[code_index + 1:code_index + 1 + len(config["tail_fields"])]]
            )
            if len(tail) != len(config["tail_fields"]):
                raise ValueError(f"Unexpected tail {source_id} page {page_number}: {tail!r}")
            payload = dict(zip(config["tail_fields"], tail))
            records.append({
                "source_id": source_id,
                "source_url": config["url"],
                "source_sha256": source_hash,
                "retrieved_at": retrieved_at,
                "list_date": list_date,
                "source_row_number": row_number,
                "english_translation_marker": number_text.endswith("*"),
                "product_name": clean(" ".join(product_parts)),
                "submitter": clean(" ".join(submitter_parts)),
                "oil_code": segment[code_index][0],
                "family_detail": config["family_detail"],
                **payload,
            })
    return records


def validate(source_id: str, records: list[dict], config: dict) -> None:
    expected = config["expected_rows"]
    assert len(records) == expected, (source_id, len(records), expected)
    assert [row["source_row_number"] for row in records] == list(range(1, expected + 1))
    assert all(row["product_name"] and row["submitter"] and row["oil_code"] for row in records)
    allowed = {
        "JASO_4T": {"MA", "MA1", "MA2", "MB"},
        "JASO_DEO": {"DH-1", "DH-2", "DH-2F", "DL-1", "DL-2", "DL-0"},
        "JASO_2T": {"FB", "FC", "FD"},
    }[source_id]
    observed_tokens = {
        token
        for row in records
        for token in row["jaso_classification"].split(",")
    }
    assert observed_tokens <= allowed, (source_id, sorted(observed_tokens - allowed))
    if "sae_viscosity" in config["tail_fields"]:
        assert all(re.fullmatch(r"(?:[0-9]{1,2}W-[0-9]{2}|[0-9]{2})", row["sae_viscosity"], re.I) for row in records)


def main() -> None:
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    all_records = []
    source_reports = []
    with tempfile.TemporaryDirectory(prefix="jaso-") as temp:
        temp_dir = Path(temp)
        for source_id, config in LISTS.items():
            content = download(config["url"])
            source_hash = hashlib.sha256(content).hexdigest()
            path = temp_dir / f"{source_id}.pdf"
            path.write_bytes(content)
            records = parse_pdf(path, source_id, config, source_hash, retrieved_at)
            validate(source_id, records, config)
            all_records.extend(records)
            source_reports.append({
                "source_id": source_id,
                "source_url": config["url"],
                "source_sha256": source_hash,
                "list_date": records[0]["list_date"],
                "rows": len(records),
                "unique_oil_codes": len({row["oil_code"] for row in records}),
            })
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_records), encoding="utf-8")
    code_counts = Counter(row["oil_code"] for row in all_records)
    duplicates = [{"oil_code": code, "rows": count} for code, count in sorted(code_counts.items()) if count > 1]
    report = {
        "schema_version": 1,
        "status": "official_filed_lists_parsed",
        "retrieved_at": retrieved_at,
        "rows": len(all_records),
        "unique_oil_codes": len(code_counts),
        "duplicate_oil_codes": duplicates,
        "sources": source_reports,
        "rights_note": "Derived factual registry rows with attribution; original PDF layout and document text are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
