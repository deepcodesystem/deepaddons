from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ma_cash_invoice_partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire par défaut (factures espèces ≤ 5000 DH)',
        help='Ce partenaire sera utilisé comme destinataire de facturation '
             'lors du fractionnement de factures (paiement espèces, législation marocaine).',
        config_parameter='l10n_ma_sale_invoice_split.default_cash_partner_id',
    )

