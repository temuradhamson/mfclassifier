#!/usr/bin/env python3
"""Normalize the recoverable official NOC Ethiopia Caltex lubricant archive."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/ethiopia-noc-caltex-products.jsonl"
REPORT = ROOT / "data/ethiopia-noc-caltex-report.json"
SOURCE_ID = "ETHIOPIA_NOC_CALTEX_RECOVERABLE_OFFICIAL_ARCHIVE"
SOURCE_URL = (
    "https://www.nocethiopia.com/index.php/2-uncategorised?start=30"
)
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"

PRODUCTS = {
    "delo_400_le": (
        "Delo 400 LE", "M", "sae_engine", ["15W-40"],
        {
            "api": ["CJ-4", "CI-4 PLUS", "CI-4", "CH-4", "CF", "SM", "SL"],
            "acea": ["E7"],
        },
    ),
    "delo_400": (
        "Delo 400", "M", "sae_engine", ["15W-40"],
        {
            "api": [
                "CI-4 PLUS", "CI-4", "CH-4", "CG-4", "CF-4", "CF",
                "CD", "SL", "SJ", "SH",
            ],
            "acea": ["E5", "E3", "A3", "B3"],
            "jaso": ["DH-1"],
        },
    ),
    "delo_gold": (
        "Delo Gold", "M", "sae_engine", ["15W-40"],
        {
            "api": ["CH-4", "CG-4", "CF-4", "CF", "CD", "SL"],
            "acea": ["E3"], "jaso": ["DH-1"],
        },
    ),
    "delo_silver": (
        "Delo Silver", "M", "sae_engine", ["10W", "30", "40", "50"],
        {"api": ["CF", "CD", "SF"]},
    ),
    "super_tractor": (
        "Super Tractor Oil", "T", "sae_gear", ["15W-40"],
        {"api": ["CF", "SF"], "api_gl": ["GL-4"]},
    ),
    "textran_tdh": (
        "Textran TDH Premium", "T", "", [""],
        {
            "api_gl": ["GL-4"],
            "performance": [
                "Volvo 97303 VME WB 101", "Massey Ferguson M1143/M1145",
                "ZF TE-ML 03E/05F/06K/17E", "Caterpillar TO-2",
            ],
        },
    ),
    "thuban_gl5": (
        "Thuban GL5 EP", "T", "sae_gear", ["80W-90", "85W-140"],
        {
            "api_gl": ["GL-5", "GL-4"], "performance": [
                "API MT-1", "Mack GO-J", "MIL-PRF-2105E",
            ],
        },
    ),
    "rando_hdz": (
        "Rando HDZ", "H", "iso_vg", ["15", "22", "32", "46", "68", "100"],
        {
            "performance": [
                "ISO 6743-4 HV", "DIN 51524-3", "US Steel 126/127",
            ],
        },
    ),
    "thuban_gl4": (
        "Thuban GL4", "T", "sae_gear", ["90", "140"],
        {"api_gl": ["GL-4"], "performance": ["MIL-L-2105"]},
    ),
    "texamatic_1888": (
        "Texamatic 1888", "T", "", [""],
        {"performance": [
            "General Motors DEXRON III(H)", "Ford MERCON", "Allison C-4",
            "Voith H55.6335",
        ]},
    ),
    "rando_hd": (
        "Rando HD", "H", "iso_vg", ["22", "32", "46", "68", "100", "150", "220"],
        {
            "performance": [
                "ISO 6743-4 HM", "DIN 51524-2 HLP", "Denison HF-0",
            ],
        },
    ),
    "torque_4n4": (
        "Torque Fluid 4N4", "T", "sae_gear", ["10W", "30", "40", "50", "60"],
        {"api": ["CF"], "performance": ["Caterpillar TO-4", "Allison C-4"]},
    ),
    # The three live grease anchors each point to the preceding product's TDS.
    "starplex": ("Starplex EP Greases", "G", "", [""], {}),
    "molytex": ("Molytex EP Greases", "G", "", [""], {}),
    "multifak": ("Multifak EP Greases", "G", "", [""], {}),
}
LABEL_TO_SERIES = {
    "delo 400 le 15w40": "delo_400_le",
    "delo 400 15w40": "delo_400",
    "delo gold 15w40": "delo_gold",
    "delo silver monograde": "delo_silver",
    "super tractor oil 15w40": "super_tractor",
    "textran tdh premiumi": "textran_tdh",
    "textran tdh premium": "textran_tdh",
    "thuban gl5 ep 80w90 and": "thuban_gl5",
    "thuban gl5 85w140": "thuban_gl5",
    "thuban gl5 ep 80w90 and 85w140": "thuban_gl5",
    "rando hdz 46 and 68": "rando_hdz",
    "rando hdz": "rando_hdz",
    "thuban gl4 90 and 140": "thuban_gl4",
    "texamatic 1888": "texamatic_1888",
    "rando hd": "rando_hd",
    "torque fluids 4n4": "torque_4n4",
    "starplex ep greases": "starplex",
    "molytex ep greases": "molytex",
    "multifak ep greases": "multifak",
}
MISMATCHED_TDS_SERIES = {
    "starplex": "linked payload identifies Textran TDH Premium",
    "molytex": "linked payload identifies Starplex EP",
    "multifak": "linked payload identifies Molytex EP",
}
EXACT_TARGETS = {
    ("delo_silver", "40"): (
        "AFAL_CALTEX_EAST_AFRICA_FEATURED_PRODUCTS", "AFAL-EA-002"
    ),
    ("super_tractor", "15W-40"): ("ZF_TE_ML", "ZF000789"),
    ("thuban_gl5", "80W-90"): (
        "MACK_2014_APPROVED_OILS", "MACK-2014-73bf4731655da13601f2"
    ),
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.href = ""
        self.text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "a":
            self.href = dict(attrs).get("href", "") or ""
            self.text = []

    def handle_data(self, data: str) -> None:
        if self.href:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href:
            label = re.sub(
                r"\s+", " ", html.unescape(" ".join(self.text))
            ).strip()
            self.links.append((self.href, label))
            self.href = ""
            self.text = []


def clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def main() -> None:
    page = fetch(SOURCE_URL)
    parser = LinkParser()
    parser.feed(page.decode(errors="replace"))
    occurrences = []
    for source_url, source_label in parser.links:
        if not any(path in source_url for path in (
            "/AgriculturalEquipmentLubricants/",
            "/EarthMovingCarLubricants/",
        )):
            continue
        label_key = clean_label(source_label)
        series = LABEL_TO_SERIES.get(label_key)
        if not series:
            raise RuntimeError(f"Unreviewed NOC lubricant label: {source_label}")
        url = source_url.replace("http://", "https://", 1)
        try:
            payload = fetch(url)
            document = {
                "url": url,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "fetch_status": "resolved",
            }
        except urllib.error.HTTPError as exc:
            if exc.code != 500 or not url.endswith(
                "/AgriculturalEquipmentLubricants/pdf1"
            ):
                raise
            document = {
                "url": url,
                "sha256": "",
                "bytes": 0,
                "fetch_status": "official_link_http_500",
            }
        occurrences.append({
            "source_label": source_label,
            "series": series,
            "document": document,
        })
    if len(occurrences) != 23:
        raise RuntimeError(
            f"NOC Ethiopia lubricant occurrence denominator changed: "
            f"{len(occurrences)}"
        )
    if Counter(row["document"]["fetch_status"] for row in occurrences) != {
        "resolved": 22, "official_link_http_500": 1,
    }:
        raise RuntimeError("NOC Ethiopia document fetch status changed")

    occurrences_by_series = defaultdict(list)
    for row in occurrences:
        occurrences_by_series[row["series"]].append(row)
    if set(occurrences_by_series) != set(PRODUCTS):
        raise RuntimeError("NOC Ethiopia reviewed product-series set changed")

    records = []
    for series, (
        base_name, family, grade_field, grades, common_specs,
    ) in PRODUCTS.items():
        source_occurrences = occurrences_by_series[series]
        documents = sorted(
            {
                (
                    row["document"]["url"],
                    row["document"]["sha256"],
                    row["document"]["bytes"],
                    row["document"]["fetch_status"],
                )
                for row in source_occurrences
            }
        )
        source_labels = sorted(
            {row["source_label"] for row in source_occurrences}
        )
        flags = [
            "official_country_distributor_recoverable_archive",
            "archive_page_live_current_product_availability_unverified",
            "source_reported_specifications_not_independent_approvals",
        ]
        if series in MISMATCHED_TDS_SERIES:
            flags.extend([
                "linked_tds_product_identity_mismatch",
                "mismatched_tds_technical_fields_not_assigned_to_product",
            ])
        if any(row[3] != "resolved" for row in documents):
            flags.append("one_official_tds_link_returns_http_500")
        for grade_index, grade in enumerate(grades, 1):
            specs = {
                **common_specs,
                "source_grade": grade,
                "source_series": series,
                "source_labels": source_labels,
                "source_occurrences": len(source_occurrences),
                "source_document_urls": [row[0] for row in documents],
                "source_document_sha256": [
                    row[1] for row in documents if row[1]
                ],
                "source_document_status": [row[3] for row in documents],
                "source_quality_flags": flags,
            }
            if grade_field:
                specs[grade_field] = grade
            grade_suffix = f" {grade}" if grade else ""
            target = EXACT_TARGETS.get((series, grade), ("", ""))
            facts = {
                "series": series,
                "base_name": base_name,
                "family": family,
                "grade_field": grade_field,
                "grade": grade,
                "labels": source_labels,
                "documents": documents,
                "common_specs": common_specs,
                "target": target,
            }
            records.append({
                "source_id": SOURCE_ID,
                "source_record_id": (
                    f"NOC-ET-{series.upper().replace('_', '-')}-"
                    f"{grade_index:02d}"
                ),
                "source_url": SOURCE_URL,
                "snapshot_date": SNAPSHOT_DATE,
                "market": "Ethiopia",
                "manufacturer": "Chevron / Caltex",
                "brand": "CALTEX",
                "product_name": f"Caltex {base_name}{grade_suffix}",
                "source_product_name": base_name,
                "family_code": family,
                "existing_target_source_id": target[0],
                "existing_target_source_record_id": target[1],
                "evidence_status": "official_country_distributor_archive_and_tds",
                "lifecycle_status": (
                    "live_official_archive_page_current_availability_unverified"
                ),
                "specifications": specs,
                "source_facts_sha256": hashlib.sha256(
                    json.dumps(
                        facts, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest(),
            })
    if len(records) != 35:
        raise RuntimeError(
            f"NOC Ethiopia identity denominator changed: {len(records)}"
        )
    output_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in records
    )
    OUT.write_text(output_text, encoding="utf-8")
    resolved = [
        row["document"] for row in occurrences
        if row["document"]["fetch_status"] == "resolved"
    ]
    report = {
        "schema_version": 1,
        "status": "official_recoverable_country_distributor_archive",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "lubricant_link_occurrences": len(occurrences),
        "reviewed_product_series": len(PRODUCTS),
        "identity_rows": len(records),
        "family_identity_counts": dict(sorted(Counter(
            row["family_code"] for row in records
        ).items())),
        "resolved_pdf_observations": len(resolved),
        "unique_resolved_pdf_payloads": len({
            row["sha256"] for row in resolved
        }),
        "broken_official_pdf_links": 1,
        "mismatched_tds_series": MISMATCHED_TDS_SERIES,
        "mismatched_tds_count": len(MISMATCHED_TDS_SERIES),
        "exact_existing_identity_matches": len(EXACT_TARGETS),
        "new_archive_identities": len(records) - len(EXACT_TARGETS),
        "normalized_output_sha256": hashlib.sha256(
            output_text.encode()
        ).hexdigest(),
        "source_page_facts_sha256": hashlib.sha256(
            json.dumps(
                occurrences, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "publication_scope": (
            "Factual product names, grades, source-reported standards, document "
            "links and hashes only; descriptions, TDS files, artwork and contacts "
            "are not redistributed."
        ),
        "denominator_note": (
            "The recoverable official archive page contains 26 PDF-link "
            "occurrences: 23 lubricant/TDS occurrences and three fuel-adulteration "
            "letters excluded as non-products. The 23 lubricant occurrences "
            "normalize to 15 series and 35 product-grade identities. This is not "
            "claimed as NOC Ethiopia's complete current catalog because other "
            "application routes currently fail to expose their former product "
            "content."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "ok",
        "occurrences": len(occurrences),
        "product_series": len(PRODUCTS),
        "identity_rows": len(records),
        "resolved_pdf_observations": len(resolved),
        "output_sha256": report["normalized_output_sha256"],
    }))


if __name__ == "__main__":
    main()
