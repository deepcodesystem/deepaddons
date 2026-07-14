from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ma_origin_partner_id = fields.Many2one(
        'res.partner',
        string='Client réel (origine)',
        copy=False,
        help='Client réel de la facture. Identique au partenaire de facturation pour les factures '
             'normales. Contient le client d\'origine de la commande vente pour les factures '
             'fractionnées (paiement espèces ≤ 5000 DH - législation marocaine).',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-remplir avec partner_id si non défini explicitement
            if vals.get('partner_id') and not vals.get('l10n_ma_origin_partner_id'):
                vals['l10n_ma_origin_partner_id'] = vals['partner_id']
        return super().create(vals_list)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if not default_values_list:
            default_values_list = [{} for move in self]
        for move, default_values in zip(self, default_values_list):
            if move.l10n_ma_origin_partner_id:
                default_values['l10n_ma_origin_partner_id'] = move.l10n_ma_origin_partner_id.id
        return super()._reverse_moves(default_values_list, cancel)

    @api.onchange('partner_id')
    def _onchange_partner_id_l10n_ma_origin(self):
        """En UI : si le partenaire change et que l'origine n'est pas fixée manuellement,
        on synchronise. Ne s'applique pas aux factures espèces (déjà renseigné par le wizard)."""
        if self.partner_id and not self.l10n_ma_origin_partner_id:
            self.l10n_ma_origin_partner_id = self.partner_id

