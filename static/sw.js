// static/js/sw.js
self.addEventListener('push', function(event) {
    const data = event.data.json();
    const options = {
        body: data.body || 'New notification',
        icon: '/static/img/gemz-logo.png',
        badge: '/static/img/gemz-logo.png',
        data: {
            url: data.url || '/',
        },
        actions: [
            { action: 'open', title: 'View' },
            { action: 'dismiss', title: 'Dismiss' },
        ]
    };
    event.waitUntil(
        self.registration.showNotification(data.title || 'Gemz Software', options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    if (event.action === 'open' || !event.action) {
        const url = event.notification.data.url || '/';
        event.waitUntil(
            clients.matchAll({ type: 'window' }).then(function(clientList) {
                for (let i = 0; i < clientList.length; i++) {
                    const client = clientList[i];
                    if (client.url === url && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
        );
    }
});