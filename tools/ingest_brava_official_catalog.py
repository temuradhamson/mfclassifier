#!/usr/bin/env python3
"""Normalize product-grade facts from the current official Brava catalog."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "brava-official-products.jsonl"
REPORT = ROOT / "data" / "brava-official-products-report.json"
SOURCE_ID = "BRAVA_LUBRICANTS_OFFICIAL_CATALOG"
CATALOG_URL = "https://bravalubricants.com/products/view-catalog/"
ROBOTS_URL = "https://bravalubricants.com/robots.txt"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"


FAMILY_BY_SLUG = {
    "brava-diamantis": "M",
    "brava-ignis": "M",
    "brava-aurum": "M",
    "brava-atf": "T",
    "brava-cvt": "T",
    "brava-euro": "M",
    "brava-elite-racing": "M",
    "brava-duratio": "M",
    "brava-optimum-hd": "M",
    "brava-optimum-max": "M",
    "brava-optimum-plus": "M",
    "brava-optimum-ultra": "M",
    "brava-omnis": "T",
    "brava-mercon-v": "T",
    "brava-atf-dexron-vi": "T",
    "brava-motus": "M",
    "brava-nauticus": "M",
    "lonvita": "U",
    "brava-armoleo": "T",
    "brava-gravis": "T",
    "brava-genex": "M",
    "brava-imperium": "H",
    "brava-fabros": "I",
    "brava-tractor-utto": "T",
    "brava-ge-1350": "M",
    "brava-frigus": "TF",
    "brava-dot-4": "TF",
    "brava-dot-3": "TF",
    "brava-victum": "H",
    "brava-power-steering-stop-leak": "H",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def clean(fragment: str) -> str:
    return re.sub(
        r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    ).strip()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def one(pattern: str, source: str) -> str:
    values = re.findall(pattern, source, flags=re.I | re.S)
    return clean(values[0]) if values else ""


def product_links(catalog_html: str) -> dict[str, str]:
    links = {}
    for raw_url in re.findall(r"href=[\"']([^\"']+)", catalog_html, flags=re.I):
        url = html.unescape(raw_url)
        if "/product/" not in url or "/product-type/" in url:
            continue
        slug = urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        links.setdefault(slug, url)
    assert set(links) == set(FAMILY_BY_SLUG), {
        "missing_mapped_pages": sorted(set(FAMILY_BY_SLUG) - set(links)),
        "new_unmapped_pages": sorted(set(links) - set(FAMILY_BY_SLUG)),
    }
    return links


def source_modified(page_html: str) -> str:
    match = re.search(
        r'<meta\s+property=["\']article:modified_time["\']\s+content=["\']([^"\']+)',
        page_html,
        flags=re.I,
    )
    return match.group(1).strip() if match else ""


def document_link(page_html: str, label: str) -> str:
    pattern = rf'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?{re.escape(label)}.*?</a>'
    values = re.findall(pattern, page_html, flags=re.I | re.S)
    return html.unescape(values[0]) if values else ""


def api_values(items: list[str]) -> list[str]:
    values = []
    for item in items:
        upper = item.upper().strip()
        if upper.startswith("API ") and not upper.startswith("API GL-"):
            body = upper[4:]
            values.extend(re.split(r"\s*[,/]\s*", body))
        elif re.fullmatch(
            r"(?:CF(?:-2)?|SL|SM|SN|SJ|CH-4|CI-4(?: PLUS)?|CJ-4|CK-4)(?:/(?:CF(?:-2)?|SL|SM|SN|SJ|CH-4|CI-4(?: PLUS)?|CJ-4|CK-4))*",
            upper,
        ):
            values.extend(upper.split("/"))
    return sorted({value.strip() for value in values if value.strip()})


def normalize_ilsac(value: str) -> str:
    compact = re.sub(r"[^A-Z0-9]", "", value.upper())
    match = re.fullmatch(r"GF(\d)([A-Z]?)", compact)
    return f"GF-{match.group(1)}{match.group(2)}" if match else value.upper().strip()


def technical_fields(family: str, title: str, items: list[str], h1: str) -> dict:
    fields: dict[str, object] = {
        "standards_and_approvals_source_reported": items,
        "api": api_values(items),
        "acea": sorted({
            item.split(":", 1)[1].strip().upper()
            for item in items if item.upper().startswith("ACEA:")
        }),
        "api_source_reported": sorted({item for item in items if item.upper().startswith("API ")}),
        "ilsac": sorted({normalize_ilsac(item[6:]) for item in items if item.upper().startswith("ILSAC ")}),
        "ilsac_source_reported": sorted({item[6:].strip() for item in items if item.upper().startswith("ILSAC ")}),
        "jaso_source_reported": sorted({
            item[5:].strip() for item in items if item.upper().startswith("JASO ")
        }),
    }
    gl_values = []
    for item in items:
        upper = item.upper().strip()
        if upper.startswith("API GL-"):
            gl_values.append(upper[4:])
        elif re.fullmatch(r"GL-\d(?:\s*,?\s*MT1)?", upper):
            gl_values.append(upper.split(",", 1)[0].strip())
    fields["api_gl"] = sorted(set(gl_values))

    sae_match = re.search(r"(?<![A-Z0-9])(?:SAE\s+)?(\d{1,2}W(?:-\d{2,3})?)(?![A-Z0-9])", title, flags=re.I)
    mono_match = re.fullmatch(r"(?:SAE\s+)?(30|40|50)", title.strip(), flags=re.I)
    sae = (sae_match or mono_match).group(1).upper() if sae_match or mono_match else ""
    if sae:
        fields["sae_gear" if family == "T" else "sae_engine"] = sae
        fields["sae_source_reported"] = title

    iso_match = re.search(r"(?:ISO|AW|EP)\s*(32|46|68|150|220)\b", title, flags=re.I)
    if iso_match and family in {"H", "I", "U"}:
        fields["iso_vg"] = iso_match.group(1)

    if family == "T":
        fields["atf_and_gear_specifications_source_reported"] = items
    if h1 == "Brava Frigus":
        fields["product_form_source_reported"] = title
    if h1 == "Brava Victum Dot 4":
        fields["brake_fluid_class"] = "DOT 4"
    elif h1 == "Brava Victum Dot 3":
        fields["brake_fluid_class"] = "DOT 3"
    if h1 == "Brava Nauticus":
        fields["nmma_source_reported"] = [
            item for item in items if "NMMA" in item.upper() or "TCW-3" in item.upper()
        ]
    return fields


def product_name(h1: str, title: str) -> str:
    if normalize(title) in normalize(h1) or title in {"ATF", "Brake Fluid", "Power Steering"}:
        return h1
    return f"{h1} {title}".strip()


def parse_page(slug: str, url: str, payload: bytes) -> list[dict]:
    page_html = payload.decode(errors="replace")
    h1 = one(r"<h1[^>]*>(.*?)</h1>", page_html)
    assert h1, url
    modified_at = source_modified(page_html)
    tds_url = document_link(page_html, "Download Technical Sheet")
    sds_url = document_link(page_html, "Download Safety Data Sheet")
    cards = re.findall(
        r'<div class="spec-cards__item">(.*?)</div>', page_html, flags=re.I | re.S
    )
    assert cards, url

    rows = []
    for card in cards:
        source_type = one(r'<p class="spec-cards__type">(.*?)</p>', card)
        title = one(r'<h3 class="spec-cards__title">(.*?)</h3>', card)
        assert source_type and title, (url, source_type, title)
        items = [
            clean(value) for value in re.findall(
                r'<li class="spec-cards__specs-item">(.*?)</li>', card, flags=re.I | re.S
            )
        ]
        package_names = [
            clean(value) for value in re.findall(
                r'<dt class="spec-cards__file-title">(.*?)</dt>', card, flags=re.I | re.S
            )
        ]
        part_labels = [
            clean(value) for value in re.findall(
                r'<dd class="spec-cards__file-name">(.*?)</dd>', card, flags=re.I | re.S
            )
        ]
        assert len(package_names) == len(part_labels), (url, title)
        packages = []
        flags = []
        for package_name, part_label in zip(package_names, part_labels):
            part_number = re.sub(r"^PART\s+No\.\s*", "", part_label, flags=re.I).strip()
            if not part_number or part_number == "HIGH MILEAGE":
                flags.append("source_part_number_placeholder_excluded")
                continue
            packages.append({"package_name": package_name, "part_number": part_number})
        if any(item.casefold() == "and more" for item in items):
            flags.append("vague_additional_specifications_not_enumerated")
            items = [item for item in items if item.casefold() != "and more"]
        if any(item.upper() == "ACEA: A4/B4" for item in items):
            flags.append("nonstandard_acea_class_source_reported_verbatim")

        family = FAMILY_BY_SLUG[slug]
        name = product_name(h1, title)
        record_hash = hashlib.sha256(f"{url}|{source_type}|{title}".encode()).hexdigest()[:16]
        rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"BRAVA-{record_hash}",
            "brand": "Brava",
            "manufacturer": "Olein Refinery Corp.",
            "product_name": name,
            "source_series": h1,
            "source_type": source_type,
            "source_variant": title,
            "family_code": family,
            "market": "PUERTO_RICO_US_EN",
            "source_url": url,
            "technical_document_url": tds_url,
            "safety_document_url": sds_url,
            "source_page_modified_at": modified_at,
            "snapshot_date": SNAPSHOT_DATE,
            "lifecycle_status": "listed_on_current_official_catalog_page",
            "specifications": technical_fields(family, title, items, h1),
            "packages": packages,
            "source_quality_flags": sorted(set(flags)),
        })
    return rows


def main() -> None:
    catalog_payload = fetch(CATALOG_URL)
    robots_payload = fetch(ROBOTS_URL)
    robots_text = robots_payload.decode(errors="replace")
    assert re.search(r"User-agent:\s*\*\s*\nDisallow:\s*(?:\n|$)", robots_text, flags=re.I)
    links = product_links(catalog_payload.decode(errors="replace"))

    rows = []
    page_evidence = []
    for slug, url in links.items():
        payload = fetch(url)
        page_rows = parse_page(slug, url, payload)
        rows.extend(page_rows)
        page_evidence.append({
            "slug": slug,
            "source_url": url,
            "source_sha256": hashlib.sha256(payload).hexdigest(),
            "normalized_product_grade_rows": len(page_rows),
        })

    part_number_occurrences: dict[str, list[dict]] = {}
    for row in rows:
        for package in row["packages"]:
            part_number_occurrences.setdefault(package["part_number"], []).append(row)
    colliding_part_numbers = {
        part_number: occurrences
        for part_number, occurrences in part_number_occurrences.items()
        if len({row["source_record_id"] for row in occurrences}) > 1
    }
    for occurrences in colliding_part_numbers.values():
        for row in occurrences:
            row["source_quality_flags"] = sorted(set(row["source_quality_flags"]) | {"source_part_number_cross_product_collision"})

    assert len(rows) == 69
    assert len({row["source_record_id"] for row in rows}) == len(rows)
    assert len({(row["brand"], row["product_name"], row["family_code"]) for row in rows}) == len(rows)
    assert all(row["product_name"] and row["source_url"] for row in rows)
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "catalog_url": CATALOG_URL,
        "robots_url": ROBOTS_URL,
        "catalog_sha256": hashlib.sha256(catalog_payload).hexdigest(),
        "robots_sha256": hashlib.sha256(robots_payload).hexdigest(),
        "source_product_pages": len(page_evidence),
        "normalized_product_grade_rows": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "rows_with_sae": sum(bool(row["specifications"].get("sae_engine") or row["specifications"].get("sae_gear")) for row in rows),
        "rows_with_iso_vg": sum(bool(row["specifications"].get("iso_vg")) for row in rows),
        "package_occurrences": sum(len(row["packages"]) for row in rows),
        "unique_part_numbers": len({package["part_number"] for row in rows for package in row["packages"]}),
        "colliding_part_numbers": {
            part_number: sorted({row["product_name"] for row in occurrences})
            for part_number, occurrences in sorted(colliding_part_numbers.items())
        },
        "source_quality_flags": dict(sorted(Counter(flag for row in rows for flag in row["source_quality_flags"]).items())),
        "page_evidence": page_evidence,
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_scope": "Derived factual product-grade, specification, package and part-number records with source attribution. Marketing descriptions, images, logos and page design are excluded.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
