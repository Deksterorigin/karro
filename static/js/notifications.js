document.addEventListener('DOMContentLoaded', () => {
    const bell = document.getElementById('notification-bell-btn');
    const dropdown = document.getElementById('notification-dropdown');
    const badge = document.getElementById('notification-badge');
    const list = document.getElementById('notification-list');
    const markAll = document.getElementById('mark-all-read-btn');

    if (!bell || !dropdown || !list) return;

    let loading = false;
    const destination = '/profile/?tab=bookings';

    function csrfToken() {
        const input = document.querySelector('[name="csrfmiddlewaretoken"]');
        if (input) return input.value;

        const cookie = document.cookie.split('; ').find(item => {
            return item.startsWith('csrftoken=');
        });
        return cookie ? decodeURIComponent(cookie.slice(10)) : '';
    }

    async function post(url) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken() }
        });
        const data = await response.json();

        if (!response.ok || data.status !== 'success') {
            throw new Error(data.message || t('common.connection_error'));
        }
    }

    async function fetchNotifications() {
        if (loading) return;
        loading = true;

        try {
            const response = await fetch('/api/notifications/');
            const data = await response.json();
            if (!response.ok || data.status !== 'success') return;

            if (badge) {
                const count = Number(data.unread_count) || 0;
                badge.textContent = count;
                badge.style.display = count ? 'flex' : 'none';
            }

            list.replaceChildren();

            if (!data.notifications?.length) {
                const empty = document.createElement('div');
                empty.className = 'notification-empty';
                empty.textContent = t('notifications.empty');
                list.appendChild(empty);
                return;
            }

            data.notifications.forEach(item => {
                const row = document.createElement('div');
                const text = document.createElement('div');
                const time = document.createElement('div');

                row.className = `notification-item${item.is_read ? '' : ' unread'}`;
                text.className = 'notification-item-text';
                time.className = 'notification-item-time';
                text.textContent = item.message;
                time.textContent = item.created_at;
                row.append(text, time);

                row.addEventListener('click', async () => {
                    if (!item.is_read) {
                        try {
                            await post(
                                `/api/notifications/mark-read/${encodeURIComponent(item.id)}/`
                            );
                        } catch (error) {
                            alert(error.message);
                            return;
                        }
                    }
                    location.href = destination;
                });

                list.appendChild(row);
            });
        } catch (error) {
            console.error('Не вдалося завантажити сповіщення:', error);
        } finally {
            loading = false;
        }
    }

    bell.addEventListener('click', event => {
        event.stopPropagation();
        const opening = dropdown.style.display !== 'flex';
        dropdown.style.display = opening ? 'flex' : 'none';
        if (opening) fetchNotifications();
    });

    document.addEventListener('click', event => {
        if (!dropdown.contains(event.target) && !bell.contains(event.target)) {
            dropdown.style.display = 'none';
        }
    });

    markAll?.addEventListener('click', async event => {
        event.stopPropagation();

        try {
            await post('/api/notifications/mark-all-read/');
            await fetchNotifications();
        } catch (error) {
            alert(error.message);
        }
    });

    fetchNotifications();
    setInterval(fetchNotifications, 30000);
});
