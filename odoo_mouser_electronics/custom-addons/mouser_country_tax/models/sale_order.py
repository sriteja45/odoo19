from odoo import models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_apply_tax(self):

        if not self.partner_id:
            return

        country = self.partner_id.country_id.code

        tax = False

        if country == 'IN':
            tax = self.env['account.tax'].search(
                [('name', '=', 'India GST 18%')],
                limit=1
            )

        elif country == 'US':
            tax = self.env['account.tax'].search(
                [('name', '=', 'USA Sales Tax 8%')],
                limit=1
            )

        elif country == 'CN':
            tax = self.env['account.tax'].search(
                [('name', '=', 'China VAT 13%')],
                limit=1
            )

        elif country == 'RU':
            tax = self.env['account.tax'].search(
                [('name', '=', 'Russia VAT 20%')],
                limit=1
            )

        if tax:
            for line in self.order_line:
                line.tax_id = [(6, 0, tax.ids)]