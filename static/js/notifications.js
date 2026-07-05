// Система сповіщень для власників СТО
document.addEventListener('DOMContentLoaded', () => {
    const bellBtn = document.getElementById('notification-bell-btn');
    const dropdown = document.getElementById('notification-dropdown');
    const badge = document.getElementById('notification-badge');
    const list = document.getElementById('notification-list');
    const markAllBtn = document.getElementById('mark-all-read-btn');

    if (!bellBtn || !dropdown) return;

    // Отримання CSRF токена з cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Отримання поточної мови сайту
    function getActiveLang() {
        return localStorage.getItem('karro_lang') || 'uk';
    }

    // Перемикач випадаючого списку
    bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isVisible = dropdown.style.display === 'flex';
        dropdown.style.display = isVisible ? 'none' : 'flex';
        if (!isVisible) {
            fetchNotifications();
        }
    });

    // Закриття при кліку поза межами списку
    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target) && !bellBtn.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });

    // Отримання та відображення сповіщень
    function fetchNotifications() {
        fetch('/api/notifications/')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    updateBadge(data.unread_count);
                    renderNotifications(data.notifications);
                }
            })
            .catch(err => console.error('Error fetching notifications:', err));
    }

    // Оновлення бейджа з кількістю непрочитаних
    function updateBadge(count) {
        if (count > 0) {
            badge.innerText = count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }

    // Відображення списку сповіщень
    function renderNotifications(notifications) {
        list.innerHTML = '';
        const lang = getActiveLang();

        if (notifications.length === 0) {
            const emptyMsg = lang === 'uk' ? 'Немає нових сповіщень' : 'No new notifications';
            list.innerHTML = `
                <div class="notification-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                    </svg>
                    <span>${emptyMsg}</span>
                </div>
            `;
            return;
        }

        notifications.forEach(item => {
            const div = document.createElement('div');
            div.className = `notification-item ${item.is_read ? '' : 'unread'}`;
            
            div.innerHTML = `
                <div class="notification-item-text">${escapeHtml(item.message)}</div>
                <div class="notification-item-time">${item.created_at}</div>
            `;

            div.addEventListener('click', (e) => {
                e.preventDefault();
                if (!item.is_read) {
                    // Позначаємо прочитаним через API
                    fetch(`/api/notifications/mark-read/${item.id}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken'),
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(res => res.json())
                    .then(data => {
                        window.location.href = '/profile/?tab=bookings';
                    })
                    .catch(err => {
                        console.error('Error marking notification as read:', err);
                        window.location.href = '/profile/?tab=bookings';
                    });
                } else {
                    window.location.href = '/profile/?tab=bookings';
                }
            });

            list.appendChild(div);
        });
    }

    // Позначення всіх сповіщень як прочитаних
    markAllBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fetch('/api/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                fetchNotifications();
            }
        })
        .catch(err => console.error('Error marking all as read:', err));
    });

    // Допоміжна функція екранування HTML
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    // Первинне завантаження та запуск опитування (інтервал 30 секунд)
    fetchNotifications();
    setInterval(fetchNotifications, 30000);
});
