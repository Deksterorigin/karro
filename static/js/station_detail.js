document.addEventListener('DOMContentLoaded', function() {
    /* ── Star picker ── */
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
                l.style.color = r <= n ? 'var(--accent)' : 'var(--border-hover)';
            });
        }
    }

    /* ── Photo upload show button ── */
    const photoInput = document.getElementById('photo-input');
    const uploadBtn = document.getElementById('upload-btn');
    if (photoInput && uploadBtn) {
        photoInput.addEventListener('change', () => {
            if (photoInput.files.length > 0) {
                uploadBtn.style.display = 'inline-block';
            }
        });
    }

    /* ── Mini map ── */
    const mapContainer = document.getElementById('station-map');
    if (mapContainer && mapContainer.dataset.lat && mapContainer.dataset.lng) {
        const lat = parseFloat(mapContainer.dataset.lat);
        const lng = parseFloat(mapContainer.dataset.lng);
        const name = mapContainer.dataset.name;
        const address = mapContainer.dataset.address;

        const map = L.map('station-map', { zoomControl: false, scrollWheelZoom: false }).setView([lat, lng], 15);

        // Light theme Voyager tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        }).addTo(map);

        // Premium light brand blue pin marker
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

        L.marker([lat, lng], { icon: pinIcon }).addTo(map).bindPopup(`
            <div style="font-family: 'Inter', sans-serif; padding: 4px;">
                <div style="font-weight: 700; font-size: 0.9rem; color: var(--text);">${name}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${address}</div>
            </div>
        `).openPopup();

        setTimeout(() => {
            map.invalidateSize();
        }, 250);
    }

    /* ── Booking Modal & AJAX ── */
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
        const bookingTimeWarning = document.getElementById('bookingTimeWarning');
        const submitBtn = document.getElementById('submitBookingBtn');
        const bookingCarSelect = document.getElementById('bookingCar');
        const bookingServiceInput = document.getElementById('bookingService');

        // Робочі години СТО
        const openingTimeStr = bookingForm.getAttribute('data-opening');
        const closingTimeStr = bookingForm.getAttribute('data-closing');

        // Валідація обраного часу візиту відповідно до робочих годин
        function validateBookingTime() {
            if (!bookingTimeInput.value) {
                bookingTimeWarning.style.display = 'none';
                submitBtn.disabled = false;
                return true;
            }

            const selectedDateTime = new Date(bookingTimeInput.value);
            const hours = String(selectedDateTime.getHours()).padStart(2, '0');
            const minutes = String(selectedDateTime.getMinutes()).padStart(2, '0');
            const selectedTimeStr = `${hours}:${minutes}`;

            if (selectedTimeStr < openingTimeStr || selectedTimeStr > closingTimeStr) {
                bookingTimeWarning.style.display = 'block';
                submitBtn.disabled = true;
                return false;
            } else {
                bookingTimeWarning.style.display = 'none';
                submitBtn.disabled = false;
                return true;
            }
        }

        bookingTimeInput.addEventListener('change', validateBookingTime);
        bookingTimeInput.addEventListener('input', validateBookingTime);

        // Відправка форми через AJAX
        bookingForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            if (!validateBookingTime()) {
                return;
            }

            const stationId = openBtn.getAttribute('data-station-id');
            const description = document.getElementById('bookingDescription').value;
            const scheduledTime = document.getElementById('bookingTime').value;
            const carId = bookingCarSelect ? bookingCarSelect.value : null;
            const serviceName = bookingServiceInput ? bookingServiceInput.value : '';
            const csrfToken = bookingForm.querySelector('[name=csrfmiddlewaretoken]').value;

            const data = {
                station_id: stationId,
                car_id: carId,
                service_name: serviceName,
                description: description,
                scheduled_time: scheduledTime
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
            })
            .catch(error => {
                alert(error.message);
            });
        });
    }
});
