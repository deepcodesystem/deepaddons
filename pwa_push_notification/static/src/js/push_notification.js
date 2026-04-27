/* @odoo-module */
/**
 * PWA Push Notification Manager
 *
 * Handles browser-side subscription to Web Push notifications and
 * communicates with the Odoo back-end to persist subscriptions.
 *
 * Compatibility: Chrome 50+, Firefox 44+, Edge 17+, Safari 16+
 */

'use strict';

(function () {
    /**
     * Convert a URL-safe base64 string to a Uint8Array.
     * Required to pass the VAPID public key to PushManager.subscribe().
     *
     * @param {string} base64String - URL-safe base64 encoded string.
     * @returns {Uint8Array}
     */
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; i++) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    /**
     * Perform a JSON-RPC call to an Odoo controller endpoint.
     *
     * @param {string} url - The Odoo route (e.g. '/pwa/push/subscribe').
     * @param {Object} params - Parameters to pass in the JSON-RPC body.
     * @returns {Promise<Object>} Resolved with the JSON-RPC result object.
     */
    async function jsonRpc(url, params) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                id: Date.now(),
                params: params,
            }),
        });
        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }
        const json = await response.json();
        if (json.error) {
            throw new Error(json.error.data ? json.error.data.message : json.error.message);
        }
        return json.result;
    }

    /**
     * Fetch the VAPID public key from Odoo system parameters.
     *
     * @returns {Promise<string>} The URL-safe base64 VAPID public key.
     */
    async function getVapidPublicKey() {
        const result = await jsonRpc('/web/dataset/call_kw', {
            model: 'ir.config_parameter',
            method: 'get_param',
            args: ['pwa_push.vapid_public_key'],
            kwargs: {},
        });
        return result;
    }

    /**
     * Subscribe the current browser to push notifications.
     *
     * 1. Requests notification permission from the user.
     * 2. Registers the service worker if not already registered.
     * 3. Creates a PushSubscription via PushManager.
     * 4. Sends the subscription to the Odoo back-end.
     *
     * @returns {Promise<boolean>} True if subscription succeeded.
     */
    async function subscribeToPush() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            console.warn('[PWA] Push notifications are not supported by this browser.');
            showStatus('Push notifications are not supported by your browser.', 'warning');
            return false;
        }

        // Request notification permission
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            showStatus('Notification permission denied.', 'warning');
            return false;
        }

        try {
            // Register service worker
            const registration = await navigator.serviceWorker.register('/service-worker.js', {
                scope: '/',
            });
            await navigator.serviceWorker.ready;

            // Get VAPID public key
            const vapidPublicKey = await getVapidPublicKey();
            if (!vapidPublicKey || vapidPublicKey === 'REPLACE_WITH_YOUR_VAPID_PUBLIC_KEY') {
                showStatus('VAPID public key is not configured. Contact your administrator.', 'danger');
                return false;
            }

            const applicationServerKey = urlBase64ToUint8Array(vapidPublicKey);

            // Subscribe via PushManager
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey,
            });

            const subscriptionJson = subscription.toJSON();

            // Send subscription to Odoo
            const result = await jsonRpc('/pwa/push/subscribe', {
                endpoint: subscriptionJson.endpoint,
                keys: subscriptionJson.keys,
            });

            if (result && result.success) {
                showStatus('Push notifications enabled! ✅', 'success');
                updateButtonState(true);
                return true;
            } else {
                showStatus('Failed to save subscription: ' + (result ? result.error : 'Unknown error'), 'danger');
                return false;
            }
        } catch (err) {
            console.error('[PWA] Error subscribing to push notifications:', err);
            showStatus('Error enabling notifications: ' + err.message, 'danger');
            return false;
        }
    }

    /**
     * Unsubscribe the current browser from push notifications.
     *
     * @returns {Promise<boolean>} True if unsubscription succeeded.
     */
    async function unsubscribeFromPush() {
        try {
            const registration = await navigator.serviceWorker.getRegistration('/');
            if (!registration) {
                showStatus('No active service worker found.', 'warning');
                return false;
            }

            const subscription = await registration.pushManager.getSubscription();
            if (!subscription) {
                showStatus('No active push subscription found.', 'warning');
                updateButtonState(false);
                return false;
            }

            const endpoint = subscription.endpoint;

            // Notify Odoo back-end
            await jsonRpc('/pwa/push/unsubscribe', { endpoint });

            // Unsubscribe in browser
            await subscription.unsubscribe();

            showStatus('Push notifications disabled.', 'info');
            updateButtonState(false);
            return true;
        } catch (err) {
            console.error('[PWA] Error unsubscribing from push notifications:', err);
            showStatus('Error disabling notifications: ' + err.message, 'danger');
            return false;
        }
    }

    /**
     * Check whether the user is currently subscribed to push notifications.
     *
     * @returns {Promise<boolean>}
     */
    async function isSubscribed() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            return false;
        }
        try {
            const registration = await navigator.serviceWorker.getRegistration('/');
            if (!registration) {
                return false;
            }
            const subscription = await registration.pushManager.getSubscription();
            return !!subscription;
        } catch (_) {
            return false;
        }
    }

    /**
     * Update the toggle button label and style based on subscription state.
     *
     * @param {boolean} subscribed - True when currently subscribed.
     */
    function updateButtonState(subscribed) {
        const btn = document.getElementById('pwa-push-toggle-btn');
        if (!btn) {
            return;
        }
        if (subscribed) {
            btn.textContent = '🔕 Disable Push Notifications';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
        } else {
            btn.textContent = '🔔 Enable Push Notifications';
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary');
        }
    }

    /**
     * Display a status message in the #pwa-push-status element.
     *
     * @param {string} message - Text to show.
     * @param {string} type - Bootstrap alert type: 'success', 'warning', 'danger', 'info'.
     */
    function showStatus(message, type) {
        const statusEl = document.getElementById('pwa-push-status');
        if (!statusEl) {
            return;
        }
        statusEl.textContent = message;
        statusEl.className = `alert alert-${type}`;
        statusEl.style.display = 'block';
        // Auto-hide after 5 seconds
        setTimeout(() => {
            statusEl.style.display = 'none';
        }, 5000);
    }

    /**
     * Initialise the push notification UI once the DOM is ready.
     * Injects a toggle button and status element if not already present
     * in the page, and wires up click handlers.
     */
    async function init() {
        // Only initialise in a browser that supports the required APIs
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            return;
        }

        const container = document.getElementById('pwa-push-container');
        if (!container) {
            // No container on the current page — nothing to do
            return;
        }

        // Inject status element
        if (!document.getElementById('pwa-push-status')) {
            const statusEl = document.createElement('div');
            statusEl.id = 'pwa-push-status';
            statusEl.style.display = 'none';
            container.appendChild(statusEl);
        }

        // Inject toggle button
        if (!document.getElementById('pwa-push-toggle-btn')) {
            const btn = document.createElement('button');
            btn.id = 'pwa-push-toggle-btn';
            btn.className = 'btn btn-primary';
            btn.type = 'button';
            container.appendChild(btn);
        }

        const subscribed = await isSubscribed();
        updateButtonState(subscribed);

        const btn = document.getElementById('pwa-push-toggle-btn');
        btn.addEventListener('click', async () => {
            btn.disabled = true;
            try {
                const currentlySubscribed = await isSubscribed();
                if (currentlySubscribed) {
                    await unsubscribeFromPush();
                } else {
                    await subscribeToPush();
                }
            } finally {
                btn.disabled = false;
            }
        });
    }

    // Expose public API for use in Odoo views or custom scripts
    window.odooVapidPush = {
        subscribe: subscribeToPush,
        unsubscribe: unsubscribeFromPush,
        isSubscribed,
    };

    // Initialise when the DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
