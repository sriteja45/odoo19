from odoo import models, fields, api


class MouserExecutiveSummary(models.Model):
    _name = "mouser.executive.summary"
    _description = "Executive Summary"

    name = fields.Char(
        string="Report Name",
        default="Executive Summary",
        required=True,
    )

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")

    total_sales = fields.Float(
        string="Total Sales",
        default=0.0,
    )

    total_purchase = fields.Float(
        string="Total Purchases",
        default=0.0,
    )

    total_assets = fields.Float(
        string="Total Assets",
        default=0.0,
    )

    total_liabilities = fields.Float(
        string="Total Liabilities",
        default=0.0,
    )

    gross_profit = fields.Float(
        string="Gross Profit",
        compute="_compute_summary",
        store=True,
    )

    net_profit = fields.Float(
        string="Net Profit",
        compute="_compute_summary",
        store=True,
    )

    equity = fields.Float(
        string="Equity",
        compute="_compute_summary",
        store=True,
    )

    profit_margin = fields.Float(
        string="Profit Margin (%)",
        compute="_compute_summary",
        store=True,
    )

    @api.depends(
        "total_sales",
        "total_purchase",
        "total_assets",
        "total_liabilities",
    )
    def _compute_summary(self):
        for rec in self:

            rec.gross_profit = (
                rec.total_sales - rec.total_purchase
            )

            rec.net_profit = rec.gross_profit

            rec.equity = (
                rec.total_assets - rec.total_liabilities
            )

            if rec.total_sales > 0:
                rec.profit_margin = (
                    rec.net_profit / rec.total_sales
                ) * 100
            else:
                rec.profit_margin = 0.0

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

            sale_orders = self.env["sale.order"].search(
                sale_domain
            )

            purchase_orders = self.env["purchase.order"].search(
                purchase_domain
            )

            total_sales = sum(
                sale_orders.mapped("amount_total")
            )

            total_purchase = sum(
                purchase_orders.mapped("amount_total")
            )

            rec.total_sales = total_sales
            rec.total_purchase = total_purchase

            # For this simplified reporting module
            rec.total_assets = total_sales
            rec.total_liabilities = total_purchase

        return True