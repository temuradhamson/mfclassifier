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

Отдельный provenance-aware слой содержит 98 955 канонических продуктовых строк
на срез 21.07.2026. В него уже входят проектные источники, AIChilon, официальные
реестры JASO, GM dexos, NMMA, NLGI, ZF TE-ML, Allison TES, Driventic DIWA,
Mercedes-Benz Trucks DTFR, Mercedes-Benz BeVo, официальные каталоги Volvo Genuine,
Mack Genuine и Scania Genuine Engine Oils, исторический Mack Service Bulletin
175-61-08 с 803 нормализованными product-grade approval identity, Brava Lubricants,
государственной Ceylon
Petroleum Corporation (Ceypetco) и тридцати
двух рынков FUCHS, исторический каталог LIQUI MOLY 2020 и
текущий LIQUI MOLY OpenAPI 2026, действующие рекомендации MAN, USDA BioPreferred
и открытый API EU Ecolabel. Слой также включает 12 664 строки
продукта-класса-вязкости из еженедельного
открытого государственного реестра масел и смазок ANP Бразилии, а также
12 626 опубликованных товарных строк государственного перечня NPT Индонезии
2021–2025. В индонезийском срезе 12 575 строк содержат номер NPT, а 51 строка
с ошибочным заполнением государственного источника сохранена с явным флагом и
не выдаётся за подтверждённую регистрацию. Открытый государственный реестр
Thailand DOEB добавляет 6 213 регистрационных строк моторных масел из последнего
доступного полного снимка за март 2024: 6 210 уникальных номеров, SAE и поля
API/ACEA/JASO/ILSAC/OEM/NMMA. 727 точных повторных регистраций объединены в
5 486 product identities с сохранением всех исходных строк. Три конфликтующих номера и одна нестандартная
вязкость сохранены с quality issues; срок действия вычисляется по опубликованной
дате и не выдаётся за live-подтверждение. Один
регистрационный номер ANP может соответствовать нескольким вязкостным или
эксплуатационным исполнениям, поэтому они не схлопываются в одну строку.
Подключены также официальные реестры DLA QPD, Blue Angel, Austrian Ecolabel UZ 14, Korea Eco-Label и
открытые Product Conformity Data MOIAT ОАЭ. Из 1 236 сертификатов MOIAT извлечено
3 176 товарных вхождений, нормализованных в 1 840 продуктов/моделей; фасовки и
продления сертификатов не раздувают число формул. Из открытого bulk-CSV US EPA
Safer Choice добавлены ещё два явно названных медицинских инструментальных
лубриканта: 12 строк UPC/GTIN/MPN объединены по товарной identity. Nordic Swan
CSV отдельно подтвердил 60 уже имеющихся EU Ecolabel строк без создания дублей.
Публичный Green Choice Philippines License Checker добавляет три исторические
карточки моторных масел по критерию GCP 2008032. Все три находятся только в
таблице Expired; опечатка источника `SW-40` сохранена и помечена, но не
исправлена догадкой. Тайваньский MOENV (26 488 строк), Singapore Green Label и
21 региональный PDF BSTI Бангладеш проверены без создания ложных product rows:
первые два не содержат смазочного продуктового охвата, а BSTI публикует только
держателя, лицензию и общий класс стандарта без торгового продукта или града.
Официальный открытый реестр документов о соответствии ЕАЭС добавляет 38 444
консервативные доказательные product identities. Полный индексированный обход
17 десятизначных кодов ТН ВЭД охватил 81 076 уникальных документов: из 51 768
товарных упоминаний объединены 13 324 повторных сертификатных случая, а 68 630
общих формулировок и не-продуктовых фрагментов исключены. Для каждой строки
сохраняются ТН ВЭД, техрегламент, lifecycle документа и кликабельная официальная
карточка. Только 2 943 строки содержат явно извлечённую торговую марку; в
35 501 строке изготовитель/держатель используется как явно помеченный fallback,
поэтому эти значения нельзя трактовать как независимо подтверждённые бренды или
как доказательство текущей доступности товара.
Открытая государственная база US EPA ChemExpo/CPDat 4.1 содержит 5 915
нормализованных продуктовых identity. В профильных и смежных PUC-категориях
проверены 10 342 товарных вхождения: 7 450 сохранены, 2 892 явных топлива,
очистителя, покрытия и иных нецелевых товаров исключены, а 1 535 вариантов
фасовки и повторных названий объединены внутри источника. Из полученных identity
275 сопоставлены с уже имеющимися строками и 5 640 создали новые канонические
позиции. Категория industrial mold
release agents добавлена после построчного аудита: из 323 исходных записей
сохранены 233 явных или вручную классифицированных продукта, 90 сомнительных
автоматических присвоений исключены. Для каждого продукта сохранены исходные ChemExpo ID и прямые ссылки;
поля состава и контактные данные не публикуются. CPDat не сообщает единый
актуальный коммерческий статус, поэтому все записи помечены как
`historical_or_current_status_not_reported` и не увеличивают число подтверждённых
активных предложений.
Публичная проверка лицензий Pakistan Standards and Quality Control Authority
добавляет 14 отдельных доказательных строк по стандарту PS 343: одну лицензию,
действующую на дату среза, и 13 истёкших. Гранулярность источника —
сертифицированная область бренда для mono-/multi-grade engine oil, а не
конкретная рецептура. Поэтому SAE/API не выводятся догадкой, а короткие названия
вроде ZIC и XCEL не объединяются с одноимёнными коммерческими продуктами.
Официальная страница Philippine Bureau of Product Standards добавляет два
живых сертификационных среза тормозных жидкостей. Из 3 558 строк PS licensees
отобраны 13 профильных лицензий и разложены в 89 licence + label + DOT scopes.
Из 19 461 строки ICC certificate holders отобраны 114 профильных записей:
129 grade-occurrences нормализованы в 34 holder + label + class identity после
объединения повторных диапазонов наклеек. Итого добавлено 123 строки: 62 DOT 3,
56 DOT 4, одна ENV6 и четыре без опубликованного функционального класса. Ошибки
источника — опечатки, неверные стандарты и шинные размеры в поле типа — не
исправляются догадкой, а сохраняются quality flags. PS/ICC не считаются
активными рыночными предложениями.
Официальный 112-страничный реестр Ghana Standards Authority за январь–сентябрь
2025 добавляет ещё 16 точных сертификационных строк: 13 моторных масел, два
трансмиссионных масла и один радиаторный coolant. Сохранены торговое
обозначение, SAE/API там, где они напечатаны, национальный/ASTM-стандарт,
лицензия, срок и точная координата в PDF. Аудированная транскрипция закреплена
SHA-256 официального документа; одна лицензия истекла к дате среза, 15 были в
пределах опубликованного срока. Эти строки также не считаются предложениями.
Из публичного государственного каталога Kenya Bureau of Standards добавлены
750 продуктов смазочного и технического назначения: 775 S-Mark permit
объединены по товарной identity, а 25 продлений/дублей не раздувают число строк.
В публикацию включены только факты сертификации и обозначения стандартов, без
адресов, контактов и текста Kenya Standards.
Публичные государственные реестры UNBS Уганды и TBS Танзании добавили ещё 229
товарных identity: 46 и 183 соответственно. В TBS перечисления внутри одной
лицензии разделены на конкретные продукты; повторные сроки одной лицензии
сохраняются как история, но не создают дубли продукта или внешнего кода.
Официальный перечень MANCAP Chemical Sector Standards Organisation of Nigeria
добавил 608 продуктов от 127 производителей. Строгий профессиональный фильтр
отобрал 286 из 2 011 сертификационных строк: 613 товарных обозначений сведены в
608 identity, а пять повторов с разной пунктуацией API или повторной строкой не
раздувают каталог. Адреса, штат, графика знака и несвязанные химические продукты
не публикуются.
Публичный S-Mark directory Rwanda Standards Board добавил девять действующих
товаров: восемь моторных масел и один пищевой смазочный материал. Из 1 843
строк каталога сохраняются только продукт, производитель, лицензия, обозначение
стандарта, статус и срок; адреса и контакты исключены. Индийский BIS включён в
план источников, но массовый отчёт защищён CAPTCHA, поэтому без официального
API/экспорта его строки не копируются. Аналогично каталог BPCL MAK учитывается
только агрегатно: официальный сайт заявляет 400+ grades, а его условия требуют
письменного разрешения на воспроизведение материалов.
Официальный каталог Ceypetco добавил 47 продуктовых града/цветовых исполнения
из 23 линий и 22 актуальных TDS. Профессиональные варианты разнесены по SAE,
ISO VG и NLGI. Два противоречия внутри TDS (SAE 10W-30/10W-40 у Scooter и
Red/Green у охлаждающей жидкости), а также нестандартная печать Ford-кода у
жидкости ГУР сохранены как quality issues и не исправляются догадкой.
Публичный API EOLCS на 21.07.2026 показывает 35 174 лицензированных продукта от
883 компаний, но строки не импортируются: условия API требуют письменного
разрешения на массовое копирование и переиздание. Это проверенный растущий seed,
а не заявление о полном мировом охвате;
подтверждённый мировой
итог появится только после подключения разрешённых источников и дедупликации.

- `data/world-catalog-products.jsonl.gz` — детерминированно сжатый полный
  JSONL-агрегат; несжатая копия создаётся локально при сборке и не хранится в Git;
- `data/world-catalog.sqlite3.xz` — детерминированно сжатая SQLite-база с
  продуктами, спецификациями, кодами, источниками, упаковками и решениями
  дедупликации; команда сборки создаёт рядом локальную `world-catalog.sqlite3`;
- `data/liqui-moly-current-products.jsonl` — 447 текущих master-products LIQUI
  MOLY и 985 артикулов/фасовок из официальных sitemap + OpenAPI;
- `data/liqui-moly-2020-2026-lifecycle.jsonl` — доказательное сопоставление
  текущих карточек с каталогом 2020 без автоматического объявления отсутствующих
  позиций снятыми с производства;
- `data/anp-brazil-lubricant-products.jsonl` — 12 664 действующих
  регистрационных продукта/града ANP с назначением, SAE/ISO/NLGI, уровнем
  свойств, составом и provenance исходных строк;
- `data/indonesia-npt-lubricant-products.jsonl` — 12 626 опубликованных
  строк NPT с компанией, товаром, сроком, страницей, техническими признаками и
  отдельными статусами качества источника; active/expired является вычисленной
  оценкой по месяцу окончания, а не live-подтверждением;
- `data/uae-moiat-conformity-products.jsonl` — 1 840 нормализованных
  сертифицированных продукта/модели ОАЭ с брендом, SAE/API/ACEA/JASO/DOT,
  сертификатами, сроками, штрихкодами и отделёнными фасовками;
- `data/eaeu-conformity-lubricant-products.jsonl` — 38 444 нормализованные
  доказательные строки ЕАЭС с 51 768 исходными товарными упоминаниями,
  объединёнными повторными сертификатами, ТН ВЭД, техрегламентами, сроками и
  прямыми ссылками на официальные карточки;
- `data/epa-safer-choice-lubricants.jsonl` — два продукта из официального
  открытого CSV EPA с объединёнными UPC, GTIN и MPN;
- `data/epa-chemexpo-lubricants.jsonl` — 5 915 нормализованных product identity
  из открытой ChemExpo/CPDat 4.1 с 7 450 исходными Product ID, PUC-категориями,
  владельцами, прямыми карточками и явным неизвестным lifecycle;
- `data/psqca-engine-oil-licences.jsonl` — 14 публичных CM-лицензий PSQCA на
  сертифицированные области брендов моторного масла по PS 343, без ложного
  достраивания индивидуальных SAE/API-градов;
- `data/philippines-bps-brake-fluid-products.jsonl` — 123 нормализованные
  доказательные PS/ICC-строки Philippine BPS по тормозным жидкостям с DOT/ENV6,
  лицензиями, сертификатами, sticker ranges и явными source-quality flags;
- `data/ghana-gsa-certified-lubricant-products.jsonl` — 16 сертифицированных
  GSA Ghana масел и coolant с SAE/API, стандартами, лицензиями и сроками;
- `data/kebs-smark-lubricant-products.jsonl` — 750 продуктов из публичного
  реестра S-Mark KEBS с 775 разрешениями, сроками и обозначениями стандартов;
- `data/east-africa-certified-lubricant-products.jsonl` — 229 продуктов из
  публичных сертификационных реестров UNBS и TBS с permit/licence lifecycle;
- `data/son-mancap-chemical-lubricant-products.jsonl` — 608 продуктов из
  официального перечня SON MANCAP Chemical Sector с техническими обозначениями
  и точной ссылкой на строку и страницу исходного PDF;
- `data/rsb-smark-lubricant-products.jsonl` — девять действующих продуктов из
  публичного S-Mark directory Rwanda Standards Board;
- `data/green-choice-philippines-lubricants.jsonl` — три архивные карточки
  моторных масел из национального публичного GCP License Checker;
- `data/austrian-ecolabel-uz14-products.jsonl` — 11 текущих продуктов пяти
  лицензиатов государственного Austrian Ecolabel UZ 14; десять карточек
  присоединены как независимые доказательства к существующим identity, одна
  добавила новую строку; действует ограничение на коммерческое переиздание;
- `data/ceypetco-lubricant-products.jsonl` — 47 продуктовых града/цветовых
  исполнения официального каталога Ceypetco со ссылками и SHA-256 22 TDS;
- `tools/ingest_eaeu_conformity_lubricants.py` — возобновляемый двухпроходный
  загрузчик открытого реестра соответствия ЕАЭС: товарное обозначение,
  изготовитель, ТН ВЭД, техрегламент, статус документа и прямая карточка;
  основной обход использует точные индексированные коды ТН ВЭД и стабильные
  `_id`-курсоры, а текстовые срезы доступны как дополнительная стратегия;
  независимые кодовые срезы и REST-проекции загружаются с ограниченной
  параллельностью (`--workers`, по умолчанию 4), а каждая сырая страница
  сохраняется как checkpoint для безопасного продолжения после 504/maintenance;
  диагностически обрезанные выгрузки остаются в `.cache` и не входят в каталог;
- `deliverables/World_lubricants_catalog_seed.xlsx` — проверяемая выгрузка;
- `deliverables/Global_lubricants_catalog_registry.xlsx` — реестр 142 источников
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
python3 tools/ingest_ceypetco_lubricants.py
python3 tools/ingest_eaeu_conformity_lubricants.py
python3 tools/ingest_man_service_products.py
python3 tools/ingest_anp_lubricant_registry.py
python3 tools/ingest_indonesia_npt_registry.py
python3 tools/ingest_thailand_doeb_lubricant_registry.py
python3 tools/ingest_dla_qpd_lubricants.py
python3 tools/ingest_blue_angel_lubricants.py
python3 tools/ingest_austrian_ecolabel_uz14.py
python3 tools/ingest_korea_ecolabel_lubricants.py
python3 tools/ingest_green_choice_philippines.py
python3 tools/ingest_uae_moiat_conformity_products.py
python3 tools/ingest_epa_safer_choice_lubricants.py
python3 tools/ingest_kebs_smark_lubricants.py
python3 tools/ingest_east_africa_certified_lubricants.py
python3 tools/ingest_son_mancap_lubricants.py
python3 tools/ingest_rsb_smark_lubricants.py
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
python3 tools/ingest_fuchs_saudi_macedonia_catalogs.py
python3 tools/ingest_fuchs_czech_catalog.py
python3 tools/ingest_fuchs_mexico_catalog.py
python3 tools/ingest_fuchs_south_africa_catalog.py
python3 tools/ingest_fuchs_brazil_catalog.py
python3 tools/ingest_fuchs_norway_catalog.py
python3 tools/ingest_fuchs_hungary_catalog.py
python3 tools/ingest_fuchs_additional_europe_catalogs.py
python3 tools/ingest_fuchs_switzerland_catalog.py
python3 tools/ingest_fuchs_global_markets_catalogs.py
python3 tools/ingest_liqui_moly_2020_catalog.py
python3 tools/ingest_liqui_moly_current_catalog.py
python3 tools/ingest_epa_chemexpo_lubricants.py
python3 tools/ingest_psqca_engine_oil_licences.py
python3 tools/ingest_philippines_bps_brake_fluids.py
python3 tools/ingest_ghana_gsa_certified_lubricants.py
python3 tools/build_world_catalog_seed.py
python3 tools/verify_world_catalog.py
```

## Локальный запуск

```bash
python3 -m http.server 8080
```

Откройте <http://localhost:8080/>.
