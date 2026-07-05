let map;
let markers = {};

// FIX (SEC-04): Функція екранування HTML для захисту від XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initMap() {
    // Center of Ukraine with standard zoom
    map = L.map('map', { zoomControl: true }).setView([49.0, 31.5], 6);

    // Switch to Voyager tile style (light theme)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);

    if (!STATIONS.length) return;

    const bounds = [];

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

    STATIONS.forEach(s => {
        const marker = L.marker([s.lat, s.lng], { icon: pinIcon }).addTo(map);

        // FIX (SEC-04): Екранування всіх user-controlled даних
        const escapedName = escapeHtml(s.name);
        const escapedCity = s.city ? escapeHtml(s.city) + ', ' : '';
        const escapedAddress = escapeHtml(s.address);

        marker.bindPopup(`
            <div style="font-family: 'Inter', sans-serif; min-width: 180px; padding: 4px;">
                <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 4px; color: var(--text);">${escapedName}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.3;">${escapedCity}${escapedAddress}</div>
                ${s.rating ? `<div style="margin-top: 8px; color: var(--accent); font-weight: 700; font-size: 0.85rem; display: flex; align-items: center; gap: 2px;">★ ${escapeHtml(String(s.rating))}</div>` : ''}
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
    } else {
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