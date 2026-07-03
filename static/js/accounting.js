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
    
    // Перетворюємо десяткові числа для правильного відображення в полях форми
    document.getElementById('edit_emp_rate').value = parseFloat(rate.replace(',', '.')).toFixed(2);
    document.getElementById('edit_emp_comm').value = parseFloat(comm.replace(',', '.')).toFixed(2);
    
    const isActive = isActiveStr === 'true';
    document.getElementById('edit_emp_is_active').value = isActiveStr;
    
    const reactivateWrap = document.getElementById('reactivate-checkbox-wrap');
    const reactivateCheckbox = document.getElementById('reactivate-checkbox');
    
    // Якщо працівник звільнений, показуємо прапорець для його повернення на роботу
    if (!isActive) {
        reactivateWrap.style.display = 'block';
        reactivateCheckbox.checked = false;
    } else {
        reactivateWrap.style.display = 'none';
        reactivateCheckbox.checked = true;
    }
    
    openModal('editEmployeeModal');
}

// Зміна списку категорій у транзакціях залежно від обраного типу (дохід чи витрата)
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
            o.setAttribute('data-i18n', 'acc.cat_' + opt.val);
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
            o.setAttribute('data-i18n', 'acc.cat_' + opt.val);
            categorySelect.appendChild(o);
        });
    }
}

// Перевірка при зміні статусу заявки: якщо обрали "Виконано", відкриваємо модалку розрахунку
function handleStatusSubmit(form, event) {
    const select = form.querySelector('.status-select-element');
    if (select && select.value === 'completed') {
        event.preventDefault();
        const bookingIdInput = form.querySelector('input[name="booking_id"]');
        if (bookingIdInput) {
            document.getElementById('complete_booking_id').value = bookingIdInput.value;
            openModal('completeBookingModal');
        }
        return false;
    }
    return true;
}

// Закриття вікна завершення ремонту
function closeCompleteModal() {
    closeModal('completeBookingModal');
}

// Створюємо слухачі кліків для закриття модалок при натисканні на сірий фон навколо них
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.acc-modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal(this.id);
            }
        });
    });
});
