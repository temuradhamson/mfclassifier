#!/usr/bin/env python3
"""Download and SHA-256 audit current Rymax Belize images and TDS/SDS assets."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARD_INPUT = ROOT / "data/belize-rymax-current-product-cards.jsonl"
FACTS_OUT = ROOT / "data/belize-rymax-current-asset-facts.jsonl"
REPORT_OUT = ROOT / "data/belize-rymax-current-assets-report.json"
UA = "MFClassifier evidence catalog/1.0"
EXPECTED_ASSET_URLS = 823
EXPECTED_ASSET_FACTS_SHA256 = (
    "e34ae5fa3e53e1b5473f259b3f5e7ca4b4058388f2d33b19208e6dfae5e9b318"
)


def fetch_asset(item):
    kind, url = item
    last_error = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = response.read()
                return {
                    "kind": kind,
                    "url": url,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "content_type": response.headers.get("Content-Type", ""),
                    "status": response.status,
                }
        except Exception as error:
            last_error = error
            time.sleep(2 ** attempt)
    raise RuntimeError(f"asset failed after retries: {url}: {last_error}")


def main():
    cards = [
        json.loads(line)
        for line in CARD_INPUT.read_text(encoding="utf-8").splitlines()
        if line
    ]
    items = sorted({
        ("image", row["product_image_url"])
        for row in cards if row["product_image_url"]
    } | {
        ("document", url)
        for row in cards for url in row["document_urls"]
    })
    facts = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch_asset, item): item for item in items}
        for future in as_completed(futures):
            facts.append(future.result())
    facts.sort(key=lambda row: (row["kind"], row["url"]))
    normalized = "\n".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) for row in facts
    ) + "\n"
    facts_hash = hashlib.sha256(normalized.encode()).hexdigest()
    if len(facts) != EXPECTED_ASSET_URLS:
        raise RuntimeError(f"Rymax asset URL denominator changed: {len(facts)}")
    if facts_hash != EXPECTED_ASSET_FACTS_SHA256:
        raise RuntimeError(f"Rymax asset facts changed: {facts_hash}")
    FACTS_OUT.write_text(normalized, encoding="utf-8")
    report = {
        "source_id": "BELIZE_RYMAX_CURRENT_PRODUCT_CATALOG",
        "snapshot_date": "2026-07-24",
        "product_cards": len(cards),
        "asset_urls_audited": len(facts),
        "image_urls_audited": sum(row["kind"] == "image" for row in facts),
        "document_urls_audited": sum(row["kind"] == "document" for row in facts),
        "unique_asset_payloads": len({row["sha256"] for row in facts}),
        "unique_image_payloads": len({
            row["sha256"] for row in facts if row["kind"] == "image"
        }),
        "unique_document_payloads": len({
            row["sha256"] for row in facts if row["kind"] == "document"
        }),
        "image_bytes": sum(
            row["bytes"] for row in facts if row["kind"] == "image"
        ),
        "document_bytes": sum(
            row["bytes"] for row in facts if row["kind"] == "document"
        ),
        "asset_facts_sha256": facts_hash,
    }
    REPORT_OUT.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
