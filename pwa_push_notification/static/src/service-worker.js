/**
 * Odoo PWA Push Notifications - Service Worker
 *
 * This service worker handles incoming push events, displays browser
 * notifications, and processes notification click / close events.
 *
 * It must be served from the root of the application (/) so that its scope
 * covers the entire PWA origin. The Odoo controller at /service-worker.js
 * handles this automatically.
 *
 * Compatibility: Chrome 50+, Firefox 44+, Edge 17+, Safari 16+
 */

'use strict';

const SW_VERSION = '18.0.1.0.0';
const CACHE_NAME = `odoo-pwa-v${SW_VERSION}`;

// ---------------------------------------------------------------------------
// Install & Activate lifecycle events
// ---------------------------------------------------------------------------

self.addEventListener('install', (event) => {
    // Activate immediately without waiting for existing clients to close
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    // Take control of all open clients without requiring a page reload
    event.waitUntil(self.clients.claim());
});

// ---------------------------------------------------------------------------
// Push event – receive and display a push notification
// ---------------------------------------------------------------------------

self.addEventListener('push', (event) => {
    if (!event.data) {
        console.warn('[SW] Push event received with no data.');
        return;
    }

    let payload;
    try {
        payload = event.data.json();
    } catch (err) {
        // Fall back to plain text if JSON parsing fails
        payload = {
            title: 'Notification',
            body: event.data.text(),
        };
    }

    const title = payload.title || 'Odoo Notification';
    const options = {
        body: payload.body || '',
        icon: payload.icon || '/web/static/img/logo.png',
        badge: payload.badge || '/web/static/img/logo.png',
        data: payload.data || {},
        requireInteraction: false,
        tag: payload.tag || 'odoo-notification',
        // Vibration pattern (ms on, ms off, …) for mobile devices
        vibrate: [200, 100, 200],
    };

    // If the payload contains an image URL, add it
    if (payload.image) {
        options.image = payload.image;
    }

    // Show the notification; keep the SW alive until it resolves
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// ---------------------------------------------------------------------------
// notificationclick – handle user clicking on the notification
// ---------------------------------------------------------------------------

self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const data = event.notification.data || {};
    // Default to the Odoo root URL
    const targetUrl = data.url || '/web';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // If an Odoo window is already open, focus it and navigate
                for (const client of clientList) {
                    if ('focus' in client) {
                        client.focus();
                        if ('navigate' in client) {
                            return client.navigate(targetUrl);
                        }
                        return;
                    }
                }
                // No window open – open a new one
                if (self.clients.openWindow) {
                    return self.clients.openWindow(targetUrl);
                }
            })
    );
});

// ---------------------------------------------------------------------------
// notificationclose – handle user dismissing the notification
// ---------------------------------------------------------------------------

self.addEventListener('notificationclose', (event) => {
    // Intentionally left lightweight; extend if you need analytics
    const data = event.notification.data || {};
    console.info('[SW] Notification closed. tag:', event.notification.tag, 'data:', data);
});

// ---------------------------------------------------------------------------
// Message event – allow pages to communicate with the SW
// ---------------------------------------------------------------------------

self.addEventListener('message', (event) => {
    if (!event.data) {
        return;
    }

    switch (event.data.type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
        case 'GET_VERSION':
            event.ports[0] && event.ports[0].postMessage({ version: SW_VERSION });
            break;
        default:
            console.warn('[SW] Unknown message type:', event.data.type);
    }
});
