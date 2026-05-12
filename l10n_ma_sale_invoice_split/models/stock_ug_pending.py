from odoo import api, fields, models


class StockUgPending(models.Model):
    _name = 'stock.ug.pending'
    _description = 'UG Livrés en attente de facturation'
    _order = 'date asc'

    product_id = fields.Many2one('product.product', string='Produit UG', required=True, readonly=True)
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id', string='Modèle produit')
    partner_id = fields.Many2one('res.partner', string='Client livré', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Bon de commande', readonly=True)
    sale_line_id = fields.Many2one('sale.order.line', string='Ligne BDC', readonly=True)
    stock_move_id = fields.Many2one('stock.move', string='Mouvement stock', readonly=True)
    date = fields.Datetime(string='Date livraison', default=fields.Datetime.now, readonly=True)
    qty_done = fields.Float(string='Qté livrée', digits=(16, 0), readonly=True)
    qty_invoiced = fields.Float(string='Qté facturée', digits=(16, 0), default=0.0)
    qty_pending = fields.Float(
        string='Qté en attente',
        compute='_compute_qty_pending',
        store=True,
        digits=(16, 0),
    )

    @api.depends('qty_done', 'qty_invoiced')
    def _compute_qty_pending(self):
        for rec in self:
            rec.qty_pending = rec.qty_done - rec.qty_invoiced

    @api.model
    def _register_ug_move(self, move):
        qty = move.quantity
        if qty <= 0:
            return
        self.create({
            'product_id': move.product_id.id,
            'partner_id': move.picking_id.partner_id.id if move.picking_id else False,
            'sale_order_id': move.sale_line_id.order_id.id if move.sale_line_id else False,
            'sale_line_id': move.sale_line_id.id if move.sale_line_id else False,
            'stock_move_id': move.id,
            'qty_done': qty,
        })

    @api.model
    def _get_next_pending(self):
        """Retourne le prochain UG à facturer (FIFO par date livraison)."""
        return self.search([('qty_pending', '>', 0)], order='date asc', limit=1)

    def _consume(self, qty=1):
        self.ensure_one()
        self.qty_invoiced += qty

