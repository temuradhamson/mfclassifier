#!/usr/bin/env python3
"""Download and normalize Korea Eco-Label EL611 lubricant records."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "korea-ecolabel-el611-lubricants.jsonl"
REPORT = ROOT / "data" / "korea-ecolabel-el611-lubricants-report.json"
SOURCE_PAGE_URL = "https://www.data.go.kr/data/15043624/fileData.do"
SOURCE_DOWNLOAD_URL = (
    "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
    "atchFileId=FILE_000000003599199&fileDetailSn=1&insertDataPrcus=N"
)
DATASET_SNAPSHOT_DATE = "2026-01-31"
TARGET_CATEGORY = "EL611.윤활유"
USER_AGENT = "MFClassifierResearch/1.0 (official-open-data-lubricant-registry)"


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z가-힣]+", " ", value).strip()


def download() -> bytes:
    request = urllib.request.Request(SOURCE_DOWNLOAD_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def canonical_product_name(value: str) -> str:
    # The registry publishes one package-specific Kixx row next to the base
    # product under the same certificate. Packaging is not a distinct formula.
    return clean(re.sub(r"\s*\(20[- ]Liter\)\s*$", "", value, flags=re.I))


def family_for(use: str, product_name: str) -> str:
    if "유압" in use:
        return "H"
    if "절삭" in use or "Chain" in product_name:
        return "I"
    return "I"


def technical(use: str, product_name: str, family: str) -> dict:
    explicit = re.findall(r"ISO\s*VG\s*(\d{1,3})", use, flags=re.I)
    suffix = re.search(r"(?:^|\s)(15|22|32|46|68|100|150|220|320|460|680)$", product_name)
    iso_vg = sorted(set(explicit + ([suffix.group(1)] if suffix and family in {"H", "I"} else [])), key=int)
    return {"iso_vg": iso_vg, "nlgi": [], "sae": []}


def main() -> None:
    raw = download()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    expected_headers = [
        "대상제품군", "업체명", "제품명", "세부 모델(품번)명", "제품구분",
        "통합인증 대표모델", "용도", "인증사유", "인증번호", "최초인증일",
        "인증시작일", "인증종료일", "사업자번호", "본사지역구분",
        "공장지역구분", "공장구분",
    ]
    assert reader.fieldnames == expected_headers, reader.fieldnames

    all_rows = 0
    source_rows = []
    for source_row_number, row in enumerate(reader, 2):
        all_rows += 1
        if clean(row["대상제품군"]) == TARGET_CATEGORY:
            source_rows.append((source_row_number, row))
    assert len(source_rows) == 21

    grouped: dict[tuple[str, str, str], list[tuple[int, dict]]] = defaultdict(list)
    for source_row_number, row in source_rows:
        product_name = canonical_product_name(row["제품명"])
        key = (normalize(row["업체명"]), normalize(product_name), clean(row["인증번호"]))
        grouped[key].append((source_row_number, row))

    records = []
    for key, occurrences in sorted(grouped.items()):
        _, first = occurrences[0]
        product_name = canonical_product_name(first["제품명"])
        manufacturer = clean(first["업체명"])
        use = clean(first["용도"])
        family = family_for(use, product_name)
        certificate = clean(first["인증번호"])
        fingerprint = hashlib.sha256("|".join(key).encode()).hexdigest()[:16]
        raw_names = sorted({clean(row["제품명"]) for _, row in occurrences})
        packages = ["20 L"] if any(re.search(r"20[- ]Liter", name, re.I) for name in raw_names) else []
        records.append({
            "source_id": "KOREA_ECOLABEL_EL611",
            "source_record_id": f"KR-EL611-{certificate}-{fingerprint}",
            "source_url": SOURCE_PAGE_URL,
            "dataset_snapshot_date": DATASET_SNAPSHOT_DATE,
            "market": "Republic of Korea",
            "product_name": product_name,
            "source_product_names": raw_names,
            "manufacturer": manufacturer,
            "official_category_code": "EL611",
            "official_category_name": "윤활유",
            "official_use": use,
            "certificate_number": certificate,
            "initial_certification_date": clean(first["최초인증일"]),
            "certification_start_date": clean(first["인증시작일"]),
            "certification_end_date": clean(first["인증종료일"]),
            "lifecycle_status": "certified_at_official_dataset_snapshot",
            "family_code": family,
            "classification_basis": "official_EL611_category_and_official_use",
            "technical": technical(use, product_name, family),
            "packages": packages,
            "source_occurrence_count": len(occurrences),
            "source_row_numbers": sorted(number for number, _ in occurrences),
        })

    assert len(records) == 20
    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "official_open_government_ecolabel_lubricants_normalized",
        "dataset_snapshot_date": DATASET_SNAPSHOT_DATE,
        "source_page_url": SOURCE_PAGE_URL,
        "source_download_url": SOURCE_DOWNLOAD_URL,
        "source_file_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "source_csv_rows_observed": all_rows,
        "portal_metadata_rows_reported": 99602,
        "source_EL611_rows": len(source_rows),
        "normalized_products": len(records),
        "duplicate_package_occurrences_merged": len(source_rows) - len(records),
        "manufacturers": len({normalize(row["manufacturer"]) for row in records}),
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "official_uses": dict(sorted(Counter(row["official_use"] for row in records).items())),
        "rights_note": "The official Korean Public Data Portal marks the file as free of use restrictions and available without login.",
        "privacy_note": "Business registration numbers, headquarters/factory locations and factory identifiers are excluded from the normalized output.",
        "grain_note": "One row is certificate + manufacturer + normalized product identity. One package-specific 20-Liter row is merged into its base product while provenance is retained.",
        "source_count_discrepancy_note": "The portal metadata reports 99,602 rows, while the downloaded 2026-01-31 CSV contains 240,695 data rows; the parser records the observed file count and filters only exact EL611 category rows.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["source_csv_rows_observed", "source_EL611_rows", "normalized_products", "manufacturers", "families"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
