// Глобальные переменные
let allData = [];
let filteredData = [];
let currentSort = { field: null, direction: 'asc' };

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupEventListeners();
    updateFooterDate();
});

// Загрузка данных
async function loadData() {
    try {
        const response = await fetch('motor_oils.json');
        const json = await response.json();
        allData = json.motor_oils;
        filteredData = [...allData];
        
        populateFilters();
        renderTable();
        updateStats();
        updateResultsCount();
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        showToast('Ошибка загрузки данных', 'error');
    }
}

// Заполнение фильтров уникальными значениями
function populateFilters() {
    const brands = [...new Set(allData.map(item => item.brand))].sort();
    const viscosities = [...new Set(allData.map(item => item.viscosity_class))].sort();

    fillSelect('filterBrand', brands);
    fillSelect('filterViscosity', viscosities);

    // Заполняем номера стандартов при первой загрузке
    updateStandardNumbers();
}

function fillSelect(id, options) {
    const select = document.getElementById(id);
    const currentValue = select.value;

    // Сохраняем первую опцию "Все..."
    const firstOption = select.options[0];
    select.innerHTML = '';
    select.appendChild(firstOption);

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        select.appendChild(option);
    });

    select.value = currentValue;
}

// Обновление списка номеров стандартов в зависимости от выбранного типа
function updateStandardNumbers() {
    const standardType = document.getElementById('filterStandardType').value;
    let standards;

    if (standardType) {
        // Фильтруем стандарты по типу - проверяем точное совпадение
        standards = [...new Set(allData
            .map(item => item.standard)
            .filter(std => {
                // Разбиваем стандарт на отдельные части (по запятой или пробелу)
                const parts = std.split(/[,\s]+/);
                // Проверяем, есть ли выбранный тип среди частей
                return parts.some(part => part.startsWith(standardType));
            })
        )].sort();
    } else {
        // Показываем все стандарты
        standards = [...new Set(allData.map(item => item.standard))].sort();
    }

    fillSelect('filterStandardNumber', standards);

    // Применяем фильтры после обновления списка
    applyFilters();
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Табы
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchTab(e.target.dataset.tab);
        });
    });
    
    // Фильтры
    document.getElementById('filterBrand').addEventListener('change', applyFilters);
    document.getElementById('filterViscosity').addEventListener('change', applyFilters);
    document.getElementById('filterStandardType').addEventListener('change', updateStandardNumbers);
    document.getElementById('filterStandardNumber').addEventListener('change', applyFilters);
    document.getElementById('filterVolume').addEventListener('change', applyFilters);
    
    // Поиск с задержкой
    let searchTimeout;
    document.getElementById('filterSearch').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => applyFilters(), 300);
    });
    
    // Сброс фильтров
    document.getElementById('clearFilters').addEventListener('click', clearFilters);
    
    // Сортировка
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortTable(th.dataset.sort));
    });
    
    // Экспорт
    document.getElementById('exportCSV').addEventListener('click', exportCSV);
    document.getElementById('exportJSON').addEventListener('click', exportJSON);
    document.getElementById('exportPrint').addEventListener('click', () => window.print());
    document.getElementById('exportCopy').addEventListener('click', copyToClipboard);
    
    // Модальное окно
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    document.getElementById('detailModal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeModal();
    });
    
    // Клавиша Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

// Переключение табов
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    document.getElementById(tabName + 'Section').classList.add('active');
    
    if (tabName === 'stats') {
        updateStats();
    }
}

// Применение фильтров
function applyFilters() {
    const brand = document.getElementById('filterBrand').value;
    const viscosity = document.getElementById('filterViscosity').value;
    const standardType = document.getElementById('filterStandardType').value;
    const standardNumber = document.getElementById('filterStandardNumber').value;
    const volume = document.getElementById('filterVolume').value;
    const search = document.getElementById('filterSearch').value.toLowerCase();

    filteredData = allData.filter(item => {
        if (brand && item.brand !== brand) return false;
        if (viscosity && item.viscosity_class !== viscosity) return false;
        if (standardType && !item.standard.includes(standardType)) return false;
        if (standardNumber && item.standard !== standardNumber) return false;

        // Фильтр по объему тары
        if (volume) {
            const containerVolume = extractVolume(item.container);
            if (containerVolume !== parseInt(volume)) return false;
        }

        if (search && !item.name.toLowerCase().includes(search) &&
            !item.brand.toLowerCase().includes(search)) return false;
        return true;
    });

    renderTable();
    updateResultsCount();
}

// Извлечение объема из строки контейнера
function extractVolume(container) {
    const match = container.match(/(\d+)\s*(литр|л)/i);
    return match ? parseInt(match[1]) : null;
}

// Сброс фильтров
function clearFilters() {
    document.getElementById('filterBrand').value = '';
    document.getElementById('filterViscosity').value = '';
    document.getElementById('filterStandardType').value = '';
    document.getElementById('filterStandardNumber').value = '';
    document.getElementById('filterVolume').value = '';
    document.getElementById('filterSearch').value = '';

    filteredData = [...allData];
    currentSort = { field: null, direction: 'asc' };

    // Обновляем список номеров стандартов
    updateStandardNumbers();

    renderTable();
    updateResultsCount();
    showToast('Фильтры сброшены');
}

// Сортировка таблицы
function sortTable(field) {
    if (currentSort.field === field) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.field = field;
        currentSort.direction = 'asc';
    }
    
    filteredData.sort((a, b) => {
        let valA = a[field] || '';
        let valB = b[field] || '';
        
        if (typeof valA === 'string') {
            valA = valA.toLowerCase();
            valB = valB.toLowerCase();
        }
        
        if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Обновление иконок сортировки
    document.querySelectorAll('th[data-sort]').forEach(th => {
        const icon = th.querySelector('.sort-icon');
        if (th.dataset.sort === field) {
            icon.textContent = currentSort.direction === 'asc' ? '↑' : '↓';
            th.classList.add('sorted');
        } else {
            icon.textContent = '↕';
            th.classList.remove('sorted');
        }
    });
    
    renderTable();
}

// Рендеринг таблицы
function renderTable() {
    const tbody = document.getElementById('tableBody');
    
    if (filteredData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" class="no-data">
                    <div class="no-data-content">
                        <span class="no-data-icon">🔍</span>
                        <p>Ничего не найдено</p>
                        <p class="no-data-hint">Попробуйте изменить параметры фильтрации</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = filteredData.map(item => `
        <tr onclick="showDetail(${item.id})">
            <td><strong>${item.name}</strong></td>
            <td><span class="badge badge-viscosity">${item.viscosity_class}</span></td>
            <td>${item.standard}</td>
            <td>${item.unit}</td>
            <td>${item.packaging}</td>
            <td><span class="badge badge-brand">${item.brand}</span></td>
            <td>${item.container}</td>
            <td class="code-cell">${item.ikpu}</td>
            <td class="code-cell">${item.enkt}</td>
            <td class="code-cell">${item.tnved}</td>
            <td class="code-cell">${item.skp}</td>
        </tr>
    `).join('');
}

// Обновление счетчика результатов
function updateResultsCount() {
    const count = filteredData.length;
    const total = allData.length;
    document.getElementById('resultsCount').textContent = 
        `Показано: ${count} из ${total} позиций`;
    document.getElementById('footerTotal').textContent = total;
}

// Обновление статистики
function updateStats() {
    const brands = [...new Set(filteredData.map(item => item.brand))];
    const viscosities = [...new Set(filteredData.map(item => item.viscosity_class))];
    const standards = [...new Set(filteredData.map(item => item.standard))];
    
    document.getElementById('totalProducts').textContent = filteredData.length;
    document.getElementById('totalBrands').textContent = brands.length;
    document.getElementById('totalViscosity').textContent = viscosities.length;
    document.getElementById('totalStandards').textContent = standards.length;
    
    // Графики
    renderChart('brandChart', countByField('brand'));
    renderChart('viscosityChart', countByField('viscosity_class'));
    renderChart('standardChart', countByField('standard'));
    renderChart('containerChart', countByVolume());
}

// Подсчет по полю
function countByField(field) {
    const counts = {};
    filteredData.forEach(item => {
        const key = item[field];
        counts[key] = (counts[key] || 0) + 1;
    });
    return Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
}

// Подсчет по объему тары
function countByVolume() {
    const counts = {};
    filteredData.forEach(item => {
        const volume = extractVolume(item.container);
        if (volume) {
            const key = `${volume} л`;
            counts[key] = (counts[key] || 0) + 1;
        }
    });
    return Object.entries(counts)
        .sort((a, b) => {
            // Сортируем по числовому значению объема
            const volA = parseInt(a[0]);
            const volB = parseInt(b[0]);
            return volA - volB;
        })
        .slice(0, 10);
}

// Рендеринг графика
function renderChart(containerId, data) {
    const container = document.getElementById(containerId);
    const maxValue = Math.max(...data.map(d => d[1]));
    
    container.innerHTML = data.map(([label, value]) => `
        <div class="chart-bar">
            <div class="chart-label" title="${label}">${label}</div>
            <div class="chart-bar-container">
                <div class="chart-bar-fill" style="width: ${(value / maxValue) * 100}%"></div>
            </div>
            <div class="chart-value">${value}</div>
        </div>
    `).join('');
}

// Показать детали
function showDetail(id) {
    const item = allData.find(i => i.id === id);
    if (!item) return;
    
    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('modalBody');
    
    modalBody.innerHTML = `
        <h2>${item.brand} ${item.name}</h2>
        <div class="detail-grid">
            <div class="detail-section">
                <h3>🛢️ Характеристики</h3>
                <div class="detail-row">
                    <span class="detail-label">Наименование:</span>
                    <span class="detail-value">${item.name}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Класс вязкости:</span>
                    <span class="detail-value"><span class="badge badge-viscosity">${item.viscosity_class}</span></span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Спецификация:</span>
                    <span class="detail-value">${item.standard}</span>
                </div>
            </div>
            <div class="detail-section">
                <h3>📦 Упаковка</h3>
                <div class="detail-row">
                    <span class="detail-label">Бренд:</span>
                    <span class="detail-value"><span class="badge badge-brand">${item.brand}</span></span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Ед. измерения:</span>
                    <span class="detail-value">${item.unit}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Упаковка:</span>
                    <span class="detail-value">${item.packaging}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Тара:</span>
                    <span class="detail-value">${item.container}</span>
                </div>
            </div>
            <div class="detail-section detail-codes">
                <h3>🔢 Коды классификации</h3>
                <div class="codes-grid">
                    <div class="code-box">
                        <span class="code-label">ИКПУ</span>
                        <span class="code-value">${item.ikpu}</span>
                    </div>
                    <div class="code-box">
                        <span class="code-label">ЕНКТ</span>
                        <span class="code-value">${item.enkt}</span>
                    </div>
                    <div class="code-box">
                        <span class="code-label">ТН ВЭД</span>
                        <span class="code-value">${item.tnved}</span>
                    </div>
                    <div class="code-box">
                        <span class="code-label">СКП</span>
                        <span class="code-value">${item.skp}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    modal.classList.add('active');
}

// Закрыть модальное окно
function closeModal() {
    document.getElementById('detailModal').classList.remove('active');
}

// Экспорт в CSV
function exportCSV() {
    const headers = ['Наименование', 'Класс вязкости', 'Спецификация',
                     'Ед.изм', 'Упаковка', 'Бренд', 'Тара', 'ИКПУ', 'ЕНКТ', 'ТН ВЭД', 'СКП'];

    const rows = filteredData.map(item => [
        item.name,
        item.viscosity_class,
        item.standard,
        item.unit,
        item.packaging,
        item.brand,
        item.container,
        item.ikpu,
        item.enkt,
        item.tnved,
        item.skp
    ]);
    
    const csvContent = '\uFEFF' + // BOM для Excel
        headers.join(';') + '\n' +
        rows.map(row => row.map(cell => `"${cell}"`).join(';')).join('\n');
    
    downloadFile(csvContent, 'motor_oils.csv', 'text/csv;charset=utf-8');
    showToast('CSV файл скачан');
}

// Экспорт в JSON
function exportJSON() {
    const jsonContent = JSON.stringify(filteredData, null, 2);
    downloadFile(jsonContent, 'motor_oils.json', 'application/json');
    showToast('JSON файл скачан');
}

// Копирование в буфер
function copyToClipboard() {
    const headers = ['Наименование', 'Класс вязкости', 'Спецификация',
                     'Ед.изм', 'Упаковка', 'Бренд', 'Тара', 'ИКПУ', 'ЕНКТ', 'ТН ВЭД', 'СКП'];

    const rows = filteredData.map(item => [
        item.name,
        item.viscosity_class,
        item.standard,
        item.unit,
        item.packaging,
        item.brand,
        item.container,
        item.ikpu,
        item.enkt,
        item.tnved,
        item.skp
    ].join('\t'));
    
    const text = headers.join('\t') + '\n' + rows.join('\n');
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Данные скопированы в буфер обмена');
    }).catch(() => {
        showToast('Ошибка копирования', 'error');
    });
}

// Скачивание файла
function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// Toast уведомления
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Обновление даты в футере
function updateFooterDate() {
    const date = new Date().toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    document.getElementById('footerDate').textContent = date;
}
