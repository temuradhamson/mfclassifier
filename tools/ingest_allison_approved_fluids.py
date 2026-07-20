#!/usr/bin/env python3
"""Download and normalize Allison's official approved-fluid PDF lists."""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "allison-approved-fluids.jsonl"
REPORT = ROOT / "data" / "allison-approved-fluids-report.json"
LANDING_URL = "https://allisontransmission.com/en-gb/aftermarket---channel/parts---service/allison-approved-fluids"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"

LISTS = [
    {
        "list_id": "ALLISON_TES_668",
        "specifications": ["Allison TES 668"],
        "list_date": "2026-06-24",
        "url": "https://allisontransmission.bynder.com/m/5ebfbe82073eb1e8/original/Allison-TES-668-Approved-Fluids-List.pdf",
    },
    {
        "list_id": "ALLISON_TES_295_468",
        "specifications": ["Allison TES 295", "Allison TES 468"],
        "list_date": "2025-06-18",
        "url": "https://allisontransmission.bynder.com/m/d20987fc6b2e871/original/Allison-TES-295-TES-468-Approved-Fluids-List.pdf",
    },
    {
        "list_id": "ALLISON_TES_389",
        "specifications": ["Allison TES 389"],
        "list_date": "2026-03-31",
        "url": "https://allisontransmission.bynder.com/m/7f99f5c23ff0ee6b/original/Allison-TES-389-Approved-Fluids-List.pdf",
    },
    {
        "list_id": "ALLISON_TES_439",
        "specifications": ["Allison TES 439"],
        "list_date": "2025-06-18",
        "url": "https://allisontransmission.bynder.com/m/691b721c72579d00/original/Allison-TES-439-Approved-Fluids-List.pdf",
    },
    {
        "list_id": "ALLISON_TES_353",
        "specifications": ["Allison TES 353"],
        "list_date": "2025-06-18",
        "url": "https://allisontransmission.bynder.com/m/292fed4acc84cc88/original/Allison-TES-353-Approved-Fluids-List.pdf",
    },
    {
        "list_id": "ALLISON_TES_781",
        "specifications": ["Allison TES 781"],
        "list_date": "2025-09-29",
        "url": "https://allisontransmission.bynder.com/m/14364c2c91dd1db/original/Allison-TES-781-Approved-Fluids-List.pdf",
    },
]

APPROVAL = r"(?:(?:668|781|439)-\d+|A[AN]-\d+)"
ROW_RE = re.compile(
    rf"^\s*(.*?)\s{{2,}}(.*?)\s{{2,}}({APPROVAL}(?:\s+{APPROVAL})*)\s*$"
)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def main() -> None:
    products = []
    files = []
    approval_numbers = set()
    for source in LISTS:
        payload = download(source["url"])
        reader = PdfReader(io.BytesIO(payload))
        parsed = []
        for page_number, page in enumerate(reader.pages, 1):
            layout = page.extract_text(extraction_mode="layout") or ""
            for line in layout.splitlines():
                match = ROW_RE.match(line)
                if not match:
                    continue
                marketer, product_name, raw_approvals = map(clean, match.groups())
                approvals = re.findall(APPROVAL, raw_approvals)
                assert approvals
                approval_numbers.update(approvals)
                parsed.append({
                    "marketer_brand": marketer,
                    "product_name": product_name,
                    "approval_numbers": approvals,
                    "page": page_number,
                })
        assert parsed, source["list_id"]
        for row_number, row in enumerate(parsed, 1):
            record_id = f"{source['list_id']}:{row_number:03d}"
            products.append({
                **row,
                "source_id": "ALLISON_APPROVED_FLUIDS",
                "source_record_id": record_id,
                "list_id": source["list_id"],
                "specifications": source["specifications"],
                "list_date": source["list_date"],
                "source_url": source["url"],
                "landing_url": LANDING_URL,
                "snapshot_date": SNAPSHOT_DATE,
                "family_code": "T",
            })
        files.append({
            **source,
            "source_sha256": hashlib.sha256(payload).hexdigest(),
            "pages": len(reader.pages),
            "products": len(parsed),
            "approval_numbers": sum(len(row["approval_numbers"]) for row in parsed),
        })

    products.sort(key=lambda row: row["source_record_id"])
    assert len(products) == 104
    assert sum(len(row["approval_numbers"]) for row in products) == 119
    assert len(approval_numbers) == 117
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in products),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": "ALLISON_APPROVED_FLUIDS",
        "landing_url": LANDING_URL,
        "lists": len(files),
        "products": len(products),
        "unique_approval_numbers": len(approval_numbers),
        "approval_occurrences": sum(len(row["approval_numbers"]) for row in products),
        "marketers_brands": len({row["marketer_brand"] for row in products}),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "source_files": files,
        "publication_scope": "Derived factual approval records with attribution; Allison PDF design and full text are not republished.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "source_files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
