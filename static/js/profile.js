function showSection(name, btn) {
    document.querySelectorAll('.section-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById('section-' + name);
    if (panel) panel.classList.add('active');
    if (btn) btn.classList.add('active');
}

// Синхронізація вибраної мови
function switchLang(lang) {
    // Пошук глобального вибору мови або пряме збереження
    const globalSelect = document.getElementById('lang-select');
    if (globalSelect) {
        globalSelect.value = lang;
        globalSelect.dispatchEvent(new Event('change'));
    } else {
        localStorage.setItem('karro_lang', lang);
        location.reload();
    }
}

// Стан фільтрації та пошуку заявок
let activeFilterStatus = 'all';
let searchQuery = '';

function updateTabCounts() {
    const cards = document.querySelectorAll('.booking-card');
    let pending = 0, confirmed = 0, completed = 0, cancelled = 0;

    cards.forEach(card => {
        const status = card.dataset.status;
        if (status === 'pending') pending++;
        else if (status === 'confirmed') confirmed++;
        else if (status === 'completed') completed++;
        else if (status === 'cancelled') cancelled++;
    });

    const spanPending = document.querySelector('.count-pending');
    const spanConfirmed = document.querySelector('.count-confirmed');
    const spanCompleted = document.querySelector('.count-completed');
    const spanCancelled = document.querySelector('.count-cancelled');

    if (spanPending) spanPending.textContent = pending;
    if (spanConfirmed) spanConfirmed.textContent = confirmed;
    if (spanCompleted) spanCompleted.textContent = completed;
    if (spanCancelled) spanCancelled.textContent = cancelled;
}

function filterByStatus(status, btnElement) {
    activeFilterStatus = status;

    // Toggle active class on tab buttons
    document.querySelectorAll('.tab-filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    if (btnElement) {
        btnElement.classList.add('active');
    }

    applyFilters();
}

function applyFilters() {
    const cards = document.querySelectorAll('.booking-card');
    const noRequests = document.getElementById('no-requests');
    let visibleCount = 0;

    cards.forEach(card => {
        const statusMatch = (activeFilterStatus === 'all' || card.dataset.status === activeFilterStatus);
        
        let searchMatch = true;
        if (searchQuery) {
            const clientName = card.dataset.clientName || '';
            const carBrand = card.dataset.carBrand || '';
            const carModel = card.dataset.carModel || '';
            const description = card.dataset.description || '';
            const stationName = card.dataset.stationName || '';

            searchMatch = clientName.includes(searchQuery) ||
                          carBrand.includes(searchQuery) ||
                          carModel.includes(searchQuery) ||
                          description.includes(searchQuery) ||
                          stationName.includes(searchQuery);
        }

        if (statusMatch && searchMatch) {
            card.classList.remove('d-none');
            visibleCount++;
        } else {
            card.classList.add('d-none');
        }
    });

    if (noRequests) {
        if (visibleCount === 0) {
            noRequests.classList.remove('d-none');
        } else {
            noRequests.classList.add('d-none');
        }
    }
}

// Перехоплення зміни статусу на "Виконано" для відображення вікна завершення ремонту
function handleStatusSubmit(form, event) {
    const statusSelect = form.querySelector('.status-select-element');
    if (statusSelect && statusSelect.value === 'completed') {
        event.preventDefault();
        const bookingId = form.querySelector('input[name="booking_id"]').value;
        const modal = document.getElementById('completeBookingModal');
        if (modal) {
            const hiddenIdInput = document.getElementById('complete_booking_id');
            if (hiddenIdInput) {
                hiddenIdInput.value = bookingId;
            }
            modal.classList.add('active');
        }
        return false;
    }
    return true;
}

// Закриття модального вікна завершення ремонту
function closeCompleteModal() {
    const modal = document.getElementById('completeBookingModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Допоміжна функція затримки виклику (debounce)
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    if (tab) {
        const btn = Array.from(document.querySelectorAll('button[onclick]')).find(b => {
            const onclickAttr = b.getAttribute('onclick') || '';
            const match = onclickAttr.match(/showSection\(\s*'([^']+)'/);
            return match && match[1] === tab;
        });
        if (btn) {
            showSection(tab, btn);
        }
    } else if (params.has('edit_station') || params.get('action') === 'new_station') {
        const btn = document.querySelector(`button[onclick*="'station'"]`);
        if (btn) {
            showSection('station', btn);
        }
    }

    // Встановлення збереженого значення мови в селекторі
    const savedLang = localStorage.getItem('karro_lang') || 'uk';
    const profLangSelect = document.getElementById('profile-lang-select');
    if (profLangSelect) {
        profLangSelect.value = savedLang;
    }

    // Розрахунок початкової кількості заявок та налаштування пошуку
    updateTabCounts();

    const searchInput = document.getElementById('booking-search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce((e) => {
            searchQuery = e.target.value.toLowerCase().trim();
            applyFilters();
        }, 150));
    }
});