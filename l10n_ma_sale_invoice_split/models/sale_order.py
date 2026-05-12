from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_split_invoice_5000(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fractionner les factures (≤ 5000 DH)',
            'res_model': 'sale.invoice.split.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    def _get_invoiceable_lines(self, final=False):
        lines = super()._get_invoiceable_lines(final=final)
        return lines.filtered(lambda l: not l.product_id.is_ug)
