/**
 * Модуль для обробки подій у реальному часі через Server-Sent Events (SSE) з автоматичним підключенням та fallback.
 */

class SSEManager {
    constructor() {
        this.chatEventSource = null;
        this.notifEventSource = null;
        this.lastChatMessageId = 0;
        this.lastNotificationId = 0;
    }

    /**
     * Підключення до SSE-потоку чату конкретного замовлення.
     */
    connectChat(bookingId, onMessageCallback) {
        if (this.chatEventSource) {
            this.chatEventSource.close();
        }

        const url = `/api/bookings/${bookingId}/chat/events/?last_id=${this.lastChatMessageId}`;
        this.chatEventSource = new EventSource(url);

        this.chatEventSource.addEventListener('message', (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        if (msg.id > this.lastChatMessageId) {
                            this.lastChatMessageId = msg.id;
                        }
                    });
                    if (typeof onMessageCallback === 'function') {
                        onMessageCallback(data.messages);
                    }
                }
            } catch (err) {
                console.error('Помилка обробки SSE повідомлення чату:', err);
            }
        });

        this.chatEventSource.onerror = () => {
            // Перепідключення через 3 секунди у разі обриву з'єднання
            this.chatEventSource.close();
            setTimeout(() => {
                this.connectChat(bookingId, onMessageCallback);
            }, 3000);
        };
    }

    /**
     * Підключення до SSE-потоку сповіщень користувача.
     */
    connectNotifications(onNotificationCallback) {
        if (this.notifEventSource) {
            this.notifEventSource.close();
        }

        const url = `/api/notifications/events/?last_id=${this.lastNotificationId}`;
        this.notifEventSource = new EventSource(url);

        this.notifEventSource.addEventListener('notification', (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(n => {
                        if (n.id > this.lastNotificationId) {
                            this.lastNotificationId = n.id;
                        }
                    });
                    if (typeof onNotificationCallback === 'function') {
                        onNotificationCallback(data.notifications);
                    }
                }
            } catch (err) {
                console.error('Помилка обробки SSE сповіщення:', err);
            }
        });

        this.notifEventSource.onerror = () => {
            this.notifEventSource.close();
            setTimeout(() => {
                this.connectNotifications(onNotificationCallback);
            }, 5000);
        };
    }

    disconnectAll() {
        if (this.chatEventSource) {
            this.chatEventSource.close();
            this.chatEventSource = null;
        }
        if (this.notifEventSource) {
            this.notifEventSource.close();
            this.notifEventSource = null;
        }
    }
}

window.sseManager = new SSEManager();
