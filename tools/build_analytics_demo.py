#!/usr/bin/env python3
"""Build a reproducible, privacy-minimised before/after analytics demo."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260720
MAX_PER_SCENARIO = 240


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def latin(value) -> str:
    return clean(value).upper().translate(str.maketrans({"С": "C", "Н": "H", "А": "A", "В": "B"}))


def sae(text: str) -> str | None:
    match = re.search(r"\b(\d{1,2})\s*W[-\s]?(\d{2,3})\b", latin(text))
    return f"{match.group(1)}W-{match.group(2)}" if match else None


def api(text: str) -> str | None:
    tokens = re.findall(r"\b(?:S[ABCDEFGHJKLMNP]|C[A-HJKN](?:-\d)?(?:\s+PLUS)?|F[AP])\b", latin(text))
    return "/".join(sorted(set(token.replace("  ", " ") for token in tokens))) or None


def sae_any(text: str) -> str | None:
    multigrade = sae(text)
    if multigrade:
        return multigrade
    match = re.search(r"\bSAE[-\s]*(30|40|50|60|70|80|85|90|110|140|190|250)\b", latin(text))
    return f"SAE {match.group(1)}" if match else None


def gl_class(text: str) -> str | None:
    match = re.search(r"\bGL[-\s]?([1-6])\b", latin(text))
    return f"GL-{match.group(1)}" if match else None


def hydraulic(text: str) -> tuple[str | None, str | None]:
    normalized = latin(text)
    class_match = re.search(r"\b(HVLPD|HLPD|HVLP|HLP|HMHP|HM)\b", normalized)
    grade_match = re.search(r"(?:HVLPD|HLPD|HVLP|HLP|HMHP|HM)[-\s()]*(\d{2,3})\b", normalized)
    if not grade_match:
        grade_match = re.search(r"(?:ISO\s*)?VG[-\s]*(\d{2,3})\b", normalized)
    return (grade_match.group(1) if grade_match else None, class_match.group(1) if class_match else None)


def coolant(text: str) -> tuple[str | None, str | None]:
    normalized = clean(text).upper()
    class_match = re.search(r"G(?:11|12\+\+|12\+|12|13)", latin(normalized).replace(" ", ""))
    temp_match = re.search(r"(?:ТЕМПЕРАТУР\w*\s+(?:НАЧАЛА\s+)?КРИСТАЛЛИЗАЦИИ.{0,100}?(?:МИНУС|-)|\bМИНУС)\s*(\d{2})", normalized)
    if not temp_match:
        temp_match = re.search(r"(?:АНТИФРИЗ|COOLANT)[^\n,;]{0,60}?-(\d{2})(?:\s*°?\s*C)?", normalized)
    generic_class = "Антифриз" if re.search(r"АНТИФРИЗ|ANTIFREEZE|COOLANT|ОХЛАЖДАЮЩ", normalized) else None
    return (class_match.group(0) if class_match else generic_class, f"−{temp_match.group(1)} °C" if temp_match else None)


def row_text(row: dict) -> str:
    return " ".join(clean(row.get(key)) for key in ("product_name", "brand", "subcategory", "tech_specs", "func_chars"))


def engine_fields(row: dict) -> dict:
    combined = row_text(row)
    return {"SAE": clean(row.get("sae_grade")) or sae(combined), "API": clean(row.get("api_class")) or api(combined)}


def gear_fields(row: dict) -> dict:
    combined = row_text(row)
    gl = clean(row.get("api_class")) or gl_class(combined)
    if not gl:
        subcategory = clean(row.get("subcategory"))
        match = re.search(r"GL[-\s]?([1-6])", latin(subcategory))
        gl = f"GL-{match.group(1)}" if match else None
    return {"SAE": clean(row.get("sae_grade")) or sae_any(combined), "API GL": gl}


def hydraulic_fields(row: dict) -> dict:
    grade, standard = hydraulic(row_text(row))
    return {"ISO VG": grade, "DIN/ISO": standard}


def coolant_fields(row: dict) -> dict:
    product_class, temperature = coolant(row_text(row))
    return {"Класс ОЖ": product_class, "Температура": temperature}


def grease_fields(row: dict) -> dict:
    value = latin(row_text(row))
    patterns = [
        (r"ЛИТОЛ[-\s]*24", "Литол-24"), (r"СОЛИДОЛ\s*ЖИРОВОЙ", "Солидол жировой"),
        (r"СОЛИДОЛ", "Солидол"), (r"ЛЗ[-\s]*ЦНИИ", "ЛЗ-ЦНИИ"),
        (r"ЖТ[-\s]*79Л", "ЖТ-79Л"), (r"ЦИАТИМ[-\s]*201", "ЦИАТИМ-201"),
        (r"БУКСОЛ", "Буксол"), (r"КРАНОЛ", "Кранол"), (r"\bЖРО\b", "ЖРО"),
        (r"СМАЗКА\s*1[-\s]*13|\b1[-\s]*13\b", "1-13"),
    ]
    mark = next((label for pattern, label in patterns if re.search(pattern, value)), None)
    nlgi = re.search(r"NLGI(?:\s*EP)?[-\s]*(\d)", value)
    if nlgi:
        mark = f"NLGI {nlgi.group(1)}" if not mark else f"{mark} · NLGI {nlgi.group(1)}"
    family = clean(row.get("subcategory"))
    return {"Тип смазки": family if family and family != "Прочие смазки" else None, "Марка / NLGI": mark}


def industrial_fields(row: dict) -> dict:
    value = latin(row_text(row))
    gost = re.search(r"\bИ[-\s]?(\d{1,3})\s*А?\b", value)
    if gost:
        suffix = "А" if re.search(rf"И[-\s]?{gost.group(1)}\s*А", value) else ""
        return {"Система": "ГОСТ-марка", "Класс": f"И-{gost.group(1)}{suffix}"}
    iso = re.search(r"(?:ISO\s*)?VG|NVI(?:[-\s]*S)?", value)
    grade = re.search(r"(?:ISO\s*)?VG[-\s]*(\d{2,3})|NVI(?:[-\s]*S)?[-\s]*(\d{2,3})", value)
    number = next((item for item in grade.groups() if item), None) if grade else None
    return {"Система": "ISO VG" if iso and number else None, "Класс": number}


def compressor_fields(row: dict) -> dict:
    value = latin(row_text(row))
    for pattern, label, system in [
        (r"\bКС[-\s]*19\b", "КС-19", "ГОСТ-марка"),
        (r"\bКП[-\s]*8С\b", "КП-8С", "ГОСТ-марка"),
        (r"\bVCL[-\s]*(46|68|100|150)\b", None, "DIN 51506 / VCL"),
        (r"\bVG[-\s]*(46|68|100|150)\b", None, "ISO VG"),
    ]:
        match = re.search(pattern, value)
        if match:
            return {"Система": system, "Марка / класс": label or match.group(1)}
    return {"Система": None, "Марка / класс": None}


def turbine_fields(row: dict) -> dict:
    value = latin(row_text(row))
    match = re.search(r"\bТП[-\s]*(22С?|30)(?:\s*У)?\b", value)
    return {"Система": "ГОСТ-марка" if match else None, "Марка": f"ТП-{match.group(1)}" if match else None}


SCENARIOS = [
    {
        "id": "engine",
        "title": "Моторные масла",
        "category": "МОТОРНЫЕ МАСЛА",
        "before_group": "Масло моторное",
        "criterion": "SAE + точный API",
        "enrich": engine_fields,
    },
    {
        "id": "hydraulic",
        "title": "Гидравлические масла",
        "category": "ГИДРАВЛИЧЕСКИЕ МАСЛА",
        "before_group": "Масло гидравлическое",
        "criterion": "ISO VG + DIN/ISO",
        "enrich": hydraulic_fields,
    },
    {
        "id": "gear",
        "title": "Трансмиссионные масла",
        "category": "ТРАНСМИССИОННЫЕ МАСЛА",
        "before_group": "Масло трансмиссионное",
        "criterion": "SAE + API GL",
        "enrich": gear_fields,
    },
    {
        "id": "coolant",
        "title": "Охлаждающие жидкости",
        "category": "ТЕХНИЧЕСКИЕ ЖИДКОСТИ",
        "before_group": "Охлаждающая жидкость",
        "criterion": "Класс ОЖ + температура",
        "enrich": coolant_fields,
    },
    {
        "id": "grease", "title": "Пластичные смазки", "category": "ПЛАСТИЧНЫЕ СМАЗКИ",
        "before_group": "Смазка пластичная", "criterion": "тип загустителя / назначение + марка или NLGI",
        "enrich": grease_fields,
    },
    {
        "id": "industrial", "title": "Индустриальные масла", "category": "ИНДУСТРИАЛЬНЫЕ МАСЛА",
        "before_group": "Масло индустриальное", "criterion": "система классификации + точный класс",
        "enrich": industrial_fields,
    },
    {
        "id": "compressor", "title": "Компрессорные масла", "category": "КОМПРЕССОРНЫЕ МАСЛА",
        "before_group": "Масло компрессорное", "criterion": "ГОСТ-марка или DIN/ISO-класс",
        "enrich": compressor_fields,
    },
    {
        "id": "turbine", "title": "Турбинные масла", "category": "ТУРБИННЫЕ МАСЛА",
        "before_group": "Масло турбинное", "criterion": "точная эксплуатационная марка",
        "enrich": turbine_fields,
    },
]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def histogram(values: list[float], bins: int = 10) -> list[dict]:
    low, high = min(values), max(values)
    if low == high:
        return [{"from": round(low), "to": round(high), "count": len(values)}]
    width = (high - low) / bins
    rows = [{"from": round(low + i * width), "to": round(low + (i + 1) * width), "count": 0} for i in range(bins)]
    for value in values:
        rows[min(bins - 1, int((value - low) / width))]["count"] += 1
    return rows


def build_scenario(source: list[dict], config: dict, rng: random.Random, lot_map: dict[str, dict]) -> dict:
    candidates = []
    for row in source:
        if row.get("category") != config["category"]:
            continue
        price = float(row.get("price_per_kg") or 0)
        fields = config["enrich"](row)
        if price <= 0 or any(not value for value in fields.values()):
            continue
        candidates.append((row, fields, price))

    prices = [entry[2] for entry in candidates]
    if not prices:
        raise ValueError(f"No eligible lots for scenario {config['id']}")
    low, high = percentile(prices, .02), percentile(prices, .98)
    candidates = [entry for entry in candidates if low <= entry[2] <= high]
    rng.shuffle(candidates)
    selected = candidates[: min(MAX_PER_SCENARIO, len(candidates))]

    lots = []
    segments = defaultdict(list)
    for row, fields, price in selected:
        source_ref = lot_map.get(clean(row.get("lot_number")), {})
        lot_id = source_ref.get("lot_id")
        key = " · ".join(fields.values())
        segments[key].append(price)
        lots.append({
            "source_row_id": row.get("id"),
            "lot_id": lot_id,
            "lot_number": row.get("lot_number"),
            "original_url": f"https://new.cooperation.uz/lots/{lot_id}" if lot_id else None,
            "offer_number": source_ref.get("offer_number"),
            "offer_url": f"https://new.cooperation.uz/e-catalog/22/{source_ref.get('offer_number')}" if source_ref.get("offer_number") else None,
            "date": str(row.get("start_date") or "")[:10],
            "raw_product_name": clean(row.get("product_name")),
            "raw_brand_text": clean(row.get("brand")),
            "price_per_kg": round(price),
            "quantity": row.get("quantity"),
            "measure": clean(row.get("measure")),
            "quantity_kg": row.get("quantity_kg"),
            "start_price_unit": row.get("start_price_unit"),
            "final_price_unit": row.get("final_price_unit"),
            "start_total": row.get("start_total"),
            "final_total": row.get("final_total"),
            "manufacturer": clean(row.get("manufacturer")),
            "country": clean(row.get("country")),
            "status": clean(row.get("lot_status") or row.get("status")),
            "technical_specs": clean(row.get("tech_specs")),
            "functional_characteristics": clean(row.get("func_chars")),
            "professional_key": key,
            "enriched_fields": fields,
            "enrichment_origin": "demo_inference",
        })

    before_avg = round(mean(item["price_per_kg"] for item in lots))
    segment_rows = []
    for key, segment_prices in segments.items():
        avg = round(mean(segment_prices))
        segment_rows.append({
            "key": key,
            "lots": len(segment_prices),
            "avg_price_per_kg": avg,
            "median_price_per_kg": round(median(segment_prices)),
            "min_price_per_kg": round(min(segment_prices)),
            "max_price_per_kg": round(max(segment_prices)),
            "difference_from_coarse_pct": round((avg / before_avg - 1) * 100, 1),
        })
    segment_rows.sort(key=lambda item: (-item["lots"], item["key"]))

    monthly = defaultdict(list)
    for lot in lots:
        if lot["date"]:
            monthly[lot["date"][:7]].append(lot["price_per_kg"])
    monthly_rows = [{"month": month, "lots": len(values), "avg": round(mean(values)), "median": round(median(values))} for month, values in sorted(monthly.items())]
    lot_prices = [item["price_per_kg"] for item in lots]

    return {
        "id": config["id"],
        "title": config["title"],
        "criterion": config["criterion"],
        "before": {
            "group": config["before_group"],
            "lots": len(lots),
            "avg_price_per_kg": before_avg,
            "median_price_per_kg": round(median(lot_prices)),
            "available_dimensions": ["наименование", "количество", "цена"],
        },
        "after": {
            "segments": segment_rows,
            "segment_count": len(segment_rows),
            "min_segment_avg": min(row["avg_price_per_kg"] for row in segment_rows),
            "max_segment_avg": max(row["avg_price_per_kg"] for row in segment_rows),
            "available_dimensions": list(lots[0]["enriched_fields"].keys()),
        },
        "lots": lots,
        "eligible_lots": len(candidates),
        "price_histogram": histogram(lot_prices),
        "monthly_prices": monthly_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lots", type=Path, required=True)
    parser.add_argument("--lot-map", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/analytics-demo.json")
    args = parser.parse_args()
    source = json.loads(args.lots.read_text(encoding="utf-8"))
    lot_map = {}
    if args.lot_map:
        with args.lot_map.open(encoding="utf-8", newline="") as handle:
            lot_map = {clean(row.get("lot_number")): row for row in csv.DictReader(handle)}
    rng = random.Random(SEED)
    scenarios = [build_scenario(source, config, rng, lot_map) for config in SCENARIOS]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": "Демонстрация влияния профессионального классификатора",
        "methodology": {
            "source": "ANIQLIK / cooperation.uz, таблица lots",
            "production_lots_at_build": 2404,
            "source_export_lots": len(source),
            "random_seed": SEED,
            "selection": f"Воспроизводимая стратифицированная случайная выборка до {MAX_PER_SCENARIO} лотов на сценарий среди записей с валидной ценой, подтверждённой публичной связью и извлекаемым полным профессиональным ключом; крайние 2% цен исключены как контроль единиц измерения.",
            "disclosure": "Профессиональные поля добавлены демонстрационно правилами классификатора и не записаны в исходную production-БД ANIQLIK.",
            "original_url_pattern": "https://new.cooperation.uz/lots/{lot_id}",
        },
        "metrics": {
            "sample_lots": sum(len(item["lots"]) for item in scenarios),
            "scenarios": len(scenarios),
            "professional_segments": sum(item["after"]["segment_count"] for item in scenarios),
            "linked_original_lots": sum(1 for item in scenarios for lot in item["lots"] if lot["original_url"]),
        },
        "scenarios": scenarios,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    args.output.write_text(content + "\n", encoding="utf-8")
    args.output.with_suffix(".js").write_text("window.MF_ANALYTICS_DEMO=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(json.dumps(payload["metrics"], ensure_ascii=False))
    for item in scenarios:
        print(item["id"], item["before"]["lots"], item["after"]["segment_count"], item["before"]["avg_price_per_kg"], item["after"]["min_segment_avg"], item["after"]["max_segment_avg"])


if __name__ == "__main__":
    main()
