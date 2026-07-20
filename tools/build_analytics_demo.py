#!/usr/bin/env python3
"""Build a reproducible, privacy-minimised before/after analytics demo."""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260720
SAMPLE_PER_SCENARIO = 36


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
    return (class_match.group(0) if class_match else None, f"−{temp_match.group(1)} °C" if temp_match else None)


SCENARIOS = [
    {
        "id": "engine",
        "title": "Моторные масла",
        "category": "МОТОРНЫЕ МАСЛА",
        "before_group": "Масло моторное",
        "criterion": "SAE + точный API",
        "enrich": lambda row: (
            {"SAE": sae(row.get("brand")), "API": api(row.get("brand"))},
            None,
        ),
    },
    {
        "id": "hydraulic",
        "title": "Гидравлические масла",
        "category": "ГИДРАВЛИЧЕСКИЕ МАСЛА",
        "before_group": "Масло гидравлическое",
        "criterion": "ISO VG + DIN/ISO",
        "enrich": lambda row: (
            dict(zip(("ISO VG", "DIN/ISO"), hydraulic(f"{row.get('brand', '')} {row.get('tech_specs', '')}"))),
            None,
        ),
    },
    {
        "id": "gear",
        "title": "Трансмиссионные масла",
        "category": "ТРАНСМИССИОННЫЕ МАСЛА",
        "before_group": "Масло трансмиссионное",
        "criterion": "SAE + API GL",
        "enrich": lambda row: (
            {"SAE": sae(row.get("brand")), "API GL": gl_class(f"{row.get('brand', '')} {row.get('subcategory', '')}")},
            None,
        ),
    },
    {
        "id": "coolant",
        "title": "Охлаждающие жидкости",
        "category": "ТЕХНИЧЕСКИЕ ЖИДКОСТИ",
        "before_group": "Охлаждающая жидкость",
        "criterion": "Класс ОЖ + температура",
        "enrich": lambda row: (
            dict(zip(("Класс ОЖ", "Температура"), coolant(f"{row.get('brand', '')} {row.get('tech_specs', '')}"))),
            None,
        ),
    },
]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def build_scenario(source: list[dict], config: dict, rng: random.Random) -> dict:
    candidates = []
    for row in source:
        if row.get("category") != config["category"]:
            continue
        price = float(row.get("price_per_kg") or 0)
        fields, _ = config["enrich"](row)
        if price <= 0 or any(not value for value in fields.values()):
            continue
        candidates.append((row, fields, price))

    prices = [entry[2] for entry in candidates]
    if not prices:
        raise ValueError(f"No eligible lots for scenario {config['id']}")
    low, high = percentile(prices, .02), percentile(prices, .98)
    candidates = [entry for entry in candidates if low <= entry[2] <= high]
    rng.shuffle(candidates)
    selected = candidates[: min(SAMPLE_PER_SCENARIO, len(candidates))]

    lots = []
    segments = defaultdict(list)
    for row, fields, price in selected:
        key = " · ".join(fields.values())
        segments[key].append(price)
        lots.append({
            "lot_number": row.get("lot_number"),
            "date": str(row.get("start_date") or "")[:10],
            "raw_product_name": clean(row.get("product_name")),
            "raw_brand_text": clean(row.get("brand")),
            "price_per_kg": round(price),
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
            "min_price_per_kg": round(min(segment_prices)),
            "max_price_per_kg": round(max(segment_prices)),
            "difference_from_coarse_pct": round((avg / before_avg - 1) * 100, 1),
        })
    segment_rows.sort(key=lambda item: (-item["lots"], item["key"]))

    return {
        "id": config["id"],
        "title": config["title"],
        "criterion": config["criterion"],
        "before": {
            "group": config["before_group"],
            "lots": len(lots),
            "avg_price_per_kg": before_avg,
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
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lots", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/analytics-demo.json")
    args = parser.parse_args()
    source = json.loads(args.lots.read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    scenarios = [build_scenario(source, config, rng) for config in SCENARIOS]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": "Демонстрация влияния профессионального классификатора",
        "methodology": {
            "source": "ANIQLIK / cooperation.uz, таблица lots",
            "production_lots_at_build": 2404,
            "source_export_lots": len(source),
            "random_seed": SEED,
            "selection": "Воспроизводимая случайная выборка среди лотов с валидной ценой и извлекаемым полным профессиональным ключом; крайние 2% цен исключены как контроль единиц измерения.",
            "disclosure": "Профессиональные поля добавлены демонстрационно правилами классификатора и не записаны в исходную production-БД ANIQLIK.",
        },
        "metrics": {
            "sample_lots": sum(len(item["lots"]) for item in scenarios),
            "scenarios": len(scenarios),
            "professional_segments": sum(item["after"]["segment_count"] for item in scenarios),
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
