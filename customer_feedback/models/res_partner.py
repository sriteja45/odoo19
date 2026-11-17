from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    total_reviews = fields.Integer(string='Total Reviews Given', compute='_compute_review_stats')
    average_rating_given = fields.Float(string='Average Rating Given', digits=(3, 2), compute='_compute_review_stats')
    last_review_date = fields.Datetime(string='Last Review Date', compute='_compute_review_stats')

    def _compute_review_stats(self):
        """Batched in a single query for the whole recordset instead of one
        search() per partner - the previous per-record loop meant opening a
        list view with N customers issued N separate SQL queries, which
        does not scale to the SRS's stated 10k/50k-record volumes."""
        stats = {}
        if self.ids:
            for customer, avg_rating, count, last_date in self.env['feedback.review']._read_group(
                [('customer_id', 'in', self.ids), ('status', '=', 'approved')],
                groupby=['customer_id'],
                aggregates=['rating:avg', 'rating:count', 'review_date:max'],
            ):
                stats[customer.id] = (count, avg_rating, last_date)
        for partner in self:
            count, avg_rating, last_date = stats.get(partner.id, (0, 0.0, False))
            partner.total_reviews = count
            partner.average_rating_given = round(avg_rating, 2) if avg_rating else 0.0
            partner.last_review_date = last_date
