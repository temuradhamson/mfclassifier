#!/usr/bin/env python3
"""Normalize factual product-grade rows from Pakistan State Oil's catalog."""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "pso-official-lubricant-products.jsonl"
REPORT = ROOT / "data" / "pso-official-lubricant-products-report.json"
SOURCE_ID = "PAKISTAN_STATE_OIL_OFFICIAL_CATALOG"
SITEMAP_URL = "https://psopk.com/sitemap.xml"
ROBOTS_URL = "https://psopk.com/robots.txt"
COPYRIGHT_URL = "https://psopk.com/en/copyright"
SNAPSHOT_DATE = "2026-07-21"
USER_AGENT = "MFClassifierResearch/1.0 (noncommercial government classification research)"


def product(family: str, name: str, grade_kind: str, grades: str) -> dict:
    return {
        "family": family,
        "name": name,
        "grade_kind": grade_kind,
        "grades": grades.split() if grades else [""],
    }


# A row is a concrete product-grade identity. Values were audited against the
# linked current PDS tables; ungraded products remain one row rather than being
# split from prose or application claims.
PRODUCTS = {
    "deo-3000": product("M", "PSO DEO 3000", "sae_engine", "10W 20W 30 40 50 15W-40 20W-50"),
    "deo-6000": product("M", "PSO DEO 6000", "sae_engine", "15W-40 20W-50"),
    "deo-8000": product("M", "PSO DEO 8000", "sae_engine", "15W-40 20W-50"),
    "deo-max": product("M", "PSO DEO MAX", "sae_engine", "15W-40"),
    "dieselube-hd": product("M", "PSO DIESELUBE HD", "sae_engine", "50"),
    "alpha-ep-grease": product("G", "PSO ALPHA EP GREASE", "nlgi", "0 1 2 3"),
    "alpha-grease": product("G", "PSO ALPHA GREASE", "nlgi", "2 3"),
    "bearing-compound": product("S", "PSO BEARING COMPOUND", "source_variant", "C T-96"),
    "compressor-oil": product("C", "PSO COMPRESSOR OIL", "iso_vg", "46 68 100 150 220"),
    "gear-wire-rope-compound": product("S", "PSO GEAR & WIRE ROPE COMPOUND", "source_variant", "A C D F G H R-96"),
    "gearled-ep": product("T", "PSO GEARLED EP", "iso_vg", "68 100 150 220 320 460 680"),
    "heat-transfer-oil": product("I", "PSO HEAT TRANSFER OIL", "iso_vg", "32 100 460"),
    "heat-transfer-oil-excel": product("I", "PSO HEAT TRANSFER OIL EXCEL", "iso_vg", "32"),
    "hygrol": product("H", "PSO HYGROL", "iso_vg", "22 32 46 68 100 150"),
    "hygrol-aw": product("H", "PSO HYGROL AW", "iso_vg", "32 46 68 100 150 220 320"),
    "hygrol-excel-aw": product("H", "PSO HYGROL EXCEL AW", "iso_vg", "100"),
    "low-pour-oil": product("C", "PSO LOW POUR OIL", "iso_vg", "32 46 68"),
    "machine-oil": product("I", "PSO MACHINE OIL", "source_variant", "HJ-20 HJ-30 HJ-40 HJ-45"),
    "moly-grease-ep": product("G", "PSO MOLY GREASE EP", "nlgi", "2"),
    "mp-grease": product("G", "PSO MP GREASE", "nlgi", "2 3"),
    "neat-metal-cutting-oil": product("I", "PSO NEAT METAL CUTTING OIL", "iso_vg", "22 32"),
    "rustillo": product("S", "PSO RUST PREVENTIVE OIL", "", ""),
    "slideway-oil": product("I", "PSO SLIDEWAY OIL", "iso_vg", "32 68 220"),
    "solcut-oil": product("I", "PSO SOLCUT OIL", "", ""),
    "spincot": product("I", "PSO SPINCOT", "iso_vg", "10 15 22"),
    "sugar-mill-oil-plus": product("I", "PSO SUGAR MILL OIL PLUS", "source_variant", "3200 3800 4200 4500"),
    "super-gas-engine-oil-plus": product("M", "PSO SUPER GAS ENGINE OIL PLUS", "source_variant", "LA-40 MA-40"),
    "synthetic-smo-gold": product("I", "PSO SYNTHETIC SMO GOLD", "source_variant", "16K 20K 25K"),
    "texol": product("I", "PSO TEXOL", "iso_vg", "32 46 68 100 150 220 320 460 680"),
    "transformer-oil": product("E", "PSO TRANSFORMER OIL", "", ""),
    "turbine-oil-t": product("U", "PSO TURBINE OIL T", "iso_vg", "32 46 68 100"),
    "pso-blaze": product("M", "PSO BLAZE 4T", "sae_engine", "20W-40 20W-50"),
    "pso-two-stroke-oil": product("M", "PSO 2-STROKE ENGINE OIL", "", ""),
    "carient-fully-synthetic": product("M", "PSO CARIENT FULLY SYNTHETIC", "sae_engine", "5W-30"),
    "carient-plus": product("M", "PSO CARIENT PLUS", "sae_engine", "20W-50"),
    "carient-s-pro": product("M", "PSO CARIENT S-PRO", "sae_engine", "0W-20 5W-30"),
    "carient-ultra-synthetic": product("M", "PSO CARIENT ULTRA", "sae_engine", "10W-30 10W-40"),
    "flushing-oil": product("TF", "PSO FLUSHING OIL", "", ""),
    "geartec-gear-oil-ep-gl4": product("T", "PSO GEARTEC GEAR OIL EP GL-4", "sae_gear", "80 90 140 80W-90 85W-140"),
    "geartec-gear-oil-ep-gl5": product("T", "PSO GEARTEC GEAR OIL EP GL-5", "sae_gear", "90 140 80W-90 85W-140"),
    "transmatic-atf": product("T", "PSO TRANSMATIC ATF", "", ""),
    "generator-oil": product("M", "PSO GENERATOR OIL", "sae_engine", "20W-40"),
    "hydraulic-brake-fluid": product("TF", "PSO HYDRAULIC BRAKE FLUID HD", "brake_fluid_class", "DOT-3 DOT-4"),
}

PAGE_ONLY_GRADES = {("deo-8000", "20W-50"), ("mp-grease", "3")}
PDS_ONLY_GRADES = {
    ("synthetic-smo-gold", "16K"),
    ("carient-ultra-synthetic", "10W-40"),
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def document_link(page_html: str, label: str) -> str:
    values = re.findall(
        rf'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*{re.escape(label)}',
        page_html,
        flags=re.I | re.S,
    )
    return html.unescape(values[0]).strip() if values else ""


def package_values(page_html: str) -> list[str]:
    match = re.search(
        r"Pack Sizes?\s*:\s*<br\s*/?>\s*(?:<span[^>]*>)?(.*?)(?:</span>|</a>)",
        page_html,
        flags=re.I | re.S,
    )
    if not match:
        return []
    return sorted({clean(value) for value in re.split(r"\s*,\s*", clean(match.group(1))) if clean(value)})


def pdf_text(payload: bytes) -> str:
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        return "\n".join(page.extract_text(x_tolerance=1, y_tolerance=3) or "" for page in pdf.pages)


STANDARD_TOKEN = re.compile(
    r"\b(?:API|ACEA|ILSAC|JASO|DEXRON|MERCON|ALLISON|ZF|DIN|ISO|ASTM|AFNOR|PARKER|DENISON|EATON|"
    r"BOSCH|FIVES|AIST|SAE|SEB|GM|CUMMINS|DAIMLER|MACK|RENAULT|VOLVO|CAT(?:ERPILLAR)?|DEUTZ|"
    r"DETROIT|MTU|MAN|MB[- ]|GLOBAL DHD|VOITH|FORD|GENERAL MOTOR|SIEMENS|ALSTOM|BS |IEC|GB )\b",
    flags=re.I,
)


def performance_claims(text: str) -> list[str]:
    claims = []
    for fragment in re.split(r"[•\n]", text):
        value = re.sub(r"\s+", " ", fragment).strip(" -\t")
        if not value or len(value) > 180 or not STANDARD_TOKEN.search(value):
            continue
        if any(token in value.casefold() for token in ("where api", "compatible with api", "viscosity grade")):
            continue
        if re.match(r"^(?:API|ACEA|ILSAC|JASO|General Motor|Ford|Allison|VOITH|Caterpillar|ZF|Cummins|Daimler|MACK|RENAULT|VOLVO|CAT|DEUTZ|Detroit|MTU|MAN|Global DHD|MB-|Parker|Bosch|Eaton|Fives|ASTM|SAE|ISO|DIN|AFNOR|AIST|SEB|GM|Siemens|Alstom|BS |IEC|GB )", value, flags=re.I):
            claims.append(value)
    return sorted(set(claims), key=str.casefold)


def normalized_specs(claims: list[str], grade_kind: str, grade: str) -> dict:
    joined = " | ".join(claims).upper()
    api = set()
    api_gl = set()
    for claim in claims:
        match = re.search(r"\bAPI\s+(.+)", claim.upper())
        if not match:
            continue
        for value in re.split(r"\s*[/,&]\s*", match.group(1)):
            value = value.strip().replace("GL 4", "GL-4").replace("GL 5", "GL-5")
            if re.fullmatch(r"GL-[45]", value):
                api_gl.add(value)
            elif re.fullmatch(
                r"(?:C(?:A|B|C|D(?:-II)?|E|F(?:-[24])?|G-4|H-4|I-4(?: PLUS)?|J-4|K-4)|"
                r"FA-4|S[ABCDEFGHJKLMNPR](?: PLUS|-RC)?|TC)",
                value,
            ):
                api.add(value)
    acea = sorted(set(re.findall(r"\b(?:E[479]|A[1-5]/B[1-5])\b", joined)))
    jaso = sorted(set(re.findall(r"\b(?:MA2|MA|FB|FC|FD|DH-1|1-A)\b", joined)))
    ilsac = sorted(set(re.findall(r"\bGF-[0-9][A-Z]?\b", joined)))
    dexron = sorted(set(re.findall(r"\bDEXRON\s+(?:III\s+[GH]|III|II)\b", joined)))
    specs: dict[str, object] = {
        "standards_and_approvals_source_reported": claims,
        "api": sorted(api),
        "api_gl": sorted(api_gl),
        "acea": acea,
        "jaso": jaso,
        "ilsac": ilsac,
        "dexron": dexron,
    }
    if grade_kind and grade:
        specs[grade_kind] = grade.replace("DOT-", "DOT ") if grade_kind == "brake_fluid_class" else grade
    return specs


def product_name(config: dict, grade: str) -> str:
    if not grade:
        return config["name"]
    labels = {
        "sae_engine": "SAE",
        "sae_gear": "SAE",
        "iso_vg": "ISO VG",
        "nlgi": "NLGI",
        "brake_fluid_class": "",
        "source_variant": "",
    }
    return " ".join(value for value in (config["name"], labels[config["grade_kind"]], grade.replace("DOT-", "DOT ")) if value)


def main() -> None:
    sitemap_payload = fetch(SITEMAP_URL)
    robots_payload = fetch(ROBOTS_URL)
    copyright_payload = fetch(COPYRIGHT_URL)
    robots = robots_payload.decode(errors="replace")
    copyright_text = clean(copyright_payload.decode(errors="replace"))
    assert "Allow: /" in robots
    assert "non-commercial, informational, and personal purposes only" in copyright_text

    urls = sorted(set(re.findall(r"https://psopk\.com/en/lubricants/[^<]+", sitemap_payload.decode(errors="replace"))))
    product_pages = {}
    for url in urls:
        slug = urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        if slug not in PRODUCTS:
            continue
        page_payload = fetch(url)
        page_html = page_payload.decode(errors="replace")
        pds_url = document_link(page_html, "Product Data Sheet")
        msds_url = document_link(page_html, "Material Safety Data Sheet")
        assert pds_url and msds_url, url
        product_pages[slug] = {
            "url": url,
            "payload": page_payload,
            "html": page_html,
            "pds_url": pds_url,
            "msds_url": msds_url,
        }
    assert set(product_pages) == set(PRODUCTS), {
        "missing": sorted(set(PRODUCTS) - set(product_pages)),
        "new": sorted(set(product_pages) - set(PRODUCTS)),
    }

    rows = []
    documents = []
    for slug, config in PRODUCTS.items():
        page = product_pages[slug]
        pds_payload = fetch(page["pds_url"])
        text = pdf_text(pds_payload)
        claims = performance_claims(text)
        pds_sha = hashlib.sha256(pds_payload).hexdigest()
        documents.append(f"{page['pds_url']}|{pds_sha}")
        packages = package_values(page["html"])
        page_factual_projection = json.dumps({
            "source_url": page["url"],
            "technical_document_url": page["pds_url"],
            "safety_document_url": page["msds_url"],
            "packages_source_reported_at_series_level": packages,
        }, ensure_ascii=False, sort_keys=True).encode()
        for grade in config["grades"]:
            flags = []
            evidence = "linked_current_product_data_sheet"
            row_claims = claims
            if (slug, grade) in PAGE_ONLY_GRADES:
                evidence = "current_product_page_only_not_observed_in_linked_pds"
                flags.append("current_page_grade_not_observed_in_linked_pds")
                row_claims = []
            if (slug, grade) in PDS_ONLY_GRADES:
                flags.append("linked_pds_grade_not_listed_in_current_page_grade_summary")
            if slug == "carient-s-pro" and grade == "0W-20":
                flags.append("current_page_ow_20_typo_resolved_by_linked_pds_0w_20")
            if slug == "hydraulic-brake-fluid":
                flags.append("current_page_title_break_typo_resolved_by_linked_pds_brake")
                if grade == "DOT-4":
                    flags.append("dot_4_table_grade_without_separate_dot_4_performance_bullet")
            specs = normalized_specs(row_claims, config["grade_kind"], grade)
            if slug == "carient-ultra-synthetic":
                specs["api"] = ["SN-RC"] if grade == "10W-30" else ["SN PLUS", "SN"]
            record_key = f"{slug}|{config['grade_kind']}|{grade}"
            rows.append({
                "source_id": SOURCE_ID,
                "source_record_id": "PSO-" + hashlib.sha256(record_key.encode()).hexdigest()[:16].upper(),
                "brand": "PSO",
                "manufacturer": "Pakistan State Oil Company Limited",
                "market": "PK",
                "family_code": config["family"],
                "product_name": product_name(config, grade),
                "source_series": config["name"],
                "source_grade": grade,
                "source_grade_kind": config["grade_kind"],
                "source_grade_evidence": evidence,
                "source_url": page["url"],
                "technical_document_url": page["pds_url"],
                "technical_document_sha256": pds_sha,
                "safety_document_url": page["msds_url"],
                "source_page_factual_projection_sha256": hashlib.sha256(page_factual_projection).hexdigest(),
                "packages_source_reported_at_series_level": packages,
                "snapshot_date": SNAPSHOT_DATE,
                "lifecycle_status": "listed_on_current_official_catalog_page",
                "publication_restriction": "noncommercial_informational_use_with_attribution",
                "specifications": specs,
                "source_quality_flags": sorted(flags),
            })

    assert len(rows) == 124, len(rows)
    assert len({row["source_record_id"] for row in rows}) == len(rows)
    assert len({(row["product_name"], row["family_code"]) for row in rows}) == len(rows)
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": SOURCE_ID,
        "sitemap_url": SITEMAP_URL,
        "robots_url": ROBOTS_URL,
        "copyright_url": COPYRIGHT_URL,
        "sitemap_url_set_sha256": hashlib.sha256("\n".join(urls).encode()).hexdigest(),
        "robots_text_sha256": hashlib.sha256(clean(robots).encode()).hexdigest(),
        "copyright_text_sha256": hashlib.sha256(copyright_text.encode()).hexdigest(),
        "source_product_series_pages": len(product_pages),
        "source_pds_documents": len(documents),
        "source_pds_aggregate_sha256": hashlib.sha256("\n".join(sorted(documents)).encode()).hexdigest(),
        "normalized_product_grade_rows": len(rows),
        "families": dict(sorted(Counter(row["family_code"] for row in rows).items())),
        "grade_evidence": dict(sorted(Counter(row["source_grade_evidence"] for row in rows).items())),
        "rows_with_source_quality_flags": sum(bool(row["source_quality_flags"]) for row in rows),
        "rows_with_series_level_packages": sum(bool(row["packages_source_reported_at_series_level"]) for row in rows),
        "output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "publication_restriction": "noncommercial_informational_use_with_attribution",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
