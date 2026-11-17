from odoo import models, fields, api


class MouserBalanceSheet(models.Model):
    _name = "mouser.balance.sheet"
    _description = "Balance Sheet"

    name = fields.Char(
        string="Report Name",
        default="Balance Sheet",
        required=True,
    )

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")

    assets = fields.Float(
        string="Total Assets",
        default=0.0,
    )

    liabilities = fields.Float(
        string="Total Liabilities",
        default=0.0,
    )

    equity = fields.Float(
        string="Equity",
        compute="_compute_equity",
        store=True,
    )

    @api.depends("assets", "liabilities")
    def _compute_equity(self):
        for rec in self:
            rec.equity = rec.assets - rec.liabilities

    def action_generate_report(self):

        for rec in self:

            sale_domain = [
                ("state", "in", ["sale", "done"])
            ]

            purchase_domain = [
                ("state", "in", ["purchase", "done"])
            ]

            if rec.date_from:
                sale_domain.append(
                    ("date_order", ">=", rec.date_from)
                )
                purchase_domain.append(
                    ("date_order", ">=", rec.date_from)
                )

            if rec.date_to:
                sale_domain.append(
                    ("date_order", "<=", rec.date_to)
                )
                purchase_domain.append(
                    ("date_order", "<=", rec.date_to)
                )

            sale_orders = self.env["sale.order"].search(sale_domain)
            purchase_orders = self.env["purchase.order"].search(
                purchase_domain
            )

            total_sales = sum(
                sale_orders.mapped("amount_total")
            )

            total_purchase = sum(
                purchase_orders.mapped("amount_total")
            )

            # Demo Balance Sheet Logic
            rec.assets = total_sales
            rec.liabilities = total_purchase

        return True