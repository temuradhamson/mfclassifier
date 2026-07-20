#!/usr/bin/env python3
"""Normalize factual product data embedded in the official FUCHS India finder."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fuchs-india-products.jsonl"
REPORT = ROOT / "data" / "fuchs-india-products-report.json"
SOURCE_URL = "https://www.fuchs.com/in/en/products/service-links/product-finder/"
IMPRINT_URL = "https://www.fuchs.com/in/en/imprint/"
SNAPSHOT_DATE = "2026-07-20"
USER_AGENT = "MFClassifier research catalog/1.0 (+government classification research)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def normalized(value: str) -> str:
    return re.sub(r"[^0-9a-z]+", " ", html.unescape(str(value or "")).casefold()).strip()


def factual_lines(value: str) -> list[str]:
    value = re.sub(r"<br\s*/?>|</(?:p|li|div)>", "\n", value or "", flags=re.I)
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return [re.sub(r"\s+", " ", line).strip() for line in value.splitlines() if line.strip()]


def flatten_groups(groups: list[dict]) -> dict[int, dict]:
    result = {}

    def walk(items: list[dict], path: list[str]) -> None:
        for item in items:
            current = path + [item["title"]]
            result[item["uid"]] = {"title": item["title"], "path": current}
            walk(item.get("children", []), current)

    walk(groups, [])
    return result


def is_series(title: str) -> bool:
    return bool(re.search(r"\bseries\b|-series\b|\bseria\b|-seria\b|\bserie\b|-serie\b|\bgrupa\b|-grupa\b", title, re.I))


def classify_family(title: str, paths: list[list[str]], source_text: str) -> tuple[str, str]:
    path_text = " | ".join(" > ".join(path) for path in paths).casefold()
    text = f"{title} {source_text}".casefold()
    if "grease guns" in path_text or "application equipment" in path_text:
        return "", "excluded_equipment"
    if re.search(r"^SILKOLENE\s+(?:PRO 4|COMP|SUPER 4)\b.*\bSAE\b", title, re.I):
        return "M", "explicit_product_line_and_grade"
    if "lubricating greases" in path_text or "special greases" in path_text or " pastes" in path_text or "smary" in path_text or re.search(r"\bgrease\b|\bpaste\b", text):
        return "G", "product_group_or_explicit_product_form"
    if "multifunctional fluids (stou)" in path_text or "płyny wielofukcyjne (stou)" in path_text:
        return "S", "multifunctional_product_group"
    if "shock absorber fluids" in path_text or "suspension/fork fluids" in path_text or "fork oils" in path_text or "ciecze robocze do zawieszeń" in path_text or "widełek sprzęgieł" in path_text:
        return "H", "suspension_fluid_product_group"
    if "chain saw oils" in path_text:
        return "I", "chain_lubricant_product_group"
    if "glass manufacturing process" in path_text or "hot forming" in path_text:
        return "TF", "technical_fluid_product_group"
    if "transformer oils" in path_text or "isolating oils" in path_text or "oleje transformatorowe" in path_text or "oleje elektroizolacyjne" in path_text:
        return "E", "product_group"
    if "turbine oils" in path_text or "oleje turbinowe" in path_text:
        return "U", "product_group"
    if any(token in path_text for token in ["compressor oils", "refrigeration oils", "vacuum pump oils", "compressor fluids", "oils for compressed air tools", "oleje sprężarkowe", "oleje do sprężarek chłodniczych", "oleje do pomp próżniowych"]):
        return "C", "product_group"
    if "engine oils" in path_text or "oleje silnikowe" in path_text or "oleje do silników" in path_text or "oleje do 2-suwowych silników" in path_text or "oleje do 4-suwowych silników" in path_text:
        return "M", "product_group"
    hydraulic_group = "hydraulic" in path_text or "hydraulik" in path_text
    gear_group = any(token in path_text for token in ["gear oils", "gear lubrication", "open gear", "transmission fluids", "axle/differential", "multifunctional fluids (utto)", "oleje przekładniowe", "oleje do przekładni", "skrzyni biegów", "skrzyń biegów", "mechanizmów różnicowych", "oleje uniwersalne (utto)"])
    if hydraulic_group and gear_group:
        return "S", "multifunctional_product_groups"
    if hydraulic_group:
        return "H", "product_group"
    if gear_group:
        return "T", "product_group"
    if any(token in path_text for token in [
        "metal processing", "service fluids", "shock absorber fluids", "fork oils", "coolants/antifreeze",
        "brake fluids", "cleaners", "cutting", "grinding", "quenching", "forming lubricants",
        "release agents", "cooling lubricants", "heat transfer oils", "glass manufacturing process",
        "obróbka metali", "ciecze do obróbki", "środki antyadhezyjne", "przemysłowe środki myjące",
        "środki antykorozyjne", "ciecze procesowe specjalne", "oleje do obróbki cieplnej",
        "płyny hamulcowe", "płyny chłodzące", "środki czyszczące", "produkty czyszczące",
        "czyszczenie filtrów", "ciecze robocze do hamulców",
        "motorcycle cleaning", "motorcycle filter treatment", "motorcycle brake & clutch fluids",
    ]):
        return "TF", "technical_fluid_product_group"
    if any(token in path_text for token in ["corrosion prevent", "dry coatings", "solid film", "sprays", "fuel additives"]):
        return "S", "special_product_group"
    if "industrial lubricants" in path_text or any(token in path_text for token in ["chain lubric", "machine oils", "slideway oils", "textile machine oils", "wire rope", "środki smarowe do zastosowań przemysłowych", "smarowanie łańcuchów", "oleje maszynowe", "oleje do maszyn mleczarskich", "oleje do prowadnic", "oleje do maszyn włókienniczych", "lin stalowych"]):
        return "I", "industrial_product_group"
    upper_title = title.upper()
    if re.search(r"\b(?:CHAIN|CHAIN SAW) (?:LUBE|OIL)|\bCHAINWAY\b", upper_title):
        return "I", "explicit_product_line_and_application"
    if re.search(r"^RENOLIN (?:DTA|UNISYN CLP .* PA)\b", upper_title):
        return "I", "explicit_product_line_and_application"
    if re.search(r"^RENOLIN (?:HIGH GEAR|PG |PA )", upper_title):
        return "T", "explicit_product_line_and_application"
    if re.search(r"MONO(?:ETHYLENE|PROPYLENE)GLYCOL|\bTOLUENE\b", upper_title):
        return "TF", "explicit_chemical_product"
    if primary_brand_prefix(title) == "RENOLIT":
        return "G", "brand_line_and_explicit_application"
    if re.search(r"\bengine oil\b|oil for [^.]{0,40}engines|olej(?:e)? do silnik|olej silnik|olio (?:per )?motor|olio motore|motori? [24][ -]?tempi", text):
        return "M", "explicit_text"
    if primary_brand_prefix(title) in {"ECOCOOL", "ECOCUT", "LUBRODAL", "PLANTOCUT", "RENOFORM", "SAWBAND", "VISCOR", "VITROLIS", "WISURA"}:
        return "TF", "brand_line_and_explicit_application"
    if re.search(r"\bhydraulic\b|olio idraulic|fluido idraulic", text):
        return "H", "explicit_text"
    if re.search(r"\bshock absorber\b", text):
        return "H", "explicit_text"
    if re.search(r"\bcompressor\b|\brefrigeration\b|\bvacuum pump\b", text):
        return "C", "explicit_text"
    if re.search(r"\bgear oil\b|\btransmission\b|\batf\b|\baxle\b|transfer case|ripartitor[ei] di coppia", text):
        return "T", "explicit_text"
    if re.search(r"\bcoolant\b|\bantifreeze\b|\bbrake (?:and clutch )?fluid\b|\bcleaner\b|\bcutting oil\b|\bquench|solvente|sgrassaggio|distaccante|stampaggio|imbutitura|calibration fluid", text):
        return "TF", "explicit_text"
    return "S", "special_product_fallback"


def primary_brand_prefix(title: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", title.upper()).split()[0]


def extract_technical(text: str, family: str) -> dict:
    upper = text.upper().replace("–", "-")
    sae = sorted(set(re.findall(r"(?<![0-9])(?:SAE\s*)?((?:0|5|10|15|20|25)W[- ]?[0-9]{2}|(?:70|75|80|85)W(?:[- ]?[0-9]{2,3})?|[0-9]{2,3}W)(?![0-9])", upper)))
    sae = [value.replace(" ", "").replace("W", "W-") if re.fullmatch(r"(?:0|5|10|15|20|25)W[0-9]{2}", value.replace(" ", "")) else value.replace(" ", "") for value in sae]
    iso_vg = sorted(set(re.findall(r"\bISO(?:\s+VG)?\s*([0-9]{1,4})\b", upper)), key=lambda value: int(value))
    nlgi = sorted(set(re.findall(r"\bNLGI(?:\s+(?:GRADE|CLASS))?\s*(000|00|0|1/2|[1-6])\b", upper)))
    ranges = re.findall(r"TEMPERATURE\s+RANGE\s*:?\s*([+-]?\d+)\s*(?:/|TO)\s*([+-]?\d+)\s*°?C", upper)
    result = {
        "sae_grades": sae,
        "iso_vg": iso_vg,
        "nlgi": nlgi,
    }
    if ranges:
        result["temperature_min_c"] = min(int(left) for left, _ in ranges)
        result["temperature_max_c"] = max(int(right) for _, right in ranges)
    thickener_patterns = [
        ("calcium sulfonate complex", r"calcium sul(?:f|ph)onate complex"),
        ("lithium complex", r"lithium complex"),
        ("lithium soap", r"lithium[- ]soap"),
        ("aluminium complex", r"aluminium complex|aluminum complex"),
        ("polyurea", r"polyurea"),
        ("bentonite", r"bentonite"),
    ]
    for label, pattern in thickener_patterns:
        if re.search(pattern, text, re.I):
            result["thickener"] = label
            break
    if family == "G":
        result["product_form"] = "paste" if re.search(r"\bpaste\b", text, re.I) else "grease"
    elif re.search(r"\bspray\b|\baerosol\b", text, re.I):
        result["product_form"] = "spray"
    else:
        result["product_form"] = "fluid_or_oil"
    return result


def main() -> None:
    payload = fetch(SOURCE_URL)
    imprint_payload = fetch(IMPRINT_URL)
    page = payload.decode("utf-8", errors="replace")
    match = re.search(r"var FuchsProductRawData = (\{.*?\});\s*</script>", page, re.S)
    assert match, "embedded FuchsProductRawData not found"
    source = json.loads(match.group(1))
    assert len(source["products"]) == 1115
    group_index = flatten_groups(source["productGroups"])
    brand_index = {row["uid"]: row["title"] for row in source["brands"]}
    industry_index = {row["uid"]: row["title"] for row in source["industries"]}

    excluded = []
    grouped = defaultdict(list)
    for row in source["products"]:
        if is_series(row["title"]):
            excluded.append({"uid": row["uid"], "title": row["title"], "reason": "series_not_specific_product_grade"})
            continue
        grouped[normalized(row["title"])].append(row)

    records = []
    duplicate_occurrences_merged = 0
    for rows in grouped.values():
        rows = sorted(rows, key=lambda row: (-int(row.get("quality") or 0), row["uid"]))
        primary = rows[0]
        uids = sorted({row["uid"] for row in rows})
        duplicate_occurrences_merged += len(rows) - 1
        group_uids = sorted({uid for row in rows for uid in row.get("productGroups", []) + row.get("productGroupRootline", [])})
        paths = sorted({tuple(group_index[uid]["path"]) for uid in group_uids if uid in group_index})
        brands = sorted({brand_index[uid] for row in rows for uid in row.get("brands", []) if uid in brand_index})
        industries = sorted({industry_index[uid] for row in rows for uid in row.get("industries", []) if uid in industry_index})
        specifications = sorted({line for row in rows for line in factual_lines(row.get("specifications", ""))})
        approvals = sorted({line for row in rows for line in factual_lines(row.get("approvals", ""))})
        recommendations = sorted({line for row in rows for line in factual_lines(row.get("recommendations", ""))})
        source_text = " ".join(
            [primary["title"]]
            + [row.get("subtitle", "") + " " + row.get("description", "") + " " + row.get("components", "") for row in rows]
            + specifications + approvals + recommendations
        )
        family, basis = classify_family(primary["title"], [list(path) for path in paths], source_text)
        if not family:
            for row in rows:
                excluded.append({"uid": row["uid"], "title": row["title"], "reason": basis})
            continue
        technical = extract_technical(source_text, family)
        records.append({
            "source_id": "FUCHS_INDIA_PRODUCT_FINDER",
            "source_record_id": f"FUCHS-IN-{uids[0]}",
            "source_uids": uids,
            "manufacturer": "FUCHS LUBRICANTS (INDIA) PVT. LTD.",
            "brand": brands[0] if brands else "FUCHS",
            "brand_lines": brands,
            "product_name": primary["title"].strip(),
            "family_code": family,
            "classification_basis": basis,
            "market": "IN",
            "product_group_paths": [list(path) for path in paths],
            "industries": industries,
            "specifications": specifications,
            "approvals": approvals,
            "fuchs_recommendations": recommendations,
            "technical": technical,
            "flags": {
                "eu_ecolabel": any(bool(row.get("isEcolabel")) for row in rows),
                "bluev": any(bool(row.get("isBluev")) for row in rows),
                "special_applications": any(bool(row.get("isSpecialApplications")) for row in rows),
            },
            "source_product_dates": sorted({row.get("date", "") for row in rows if row.get("date")}),
            "source_description_sha256": sorted({hashlib.sha256((row.get("description") or "").encode()).hexdigest() for row in rows}),
            "source_urls": ["https://www.fuchs.com" + row["url"] for row in rows],
            "source_url": SOURCE_URL,
            "snapshot_date": SNAPSHOT_DATE,
            "grain_warning": "compound_designation_review" if "/" in primary["title"] else "",
        })

    records.sort(key=lambda row: (normalized(row["product_name"]), row["source_record_id"]))
    assert len(records) == 1007
    assert len({row["source_record_id"] for row in records}) == len(records)
    assert len({normalized(row["product_name"]) for row in records}) == len(records)
    assert all(row["family_code"] in {"M", "T", "H", "I", "C", "U", "E", "G", "TF", "S"} for row in records)
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    report = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source_id": "FUCHS_INDIA_PRODUCT_FINDER",
        "source_url": SOURCE_URL,
        "imprint_url": IMPRINT_URL,
        "source_html_sha256": hashlib.sha256(payload).hexdigest(),
        "imprint_html_sha256": hashlib.sha256(imprint_payload).hexdigest(),
        "embedded_source_rows": len(source["products"]),
        "products": len(records),
        "source_series_rows_excluded": sum(row["reason"] == "series_not_specific_product_grade" for row in excluded),
        "equipment_rows_excluded": sum(row["reason"] == "excluded_equipment" for row in excluded),
        "duplicate_source_occurrences_merged": duplicate_occurrences_merged,
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "brand_lines": len({brand for row in records for brand in row["brand_lines"]}),
        "compound_designation_review_rows": sum(bool(row["grain_warning"]) for row in records),
        "classification_basis": dict(sorted(Counter(row["classification_basis"] for row in records).items())),
        "normalized_output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "rights_review": "Only factual fields are republished with attribution. Marketing descriptions are excluded and represented only by SHA-256 evidence hashes; the India imprint limits copying of documentation for commercial use.",
        "publication_scope": "Product identity, region, group, specifications, approvals, recommendations and derived technical fields; no marketing descriptions or page layout.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
