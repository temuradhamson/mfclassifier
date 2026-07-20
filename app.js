const DATA = window.MF_CLASSIFIER_DATA;
const ANALYTICS = window.MF_ANALYTICS_DEMO;
const PAGE_SIZE = 30;
const CLASS_PAGE_SIZE = 24;
const IMPACT_PAGE_SIZE = 24;

const state = {
  view: "overview",
  productPage: 1,
  classPage: 1,
  reference: "standards",
  referenceRows: [],
  analyticsScenario: "engine",
  impactLotPage: 1,
  impactLotQuery: "",
  impactChartFilter: null,
  products: [],
  classes: [],
};

const $ = (id) => document.getElementById(id);
const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];
const has = (value) => value !== null && value !== undefined && String(value).trim() !== "";
const text = (value, fallback = "—") => has(value) ? String(value) : fallback;
const esc = (value) => text(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const norm = (value) => String(value || "").toLocaleLowerCase("ru").replaceAll("ё", "е").replace(/[^a-zа-я0-9]+/g, " ").trim();
const compact = (value) => norm(value).replaceAll(" ", "");
const unique = (values) => [...new Set(values.filter(has))].sort((a, b) => String(a).localeCompare(String(b), "ru", { numeric: true }));
const formatNumber = (value) => new Intl.NumberFormat("ru-RU").format(value || 0);
const formatDate = (value) => {
  if (!has(value)) return null;
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[3]}.${match[2]}.${match[1]}` : String(value);
};

function init() {
  if (!DATA?.products || !DATA?.classes) {
    document.body.innerHTML = '<main class="fatal-error"><h1>Данные не загружены</h1><p>Обновите страницу.</p></main>';
    return;
  }
  state.products = DATA.products;
  state.classes = DATA.classes;
  bindEvents();
  populateFilters();
  renderOverview();
  renderProducts();
  renderClasses();
  renderReferences();
  renderImpact();
  renderHeader();
  restoreTheme();
  navigate((location.hash || "#overview").slice(1), false);
}

function bindEvents() {
  $("mainNav").addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (button) navigate(button.dataset.view);
  });
  qsa("[data-go]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.go)));
  qsa("[data-reference]").forEach((button) => button.addEventListener("click", () => {
    state.reference = button.dataset.reference;
    navigate("references");
    renderReferences();
  }));

  let productTimer;
  $("productSearch").addEventListener("input", () => {
    clearTimeout(productTimer);
    productTimer = setTimeout(() => { state.productPage = 1; renderProducts(); }, 140);
  });
  ["productFamily", "productCategory", "productGrade", "productSystem", "productSpecification", "productBrand"].forEach((id) => $(id).addEventListener("change", () => {
    state.productPage = 1; updateProductCascade(); renderProducts();
  }));
  $("productLink").addEventListener("change", () => { state.productPage = 1; renderProducts(); });
  $("clearProductFilters").addEventListener("click", clearProductFilters);
  $("productTableBody").addEventListener("click", (event) => {
    const row = event.target.closest("[data-product-id]");
    if (row) openProduct(row.dataset.productId);
  });
  $("exportProducts").addEventListener("click", exportProducts);

  let classTimer;
  $("classSearch").addEventListener("input", () => {
    clearTimeout(classTimer);
    classTimer = setTimeout(() => { state.classPage = 1; renderClasses(); }, 140);
  });
  ["classCategory", "classKind"].forEach((id) => $(id).addEventListener("change", () => {
    state.classPage = 1; renderClasses();
  }));
  $("clearClassFilters").addEventListener("click", clearClassFilters);
  $("classGrid").addEventListener("click", (event) => {
    const card = event.target.closest("[data-class-id]");
    if (card) openClass(card.dataset.classId);
  });

  $("referenceTabs").addEventListener("click", (event) => {
    const button = event.target.closest("[data-reference]");
    if (!button) return;
    state.reference = button.dataset.reference;
    $("referenceSearch").value = "";
    renderReferences();
  });
  $("referenceSearch").addEventListener("input", renderReferences);
  $("referenceContent").addEventListener("click", (event) => {
    const item = event.target.closest("[data-reference-item]");
    if (item) openReference(item.dataset.referenceItem);
  });
  $("impactTabs").addEventListener("click", (event) => {
    const button = event.target.closest("[data-impact-scenario]");
    if (!button) return;
    state.analyticsScenario = button.dataset.impactScenario;
    state.impactLotPage = 1;
    state.impactLotQuery = "";
    state.impactChartFilter = null;
    $("impactLotSearch").value = "";
    renderImpact();
  });
  let impactTimer;
  $("impactLotSearch").addEventListener("input", () => {
    clearTimeout(impactTimer);
    impactTimer = setTimeout(() => {
      state.impactLotQuery = $("impactLotSearch").value;
      state.impactLotPage = 1;
      renderImpactLots();
    }, 120);
  });
  $("impactLots").addEventListener("click", (event) => {
    const row = event.target.closest("[data-impact-lot]");
    if (row) openImpactLot(row.dataset.impactLot);
  });
  $("impactView").addEventListener("click", (event) => {
    if (event.target.closest("[data-clear-impact-filter]")) {
      state.impactChartFilter = null;
      state.impactLotPage = 1;
      renderImpactLots();
      return;
    }
    const target = event.target.closest("[data-chart-filter]");
    if (!target) return;
    const kind = target.dataset.chartFilter;
    state.impactChartFilter = {
      kind,
      value: target.dataset.value || "",
      from: Number(target.dataset.from || 0),
      to: target.dataset.to ? Number(target.dataset.to) : null,
      phase: target.dataset.phase || "",
    };
    state.impactLotPage = 1;
    renderImpactLots();
    $("impactLots").closest(".impact-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("impactView").addEventListener("pointermove", (event) => {
    const target = event.target.closest("[data-tip]");
    if (!target) return hideChartTooltip();
    showChartTooltip(target.dataset.tip, event.clientX, event.clientY);
  });
  $("impactView").addEventListener("pointerleave", hideChartTooltip);

  $("matcherForm").addEventListener("submit", runMatcher);
  $("matchResults").addEventListener("click", (event) => {
    const card = event.target.closest("[data-class-id]");
    if (card) openClass(card.dataset.classId);
  });

  $("drawerClose").addEventListener("click", closeDrawer);
  $("drawerBackdrop").addEventListener("click", closeDrawer);
  $("drawerContent").addEventListener("click", (event) => {
    const product = event.target.closest("[data-linked-product]");
    if (product) openProduct(product.dataset.linkedProduct);
    const classLink = event.target.closest("[data-linked-class]");
    if (classLink) openClass(classLink.dataset.linkedClass);
  });

  $("themeToggle").addEventListener("click", toggleTheme);
  $("globalSearch").addEventListener("focus", openCommand);
  $("globalSearch").addEventListener("click", openCommand);
  $("commandInput").addEventListener("input", renderCommandResults);
  $("commandResults").addEventListener("click", handleCommandResult);
  $("commandPalette").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeCommand();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      event.preventDefault(); openCommand();
    }
    if (event.key === "Escape") { closeDrawer(); closeCommand(); }
  });
  window.addEventListener("hashchange", () => navigate((location.hash || "#overview").slice(1), false));
}

function renderHeader() {
  $("headerDataCount").textContent = `${formatNumber(DATA.metrics.products)} продуктов · ${formatNumber(DATA.metrics.classes)} классов`;
  $("navProducts").textContent = DATA.metrics.products;
  $("navClasses").textContent = DATA.metrics.classes;
  $("generatedAt").textContent = new Date(DATA.generated_at).toLocaleDateString("ru-RU");
}

function navigate(view, updateHash = true) {
  const valid = ["overview", "products", "classes", "references", "impact", "matcher"];
  state.view = valid.includes(view) ? view : "overview";
  qsa(".view").forEach((section) => section.classList.toggle("active", section.id === `${state.view}View`));
  qsa(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === state.view));
  if (updateHash && location.hash !== `#${state.view}`) history.pushState(null, "", `#${state.view}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function fillSelect(id, values, label = (value) => value) {
  const select = $(id);
  const first = select.options[0];
  select.innerHTML = "";
  select.appendChild(first);
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label(value);
    select.appendChild(option);
  });
}

function populateFilters() {
  updateProductCascade();
  fillSelect("classCategory", unique(DATA.classes.map((item) => item.category)));
  const categoryMap = new Map();
  DATA.classes.forEach((item) => categoryMap.set(item.category_code, item.category_code === "TF" ? "Технические жидкости" : item.category));
  fillSelect("matchCategory", [...categoryMap.keys()].sort(), (value) => `${value} · ${categoryMap.get(value)}`);
}

function renderOverview() {
  const metrics = [
    ["◉", "Продукты", DATA.metrics.products, `${DATA.metrics.brands} бренд`],
    ["◇", "Отраслевые классы", DATA.metrics.classes, `${DATA.metrics.class_links} связей с товарами`],
    ["≡", "Стандарты и ASTM", DATA.metrics.standards + DATA.metrics.astm_methods, "нормативных записей"],
    ["⌁", "CHILON LUBRICANTS", DATA.metrics.reference_products, "референсных позиций"],
  ];
  $("metricGrid").innerHTML = metrics.map(([icon, label, value, note]) => `
    <article class="metric-card"><div class="metric-top"><span>${esc(label)}</span><i>${icon}</i></div><strong>${formatNumber(value)}</strong><small>${esc(note)}</small></article>
  `).join("");

  const categories = Object.entries(DATA.facets.categories).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max = Math.max(...categories.map((item) => item[1]));
  $("categoryBars").innerHTML = categories.map(([label, value]) => `
    <div class="category-row"><span title="${esc(label)}">${esc(label)}</span><div class="bar-track"><div class="bar-fill" style="width:${value / max * 100}%"></div></div><b>${value}</b></div>
  `).join("");

  const linked = DATA.metrics.class_links;
  const unlinked = DATA.metrics.products - linked;
  const coverage = Math.round(linked / DATA.metrics.products * 100);
  $("coverageGauge").style.setProperty("--coverage", coverage);
  $("coverageGauge").innerHTML = `<div class="coverage-value"><strong>${coverage}%</strong><span>имеют связь</span></div>`;
  $("coverageLegend").innerHTML = `
    <div class="legend-row"><span>Предложен отраслевой класс</span><b>${linked}</b></div>
    <div class="legend-row"><span>Требуют экспертной разметки</span><b>${unlinked}</b></div>
    <div class="legend-row"><span>Конфликты источника</span><b>${DATA.quality.anomalies.length}</b></div>`;
  $("sourceStrip").innerHTML = DATA.sources.map((item) => `<div class="source-chip" title="${esc(item.title)}"><b>${esc(item.title)}</b><span>${esc(item.type)} · ${item.records || item.pages || "—"}</span></div>`).join("");
}

function rub(value) { return `${formatNumber(Math.round(value || 0))} сум`; }
function compactRub(value) { return `${formatNumber(Math.round(value || 0))}`; }

function renderImpact() {
  if (!ANALYTICS?.scenarios?.length) {
    $("impactComparison").innerHTML = '<div class="empty-state">Демонстрационная выборка не загружена</div>';
    return;
  }
  $("impactMetrics").innerHTML = [
    [formatNumber(ANALYTICS.methodology.production_lots_at_build), "лота в production ANIQLIK"],
    [formatNumber(ANALYTICS.metrics.sample_lots), "реальных лотов в расширенной выборке"],
    [formatNumber(ANALYTICS.metrics.professional_segments), "профессиональных ценовых сегментов"],
    [formatNumber(ANALYTICS.metrics.detailed_lots), "лотов с раскрываемой карточкой деталей"],
  ].map(([value, label]) => `<div><strong>${value}</strong><span>${esc(label)}</span></div>`).join("");
  $("impactTabs").innerHTML = ANALYTICS.scenarios.map((item) => `<button class="${item.id === state.analyticsScenario ? "active" : ""}" data-impact-scenario="${esc(item.id)}">${esc(item.title)}<em>${item.before.lots}</em></button>`).join("");
  const scenario = ANALYTICS.scenarios.find((item) => item.id === state.analyticsScenario) || ANALYTICS.scenarios[0];
  const spread = scenario.after.max_segment_avg / scenario.after.min_segment_avg;
  $("impactComparison").innerHTML = `
    <article class="before-card"><div class="compare-top"><span>ДО КЛАССИФИКАТОРА</span><b>Старшая группа</b></div><h2>${esc(scenario.before.group)}</h2><div class="coarse-price"><strong>${rub(scenario.before.avg_price_per_kg)}</strong><span>единая средняя цена / кг</span></div><div class="dimension-list">${scenario.before.available_dimensions.map((value) => `<span>${esc(value)}</span>`).join("")}</div><p>Разные вязкости и эксплуатационные классы смешаны в одном показателе.</p></article>
    <div class="compare-arrow"><span>→</span><b>классификатор</b></div>
    <article class="after-card"><div class="compare-top"><span>ПОСЛЕ КЛАССИФИКАТОРА</span><b>${esc(scenario.criterion)}</b></div><h2>${scenario.after.segment_count} отдельных сегментов</h2><div class="price-range"><div><small>от</small><strong>${rub(scenario.after.min_segment_avg)}</strong></div><i>→</i><div><small>до</small><strong>${rub(scenario.after.max_segment_avg)}</strong></div></div><div class="impact-spread"><strong>${spread.toFixed(1)}×</strong><span>разница средних цен между конкретными продуктами</span></div><div class="dimension-list after">${scenario.after.available_dimensions.map((value) => `<span>${esc(value)}</span>`).join("")}</div></article>`;
  $("impactCriterion").textContent = scenario.criterion;
  const maxPrice = Math.max(...scenario.after.segments.map((item) => item.avg_price_per_kg));
  $("impactSegments").innerHTML = `<div class="segment-list">${scenario.after.segments.map((item) => {
    const delta = item.difference_from_coarse_pct;
    const tip = `${item.key}\n${item.lots} лотов · средняя ${rub(item.avg_price_per_kg)}\nОтклонение от общей средней ${delta > 0 ? "+" : ""}${delta}%\nНажмите, чтобы показать эти лоты`;
    return `<div class="segment-row interactive-chart-item" data-chart-filter="segment" data-value="${esc(item.key)}" data-tip="${esc(tip)}"><div><b>${esc(item.key)}</b><small>${item.lots} ${item.lots === 1 ? "лот · малая выборка" : "лота"}</small></div><div class="segment-track"><i style="width:${Math.max(4, item.avg_price_per_kg / maxPrice * 100)}%"></i><u style="left:${scenario.before.avg_price_per_kg / maxPrice * 100}%" title="Средняя до классификатора"></u></div><strong>${rub(item.avg_price_per_kg)}</strong><span class="delta ${delta > 0 ? "up" : "down"}">${delta > 0 ? "+" : ""}${delta}%</span></div>`;
  }).join("")}</div><div class="segment-legend"><span><i></i>Средняя конкретного продукта</span><span><u></u>Средняя старшей группы: ${rub(scenario.before.avg_price_per_kg)}</span></div>`;
  renderImpactCharts(scenario);
  renderImpactLots();
  $("impactMethod").innerHTML = `<strong>Методика и честная маркировка</strong><p>${esc(ANALYTICS.methodology.selection)} ${esc(ANALYTICS.methodology.disclosure)}</p><span>Источник: ${esc(ANALYTICS.methodology.source)} · seed ${ANALYTICS.methodology.random_seed} · контрагенты не публикуются</span>`;
}

function renderImpactCharts(scenario) {
  const histogram = scenario.price_histogram || [];
  const maxBin = Math.max(1, ...histogram.map((item) => item.count));
  $("impactHistogram").innerHTML = `<div class="histogram">${histogram.map((item) => {
    const tip = `${item.count} лотов\n${rub(item.from)} — ${rub(item.to)}\n${Math.round(item.count / scenario.before.lots * 100)}% выборки · нажмите для фильтра`;
    return `<div class="histogram-bin interactive-chart-item" data-chart-filter="price" data-from="${item.from}" data-to="${item.to}" data-tip="${esc(tip)}"><b>${item.count}</b><i style="height:${Math.max(5, item.count / maxBin * 100)}%"></i><span>${compactRub(item.from)}</span></div>`;
  }).join("")}</div><div class="chart-note"><span>Минимум ${rub(histogram[0]?.from)}</span><b>Общая средняя ${rub(scenario.before.avg_price_per_kg)}</b><span>Максимум ${rub(histogram.at(-1)?.to)}</span></div>`;

  const palette = ["#3d73e6", "#38a8b8", "#6f64d9", "#e7a23c", "#e26464", "#58a46b", "#a366c2"];
  const top = scenario.after.segments.slice().sort((a, b) => b.lots - a.lots).slice(0, 6);
  const used = top.reduce((sum, item) => sum + item.lots, 0);
  const composition = [...top, ...(used < scenario.before.lots ? [{ key: "Другие сегменты", lots: scenario.before.lots - used }] : [])];
  let offset = 0;
  const stops = composition.map((item, index) => {
    const start = offset;
    offset += item.lots / scenario.before.lots * 100;
    return `${palette[index % palette.length]} ${start}% ${offset}%`;
  }).join(",");
  $("impactComposition").innerHTML = `<div class="composition-chart"><div class="composition-donut" style="background:conic-gradient(${stops})" data-tip="${scenario.after.segment_count} профессиональных сегментов вместо одной старшей группы"><div><strong>${scenario.after.segment_count}</strong><span>сегментов</span></div></div><div class="composition-legend">${composition.map((item, index) => {
    const clickable = item.key !== "Другие сегменты";
    const tip = `${item.key}\n${item.lots} лотов · ${Math.round(item.lots / scenario.before.lots * 100)}% выборки${clickable ? "\nНажмите для фильтра" : ""}`;
    return `<div class="${clickable ? "interactive-chart-item" : ""}" ${clickable ? `data-chart-filter="segment" data-value="${esc(item.key)}"` : ""} data-tip="${esc(tip)}"><i style="background:${palette[index % palette.length]}"></i><span>${esc(item.key)}</span><b>${Math.round(item.lots / scenario.before.lots * 100)}%</b></div>`;
  }).join("")}</div></div>`;

  const trend = scenario.monthly_prices || [];
  if (trend.length < 2) {
    $("impactTrend").innerHTML = '<div class="chart-empty">Недостаточно месяцев для динамики</div>';
  } else {
    const values = trend.flatMap((item) => [item.avg, item.median]);
    const min = Math.min(...values) * .94;
    const max = Math.max(...values) * 1.06;
    const x = (index) => 34 + index * (712 / Math.max(1, trend.length - 1));
    const y = (value) => 18 + (max - value) / Math.max(1, max - min) * 150;
    const points = (field) => trend.map((item, index) => `${x(index)},${y(item[field])}`).join(" ");
    $("impactTrend").innerHTML = `<svg class="trend-chart" viewBox="0 0 780 215" role="img" aria-label="Динамика средней и медианной цены"><line x1="34" y1="168" x2="746" y2="168" class="axis-line"></line><polyline points="${points("avg")}" class="trend-line avg"></polyline><polyline points="${points("median")}" class="trend-line median"></polyline>${trend.map((item, index) => {
      const tip = `${item.month}\n${item.lots} лотов\nСредняя ${rub(item.avg)} · медиана ${rub(item.median)}\nНажмите для фильтра по месяцу`;
      return `<circle cx="${x(index)}" cy="${y(item.avg)}" r="5" class="trend-dot avg interactive-chart-item" data-chart-filter="month" data-value="${esc(item.month)}" data-tip="${esc(tip)}"></circle><circle cx="${x(index)}" cy="${y(item.median)}" r="4" class="trend-dot median interactive-chart-item" data-chart-filter="month" data-value="${esc(item.month)}" data-tip="${esc(tip)}"></circle><text x="${x(index)}" y="194" text-anchor="middle">${esc(item.month.slice(2))}</text>`;
    }).join("")}</svg><div class="trend-legend"><span><i class="avg"></i>Средняя цена</span><span><i class="median"></i>Медианная цена</span></div>`;
  }

  const ranges = scenario.after.segments.slice().sort((a, b) => b.lots - a.lots).slice(0, 8);
  const rangeMin = Math.min(...ranges.map((item) => item.min_price_per_kg));
  const rangeMax = Math.max(...ranges.map((item) => item.max_price_per_kg));
  const pos = (value) => (value - rangeMin) / Math.max(1, rangeMax - rangeMin) * 100;
  $("impactRanges").innerHTML = `<div class="range-chart">${ranges.map((item) => {
    const tip = `${item.key}\nМинимум ${rub(item.min_price_per_kg)}\nМедиана ${rub(item.median_price_per_kg)}\nМаксимум ${rub(item.max_price_per_kg)}\nНажмите для фильтра`;
    return `<div class="range-row interactive-chart-item" data-chart-filter="segment" data-value="${esc(item.key)}" data-tip="${esc(tip)}"><div><b>${esc(item.key)}</b><small>${item.lots} лотов</small></div><div class="range-track"><i style="left:${pos(item.min_price_per_kg)}%;width:${Math.max(1.2, pos(item.max_price_per_kg) - pos(item.min_price_per_kg))}%"></i><u style="left:${pos(item.median_price_per_kg)}%"></u></div><span>${rub(item.min_price_per_kg)} — ${rub(item.max_price_per_kg)}</span></div>`;
  }).join("")}</div>`;

  renderImpactAccuracy(scenario);
}

function renderImpactAccuracy(scenario) {
  const accuracy = scenario.benchmark_accuracy;
  const maxError = Math.max(1, accuracy.before_error_pct, accuracy.after_error_pct);
  $("impactAccuracy").innerHTML = `<div class="accuracy-result"><strong>−${accuracy.error_reduction_pct}%</strong><span>снижение средней ошибки ценового ориентира</span></div><div class="accuracy-bars">${[
    ["До · одна медиана группы", accuracy.before_error_pct, "before"],
    ["После · медиана своего класса", accuracy.after_error_pct, "after"],
  ].map(([label, value, phase]) => `<div data-tip="${esc(`${label}\nСреднее абсолютное отклонение ${value}%`)}"><span>${esc(label)}</span><div><i class="${phase}" style="width:${value / maxError * 100}%"></i></div><b>${value}%</b></div>`).join("")}</div><div class="accuracy-zone"><div><small>Лоты в коридоре ±20% · до</small><strong>${accuracy.before_within_20_pct}%</strong></div><i>→</i><div><small>После классификации</small><strong>${accuracy.after_within_20_pct}%</strong></div></div>`;

  const maxBand = Math.max(1, ...scenario.deviation_bands.flatMap((item) => [item.before, item.after]));
  $("impactDeviation").innerHTML = `<div class="deviation-legend"><span><i class="before"></i>До классификатора</span><span><i class="after"></i>После</span></div><div class="deviation-chart">${scenario.deviation_bands.map((item) => `<div class="deviation-column"><div class="deviation-bars"><i class="before interactive-chart-item" style="height:${Math.max(4, item.before / maxBand * 100)}%" data-chart-filter="deviation" data-phase="before" data-from="${item.from}" ${item.to ? `data-to="${item.to}"` : ""} data-tip="${esc(`До классификатора\n${item.label} от единого ориентира\n${item.before} лотов · нажмите для фильтра`)}"><b>${item.before}</b></i><i class="after interactive-chart-item" style="height:${Math.max(4, item.after / maxBand * 100)}%" data-chart-filter="deviation" data-phase="after" data-from="${item.from}" ${item.to ? `data-to="${item.to}"` : ""} data-tip="${esc(`После классификатора\n${item.label} от ориентира своего класса\n${item.after} лотов · нажмите для фильтра`)}"><b>${item.after}</b></i></div><span>${esc(item.label)}</span></div>`).join("")}</div>`;
}

function currentImpactScenario() {
  return ANALYTICS.scenarios.find((item) => item.id === state.analyticsScenario) || ANALYTICS.scenarios[0];
}

function impactFilterLabel(filter) {
  if (!filter) return "";
  if (filter.kind === "segment") return `Сегмент: ${filter.value}`;
  if (filter.kind === "month") return `Месяц: ${filter.value}`;
  if (filter.kind === "price") return `Цена: ${rub(filter.from)} — ${rub(filter.to)}`;
  if (filter.kind === "deviation") return `${filter.phase === "before" ? "До" : "После"}: отклонение ${filter.from}%${filter.to ? `–${filter.to}%` : "+"}`;
  return "Фильтр графика";
}

function matchesImpactChartFilter(item, filter) {
  if (!filter) return true;
  if (filter.kind === "segment") return item.professional_key === filter.value;
  if (filter.kind === "month") return String(item.date || "").startsWith(filter.value);
  if (filter.kind === "price") return item.price_per_kg >= filter.from && item.price_per_kg <= filter.to;
  if (filter.kind === "deviation") {
    const value = item[filter.phase === "before" ? "before_deviation_pct" : "after_deviation_pct"];
    return value >= filter.from && (filter.to === null || value < filter.to);
  }
  return true;
}

function renderImpactLots() {
  const scenario = currentImpactScenario();
  if (!scenario) return;
  const query = norm(state.impactLotQuery);
  const lots = scenario.lots.filter((item) => matchesImpactChartFilter(item, state.impactChartFilter) && (!query || norm([item.lot_number, item.raw_product_name, item.raw_brand_text, item.professional_key, item.manufacturer].join(" ")).includes(query)));
  const pages = Math.max(1, Math.ceil(lots.length / IMPACT_PAGE_SIZE));
  state.impactLotPage = Math.min(state.impactLotPage, pages);
  const slice = lots.slice((state.impactLotPage - 1) * IMPACT_PAGE_SIZE, state.impactLotPage * IMPACT_PAGE_SIZE);
  $("impactLotCount").textContent = `${formatNumber(lots.length)} из ${formatNumber(scenario.lots.length)} лотов`;
  $("impactActiveFilter").innerHTML = state.impactChartFilter ? `<button type="button" data-clear-impact-filter>${esc(impactFilterLabel(state.impactChartFilter))}<b>×</b></button>` : "";
  $("impactLots").innerHTML = slice.length ? slice.map((item) => `<tr data-impact-lot="${esc(item.source_row_id)}"><td><b>${esc(item.lot_number)}</b><small>${esc(formatDate(item.date))}${item.lot_id ? ` · ID ${esc(item.lot_id)}` : ""}</small></td><td><span>${esc(item.raw_product_name)}</span><small>${esc(item.raw_brand_text)}</small></td><td><span class="enriched-key">${esc(item.professional_key)}</span><small class="demo-origin">вычислено для демонстрации</small></td><td><b>${rub(item.price_per_kg)}</b><small>${item.quantity ? `${formatNumber(item.quantity)} ${esc(item.measure)}` : ""}</small></td></tr>`).join("") : '<tr><td colspan="4" class="empty-state">Лоты не найдены</td></tr>';
  renderPagination("impactLotPagination", state.impactLotPage, pages, (page) => { state.impactLotPage = page; renderImpactLots(); });
}

function openImpactLot(sourceRowId) {
  const lot = currentImpactScenario()?.lots.find((item) => String(item.source_row_id) === String(sourceRowId));
  if (!lot) return;
  const sourceRows = [
    ["Номер лота", lot.lot_number], ["ID лота ANIQLIK", lot.lot_id], ["Дата начала", formatDate(lot.date)],
    ["Исходное наименование", lot.raw_product_name], ["Бренд / марка", lot.raw_brand_text],
    ["Количество", lot.quantity ? `${formatNumber(lot.quantity)} ${lot.measure}` : null],
    ["Эквивалент массы", lot.quantity_kg ? `${formatNumber(lot.quantity_kg)} кг` : null],
    ["Стартовая цена за единицу", lot.start_price_unit ? rub(lot.start_price_unit) : null],
    ["Итоговая цена за единицу", lot.final_price_unit ? rub(lot.final_price_unit) : null],
    ["Цена в пересчёте на кг", rub(lot.price_per_kg)], ["Статус", lot.status],
    ["Производитель", lot.manufacturer], ["Страна", lot.country],
  ].filter(([, value]) => has(value));
  const inferredRows = Object.entries(lot.enriched_fields || {});
  openDrawer(`<div class="drawer-hero impact-drawer-hero"><span class="eyebrow">ANIQLIK · реальный лот</span><h2>${esc(lot.lot_number)}</h2><p>${esc(lot.raw_brand_text || lot.raw_product_name)}</p><div class="drawer-chips"><span>${esc(lot.professional_key)}</span><span>DEMO-ОБОГАЩЕНИЕ</span></div></div><div class="drawer-body"><div class="drawer-note"><strong>Разделение источников</strong><br>Коммерческие сведения взяты из ANIQLIK. Профессиональные поля ниже вычислены демонстрационно и не записаны в исходную БД.</div>${detailSection("Исходные данные лота", sourceRows)}${detailSection("Профессиональное обогащение", inferredRows)}${detailSection("Влияние классификатора", [["Отклонение от общей медианы (до)", `${lot.before_deviation_pct}%`], ["Отклонение от медианы своего класса (после)", `${lot.after_deviation_pct}%`]])}${lot.technical_specs ? `<section class="drawer-section"><h3>Технические характеристики</h3><p class="lot-long-text">${esc(lot.technical_specs)}</p></section>` : ""}${lot.functional_characteristics ? `<section class="drawer-section"><h3>Функциональные характеристики</h3><p class="lot-long-text">${esc(lot.functional_characteristics)}</p></section>` : ""}</div>`);
}

function showChartTooltip(message, x, y) {
  const tooltip = $("chartTooltip");
  tooltip.textContent = message;
  tooltip.classList.add("show");
  const left = Math.min(window.innerWidth - 240, x + 14);
  const top = Math.min(window.innerHeight - 120, y + 14);
  tooltip.style.left = `${Math.max(8, left)}px`;
  tooltip.style.top = `${Math.max(8, top)}px`;
}

function hideChartTooltip() {
  $("chartTooltip").classList.remove("show");
}

function productSearchText(item) {
  return norm([item.name, item.brand, item.category, item.viscosity, item.din_gost_class,
    item.sae_class, item.api_class, item.gost_name, item.coolant_class, item.grease_class,
    item.certificate_number, item.technical_document, item.tnved_code, item.ikpu, item.enkt, item.skp].join(" "));
}

function cleanStandard(value, prefix) {
  return String(value || "").trim().replace(new RegExp(`^${prefix}\\s*`, "i"), "").trim();
}

function normalizeSae(value) {
  const grade = cleanStandard(value, "SAE[-\\s]*").toUpperCase().replaceAll(" ", "").replace(/^-/, "");
  return /^\d{1,2}W\d{2}$/.test(grade) ? grade.replace("W", "W-") : grade;
}

function normalizeIsoVg(value) {
  return String(value || "").trim().replace(/^(?:ISO\s*)?VG\s*/i, "").trim();
}

function professionalProfile(item) {
  const category = norm(item.category);
  if (category.includes("моторн")) return { kind: "engine", gradeLabel: "Вязкость SAE", grade: normalizeSae(item.sae_class) };
  if (category.includes("трансмиссион")) return { kind: "gear", gradeLabel: "Вязкость SAE", grade: normalizeSae(item.sae_class) };
  if (category.includes("смазк")) return { kind: "grease", gradeLabel: "Класс DIN 51502", grade: cleanStandard(item.grease_class, "Смазка пластичная") };
  if (item.category_code === "TF" || category.includes("охлаждающ")) return { kind: "coolant", gradeLabel: "Класс охлаждающей жидкости", grade: item.coolant_class };
  return { kind: "industrial", gradeLabel: "Вязкость ISO VG", grade: normalizeIsoVg(item.viscosity) };
}

function aceaValue(item) {
  const match = String(item.technical_document || "").match(/ACEA\s+([^,;]+)/i);
  return match ? match[1].trim() : "";
}

function apiValue(item) {
  const documented = String(item.technical_document || "").match(/API\s+(.+?)(?=,\s*ACEA|;|$)/i);
  return cleanStandard(documented?.[1] || item.api_class, "API");
}

function standardValues(item) {
  const profile = professionalProfile(item);
  const values = [];
  const add = (system, value) => { if (has(value)) values.push({ system, value: String(value).trim() }); };
  if (profile.kind === "engine") {
    add("API", apiValue(item)); add("ACEA", aceaValue(item)); add("ГОСТ", item.gost_name);
  } else if (profile.kind === "gear") {
    add("API GL", apiValue(item)); add("ГОСТ", item.gost_name);
  } else if (profile.kind === "coolant") {
    add("ГОСТ / ТУ", /ГОСТ|GOST|ТУ|TS\s/i.test(item.technical_document || "") ? item.technical_document : "");
  } else if (profile.kind === "grease") {
    add("DIN 51502", item.grease_class); add("ГОСТ", item.gost_name);
  } else {
    add("DIN / ISO", item.din_gost_class); add("ГОСТ", item.gost_name);
  }
  return values;
}

function selectValue(id) { return $(id).value; }
function setCascadeOptions(id, values, placeholder, label = (value) => value) {
  const select = $(id);
  const current = select.value;
  select.innerHTML = `<option value="">${esc(placeholder)}</option>` + values.map((value) => `<option value="${esc(value)}">${esc(label(value))}</option>`).join("");
  if (values.includes(current)) select.value = current;
}

function matchesProfessional(item, filters, through = "brand") {
  const order = ["family", "category", "grade", "system", "specification", "brand"];
  const limit = order.indexOf(through);
  const profile = professionalProfile(item);
  if (limit >= 0 && filters.family && item.family !== filters.family) return false;
  if (limit >= 1 && filters.category && item.category !== filters.category) return false;
  if (limit >= 2 && filters.grade && profile.grade !== filters.grade) return false;
  if (limit >= 3 && filters.system && !standardValues(item).some((entry) => entry.system === filters.system)) return false;
  if (limit >= 4 && filters.specification && !standardValues(item).some((entry) => entry.system === filters.system && entry.value === filters.specification)) return false;
  if (limit >= 5 && filters.brand && item.brand !== filters.brand) return false;
  return true;
}

function productFilters() {
  return {
    family: selectValue("productFamily"), category: selectValue("productCategory"), grade: selectValue("productGrade"),
    system: selectValue("productSystem"), specification: selectValue("productSpecification"), brand: selectValue("productBrand"),
  };
}

function updateProductCascade() {
  let filters = productFilters();
  setCascadeOptions("productFamily", unique(DATA.products.map((item) => item.family)), "Все семейства", (value) => value === "Масла" ? "Смазочные материалы" : value);
  filters = productFilters();
  let base = DATA.products.filter((item) => matchesProfessional(item, filters, "family"));
  setCascadeOptions("productCategory", unique(base.map((item) => item.category)), "Все категории");
  filters = productFilters();
  base = DATA.products.filter((item) => matchesProfessional(item, filters, "category"));
  const profiles = base.map(professionalProfile);
  const labels = unique(profiles.map((profile) => profile.gradeLabel));
  $("productGradeLabel").textContent = labels.length === 1 ? labels[0] : "Вязкость / класс";
  setCascadeOptions("productGrade", unique(profiles.map((profile) => profile.grade)), "Все значения");
  filters = productFilters();
  base = DATA.products.filter((item) => matchesProfessional(item, filters, "grade"));
  const systemOrder = ["API", "API GL", "ACEA", "DIN / ISO", "DIN 51502", "ГОСТ", "ГОСТ / ТУ"];
  const systems = unique(base.flatMap((item) => standardValues(item).map((entry) => entry.system))).sort((a, b) => systemOrder.indexOf(a) - systemOrder.indexOf(b));
  setCascadeOptions("productSystem", systems, "Все системы");
  filters = productFilters();
  base = DATA.products.filter((item) => matchesProfessional(item, filters, "system"));
  setCascadeOptions("productSpecification", unique(base.flatMap((item) => standardValues(item).filter((entry) => !filters.system || entry.system === filters.system).map((entry) => entry.value))), "Все спецификации");
  filters = productFilters();
  base = DATA.products.filter((item) => matchesProfessional(item, filters, "specification"));
  setCascadeOptions("productBrand", unique(base.map((item) => item.brand)), "Все бренды");
  filters = productFilters();
  $("productGrade").disabled = !filters.category;
  $("productSystem").disabled = !filters.category;
  $("productSpecification").disabled = !filters.system;
  $("selectorHint").textContent = filters.category
    ? `${$("productGradeLabel").textContent} → функциональный стандарт → спецификация → доступный бренд.`
    : "Выберите категорию — следующие списки перестроятся под её профессиональную классификацию.";
}

function filteredProducts() {
  const query = norm($("productSearch").value).split(/\s+/).filter(Boolean);
  const filters = productFilters();
  const link = $("productLink").value;
  return DATA.products.filter((item) => {
    if (!matchesProfessional(item, filters)) return false;
    if (link === "linked" && !item.class_match) return false;
    if (link === "unlinked" && item.class_match) return false;
    const haystack = productSearchText(item);
    return query.every((token) => haystack.includes(token));
  });
}

function productSpecs(item) {
  return unique([
    item.viscosity ? `ISO VG ${normalizeIsoVg(item.viscosity)}` : null,
    item.sae_class ? `SAE ${normalizeSae(item.sae_class)}` : null,
    item.api_class ? `API ${apiValue(item)}` : null,
    item.din_gost_class, item.coolant_class, item.grease_class,
  ]).slice(0, 4);
}

function certificateLabel(status) {
  return { valid: "Действует", expired: "Истёк", no_expiry: "Без срока", missing: "Не указан" }[status] || status;
}

function renderProducts() {
  const products = filteredProducts();
  const pages = Math.max(1, Math.ceil(products.length / PAGE_SIZE));
  state.productPage = Math.min(state.productPage, pages);
  const slice = products.slice((state.productPage - 1) * PAGE_SIZE, state.productPage * PAGE_SIZE);
  $("productResultCount").textContent = `${formatNumber(products.length)} позиций`;
  $("productTableBody").innerHTML = slice.length ? slice.map((item) => `
    <tr data-product-id="${item.id}">
      <td class="product-name"><b>${esc(item.name)}</b><span>${esc(item.brand)}</span></td>
      <td class="muted-cell">${esc(item.category)}</td>
      <td><div class="spec-stack">${productSpecs(item).map((value) => `<span class="spec-pill">${esc(value)}</span>`).join("") || "—"}</div></td>
      <td class="code-lines">${item.tnved_code ? `ТН ВЭД ${esc(item.tnved_code)}` : "—"}${item.ikpu ? `<br>ИКПУ ${esc(item.ikpu)}` : ""}</td>
      <td><span class="status-pill ${esc(item.certificate_status)}">${certificateLabel(item.certificate_status)}</span>${item.certificate_expires_at ? `<div class="code-lines">до ${formatDate(item.certificate_expires_at)}</div>` : ""}</td>
      <td>${item.class_match ? `<div class="class-link"><span class="class-code">${esc(item.class_match.class_id)}</span><small>${item.class_match.confidence}% · предложен</small></div>` : '<div class="class-link empty"><span>—</span><small>нужна разметка</small></div>'}</td>
    </tr>`).join("") : '<tr><td colspan="6" class="empty-state">По заданным фильтрам ничего не найдено</td></tr>';
  renderPagination("productPagination", state.productPage, pages, (page) => { state.productPage = page; renderProducts(); });
}

function clearProductFilters() {
  ["productSearch", "productFamily", "productCategory", "productGrade", "productSystem", "productSpecification", "productBrand", "productLink"].forEach((id) => $(id).value = "");
  state.productPage = 1; updateProductCascade(); renderProducts();
}

function classSearchText(item) {
  return norm([item.id, item.category, item.product_form, item.base_composition, item.base_oil,
    item.thickener, item.nlgi, item.iso_vg, item.sae_engine, item.sae_gear, item.api,
    item.api_gl, item.acea, item.gost, item.astm_product, (item.astm_tests || []).join(" "),
    item.application, item.examples, item.analogues, (item.standards || []).join(" ")].join(" "));
}

function filteredClasses() {
  const tokens = norm($("classSearch").value).split(/\s+/).filter(Boolean);
  const category = $("classCategory").value;
  const kind = $("classKind").value;
  return DATA.classes.filter((item) => {
    if (category && item.category !== category) return false;
    if (kind && item.kind !== kind) return false;
    const haystack = classSearchText(item);
    return tokens.every((token) => haystack.includes(token));
  });
}

function classSpecs(item) {
  return unique([
    item.iso_vg ? `ISO VG ${item.iso_vg}` : null,
    item.sae_engine ? `SAE ${item.sae_engine}` : null,
    item.sae_gear ? `SAE ${item.sae_gear}` : null,
    item.api, item.api_gl, item.acea, item.gost, item.nlgi ? `NLGI ${item.nlgi}` : null,
    ...(item.standards || []),
  ]).slice(0, 5);
}

function renderClasses() {
  const classes = filteredClasses();
  const pages = Math.max(1, Math.ceil(classes.length / CLASS_PAGE_SIZE));
  state.classPage = Math.min(state.classPage, pages);
  const slice = classes.slice((state.classPage - 1) * CLASS_PAGE_SIZE, state.classPage * CLASS_PAGE_SIZE);
  $("classResultCount").textContent = `${formatNumber(classes.length)} классов`;
  $("classGrid").innerHTML = slice.length ? slice.map((item) => `
    <article class="class-card" data-class-id="${esc(item.id)}">
      <div class="class-card-top"><span class="class-code">${esc(item.id)}</span><span class="kind-badge">${item.kind === "technical_fluid" ? "ТЕХЖИДКОСТЬ" : esc(item.category_code)}</span></div>
      <h3>${esc(item.category)}${item.product_form ? ` · ${esc(item.product_form)}` : ""}</h3>
      <p>${esc(item.application || item.notes || item.astm_notes || "Технический класс смазочного материала")}</p>
      <div class="class-card-specs">${classSpecs(item).map((value) => `<span class="spec-pill">${esc(value)}</span>`).join("")}</div>
      ${has(item.temp_min) || has(item.temp_max) ? `<div class="class-card-temp">Рабочий диапазон: ${esc(item.temp_min)}…${esc(item.temp_max)} °C</div>` : ""}
    </article>`).join("") : '<div class="empty-state">Классы не найдены</div>';
  renderPagination("classPagination", state.classPage, pages, (page) => { state.classPage = page; renderClasses(); });
}

function clearClassFilters() {
  ["classSearch", "classCategory", "classKind"].forEach((id) => $(id).value = "");
  state.classPage = 1; renderClasses();
}

function renderPagination(id, current, pages, onChange) {
  const container = $(id);
  if (pages <= 1) { container.innerHTML = ""; return; }
  const visible = unique([1, pages, current - 1, current, current + 1].filter((page) => page >= 1 && page <= pages));
  let previous = 0;
  const parts = [`<button ${current === 1 ? "disabled" : ""} data-page="${current - 1}">←</button>`];
  visible.forEach((page) => {
    if (page - previous > 1) parts.push("<span>…</span>");
    parts.push(`<button class="${page === current ? "active" : ""}" data-page="${page}">${page}</button>`);
    previous = page;
  });
  parts.push(`<button ${current === pages ? "disabled" : ""} data-page="${current + 1}">→</button>`);
  container.innerHTML = parts.join("");
  qsa("button[data-page]", container).forEach((button) => button.addEventListener("click", () => {
    if (!button.disabled) onChange(Number(button.dataset.page));
  }));
}

function referenceDataset() {
  const refs = DATA.references;
  return {
    standards: refs.standards,
    astm: refs.astm_methods,
    industries: refs.industries,
    temperatures: refs.temperature_zones,
    chilon: refs.chilon_lubricants,
    sources: DATA.sources,
  }[state.reference] || refs.standards;
}

function referenceText(item) {
  return norm(Object.values(item).join(" "));
}

function renderReferences() {
  qsa("[data-reference]", $("referenceTabs")).forEach((button) => button.classList.toggle("active", button.dataset.reference === state.reference));
  const tokens = norm($("referenceSearch").value).split(/\s+/).filter(Boolean);
  const rows = referenceDataset().filter((item) => tokens.every((token) => referenceText(item).includes(token)));
  state.referenceRows = rows;
  const container = $("referenceContent");
  if (state.reference === "temperatures") {
    container.innerHTML = `<div class="temperature-scale">${rows.map((item) => {
      const min = Number(item["От °C"]), max = Number(item["До °C"]);
      const left = temperaturePosition(min), right = temperaturePosition(max);
      return `<div class="temperature-row"><div><b>${esc(item["Зона"])}</b><small>${esc(item["Код"])}</small></div><div class="temperature-range"><span style="--range-left:${left}%;--range-right:${100 - right}%"></span><i class="range-start" style="left:${left}%"></i><i class="range-end" style="left:${right}%"></i></div><small>${min}…${max} °C</small></div>`;
    }).join("")}</div>`;
    return;
  }
  if (state.reference === "sources") {
    container.innerHTML = `<div class="source-list">${rows.map((item) => `<article class="source-row"><span class="source-type">${esc(item.type)}</span><div><b>${esc(item.title)}</b><p>${esc(item.role)}</p></div><small>${esc(item.edition || `${item.records || item.pages || "—"} записей`)}</small></article>`).join("")}</div>`;
    return;
  }
  container.innerHTML = `<div class="reference-grid">${rows.map((item, index) => referenceCard(item, index)).join("")}</div>`;
}

function temperaturePosition(value) {
  const number = Math.max(-273, Math.min(2000, Number(value)));
  // 300…2000 °C is shown as an explicitly broken extension so that the
  // practically important −273…300 °C ranges remain readable.
  return number <= 300 ? (number + 273) / 573 * 82 : 82 + (number - 300) / 1700 * 18;
}

function referenceCard(item, index) {
  if (state.reference === "standards") return `<article class="reference-card" data-reference-item="${index}"><div class="ref-top"><span>${esc(item["Организация"])}</span><span>${esc(item["Регион"])}</span></div><h3>${esc(item["Стандарт"])}</h3><p>${esc(item["Назначение"])}</p><dl><dt>Примечание</dt><dd>${esc(item["Примечание"])}</dd></dl></article>`;
  if (state.reference === "astm") return `<article class="reference-card" data-reference-item="${index}"><div class="ref-top"><span>${esc(item["Категория"])}</span><span>ASTM</span></div><h3>${esc(item["ASTM_Code"])}</h3><p>${esc(item["Название"])}</p><dl><dt>Применение</dt><dd>${esc(item["Применение"])}</dd><dt>Параметры</dt><dd>${esc(item["Ключевые_параметры"])}</dd></dl></article>`;
  if (state.reference === "industries") return `<article class="reference-card" data-reference-item="${index}"><div class="ref-top"><span>${esc(item["Сектор"])}</span><span>${esc(item["Коды классификатора"])}</span></div><h3>${esc(item["Отрасль"])}</h3><p>${esc(item["Оборудование"])}</p><dl><dt>Материал</dt><dd>${esc(item["Тип смазки"])}</dd><dt>Особенности</dt><dd>${esc(item["Особенности"])}</dd></dl></article>`;
  return `<article class="reference-card"><div class="ref-top"><span>${esc(item.id)}</span><span>стр. ${esc(item.catalog_pages)}</span></div><h3>${esc(item.name)}</h3><p>${esc(item.source)}</p></article>`;
}

function openReference(index) {
  const item = state.referenceRows[Number(index)];
  if (!item) return;
  const rows = Object.entries(item).filter(([, value]) => has(value));
  openDrawer(`<div class="drawer-hero"><span class="eyebrow">Справочная запись</span><h2>${esc(item["Стандарт"] || item["ASTM_Code"] || item["Отрасль"] || item.name)}</h2><p>${esc(state.reference.toUpperCase())}</p></div><div class="drawer-body">${detailSection("Поля записи", rows)}</div>`);
}

function field(label, value) { return has(value) ? [label, value] : null; }
function detailSection(title, fields) {
  const rows = fields.filter(Boolean);
  if (!rows.length) return "";
  return `<section class="drawer-section"><h3>${esc(title)}</h3><dl class="detail-list">${rows.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(Array.isArray(value) ? value.join("; ") : value)}</dd></div>`).join("")}</dl></section>`;
}

function apiTokens(item) {
  const raw = apiValue(item).toUpperCase().replaceAll("С", "C").replaceAll("Н", "H");
  return unique((raw.match(/\b(?:S[ABCDEFGHJKLMNP]|C[A-HJKN](?:-\d)?(?:\s+PLUS)?|F[AP]|GL-?[1-6])\b/g) || []).map((value) => value.replace(/\s+/g, " ")));
}

function functionalTokens(item) {
  const profile = professionalProfile(item);
  if (["engine", "gear"].includes(profile.kind)) return apiTokens(item);
  if (profile.kind === "coolant") return unique([compact(item.technical_document)]);
  if (profile.kind === "grease") return unique([compact(profile.grade)]);
  return unique(standardValues(item).map((entry) => `${compact(entry.system)}:${compact(entry.value)}`));
}

function equivalenceSignature(item) {
  const profile = professionalProfile(item);
  const grade = compact(profile.grade);
  const standards = functionalTokens(item);
  if (!grade || !standards.length || standards.some((value) => !value)) return null;
  if (["engine", "gear"].includes(profile.kind)) {
    return { key: `${profile.kind}|${grade}|${standards.join("|")}`, reason: `${profile.gradeLabel.replace("Вязкость ", "")} ${profile.grade} + точный ${profile.kind === "gear" ? "API GL" : "API"} ${standards.join("/")}` };
  }
  if (profile.kind === "industrial") {
    const category = norm(item.category).replace(/\bсинтетические\b/g, "").trim();
    return { key: `${profile.kind}|${category}|${grade}|${standards.join("|")}`, reason: `ISO VG ${profile.grade} + ${standardValues(item).map((entry) => `${entry.system} ${entry.value}`).join(" / ")}` };
  }
  if (profile.kind === "coolant") return { key: `${profile.kind}|${grade}|${standards.join("|")}`, reason: `${profile.gradeLabel} ${profile.grade} + единый ГОСТ/ТУ` };
  return { key: `${profile.kind}|${grade}`, reason: `${profile.gradeLabel} ${profile.grade}` };
}

function equivalentProducts(item) {
  const signature = equivalenceSignature(item);
  if (!signature) return [];
  return DATA.products.map((candidate) => {
    if (candidate.id === item.id) return null;
    const candidateSignature = equivalenceSignature(candidate);
    if (!candidateSignature || candidateSignature.key !== signature.key) return null;
    return {
      item: candidate,
      score: 100,
      reason: signature.reason,
      otherBrand: candidate.brand !== item.brand,
    };
  }).filter(Boolean).sort((a, b) => Number(b.otherBrand) - Number(a.otherBrand) || a.item.name.localeCompare(b.item.name, "ru")).slice(0, 8);
}

function analoguesSection(item) {
  const analogues = equivalentProducts(item);
  if (!analogues.length) return `<section class="drawer-section analogue-section"><div class="section-title"><h3>Аналоги продукции</h3><span>по классификации</span></div><p class="analogue-empty">Точного сопоставления по вязкости и функциональному стандарту в текущей базе нет.</p></section>`;
  return `<section class="drawer-section analogue-section"><div class="section-title"><h3>Аналоги продукции · ${analogues.length}</h3><span>строгое совпадение ключа</span></div><div class="analogue-list">${analogues.map(({ item: analogue, score, reason }) => `
    <button class="analogue-card" data-linked-product="${esc(analogue.id)}"><span class="analogue-score">${score}%</span><span><b>${esc(analogue.name)}</b><small>${esc(analogue.brand)} · ${esc(reason)}</small></span><i>→</i></button>`).join("")}</div><p class="analogue-disclaimer">Сопоставление справочное: перед заменой продукта проверьте допуски OEM и техническую документацию.</p></section>`;
}

function openProduct(id) {
  const item = DATA.products.find((product) => product.id === id);
  if (!item) return;
  const linkedClass = item.class_match && DATA.classes.find((entry) => entry.id === item.class_match.class_id);
  openDrawer(`
    <div class="drawer-hero"><span class="eyebrow">${esc(item.brand)} · ${esc(item.category)}</span><h2>${esc(item.name)}</h2><p>${esc(item.family)}</p><div class="drawer-chips">${productSpecs(item).map((value) => `<span>${esc(value)}</span>`).join("")}</div></div>
    <div class="drawer-body">
      ${linkedClass ? `<div class="drawer-note" data-linked-class="${esc(linkedClass.id)}"><strong>Предлагаемый класс ${esc(linkedClass.id)}</strong><br>${item.class_match.confidence}% · признаки: ${esc(item.class_match.basis.join(", "))}. Нажмите, чтобы открыть класс.</div>` : '<div class="drawer-note">Отраслевой класс пока не назначен: недостаточно однозначных признаков.</div>'}
      ${analoguesSection(item)}
      ${detailSection("Классификация", [field("ISO VG", item.viscosity), field("DIN / ГОСТ", item.din_gost_class), field("SAE", item.sae_class), field("API", item.api_class), field("Название по ГОСТ", item.gost_name), field("Класс ОЖ", item.coolant_class), field("Класс смазки", item.grease_class)])}
      ${detailSection("Документы и сертификаты", [field("Сертификат", item.certificate_number), field("Выдан", formatDate(item.certificate_issued_at)), field("Действует до", formatDate(item.certificate_expires_at)), field("Локальный производитель", item.local_producer_certificate), field("ГОСТ / ТУ / регламент", item.technical_document)])}
      ${detailSection("Коды классификаторов", [field("ТН ВЭД", item.tnved_code), field("ИКПУ", item.ikpu), field("ЕНКТ", item.enkt), field("СКП", item.skp)])}
      ${detailSection("Поставка", [field("Единица", item.unit), field("Упаковка", item.packaging), field("Тара", item.container)])}
      ${detailSection("Происхождение данных", [field("Источник", item.source), field("Строка", item.source_row), field("Legacy ID", item.legacy_id)])}
    </div>`);
}

function openClass(id) {
  const item = DATA.classes.find((entry) => entry.id === id);
  if (!item) return;
  const linked = DATA.products.filter((product) => product.class_match?.class_id === item.id).slice(0, 20);
  openDrawer(`
    <div class="drawer-hero"><span class="eyebrow">${esc(item.category)} · ${item.kind === "technical_fluid" ? "техническая жидкость" : "смазочный материал"}</span><h2>${esc(item.id)}</h2><p>${esc(item.application || item.product_form)}</p><div class="drawer-chips">${classSpecs(item).map((value) => `<span>${esc(value)}</span>`).join("")}</div></div>
    <div class="drawer-body">
      ${detailSection("Классификационные признаки", [field("Форма", item.product_form), field("Состояние", item.aggregate_state), field("Состав", item.base_composition), field("Базовое масло", item.base_oil), field("Загуститель", item.thickener), field("NLGI", item.nlgi), field("ISO VG", item.iso_vg), field("SAE Engine", item.sae_engine), field("SAE Gear", item.sae_gear), field("API", item.api), field("API GL", item.api_gl), field("ACEA", item.acea), field("ГОСТ", item.gost)])}
      ${detailSection("Эксплуатация", [field("Температура от", has(item.temp_min) ? `${item.temp_min} °C` : null), field("Температура до", has(item.temp_max) ? `${item.temp_max} °C` : null), field("Применение", item.application), field("Примеры", item.examples), field("Аналоги", item.analogues), field("Особенности", item.notes)])}
      ${detailSection("ASTM", [field("Класс продукта", item.astm_product), field("Методы испытаний", item.astm_tests), field("Комментарий", item.astm_notes)])}
      ${detailSection("ТН ВЭД — подсказка", [field("Глава", item.tnved_chapter), field("Код", item.tnved_hint)])}
      ${linked.length ? `<section class="drawer-section"><h3>Связанные продукты · ${linked.length}</h3><div class="linked-products">${linked.map((product) => `<button class="linked-product" data-linked-product="${product.id}">${esc(product.brand)} · ${esc(product.name)}</button>`).join("")}</div></section>` : ""}
    </div>`);
}

function openDrawer(html) {
  $("drawerContent").innerHTML = html;
  $("detailDrawer").classList.add("open");
  $("drawerBackdrop").classList.add("open");
  document.body.style.overflow = "hidden";
}
function closeDrawer() {
  $("detailDrawer").classList.remove("open");
  $("drawerBackdrop").classList.remove("open");
  document.body.style.overflow = "";
}

function runMatcher(event) {
  event.preventDefault();
  const category = $("matchCategory").value;
  const grade = compact($("matchGrade").value.replace(/SAE|ISO\s*VG/gi, ""));
  const standard = compact($("matchStandard").value);
  const queryTokens = norm($("matchQuery").value).split(/\s+/).filter((token) => token.length > 2);
  const candidates = DATA.classes.map((item) => {
    let score = 0;
    const reasons = [];
    if (item.category_code === category || (category === "TF" && item.kind === "technical_fluid")) { score += 42; reasons.push("категория"); }
    else return null;
    const grades = [item.iso_vg, item.sae_engine, item.sae_gear, item.nlgi].map(compact).filter(Boolean);
    if (grade && grades.some((value) => value === grade || value.includes(grade))) { score += 32; reasons.push("вязкость/консистенция"); }
    const standards = compact([item.id, item.api, item.api_gl, item.acea, item.gost, item.thickener, ...(item.standards || [])].join(" "));
    if (standard && standards.includes(standard)) { score += 18; reasons.push("стандарт"); }
    const haystack = classSearchText(item);
    const queryHits = queryTokens.filter((token) => haystack.includes(token));
    if (queryTokens.length) { score += Math.min(18, queryHits.length * 6); if (queryHits.length) reasons.push("назначение"); }
    if (!grade && !standard && !queryTokens.length) score = 50;
    return { item, score: Math.min(99, score), reasons };
  }).filter(Boolean).sort((a, b) => b.score - a.score || a.item.id.localeCompare(b.item.id)).slice(0, 8);
  $("matchResults").innerHTML = candidates.length ? `
    <div class="match-heading"><span class="eyebrow">Результат подбора</span><h2>Наиболее близкие классы</h2><p>Совпадение рассчитано по указанным признакам.</p></div>
    <div class="match-list">${candidates.map(({ item, score, reasons }) => `<article class="match-card" data-class-id="${esc(item.id)}"><div class="match-score" style="--score:${score}%" data-score="${score}%"></div><div><h3>${esc(item.id)} · ${esc(item.category)}</h3><p>${esc(item.application || item.product_form)}</p><div class="match-reasons">${reasons.map((reason) => `<span class="spec-pill">${esc(reason)}</span>`).join("")}</div></div><span class="class-code">Открыть →</span></article>`).join("")}</div>` : '<div class="empty-state">Не найдено подходящих классов. Уточните категорию или признаки.</div>';
  $("matchResults").scrollIntoView({ behavior: "smooth", block: "start" });
}

function openCommand() {
  $("globalSearch").blur();
  $("commandPalette").classList.add("open");
  $("commandPalette").setAttribute("aria-hidden", "false");
  $("commandInput").value = "";
  renderCommandResults();
  setTimeout(() => $("commandInput").focus(), 20);
}
function closeCommand() {
  $("commandPalette").classList.remove("open");
  $("commandPalette").setAttribute("aria-hidden", "true");
}
function renderCommandResults() {
  const tokens = norm($("commandInput").value).split(/\s+/).filter(Boolean);
  let results = [];
  if (tokens.length) {
    results = [
      ...DATA.products.filter((item) => tokens.every((token) => productSearchText(item).includes(token))).slice(0, 7).map((item) => ({ kind: "product", id: item.id, title: item.name, meta: `${item.brand} · ${item.category}`, icon: "◉" })),
      ...DATA.classes.filter((item) => tokens.every((token) => classSearchText(item).includes(token))).slice(0, 5).map((item) => ({ kind: "class", id: item.id, title: item.id, meta: `${item.category} · ${item.application || "класс"}`, icon: "◇" })),
    ].slice(0, 12);
  }
  $("commandResults").innerHTML = results.length ? results.map((item) => `<button class="command-result" data-command-kind="${item.kind}" data-command-id="${esc(item.id)}"><i>${item.icon}</i><span><b>${esc(item.title)}</b><span>${esc(item.meta)}</span></span><em>${item.kind === "product" ? "Продукт" : "Класс"}</em></button>`).join("") : `<div class="empty-state">${tokens.length ? "Ничего не найдено" : "Введите название, стандарт или код"}</div>`;
}
function handleCommandResult(event) {
  const button = event.target.closest("[data-command-kind]");
  if (!button) return;
  closeCommand();
  button.dataset.commandKind === "product" ? openProduct(button.dataset.commandId) : openClass(button.dataset.commandId);
}

function exportProducts() {
  const rows = filteredProducts();
  const columns = ["brand", "category", "name", "viscosity", "din_gost_class", "sae_class", "api_class", "gost_name", "coolant_class", "grease_class", "certificate_number", "certificate_expires_at", "technical_document", "tnved_code", "ikpu", "enkt", "skp"];
  const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [columns.join(";"), ...rows.map((row) => columns.map((column) => quote(row[column])).join(";"))].join("\n");
  const url = URL.createObjectURL(new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a"); link.href = url; link.download = "mf-classifier-products.csv"; link.click(); URL.revokeObjectURL(url);
  showToast(`Экспортировано ${rows.length} позиций`);
}

function restoreTheme() {
  const saved = localStorage.getItem("mf-theme");
  if (saved) document.documentElement.dataset.theme = saved;
}
function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("mf-theme", next);
}
function showToast(message) {
  const toast = $("toast"); toast.textContent = message; toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2400);
}

document.addEventListener("DOMContentLoaded", init);
