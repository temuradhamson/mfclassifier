#!/usr/bin/env python3
"""Build the source registry and planning estimate for a global lubricants catalog."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "deliverables" / "Global_lubricants_catalog_registry.xlsx"


SOURCES = [
    ("TotalEnergies", "Global", "Product catalog", "https://lubricants.catalog.totalenergies.com/corporate/en_UK", 1246, "products", "Count observed 2026-07-20; GTCU 4.3 prohibits substantial database extraction/reuse", "written_permission_required"),
    ("Shell", "Global / market-specific", "EPC product catalog", "https://www.epc.shell.com/?lang=eng", None, None, "TDS/SDS by market; copying is restricted by site terms", "permission_or_permitted_access_required"),
    ("Mobil", "Global / market-specific", "Industrial product search", "https://www.mobil.com/en/lubricants/for-businesses/industrial/lubricants/search", None, None, "Search by product, specification, application and equipment builder", "ready_for_technical_review"),
    ("FUCHS", "India", "Product finder", "https://www.fuchs.com/in/en/products/service-links/product-finder/", 1115, "products", "Broad automotive, industrial, grease and metalworking portfolio", "ready_for_technical_review"),
    ("FUCHS", "United States", "Product finder", "https://www.fuchs.com/us/en/products/service-links/product-finder/", 686, "products", "Market catalog; overlaps other FUCHS markets", "ready_for_technical_review"),
    ("Motul", "Global", "Corporate disclosure", "https://cms.motul.com/images/DPEF_2024_english_e9953e284f.pdf", 19000, "active references", "Also reports more than 400 formulations; references are not normalized products", "count_evidence_only"),
    ("LIQUI MOLY", "Global / market-specific", "Official product catalog", "https://www.liqui-moly.com/en/products.html", None, None, "Automotive oils, additives, service fluids and related products", "discovery"),
    ("Castrol", "Global / market-specific", "Official product finder", "https://www.castrol.com/en/global/corporate/products.html", None, None, "Automotive and industrial ranges; market variants must be retained", "discovery"),
    ("MOLYKOTE / DuPont", "Global / location-filtered", "Official product finder", "https://www.dupont.com/molykote.html", None, None, "Hundreds of specialty lubricants; detailed chemistry and temperature attributes", "ready_for_technical_review"),
    ("Klüber Lubrication", "Global / market-specific", "Official products", "https://www.klueber.com/global/en/products-service/products/", None, None, "Specialty industrial lubricants", "discovery"),
    ("SKF", "Global", "Maintenance and lubrication products", "https://www.skf.com/group/products/maintenance-products/lubrication-management", None, None, "Greases, oils and lubrication-system consumables; exclude equipment", "discovery"),
    ("Petro-Canada Lubricants", "Global / market-specific", "Official products", "https://lubricants.petro-canada.com/en-ca/products", None, None, "Industrial, automotive, food-grade and specialty fluids", "discovery"),
    ("Chevron Lubricants", "Global / market-specific", "Official products", "https://www.chevronlubricants.com/en_us/home/products.html", None, None, "Delo, Havoline and industrial products", "discovery"),
    ("Valvoline", "Global / market-specific", "Official products", "https://www.valvolineglobal.com/en/products/", None, None, "Automotive oils and fluids; region-specific availability", "discovery"),
    ("PETRONAS Lubricants", "Global / market-specific", "Official products", "https://global.pli-petronas.com/products", None, None, "Automotive and industrial lubricants", "discovery"),
    ("ENEOS", "Global / market-specific", "Official products", "https://www.eneos-global.com/products/lubricants/", None, None, "Automotive and industrial lubricants", "discovery"),
    ("Idemitsu", "Global / market-specific", "Official lubricants", "https://www.idemitsu.com/en/business/lube/", None, None, "Automotive and industrial lubricants", "discovery"),
    ("Repsol", "Global / market-specific", "Official lubricants", "https://lubricants.repsol.com/en/products/", None, None, "Automotive and industrial product ranges", "discovery"),
    ("Gulf Oil", "Global / market-specific", "Official products", "https://www.gulfoilltd.com/products", None, None, "Automotive and industrial product ranges", "discovery"),
    ("Sinopec Lubricant", "Global / market-specific", "Official products", "https://www.sinopeclube.com/", None, None, "Automotive and industrial products; multilingual source review needed", "discovery"),
]


FIELDS = [
    ("identity", "source_product_id; manufacturer; brand; product_line; product_name; grade; market; status"),
    ("classification", "family; product_form; application; industry; standardized_name; technical_profile_id; proposed_enkt"),
    ("performance", "SAE; API; ACEA; ISO_VG; DIN; ISO_class; ASTM; GOST; OEM_approvals"),
    ("composition", "base_oil; thickener; NLGI; coolant_chemistry; petroleum_share; physical_state"),
    ("operating limits", "temperature_min_c; temperature_max_c; viscosity_40c; viscosity_100c; viscosity_index"),
    ("trade and state codes", "SKP; IKPU; TNVED_candidates; ENKT_current; unit; package; conversion_to_kg"),
    ("provenance", "source_url; TDS_url; SDS_url; source_date; valid_from; valid_to; extraction_method; evidence_hash"),
    ("quality", "confidence; review_status; reviewer; duplicate_cluster; canonical_product_id; validation_notes"),
]


ESTIMATES = [
    ("Normalized formulation-grade-market", "Brand + formulation + grade + market; package sizes excluded", 150000, 400000, 250000, "Primary analytical catalog and ENKT mapping layer"),
    ("Global commercial SKU/reference", "Country + package + label/language + sellable reference retained", 1000000, 3000000, 1800000, "Procurement and price-observation layer"),
    ("Unique technical profiles", "Brand-independent professional equivalence classes", 3000, 12000, 6000, "Candidate ENKT extension after expert validation"),
]


RULES = [
    (1, "Never overwrite source wording", "Keep raw product name, market and source snapshot alongside normalized values"),
    (2, "One canonical product is not one package", "Bottle, drum and IBC are offers/SKUs linked to the same product formulation"),
    (3, "Market variants remain visible", "Merge only when formula, grade, approvals and manufacturer identity are demonstrably the same"),
    (4, "Series is not a grade", "Mobil SHC 600 is a series; SHC 626 and SHC 630 are separate product-grade rows"),
    (5, "Approval beats marketing similarity", "Equivalence requires the professional key for the family, not name or viscosity alone"),
    (6, "Sources and rights are mandatory", "Use official pages, licensed feeds or permitted access; respect robots, terms and rate limits"),
    (7, "Lifecycle is versioned", "Active, superseded, discontinued and historical products are retained with validity dates"),
    (8, "Counts are reproducible", "Publish counts by grain, date, source, market, duplicate state and validation status"),
]


def style(ws) -> None:
    fill = PatternFill("solid", fgColor="17365D")
    for cell in ws[1]:
        cell.fill = fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for column in ws.columns:
        letter = get_column_letter(column[0].column)
        ws.column_dimensions[letter].width = min(70, max(12, max(len(str(c.value or "")) for c in column) + 2))
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def add(wb, title, headers, rows):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for row in rows:
        ws.append(row)
    style(ws)
    return ws


def main() -> None:
    wb = Workbook()
    wb.remove(wb.active)
    add(wb, "01_Паспорт", ["Показатель", "Значение"], [
        ("Статус", "Стартовый реестр источников; не завершённая мировая выгрузка"),
        ("Дата среза", date.today().isoformat()),
        ("Главная единица строки", "Brand + formulation + grade + market, без фасовки"),
        ("Плановое ядро", "250 000 нормализованных строк; рабочий диапазон 150 000–400 000"),
        ("Отдельный SKU-слой", "1,0–3,0 млн строк с рынками, языками и фасовками"),
        ("Критерий завершения", "Все источники имеют дату обхода; новые источники два цикла подряд дают <0,5% новых canonical products"),
        ("Ограничение", "Точный итог неизвестен до обхода, правовой проверки доступа и дедупликации"),
    ])
    add(wb, "02_Источники", ["Компания/бренд", "Рынок", "Источник", "URL", "Наблюдаемое число", "Единица числа", "Примечание", "Статус"], SOURCES)
    add(wb, "03_Оценка_объёма", ["Слой", "Гранулярность", "Минимум", "Максимум", "Плановый ориентир", "Назначение"], ESTIMATES)
    add(wb, "04_Схема_данных", ["Блок", "Поля"], FIELDS)
    add(wb, "05_Дедупликация", ["№", "Правило", "Реализация"], RULES)
    add(wb, "06_Этапы", ["Этап", "Результат", "Контроль"], [
        ("A. Реестр производителей", "Страны, бренды, владельцы, официальные каталоги", "URL, рынок, права доступа, дата"),
        ("B. Получение", "Raw snapshots и документы TDS/PDS/SDS", "Хэш, HTTP metadata, parser version"),
        ("C. Нормализация", "Единые семейства и профессиональные признаки", "Family-specific validation"),
        ("D. Дедупликация", "Canonical products + market offers + packages", "Explainable merge/split decisions"),
        ("E. Кодирование", "Связи ENKT–SKP–IKPU–TNVED", "Source, confidence, reviewer, validity"),
        ("F. Публикация", "Версионированный открытый каталог", "Coverage dashboard and reproducible counts"),
    ])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT)
    print(f"sources={len(SOURCES)} output={OUTPUT}")


if __name__ == "__main__":
    main()
