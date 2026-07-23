from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        ug_location = self.env.ref(
            'l10n_ma_sale_invoice_split.stock_location_ug_delivered',
            raise_if_not_found=False,
        )
        ug_move_ids = []

        if ug_location:
            for picking in self:
                ug_moves = picking.move_ids.filtered(
                    lambda m: m.state not in ('done', 'cancel')
                    and m.sale_line_id
                    and m.sale_line_id.product_id.is_ug
                    and not m.origin_returned_move_id
                )
                if ug_moves:
                    ug_moves.write({'location_dest_id': ug_location.id})
                    ug_moves.move_line_ids.write({'location_dest_id': ug_location.id})
                    ug_move_ids.extend(ug_moves.ids)

        res = super()._action_done()

        if ug_move_ids:
            done_ug = self.env['stock.move'].browse(ug_move_ids).filtered(
                lambda m: m.state == 'done'
            )
            for move in done_ug:
                self.env['stock.ug.pending']._register_ug_move(move)

        for picking in self:
            if picking.return_id:
                return_ug_moves = picking.move_ids.filtered(
                    lambda m: m.state == 'done'
                    and m.origin_returned_move_id
                    and m.sale_line_id
                    and m.sale_line_id.product_id.is_ug
                )
                if return_ug_moves:
                    self.env['stock.ug.pending']._handle_ug_return(return_ug_moves)

        return res

