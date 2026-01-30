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

// Получение описания стандарта
function getStandardDescription(standard) {
    const descriptions = {
        // API Бензиновые
        'SP': 'API SP (2020+) - новейший стандарт для современных бензиновых двигателей. Обеспечивает защиту от преждевременного воспламенения на низких оборотах (LSPI), улучшенную экономию топлива и совместимость с системами нейтрализации выхлопных газов.',
        'SN': 'API SN (2010+) - для современных бензиновых двигателей. Улучшенная защита от высокотемпературных отложений, окисления масла. Совместимо с катализаторами и турбокомпрессорами.',
        'SM': 'API SM (2004-2010) - для бензиновых двигателей. Повышенная стойкость к окислению, защита от отложений, улучшенные низкотемпературные свойства.',
        'SL': 'API SL (2001-2003) - для многоклапанных бензиновых двигателей с турбонаддувом. Энергосберегающие свойства, защита от износа.',
        'SJ': 'API SJ (1996-2001) - для старых бензиновых двигателей. Базовая защита от износа и отложений.',
        'SG': 'API SG (1989-1993) - для бензиновых двигателей старого поколения.',
        'SF': 'API SF (1980-1988) - для карбюраторных двигателей, устаревший стандарт.',

        // API Дизельные
        'CI-4': 'API CI-4 (2002+) - для современных высокооборотных дизелей с рециркуляцией выхлопных газов (EGR). Повышенная термическая стабильность, контроль сажи и износа.',
        'CH-4': 'API CH-4 (1998+) - для дизелей, работающих на топливе с содержанием серы до 0.5%. Защита от высокотемпературных отложений.',
        'CG-4': 'API CG-4 (1995+) - для дизелей, эксплуатируемых в тяжелых условиях на шоссе.',
        'CF-4': 'API CF-4 (1990+) - для высокооборотных четырехтактных дизелей. Контроль за образованием нагара и износом.',
        'CF': 'API CF - для дизелей с непрямым впрыском.',
        'CD': 'API CD (1955+) - для дизелей с повышенным содержанием серы в топливе.',
        'CC': 'API CC (1961-1990) - для дизелей умеренного режима работы.',
        'CB': 'API CB (1949-1961) - для дизелей с умеренной нагрузкой, устаревший стандарт.',

        // API Составные стандарты (универсальные)
        'SN/CF': 'API SN/CF - универсальное масло для современных бензиновых (SN) и дизельных (CF) двигателей. Подходит для смешанных парков техники.',
        'SM/CF': 'API SM/CF - универсальное масло для бензиновых двигателей 2004-2010 и дизелей с непрямым впрыском.',
        'SL/CF': 'API SL/CF - универсальное масло для бензиновых двигателей 2001-2003 и дизелей с непрямым впрыском.',
        'SJ/CF': 'API SJ/CF - универсальное масло для старых бензиновых двигателей и дизелей.',
        'CI-4/SL': 'API CI-4/SL - универсальное масло для современных дизелей с EGR и бензиновых двигателей 2001-2003.',
        'CI-4/CH-4/SL': 'API CI-4/CH-4/SL - универсальное масло для современных и средневозрастных дизелей и бензиновых двигателей.',
        'CH-4/SJ': 'API CH-4/SJ - универсальное масло для дизелей 1998+ и бензиновых двигателей 1996-2001.',
        'CH-4/CG-4/SJ': 'API CH-4/CG-4/SJ - универсальное масло для дизелей и бензиновых двигателей старого поколения.',
        'CF-4/SG': 'API CF-4/SG - универсальное масло для старых четырехтактных дизелей и бензиновых двигателей.',
        'SF/CC': 'API SF/CC - устаревшее универсальное масло для старых бензиновых и дизельных двигателей.',
        'SG/CD': 'API SG/CD - универсальное масло для бензиновых и дизельных двигателей старого поколения.',

        // API Plus версии
        'CH-4 Plus': 'API CH-4 Plus - улучшенная версия CH-4 с повышенной защитой от окисления и износа для дизельных двигателей.',
        'CI-4 Plus': 'API CI-4 Plus - улучшенная версия CI-4 с повышенной стойкостью к сажеобразованию для дизелей с EGR.',

        // ACEA Бензин/Дизель
        'A3/B3': 'ACEA A3/B3 - для высокопроизводительных бензиновых и дизельных двигателей. Увеличенные интервалы замены, работа в тяжелых условиях.',
        'A3/B4': 'ACEA A3/B4 - для бензиновых и дизельных двигателей с прямым впрыском (включая насос-форсунки). Совместимо с сажевыми фильтрами некоторых типов.',
        'A5/B5': 'ACEA A5/B5 - для современных двигателей с увеличенными интервалами замены. Улучшенная топливная экономичность.',

        // ACEA Малозольные
        'C2': 'ACEA C2 - малозольное масло для двигателей с сажевым фильтром (DPF) и трёхкомпонентным катализатором. Низкая вязкость HTHS, экономия топлива.',
        'C3': 'ACEA C3 - малозольное масло для двигателей с сажевым фильтром (DPF). Средняя вязкость HTHS, совместимо с большинством европейских двигателей.',
        'C5': 'ACEA C5 - новейшее малозольное масло для современных двигателей с системами очистки выхлопа. Максимальная экономия топлива.',
        'C2/C3': 'ACEA C2/C3 - универсальное малозольное масло, совместимое с требованиями C2 и C3. Подходит для большинства современных двигателей с DPF.',
        'A3/B3/B4': 'ACEA A3/B3/B4 - универсальное масло для высокопроизводительных бензиновых и дизельных двигателей, включая с прямым впрыском.',

        // ACEA Дизель грузовой
        'E7': 'ACEA E7 - для тяжелонагруженных дизелей Euro 1-5 без DPF. Увеличенные интервалы замены, защита от износа и отложений.',
        'E7-12': 'ACEA E7-12 (редакция 2012) - для дизелей тяжелой техники Euro 1-5. Работа на топливе с различным содержанием серы.',

        // ILSAC
        'GF-6A': 'ILSAC GF-6A (2020+) - для японских и корейских автомобилей. Защита от LSPI, улучшенная экономия топлива, совместимость с турбодвигателями.',
        'GF-5': 'ILSAC GF-5 (2010+) - для японских двигателей. Энергосбережение, защита турбокомпрессоров, совместимость с уплотнениями.',

        // JASO
        'MA2': 'JASO MA2 - для мотоциклов с мокрым сцеплением. Высокий коэффициент трения, предотвращает пробуксовку сцепления при разгоне и переключении передач.',
        'MA': 'JASO MA - для 4-тактных мотоциклов с интегрированной КПП и мокрым сцеплением.',
        'MB': 'JASO MB - для скутеров с автоматической трансмиссией (CVT), низкий коэффициент трения.',

        // VDS
        'VDS-3': 'VDS-3 (Volvo) - для дизелей Volvo с увеличенными интервалами замены. Совместимо с двигателями Euro 3-5 без DPF.',

        // ГОСТ
        'ГОСТ 8581-78': 'ГОСТ 8581-78 - масла для автотракторных дизелей советского и российского производства. Группы Г2, В2 для разных условий эксплуатации.',
        'ТУ': 'ТУ (Технические Условия) - масла производятся по специальным техническим условиям производителя.',

        // Дополнительные стандарты
        'SN Plus': 'API SN Plus - расширенная версия API SN с улучшенной защитой от LSPI для турбированных двигателей с прямым впрыском.'
    };

    return descriptions[standard] || '';
}

// Получение информации о применении
function getApplicationInfo(standard) {
    const info = {
        // Бензиновые
        'SP': { engines: '🚗 Современные бензиновые (2020+)', age: 'Новые двигатели', type: 'Турбо, атмосферные, гибриды' },
        'SN': { engines: '🚗 Бензиновые (2010+)', age: 'Современные двигатели', type: 'Турбо, атмосферные, многоклапанные' },
        'SN Plus': { engines: '🚗 Бензиновые с прямым впрыском', age: 'Современные (2017+)', type: 'Турбо с прямым впрыском' },
        'SM': { engines: '🚗 Бензиновые (2004-2010)', age: 'Средний возраст', type: 'Атмосферные, турбо' },
        'SL': { engines: '🚗 Бензиновые (2001-2003)', age: 'Старые двигатели', type: 'Многоклапанные' },
        'SJ': { engines: '🚗 Бензиновые (1996-2001)', age: 'Устаревшие', type: 'Карбюраторные, инжекторные' },
        'SG': { engines: '🚗 Бензиновые (1989-1993)', age: 'Очень старые', type: 'Карбюраторные' },

        // Дизельные
        'CI-4': { engines: '🚛 Дизельные с EGR', age: 'Современные (2002+)', type: 'Турбодизели Euro 3-4' },
        'CH-4': { engines: '🚛 Дизельные (1998+)', age: 'Средний возраст', type: 'Турбодизели' },
        'CF-4': { engines: '🚛 Дизельные (1990+)', age: 'Старые', type: 'Четырехтактные дизели' },
        'CF': { engines: '🚛 Дизельные', age: 'Старые', type: 'Непрямой впрыск' },
        'CD': { engines: '🚛 Дизельные', age: 'Устаревшие', type: 'С высоким содержанием серы' },
        'CC': { engines: '🚛 Дизельные', age: 'Очень старые', type: 'Умеренная нагрузка' },
        'CB': { engines: '🚜 Тракторные дизели', age: 'Старые советские', type: 'Тепловозы, судовые' },

        // Составные стандарты
        'SN/CF': { engines: '🚗🚛 Бензин и дизель', age: 'Современные', type: 'Универсальное' },
        'SM/CF': { engines: '🚗🚛 Бензин и дизель', age: 'Средний возраст', type: 'Универсальное' },
        'SL/CF': { engines: '🚗🚛 Бензин и дизель', age: 'Старые', type: 'Универсальное' },
        'SJ/CF': { engines: '🚗🚛 Бензин и дизель', age: 'Устаревшие', type: 'Универсальное' },
        'CI-4/SL': { engines: '🚛🚗 Дизель и бензин', age: 'Современные', type: 'Универсальное' },
        'CI-4/CH-4/SL': { engines: '🚛🚗 Дизель и бензин', age: 'Современные и средние', type: 'Универсальное' },
        'CH-4/SJ': { engines: '🚛🚗 Дизель и бензин', age: 'Средний возраст', type: 'Универсальное' },
        'CH-4/CG-4/SJ': { engines: '🚛🚗 Дизель и бензин', age: 'Старые', type: 'Универсальное' },
        'CF-4/SG': { engines: '🚛🚗 Дизель и бензин', age: 'Старые', type: 'Универсальное' },
        'SF/CC': { engines: '🚗🚛 Бензин и дизель', age: 'Очень старые', type: 'Устаревшее' },
        'SG/CD': { engines: '🚗🚛 Бензин и дизель', age: 'Очень старые', type: 'Устаревшее' },
        'CH-4 Plus': { engines: '🚛 Дизельные', age: 'Современные (1998+)', type: 'Улучшенная защита' },
        'CI-4 Plus': { engines: '🚛 Дизельные с EGR', age: 'Современные (2002+)', type: 'Повышенная стойкость' },

        // ACEA
        'A3/B3': { engines: '🚗🚛 Бензин/дизель', age: 'Европейские авто', type: 'Высокая нагрузка' },
        'A3/B4': { engines: '🚗🚛 Бензин/дизель с прямым впрыском', age: 'Современные европейские', type: 'Турбо, насос-форсунки' },
        'A3/B3/B4': { engines: '🚗🚛 Бензин/дизель универсальное', age: 'Европейские авто', type: 'Высокая нагрузка, турбо' },
        'C2': { engines: '🚗 С DPF', age: 'Современные Euro 4-6', type: 'Малозольные, экономичные' },
        'C3': { engines: '🚗 С сажевым фильтром (DPF)', age: 'Современные Euro 4-6', type: 'Малозольные' },
        'C2/C3': { engines: '🚗 С DPF универсальное', age: 'Современные Euro 4-6', type: 'Малозольные' },
        'C5': { engines: '🚗 Новейшие с DPF', age: 'Современные Euro 6', type: 'Экономичные' },
        'E7': { engines: '🚛 Грузовые дизели', age: 'Euro 1-5', type: 'Тяжелая техника' },
        'E7-12': { engines: '🚛 Грузовые дизели', age: 'Euro 1-5', type: 'Тяжелая техника' },

        // ILSAC
        'GF-6A': { engines: '🚗 Японские/корейские', age: 'Новейшие (2020+)', type: 'Все типы' },
        'GF-5': { engines: '🚗 Японские/корейские', age: 'Современные (2010+)', type: 'Энергосберегающие' },

        // JASO
        'MA2': { engines: '🏍️ Мотоциклы', age: 'Все возрасты', type: 'С мокрым сцеплением' },
        'MA': { engines: '🏍️ Мотоциклы', age: 'Все возрасты', type: '4-тактные' },

        // VDS
        'VDS-3': { engines: '🚛 Volvo дизели', age: 'Euro 3-5', type: 'Без DPF' },

        // ГОСТ
        'ГОСТ': { engines: '🚜 Советская/российская техника', age: 'Все возрасты', type: 'Автотракторные дизели' },
        'ГОСТ 8581-78': { engines: '🚜 Советская/российская техника', age: 'Все возрасты', type: 'Автотракторные дизели' },
        'ТУ': { engines: '🏭 Специальные применения', age: 'По ТУ производителя', type: 'Специализированные' }
    };

    return info[standard] || { engines: '—', age: '—', type: '—' };
}

// Показать детали
function showDetail(id) {
    const item = allData.find(i => i.id === id);
    if (!item) return;

    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('modalBody');

    // Парсим стандарты - правильно извлекаем коды стандартов
    const standardParts = item.standard.split(',').map(s => s.trim());
    const standards = [];

    standardParts.forEach(part => {
        // Убираем префиксы (API, ACEA, ILSAC, JASO, VDS, ГОСТ, ТУ, Ts) и извлекаем коды
        const cleaned = part.replace(/^(API|ACEA|ILSAC|JASO|VDS|ГОСТ|ТУ|Ts)\s+/i, '');

        // Для случаев типа "ГОСТ 8581-78" или "VDS-3" без префикса API
        if (cleaned && cleaned !== part) {
            standards.push(cleaned);
        } else if (part.match(/^(ГОСТ|ТУ|VDS|Ts)/i)) {
            standards.push(part);
        }
    });

    const standardsHtml = standards.map(std => {
        const desc = getStandardDescription(std);
        const app = getApplicationInfo(std);

        if (!desc) return '';

        return `
            <div class="standard-item">
                <div class="standard-badge">${std}</div>
                <div class="standard-info">
                    <p class="standard-desc">${desc}</p>
                    <div class="standard-meta">
                        <span><strong>Двигатели:</strong> ${app.engines}</span>
                        <span><strong>Возраст:</strong> ${app.age}</span>
                        <span><strong>Тип:</strong> ${app.type}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');

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
            ${standardsHtml ? `
            <div class="detail-section detail-standards">
                <h3>📋 Стандарты и допуски</h3>
                <div class="standards-list">
                    ${standardsHtml}
                </div>
            </div>
            ` : ''}
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
