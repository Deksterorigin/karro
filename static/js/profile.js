function showSection(name, btn) {
    document.querySelectorAll('.section-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById('section-' + name);
    if (panel) panel.classList.add('active');
    if (btn) btn.classList.add('active');

    // Якщо відкрили календар, оновлюємо його розміри
    if (name === 'calendar' && window.karroCalendar) {
        window.karroCalendar.render();
    }
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

    // Перемикаємо активний клас для кнопок фільтрації статусу
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
            const workInput = document.getElementById('complete_work_list');
            if (workInput) {
                const serviceName = form.getAttribute('data-service-name') || '';
                const description = form.getAttribute('data-description') || '';
                workInput.value = serviceName || description || '';
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

// Перемикач видимості історії обслуговування авто
function toggleCarHistory(historyId) {
    const container = document.getElementById(historyId);
    if (container) {
        container.classList.toggle('d-none');
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

    // Ініціалізація FullCalendar
    const calendarEl = document.getElementById('calendar');
    const calendarPanel = document.getElementById('section-calendar');
    if (calendarEl && calendarPanel) {
        const stationId = calendarPanel.getAttribute('data-station-id');
        if (stationId) {
            const calendar = new FullCalendar.Calendar(calendarEl, {
                initialView: 'timeGridWeek',
                locale: 'uk',
                slotMinTime: '08:00',
                slotMaxTime: '20:00',
                headerToolbar: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay'
                },
                buttonText: {
                    today: 'Сьогодні',
                    month: 'Місяць',
                    week: 'Тиждень',
                    day: 'День'
                },
                editable: true, // дозволяє drag-and-drop
                eventSources: [
                    {
                        url: `/api/stations/${stationId}/calendar-events/`,
                        method: 'GET',
                        failure: function() {
                            alert('Помилка завантаження замовлень для календаря');
                        }
                    }
                ],
                eventDrop: function(info) {
                    // Користувач перетягнув замовлення
                    if (!confirm(`Перенести замовлення на ${info.event.start.toLocaleString('uk-UA')}?`)) {
                        info.revert();
                        return;
                    }

                    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                    const bookingId = info.event.id;
                    const newStart = info.event.start.toISOString();

                    fetch(`/api/bookings/${bookingId}/reschedule/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({
                            scheduled_time: newStart
                        })
                    })
                    .then(response => response.json().then(data => {
                        if (!response.ok) throw new Error(data.message || 'Помилка при перенесенні');
                        return data;
                    }))
                    .then(data => {
                        alert(data.message);
                        calendar.refetchEvents();
                    })
                    .catch(error => {
                        alert(error.message);
                        info.revert();
                    });
                },
                eventClick: function(info) {
                    const props = info.event.extendedProps;
                    alert(`Замовлення #${info.event.id}\nКлієнт: ${props.clientName}\nАвтомобіль: ${props.car}\nПослуга: ${info.event.title.split(' - ').slice(-1)[0]}\nОпис: ${props.description}\nСтатус: ${props.status}\nБокс: ${props.boxName}`);
                }
            });

            window.karroCalendar = calendar;
            
            // Якщо вкладка календаря вже відкрита при завантаженні
            if (calendarPanel.classList.contains('active')) {
                calendar.render();
            }
        }
    }
});

// Змінна для збереження вибраних запчастин при завершенні ремонту
let selectedBookingParts = [];

function openAddPartModal() {
    const modal = document.getElementById('addSparePartModal');
    if (modal) modal.classList.add('active');
}

function closeAddPartModal() {
    const modal = document.getElementById('addSparePartModal');
    if (modal) modal.classList.remove('active');
}

function openEditPartModal(id, name, sku, qty, costPrice, sellingPrice, minQty) {
    const modal = document.getElementById('editSparePartModal');
    if (modal) {
        document.getElementById('edit_part_id').value = id;
        document.getElementById('edit_part_name').value = name;
        document.getElementById('edit_part_sku').value = sku;
        document.getElementById('edit_part_quantity').value = qty;
        document.getElementById('edit_part_cost_price').value = costPrice;
        document.getElementById('edit_part_selling_price').value = sellingPrice;
        document.getElementById('edit_part_min_quantity').value = minQty;
        modal.classList.add('active');
    }
}

function closeEditPartModal() {
    const modal = document.getElementById('editSparePartModal');
    if (modal) modal.classList.remove('active');
}

function addPartToBooking() {
    const select = document.getElementById('complete_part_select');
    const qtyInput = document.getElementById('complete_part_qty');
    if (!select || !select.value) return;

    const option = select.options[select.selectedIndex];
    const partId = parseInt(select.value);
    const partName = option.getAttribute('data-name');
    const price = parseFloat(option.getAttribute('data-price')) || 0;
    const stock = parseInt(option.getAttribute('data-stock')) || 0;
    const qty = parseInt(qtyInput.value) || 1;

    if (qty > stock) {
        alert(`На складі є лише ${stock} шт цієї деталі.`);
        return;
    }

    const existingIndex = selectedBookingParts.findIndex(p => p.part_id === partId);
    if (existingIndex >= 0) {
        selectedBookingParts[existingIndex].qty += qty;
    } else {
        selectedBookingParts.push({
            part_id: partId,
            name: partName,
            price: price,
            qty: qty
        });
    }

    renderSelectedParts();
}

function removePartFromBooking(partId) {
    selectedBookingParts = selectedBookingParts.filter(p => p.part_id !== partId);
    renderSelectedParts();
}

function renderSelectedParts() {
    const container = document.getElementById('selected_parts_list');
    const jsonInput = document.getElementById('used_parts_json');
    if (!container) return;

    container.innerHTML = '';
    if (selectedBookingParts.length === 0) {
        jsonInput.value = '[]';
        return;
    }

    jsonInput.value = JSON.stringify(selectedBookingParts);
    selectedBookingParts.forEach(p => {
        const itemDiv = document.createElement('div');
        itemDiv.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:#ffffff; border:1px solid var(--border-color); padding:4px 8px; border-radius:6px; margin-top:4px;';
        itemDiv.innerHTML = `
            <span><strong>${p.name}</strong> x${p.qty} (${p.price * p.qty} грн)</span>
            <button type="button" onclick="removePartFromBooking(${p.part_id})" style="background:none; border:none; color:#ef4444; cursor:pointer; font-size:1.1rem; line-height:1;">&times;</button>
        `;
        container.appendChild(itemDiv);
    });
}

/* ══ КЛІЄНТСЬКІ СКРИПТИ ЧАТУ ЗАМОВЛЕННЯ ══ */
let currentChatBookingId = null;
let chatPollingTimer = null;
let selectedChatPhotoFile = null;

function openBookingChat(bookingId) {
    currentChatBookingId = bookingId;
    const bIdSpan = document.getElementById('chat_booking_id');
    if (bIdSpan) bIdSpan.textContent = bookingId;

    const modal = document.getElementById('bookingChatModal');
    if (modal) modal.classList.add('active');

    // Очищаємо інпути
    const textInput = document.getElementById('chat_text_input');
    if (textInput) textInput.value = '';
    const costInput = document.getElementById('chat_proposed_cost');
    if (costInput) costInput.value = '';
    clearChatImagePreview();

    // Отримуємо повідомлення
    fetchBookingMessages();

    // Запускаємо авто-полінг раз на 4 сек
    if (chatPollingTimer) clearInterval(chatPollingTimer);
    chatPollingTimer = setInterval(fetchBookingMessages, 4000);
}

function closeBookingChat() {
    const modal = document.getElementById('bookingChatModal');
    if (modal) modal.classList.remove('active');
    currentChatBookingId = null;
    if (chatPollingTimer) {
        clearInterval(chatPollingTimer);
        chatPollingTimer = null;
    }
}

function fetchBookingMessages() {
    if (!currentChatBookingId) return;

    fetch(`/api/bookings/${currentChatBookingId}/chat/`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                renderBookingMessages(data.messages);
            }
        })
        .catch(err => console.error('Error fetching chat messages:', err));
}

function renderBookingMessages(messages) {
    const container = document.getElementById('chat_messages_container');
    if (!container) return;

    if (!messages || messages.length === 0) {
        container.innerHTML = '<div style="text-align:center; color: var(--text-muted); font-size:0.85rem; margin-top:2rem;">Немає повідомлень. Почніть діалог!</div>';
        return;
    }

    const isAtBottom = (container.scrollHeight - container.scrollTop <= container.clientHeight + 100);

    let html = '';
    messages.forEach(msg => {
        const alignClass = msg.is_me ? 'me' : 'other';
        const senderBadge = msg.sender_role === 'station' ? '🔧 СТО / Механік' : '👤 Клієнт';

        let imageHtml = '';
        if (msg.image_url) {
            imageHtml = `<img src="${msg.image_url}" alt="Дефект" class="chat-defect-photo" onclick="viewChatPhoto('${msg.image_url}')">`;
        }

        let costHtml = '';
        if (msg.proposed_cost) {
            let statusText = '';
            if (msg.is_approved === true) {
                statusText = '<span style="color:#10b981; font-weight:bold;">✅ Узгоджено</span>';
            } else if (msg.is_approved === false) {
                statusText = '<span style="color:#ef4444; font-weight:bold;">❌ Відхилено</span>';
            } else {
                statusText = '<span style="color:#f59e0b; font-weight:bold;">⏳ Очікує узгодження</span>';
            }

            let actionButtons = '';
            if (!msg.is_me && msg.is_approved === null) {
                actionButtons = `
                    <div class="chat-approval-actions">
                        <button type="button" class="btn-approve-cost" onclick="respondCostApproval(${msg.id}, 'approve')">Підтвердити</button>
                        <button type="button" class="btn-decline-cost" onclick="respondCostApproval(${msg.id}, 'decline')">Відхилити</button>
                    </div>
                `;
            }

            costHtml = `
                <div class="chat-cost-card">
                    <div>Додаткові роботи / деталі: <strong>+${msg.proposed_cost} грн</strong></div>
                    <div style="margin-top:2px;">Статус: ${statusText}</div>
                    ${actionButtons}
                </div>
            `;
        }

        html += `
            <div class="chat-message-row ${alignClass}">
                <div class="chat-sender-name">${escapeHtml(msg.sender_name)} (${senderBadge})</div>
                <div class="chat-bubble">
                    ${msg.text ? `<div>${escapeHtml(msg.text)}</div>` : ''}
                    ${imageHtml}
                    ${costHtml}
                    <div class="chat-time-stamp">${msg.created_at}</div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;

    if (isAtBottom) {
        container.scrollTop = container.scrollHeight;
    }
}

function handleChatPhotoSelected(input) {
    if (input.files && input.files[0]) {
        selectedChatPhotoFile = input.files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('chat_image_preview_img').src = e.target.result;
            document.getElementById('chat_image_preview_box').classList.remove('d-none');
        };
        reader.readAsDataURL(selectedChatPhotoFile);
    }
}

function clearChatImagePreview() {
    selectedChatPhotoFile = null;
    const fileInput = document.getElementById('chat_photo_input');
    if (fileInput) fileInput.value = '';
    const previewBox = document.getElementById('chat_image_preview_box');
    if (previewBox) previewBox.classList.add('d-none');
}

function handleSendChatMessage(event) {
    event.preventDefault();
    if (!currentChatBookingId) return;

    const textInput = document.getElementById('chat_text_input');
    const text = textInput ? textInput.value.trim() : '';

    const costInput = document.getElementById('chat_proposed_cost');
    const proposedCost = costInput ? costInput.value.trim() : '';

    if (!text && !selectedChatPhotoFile && !proposedCost) {
        return;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const formData = new FormData();
    formData.append('text', text);
    if (selectedChatPhotoFile) {
        formData.append('image', selectedChatPhotoFile);
    }
    if (proposedCost) {
        formData.append('proposed_cost', proposedCost);
    }

    fetch(`/api/bookings/${currentChatBookingId}/chat/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            textInput.value = '';
            if (costInput) costInput.value = '';
            clearChatImagePreview();
            fetchBookingMessages();
        } else {
            alert(data.message || 'Помилка надсилання повідомлення');
        }
    })
    .catch(err => {
        console.error('Error sending message:', err);
        alert('Помилка з\'єднання з сервером.');
    });
}

function respondCostApproval(messageId, action) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const formData = new FormData();
    formData.append('action', action);

    fetch(`/api/chat-message/${messageId}/approval/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            fetchBookingMessages();
        } else {
            alert(data.message || 'Помилка при узгодженні');
        }
    });
}

function viewChatPhoto(url) {
    const modal = document.getElementById('photoViewerModal');
    const img = document.getElementById('photo_viewer_img');
    if (modal && img) {
        img.src = url;
        modal.classList.add('active');
    }
}

function closePhotoViewer() {
    const modal = document.getElementById('photoViewerModal');
    if (modal) modal.classList.remove('active');
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Перемикач активності дня у графіку роботи
function toggleDayInputs(dayNum) {
    const checkbox = document.getElementById('is_working_' + dayNum);
    const row = document.getElementById('inputs_row_' + dayNum);
    const badge = document.getElementById('status_badge_' + dayNum);

    if (!checkbox || !row) return;

    if (checkbox.checked) {
        row.style.opacity = '1';
        row.style.pointerEvents = 'auto';
        if (badge) {
            badge.style.background = '#10b981';
            badge.textContent = 'Робочий';
        }
    } else {
        row.style.opacity = '0.4';
        row.style.pointerEvents = 'none';
        if (badge) {
            badge.style.background = '#ef4444';
            badge.textContent = 'Вихідний';
        }
    }
}

// Скопіювати розклад понеділка на всі будні дні (Пн - Пт)
function copyMondayScheduleToWeekdays() {
    const monCheck = document.getElementById('is_working_0');
    if (!monCheck) return;

    const isMonWorking = monCheck.checked;
    const monOpen = document.getElementById('opening_time_0').value;
    const monClose = document.getElementById('closing_time_0').value;
    const monBreakStart = document.getElementById('break_start_0').value;
    const monBreakEnd = document.getElementById('break_end_0').value;

    for (let day = 1; day <= 4; day++) {
        const check = document.getElementById('is_working_' + day);
        if (check) check.checked = isMonWorking;
        
        const open = document.getElementById('opening_time_' + day);
        if (open) open.value = monOpen;

        const close = document.getElementById('closing_time_' + day);
        if (close) close.value = monClose;

        const bStart = document.getElementById('break_start_' + day);
        if (bStart) bStart.value = monBreakStart;

        const bEnd = document.getElementById('break_end_' + day);
        if (bEnd) bEnd.value = monBreakEnd;

        toggleDayInputs(day);
    }
}