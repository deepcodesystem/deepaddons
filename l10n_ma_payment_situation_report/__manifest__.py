{
    'name': 'Maroc - Situation de paiement par client',
    'version': '18.0.1.1.0',
    'category': 'Accounting',
    'summary': 'Rapport de situation de paiement par client et rapport global des impayés (factures fractionnées « Client Comptoir » incluses)',
    'description': """
Situation de paiement par client
================================
Génère un rapport PDF regroupant, par bon de commande, les factures associées
(fractionnées « Client Comptoir » incluses, via l10n_ma_origin_partner_id) et leurs paiements.
Sélection multiple de clients via un champ many2many.

Situation des impayés - tous clients
====================================
Génère un PDF listant tous les clients avec un solde impayé (une ligne par client,
trié par impayé décroissant, total général en fin de rapport).
    """,
    'author': 'GetapERP',
    'website': 'https://www.getaperp.com',
    'depends': ['account', 'sale', 'l10n_ma_sale_invoice_split'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/payment_situation_wizard_views.xml',
        'wizard/unpaid_customers_wizard_views.xml',
        'report/payment_situation_report.xml',
        'report/payment_situation_report_templates.xml',
        'report/unpaid_customers_report.xml',
        'report/unpaid_customers_report_templates.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
