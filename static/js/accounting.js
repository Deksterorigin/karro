/* ═════════════════════════════════════════════
   Karro Standalone Accounting Interactivity JS
   All comments written in Ukrainian
   ═════════════════════════════════════════════ */

let trendChart = null;
let categoryChart = null;

// Функція ініціалізації та оновлення графіків
function initCharts() {
    const isDark = document.body.classList.contains('dark-theme');
    
    // Кольори шрифтів та сіток залежно від обраної теми
    const textColor = isDark ? '#94a3b8' : '#555555';
    const gridColor = isDark ? '#212c42' : '#e5e7eb';
    
    // 1. Графік динаміки доходів та витрат СТО
    const trendCtx = document.getElementById('financeTrendChart');
    if (trendCtx) {
        if (trendChart) {
            trendChart.destroy();
        }
        
        const ctx2d = trendCtx.getContext('2d');
        trendChart = new Chart(ctx2d, {
            type: 'line',
            data: {
                labels: window.chartDates || [],
                datasets: [
                    {
                        label: 'Доходи',
                        data: window.chartIncomes || [],
                        borderColor: isDark ? '#14b8a6' : '#319795',
                        backgroundColor: 'rgba(20, 184, 166, 0.05)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 3,
                        pointBackgroundColor: isDark ? '#14b8a6' : '#319795',
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Витрати',
                        data: window.chartExpenses || [],
                        borderColor: isDark ? '#f43f5e' : '#e53e3e',
                        backgroundColor: 'rgba(244, 63, 94, 0.05)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 3,
                        pointBackgroundColor: isDark ? '#f43f5e' : '#e53e3e',
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: textColor,
                            font: { family: 'Inter', size: 12, weight: '600' }
                        }
                    },
                    tooltip: {
                        padding: 12,
                        backgroundColor: isDark ? '#1e293b' : '#ffffff',
                        titleColor: isDark ? '#f8fafc' : '#1a1a1a',
                        bodyColor: isDark ? '#cbd5e1' : '#555555',
                        borderColor: isDark ? '#334155' : '#e5e7eb',
                        borderWidth: 1,
                        usePointStyle: true
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'transparent' },
                        ticks: { color: textColor, font: { family: 'Inter' } }
                    },
                    y: {
                        grid: { color: gridColor },
                        ticks: { color: textColor, font: { family: 'Inter' } }
                    }
                }
            }
        });
    }
    
    // 2. Кругова діаграма витрат за категоріями
    const categoryCtx = document.getElementById('expenseCategoryChart');
    if (categoryCtx) {
        if (categoryChart) {
            categoryChart.destroy();
        }
        
        const ctx2d = categoryCtx.getContext('2d');
        categoryChart = new Chart(ctx2d, {
            type: 'doughnut',
            data: {
                labels: window.categoryLabels || [],
                datasets: [{
                    data: window.categoryValues || [],
                    backgroundColor: [
                        '#3b82f6', // Синій
                        '#10b981', // Зелений
                        '#f59e0b', // Помаранчевий
                        '#8b5cf6', // Фіолетовий
                        '#ec4899', // Рожевий
                        '#64748b'  // Сірий
                    ],
                    borderWidth: isDark ? 2 : 1,
                    borderColor: isDark ? '#121824' : '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: textColor,
                            font: { family: 'Inter', size: 12, weight: '500' },
                            padding: 15
                        }
                    },
                    tooltip: {
                        padding: 12,
                        backgroundColor: isDark ? '#1e293b' : '#ffffff',
                        titleColor: isDark ? '#f8fafc' : '#1a1a1a',
                        bodyColor: isDark ? '#cbd5e1' : '#555555',
                        borderColor: isDark ? '#334155' : '#e5e7eb',
                        borderWidth: 1
                    }
                }
            }
        });
    }
}

// Перемикач табів дашборду бухгалтерії
function switchDashboardTab(tabId, btnElement) {
    // Приховуємо вміст усіх табів
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Знімаємо активний статус з усіх кнопок табів
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Показуємо обраний таб та активуємо кнопку
    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.classList.add('active');
    }
    if (btnElement) {
        btnElement.classList.add('active');
    }
    
    // Зберігаємо останній активний таб в сесію для зручності при перезавантаженні
    sessionStorage.setItem('karro_acc_active_tab', tabId);
}

// Відкриття модального вікна
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.add('active');
    }
}

// Закриття модального вікна
function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove('active');
    }
}

// Заповнення форми виплати зарплати даними працівника перед показом
function openPayoutModal(id, name, balance) {
    document.getElementById('payout_emp_id').value = id;
    document.getElementById('payout_emp_name').textContent = name;
    document.getElementById('payout_max_amount').textContent = balance;
    
    const amountInput = document.getElementById('payout_amount_input');
    amountInput.max = balance;
    amountInput.value = balance;
    
    openModal('payoutModal');
}

// Заповнення форми редагування працівника даними
function openEditEmployeeModal(id, name, phone, email, position, rate, comm, isActiveStr = 'true') {
    const form = document.getElementById('editEmployeeForm');
    form.action = `/accounting/employee/edit/${id}/`;
    
    document.getElementById('edit_emp_name').value = name;
    document.getElementById('edit_emp_phone').value = phone;
    document.getElementById('edit_emp_email').value = email;
    document.getElementById('edit_emp_position').value = position;
    
    // Конвертація для правильної роботи з формами
    document.getElementById('edit_emp_rate').value = parseFloat(rate.replace(',', '.')).toFixed(2);
    document.getElementById('edit_emp_comm').value = parseFloat(comm.replace(',', '.')).toFixed(2);
    
    const isActive = isActiveStr === 'true';
    document.getElementById('edit_emp_is_active').value = isActiveStr;
    
    const reactivateWrap = document.getElementById('reactivate-checkbox-wrap');
    const reactivateCheckbox = document.getElementById('reactivate-checkbox');
    
    if (!isActive) {
        reactivateWrap.style.display = 'block';
        reactivateCheckbox.checked = false;
    } else {
        reactivateWrap.style.display = 'none';
        reactivateCheckbox.checked = true;
    }
    
    openModal('editEmployeeModal');
}

// Динамічний вибір категорій транзакцій (витрати чи доходи)
function toggleCategories(txType) {
    const categorySelect = document.getElementById('tx_category_select');
    if (!categorySelect) return;
    categorySelect.innerHTML = '';
    
    const lang = localStorage.getItem('karro_lang') || 'uk';
    
    if (txType === 'expense') {
        const options = [
            { val: 'spare_parts', uk: 'Запчастини', en: 'Spare Parts' },
            { val: 'rent', uk: 'Оренда', en: 'Rent' },
            { val: 'utilities', uk: 'Комунальні послуги', en: 'Utilities' },
            { val: 'other_expense', uk: 'Інші витрати', en: 'Other Expense' }
        ];
        options.forEach(opt => {
            const o = document.createElement('option');
            o.value = opt.val;
            o.textContent = lang === 'en' ? opt.en : opt.uk;
            categorySelect.appendChild(o);
        });
    } else {
        const options = [
            { val: 'service', uk: 'Послуги СТО (Ремонт)', en: 'Service Revenue' },
            { val: 'other_income', uk: 'Інші доходи', en: 'Other Income' }
        ];
        options.forEach(opt => {
            const o = document.createElement('option');
            o.value = opt.val;
            o.textContent = lang === 'en' ? opt.en : opt.uk;
            categorySelect.appendChild(o);
        });
    }
}

// Запуск при завантаженні DOM
document.addEventListener('DOMContentLoaded', () => {
    // 1. Обробка перемикача тем
    const body = document.body;
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const savedTheme = localStorage.getItem('karro_theme');
    
    // Встановлюємо збережену тему за замовчуванням
    if (savedTheme === 'dark') {
        body.classList.add('dark-theme');
    } else if (savedTheme === 'light') {
        body.classList.remove('dark-theme');
    }
    
    // Ініціалізуємо графіки з урахуванням теми
    initCharts();
    
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            body.classList.toggle('dark-theme');
            const isDark = body.classList.contains('dark-theme');
            localStorage.setItem('karro_theme', isDark ? 'dark' : 'light');
            
            // Оновлюємо колірну схему графіків Chart.js
            initCharts();
        });
    }
    
    // 2. Перевіряємо та відновлюємо останній активний таб з сесії
    const lastActiveTab = sessionStorage.getItem('karro_acc_active_tab');
    if (lastActiveTab) {
        // Знаходимо кнопку таба за ідентифікатором
        const buttons = document.querySelectorAll('.tab-button');
        let matchedBtn = null;
        buttons.forEach(btn => {
            const clickAttr = btn.getAttribute('onclick');
            if (clickAttr && clickAttr.includes(lastActiveTab)) {
                matchedBtn = btn;
            }
        });
        if (matchedBtn) {
            switchDashboardTab(lastActiveTab, matchedBtn);
        }
    }
    
    // 3. Закриття модалок при кліку на фон
    document.querySelectorAll('.acc-modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal(this.id);
            }
        });
    });
});
