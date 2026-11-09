# -*- coding: utf-8 -*-
"""Model for storing PWA push notification subscriptions."""

import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PushSubscription(models.Model):
    """Stores browser push notification subscriptions for PWA users.

    Each record represents a unique browser/device subscription endpoint
    associated with an Odoo user. The subscription data (endpoint, keys)
    is used by pywebpush to deliver Web Push notifications.
    """

    _name = 'push.subscription'
    _description = 'PWA Push Subscription'
    _order = 'create_date desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help='Computed name based on the associated user.',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        help='Odoo user who owns this push subscription.',
    )
    endpoint = fields.Text(
        string='Endpoint',
        required=True,
        help='Browser-provided URL that receives push messages.',
    )
    p256dh_key = fields.Text(
        string='P256DH Key',
        required=True,
        help='Client public key used for message encryption (p256dh).',
    )
    auth_key = fields.Text(
        string='Auth Key',
        required=True,
        help='Authentication secret used for message encryption.',
    )
    subscription_json = fields.Text(
        string='Subscription JSON',
        help='Full JSON object of the browser push subscription.',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive subscriptions will not receive push notifications.',
    )
    create_date = fields.Datetime(
        string='Creation Date',
        readonly=True,
    )
    last_notification_date = fields.Datetime(
        string='Last Notification Date',
        readonly=True,
        help='Date and time of the last successfully sent push notification.',
    )

    @api.depends('user_id')
    def _compute_name(self):
        """Compute a human-readable name from the linked user."""
        for record in self:
            record.name = record.user_id.name or 'Push Subscription'

    def send_notification(self, title, message, data=None):
        """Send a push notification to this subscription.

        :param str title: Notification title displayed in the browser.
        :param str message: Notification body text.
        :param dict data: Optional extra data forwarded to the Service Worker.
        :return: True if the notification was sent successfully, False otherwise.
        :rtype: bool
        """
        self.ensure_one()
        try:
            payload = self._prepare_payload(title, message, data)
            self._send_webpush(payload)
            self.write({'last_notification_date': fields.Datetime.now()})
            return True
        except Exception as exc:
            _logger.warning(
                'Failed to send push notification to subscription %s: %s',
                self.id,
                exc,
            )
            return False

    def _prepare_payload(self, title, message, data=None):
        """Build the JSON payload that will be delivered to the Service Worker.

        :param str title: Notification title.
        :param str message: Notification body.
        :param dict data: Optional custom data.
        :return: JSON-encoded payload string.
        :rtype: str
        """
        payload = {
            'title': title,
            'body': message,
            'icon': '/web/static/img/logo.png',
            'badge': '/web/static/img/logo.png',
            'data': data or {},
        }
        return json.dumps(payload)

    def _send_webpush(self, payload):
        """Deliver the payload via pywebpush using the stored VAPID credentials.

        :param str payload: JSON string to send as the notification body.
        :raises UserError: When VAPID keys are not configured.
        :raises Exception: Propagates pywebpush / network errors.
        """
        try:
            from pywebpush import webpush, WebPushException  # noqa: PLC0415
        except ImportError as exc:
            raise UserError(
                'The pywebpush library is required. '
                'Please install it with: pip install pywebpush'
            ) from exc

        ICP = self.env['ir.config_parameter'].sudo()
        vapid_private_key = ICP.get_param('pwa_push.vapid_private_key', '')
        vapid_email = ICP.get_param('pwa_push.vapid_email', 'mailto:admin@example.com')

        if not vapid_private_key:
            raise UserError(
                'VAPID private key is not configured. '
                'Please set pwa_push.vapid_private_key in System Parameters.'
            )

        subscription_info = {
            'endpoint': self.endpoint,
            'keys': {
                'p256dh': self.p256dh_key,
                'auth': self.auth_key,
            },
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims={'sub': vapid_email},
            )
        except WebPushException as exc:
            _logger.error(
                'WebPush delivery failed for subscription %s: %s',
                self.id,
                exc,
            )
            # Mark subscription as inactive when the endpoint is gone (HTTP 410)
            if exc.response is not None and exc.response.status_code == 410:
                self.write({'active': False})
                _logger.info(
                    'Subscription %s deactivated due to 410 Gone response.',
                    self.id,
                )
            raise

    def action_test_notification(self):
        """Send a test notification from the form view button.

        :return: Notification action dict to display result to the user.
        :rtype: dict
        """
        self.ensure_one()
        success = self.send_notification(
            title='Test Notification',
            message='This is a test push notification from Odoo.',
            data={'url': '/web'},
        )
        if success:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Test notification sent successfully.',
                    'type': 'success',
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Error',
                'message': 'Failed to send the test notification. Check the logs.',
                'type': 'danger',
            },
        }
