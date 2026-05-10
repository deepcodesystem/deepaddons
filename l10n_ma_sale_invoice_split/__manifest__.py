{
    'name': 'Fractionnement Factures 5000 DH (Maroc)',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Créer plusieurs factures clients depuis une commande vente - Limite 5000 DH espèces (législation marocaine)',
    'author': 'GetapPRO',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}

