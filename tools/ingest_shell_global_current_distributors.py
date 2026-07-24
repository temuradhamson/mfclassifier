#!/usr/bin/env python3
"""Extract factual market/distributor coverage from Shell's official locator.

This is deliberately a market-presence evidence layer, not a product catalog:
an approved distributor does not prove that every global Shell SKU is stocked
in that market.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/shell-global-current-distributors.jsonl"
REPORT = ROOT / "data/shell-global-current-distributors-report.json"
SOURCE_ID = "SHELL_GLOBAL_CURRENT_APPROVED_DISTRIBUTOR_LOCATOR"
SOURCE_URL = (
    "https://www.shell.com/motorist/oils-lubricants/distributor-locator.html"
)
MODEL_URL = SOURCE_URL.removesuffix(".html") + ".model.json"


class TextAndLinksParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"p", "br", "li", "div"}:
            self.parts.append("\n")
        href = dict(attrs).get("href")
        if href:
            self.links.append(html.unescape(href.strip()))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "li", "div"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def lines(self) -> list[str]:
        return [
            re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()
            for value in "".join(self.parts).splitlines()
            if value.strip()
        ]


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def fetch_model() -> bytes:
    request = urllib.request.Request(
        MODEL_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; WorldLubricantsCatalog/1.0; "
                "+https://github.com/temuradhamson/mfclassifier)"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        if response.status != 200:
            raise RuntimeError(f"Shell model returned HTTP {response.status}")
        return response.read()


def extract_label_values(lines: list[str], labels: tuple[str, ...]) -> list[str]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(
        rf"^(?:{label_pattern})\s*:?\s*(.+)$",
        flags=re.IGNORECASE,
    )
    values: list[str] = []
    for line in lines:
        match = pattern.match(line)
        if match:
            value = match.group(1).strip(" :-")
            if value and value not in values:
                values.append(value)
    return values


def stable_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unknown-market"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        help="Optional saved Shell .model.json; otherwise fetch the official URL.",
    )
    args = parser.parse_args()

    source_bytes = args.input.read_bytes() if args.input else fetch_model()
    model = json.loads(source_bytes)
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()

    date_modified = ""
    for node in walk(model):
        if node.get("name") == "dateModified":
            date_modified = str(node.get("value", ""))
            break

    country_nodes = [
        node
        for node in walk(model)
        if node.get("organism") == "PromoSimple.Text"
        and node.get("model", {}).get("title")
    ]
    if len(country_nodes) < 100:
        raise AssertionError(
            f"Expected at least 100 official country sections, got "
            f"{len(country_nodes)}"
        )

    title_occurrences: defaultdict[str, int] = defaultdict(int)
    rows: list[dict[str, Any]] = []
    for node in country_nodes:
        market_label = str(node["model"]["title"]).strip()
        title_occurrences[market_label] += 1
        occurrence = title_occurrences[market_label]
        source_html = str(node["model"].get("text", ""))
        parsed = TextAndLinksParser()
        parsed.feed(source_html)
        lines = parsed.lines()

        brands = extract_label_values(lines, ("Brand",))
        distributor_names = extract_label_values(
            lines,
            ("Distributor name", "Distributor", "Company Name"),
        )
        for line_index, line in enumerate(lines):
            legal_entity_match = re.match(
                r"^in the form of legal entity\s+(.+)$",
                line,
                flags=re.IGNORECASE,
            )
            if legal_entity_match and line_index:
                trading_name = lines[line_index - 1]
                legal_name = legal_entity_match.group(1).strip()
                combined_name = f"{trading_name} ({legal_name})"
                if combined_name not in distributor_names:
                    distributor_names.append(combined_name)
        websites = sorted(
            {
                link
                for link in parsed.links
                if link.startswith(("http://", "https://"))
                and "shell.com/motorist/oils-lubricants/distributor-locator"
                not in link
            }
        )
        public_emails = sorted(
            {
                link.removeprefix("mailto:").split("?")[0]
                for link in parsed.links
                if link.lower().startswith("mailto:")
            }
        )
        block_sha256 = hashlib.sha256(
            "\n".join(lines).encode("utf-8")
        ).hexdigest()
        has_details = bool(lines and (distributor_names or websites or public_emails))

        rows.append(
            {
                "source_id": SOURCE_ID,
                "source_record_id": (
                    f"SHELL-DIST-{stable_slug(market_label).upper()}-"
                    f"{occurrence:02d}"
                ),
                "market_label": market_label,
                "market_section_occurrence": occurrence,
                "brands_as_published": brands,
                "distributor_names": distributor_names,
                "distributor_websites": websites,
                "public_business_emails": public_emails,
                "official_block_text_sha256": block_sha256,
                "official_page_last_modified": date_modified,
                "source_url": SOURCE_URL,
                "snapshot_date": str(date.today()),
                "evidence_scope": (
                    "official_approved_distributor_market_presence"
                    if has_details
                    else "country_section_present_without_distributor_details"
                ),
                "product_scope_status": (
                    "no_country_sku_or_stock_inference_permitted"
                ),
            }
        )

    assert len(rows) == len(country_nodes)
    assert len({row["source_record_id"] for row in rows}) == len(rows)
    unique_market_labels = len({row["market_label"] for row in rows})
    empty_sections = [
        row["market_label"]
        for row in rows
        if row["evidence_scope"]
        == "country_section_present_without_distributor_details"
    ]
    brand_counts = Counter(
        brand
        for row in rows
        for brand in row["brands_as_published"]
    )

    rendered = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )
    OUT.write_text(rendered, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_model_url": MODEL_URL,
        "source_model_sha256": source_sha256,
        "official_page_last_modified": date_modified,
        "snapshot_date": str(date.today()),
        "country_section_rows": len(rows),
        "unique_market_labels": unique_market_labels,
        "duplicate_market_section_counts": {
            market: count
            for market, count in sorted(title_occurrences.items())
            if count > 1
        },
        "sections_with_distributor_details": len(rows) - len(empty_sections),
        "sections_without_distributor_details": empty_sections,
        "published_brand_label_counts": dict(sorted(brand_counts.items())),
        "normalized_output_sha256": hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "Approved-distributor market evidence only. It must not be "
            "expanded into country-level SKU availability or stock claims."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
