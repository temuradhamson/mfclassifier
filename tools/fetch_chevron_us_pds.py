#!/usr/bin/env python3
"""Fetch and hash every PDS linked by the complete Chevron US discovery."""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader, __version__ as pypdf_version


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "data" / "chevron-us-complete-product-discovery.jsonl"
CACHE = ROOT / ".cache" / "chevron-us-pds"
OUTPUT = ROOT / "data" / "chevron-us-pds-inventory.jsonl"
REPORT = ROOT / "data" / "chevron-us-pds-inventory-report.json"


def fetch(url: str) -> tuple[bytes, str, bool]:
    last_error: Exception | None = None
    last_non_pdf: tuple[bytes, str, bool] | None = None
    for attempt in range(3):
        try:
            request = Request(
                url,
                headers={"User-Agent": "mfclassifier-pds-audit/1.0"},
            )
            with urlopen(request, timeout=90) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "")
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                if payload.startswith(b"%PDF-"):
                    return payload, content_type, True
                last_non_pdf = payload, content_type, False
                raise RuntimeError("response is not a PDF: " + content_type)
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
    if last_non_pdf is not None:
        return last_non_pdf
    raise RuntimeError(f"{url}: {last_error}")


def audit_one(item: tuple[str, list[dict]]) -> dict:
    url, linked_rows = item
    cache_id = hashlib.sha256(url.encode()).hexdigest()[:20]
    pdf_path = CACHE / f"{cache_id}.pdf"
    text_path = CACHE / f"{cache_id}.txt"
    if pdf_path.exists() and pdf_path.read_bytes().startswith(b"%PDF-"):
        payload = pdf_path.read_bytes()
        content_type = "application/pdf"
        is_pdf = True
    else:
        payload, content_type, is_pdf = fetch(url)
    if is_pdf:
        pdf_path.write_bytes(payload)
        reader = PdfReader(pdf_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        text_path.write_text(text, encoding="utf-8")
        printed_pages = len(reader.pages)
        retrieval_status = "public_pdf_downloaded"
    else:
        text = payload.decode("utf-8", errors="replace")
        text_path.write_text(text, encoding="utf-8")
        printed_pages = 0
        retrieval_status = "http_200_non_pdf_temporary_difficulty_page"
    return {
        "document_id": "CHEVRON-US-PDS-" + cache_id,
        "document_url": url,
        "document_sha256": hashlib.sha256(payload).hexdigest(),
        "document_bytes": len(payload),
        "content_type": content_type,
        "retrieval_status": retrieval_status,
        "printed_pages": printed_pages,
        "extracted_text_chars": len(text),
        "extracted_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "linked_product_pages": [
            {
                "source_record_id": row["source_record_id"],
                "product_name": row["product_name"],
                "source_url": row["source_url"],
            }
            for row in sorted(
                linked_rows, key=lambda row: row["source_record_id"]
            )
        ],
        "snapshot_date": "2026-07-24",
        "source_id": "CHEVRON_US_COMPLETE_LIVE_PRODUCT_PDS_CORPUS",
    }


def main() -> None:
    rows = [
        json.loads(line)
        for line in DISCOVERY.read_text(encoding="utf-8").splitlines()
        if line
    ]
    links: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["excluded_from_lubricant_scope"]:
            continue
        for url in row["pds_urls"]:
            links[url].append(row)
    if len(links) != 204:
        raise RuntimeError(
            f"Chevron in-scope unique PDS denominator changed: {len(links)}"
        )
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        inventory = list(pool.map(audit_one, sorted(links.items())))
    inventory.sort(key=lambda row: row["document_url"])
    OUTPUT.write_text(
        "".join(
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ) + "\n"
            for row in inventory
        ),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "status": "complete_pds_corpus_downloaded_hashed_and_text_extracted",
        "snapshot_date": "2026-07-24",
        "source_id": "CHEVRON_US_COMPLETE_LIVE_PRODUCT_PDS_CORPUS",
        "discovery_product_pages": len(rows),
        "in_scope_candidate_pages": sum(
            not row["excluded_from_lubricant_scope"] for row in rows
        ),
        "unique_pds_urls": len(inventory),
        "unique_response_payloads": len({
            row["document_sha256"] for row in inventory
        }),
        "unique_pdf_payloads": len({
            row["document_sha256"]
            for row in inventory
            if row["retrieval_status"] == "public_pdf_downloaded"
        }),
        "downloaded_pdf_documents": sum(
            row["retrieval_status"] == "public_pdf_downloaded"
            for row in inventory
        ),
        "non_pdf_official_responses": sum(
            row["retrieval_status"] != "public_pdf_downloaded"
            for row in inventory
        ),
        "pds_url_occurrences": sum(
            len(row["pds_urls"])
            for row in rows
            if not row["excluded_from_lubricant_scope"]
        ),
        "total_response_bytes": sum(
            row["document_bytes"] for row in inventory
        ),
        "total_pdf_bytes": sum(
            row["document_bytes"]
            for row in inventory
            if row["retrieval_status"] == "public_pdf_downloaded"
        ),
        "total_printed_pages": sum(
            row["printed_pages"] for row in inventory
        ),
        "pdf_documents_with_no_extracted_text": sum(
            row["retrieval_status"] == "public_pdf_downloaded"
            and
            not row["extracted_text_chars"] for row in inventory
        ),
        "pypdf_version": pypdf_version,
        "normalized_output_sha256": hashlib.sha256(
            OUTPUT.read_bytes()
        ).hexdigest(),
        "cache_scope": (
            "PDF payloads and extracted text remain under ignored .cache; "
            "only non-expressive document metadata, hashes and product-page "
            "links are retained in the repository."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "pds_urls": len(inventory),
        "pdf_payloads": report["unique_pdf_payloads"],
        "pages": report["total_printed_pages"],
        "bytes": report["total_pdf_bytes"],
        "non_pdf": report["non_pdf_official_responses"],
        "no_text": report["pdf_documents_with_no_extracted_text"],
        "sha256": report["normalized_output_sha256"],
    }))


if __name__ == "__main__":
    main()
