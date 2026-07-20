const DATA = window.MF_CLASSIFIER_DATA;
const PAGE_SIZE = 30;
const CLASS_PAGE_SIZE = 24;

const state = {
  view: "overview",
  productPage: 1,
  classPage: 1,
  reference: "standards",
  referenceRows: [],
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
  const valid = ["overview", "products", "classes", "references", "matcher"];
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
    container.innerHTML = `<div class="temperature-scale">
      <div class="temperature-axis"><span>Общая шкала</span><div class="temperature-axis-track"><i style="left:0%">−273</i><i style="left:${temperaturePosition(0)}%">0</i><i style="left:${temperaturePosition(300)}%">300</i><b style="left:${temperaturePosition(300)}%" aria-label="разрыв шкалы">//</b><i style="left:100%">2000</i></div><small>°C</small></div>
      ${rows.map((item) => {
      const min = Number(item["От °C"]), max = Number(item["До °C"]);
      const left = temperaturePosition(min), right = temperaturePosition(max);
      return `<div class="temperature-row"><div><b>${esc(item["Зона"])}</b><small>${esc(item["Код"])}</small></div><div class="temperature-range"><span style="left:${left}%;width:${Math.max(.5, right - left)}%"></span><i class="range-start" style="left:${left}%"></i><i class="range-end" style="left:${right}%"></i>${max > 300 ? `<b class="range-break" style="left:${temperaturePosition(300)}%">//</b>` : ""}</div><small>${min}…${max} °C</small></div>`;
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
