from odoo import models, fields, api


class MouserProfitLoss(models.Model):
    _name = "mouser.profit.loss"
    _description = "Profit and Loss Report"

    name = fields.Char(
        string="Report Name",
        default="Profit & Loss",
        required=True,
    )

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")

    # ---------------------------------------------------------
    # Internal fields (Hidden in UI)
    # ---------------------------------------------------------

    revenue = fields.Float(default=0.0)
    cost_of_revenue = fields.Float(default=0.0)

    # Orders used for this report
    sale_order_ids = fields.Many2many(
        "sale.order",
        string="Sales Orders",
        readonly=True,
    )

    purchase_order_ids = fields.Many2many(
        "purchase.order",
        string="Purchase Orders",
        readonly=True,
    )

    # ---------------------------------------------------------
    # Report Summary Fields
    # ---------------------------------------------------------

    gross_profit = fields.Float(
        string="Gross Profit",
        compute="_compute_profit",
        store=True,
    )

    expenses = fields.Float(
        string="Operating Expenses",
        default=0.0,
    )

    operating_profit = fields.Float(
        string="Operating Profit",
        compute="_compute_profit",
        store=True,
    )

    net_profit = fields.Float(
        string="Net Profit",
        compute="_compute_profit",
        store=True,
    )

    profit_margin = fields.Float(
        string="Profit Margin (%)",
        compute="_compute_profit",
        store=True,
    )

    # ---------------------------------------------------------
    # Profit Calculation
    # ---------------------------------------------------------

    @api.depends("revenue", "cost_of_revenue", "expenses")
    def _compute_profit(self):
        for rec in self:

            rec.gross_profit = rec.revenue - rec.cost_of_revenue

            rec.operating_profit = rec.gross_profit - rec.expenses

            rec.net_profit = rec.operating_profit

            if rec.revenue > 0:
                rec.profit_margin = (
                    rec.net_profit / rec.revenue
                ) * 100
            else:
                rec.profit_margin = 0.0

    # ---------------------------------------------------------
    # Generate Report
    # ---------------------------------------------------------

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

            # Fetch Orders
            sale_orders = self.env["sale.order"].search(sale_domain)
            purchase_orders = self.env["purchase.order"].search(
                purchase_domain
            )

            # Save orders used in report
            rec.sale_order_ids = [(6, 0, sale_orders.ids)]
            rec.purchase_order_ids = [(6, 0, purchase_orders.ids)]

            # Calculate totals
            total_sales = sum(
                sale_orders.mapped("amount_total")
            )

            total_purchase = sum(
                purchase_orders.mapped("amount_total")
            )

            # Hidden calculation values
            rec.revenue = total_sales
            rec.cost_of_revenue = total_purchase

            # Operating expenses are not implemented yet
            rec.expenses = 0.0

        return True