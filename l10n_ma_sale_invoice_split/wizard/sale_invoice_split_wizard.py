from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class SaleInvoiceSplitWizard(models.TransientModel):
    _name = 'sale.invoice.split.wizard'
    _description = 'Fractionnement des factures - Limite 5000 DH (Maroc)'

    sale_order_id = fields.Many2one('sale.order', string='Bon de commande', required=True, readonly=True)
    limit_amount = fields.Float(string='Limite TTC par facture (DH)', default=5000.0)
    currency_id = fields.Many2one(related='sale_order_id.currency_id', readonly=True)
    invoice_partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire de facturation',
        help='Partenaire utilisé sur les factures générées (ex: Client Comptoir Espèces). '
             'Le client réel de la commande sera conservé sur chaque facture.',
    )
    invoice_count = fields.Integer(string='Nombre de factures à créer', compute='_compute_invoice_count')
    warning_message = fields.Char(string='Avertissement', compute='_compute_invoice_count')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        param = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_ma_sale_invoice_split.default_cash_partner_id'
        )
        if param and 'invoice_partner_id' in fields_list:
            try:
                res['invoice_partner_id'] = int(param)
            except (ValueError, TypeError):
                pass
        return res

    @api.depends('sale_order_id', 'limit_amount')
    def _compute_invoice_count(self):
        for wiz in self:
            wiz.warning_message = False
            if not wiz.sale_order_id or wiz.limit_amount <= 0:
                wiz.invoice_count = 0
                continue
            try:
                split = wiz._get_split_plan()
                wiz.invoice_count = len(split)
                # Warn if any single invoice exceeds the limit (unit price > limit)
                oversized = [
                    item for inv in split for item in inv
                    if float_compare(item['ttc'], wiz.limit_amount, precision_digits=2) > 0
                ]
                if oversized:
                    wiz.warning_message = _(
                        "⚠ Certaines lignes dépassent individuellement la limite (prix unitaire TTC > %.2f DH). "
                        "Elles sont placées seules dans une facture."
                    ) % wiz.limit_amount
            except UserError:
                wiz.invoice_count = 0

    def _get_ttc_for_qty(self, line, qty):
        """Calcule le montant TTC pour une quantité donnée d'une ligne de commande."""
        price_unit_disc = line.price_unit * (1.0 - line.discount / 100.0)
        taxes = line.tax_id.compute_all(
            price_unit_disc,
            line.order_id.currency_id,
            qty,
            product=line.product_id,
            partner=line.order_id.partner_shipping_id,
        )
        return taxes['total_included']

    def _get_split_plan(self):
        """
        Retourne une liste de factures. Chaque facture = liste de dicts {line, qty, ttc}.
        Le total TTC de chaque facture ne dépasse pas self.limit_amount.
        """
        order = self.sale_order_id
        limit = self.limit_amount

        invoiceable = []
        for line in order.order_line:
            if line.display_type or line.product_id.type == 'combo':
                continue
            if float_compare(line.qty_to_invoice, 0.0, precision_digits=5) <= 0:
                continue
            invoiceable.append({'line': line, 'qty_remaining': line.qty_to_invoice})

        if not invoiceable:
            raise UserError(_("Aucune ligne à facturer sur ce bon de commande."))

        invoices = []
        current = []
        current_total = 0.0

        for item in invoiceable:
            line = item['line']
            qty_remaining = item['qty_remaining']
            rounding = line.product_uom.rounding or 0.001

            while float_compare(qty_remaining, 0.0, precision_rounding=rounding) > 0:
                ttc_full = self._get_ttc_for_qty(line, qty_remaining)

                if float_compare(current_total + ttc_full, limit, precision_digits=2) <= 0:
                    # La quantité restante tient entièrement dans la facture courante
                    current.append({'line': line, 'qty': qty_remaining, 'ttc': ttc_full})
                    current_total += ttc_full
                    qty_remaining = 0.0
                else:
                    ttc_unit = self._get_ttc_for_qty(line, 1.0)

                    if float_compare(ttc_unit, limit, precision_digits=2) > 0:
                        # 1 unité seule dépasse la limite → facture individuelle obligatoire
                        if current:
                            invoices.append(current)
                            current = []
                            current_total = 0.0
                        ttc_one = self._get_ttc_for_qty(line, 1.0)
                        invoices.append([{'line': line, 'qty': 1.0, 'ttc': ttc_one}])
                        qty_remaining = float_round(qty_remaining - 1.0, precision_rounding=rounding)
                    else:
                        space = limit - current_total
                        if float_compare(space, ttc_unit, precision_digits=2) >= 0:
                            # Calculer combien d'unités tiennent dans l'espace restant
                            qty_fits = float_round(
                                space / ttc_unit,
                                precision_rounding=rounding,
                                rounding_method='DOWN',
                            )
                            qty_fits = min(qty_fits, qty_remaining)
                            if float_compare(qty_fits, 0.0, precision_rounding=rounding) <= 0:
                                # Plus de place, fermer la facture courante
                                if current:
                                    invoices.append(current)
                                current = []
                                current_total = 0.0
                                continue
                            ttc_fits = self._get_ttc_for_qty(line, qty_fits)
                            current.append({'line': line, 'qty': qty_fits, 'ttc': ttc_fits})
                            current_total += ttc_fits
                            qty_remaining = float_round(qty_remaining - qty_fits, precision_rounding=rounding)
                        else:
                            # Plus de place dans la facture courante → la fermer
                            if current:
                                invoices.append(current)
                            current = []
                            current_total = 0.0

        if current:
            invoices.append(current)

        return invoices

    def action_create_invoices(self):
        self.ensure_one()
        split = self._get_split_plan()
        order = self.sale_order_id
        created = self.env['account.move']

        for invoice_lines in split:
            move_vals = order._prepare_invoice()
            move_vals.pop('invoice_line_ids', None)

            # Substitution du partenaire de facturation si défini
            if self.invoice_partner_id:
                move_vals['partner_id'] = self.invoice_partner_id.id
                move_vals['partner_shipping_id'] = self.invoice_partner_id.id
                move_vals['l10n_ma_origin_partner_id'] = order.partner_id.id

            move = self.env['account.move'].with_context(
                default_move_type='out_invoice'
            ).create(move_vals)

            line_vals_list = []
            for idx, item in enumerate(invoice_lines, start=1):
                ol = item['line']
                vals = ol._prepare_invoice_line(sequence=idx, quantity=item['qty'])
                line_vals_list.append((0, 0, vals))

            move.write({'invoice_line_ids': line_vals_list})
            created |= move

        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_out_invoice_type'
        )
        if len(created) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = created.id
        else:
            action['domain'] = [('id', 'in', created.ids)]
            action['context'] = {'default_move_type': 'out_invoice'}
        return action

