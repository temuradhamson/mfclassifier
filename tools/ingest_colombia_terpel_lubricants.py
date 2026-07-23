#!/usr/bin/env python3
"""Build the current Colombian Terpel lubricant catalog from official cards.

The public sitemap exposes 30 product cards with technical or safety sheets.
Three audience-specific battery-water cards share one document identity and
the two DOT 4 cards share another, yielding 27 unique products.  The matrix
below contains only audited, non-expressive technical facts from those cards
and documents; source prose and PDFs are not redistributed.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/colombia-terpel-current-lubricants.jsonl"
REPORT = ROOT / "data/colombia-terpel-current-lubricants-report.json"
SOURCE_ID = "COLOMBIA_TERPEL_CURRENT_LUBRICANT_CATALOG"
BASE = "https://www.terpel.com"
SITEMAP_URL = f"{BASE}/sitemap.xml"
CATALOG_URL = f"{BASE}/empresas/lubricantes/lubricantes-terpel"
TERMS_URL = f"{BASE}/terminos-legales2"
SNAPSHOT_DATE = "2026-07-23"
UA = "MFClassifier evidence catalog/1.0"


def p(name: str, slug: str, family: str, line: str, **technical: object) -> dict:
    return {"name": name, "slug": slug, "family_code": family, "product_line": line, "technical": technical}


PRODUCTS = [
    p("Terpel ULTREK 15W-40 PLUS", "transportadores/terpel-ultrek-15w-40-plus", "M", "heavy_duty_engine",
      sae_engine="15W-40", api=["CI-4 PLUS", "SL"], acea=["E7", "E9-12"], jaso=["DH-2"]),
    p("Terpel ULTREK TRANSMISIONES 80W-90", "transportadores/terpel-ultrek-transmision-80w-90", "T", "automotive_gear",
      sae_gear="80W-90", api_gl=["GL-5"]),
    p("Terpel Líquido para Frenos DOT 3", "conductores/liquido-para-frenos-dot-3", "TF", "brake_fluid",
      brake_fluid_class=["DOT 3"]),
    p("Terpel Líquido para Frenos DOT 4", "conductores/liquido-para-frenos-dot-4", "TF", "brake_fluid",
      brake_fluid_class=["DOT 4"]),
    p("Terpel OILTEC 50 MONOGRADO", "conductores/terpel-oiltec-50-monogrado", "M", "passenger_car_engine",
      sae_engine="50", api=["SF"]),
    p("Terpel CELERITY BIO ANTIHUMO", "motociclistas/terpel-celerity-bio-antihumo", "M", "two_stroke",
      api=["TC"], jaso=["FD"]),
    p("Terpel CELERITY FB", "motociclistas/terpel-celerity-fb", "M", "two_stroke",
      jaso=["FB"]),
    p("Terpel Agua Desmineralizada para Baterías", "conductores/agua-desmineralizada-para-baterias", "TF", "battery_fluid",
      fluid_type="demineralized battery water"),
    p("Terpel CELERITY 15W-50 SEMISINTÉTICO", "motociclistas/terpel-celerity-15w-50-semisintetico", "M", "motorcycle",
      sae_engine="15W-50", api=["SL"], jaso=["MA2"]),
    p("Terpel CELERITY 25W-50 GRUESO", "motociclistas/terpel-celerity-25w-50-grueso", "M", "motorcycle",
      sae_engine="25W-50", api=["SL"], jaso=["MA2"]),
    p("Terpel REFRIGERANTE ESTÁNDAR", "conductores/refrigerante-terpel-estandar", "TF", "coolant",
      coolant_type="water-based corrosion-inhibiting ready-to-use coolant",
      performance=["NTC 3618", "ASTM D4340", "ASTM D1384", "ASTM D2570"]),
    p("Terpel REFRIGERANTE LARGA VIDA", "conductores/refrigerante-terpel-larga-vida", "TF", "coolant",
      coolant_type="OAT long-life coolant, source-reported polyglycols 40%",
      performance=["NTC 3614", "NTC 3592", "ASTM D3306", "ASTM D4985", "JIS K2234", "GM 6277M"]),
    p("Terpel OILTEC 40 MONOGRADO", "conductores/terpel-oiltec-40-monogrado", "M", "passenger_car_engine",
      sae_engine="40", api=["SF"]),
    p("Terpel OILTEC TERGAS 50", "conductores/terpel-oiltec-tergas-50", "M", "gas_engine",
      sae_engine="50", api=["SF"]),
    p("Terpel OILTEC 10W-30 TITANIO SEMISINTÉTICO", "conductores/terpel-oiltec-10w-30-titanio-semisintetico", "M", "passenger_car_engine",
      sae_engine="10W-30", api=["SP"], ilsac=["GF-6A"], performance=["API SP Resource Conserving"]),
    p("Terpel OILTEC TERGAS 20W-50", "conductores/terpel-oiltec-tergas-20w-50", "M", "gas_engine",
      sae_engine="20W-50", api=["SP"]),
    p("Terpel OILTEC 10W-40 TITANIO", "conductores/terpel-oiltec-10w-40-titanio", "M", "passenger_car_engine",
      sae_engine="10W-40", api=["SP"]),
    p("Terpel OILTEC 20W-50 TITANIO", "conductores/terpel-oiltec-20w-50-titanio", "M", "passenger_car_engine",
      sae_engine="20W-50", api=["SP"]),
    p("Terpel OILTEC 20W-50 MULTÍGRADO", "conductores/terpel-oiltec-20w-50-multigrado", "M", "passenger_car_engine",
      sae_engine="20W-50", api=["SP"]),
    p("Terpel CELERITY 20W-50 TITANIO", "motociclistas/terpel-celerity-20w-50-titanio", "M", "motorcycle",
      sae_engine="20W-50", api=["SL"], jaso=["MA2"]),
    p("Terpel ULTREK TRANSMISIONES 90", "transportadores/terpel-ultrek-transmision-90", "T", "automotive_gear",
      sae_gear="90", api_gl=["GL-5"]),
    p("Terpel ULTREK DIFERENCIALES 85W-140", "transportadores/terpel-ultrek-diferencial-85w-140", "T", "automotive_gear",
      sae_gear="85W-140", api_gl=["GL-5"]),
    p("Terpel ULTREK 15W-40 MULTÍGRADO", "transportadores/terpel-ultrek-15w-40-multigrado", "M", "heavy_duty_engine",
      sae_engine="15W-40", api=["CH-4", "SJ"]),
    p("Terpel ULTREK 50 MONOGRADO", "transportadores/terpel-ultrek-50-monogrado", "M", "heavy_duty_engine",
      sae_engine="50", api=["CF", "SF"]),
    p("Terpel ULTREK 25W-50 ALTO KM", "transportadores/terpel-ultrek-25w-50-alto-km", "M", "heavy_duty_engine",
      sae_engine="25W-50", api=["CF-4"]),
    p("Terpel ULTREK DIFERENCIALES 140", "transportadores/terpel-ultrek-diferencial-140", "T", "automotive_gear",
      sae_gear="140", api_gl=["GL-5"]),
    p("Terpel ULTREK 15W-40 PRO CK4 SEMISINTÉTICO", "transportadores/terpel-ultrek-15w-40-pro-semisintetico", "M", "heavy_duty_engine",
      sae_engine="15W-40", api=["CK-4", "SP"], acea=["E11-22", "E7-22", "E9-16"], jaso=["DH-2"],
      performance=["DTFR 15C100", "Renault Trucks RLD-3", "MTU Type 2.1", "Deutz DQC III-10 LA", "MAN M 3275-1", "MAN M 3575"]),
]


def get(url: str) -> tuple[bytes, str, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read(), response.geturl(), dict(response.headers)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def document_links(page_html: str, page_url: str) -> list[dict]:
    found = []
    pattern = r'<a[^>]+href="([^"]+)"[^>]+title="([^"]*Ficha[^"]*)"'
    for href, label in re.findall(pattern, page_html, re.I | re.S):
        found.append({
            "label": html.unescape(label).strip(),
            "url": urllib.parse.urljoin(page_url, html.unescape(href)),
        })
    return found


def main() -> None:
    sitemap_bytes, _, _ = get(SITEMAP_URL)
    sitemap_root = ET.fromstring(sitemap_bytes)
    sitemap = {}
    for entry in sitemap_root.findall(".//{*}url"):
        loc = entry.findtext("{*}loc")
        if loc:
            sitemap[loc] = entry.findtext("{*}lastmod") or ""

    rows = []
    document_cache: dict[str, dict] = {}
    for index, product in enumerate(PRODUCTS, 1):
        page_url = f"{CATALOG_URL}/{product['slug']}"
        if page_url not in sitemap:
            raise RuntimeError(f"Terpel product missing from official sitemap: {page_url}")
        page_bytes, final_url, _ = get(page_url)
        page_html = page_bytes.decode("utf-8", "replace")
        links = document_links(page_html, final_url)
        if not links:
            raise RuntimeError(f"Terpel product has no official technical/safety document: {page_url}")
        for document in links:
            url = document["url"]
            if url not in document_cache:
                content, final_document_url, headers = get(url)
                if not content.startswith(b"%PDF"):
                    raise RuntimeError(f"Terpel document is not a PDF: {url}")
                document_cache[url] = {
                    "url": url,
                    "final_url": final_document_url,
                    "sha256": sha256(content),
                    "bytes": len(content),
                    "content_disposition_source": headers.get("Content-Disposition", ""),
                }
            document.update(document_cache[url])

        technical = {
            "sae_engine": product["technical"].get("sae_engine", ""),
            "sae_gear": product["technical"].get("sae_gear", ""),
            "api": product["technical"].get("api", []),
            "api_gl": product["technical"].get("api_gl", []),
            "acea": product["technical"].get("acea", []),
            "ilsac": product["technical"].get("ilsac", []),
            "jaso": product["technical"].get("jaso", []),
            "brake_fluid_class": product["technical"].get("brake_fluid_class", []),
            "coolant_type": product["technical"].get("coolant_type", ""),
            "fluid_type": product["technical"].get("fluid_type", ""),
            "performance": product["technical"].get("performance", []),
        }
        rows.append({
            "source_id": SOURCE_ID,
            "source_record_id": f"TERPEL-CO-{index:02d}",
            "market": "Colombia",
            "manufacturer": "Organización Terpel S.A.",
            "brand": "Terpel",
            "product_name": product["name"],
            "product_line": product["product_line"],
            "family_code": product["family_code"],
            "technical": technical,
            "lifecycle_status": "listed_on_current_official_product_sitemap",
            "evidence_status": "official_manufacturer_product_card_and_documents",
            "snapshot_date": SNAPSHOT_DATE,
            "source_url": page_url,
            "source_page_lastmod": sitemap[page_url],
            "source_page_sha256": sha256(page_bytes),
            "documents": links,
            "source_quality_flags": [
                "official_product_identity_and_specifications",
                "catalog_presence_not_independent_performance_approval",
                "duplicate_audience_cards_collapsed_by_identical_document_identity",
                "marketing_prose_excluded",
            ],
        })

    if len(PRODUCTS) != 27 or len(rows) != 27:
        raise RuntimeError(f"Terpel audit matrix drift: {len(PRODUCTS)} products, {len(rows)} rows")

    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "source_id": SOURCE_ID,
        "snapshot_date": SNAPSHOT_DATE,
        "sitemap_url": SITEMAP_URL,
        "sitemap_rows": len(sitemap),
        "sitemap_sha256": sha256(sitemap_bytes),
        "product_cards_with_documents_observed": 30,
        "duplicate_audience_cards_collapsed": 3,
        "normalized_products": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "product_lines": dict(sorted(Counter(row["product_line"] for row in rows).items())),
        "unique_source_documents": len(document_cache),
        "technical_sheet_links": sum(
            document["label"] == "Ficha técnica" for row in rows for document in row["documents"]
        ),
        "safety_sheet_links": sum(
            document["label"] == "Ficha de seguridad" for row in rows for document in row["documents"]
        ),
        "normalized_output_sha256": sha256(OUT.read_bytes()),
        "rights_boundary": (
            "Official public pages and documents are used for attributed non-expressive factual "
            "extraction only. Terpel source prose, page presentation and PDFs are not redistributed."
        ),
        "terms_url": TERMS_URL,
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
