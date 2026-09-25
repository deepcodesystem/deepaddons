import os
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PaymentSituationReportWizard(models.TransientModel):
    _name = 'payment.situation.report.wizard'
    _description = 'Situation de paiement par client (factures fractionnées incluses)'

    partner_ids = fields.Many2many(
        'res.partner',
        string='Clients',
        required=True,
        domain=[('customer_rank', '>', 0)],
        help='Un ou plusieurs clients. Un PDF unique contenant une section par client sera généré.',
    )
    date_from = fields.Date(
        string='Du',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='Au',
        required=True,
        default=fields.Date.context_today,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_from and wiz.date_to and wiz.date_from > wiz.date_to:
                raise UserError(_("La date 'Du' doit être antérieure ou égale à la date 'Au'."))

    def _get_invoices_domain(self, partner):
        return [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            '|',
            ('l10n_ma_origin_partner_id', '=', partner.id),
            ('partner_id', '=', partner.id),
        ]

    def _get_orders_for_partner(self, partner):
        """Retourne [(order_key, order_name, invoices)] regroupé par bon de commande."""
        self.ensure_one()
        invoices = self.env['account.move'].search_read(
            self._get_invoices_domain(partner),
            ['name', 'move_type', 'amount_total', 'amount_residual', 'invoice_origin', 'partner_id'],
        )
        invoice_ids = [inv['id'] for inv in invoices]
        # Lien facture -> SO via les lignes de facture (sale_line_id.order_id)
        order_link = {}
        if invoice_ids:
            self.env.cr.execute("""
                SELECT DISTINCT aml.move_id, so.id, so.name
                FROM sale_order_line_invoice_rel rel
                JOIN sale_order_line sol ON sol.id = rel.order_line_id
                JOIN sale_order so ON so.id = sol.order_id
                JOIN account_move_line aml ON aml.id = rel.invoice_line_id
                WHERE aml.move_id IN %s
            """, [tuple(invoice_ids)])
            for move_id, so_id, so_name in self.env.cr.fetchall():
                order_link[move_id] = (so_id, so_name)

        groups = {}
        for inv in invoices:
            link = order_link.get(inv['id'])
            if link:
                order_key = link[0]
                order_name = link[1]
            else:
                order_key = 0
                order_name = inv['invoice_origin'] or _('Sans commande')
            group = groups.setdefault(order_key, {
                'name': order_name,
                'invoice_count': 0,
                'invoiced': 0.0,
                'paid': 0.0,
            })
            group['invoice_count'] += 1
            # Les avoirs (out_refund) ont un amount_total positif en base :
            # on les soustrait de la facturation.
            sign = -1 if inv['move_type'] == 'out_refund' else 1
            group['invoiced'] += sign * inv['amount_total']

        # Total payé : uniquement les rapprochements avec des paiements réels
        # (account.payment). Les rapprochements facture <-> avoir ne sont PAS
        # des paiements : l'avoir est déjà déduit de la facturation.
        if invoice_ids:
            self.env.cr.execute("""
                SELECT aml.move_id,
                       SUM(CASE WHEN p.credit_move_id = aml.id THEN -p.amount ELSE p.amount END)
                FROM account_move_line aml
                JOIN account_partial_reconcile p
                     ON p.debit_move_id = aml.id OR p.credit_move_id = aml.id
                JOIN account_move_line cml
                     ON cml.id IN (p.debit_move_id, p.credit_move_id) AND cml.id != aml.id
                JOIN account_move cm ON cm.id = cml.move_id
                JOIN account_payment ap ON ap.move_id = cm.id
                WHERE aml.move_id IN %s
                GROUP BY aml.move_id
            """, [tuple(invoice_ids)])
            paid_by_move = dict(self.env.cr.fetchall())
        else:
            paid_by_move = {}

        for inv in invoices:
            link = order_link.get(inv['id'])
            order_key = link[0] if link else 0
            if order_key in groups:
                groups[order_key]['paid'] += paid_by_move.get(inv['id'], 0.0)

        result = [
            (key, g['name'], g['invoice_count'], g['invoiced'], g['paid'])
            for key, g in groups.items()
        ]
        # Tri : bon de commande réel d'abord par nom, "Sans commande" en dernier
        result.sort(key=lambda r: (r[0] == 0, r[1]))
        return result

    def _get_report_data(self):
        self.ensure_one()
        data = []
        for partner in self.partner_ids:
            orders = self._get_orders_for_partner(partner)
            total_invoiced = sum(o[3] for o in orders)
            total_paid = sum(o[4] for o in orders)
            data.append({
                'partner': partner,
                'orders': orders,
                'total_invoiced': total_invoiced,
                'total_paid': total_paid,
                'total_balance': total_invoiced - total_paid,
            })
        return data

    def action_print_report(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError(_("Veuillez sélectionner au moins un client."))
        return self.env.ref(
            'l10n_ma_payment_situation_report.action_report_payment_situation'
        ).report_action(self)
