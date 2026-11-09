# -*- coding: utf-8 -*-
"""Extension of res.users to support PWA push notifications."""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    """Extend res.users with PWA push notification capabilities.

    Adds a one-to-many relationship to push subscriptions and helper methods
    for sending notifications to all active subscriptions of a user.
    """

    _inherit = 'res.users'

    push_subscription_ids = fields.One2many(
        'push.subscription',
        'user_id',
        string='Push Subscriptions',
        help='All browser push notification subscriptions for this user.',
    )
    push_subscription_count = fields.Integer(
        string='Push Subscriptions',
        compute='_compute_push_subscription_count',
        help='Number of active push notification subscriptions.',
    )

    @api.depends('push_subscription_ids', 'push_subscription_ids.active')
    def _compute_push_subscription_count(self):
        """Count active push subscriptions for each user."""
        for user in self:
            user.push_subscription_count = len(
                user.push_subscription_ids.filtered('active')
            )

    def send_push_notification(self, title, message, data=None):
        """Send a push notification to all active subscriptions of this user.

        Iterates over every active :class:`push.subscription` record linked to
        the user and attempts delivery. Failures are logged but do not abort
        the remaining deliveries.

        :param str title: Notification title.
        :param str message: Notification body text.
        :param dict data: Optional extra data forwarded to the Service Worker.
        :return: Number of successfully delivered notifications.
        :rtype: int
        """
        sent_count = 0
        for user in self:
            active_subs = user.push_subscription_ids.filtered('active')
            for subscription in active_subs:
                try:
                    if subscription.send_notification(title, message, data):
                        sent_count += 1
                except Exception as exc:  # pylint: disable=broad-except
                    _logger.warning(
                        'Could not send push notification to user %s '
                        '(subscription %s): %s',
                        user.id,
                        subscription.id,
                        exc,
                    )
        return sent_count

    def action_view_push_subscriptions(self):
        """Open the list of push subscriptions for this user.

        :return: Action dictionary for opening the push.subscription list view.
        :rtype: dict
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Push Subscriptions',
            'res_model': 'push.subscription',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }

    def action_send_test_push_notification(self):
        """Send a test push notification from the user form view.

        :return: Client action dict to display a success/error notification.
        :rtype: dict
        """
        self.ensure_one()
        sent = self.send_push_notification(
            title='Test Notification',
            message='This is a test push notification from Odoo.',
            data={'url': '/web'},
        )
        if sent:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Test notification sent to {sent} subscription(s).',
                    'type': 'success',
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Warning',
                'message': 'No active push subscriptions found for this user.',
                'type': 'warning',
            },
        }
