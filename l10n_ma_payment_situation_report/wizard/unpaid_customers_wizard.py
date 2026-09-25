from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UnpaidCustomersReportWizard(models.TransientModel):
    _name = 'unpaid.customers.report.wizard'
    _description = 'Situation des impayés - tous clients (factures fractionnées incluses)'

    date_to = fields.Date(
        string='Situation au',
        required=True,
        default=fields.Date.context_today,
    )
    restrict_partners = fields.Boolean(
        string='Restreindre à des clients précis',
        default=False,
        help='Si coché, seuls les clients sélectionnés apparaîtront. Sinon, tous les clients avec un impayé seront listés.',
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Clients',
        #domain=[('customer_rank', '>', 0)],
        help='Restreint le rapport à ces clients (si "Restreindre à des clients précis" est coché).',
    )

    @api.constrains('date_to', 'restrict_partners', 'partner_ids')
    def _check_wizard(self):
        for wiz in self:
            if wiz.restrict_partners and not wiz.partner_ids:
                raise UserError(_("Veuillez sélectionner au moins un client ou décocher la restriction."))

    def _get_customers_data(self):
        """Retourne la liste des clients ayant un impayé, triée par impayé décroissant.

        Chaque élément : dict(partner, invoice_count, invoiced, paid, balance).
        """
        self.ensure_one()
        domain = [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '<=', self.date_to),
        ]
        if self.restrict_partners:
            pids = self.partner_ids.ids
            domain += ['|'] * (2 * len(pids) - 1) + [
                term for pid in pids for term in
                [('l10n_ma_origin_partner_id', '=', pid), ('partner_id', '=', pid)]
            ]
        moves = self.env['account.move'].search_read(
            domain,
            ['name', 'move_type', 'amount_total', 'l10n_ma_origin_partner_id', 'partner_id'],
        )
        move_ids = [m['id'] for m in moves]

        # Payé : uniquement les rapprochements avec des paiements réels (account.payment)
        paid_by_move = {}
        if move_ids:
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
            """, [tuple(move_ids)])
            paid_by_move = dict(self.env.cr.fetchall())

        # Agrégation par client (client réel d'origine, sinon partenaire de la facture)
        customers = {}
        for m in moves:
            pid = m['l10n_ma_origin_partner_id'] and m['l10n_ma_origin_partner_id'][0] or m['partner_id'][0]
            c = customers.setdefault(pid, {'invoice_count': 0, 'invoiced': 0.0, 'paid': 0.0})
            c['invoice_count'] += 1
            sign = -1 if m['move_type'] == 'out_refund' else 1
            c['invoiced'] += sign * m['amount_total']
            c['paid'] += paid_by_move.get(m['id'], 0.0)

        result = []
        for pid, c in customers.items():
            balance = c['invoiced'] - c['paid']
            if balance > 0:
                result.append({
                    'partner': self.env['res.partner'].browse(pid),
                    'invoice_count': c['invoice_count'],
                    'invoiced': c['invoiced'],
                    'paid': c['paid'],
                    'balance': balance,
                })
        result.sort(key=lambda r: r['balance'], reverse=True)
        return result

    def action_print_report(self):
        self.ensure_one()
        if self.restrict_partners and not self.partner_ids:
            raise UserError(_("Veuillez sélectionner au moins un client ou décocher la restriction."))
        return self.env.ref(
            'l10n_ma_payment_situation_report.action_report_unpaid_customers'
        ).report_action(self)
