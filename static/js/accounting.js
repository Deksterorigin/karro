let trendChart = null;
let categoryChart = null;

function initCharts() {
    if (typeof Chart === 'undefined') return;

    const dark = document.documentElement.classList.contains('dark');
    const textColor = dark ? '#adb5bd' : '#495057';
    const gridColor = dark ? '#333333' : '#dee2e6';
    const tooltip = {
        padding: 12,
        backgroundColor: dark ? '#1c1c1c' : '#ffffff',
        titleColor: dark ? '#e9ecef' : '#212529',
        bodyColor: textColor,
        borderColor: gridColor,
        borderWidth: 1
    };

    if (trendChart) trendChart.destroy();
    if (categoryChart) categoryChart.destroy();

    const trendCanvas = document.getElementById('financeTrendChart');
    if (trendCanvas) {
        trendChart = new Chart(trendCanvas, {
            type: 'line',
            data: {
                labels: window.chartDates || [],
                datasets: [
                    {
                        label: getLang() === 'en' ? 'Income' : 'Доходи',
                        data: window.chartIncomes || [],
                        borderColor: dark ? '#4dd88f' : '#198754',
                        backgroundColor: 'rgba(25, 135, 84, 0.06)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: getLang() === 'en' ? 'Expenses' : 'Витрати',
                        data: window.chartExpenses || [],
                        borderColor: dark ? '#f16a76' : '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.05)',
                        fill: true,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: textColor } },
                    tooltip
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor } }
                }
            }
        });
    }

    const categoryCanvas = document.getElementById('expenseCategoryChart');
    if (categoryCanvas) {
        categoryChart = new Chart(categoryCanvas, {
            type: 'doughnut',
            data: {
                labels: window.categoryLabels || [],
                datasets: [{
                    data: window.categoryValues || [],
                    backgroundColor: [
                        '#0d6efd', '#198754', '#ffc107',
                        '#6f42c1', '#d63384', '#868e96'
                    ],
                    borderColor: dark ? '#1c1c1c' : '#ffffff',
                    borderWidth: dark ? 2 : 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: textColor, padding: 15 }
                    },
                    tooltip
                }
            }
        });
    }
}

function switchDashboardTab(tabId, button) {
    const target = document.getElementById(tabId);
    if (!target || !target.classList.contains('tab-content')) return;

    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.toggle('active', tab === target);
    });
    document.querySelectorAll('.tab-button').forEach(tabButton => {
        tabButton.classList.toggle('active', tabButton === button);
    });

    sessionStorage.setItem('karro_acc_active_tab', tabId);
}

function openModal(id) {
    document.getElementById(id)?.classList.add('active');
}

function closeModal(id) {
    document.getElementById(id)?.classList.remove('active');
}

function openPayoutModal(id, name, balance) {
    const form = document.getElementById('payoutForm');
    const employeeInput = document.getElementById('payout_emp_id');
    const amountInput = document.getElementById('payout_amount_input');

    if (form) form.action = '/accounting/employee/pay/';
    if (employeeInput) employeeInput.value = id;

    const nameElement = document.getElementById('payout_emp_name');
    const balanceElement = document.getElementById('payout_max_amount');
    if (nameElement) nameElement.textContent = name;
    if (balanceElement) balanceElement.textContent = balance;

    if (amountInput) {
        const amount = Number(String(balance).replace(',', '.'));
        amountInput.max = Number.isFinite(amount) ? amount.toFixed(2) : '';
        amountInput.value = amount > 0 ? amount.toFixed(2) : '';
    }

    openModal('payoutModal');
}

function openEditEmployeeModal(
    id, name, phone, email, position, rate, commission, isActiveStr = 'true'
) {
    const form = document.getElementById('editEmployeeForm');
    if (!form) return;

    form.action = `/accounting/employee/edit/${encodeURIComponent(id)}/`;

    const values = {
        edit_emp_name: name,
        edit_emp_phone: phone,
        edit_emp_email: email,
        edit_emp_position: position,
        edit_emp_rate: String(rate).replace(',', '.'),
        edit_emp_comm: String(commission).replace(',', '.'),
        edit_emp_is_active: isActiveStr
    };

    Object.entries(values).forEach(([elementId, value]) => {
        const input = document.getElementById(elementId);
        if (input) input.value = value ?? '';
    });

    const active = String(isActiveStr).toLowerCase() === 'true';
    const reactivateWrap = document.getElementById('reactivate-checkbox-wrap');
    const reactivateCheckbox = document.getElementById('reactivate-checkbox');

    if (reactivateWrap) reactivateWrap.style.display = active ? 'none' : 'block';
    if (reactivateCheckbox) reactivateCheckbox.checked = active;

    openModal('editEmployeeModal');
}

function toggleCategories(txType) {
    const select = document.getElementById('tx_category_select');
    if (!select) return;

    const categories = txType === 'expense'
        ? [
            ['spare_parts', 'Запчастини', 'Spare Parts'],
            ['rent', 'Оренда', 'Rent'],
            ['utilities', 'Комунальні послуги', 'Utilities'],
            ['other_expense', 'Інші витрати', 'Other Expense']
        ]
        : [
            ['service', 'Послуги СТО (Ремонт)', 'Service Revenue'],
            ['other_income', 'Інші доходи', 'Other Income']
        ];

    const previousValue = select.value;
    select.replaceChildren();

    categories.forEach(([value, uk, en]) => {
        const option = new Option(getLang() === 'en' ? en : uk, value);
        select.add(option);
    });

    if (categories.some(([value]) => value === previousValue)) {
        select.value = previousValue;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    window.addEventListener('themeChanged', initCharts);

    document.getElementById('theme-toggle-btn')?.addEventListener('click', () => {
        const globalToggle = document.getElementById('theme-toggle');
        if (globalToggle) {
            globalToggle.click();
            return;
        }

        const dark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('karro_theme', dark ? 'dark' : 'light');
        window.dispatchEvent(new CustomEvent('themeChanged'));
    });

    const savedTab = sessionStorage.getItem('karro_acc_active_tab');
    if (savedTab) {
        const button = [...document.querySelectorAll('.tab-button')].find(item => {
            return item.getAttribute('onclick')?.includes(`'${savedTab}'`);
        });
        if (button) switchDashboardTab(savedTab, button);
    }

    document.querySelectorAll('.acc-modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', event => {
            if (event.target === overlay) closeModal(overlay.id);
        });
    });

    const payoutForm = document.getElementById('payoutForm');
    payoutForm?.addEventListener('submit', event => {
        const employeeId = document.getElementById('payout_emp_id')?.value;
        const input = document.getElementById('payout_amount_input');
        const amount = Number(input?.value);

        if (!employeeId || !Number.isFinite(amount) || amount <= 0 ||
            amount > Number(input.max)) {
            event.preventDefault();
            alert(getLang() === 'en'
                ? 'Enter an amount within the available balance.'
                : 'Вкажіть суму в межах доступного балансу.');
        }
    });
});
