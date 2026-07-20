let allData = [];
let filteredData = [];
let currentSort = { field: "number", direction: "asc" };

const byId = (id) => document.getElementById(id);
const text = (value) => value === null || value === undefined || value === "" ? "—" : String(value);
const escapeHtml = (value) => text(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

document.addEventListener("DOMContentLoaded", () => {
    loadData();
    setupEventListeners();
    byId("footerDate").textContent = new Date().toLocaleDateString("ru-RU");
});

async function loadData() {
    try {
        const response = await fetch("product_catalog.json?v=20260720");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        allData = payload.products || [];
        filteredData = [...allData];
        populateFilters();
        applyFilters();
    } catch (error) {
        console.error(error);
        showToast("Не удалось загрузить классификатор", "error");
    }
}
function unique(field) {
    return [...new Set(allData.map((item) => item[field]).filter(Boolean))]
        .sort((a, b) => String(a).localeCompare(String(b), "ru", { numeric: true }));
}

function fillSelect(id, values) {
    const select = byId(id);
    const current = select.value;
    const first = select.options[0];
    select.innerHTML = "";
    select.appendChild(first);
    values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    });
    select.value = values.includes(current) ? current : "";
}

function populateFilters() {
    fillSelect("filterBrand", unique("brand"));
    fillSelect("filterFamily", unique("family"));
    fillSelect("filterCategory", unique("category"));
    fillSelect("filterStandardType", [...new Set(allData.flatMap((item) => item.standard_types || []))]
        .sort((a, b) => String(a).localeCompare(String(b), "ru")));
    fillSelect("filterTnved", unique("tnved_code").map(String));
}

function setupEventListeners() {
    document.querySelectorAll(".tab-btn").forEach((button) => {
        button.addEventListener("click", () => switchTab(button.dataset.tab));
    });
    ["filterBrand", "filterFamily", "filterCategory", "filterStandardType", "filterCertificate", "filterTnved"]
        .forEach((id) => byId(id).addEventListener("change", applyFilters));
    let timer;
    byId("filterSearch").addEventListener("input", () => {
        clearTimeout(timer);
        timer = setTimeout(applyFilters, 220);
    });
    byId("clearFilters").addEventListener("click", clearFilters);
    document.querySelectorAll("th[data-sort]").forEach((cell) => {
        cell.addEventListener("click", () => sortTable(cell.dataset.sort));
    });
    byId("tableBody").addEventListener("click", (event) => {
        const row = event.target.closest("[data-product-id]");
        if (row) showDetail(Number(row.dataset.productId));
    });
    byId("exportCSV").addEventListener("click", exportCSV);
    byId("exportJSON").addEventListener("click", exportJSON);
    byId("exportPrint").addEventListener("click", () => window.print());
    byId("exportCopy").addEventListener("click", copyToClipboard);
    document.querySelector(".modal-close").addEventListener("click", closeModal);
    byId("detailModal").addEventListener("click", (event) => {
        if (event.target === event.currentTarget) closeModal();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeModal();
    });
}

function switchTab(name) {
    document.querySelectorAll(".tab-btn").forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === name);
    });
    document.querySelectorAll(".content-section").forEach((section) => section.classList.remove("active"));
    byId(`${name}Section`).classList.add("active");
    if (name === "stats") updateStats();
}

function searchable(item) {
    return [
        item.name, item.brand, item.family, item.category, item.viscosity,
        item.din_gost_class, item.sae_class, item.api_class, item.gost_name,
        item.coolant_class, item.grease_class, item.certificate_number,
        item.technical_document, item.tnved_code, item.ikpu, item.enkt, item.skp,
        item.analogues, item.application,
    ].filter(Boolean).join(" ").toLocaleLowerCase("ru-RU");
}

function certificateStatus(item) {
    if (!item.certificate_number) return "missing";
    if (!item.certificate_expires_at) return "no_expiry";
    return item.certificate_expires_at < new Date().toISOString().slice(0, 10) ? "expired" : "valid";
}

function applyFilters() {
    const filters = {
        brand: byId("filterBrand").value,
        family: byId("filterFamily").value,
        category: byId("filterCategory").value,
        standard: byId("filterStandardType").value,
        certificate: byId("filterCertificate").value,
        tnved: byId("filterTnved").value,
        search: byId("filterSearch").value.trim().toLocaleLowerCase("ru-RU"),
    };
    const searchTokens = filters.search.split(/\s+/).filter(Boolean);
    filteredData = allData.filter((item) => {
        if (filters.brand && item.brand !== filters.brand) return false;
        if (filters.family && item.family !== filters.family) return false;
        if (filters.category && item.category !== filters.category) return false;
        if (filters.standard && !(item.standard_types || []).includes(filters.standard)) return false;
        if (filters.certificate && certificateStatus(item) !== filters.certificate) return false;
        if (filters.tnved && String(item.tnved_code || "") !== filters.tnved) return false;
        const haystack = searchable(item);
        return searchTokens.every((token) => haystack.includes(token));
    });
    sortCurrent();
    renderTable();
    updateStats();
    updateResultsCount();
}

function clearFilters() {
    ["filterBrand", "filterFamily", "filterCategory", "filterStandardType", "filterCertificate", "filterTnved"]
        .forEach((id) => { byId(id).value = ""; });
    byId("filterSearch").value = "";
    currentSort = { field: "number", direction: "asc" };
    applyFilters();
    showToast("Фильтры сброшены");
}

function sortTable(field) {
    currentSort = currentSort.field === field
        ? { field, direction: currentSort.direction === "asc" ? "desc" : "asc" }
        : { field, direction: "asc" };
    sortCurrent();
    renderTable();
    document.querySelectorAll("th[data-sort]").forEach((cell) => {
        const icon = cell.querySelector(".sort-icon");
        const active = cell.dataset.sort === field;
        cell.classList.toggle("sorted", active);
        if (icon) icon.textContent = active ? (currentSort.direction === "asc" ? "↑" : "↓") : "↕";
    });
}

function sortCurrent() {
    const multiplier = currentSort.direction === "asc" ? 1 : -1;
    filteredData.sort((a, b) => String(a[currentSort.field] ?? "")
        .localeCompare(String(b[currentSort.field] ?? ""), "ru", { numeric: true }) * multiplier);
}

function standardSummary(item) {
    return [
        item.viscosity ? `ISO VG ${item.viscosity}` : null,
        item.din_gost_class,
        item.sae_class ? `SAE ${item.sae_class}`.replace("SAE SAE", "SAE") : null,
        item.api_class ? `API ${item.api_class}`.replace("API API", "API") : null,
        item.coolant_class,
        item.grease_class,
    ].filter(Boolean).join(" · ") || "—";
}

function formatDate(value) {
    if (!value) return "—";
    const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
    return match ? `${match[3]}.${match[2]}.${match[1]}` : value;
}

function renderTable() {
    const body = byId("tableBody");
    if (!filteredData.length) {
        body.innerHTML = '<tr><td colspan="9" class="no-data"><div class="no-data-content"><span class="no-data-icon">🔍</span><p>Ничего не найдено</p></div></td></tr>';
        return;
    }
    body.innerHTML = filteredData.map((item) => `
        <tr data-product-id="${item.id}">
            <td><span class="badge badge-brand">${escapeHtml(item.brand)}</span></td>
            <td>${escapeHtml(item.category)}</td>
            <td><strong>${escapeHtml(item.name)}</strong></td>
            <td>${escapeHtml(item.viscosity ? `ISO VG ${item.viscosity}` : "—")}</td>
            <td>${escapeHtml(standardSummary(item))}</td>
            <td>${escapeHtml(item.gost_name)}</td>
            <td>${escapeHtml(item.technical_document)}</td>
            <td>${escapeHtml(formatDate(item.certificate_expires_at))}</td>
            <td class="code-cell">${escapeHtml(item.tnved_code)}</td>
        </tr>
    `).join("");
}

function updateResultsCount() {
    byId("resultsCount").textContent = `Показано: ${filteredData.length} из ${allData.length} позиций`;
    byId("footerTotal").textContent = allData.length;
}

function countsBy(field) {
    const counts = new Map();
    filteredData.forEach((item) => {
        const value = item[field];
        if (value) counts.set(String(value), (counts.get(String(value)) || 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12);
}

function standardCounts() {
    const counts = new Map();
    filteredData.forEach((item) => (item.standard_types || []).forEach((value) => {
        counts.set(value, (counts.get(value) || 0) + 1);
    }));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function updateStats() {
    byId("totalProducts").textContent = filteredData.length;
    byId("totalBrands").textContent = new Set(filteredData.map((item) => item.brand)).size;
    byId("totalViscosity").textContent = new Set(filteredData.flatMap((item) => item.standard_types || [])).size;
    byId("totalStandards").textContent = filteredData.filter((item) => item.certificate_number).length;
    renderChart("brandChart", countsBy("brand"));
    renderChart("viscosityChart", countsBy("category"));
    renderChart("standardChart", standardCounts());
    renderChart("containerChart", countsBy("tnved_code"));
}

function renderChart(id, data) {
    const container = byId(id);
    if (!data.length) {
        container.innerHTML = '<div class="no-data">Нет данных</div>';
        return;
    }
    const max = Math.max(...data.map((item) => item[1]));
    container.innerHTML = data.map(([label, value]) => `
        <div class="chart-bar">
            <div class="chart-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
            <div class="chart-bar-container"><div class="chart-bar-fill" style="width:${(value / max) * 100}%"></div></div>
            <div class="chart-value">${value}</div>
        </div>
    `).join("");
}

function hasValue(value) {
    return value !== null && value !== undefined && String(value).trim() !== "";
}

function detailField(label, value, options = {}) {
    if (!hasValue(value)) return "";
    const valueClass = options.code ? " detail-value-code" : "";
    return `<div class="detail-row">
        <span class="detail-label">${escapeHtml(label)}</span>
        <span class="detail-value${valueClass}">${escapeHtml(value)}</span>
    </div>`;
}

function detailSection(icon, title, fields) {
    const content = fields.filter(Boolean).join("");
    if (!content) return "";
    return `<section class="product-card-section">
        <h3><span>${icon}</span>${escapeHtml(title)}</h3>
        <div class="product-card-fields">${content}</div>
    </section>`;
}

function productIcon(item) {
    if (item.family === "Охлаждающие жидкости") return "❄️";
    if (item.family === "Пластичные смазки") return "⚙️";
    return "💧";
}

function viscosityLabel(value) {
    if (!hasValue(value)) return null;
    return /^ISO\s*VG/i.test(String(value)) ? value : `ISO VG ${value}`;
}

function sourceLabel(value) {
    const labels = {
        chilon_2026: "Реестр CHILON/UNO 2026",
        "chilon_2026+legacy_mfpresent": "Реестр CHILON/UNO + MFPRESENT",
        legacy_mfpresent: "Мультибрендовый справочник MFPRESENT",
        legacy_mfpresent_greases: "Отраслевой справочник пластичных смазок",
    };
    return labels[value] || value;
}

function productChips(item) {
    const chips = [
        viscosityLabel(item.viscosity),
        item.sae_class ? `SAE ${item.sae_class}`.replace("SAE SAE", "SAE") : null,
        item.api_class ? `API ${item.api_class}`.replace("API API", "API") : null,
        item.din_gost_class,
        item.coolant_class,
        item.grease_class,
    ].filter(hasValue);
    return [...new Set(chips)].slice(0, 6)
        .map((value) => `<span class="product-chip">${escapeHtml(value)}</span>`).join("");
}

function showDetail(id) {
    const item = allData.find((product) => product.id === id);
    if (!item) return;
    const certificate = certificateStatus(item);
    const certificateLabel = {
        valid: "Действующий сертификат",
        expired: "Срок сертификата истёк",
        no_expiry: "Срок не указан",
        missing: null,
    }[certificate];
    byId("modalBody").innerHTML = `
        <header class="product-hero">
            <div class="product-icon">${productIcon(item)}</div>
            <div class="product-identity">
                <div class="product-eyebrow">
                    <span class="product-brand">${escapeHtml(item.brand)}</span>
                    <span>${escapeHtml(item.category)}</span>
                </div>
                <h2>${escapeHtml(item.name)}</h2>
                <div class="product-chips">${productChips(item)}</div>
            </div>
        </header>
        <div class="product-card-body">
            ${certificateLabel ? `<div class="certificate-pill certificate-${certificate}"><i class="bi bi-patch-check"></i>${certificateLabel}${item.certificate_expires_at ? ` · до ${formatDate(item.certificate_expires_at)}` : ""}</div>` : ""}
            <div class="product-sections">
                ${detailSection("📐", "Классификация", [
                    detailField("ISO VG", item.viscosity),
                    detailField("SAE", item.sae_class),
                    detailField("API", item.api_class),
                    detailField("DIN / ГОСТ", item.din_gost_class),
                    detailField("ГОСТ-наименование", item.gost_name),
                    detailField("Класс ОЖ", item.coolant_class),
                    detailField("Класс смазки", item.grease_class),
                ])}
                ${detailSection("📋", "Документы", [
                    detailField("ГОСТ / ТУ / регламент", item.technical_document),
                    detailField("Сертификат", item.certificate_number, { code: true }),
                    detailField("Выдан", item.certificate_issued_at ? formatDate(item.certificate_issued_at) : null),
                    detailField("Действует до", item.certificate_expires_at ? formatDate(item.certificate_expires_at) : null),
                    detailField("Локальный производитель", item.local_producer_certificate),
                ])}
                ${detailSection("🔢", "Коды", [
                    detailField("ТН ВЭД", item.tnved_code, { code: true }),
                    detailField("ИКПУ", item.ikpu, { code: true }),
                    detailField("ЕНКТ", item.enkt, { code: true }),
                    detailField("СКП", item.skp, { code: true }),
                ])}
                ${detailSection("📦", "Поставка", [
                    detailField("Единица", item.unit),
                    detailField("Упаковка", item.packaging),
                    detailField("Тара", item.container),
                ])}
                ${detailSection("⚙️", "Применение и свойства", [
                    detailField("Применение", item.application),
                    detailField("Консистенция", item.consistency),
                    detailField("Загуститель", item.thickener),
                    detailField("Температуры", item.temperature_range),
                    detailField("Водостойкость", item.water_resistance),
                    detailField("Аналоги", item.analogues),
                    detailField("Особенности", item.features),
                ])}
            </div>
            <footer class="product-card-footer">
                <span><i class="bi bi-database"></i>${escapeHtml(sourceLabel(item.source_system))}</span>
                ${item.source_row ? `<span>Строка ${escapeHtml(item.source_row)}</span>` : ""}
            </footer>
        </div>`;
    byId("detailModal").classList.add("active");
    document.body.classList.add("modal-open");
}

function closeModal() {
    byId("detailModal").classList.remove("active");
    document.body.classList.remove("modal-open");
}

function download(content, filename, type) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

function exportCSV() {
    const columns = ["brand", "family", "category", "name", "viscosity", "din_gost_class", "sae_class", "api_class", "gost_name", "coolant_class", "grease_class", "certificate_number", "certificate_issued_at", "certificate_expires_at", "technical_document", "tnved_code", "ikpu", "enkt", "skp", "unit", "packaging", "container", "application", "analogues", "source_system"];
    const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const csv = [columns.join(";"), ...filteredData.map((item) => columns.map((column) => quote(item[column])).join(";"))].join("\n");
    download(`\ufeff${csv}`, "classifier_lubricants.csv", "text/csv;charset=utf-8");
}

function exportJSON() {
    download(JSON.stringify(filteredData, null, 2), "classifier_lubricants.json", "application/json");
}

async function copyToClipboard() {
    const lines = filteredData.map((item) => [item.brand, item.category, item.name, standardSummary(item), item.tnved_code || ""].join("\t"));
    await navigator.clipboard.writeText(["Бренд\tКатегория\tНаименование\tКлассификация\tТН ВЭД", ...lines].join("\n"));
    showToast("Скопировано в буфер обмена");
}

function showToast(message, type = "success") {
    const toast = byId("toast");
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => { toast.className = "toast"; }, 2600);
}
