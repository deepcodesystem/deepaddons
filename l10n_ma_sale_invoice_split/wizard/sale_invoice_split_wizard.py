import math

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
    deposit_amount = fields.Monetary(
        string='Acomptes à déduire (TTC)',
        currency_field='currency_id',
        compute='_compute_invoice_count',
        help="Acomptes déjà facturés sur la commande et pas encore déduits. Ils sont déduits "
             "sur les factures fractionnées : le plafond s'applique au montant net à payer.",
    )
    warning_message = fields.Char(string='Avertissement', compute='_compute_invoice_count')
    campaign_mode = fields.Boolean(
        string='Mode Campagne (injecter 1 UG)',
        default=False,
        help="En mode campagne, 1 unité gratuite (prix 0) sera injectée dans la première "
             "facture générée, prélevée du stock tampon UG (FIFO).",
    )
    ug_pending_count = fields.Integer(
        string='UG en stock tampon',
        compute='_compute_ug_pending_count',
    )

    @api.depends('campaign_mode')
    def _compute_ug_pending_count(self):
        # Calculer la somme totale des quantités en attente (pas le nombre d'enregistrements)
        pendings = self.env['stock.ug.pending'].search([('qty_pending', '>', 0)])
        total_qty = sum(pendings.mapped('qty_pending'))
        for wiz in self:
            wiz.ug_pending_count = int(total_qty)

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
            wiz.deposit_amount = sum(
                wiz._get_ttc_for_qty(dl, -dl.qty_to_invoice) for dl in wiz._get_deposit_lines()
            ) if wiz.sale_order_id else 0.0
            if not wiz.sale_order_id or wiz.limit_amount <= 0:
                wiz.invoice_count = 0
                continue
            try:
                split = wiz._get_split_plan()
                wiz.invoice_count = len(split)
                oversized = [
                    inv for inv in split
                    if float_compare(sum(item['ttc'] for item in inv), wiz.limit_amount, precision_digits=2) > 0
                ]
                if oversized:
                    wiz.warning_message = _(
                        "⚠ Certaines lignes dépassent individuellement la limite (prix unitaire TTC > %.2f DH). "
                        "Elles sont placées seules dans une facture."
                    ) % wiz.limit_amount
            except UserError:
                wiz.invoice_count = 0

    def _get_ttc_for_qty(self, line, qty):
        price_unit_disc = line.price_unit * (1.0 - line.discount / 100.0)
        taxes = line.tax_id.compute_all(
            price_unit_disc,
            line.order_id.currency_id,
            qty,
            product=line.product_id,
            partner=line.order_id.partner_shipping_id,
        )
        return taxes['total_included']

    def _get_deposit_lines(self):
        """Lignes d'acompte déjà facturées et pas encore déduites (qty_to_invoice < 0)."""
        return self.sale_order_id.order_line.filtered(
            lambda l: l.is_downpayment
            and not l.display_type
            and float_compare(l.qty_to_invoice, 0.0, precision_digits=5) < 0
        )

    def _get_split_plan(self):
        """Répartit les lignes à facturer en factures dont le NET à payer est <= limite.

        Les acomptes déjà facturés sont déduits en partant de la première facture :
        une facture peut contenir jusqu'à (limite + acompte restant) de produits,
        l'acompte déduit ramenant son net à payer sous la limite.
        Chaque élément du plan : {'line', 'qty', 'ttc', 'is_deposit'} (ttc négatif pour un acompte).
        """
        order = self.sale_order_id
        limit = self.limit_amount
        uom_precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        invoiceable = []
        for line in order.order_line:
            if line.display_type or line.is_downpayment or line.product_id.type == 'combo' or line.product_id.is_ug:
                continue
            if float_compare(line.qty_to_invoice, 0.0, precision_digits=5) <= 0:
                continue
            invoiceable.append({'line': line, 'qty_remaining': math.floor(line.qty_to_invoice)})

        if not invoiceable:
            raise UserError(_("Aucune ligne à facturer sur ce bon de commande."))

        deposits = [
            {'line': dl, 'qty_left': -dl.qty_to_invoice, 'ttc_unit': self._get_ttc_for_qty(dl, 1.0)}
            for dl in self._get_deposit_lines()
        ]
        state = {'deposit_left': sum(self._get_ttc_for_qty(d['line'], d['qty_left']) for d in deposits)}

        invoices = []
        current = []
        current_total = 0.0

        def cap():
            return limit + state['deposit_left']

        def take_deposits(gross):
            """Lignes de déduction d'acompte pour une facture de montant brut `gross`."""
            items = []
            to_deduct = min(state['deposit_left'], gross)
            for d in deposits:
                if float_compare(to_deduct, 0.0, precision_digits=2) <= 0:
                    break
                if float_compare(d['qty_left'], 0.0, precision_digits=uom_precision) <= 0:
                    continue
                full_ttc = self._get_ttc_for_qty(d['line'], d['qty_left'])
                if float_compare(full_ttc, to_deduct, precision_digits=2) <= 0:
                    qty, ttc = d['qty_left'], full_ttc
                else:
                    # Déduction partielle : arrondi au-dessus pour que le net reste <= limite
                    qty = min(
                        float_round(to_deduct / d['ttc_unit'], precision_digits=uom_precision, rounding_method='UP'),
                        d['qty_left'],
                    )
                    ttc = self._get_ttc_for_qty(d['line'], qty)
                d['qty_left'] -= qty
                to_deduct -= ttc
                state['deposit_left'] = max(state['deposit_left'] - ttc, 0.0)
                items.append({'line': d['line'], 'qty': qty, 'ttc': -ttc, 'is_deposit': True})
            return items

        def flush():
            nonlocal current, current_total
            if current:
                invoices.append(current + take_deposits(current_total))
            current = []
            current_total = 0.0

        for item in invoiceable:
            line = item['line']
            qty_remaining = item['qty_remaining']
            rounding = 1.0

            while float_compare(qty_remaining, 0.0, precision_rounding=rounding) > 0:
                ttc_full = self._get_ttc_for_qty(line, qty_remaining)

                if float_compare(current_total + ttc_full, cap(), precision_digits=2) <= 0:
                    current.append({'line': line, 'qty': qty_remaining, 'ttc': ttc_full, 'is_deposit': False})
                    current_total += ttc_full
                    qty_remaining = 0.0
                    continue

                ttc_unit = self._get_ttc_for_qty(line, 1.0)
                if float_compare(ttc_unit, cap(), precision_digits=2) > 0:
                    # Une seule unité dépasse le plafond : facture dédiée
                    flush()
                    current = [{'line': line, 'qty': 1, 'ttc': ttc_unit, 'is_deposit': False}]
                    current_total = ttc_unit
                    flush()
                    qty_remaining -= 1
                    continue

                space = cap() - current_total
                qty_fits = min(math.floor(space / ttc_unit), qty_remaining) if space > 0 else 0
                if qty_fits <= 0 and not current:
                    # Arrondi flottant : l'unité tient dans le plafond (vérifié ci-dessus)
                    qty_fits = 1
                if qty_fits <= 0:
                    flush()
                    continue
                ttc_fits = self._get_ttc_for_qty(line, qty_fits)
                current.append({'line': line, 'qty': qty_fits, 'ttc': ttc_fits, 'is_deposit': False})
                current_total += ttc_fits
                qty_remaining -= qty_fits

        flush()
        return invoices

    def action_create_invoices(self):
        self.ensure_one()
        split = self._get_split_plan()
        order = self.sale_order_id
        created = self.env['account.move']

        for invoice_lines in split:
            move_vals = order._prepare_invoice()
            move_vals.pop('invoice_line_ids', None)

            if self.invoice_partner_id:
                move_vals['partner_id'] = self.invoice_partner_id.id
                move_vals['partner_shipping_id'] = self.invoice_partner_id.id
                move_vals['l10n_ma_origin_partner_id'] = order.partner_id.id

            move = self.env['account.move'].with_context(
                default_move_type='out_invoice'
            ).create(move_vals)

            product_items = [i for i in invoice_lines if not i['is_deposit']]
            deposit_items = [i for i in invoice_lines if i['is_deposit']]

            line_vals_list = []
            seq = 1
            for item in product_items:
                vals = item['line']._prepare_invoice_line(sequence=seq, quantity=item['qty'])
                line_vals_list.append((0, 0, vals))
                seq += 1

            # Injection du UG dans chaque facture en mode campagne (si disponible)
            ug_pending = False
            if self.campaign_mode:
                ug_pending = self.env['stock.ug.pending']._get_next_pending()
                if ug_pending:
                    line_vals_list.append((0, 0, {
                        'product_id': ug_pending.product_id.id,
                        'quantity': 1,
                        'price_unit': 0.0,
                        'name': _('%s (Unité Gratuite - Campagne)') % ug_pending.product_id.display_name,
                        'sequence': seq,
                    }))
                    seq += 1

            # Déduction des acomptes (même mécanique qu'Odoo standard : section + quantité négative)
            if deposit_items:
                line_vals_list.append((0, 0, order._prepare_down_payment_section_line(sequence=seq)))
                seq += 1
                for item in deposit_items:
                    vals = item['line']._prepare_invoice_line(sequence=seq, quantity=-item['qty'])
                    line_vals_list.append((0, 0, vals))
                    seq += 1

            move.write({'invoice_line_ids': line_vals_list})

            # Consommer le UG pending après écriture de la facture
            if ug_pending:
                ug_pending._consume(1)

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
