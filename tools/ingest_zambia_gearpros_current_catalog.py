#!/usr/bin/env python3
"""Normalize the complete current GearPros Zambia online lubricant shop."""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
SKU_OUT = ROOT / "data/zambia-gearpros-current-skus.jsonl"
PRODUCT_OUT = ROOT / "data/zambia-gearpros-current-products.jsonl"
REPORT = ROOT / "data/zambia-gearpros-current-report.json"
SOURCE_ID = "ZAMBIA_GEARPROS_CURRENT_LUBRICANT_SHOP"
SHOP_URL = "https://gearpros.co.zm/pages/shop.php"
BASE_URL = "https://gearpros.co.zm/"


def fetch(url: str, attempts: int = 4) -> bytes:
    for attempt in range(attempts):
        result = subprocess.run(
            [
                "curl", "-LsS", "--fail", "--max-time", "60",
                "-A", "Mozilla/5.0 (compatible; catalog-research/1.0)",
                url,
            ],
            capture_output=True,
        )
        if result.returncode == 0:
            return result.stdout
        if attempt + 1 == attempts:
            raise RuntimeError(
                f"fetch failed: {url}: "
                + result.stderr.decode("utf-8", errors="replace")
            )
        time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def clean(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(
        r"\s+", " ", html.unescape(value).replace("\xa0", " ")
    ).strip()


def section_items(block: str, prefix: str) -> list[str]:
    match = re.search(
        rf'<div id="{prefix}_[^"]+"[^>]*>(.*?)</div>\s*</div>',
        block,
        flags=re.S,
    )
    if not match:
        return []
    return [
        clean(value)
        for value in re.findall(r"<li[^>]*>(.*?)</li>", match.group(1), re.S)
        if clean(value)
    ]


def family_for(name: str) -> str:
    upper = name.upper()
    if "COOLANT" in upper or "ANTIFREEZE" in upper:
        return "C"
    if "MOBILGEAR" in upper:
        return "I"
    if "MOBILUBE" in upper or "MOBILFLUID" in upper:
        return "T"
    if "NUTO" in upper:
        return "H"
    return "M"


def specifications(name: str, family: str) -> dict:
    upper = name.upper().replace("™", "")
    specs: dict[str, list[str]] = {}
    sae = []
    for winter, hot in re.findall(
        r"(?<!\d)(0W|5W|10W|15W|20W|75W|80W|85W)[- ]?(\d{2,3})\b",
        upper,
    ):
        value = f"{winter}-{hot}"
        if value not in sae:
            sae.append(value)
    if sae:
        specs["sae_gear" if family in {"I", "T"} else "sae_engine"] = sae
    iso_vg = []
    if "MOBILGEAR 600 XP" in upper:
        match = re.search(r"\b(220|320)\b", upper)
        if match:
            iso_vg.append(match.group(1))
    if "NUTO H" in upper:
        match = re.search(r"\b(32|46|68)\b", upper)
        if match:
            iso_vg.append(match.group(1))
    if iso_vg:
        specs["iso_vg"] = iso_vg
    return specs


def product_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("™", "")).strip()


def render(rows: list[dict]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )


def main() -> None:
    payload = fetch(SHOP_URL)
    source = payload.decode("utf-8", errors="replace")
    starts = [
        match.start()
        for match in re.finditer(
            r'<div class="col-sm-6 col-md-4 col-lg-3 product-wrapper"',
            source,
        )
    ]
    assert len(starts) == 22
    section_end = source.find("</section>", starts[-1])
    assert section_end > starts[-1]
    starts.append(section_end)

    sku_rows = []
    for index in range(len(starts) - 1):
        block = source[starts[index]:starts[index + 1]]
        name_match = re.search(
            r'<h3 class="product-name"[^>]*>(.*?)</h3>', block, re.S
        )
        product_id_match = re.search(
            r"checkout\.php\?product_id=([^\"&]+)", block
        )
        pack_match = re.search(
            r"selectPacking\(this,\s*'[^']+',\s*"
            r"([\d.]+),\s*([\d.]+),\s*'([^']*)',\s*(true|false),"
            r".*?</button>",
            block,
            re.S,
        )
        description_match = re.search(
            r'<div id="desc_[^"]+"[^>]*>.*?'
            r'<div class="accordion-body"[^>]*>(.*?)</div>\s*</div>',
            block,
            re.S,
        )
        assert (
            name_match and product_id_match and pack_match
            and description_match
        )
        name = clean(name_match.group(1))
        product_id = product_id_match.group(1)
        pack_button = pack_match.group(0)
        package_match = re.search(r">\s*([^<>]+?)\s*</button>", pack_button, re.S)
        assert package_match
        package = clean(package_match.group(1))
        original_price = float(pack_match.group(1))
        current_price = float(pack_match.group(2))
        sale_label = clean(pack_match.group(3))
        is_sale = pack_match.group(4) == "true"
        pds_match = re.search(
            r'href="([^"]+)"[^>]*>.*?Product Data Sheet',
            block,
            re.S | re.I,
        )
        pds_url = urljoin(SHOP_URL, pds_match.group(1)) if pds_match else ""
        pds_sha256 = ""
        if pds_url:
            pds_sha256 = hashlib.sha256(fetch(pds_url)).hexdigest()
            time.sleep(1)
        family = family_for(name)
        brand = "MOBIL" if name.upper().startswith("MOBIL") else "CENTLUBE"
        description = clean(description_match.group(1))
        sku_rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"GEARPROS-{product_id}",
            "source_product_id": product_id,
            "country": "Zambia",
            "brand": brand,
            "source_product_name": name,
            "product_name": product_label(name),
            "family_code": family,
            "specifications": specifications(name, family),
            "package": package,
            "price_amount": current_price,
            "price_original_amount": original_price,
            "price_currency": "",
            "price_currency_symbol": "$",
            "price_status": (
                "published_sale_price_currency_unspecified"
                if is_sale
                else "published_price_currency_unspecified"
            ),
            "sale_label": sale_label,
            "is_sale": is_sale,
            "approvals_source_reported": section_items(block, "app"),
            "recommendations_source_reported": section_items(block, "rec"),
            "requirements_source_reported": section_items(block, "req"),
            "pds_url": pds_url,
            "pds_sha256": pds_sha256,
            "description_sha256": hashlib.sha256(
                description.encode("utf-8")
            ).hexdigest(),
            "source_url": urljoin(
                SHOP_URL,
                f"checkout.php?product_id={product_id}",
            ),
            "catalog_url": SHOP_URL,
            "snapshot_date": str(date.today()),
            "lifecycle_status": (
                "listed_current_catalog_orderable_status_not_stock_verified"
            ),
            "source_quality_flags": [
                "official_country_distributor_current_shop_card",
                "currency_symbol_published_iso_currency_not_stated",
                "order_action_present_stock_quantity_not_published",
                "marketing_description_not_redistributed",
            ],
        })
    assert len(sku_rows) == len({
        row["source_product_id"] for row in sku_rows
    }) == 22

    groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in sku_rows:
        key = (row["brand"], row["family_code"], row["product_name"].upper())
        groups.setdefault(key, []).append(row)
    product_rows = []
    for (brand, family, _), members in sorted(groups.items()):
        member = members[0]
        source_ids = sorted(row["source_record_id"] for row in members)
        material = json.dumps(
            [brand, family, member["product_name"]],
            ensure_ascii=False,
        )
        product_rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": (
                "GEARPROS-PRODUCT-"
                + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
            ),
            "country": "Zambia",
            "brand": brand,
            "product_name": member["product_name"],
            "family_code": family,
            "specifications": member["specifications"],
            "source_sku_record_ids": source_ids,
            "source_product_ids": sorted(
                row["source_product_id"] for row in members
            ),
            "packages": sorted(row["package"] for row in members),
            "source_urls": sorted(row["source_url"] for row in members),
            "approvals_source_reported": sorted({
                value for row in members
                for value in row["approvals_source_reported"]
            }),
            "recommendations_source_reported": sorted({
                value for row in members
                for value in row["recommendations_source_reported"]
            }),
            "requirements_source_reported": sorted({
                value for row in members
                for value in row["requirements_source_reported"]
            }),
            "pds_evidence": sorted(
                {
                    (row["pds_url"], row["pds_sha256"])
                    for row in members if row["pds_url"]
                }
            ),
            "snapshot_date": str(date.today()),
            "lifecycle_status": (
                "listed_current_catalog_orderable_status_not_stock_verified"
            ),
            "source_quality_flags": sorted({
                flag for row in members
                for flag in row["source_quality_flags"]
            }),
        })

    sku_rows.sort(key=lambda row: row["source_record_id"])
    product_rows.sort(key=lambda row: row["source_record_id"])
    sku_rendered = render(sku_rows)
    product_rendered = render(product_rows)
    SKU_OUT.write_text(sku_rendered, encoding="utf-8")
    PRODUCT_OUT.write_text(product_rendered, encoding="utf-8")
    report = {
        "source_id": SOURCE_ID,
        "source_url": SHOP_URL,
        "snapshot_date": str(date.today()),
        "shop_cards": len(sku_rows),
        "unique_source_product_ids": len({
            row["source_product_id"] for row in sku_rows
        }),
        "product_grade_identities": len(product_rows),
        "package_skus_collapsed": len(sku_rows) - len(product_rows),
        "families": dict(sorted(Counter(
            row["family_code"] for row in product_rows
        ).items())),
        "brands": dict(sorted(Counter(
            row["brand"] for row in product_rows
        ).items())),
        "priced_skus": sum(
            row["price_amount"] > 0 for row in sku_rows
        ),
        "sale_skus": sum(row["is_sale"] for row in sku_rows),
        "skus_with_pds": sum(bool(row["pds_url"]) for row in sku_rows),
        "skus_with_approvals": sum(
            bool(row["approvals_source_reported"]) for row in sku_rows
        ),
        "skus_with_requirements": sum(
            bool(row["requirements_source_reported"]) for row in sku_rows
        ),
        "skus_with_recommendations": sum(
            bool(row["recommendations_source_reported"]) for row in sku_rows
        ),
        "normalized_skus_sha256": hashlib.sha256(
            sku_rendered.encode("utf-8")
        ).hexdigest(),
        "normalized_products_sha256": hashlib.sha256(
            product_rendered.encode("utf-8")
        ).hexdigest(),
        "quality_note": (
            "The complete public shop page contains 22 orderable product "
            "cards. The dollar symbol is retained verbatim while ISO currency "
            "is left blank because the page does not state it."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
