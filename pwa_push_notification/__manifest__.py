# -*- coding: utf-8 -*-
{
    'name': 'PWA Push Notifications',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Send push notifications to PWA users',
    'description': """
PWA Push Notifications
======================
This module enables Web Push Notifications for Odoo PWA (Progressive Web App)
users without requiring a native Android application.

Features:
- Subscribe/unsubscribe to push notifications from the browser
- Send push notifications to individual users or groups
- VAPID key management
- Service Worker integration
- Administration interface for managing subscriptions
    """,
    'author': 'DeepCodeSystem',
    'website': 'https://github.com/deepcodesystem/deepaddons',
    'depends': ['web', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'data/vapid_keys.xml',
        'views/push_subscription_views.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'pwa_push_notification/static/src/js/push_notification.js',
        ],
    },
    'external_dependencies': {
        'python': ['pywebpush', 'py_vapid'],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
