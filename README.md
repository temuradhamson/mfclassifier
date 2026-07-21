# MF Classifier v3

Единый классификатор смазочных материалов и технических жидкостей.

Публичная версия: <https://temuradhamson.github.io/mfclassifier/>

## Что внутри

- 531 уникальная коммерческая позиция и 21 бренд;
- 225 отраслевых классов масел, смазок и технических жидкостей;
- 42 международных стандарта и 42 метода ASTM;
- 40 отраслевых сценариев и 9 температурных зон;
- 282 референсные позиции CHILON LUBRICANTS;
- объяснимые предлагаемые связи между товарами и техническими классами;
- актуальные сертификаты, ТН ВЭД, ИКПУ, ЕНКТ и СКП там, где они есть в источниках.
- демонстрация «До / После» на воспроизводимой выборке из 558 реальных лотов
  ANIQLIK: 8 продуктовых сценариев, 89 профессиональных ценовых сегментов,
  интерактивные графики распределения, динамики и точности ценового ориентира,
  а также раскрываемые карточки лотов.

## Архитектура данных

`data/catalog-v3.json` — переносимая JSON-модель. `data/catalog-v3.js` содержит
ту же модель в виде `window.MF_CLASSIFIER_DATA` для надёжной работы статического
GitHub Pages без отдельного сетевого запроса.

Сущности не смешиваются в одну таблицу:

- `products` — реальные коммерческие продукты;
- `classes` — эталонные технические классы;
- `references` — стандарты, ASTM, отрасли, температуры и CHILON LUBRICANTS;
- `sources` — происхождение и редакции данных;
- `quality` — конфликты, покрытие связями и оговорки.

Связь `product.class_match` имеет статус `suggested`, confidence и список
признаков. Она является технической подсказкой, а не юридическим заключением.

`data/analytics-demo.json` содержит обезличенную выборку лотов для демонстрации
влияния классификатора на ценовую аналитику. Номера лотов, исходные названия и
цены реальны. Профессиональные поля помечены как демонстрационно вычисленные и
в production-базу ANIQLIK не записываются. Внешние переходы на карточки
cooperation.uz намеренно не публикуются; подробности открываются внутри
классификатора.

## Сборка данных

```bash
python3 -m pip install -r requirements-build.txt
python3 tools/build_catalog.py
python3 tools/build_analytics_demo.py \
  --lots /path/to/lots_all.json \
  --lot-map /path/to/lot_map.csv
```

Исходные Excel находятся в `sources/`. Для повторного извлечения указателя
Справочный каталог передайте через `--reference-pdf`; сгенерированные данные уже включены в
репозиторий.

## Мировой каталог и расширение ЕНКТ

Отдельный provenance-aware слой содержит 18 504 канонические продуктовые строки
на срез 21.07.2026. В него уже входят проектные источники, AIChilon, официальные
реестры JASO, GM dexos, NMMA, NLGI, ZF TE-ML, Allison TES, Driventic DIWA, Mercedes-Benz Trucks DTFR, Mercedes-Benz BeVo, официальные каталоги Volvo Genuine и четырнадцати рынков FUCHS, исторический каталог LIQUI MOLY 2020 и текущий LIQUI MOLY OpenAPI 2026, действующие рекомендации MAN, USDA BioPreferred и открытый API EU Ecolabel. Это проверенный
растущий seed, а не заявление о полном мировом охвате; подтверждённый мировой
итог появится только после подключения разрешённых источников и дедупликации.

- `data/world-catalog.sqlite3.gz` — детерминированно сжатая SQLite-база с
  продуктами, спецификациями, кодами, источниками, упаковками и решениями
  дедупликации; команда сборки создаёт рядом локальную `world-catalog.sqlite3`;
- `data/liqui-moly-current-products.jsonl` — 447 текущих master-products LIQUI
  MOLY и 985 артикулов/фасовок из официальных sitemap + OpenAPI;
- `data/liqui-moly-2020-2026-lifecycle.jsonl` — доказательное сопоставление
  текущих карточек с каталогом 2020 без автоматического объявления отсутствующих
  позиций снятыми с производства;
- `deliverables/World_lubricants_catalog_seed.xlsx` — проверяемая выгрузка;
- `deliverables/Global_lubricants_catalog_registry.xlsx` — реестр 55 источников
  и статусы допуска;
- `deliverables/ENKT_GSM_extension_pilot.xlsx` — 171 пилотный технический
  профиль и предложение по пятизначному суффиксу ЕНКТ.

```bash
python3 tools/ingest_jaso_filed_oils.py
python3 tools/ingest_official_licensed_products.py
python3 tools/ingest_usda_biopreferred.py
python3 tools/ingest_zf_te_ml.py
python3 tools/ingest_allison_approved_fluids.py
python3 tools/ingest_driventic_diwa_approved_oils.py
python3 tools/ingest_mercedes_dtfr_approved_fluids.py
python3 tools/ingest_mercedes_bevo_approved_fluids.py
python3 tools/ingest_volvo_genuine_fluids.py
python3 tools/ingest_man_service_products.py
python3 tools/ingest_fuchs_india_catalog.py
python3 tools/ingest_fuchs_us_catalog.py
python3 tools/ingest_fuchs_germany_catalog.py
python3 tools/ingest_fuchs_poland_catalog.py
python3 tools/ingest_fuchs_italy_catalog.py
python3 tools/ingest_fuchs_sweden_catalog.py
python3 tools/ingest_fuchs_spain_catalog.py
python3 tools/ingest_fuchs_france_catalog.py
python3 tools/ingest_fuchs_turkey_catalog.py
python3 tools/ingest_fuchs_canada_catalog.py
python3 tools/ingest_fuchs_china_catalog.py
python3 tools/ingest_fuchs_czech_catalog.py
python3 tools/ingest_fuchs_mexico_catalog.py
python3 tools/ingest_fuchs_south_africa_catalog.py
python3 tools/ingest_liqui_moly_2020_catalog.py
python3 tools/ingest_liqui_moly_current_catalog.py
python3 tools/build_world_catalog_seed.py
python3 tools/verify_world_catalog.py
```

## Локальный запуск

```bash
python3 -m http.server 8080
```

Откройте <http://localhost:8080/>.
