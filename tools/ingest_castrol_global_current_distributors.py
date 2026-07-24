#!/usr/bin/env python3
"""Extract Castrol's current official distributor-market evidence.

Only non-expressive factual fields needed for market coverage are published.
Postal addresses and telephone numbers participate in the source-row hash but
are intentionally omitted from the normalized dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/castrol-global-current-distributors.jsonl"
REPORT = ROOT / "data/castrol-global-current-distributors-report.json"
SOURCE_ID = "CASTROL_GLOBAL_CURRENT_AUTHORISED_DISTRIBUTORS"
SOURCE_URL = (
    "https://www.castrol.com/en/global/corporate/about-castrol/"
    "distributors.html"
)


def normalize_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        html.unescape(value).replace("\xa0", " "),
    ).strip()


class CastrolTableParser(HTMLParser):
    """Associate each six-column distributor table with its preceding RTE."""

    def __init__(self) -> None:
        super().__init__()
        self.div_depth = 0
        self.rte_depth: int | None = None
        self.rte_parts: list[str] = []
        self.last_rte_text = ""
        self.in_table = False
        self.table_rows: list[list[str]] = []
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None
        self.distributor_tables: list[tuple[str, list[list[str]]]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "div":
            self.div_depth += 1
            if "nr-text-component" in (attributes.get("class") or ""):
                self.rte_depth = self.div_depth
                self.rte_parts = []
        if self.rte_depth is not None and tag in {
            "br", "p", "h1", "h2", "h3", "h4", "h5", "li"
        }:
            self.rte_parts.append(" ")

        if tag == "table":
            self.in_table = True
            self.table_rows = []
        elif self.in_table and tag == "tr":
            self.current_row = []
        elif self.in_table and tag in {"td", "th"}:
            self.current_cell = []
        elif self.current_cell is not None and tag == "br":
            self.current_cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.rte_depth is not None:
            self.rte_parts.append(data)
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            if self.rte_depth == self.div_depth:
                self.last_rte_text = normalize_text("".join(self.rte_parts))
                self.rte_depth = None
            self.div_depth -= 1

        if self.in_table and tag in {"td", "th"}:
            assert self.current_row is not None
            assert self.current_cell is not None
            self.current_row.append(normalize_text("".join(self.current_cell)))
            self.current_cell = None
        elif self.in_table and tag == "tr":
            if self.current_row:
                self.table_rows.append(self.current_row)
            self.current_row = None
        elif tag == "table" and self.in_table:
            if (
                self.table_rows
                and self.table_rows[0]
                and self.table_rows[0][0].casefold() == "distributor name"
            ):
                self.distributor_tables.append(
                    (self.last_rte_text, self.table_rows)
                )
            self.in_table = False


def fetch_source() -> bytes:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; WorldLubricantsCatalog/1.0; "
                "+https://github.com/temuradhamson/mfclassifier)"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        if response.status != 200:
            raise RuntimeError(f"Castrol page returned HTTP {response.status}")
        return response.read()


def canonical_market_label(published: str) -> str:
    match = re.fullmatch(
        r"(.+?) \(English\) (.+?) \((?:French|Spanish|Arabic)\)",
        published,
    )
    if match and match.group(1) == match.group(2):
        return match.group(1)
    return published


def clean_public_value(value: str) -> str:
    if value.casefold() in {"n/a", "na", "contact for details"}:
        return ""
    return value


def main() -> None:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
        "--input",
        type=Path,
        help="Optional saved official HTML; otherwise fetch the live page.",
    )
    args = argument_parser.parse_args()

    source_bytes = args.input.read_bytes() if args.input else fetch_source()
    parser = CastrolTableParser()
    parser.feed(source_bytes.decode("utf-8", errors="replace"))
    tables = parser.distributor_tables
    if len(tables) < 100:
        raise AssertionError(
            f"Expected at least 100 distributor tables, got {len(tables)}"
        )

    rows: list[dict[str, Any]] = []
    for published_market, table_rows in tables:
        header = [value.casefold() for value in table_rows[0]]
        assert header == [
            "distributor name", "postal address", "website",
            "phone", "email", "sectors",
        ]
        market = canonical_market_label(published_market)
        for table_row_index, cells in enumerate(table_rows[1:], 1):
            if len(cells) != 6:
                raise AssertionError(
                    f"{published_market}: expected six cells, got {len(cells)}"
                )
            distributor, postal, website, phone, email, sectors = cells
            row_hash = hashlib.sha256(
                "\x1f".join(cells).encode("utf-8")
            ).hexdigest()
            rows.append(
                {
                    "source_id": SOURCE_ID,
                    "source_record_id": f"CASTROL-DIST-{len(rows) + 1:04d}",
                    "market_label": market,
                    "market_label_as_published": published_market,
                    "source_table_row": table_row_index,
                    "distributor_name": distributor,
                    "website_as_published": clean_public_value(website),
                    "public_business_email_as_published": clean_public_value(email),
                    "sectors_as_published": clean_public_value(sectors),
                    "official_source_row_sha256": row_hash,
                    "source_url": SOURCE_URL,
                    "snapshot_date": str(date.today()),
                    "evidence_scope": (
                        "official_authorised_distributor_market_presence"
                    ),
                    "product_scope_status": (
                        "no_country_sku_or_stock_inference_permitted"
                    ),
                    "privacy_note": (
                        "postal_address_and_phone_omitted_from_normalized_output"
                    ),
                }
            )

    assert len({row["source_record_id"] for row in rows}) == len(rows)
    assert len({
        (row["market_label_as_published"], row["source_table_row"])
        for row in rows
    }) == len(rows)
    market_counts = Counter(row["market_label"] for row in rows)
    sector_counts = Counter(
        row["sectors_as_published"] or "not_stated"
        for row in rows
    )
    rendered = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )
    OUT.write_text(rendered, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_html_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "snapshot_date": str(date.today()),
        "market_tables": len(tables),
        "unique_market_labels": len(market_counts),
        "distributor_rows": len(rows),
        "unique_distributor_names_casefolded": len({
            row["distributor_name"].casefold() for row in rows
        }),
        "markets_with_multiple_distributor_rows": sum(
            count > 1 for count in market_counts.values()
        ),
        "market_distributor_row_counts": dict(sorted(market_counts.items())),
        "sector_label_counts": dict(sorted(sector_counts.items())),
        "normalized_output_sha256": hashlib.sha256(
            rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "Authorised-distributor market evidence only. It must not be "
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
