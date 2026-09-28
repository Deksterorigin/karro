document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('star-picker');
    const ratingInput = document.getElementById('rating-value');

    if (picker && ratingInput) {
        const labels = [...picker.querySelectorAll('label[data-rating]')];
        let rating = Number(ratingInput.value) || 5;

        function paintStars(value) {
            labels.forEach(label => {
                label.style.color = Number(label.dataset.rating) <= value
                    ? '#F59E0B'
                    : 'var(--border-hover)';
            });
        }

        paintStars(rating);
        labels.forEach(label => {
            label.addEventListener('click', () => {
                rating = Number(label.dataset.rating);
                ratingInput.value = rating;
                paintStars(rating);
            });
            label.addEventListener('mouseenter', () => {
                paintStars(Number(label.dataset.rating));
            });
        });
        picker.addEventListener('mouseleave', () => paintStars(rating));
    }

    const photoInput = document.getElementById('photo-input');
    const uploadButton = document.getElementById('upload-btn');
    photoInput?.addEventListener('change', () => {
        if (uploadButton) {
            uploadButton.style.display = photoInput.files.length
                ? 'inline-block'
                : 'none';
        }
    });

    const mapElement = document.getElementById('station-map');
    if (mapElement && typeof L !== 'undefined') {
        const lat = Number(mapElement.dataset.lat);
        const lng = Number(mapElement.dataset.lng);

        if (Number.isFinite(lat) && Number.isFinite(lng) &&
            Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
            const map = L.map(mapElement, {
                zoomControl: false,
                scrollWheelZoom: false
            }).setView([lat, lng], 15);

            L.tileLayer(
                'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
                {
                    maxZoom: 19,
                    subdomains: ['a', 'b', 'c'],
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Tiles &copy; <a href="https://www.hotosm.org/">HOT</a>'
                }
            ).addTo(map);

            const popup = document.createElement('div');
            const name = document.createElement('strong');
            const address = document.createElement('div');
            name.textContent = mapElement.dataset.name || '';
            address.textContent = mapElement.dataset.address || '';
            popup.append(name, address);

            L.marker([lat, lng]).addTo(map).bindPopup(popup).openPopup();
            setTimeout(() => map.invalidateSize(), 250);
        }
    }

    const openButton = document.getElementById('openBookingModalBtn');
    const modal = document.getElementById('bookingModal');
    const form = document.getElementById('bookingForm');
    if (!openButton || !modal || !form) return;

    const dateInput = document.getElementById('bookingDate');
    const timeInput = document.getElementById('bookingTime');
    const durationInput = document.getElementById('bookingDuration');
    const slotsGrid = document.getElementById('slotsGrid');
    const submitButton = document.getElementById('submitBookingBtn');
    const stationId = openButton.dataset.stationId;
    let slotsRequest = null;

    if (!dateInput || !timeInput || !durationInput ||
        !slotsGrid || !submitButton || !stationId) return;

    const today = new Date();
    dateInput.min = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, '0'),
        String(today.getDate()).padStart(2, '0')
    ].join('-');

    function showSlotMessage(text) {
        slotsGrid.replaceChildren();
        const label = document.createElement('span');
        label.className = 'info-text';
        label.textContent = text;
        slotsGrid.appendChild(label);
    }

    async function loadSlots() {
        slotsRequest?.abort();
        timeInput.value = '';
        submitButton.disabled = true;

        if (!dateInput.value) {
            showSlotMessage(t('st.pick_date_hint'));
            return;
        }

        const controller = new AbortController();
        slotsRequest = controller;
        showSlotMessage(t('st.loading_slots'));

        const params = new URLSearchParams({
            date: dateInput.value,
            duration: durationInput.value
        });

        try {
            const response = await fetch(
                `/api/stations/${encodeURIComponent(stationId)}/available-slots/?${params}`,
                { signal: controller.signal }
            );
            const data = await response.json();
            if (!response.ok || data.status !== 'success') {
                throw new Error(data.message || t('st.slots_error'));
            }

            if (slotsRequest !== controller) return;
            if (data.is_closed) {
                showSlotMessage(data.message || t('st.closed_day_msg'));
            } else if (!data.slots?.length) {
                showSlotMessage(t('st.no_slots_left'));
            } else {
                slotsGrid.replaceChildren();
                data.slots.forEach(slot => {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'slot-btn';
                    button.textContent = slot;
                    button.addEventListener('click', () => {
                        slotsGrid.querySelectorAll('.slot-btn').forEach(item => {
                            item.classList.remove('active');
                        });
                        button.classList.add('active');
                        timeInput.value = `${dateInput.value}T${slot}`;
                        submitButton.disabled = false;
                    });
                    slotsGrid.appendChild(button);
                });
            }
        } catch (error) {
            if (error.name !== 'AbortError' && slotsRequest === controller) {
                showSlotMessage(error.message || t('common.connection_error'));
            }
        }
    }

    openButton.addEventListener('click', () => modal.classList.add('active'));
    document.getElementById('closeBookingModalBtn')?.addEventListener(
        'click',
        () => modal.classList.remove('active')
    );
    modal.addEventListener('click', event => {
        if (event.target === modal) modal.classList.remove('active');
    });

    dateInput.addEventListener('change', loadSlots);
    durationInput.addEventListener('change', loadSlots);

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!timeInput.value) {
            alert(t('st.pick_slot_alert'));
            return;
        }

        submitButton.disabled = true;
        const csrf = form.querySelector('[name="csrfmiddlewaretoken"]')?.value;
        const data = {
            station_id: stationId,
            car_id: document.getElementById('bookingCar')?.value || '',
            service_name: document.getElementById('bookingService')?.value || '',
            description: document.getElementById('bookingDescription')?.value || '',
            scheduled_time: timeInput.value,
            duration: durationInput.value
        };

        try {
            const response = await fetch('/api/bookings/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf || ''
                },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (!response.ok || result.status !== 'success') {
                throw new Error(
                    result.message ||
                    (response.status === 401
                        ? t('st.login_required')
                        : t('st.server_error'))
                );
            }

            alert(result.message);
            modal.classList.remove('active');
            form.reset();
            timeInput.value = '';
            showSlotMessage(t('st.pick_date_hint'));
        } catch (error) {
            alert(error.message || t('common.connection_error'));
        } finally {
            submitButton.disabled = !timeInput.value;
        }
    });
});
