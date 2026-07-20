document.addEventListener('DOMContentLoaded', function() {
    /* Вибір зірочок для оцінки відгуку */
    const picker = document.getElementById('star-picker');
    const ratingInput = document.getElementById('rating-value');

    if (picker && ratingInput) {
        const labels = picker.querySelectorAll('label');
        let currentRating = 5;
        updateStars(currentRating);

        labels.forEach(label => {
            const rating = parseInt(label.dataset.rating);

            label.addEventListener('click', () => {
                currentRating = rating;
                ratingInput.value = rating;
                updateStars(rating);
            });

            label.addEventListener('mouseenter', () => updateStars(rating));
        });

        picker.addEventListener('mouseleave', () => updateStars(currentRating));

        function updateStars(n) {
            labels.forEach(l => {
                const r = parseInt(l.dataset.rating);
                l.style.color = r <= n ? '#F59E0B' : 'var(--border-hover)';
            });
        }
    }

    /* Кнопка завантаження фотографії СТО */
    const photoInput = document.getElementById('photo-input');
    const uploadBtn = document.getElementById('upload-btn');
    if (photoInput && uploadBtn) {
        photoInput.addEventListener('change', () => {
            if (photoInput.files.length > 0) {
                uploadBtn.style.display = 'inline-block';
            }
        });
    }

    /* Міні-карта розташування СТО */
    const mapContainer = document.getElementById('station-map');
    if (mapContainer && mapContainer.dataset.lat && mapContainer.dataset.lng) {
        const lat = parseFloat(mapContainer.dataset.lat);
        const lng = parseFloat(mapContainer.dataset.lng);
        const name = mapContainer.dataset.name;
        const address = mapContainer.dataset.address;

        // Функція екранування HTML для захисту від XSS
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        const map = L.map('station-map', { zoomControl: false, scrollWheelZoom: false }).setView([lat, lng], 15);

        // Світла тема карти Voyager
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        }).addTo(map);

        // Брендований синій маркер для СТО
        const pinIcon = L.divIcon({
            html: `
                <svg viewBox="0 0 24 24" width="32" height="32" fill="none" style="filter: drop-shadow(0 4px 8px rgba(0,82,204,0.25));">
                    <path d="M12 2C8.13 2 5 5.13 5 9C5 14.25 12 22 12 22S19 14.25 19 9C19 5.13 15.87 2 12 2Z" fill="#0052CC" stroke="#ffffff" stroke-width="1.5"/>
                    <circle cx="12" cy="9" r="3" fill="#ffffff"/>
                </svg>
            `,
            className: 'custom-pin-marker',
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32]
        });

        // Безпечно виводимо дані СТО в попапі на карті
        L.marker([lat, lng], { icon: pinIcon }).addTo(map).bindPopup(`
            <div style="font-family: 'Inter', sans-serif; padding: 4px;">
                <div style="font-weight: 700; font-size: 0.9rem; color: var(--text);">${escapeHtml(name)}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(address)}</div>
            </div>
        `).openPopup();

        setTimeout(() => {
            map.invalidateSize();
        }, 250);
    }

    /* Модальне вікно створення заявки та AJAX-запит */
    const openBtn = document.getElementById('openBookingModalBtn');
    const closeBtn = document.getElementById('closeBookingModalBtn');
    const modal = document.getElementById('bookingModal');
    const bookingForm = document.getElementById('bookingForm');

    if (openBtn && modal && bookingForm) {
        // Відкриття модалки
        openBtn.addEventListener('click', () => {
            modal.classList.add('active');
        });

        // Закриття модалки
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
        });

        // Закриття при кліку поза формою
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });

        const bookingTimeInput = document.getElementById('bookingTime');
        const bookingDateInput = document.getElementById('bookingDate');
        const bookingDurationSelect = document.getElementById('bookingDuration');
        const slotsGrid = document.getElementById('slotsGrid');
        const submitBtn = document.getElementById('submitBookingBtn');
        const bookingCarSelect = document.getElementById('bookingCar');
        const bookingServiceInput = document.getElementById('bookingService');

        // Встановлення мінімальної дати для вибору (сьогодні)
        if (bookingDateInput) {
            const today = new Date().toISOString().split('T')[0];
            bookingDateInput.min = today;
        }

        // Функція оновлення доступних слотів
        function fetchAvailableSlots() {
            const date = bookingDateInput.value;
            const duration = bookingDurationSelect.value;
            const stationId = openBtn.getAttribute('data-station-id');

            if (!date) {
                slotsGrid.innerHTML = '<span class="info-text">Будь ласка, оберіть дату для пошуку вільних слотів.</span>';
                submitBtn.disabled = true;
                bookingTimeInput.value = '';
                return;
            }

            slotsGrid.innerHTML = '<span class="info-text">Завантаження слотів...</span>';
            submitBtn.disabled = true;
            bookingTimeInput.value = '';

            fetch(`/api/stations/${stationId}/available-slots/?date=${date}&duration=${duration}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        if (data.slots && data.slots.length > 0) {
                            slotsGrid.innerHTML = '';
                            data.slots.forEach(slot => {
                                const btn = document.createElement('button');
                                btn.type = 'button';
                                btn.className = 'slot-btn';
                                btn.textContent = slot;
                                btn.addEventListener('click', () => {
                                    // Знімаємо клас active з інших кнопок
                                    slotsGrid.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('active'));
                                    btn.classList.add('active');
                                    // Записуємо повну дату та час
                                    bookingTimeInput.value = `${date}T${slot}`;
                                    submitBtn.disabled = false;
                                });
                                slotsGrid.appendChild(btn);
                            });
                        } else {
                            slotsGrid.innerHTML = '<span class="info-text" style="color: var(--error);">Немає вільних боксів на цю дату. Оберіть іншу.</span>';
                        }
                    } else {
                        slotsGrid.innerHTML = `<span class="info-text" style="color: var(--error);">${data.message || 'Помилка завантаження слотів'}</span>`;
                    }
                })
                .catch(err => {
                    slotsGrid.innerHTML = '<span class="info-text" style="color: var(--error);">Помилка підключення до сервера</span>';
                });
        }

        if (bookingDateInput && bookingDurationSelect) {
            bookingDateInput.addEventListener('change', fetchAvailableSlots);
            bookingDurationSelect.addEventListener('change', fetchAvailableSlots);
        }

        // Відправка форми через AJAX
        bookingForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            if (!bookingTimeInput.value) {
                alert('Будь ласка, оберіть час візиту зі списку вільних слотів.');
                return;
            }

            const stationId = openBtn.getAttribute('data-station-id');
            const description = document.getElementById('bookingDescription').value;
            const scheduledTime = bookingTimeInput.value;
            const duration = bookingDurationSelect.value;
            const carId = bookingCarSelect ? bookingCarSelect.value : null;
            const serviceName = bookingServiceInput ? bookingServiceInput.value : '';
            const csrfToken = bookingForm.querySelector('[name=csrfmiddlewaretoken]').value;

            const data = {
                station_id: stationId,
                car_id: carId,
                service_name: serviceName,
                description: description,
                scheduled_time: scheduledTime,
                duration: duration
            };

            fetch('/api/bookings/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            })
            .then(response => {
                if (response.status === 401) {
                    throw new Error('Будь ласка, авторизуйтесь для запису на СТО.');
                }
                return response.json().then(res => {
                    if (!response.ok) throw new Error(res.message || 'Помилка сервера');
                    return res;
                });
            })
            .then(data => {
                alert(data.message);
                modal.classList.remove('active');
                bookingForm.reset();
                if (slotsGrid) {
                    slotsGrid.innerHTML = '<span class="info-text">Будь ласка, оберіть дату для пошуку вільних слотів.</span>';
                }
            })
            .catch(error => {
                alert(error.message);
            });
        });
    }
});
