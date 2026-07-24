#!/usr/bin/env python3
"""Normalize ENACOL Cabo Verde's four officially linked 2019 price catalogs.

The current ENACOL lubricant landing page still links these PDFs, but their
HTTP Last-Modified dates are in 2019. Product identities remain useful official
country-market evidence. Prices are therefore retained as historical offers
and must never be counted as current availability.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUT_PRODUCTS = ROOT / "data" / "cabo-verde-enacol-legacy-products.jsonl"
OUT_OFFERS = ROOT / "data" / "cabo-verde-enacol-legacy-offers.jsonl"
REPORT = ROOT / "data" / "cabo-verde-enacol-legacy-report.json"
CACHE = ROOT / ".cache" / "enacol-cabo-verde"
LANDING_URL = "https://www.enacol.cv/lubrificantes/"
ROBOTS_URL = "https://www.enacol.cv/robots.txt"
PRIVACY_URL = "https://www.enacol.cv/privacidade/"
PDF_BASE = "https://www.enacol.cv/wp-content/uploads/2019/05"
SOURCE_ID = "CABO_VERDE_ENACOL_OFFICIALLY_LINKED_2019_PRICE_CATALOGS"
SNAPSHOT_DATE = "2026-07-24"
USER_AGENT = "MFClassifierResearch/1.0 (government-classification research)"

CATALOGS = {
    "auto": {
        "url": f"{PDF_BASE}/lubrificantes_auto.pdf",
        "pages": 6,
        "column_bounds": (170, 395, 455),
    },
    "industria": {
        "url": f"{PDF_BASE}/lubrificantes_industria.pdf",
        "pages": 3,
        "column_bounds": (185, 405, 470),
    },
    "marinha": {
        "url": f"{PDF_BASE}/lubrificantes_marinha.pdf",
        "pages": 1,
        "column_bounds": (165, 400, 465),
    },
    "massa": {
        "url": f"{PDF_BASE}/lubrificantes_massa.pdf",
        "pages": 3,
        "column_bounds": (230, 500, 640),
    },
}

# These rows are headings or consumer cleaning/care products outside the
# lubricant, coolant and operational technical-fluid scope.
EXCLUDED_NAMES = {
    "Galp Care",
    "Galp Care Shampoo Auto",
    "Galp Care Limpa Cockpit",
    "Galp Care Limpa Estofos",
    "Galp Care Anti-Furo",
    "Galp Expert Limpeza Professional",
    "Galp Expert - Fluídos para Travões",
}


def fetch(url: str) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read(), {key.casefold(): value for key, value in response.headers.items()}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def grouped_lines(page: pdfplumber.page.Page) -> list[list[dict]]:
    """Reconstruct visual rows while tolerating the marine PDF's 2 px drift."""
    groups: list[list[object]] = []
    words = sorted(
        page.extract_words(x_tolerance=1, y_tolerance=2),
        key=lambda word: (word["top"], word["x0"]),
    )
    for word in words:
        if not groups or abs(float(groups[-1][0]) - word["top"]) > 3.5:
            groups.append([word["top"], []])
        groups[-1][1].append(word)
    return [group[1] for group in groups]


def columns(words: list[dict], bounds: tuple[int, int, int]) -> tuple[str, str, str, str]:
    values = []
    lower = 0
    for upper in (*bounds, 10_000):
        values.append(clean(" ".join(
            word["text"]
            for word in sorted(words, key=lambda item: item["x0"])
            if lower <= word["x0"] < upper
        )))
        lower = upper
    return tuple(values)  # type: ignore[return-value]


def extract_blocks(payload: bytes, catalog: str) -> tuple[list[dict], int]:
    config = CATALOGS[catalog]
    blocks: list[dict] = []
    with pdfplumber.open(io.BytesIO(payload)) as document:
        if len(document.pages) != config["pages"]:
            raise RuntimeError(
                f"{catalog}: expected {config['pages']} pages, found {len(document.pages)}"
            )
        for page_number, page in enumerate(document.pages, 1):
            current = None
            for words in grouped_lines(page):
                left, specification, package, price = columns(
                    words, config["column_bounds"]
                )
                if (
                    left.startswith("Galp ")
                    or left.startswith("Total Lubmarine")
                    or left == "AdBlue"
                ):
                    current = {
                        "catalog": catalog,
                        "page": page_number,
                        "name": left,
                        "specification_lines": [],
                        "package_price_rows": [],
                    }
                    blocks.append(current)
                if current is None:
                    continue
                if specification and specification != "Especificações":
                    current["specification_lines"].append(specification)
                if package and package != "Embalagem":
                    current["package_price_rows"].append({
                        "package": package,
                        "price_raw": price if price != "Preço" else "",
                    })
    return blocks, config["pages"]


def family_code(catalog: str, name: str) -> str:
    if catalog == "massa":
        return "G"
    if name == "AdBlue":
        return "TF"
    if catalog == "marinha":
        upper = name.upper()
        if "VISGA " in upper:
            return "H"
        if any(value in upper for value in ("DACNIS ", "BARELF ", "PLANETELF ")):
            return "C"
        if "EPONA " in upper:
            return "I"
        if "CERAN " in upper:
            return "G"
        return "M"
    if catalog == "industria":
        if name.startswith(("Galp Tralub", "Galp Hidraulic")):
            return "T"
        if name.startswith(("Galp Hidrolep", "Galp Hidroliv", "Galp FGL H")):
            return "H"
        if name.startswith("Galp Turbinoil"):
            return "U"
        if name.startswith(("Galp Polar", "Galp Lubarep")):
            return "C"
        if name.startswith(("Galp Moldax", "Galp Calibração")):
            return "S"
        return "I"
    if name.startswith(("Galp Transvex", "Galp Multitrans", "Galp LS 90", "Galp Transoil", "Galp Transmatic")):
        return "T"
    if name == "Galp Moto Action Chain":
        return "S"
    if name == "Galp Moto Action Fork Oil 5W":
        return "H"
    if name.startswith(("Galp Care ", "Galp Expert Trávia", "Galp Boost ")):
        return "TF"
    if name.startswith(("Galp Expert Multiusos", "Galp Expert PL")):
        return "S"
    return "M"


def normalized_sae(value: str) -> str:
    value = value.upper().replace(" ", "")
    match = re.fullmatch(r"(\d{1,2}W)(\d{2,3})", value)
    return f"{match.group(1)}-{match.group(2)}" if match else value


def api_values(text: str) -> tuple[list[str], list[str]]:
    api: set[str] = set()
    api_gl: set[str] = set()
    for match in re.finditer(r"\bAPI\s+([^;|]+)", text, re.I):
        fragment = match.group(1).upper()
        api_gl.update(re.findall(r"\bGL-?[1-6]\b", fragment))
        api.update(re.findall(
            r"\b(?:C[A-H](?:-[24])?|C[IJK]-4|CF-2|S[A-P]|T[CD])\b",
            fragment,
        ))
    return (
        sorted(api),
        sorted(value.replace("GL", "GL-") if "-" not in value else value for value in api_gl),
    )


def inferred_iso_vg(catalog: str, name: str, family: str) -> str:
    if family not in {"H", "I", "C", "U"}:
        return ""
    prefixes = (
        "Galp Hidrolep", "Galp Hidroliv", "Galp FGL H", "Galp Turbinoil",
        "Galp Transgear", "Galp Polar", "Galp Lubarep", "Galp ROC",
        "Galp Mafertex", "Galp Termoil", "Galp WOT", "Total Lubmarine VISGA",
        "Total Lubmarine DACNIS", "Total Lubmarine EPONA",
        "Total Lubmarine BARELF", "Total Lubmarine PLANETELF",
    )
    if not name.startswith(prefixes):
        return ""
    match = re.search(r"(?:\s|FGL [HE])(\d{2,3})$", name.upper())
    return match.group(1) if match else ""


def specifications(catalog: str, name: str, family: str, lines: list[str]) -> dict:
    text = " | ".join(lines)
    sae_matches = re.findall(
        r"\bSAE\s+(\d{1,2}W(?:-\d{2,3})?|\d{1,3})\b", text, re.I
    )
    if not sae_matches and name == "Total Lubmarine DISOLA W 15W40":
        sae_matches = ["15W40"]
    api, api_gl = api_values(text)
    acea = sorted(set(re.findall(r"\b[ABCDE][1-9]\b", " ".join(
        match.group(1)
        for match in re.finditer(r"\bACEA\s+([^;|]+)", text, re.I)
    ).upper())))
    nlgi_match = re.search(r"\bNLGI\s+([0-6](?:-[0-6])?|00|000)\b", text, re.I)
    brake_match = re.search(r"\bDOT\s*([345](?:\.\d)?)\b", text, re.I)
    standards = sorted({
        clean(line)
        for line in lines
        if len(clean(line)) <= 220
        and re.search(
            r"\b(?:API|ACEA|ILSAC|JASO|SAE|ISO|DIN|ASTM|AFNOR|ANSI|AGMA|"
            r"NSF|FDA|NMMA|MIL|VW|VOLVO|MB|MAN|BMW|PORSCHE|RENAULT|FORD|"
            r"GM|ZF|ALLISON|CAT(?:ERPILLAR)?|CUMMINS|MACK|MTU|DEUTZ|"
            r"SCANIA|FIAT|JOHN DEERE|CASE|VICKERS|DENISON|CINCINNATI)\b",
            line,
            re.I,
        )
    }, key=str.casefold)
    specs: dict[str, object] = {
        "sae_engine": "",
        "sae_gear": "",
        "iso_vg": inferred_iso_vg(catalog, name, family),
        "nlgi": nlgi_match.group(1) if nlgi_match else "",
        "api": api,
        "api_gl": api_gl,
        "acea": acea,
        "ilsac": sorted(set(re.findall(r"\bGF-[1-7][A-Z]?\b", text.upper()))),
        "jaso": sorted(set(re.findall(r"\b(?:MA2?|FB|FC|FD)\b", " ".join(
            match.group(1)
            for match in re.finditer(r"\bJASO\s+([^;|]+)", text, re.I)
        ).upper()))),
        "brake_fluid_class": f"DOT {brake_match.group(1)}" if brake_match else "",
        "standards_and_approvals_source_reported": standards,
    }
    if sae_matches:
        field = "sae_gear" if family == "T" else "sae_engine"
        specs[field] = normalized_sae(sae_matches[0])
    concentration = re.search(r"\bConcentra(?:ção|cao)\s+(\d+)%", text, re.I)
    if concentration:
        specs["coolant_concentration_percent"] = int(concentration.group(1))
    thickener = re.search(r"Espessante:\s*([^.;]+)", text, re.I)
    if thickener:
        specs["thickener_source_reported"] = clean(thickener.group(1))
    if name == "Galp Turan G 0-1":
        specs["grease_grade_source_reported"] = "0-1"
    return specs


def package_facts(package: str) -> dict:
    normalized = package.replace(",", ".")
    match = re.search(
        r"(?:(\d+)\s*x\s*)?(\d+(?:\.\d+)?)\s*(Lt?s?|ml|Kg?s?|gr)\b",
        normalized,
        re.I,
    )
    if not match:
        return {"quantity_per_package": None, "unit": "", "weight_kg": None}
    count = int(match.group(1) or 1)
    quantity = float(match.group(2)) * count
    unit_raw = match.group(3).casefold()
    if unit_raw in {"lt", "lts"}:
        unit = "l"
    elif unit_raw == "ml":
        unit = "l"
        quantity /= 1000
    elif unit_raw in {"kg", "kgs"}:
        unit = "kg"
    else:
        unit = "kg"
        quantity /= 1000
    return {
        "quantity_per_package": quantity,
        "unit": unit,
        "weight_kg": quantity if unit == "kg" else None,
    }


def price_amount(value: str) -> int | None:
    if not value:
        return None
    if not re.fullmatch(r"[\d .]+\s+ECV", value):
        raise RuntimeError(f"Unexpected ENACOL price: {value!r}")
    return int(re.sub(r"\D", "", value.removesuffix("ECV")))


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    landing, _ = fetch(LANDING_URL)
    robots, _ = fetch(ROBOTS_URL)
    privacy, _ = fetch(PRIVACY_URL)
    landing_text = landing.decode(errors="replace")
    if not all(config["url"].replace("https://", "http://").encode() in landing for config in CATALOGS.values()):
        raise RuntimeError("ENACOL landing page no longer links all four catalogs")
    if b"Disallow: /wp-admin/" not in robots or b"Allow: /wp-admin/admin-ajax.php" not in robots:
        raise RuntimeError("Unexpected ENACOL robots policy")
    if b"Pol\xc3\xadtica de Privacidade" not in privacy and b"pol\xc3\xadtica de privacidade" not in privacy:
        raise RuntimeError("ENACOL privacy page marker changed")

    documents = {}
    all_blocks = []
    for catalog, config in CATALOGS.items():
        payload, headers = fetch(config["url"])
        (CACHE / f"{catalog}.pdf").write_bytes(payload)
        blocks, pages = extract_blocks(payload, catalog)
        documents[catalog] = {
            "url": config["url"],
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "pages": pages,
            "last_modified": headers.get("last-modified", ""),
            "etag": headers.get("etag", ""),
            "raw_product_like_blocks": len(blocks),
        }
        if "2019" not in headers.get("last-modified", ""):
            raise RuntimeError(
                f"{catalog}: historical Last-Modified marker changed: "
                f"{headers.get('last-modified', '')!r}"
            )
        all_blocks.extend(blocks)

    products = []
    offers = []
    excluded = []
    for block in all_blocks:
        if block["name"] in EXCLUDED_NAMES:
            excluded.append(block["name"])
            continue
        family = family_code(block["catalog"], block["name"])
        record_id = f"ENACOL-CV-{len(products) + 1:03d}"
        brand = (
            "Total Lubmarine"
            if block["name"].startswith("Total Lubmarine")
            else "Galp"
            if block["name"].startswith("Galp ")
            else "Brand not stated"
        )
        manufacturer = (
            "Total Lubmarine"
            if brand == "Total Lubmarine"
            else "Galp Energia"
            if brand == "Galp"
            else ""
        )
        document = documents[block["catalog"]]
        technical = specifications(
            block["catalog"], block["name"], family, block["specification_lines"]
        )
        factual_projection = {
            "catalog": block["catalog"],
            "page": block["page"],
            "product_name": block["name"],
            "brand": brand,
            "family_code": family,
            "technical": technical,
            "packages": block["package_price_rows"],
        }
        products.append({
            "source_id": SOURCE_ID,
            "source_record_id": record_id,
            "source_url": LANDING_URL,
            "technical_document_url": document["url"],
            "technical_document_sha256": document["sha256"],
            "source_page": block["page"],
            "source_factual_projection_sha256": hashlib.sha256(
                json.dumps(
                    factual_projection,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            "snapshot_date": SNAPSHOT_DATE,
            "market": "Cabo Verde",
            "manufacturer": manufacturer,
            "brand": brand,
            "local_distributor": "ENACOL — Empresa Nacional de Combustíveis, S.A.",
            "product_name": block["name"],
            "family_code": family,
            "lifecycle_status": "officially_linked_legacy_price_catalog_2019",
            "evidence_status": "official_country_distributor_historical_price_catalog",
            "technical": technical,
            "source_quality_flags": [
                "catalog_http_last_modified_2019_not_current_availability",
                "price_preserved_as_historical_offer_not_active_offer",
                *(
                    ["source_brand_not_stated"]
                    if brand == "Brand not stated" else []
                ),
            ],
        })
        for package_index, package_row in enumerate(block["package_price_rows"], 1):
            facts = package_facts(package_row["package"])
            offers.append({
                "source_id": SOURCE_ID,
                "source_record_id": f"{record_id}-PKG-{package_index:02d}",
                "product_source_record_id": record_id,
                "market": "Cabo Verde",
                "package_name": package_row["package"],
                **facts,
                "price_amount": price_amount(package_row["price_raw"]),
                "price_currency": "CVE",
                "price_currency_source_reported": "ECV",
                "price_status": (
                    "published_historical_2019_catalog_price"
                    if package_row["price_raw"]
                    else "historical_catalog_package_price_missing"
                ),
                "lifecycle_status": "historical_official_price_catalog_2019",
                "archive_type": "official_distributor_legacy_price_catalog",
                "archive_reason": "PDF HTTP Last-Modified is 2019; current availability is not asserted",
                "source_url": document["url"],
                "source_page": block["page"],
            })

    if len(products) != 148:
        raise RuntimeError(f"Expected 148 in-scope product rows, found {len(products)}")
    if len(excluded) != len(EXCLUDED_NAMES) or set(excluded) != EXCLUDED_NAMES:
        raise RuntimeError(f"Unexpected exclusion set: {excluded!r}")
    if len({row["source_record_id"] for row in products}) != len(products):
        raise RuntimeError("Duplicate ENACOL source record IDs")
    if len({(row["brand"].casefold(), row["product_name"].casefold()) for row in products}) != len(products):
        raise RuntimeError("Duplicate ENACOL brand/product identities")
    if not offers or not all(row["package_name"] for row in offers):
        raise RuntimeError("ENACOL historical package extraction failed")

    product_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in products
    )
    offer_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in offers
    )
    OUT_PRODUCTS.write_text(product_text, encoding="utf-8")
    OUT_OFFERS.write_text(offer_text, encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "officially_linked_complete_2019_price_catalogs_normalized",
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "owner": "ENACOL — Empresa Nacional de Combustíveis, S.A.",
        "market": "Cabo Verde",
        "landing_url": LANDING_URL,
        "robots_url": ROBOTS_URL,
        "privacy_url": PRIVACY_URL,
        "landing_sha256": hashlib.sha256(landing).hexdigest(),
        "robots_sha256": hashlib.sha256(robots).hexdigest(),
        "privacy_sha256": hashlib.sha256(privacy).hexdigest(),
        "documents": documents,
        "source_product_like_blocks": len(all_blocks),
        "excluded_out_of_scope_or_heading_rows": len(excluded),
        "excluded_names": sorted(excluded),
        "normalized_product_rows": len(products),
        "historical_package_offer_rows": len(offers),
        "historical_priced_offer_rows": sum(
            row["price_amount"] is not None for row in offers
        ),
        "historical_unpriced_package_rows": sum(
            row["price_amount"] is None for row in offers
        ),
        "brands": dict(sorted(Counter(row["brand"] for row in products).items())),
        "families": dict(sorted(Counter(row["family_code"] for row in products).items())),
        "catalog_product_rows": dict(sorted(Counter(
            next(
                catalog
                for catalog, document in documents.items()
                if document["url"] == row["technical_document_url"]
            )
            for row in products
        ).items())),
        "rows_with_sae": sum(
            bool(row["technical"]["sae_engine"] or row["technical"]["sae_gear"])
            for row in products
        ),
        "rows_with_iso_vg": sum(
            bool(row["technical"]["iso_vg"]) for row in products
        ),
        "rows_with_nlgi": sum(bool(row["technical"]["nlgi"]) for row in products),
        "rows_with_api_or_api_gl": sum(
            bool(row["technical"]["api"] or row["technical"]["api_gl"])
            for row in products
        ),
        "product_output_sha256": hashlib.sha256(product_text.encode()).hexdigest(),
        "offer_output_sha256": hashlib.sha256(offer_text.encode()).hexdigest(),
        "lifecycle_note": (
            "The four PDFs remain linked from the current official ENACOL page, "
            "but every PDF reports an HTTP Last-Modified date of 5 May 2019. "
            "Products and prices are historical evidence, not current offers."
        ),
        "grain_note": (
            "One product row per published product/grade line; one historical "
            "offer row per explicit package line. Case quantities are arithmetically "
            "normalized from the printed pack expression."
        ),
        "publication_scope": (
            "Attributed factual product names, classifications, standards, package "
            "and historical price facts with URLs/hashes only; descriptions, artwork "
            "and page layout are not redistributed."
        ),
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
