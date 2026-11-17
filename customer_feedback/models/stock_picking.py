from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            if picking.state == 'done' and picking.picking_type_id.code == 'outgoing' and picking.sale_id:
                self.env['feedback.request'].sudo().create_from_picking(picking)
        return res
