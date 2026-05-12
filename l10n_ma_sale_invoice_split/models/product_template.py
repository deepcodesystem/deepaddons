from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_ug = fields.Boolean(
        string='Unité Gratuite (UG)',
        default=False,
        help="Si coché, ce produit est traité comme une unité gratuite : "
             "il apparaît sur la commande et le bon de livraison, "
             "mais est exclu de la facturation.",
    )

