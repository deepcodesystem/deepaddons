# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from collections import defaultdict

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def group_subscription_lines(self):
        """
        Groupe les lignes de commande par modèle d'abonnement.
        Priorité : modèle défini sur la variante produit.
        Fallback : modèle défini sur le template produit.
        """
        grouped = defaultdict(list)
        for order_line in self.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id.subscribable
        ):
            tmpl = (
                order_line.product_id.subscription_template_id
                or order_line.product_id.product_tmpl_id.subscription_template_id
            )
            if tmpl:
                grouped[tmpl].append(order_line)
        return grouped

