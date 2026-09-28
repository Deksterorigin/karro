let map;
const markers = {};

function requestUserLocation() {
    const button = document.getElementById('btnNearby');

    if (!navigator.geolocation) {
        alert(t('search.geo_unsupported'));
        return;
    }

    if (button) {
        button.textContent = t('search.locating');
        button.disabled = true;
    }

    const restoreButton = () => {
        if (button) {
            button.textContent = t('search.btn_nearby');
            button.disabled = false;
        }
    };

    const success = position => {
        const lat = document.getElementById('userLat');
        const lng = document.getElementById('userLng');
        const form = document.getElementById('searchForm');

        if (!lat || !lng || !form) {
            restoreButton();
            return;
        }

        lat.value = position.coords.latitude;
        lng.value = position.coords.longitude;
        form.submit();
    };

    navigator.geolocation.getCurrentPosition(
        success,
        () => navigator.geolocation.getCurrentPosition(
            success,
            error => {
                alert(error.code === 1
                    ? t('search.geo_denied')
                    : t('search.geo_denied_short'));
                restoreButton();
            },
            { timeout: 10000, maximumAge: 600000 }
        ),
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 300000 }
    );
}

function highlightCard(id) {
    document.querySelectorAll('.station-card').forEach(card => {
        card.classList.remove('active');
    });

    const card = document.getElementById(`card-${id}`);
    if (card) {
        card.classList.add('active');
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function focusMarker(id, lat, lng) {
    document.querySelectorAll('.station-card').forEach(card => {
        card.classList.remove('active');
    });
    document.getElementById(`card-${id}`)?.classList.add('active');

    const latitude = Number(lat);
    const longitude = Number(lng);
    if (map && markers[id] &&
        Number.isFinite(latitude) && Number.isFinite(longitude)) {
        map.setView([latitude, longitude], 15);
        markers[id].openPopup();
    }
}

function initMap() {
    const element = document.getElementById('map');
    if (!element || typeof L === 'undefined') return;

    map = L.map(element).setView([49, 31.5], 6);
    L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
        {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
        }
    ).addTo(map);

    const bounds = L.latLngBounds([]);
    const userLat = Number(window.USER_LAT);
    const userLng = Number(window.USER_LNG);
    const hasUserLocation = window.USER_LAT !== null &&
        window.USER_LAT !== undefined &&
        window.USER_LNG !== null &&
        window.USER_LNG !== undefined &&
        Number.isFinite(userLat) && Number.isFinite(userLng) &&
        Math.abs(userLat) <= 90 && Math.abs(userLng) <= 180;

    if (hasUserLocation) {
        L.circleMarker([userLat, userLng], {
            radius: 9,
            color: '#ffffff',
            weight: 2,
            fillColor: '#10B981',
            fillOpacity: 1
        }).addTo(map).bindPopup(t('search.you_are_here'));
        bounds.extend([userLat, userLng]);

        const radius = Number(window.SELECTED_RADIUS);
        if (Number.isFinite(radius) && radius > 0) {
            const circle = L.circle([userLat, userLng], {
                radius: radius * 1000,
                color: '#0052CC',
                fillOpacity: 0.08,
                weight: 1.5,
                dashArray: '4, 4'
            }).addTo(map);
            bounds.extend(circle.getBounds());
        }
    }

    (Array.isArray(window.STATIONS) ? window.STATIONS : []).forEach(station => {
        const lat = Number(station.lat);
        const lng = Number(station.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng) ||
            Math.abs(lat) > 90 || Math.abs(lng) > 180) return;

        const popup = document.createElement('div');
        const link = document.createElement('a');
        const address = document.createElement('div');

        link.href = `/station/${encodeURIComponent(station.id)}/`;
        link.textContent = `${station.name} →`;
        link.style.fontWeight = '700';
        address.textContent = [station.city, station.address]
            .filter(Boolean).join(', ');

        popup.append(link, address);

        if (station.distance !== null && station.distance !== undefined) {
            const distance = document.createElement('div');
            distance.textContent = (
                `${t('search.distance')} ${station.distance} ${t('common.km')}`
            );
            popup.appendChild(distance);
        }

        if (station.rating !== null && station.rating !== undefined) {
            const rating = document.createElement('div');
            rating.textContent = `★ ${station.rating}`;
            popup.appendChild(rating);
        }

        const marker = L.marker([lat, lng]).addTo(map).bindPopup(popup);
        marker.on('click', () => highlightCard(station.id));
        markers[station.id] = marker;
        bounds.extend([lat, lng]);
    });

    if (bounds.isValid()) {
        if (bounds.getNorthEast().equals(bounds.getSouthWest())) {
            map.setView(bounds.getCenter(), hasUserLocation ? 12 : 14);
        } else {
            map.fitBounds(bounds, { padding: [40, 40] });
        }
    }

    setTimeout(() => map.invalidateSize(), 250);
}

document.addEventListener('DOMContentLoaded', initMap);