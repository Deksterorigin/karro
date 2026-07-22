let map;
let markers = {};

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function requestUserLocation() {
    const btnNearby = document.getElementById('btnNearby');
    if (!navigator.geolocation) {
        alert('Ваш браузер не підтримує геолокацію.');
        return;
    }

    if (btnNearby) {
        btnNearby.textContent = 'Визначення...';
        btnNearby.disabled = true;
    }

    function handleSuccess(pos) {
        const latInput = document.getElementById('userLat');
        const lngInput = document.getElementById('userLng');
        if (latInput && lngInput) {
            latInput.value = pos.coords.latitude;
            lngInput.value = pos.coords.longitude;
        }
        const searchForm = document.getElementById('searchForm');
        if (searchForm) {
            searchForm.submit();
        }
    }

    function handleFallback() {
        navigator.geolocation.getCurrentPosition(
            handleSuccess,
            err => {
                let msg = 'Неможливо отримати геолокацію.';
                if (err.code === 1) {
                    msg = 'Будь ласка, дозвольте доступ до геопозиції у налаштуваннях браузера.';
                }
                alert(msg);
                if (btnNearby) {
                    btnNearby.textContent = 'Поруч';
                    btnNearby.disabled = false;
                }
            },
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 }
        );
    }

    navigator.geolocation.getCurrentPosition(
        handleSuccess,
        handleFallback,
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 300000 }
    );
}

function initMap() {
    map = L.map('map', { zoomControl: true }).setView([49.0, 31.5], 6);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);

    const bounds = [];

    if (typeof USER_LAT !== 'undefined' && USER_LAT && typeof USER_LNG !== 'undefined' && USER_LNG) {
        const userIcon = L.divIcon({
            html: `
                <div style="position:relative; width:24px; height:24px;">
                    <div style="position:absolute; width:24px; height:24px; border-radius:50%; background:rgba(16,185,129,0.3);"></div>
                    <div style="position:absolute; top:4px; left:4px; width:16px; height:16px; border-radius:50%; background:#10B981; border:2px solid #FFFFFF; box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>
                </div>
            `,
            className: 'user-pin-marker',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });

        const userMarker = L.marker([USER_LAT, USER_LNG], { icon: userIcon }).addTo(map);
        userMarker.bindPopup('<div style="font-family:sans-serif; font-weight:700; font-size:0.85rem; color:#10B981;">Ви знаходитесь тут</div>');
        bounds.push([USER_LAT, USER_LNG]);
    }

    if (!STATIONS.length) {
        if (bounds.length) {
            map.setView(bounds[0], 12);
        }
        return;
    }

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

    STATIONS.forEach(s => {
        const marker = L.marker([s.lat, s.lng], { icon: pinIcon }).addTo(map);

        const escapedName = escapeHtml(s.name);
        const escapedCity = s.city ? escapeHtml(s.city) + ', ' : '';
        const escapedAddress = escapeHtml(s.address);
        const distStr = s.distance ? `<div style="color:#059669; font-weight:700; font-size:0.8rem; margin-top:2px;">Відстань: ${s.distance} км</div>` : '';

        marker.bindPopup(`
            <div style="font-family: 'Inter', sans-serif; min-width: 190px; padding: 4px;">
                <a href="/station/${s.id}/" style="font-weight: 700; font-size: 0.95rem; margin-bottom: 4px; color: var(--accent, #0052CC); text-decoration: none; display: block;">${escapedName} &rarr;</a>
                <div style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.3;">${escapedCity}${escapedAddress}</div>
                ${distStr}
                ${s.rating ? `<div style="margin-top: 6px; color: var(--accent); font-weight: 700; font-size: 0.85rem; display: flex; align-items: center; gap: 2px;">★ ${escapeHtml(String(s.rating))}</div>` : ''}
                <div style="margin-top: 10px;">
                    <a href="/station/${s.id}/" style="display: inline-block; font-size: 0.75rem; font-weight: 700; color: #ffffff; background: #0052CC; padding: 5px 12px; border-radius: 6px; text-decoration: none;">Переглянути СТО</a>
                </div>
            </div>
        `);

        marker.on('click', () => {
            highlightCard(s.id);
        });

        markers[s.id] = marker;
        bounds.push([s.lat, s.lng]);
    });

    if (bounds.length === 1) {
        map.setView(bounds[0], 14);
    } else if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [40, 40] });
    }
}

function focusMarker(id, lat, lng) {
    document.querySelectorAll('.station-card').forEach(c => c.classList.remove('active'));
    const card = document.getElementById('card-' + id);
    if (card) card.classList.add('active');

    if (lat !== null && lng !== null && markers[id]) {
        map.setView([parseFloat(lat), parseFloat(lng)], 15);
        markers[id].openPopup();
    }
}

function highlightCard(id) {
    document.querySelectorAll('.station-card').forEach(c => c.classList.remove('active'));
    const card = document.getElementById('card-' + id);
    if (card) {
        card.classList.add('active');
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    setTimeout(() => {
        if (map) {
            map.invalidateSize();
        }
    }, 250);
});