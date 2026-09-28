function showSection(name, button) {
    const panel = document.getElementById(`section-${name}`);
    if (!panel) return;

    document.querySelectorAll('.section-panel').forEach(item => {
        item.classList.toggle('active', item === panel);
    });
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item === button);
    });

    button?.scrollIntoView?.({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center'
    });

    if (name === 'calendar' && window.karroCalendar) {
        window.karroCalendar.render();
        window.karroCalendar.updateSize();
    }
}

function switchLang(lang) {
    const globalSelect = document.getElementById('lang-select');
    if (globalSelect) {
        globalSelect.value = lang;
        globalSelect.dispatchEvent(new Event('change'));
    } else {
        localStorage.setItem('karro_lang', lang);
        location.reload();
    }
}

let activeFilterStatus = 'all';
let searchQuery = '';

function updateTabCounts() {
    const counts = {
        pending: 0,
        confirmed: 0,
        completed: 0,
        cancelled: 0
    };

    document.querySelectorAll('.booking-card').forEach(card => {
        if (card.dataset.status in counts) counts[card.dataset.status]++;
    });

    Object.entries(counts).forEach(([status, count]) => {
        const label = document.querySelector(`.count-${status}`);
        if (label) label.textContent = count;
    });
}

function filterByStatus(status, button) {
    activeFilterStatus = status;

    document.querySelectorAll('.tab-filter-btn').forEach(item => {
        item.classList.toggle('active', item === button);
    });

    applyFilters();
}

function applyFilters() {
    let visibleCount = 0;

    document.querySelectorAll('.booking-card').forEach(card => {
        const fields = [
            card.dataset.clientName,
            card.dataset.carBrand,
            card.dataset.carModel,
            card.dataset.description,
            card.dataset.stationName
        ].join(' ').toLocaleLowerCase();

        const visible = (
            (activeFilterStatus === 'all' ||
                card.dataset.status === activeFilterStatus) &&
            fields.includes(searchQuery)
        );

        card.classList.toggle('d-none', !visible);
        if (visible) visibleCount++;
    });

    document.getElementById('no-requests')?.classList.toggle(
        'd-none',
        visibleCount > 0
    );
}

function handleStatusSubmit(form, event) {
    const status = form.querySelector('.status-select-element')?.value;
    if (status !== 'completed') return true;

    event.preventDefault();

    const bookingId = form.querySelector('[name="booking_id"]')?.value;
    const modal = document.getElementById('completeBookingModal');
    if (!bookingId || !modal) return false;

    selectedBookingParts = [];
    renderSelectedParts();

    const completionForm = modal.querySelector('form');
    if (completionForm) {
        completionForm.action = '/accounting/booking/complete/';
    }

    const idInput = document.getElementById('complete_booking_id');
    const workInput = document.getElementById('complete_work_list');

    if (idInput) idInput.value = bookingId;
    if (workInput) {
        workInput.value = (
            form.dataset.serviceName ||
            form.dataset.description ||
            ''
        );
    }

    modal.classList.add('active');
    return false;
}

function closeCompleteModal() {
    document.getElementById('completeBookingModal')?.classList.remove('active');
}

function toggleCarHistory(historyId) {
    document.getElementById(historyId)?.classList.toggle('d-none');
}

function csrfToken() {
    const input = document.querySelector('[name="csrfmiddlewaretoken"]');
    if (input) return input.value;

    const cookie = document.cookie.split('; ').find(item => {
        return item.startsWith('csrftoken=');
    });
    return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
}

async function jsonResponse(response) {
    const data = await response.json();
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || t('common.connection_error'));
    }
    return data;
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(location.search);
    const requestedTab = params.get('tab') ||
        (params.has('edit_station') || params.get('action') === 'new_station'
            ? 'station'
            : null);

    if (requestedTab) {
        const button = [...document.querySelectorAll('.nav-item')].find(item => {
            return item.getAttribute('onclick')?.includes(`'${requestedTab}'`);
        });
        if (button) showSection(requestedTab, button);
    }

    const languageSelect = document.getElementById('profile-lang-select');
    if (languageSelect) languageSelect.value = getLang();

    updateTabCounts();

    let searchTimer;
    document.getElementById('booking-search')?.addEventListener('input', event => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            searchQuery = event.target.value.trim().toLocaleLowerCase();
            applyFilters();
        }, 150);
    });

    const calendarElement = document.getElementById('calendar');
    const calendarPanel = document.getElementById('section-calendar');
    const stationId = calendarPanel?.dataset.stationId;

    if (calendarElement && stationId && typeof FullCalendar !== 'undefined') {
        const calendar = new FullCalendar.Calendar(calendarElement, {
            initialView: 'timeGridWeek',
            locale: getLang() === 'en' ? 'en' : 'uk',
            slotMinTime: '08:00',
            slotMaxTime: '20:00',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            buttonText: getLang() === 'en'
                ? { today: 'Today', month: 'Month', week: 'Week', day: 'Day' }
                : { today: 'Сьогодні', month: 'Місяць', week: 'Тиждень', day: 'День' },
            editable: true,
            eventSources: [{
                url: `/api/stations/${encodeURIComponent(stationId)}/calendar-events/`,
                failure: () => alert(t('cal.load_error'))
            }],
            eventDrop: async info => {
                const dateText = info.event.start.toLocaleString(
                    getLang() === 'en' ? 'en-US' : 'uk-UA'
                );

                if (!confirm(`${t('cal.confirm_move')} ${dateText}?`)) {
                    info.revert();
                    return;
                }

                try {
                    const response = await fetch(
                        `/api/bookings/${encodeURIComponent(info.event.id)}/reschedule/`,
                        {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': csrfToken()
                            },
                            body: JSON.stringify({
                                scheduled_time: info.event.start.toISOString()
                            })
                        }
                    );
                    const data = await jsonResponse(response);
                    alert(data.message);
                    calendar.refetchEvents();
                } catch (error) {
                    info.revert();
                    alert(error.message);
                }
            },
            eventClick: info => {
                const props = info.event.extendedProps;
                alert(
                    `${t('cal.booking')} #${info.event.id}\n` +
                    `${t('common.client')}: ${props.clientName}\n` +
                    `${t('common.car')}: ${props.car}\n` +
                    `${t('acc.tbl_desc')}: ${props.description}\n` +
                    `${t('inv.th_status')}: ${props.status}\n` +
                    `${t('cal.box')}: ${props.boxName}`
                );
            }
        });

        window.karroCalendar = calendar;
        if (calendarPanel.classList.contains('active')) calendar.render();
    }

    const completionForm = document.getElementById('completeBookingModal')
        ?.querySelector('form');

    completionForm?.addEventListener('submit', event => {
        renderSelectedParts();

        const priceInput = completionForm.querySelector(
            '[name="total_price"], [name="actual_price"]'
        );
        const price = Number(priceInput?.value);
        if (!Number.isFinite(price) || price <= 0) {
            event.preventDefault();
            alert(getLang() === 'en'
                ? 'Enter a valid repair price.'
                : 'Вкажіть коректну вартість ремонту.');
            return;
        }

        const totalPrice = completionForm.querySelector('[name="total_price"]');
        const actualPrice = completionForm.querySelector('[name="actual_price"]');

        if (!totalPrice || !actualPrice) {
            const hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.name = totalPrice ? 'actual_price' : 'total_price';
            hidden.value = priceInput.value;
            completionForm.appendChild(hidden);
        }
    });
});

let selectedBookingParts = [];

function openAddPartModal() {
    document.getElementById('addSparePartModal')?.classList.add('active');
}

function closeAddPartModal() {
    document.getElementById('addSparePartModal')?.classList.remove('active');
}

function openEditPartModal(id, name, sku, qty, costPrice, sellingPrice, minQty) {
    const modal = document.getElementById('editSparePartModal');
    if (!modal) return;

    const values = {
        edit_part_id: id,
        edit_part_name: name,
        edit_part_sku: sku,
        edit_part_quantity: qty,
        edit_part_cost_price: costPrice,
        edit_part_selling_price: sellingPrice,
        edit_part_min_quantity: minQty
    };

    Object.entries(values).forEach(([elementId, value]) => {
        const input = document.getElementById(elementId);
        if (input) input.value = value ?? '';
    });

    modal.classList.add('active');
}

function closeEditPartModal() {
    document.getElementById('editSparePartModal')?.classList.remove('active');
}

function addPartToBooking() {
    const select = document.getElementById('complete_part_select');
    const quantityInput = document.getElementById('complete_part_qty');
    if (!select?.value || !quantityInput) return;

    const option = select.selectedOptions[0];
    const partId = Number(select.value);
    const quantity = Number(quantityInput.value);
    const stock = Number(option.dataset.stock);
    const price = Number(option.dataset.price) || 0;

    if (!Number.isInteger(partId) || !Number.isInteger(quantity) ||
        quantity < 1 || !Number.isInteger(stock) || stock < 0) {
        alert(getLang() === 'en'
            ? 'Enter a valid quantity.'
            : 'Вкажіть коректну кількість.');
        return;
    }

    const existing = selectedBookingParts.find(part => part.part_id === partId);
    if (quantity + (existing?.qty || 0) > stock) {
        alert(t('inv.only_stock').replace('{n}', stock));
        return;
    }

    if (existing) {
        existing.qty += quantity;
    } else {
        selectedBookingParts.push({
            part_id: partId,
            name: option.dataset.name || option.textContent,
            price,
            qty: quantity
        });
    }

    renderSelectedParts();
}

function removePartFromBooking(partId) {
    selectedBookingParts = selectedBookingParts.filter(part => {
        return part.part_id !== Number(partId);
    });
    renderSelectedParts();
}

function renderSelectedParts() {
    const container = document.getElementById('selected_parts_list');
    const jsonInput = document.getElementById('used_parts_json');

    if (jsonInput) {
        jsonInput.value = JSON.stringify(selectedBookingParts.map(part => ({
            part_id: part.part_id,
            qty: part.qty,
            quantity: part.qty
        })));
    }
    if (!container) return;

    container.replaceChildren();

    selectedBookingParts.forEach(part => {
        const row = document.createElement('div');
        row.className = 'selected-part-row';

        const label = document.createElement('span');
        label.textContent = (
            `${part.name} × ${part.qty} ` +
            `(${(part.price * part.qty).toFixed(2)} ${t('common.uah')})`
        );

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'selected-part-remove';
        removeButton.textContent = '×';
        removeButton.addEventListener('click', () => {
            removePartFromBooking(part.part_id);
        });

        row.append(label, removeButton);
        container.appendChild(row);
    });
}

let currentChatBookingId = null;
let chatPollingTimer = null;
let selectedChatPhotoFile = null;

function openBookingChat(bookingId) {
    closeBookingChat();
    currentChatBookingId = bookingId;

    const bookingLabel = document.getElementById('chat_booking_id');
    if (bookingLabel) bookingLabel.textContent = bookingId;

    document.getElementById('bookingChatModal')?.classList.add('active');

    const textInput = document.getElementById('chat_text_input');
    const costInput = document.getElementById('chat_proposed_cost');
    if (textInput) textInput.value = '';
    if (costInput) costInput.value = '';
    clearChatImagePreview();

    fetchBookingMessages();
    chatPollingTimer = setInterval(fetchBookingMessages, 4000);
}

function closeBookingChat() {
    document.getElementById('bookingChatModal')?.classList.remove('active');
    currentChatBookingId = null;

    if (chatPollingTimer) {
        clearInterval(chatPollingTimer);
        chatPollingTimer = null;
    }
}

async function fetchBookingMessages() {
    const bookingId = currentChatBookingId;
    if (!bookingId) return;

    try {
        const response = await fetch(
            `/api/bookings/${encodeURIComponent(bookingId)}/chat/`
        );
        const data = await jsonResponse(response);

        if (currentChatBookingId === bookingId) {
            renderBookingMessages(data.messages);
        }
    } catch (error) {
        console.error('Не вдалося завантажити чат:', error);
    }
}

function chatText(tag, className, text) {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = text;
    return element;
}

function renderBookingMessages(chatMessages) {
    const container = document.getElementById('chat_messages_container');
    if (!container) return;

    const atBottom = (
        container.scrollHeight - container.scrollTop <=
        container.clientHeight + 100
    );

    container.replaceChildren();

    if (!chatMessages?.length) {
        container.appendChild(chatText(
            'div',
            'chat-empty',
            t('chat.empty')
        ));
        return;
    }

    chatMessages.forEach(message => {
        const row = document.createElement('div');
        row.className = `chat-message-row ${message.is_me ? 'me' : 'other'}`;

        const senderLabel = message.sender_role === 'station'
            ? t('chat.from_station')
            : t('chat.from_client');

        row.appendChild(chatText(
            'div',
            'chat-sender-name',
            `${message.sender_name} (${senderLabel})`
        ));

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';

        if (message.text) {
            bubble.appendChild(chatText('div', 'chat-text', message.text));
        }

        if (message.image_url) {
            const image = document.createElement('img');
            image.className = 'chat-defect-photo';
            image.alt = '';
            image.src = message.image_url;
            image.addEventListener('click', () => {
                viewChatPhoto(message.image_url);
            });
            bubble.appendChild(image);
        }

        if (message.proposed_cost !== null) {
            const costCard = document.createElement('div');
            costCard.className = 'chat-cost-card';
            costCard.appendChild(chatText(
                'div',
                '',
                `${t('chat.extra_cost')}: +${message.proposed_cost} ${t('common.uah')}`
            ));

            const status = message.is_approved === true
                ? t('chat.approved')
                : message.is_approved === false
                    ? t('chat.declined')
                    : t('chat.pending');

            costCard.appendChild(chatText(
                'div',
                'chat-cost-status',
                `${t('inv.th_status')}: ${status}`
            ));

            if (!message.is_me && message.is_approved === null) {
                const actions = document.createElement('div');
                actions.className = 'chat-approval-actions';

                [
                    ['approve', 'btn-approve-cost', t('chat.approve_btn')],
                    ['decline', 'btn-decline-cost', t('chat.decline_btn')]
                ].forEach(([action, className, label]) => {
                    const button = chatText('button', className, label);
                    button.type = 'button';
                    button.addEventListener('click', () => {
                        respondCostApproval(message.id, action);
                    });
                    actions.appendChild(button);
                });

                costCard.appendChild(actions);
            }

            bubble.appendChild(costCard);
        }

        bubble.appendChild(chatText(
            'div',
            'chat-time-stamp',
            message.created_at || ''
        ));
        row.appendChild(bubble);
        container.appendChild(row);
    });

    if (atBottom) container.scrollTop = container.scrollHeight;
}

function handleChatPhotoSelected(input) {
    const file = input.files?.[0];
    if (!file) {
        clearChatImagePreview();
        return;
    }

    if (!file.type.startsWith('image/') || file.size > 3 * 1024 * 1024) {
        alert(getLang() === 'en'
            ? 'Choose an image smaller than 3 MB.'
            : 'Оберіть зображення розміром до 3 МБ.');
        clearChatImagePreview();
        return;
    }

    selectedChatPhotoFile = file;
    const reader = new FileReader();

    reader.onload = () => {
        if (selectedChatPhotoFile !== file) return;

        const preview = document.getElementById('chat_image_preview_img');
        const box = document.getElementById('chat_image_preview_box');

        if (preview) preview.src = reader.result;
        box?.classList.remove('d-none');
    };

    reader.readAsDataURL(file);
}

function clearChatImagePreview() {
    selectedChatPhotoFile = null;

    const input = document.getElementById('chat_photo_input');
    const preview = document.getElementById('chat_image_preview_img');

    if (input) input.value = '';
    if (preview) preview.removeAttribute('src');

    document.getElementById('chat_image_preview_box')
        ?.classList.add('d-none');
}

async function handleSendChatMessage(event) {
    event.preventDefault();

    const bookingId = currentChatBookingId;
    if (!bookingId) return;

    const textInput = document.getElementById('chat_text_input');
    const costInput = document.getElementById('chat_proposed_cost');
    const text = textInput?.value.trim() || '';
    const cost = costInput?.value.trim() || '';

    if (!text && !selectedChatPhotoFile && !cost) return;

    const formData = new FormData();
    formData.append('text', text);
    if (selectedChatPhotoFile) formData.append('image', selectedChatPhotoFile);
    if (cost) formData.append('proposed_cost', cost);

    try {
        const response = await fetch(
            `/api/bookings/${encodeURIComponent(bookingId)}/chat/`,
            {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken() },
                body: formData
            }
        );
        await jsonResponse(response);

        if (currentChatBookingId !== bookingId) return;

        if (textInput) textInput.value = '';
        if (costInput) costInput.value = '';
        clearChatImagePreview();
        fetchBookingMessages();
    } catch (error) {
        alert(error.message || t('chat.send_error'));
    }
}

async function respondCostApproval(messageId, action) {
    const formData = new FormData();
    formData.append('action', action);

    try {
        const response = await fetch(
            `/api/chat-message/${encodeURIComponent(messageId)}/approval/`,
            {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken() },
                body: formData
            }
        );
        await jsonResponse(response);
        fetchBookingMessages();
    } catch (error) {
        alert(error.message || t('chat.approval_error'));
    }
}

function viewChatPhoto(url) {
    const modal = document.getElementById('photoViewerModal');
    const image = document.getElementById('photo_viewer_img');

    if (modal && image) {
        image.src = url;
        modal.classList.add('active');
    }
}

function closePhotoViewer() {
    document.getElementById('photoViewerModal')?.classList.remove('active');

    const image = document.getElementById('photo_viewer_img');
    if (image) image.removeAttribute('src');
}

function toggleDayInputs(day) {
    const checkbox = document.getElementById(`is_working_${day}`);
    const row = document.getElementById(`inputs_row_${day}`);
    const badge = document.getElementById(`status_badge_${day}`);
    if (!checkbox || !row) return;

    row.style.opacity = checkbox.checked ? '1' : '0.4';
    row.style.pointerEvents = checkbox.checked ? 'auto' : 'none';

    if (badge) {
        badge.style.background = checkbox.checked ? '#10b981' : '#ef4444';
        badge.textContent = checkbox.checked
            ? t('sched.working')
            : t('st.day_off');
    }
}

function copyMondayScheduleToWeekdays() {
    const monday = document.getElementById('is_working_0');
    if (!monday) return;

    for (let day = 1; day <= 4; day++) {
        const checkbox = document.getElementById(`is_working_${day}`);
        if (checkbox) checkbox.checked = monday.checked;

        [
            'opening_time',
            'closing_time',
            'break_start',
            'break_end'
        ].forEach(field => {
            const source = document.getElementById(`${field}_0`);
            const target = document.getElementById(`${field}_${day}`);
            if (source && target) target.value = source.value;
        });

        toggleDayInputs(day);
    }
}