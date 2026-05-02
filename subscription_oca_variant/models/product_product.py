# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    subscription_template_id = fields.Many2one(
        comodel_name="sale.subscription.template",
        string="Modèle d'abonnement (variante)",
    )

