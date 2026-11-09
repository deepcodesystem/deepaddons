# -*- coding: utf-8 -*-
"""HTTP controllers for PWA push notification management."""

import json
import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PwaNotificationController(http.Controller):
    """Handles browser-side subscription management and service worker delivery.

    Routes:
    - POST /pwa/push/subscribe    – register a new push subscription
    - POST /pwa/push/unsubscribe  – deactivate an existing subscription
    - POST /pwa/push/test         – send a test notification to the current user
    - GET  /service-worker.js     – serve the Service Worker JavaScript file
    """

    @http.route('/pwa/push/subscribe', type='json', auth='user', methods=['POST'])
    def subscribe(self, endpoint=None, keys=None, **kwargs):
        """Register or update a browser push subscription for the current user.

        The browser sends the subscription object created by
        ``PushManager.subscribe()``. This endpoint persists it so that Odoo
        can later use it to send push notifications.

        :param str endpoint: Push service URL provided by the browser.
        :param dict keys: Dict with ``p256dh`` and ``auth`` keys.
        :return: ``{'success': True, 'subscription_id': <id>}`` on success,
                 ``{'success': False, 'error': <msg>}`` on failure.
        :rtype: dict
        """
        if not endpoint or not keys:
            return {'success': False, 'error': 'Missing endpoint or keys'}

        p256dh = keys.get('p256dh', '')
        auth = keys.get('auth', '')

        if not p256dh or not auth:
            return {'success': False, 'error': 'Missing p256dh or auth key'}

        env = request.env
        PushSubscription = env['push.subscription'].sudo()

        # Reuse existing subscription if the endpoint already exists
        existing = PushSubscription.search(
            [('endpoint', '=', endpoint), ('user_id', '=', env.user.id)],
            limit=1,
        )

        subscription_data = {
            'endpoint': endpoint,
            'p256dh_key': p256dh,
            'auth_key': auth,
            'subscription_json': json.dumps({
                'endpoint': endpoint,
                'keys': keys,
            }),
            'active': True,
        }

        if existing:
            existing.write(subscription_data)
            subscription_id = existing.id
        else:
            subscription_data['user_id'] = env.user.id
            sub = PushSubscription.create(subscription_data)
            subscription_id = sub.id

        _logger.info(
            'Push subscription %s saved for user %s',
            subscription_id,
            env.user.login,
        )
        return {'success': True, 'subscription_id': subscription_id}

    @http.route('/pwa/push/unsubscribe', type='json', auth='user', methods=['POST'])
    def unsubscribe(self, endpoint=None, **kwargs):
        """Deactivate a push subscription identified by its endpoint URL.

        :param str endpoint: The push service endpoint URL to deactivate.
        :return: ``{'success': True}`` on success,
                 ``{'success': False, 'error': <msg>}`` on failure.
        :rtype: dict
        """
        if not endpoint:
            return {'success': False, 'error': 'Missing endpoint'}

        env = request.env
        subs = env['push.subscription'].sudo().search([
            ('endpoint', '=', endpoint),
            ('user_id', '=', env.user.id),
        ])

        if subs:
            subs.write({'active': False})
            _logger.info(
                'Push subscription deactivated for user %s (endpoint: %s…)',
                env.user.login,
                endpoint[:40],
            )

        return {'success': True}

    @http.route('/pwa/push/test', type='json', auth='user', methods=['POST'])
    def test_notification(self, **kwargs):
        """Send a test push notification to the current user's subscriptions.

        :return: ``{'success': True, 'message': '…'}`` on success,
                 ``{'success': False, 'error': <msg>}`` on failure.
        :rtype: dict
        """
        user = request.env.user
        try:
            sent = user.send_push_notification(
                title='Test Notification 🔔',
                message='Your PWA push notifications are working correctly!',
                data={'url': '/web'},
            )
            if sent:
                return {
                    'success': True,
                    'message': f'Test notification sent to {sent} subscription(s).',
                }
            return {
                'success': False,
                'error': 'No active push subscriptions found for your account.',
            }
        except Exception as exc:  # pylint: disable=broad-except
            _logger.error('Error sending test notification: %s', exc)
            return {'success': False, 'error': str(exc)}

    @http.route('/service-worker.js', type='http', auth='public', methods=['GET'])
    def service_worker(self, **kwargs):
        """Serve the Service Worker JavaScript file at the root scope.

        The Service Worker must be served from the root path so that its scope
        covers the entire PWA origin.

        :return: HTTP response with the service-worker.js content.
        :rtype: :class:`werkzeug.wrappers.Response`
        """
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sw_path = os.path.join(module_path, 'static', 'src', 'service-worker.js')

        try:
            with open(sw_path, 'r', encoding='utf-8') as sw_file:
                content = sw_file.read()
        except FileNotFoundError:
            _logger.error('service-worker.js not found at %s', sw_path)
            return request.make_response(
                '// Service Worker not found',
                headers=[('Content-Type', 'application/javascript')],
            )

        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/javascript'),
                ('Cache-Control', 'no-cache, no-store, must-revalidate'),
                ('Service-Worker-Allowed', '/'),
            ],
        )
