// ============================= //
// ДАННЫЕ И СОСТОЯНИЕ
// ============================= //

let motorOilsData = [];
let greasesData = [];
let filtersData = {};

// ============================= //
// ИНИЦИАЛИЗАЦИЯ
// ============================= //

document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    initializeTabs();
    initializeFilters();
    initializeSearchButtons();
    
    // Показываем все результаты по умолчанию
    displayMotorOils(motorOilsData);
    displayGreases(greasesData);
});

// ============================= //
// ЗАГРУЗКА ДАННЫХ
// ============================= //

async function loadData() {
    try {
        // Загружаем моторные масла
        const motorResponse = await fetch('motor_oils.json');
        motorOilsData = await motorResponse.json();
        
        // Загружаем смазки
        const greasesResponse = await fetch('greases.json');
        greasesData = await greasesResponse.json();
        
        // Загружаем фильтры
        const filtersResponse = await fetch('filters.json');
        filtersData = await filtersResponse.json();
        
        console.log('✓ Данные загружены:', {
            motorOils: motorOilsData.length,
            greases: greasesData.length
        });
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        alert('Не удалось загрузить данные. Проверьте, что JSON файлы находятся в той же папке.');
    }
}

// ============================= //
// ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК
// ============================= //

function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Убираем active у всех кнопок и контента
            tabButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Добавляем active к выбранной вкладке
            button.classList.add('active');
            document.getElementById(`${tabName}-content`).classList.add('active');
        });
    });
}

// ============================= //
// ИНИЦИАЛИЗАЦИЯ ФИЛЬТРОВ
// ============================= //

function initializeFilters() {
    // Заполняем фильтры для моторных масел
    populateSelect('sae-filter', filtersData.motor_oils.SAE);
    populateSelect('api-filter', filtersData.motor_oils.API);
    populateSelect('acea-filter', filtersData.motor_oils.ACEA);
    
    // Заполняем фильтры для смазок
    populateSelect('consistency-filter', filtersData.greases['Консистенция']);
    populateSelect('thickener-filter', filtersData.greases['Загуститель']);
    populateSelect('temp-filter', filtersData.greases['Температурный диапазон']);
}

function populateSelect(selectId, options) {
    const select = document.getElementById(selectId);
    
    options.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option;
        optionElement.textContent = option;
        select.appendChild(optionElement);
    });
}

// ============================= //
// КНОПКИ ПОИСКА И СБРОСА
// ============================= //

function initializeSearchButtons() {
    // Моторные масла
    document.getElementById('motor-search-btn').addEventListener('click', searchMotorOils);
    document.getElementById('motor-reset-btn').addEventListener('click', resetMotorFilters);
    
    // Смазки
    document.getElementById('greases-search-btn').addEventListener('click', searchGreases);
    document.getElementById('greases-reset-btn').addEventListener('click', resetGreasesFilters);
}

// ============================= //
// ПОИСК МОТОРНЫХ МАСЕЛ
// ============================= //

function searchMotorOils() {
    const sae = document.getElementById('sae-filter').value;
    const api = document.getElementById('api-filter').value;
    const acea = document.getElementById('acea-filter').value;
    
    let results = motorOilsData;
    
    if (sae) {
        results = results.filter(oil => oil.SAE === sae);
    }
    
    if (api) {
        results = results.filter(oil => oil.API === api);
    }
    
    if (acea) {
        results = results.filter(oil => oil.ACEA === acea);
    }
    
    displayMotorOils(results);
}

function resetMotorFilters() {
    document.getElementById('sae-filter').value = '';
    document.getElementById('api-filter').value = '';
    document.getElementById('acea-filter').value = '';
    displayMotorOils(motorOilsData);
}

// ============================= //
// ПОИСК СМАЗОК
// ============================= //

function searchGreases() {
    const consistency = document.getElementById('consistency-filter').value;
    const thickener = document.getElementById('thickener-filter').value;
    const temp = document.getElementById('temp-filter').value;
    
    let results = greasesData;
    
    if (consistency) {
        results = results.filter(grease => grease['Консистенция'] === consistency);
    }
    
    if (thickener) {
        results = results.filter(grease => grease['Загуститель'] === thickener);
    }
    
    if (temp) {
        results = results.filter(grease => grease['Температурный диапазон'] === temp);
    }
    
    displayGreases(results);
}

function resetGreasesFilters() {
    document.getElementById('consistency-filter').value = '';
    document.getElementById('thickener-filter').value = '';
    document.getElementById('temp-filter').value = '';
    displayGreases(greasesData);
}

// ============================= //
// ОТОБРАЖЕНИЕ МОТОРНЫХ МАСЕЛ
// ============================= //

function displayMotorOils(oils) {
    const container = document.getElementById('motor-cards');
    const countElement = document.getElementById('motor-count');
    
    countElement.textContent = `${oils.length} найдено`;
    
    if (oils.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3>Ничего не найдено</h3>
                <p>Попробуйте изменить параметры поиска</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = oils.map(oil => createMotorOilCard(oil)).join('');
}

function createMotorOilCard(oil) {
    return `
        <div class="product-card">
            <div class="card-header">
                <div class="card-title">${oil.SAE}</div>
                <div class="card-subtitle">${oil.Состав}</div>
            </div>
            
            <div class="card-specs">
                <div class="spec-row">
                    <span class="spec-label">API:</span>
                    <span class="spec-value">
                        <span class="badge">${oil.API}</span>
                    </span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">ACEA:</span>
                    <span class="spec-value">
                        <span class="badge secondary">${oil.ACEA}</span>
                    </span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">ASTM:</span>
                    <span class="spec-value">${oil.ASTM}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Температура:</span>
                    <span class="spec-value">${oil['Темп. °C']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Применение:</span>
                    <span class="spec-value">${oil['Применение']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Примеры:</span>
                    <span class="spec-value"><strong>${oil['Примеры']}</strong></span>
                </div>
            </div>
        </div>
    `;
}

// ============================= //
// ОТОБРАЖЕНИЕ СМАЗОК
// ============================= //

function displayGreases(greases) {
    const container = document.getElementById('greases-cards');
    const countElement = document.getElementById('greases-count');
    
    countElement.textContent = `${greases.length} найдено`;
    
    if (greases.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3>Ничего не найдено</h3>
                <p>Попробуйте изменить параметры поиска</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = greases.map(grease => createGreaseCard(grease)).join('');
}

function createGreaseCard(grease) {
    return `
        <div class="product-card">
            <div class="card-header">
                <div class="card-title">${grease['Код']}</div>
                <div class="card-subtitle">${grease['DIN 51502']}</div>
            </div>
            
            <div class="card-specs">
                <div class="spec-row">
                    <span class="spec-label">Консистенция:</span>
                    <span class="spec-value">${grease['Консистенция']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Загуститель:</span>
                    <span class="spec-value">${grease['Загуститель']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Температура:</span>
                    <span class="spec-value">${grease['Температурный диапазон']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">ASTM:</span>
                    <span class="spec-value">${grease['ASTM']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">EP свойства:</span>
                    <span class="spec-value">${grease['Противозадирные свойства']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Водостойкость:</span>
                    <span class="spec-value">${grease['Водостойкость']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Применение:</span>
                    <span class="spec-value">${grease['Область применения']}</span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Аналоги:</span>
                    <span class="spec-value"><strong>${grease['Аналоги']}</strong></span>
                </div>
                
                <div class="spec-row">
                    <span class="spec-label">Особенности:</span>
                    <span class="spec-value">
                        <span class="badge neutral">${grease['Особенности']}</span>
                    </span>
                </div>
            </div>
        </div>
    `;
}

// ============================= //
// УТИЛИТЫ
// ============================= //

// Можно добавить дополнительные функции:
// - Поиск по названию
// - Сортировка результатов
// - Экспорт в Excel/PDF
// - Сравнение продуктов
