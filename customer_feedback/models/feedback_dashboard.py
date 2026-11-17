# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FeedbackDashboard(models.TransientModel):
    _name = 'feedback.dashboard'
    _description = 'Customer Feedback Dashboard'

    pending_review_count = fields.Integer(compute='_compute_dashboard_data')
    approved_review_count = fields.Integer(compute='_compute_dashboard_data')
    rejected_review_count = fields.Integer(compute='_compute_dashboard_data')
    total_review_count = fields.Integer(compute='_compute_dashboard_data')
    average_rating = fields.Float(compute='_compute_dashboard_data', digits=(3, 2))
    top_rated_product_ids = fields.Many2many(
        'product.template', string='Top Rated Products', compute='_compute_dashboard_data')
    lowest_rated_product_ids = fields.Many2many(
        'product.template', string='Lowest Rated Products', compute='_compute_dashboard_data')
    recent_review_ids = fields.Many2many(
        'feedback.review', string='Recent Reviews', compute='_compute_dashboard_data')

    @api.depends()
    def _compute_dashboard_data(self):
        """Prefer native aggregates and _read_group; avoid loading all reviews.

        - Counts / average: single grouped query on feedback.review
        - Top / lowest products: native product.template.rating_avg / rating_count
        - Recent list: limited search only
        """
        Review = self.env['feedback.review']
        Product = self.env['product.template']

        # Status counts in one grouped query
        status_counts = dict.fromkeys(
            ('pending', 'approved', 'rejected', 'draft', 'hidden'), 0)
        for status, count in Review._read_group(
                domain=[], groupby=['status'], aggregates=['__count']):
            if status in status_counts:
                status_counts[status] = count
        total = sum(status_counts.values())

        # Average of approved ratings: prefer SQL aggregate, avoid loading all rows
        avg = 0.0
        approved_count = status_counts['approved']
        if approved_count:
            # Group by a constant-friendly key: status (already filtered)
            rows = Review._read_group(
                domain=[('status', '=', 'approved')],
                groupby=['status'],
                aggregates=['rating:avg', '__count'],
            )
            if rows:
                # row shape: (status, rating_avg, count) in Odoo 17+
                try:
                    _status, avg_val, _cnt = rows[0]
                    avg = round(float(avg_val or 0.0), 2)
                except (TypeError, ValueError, IndexError):
                    approved = Review.search([('status', '=', 'approved')])
                    avg = round(
                        sum(approved.mapped('rating')) / len(approved), 2
                    ) if approved else 0.0

        # Top / lowest: native rating.mixin fields (source of truth)
        top = Product.search(
            [('rating_count', '>', 0)],
            order='rating_avg desc, rating_count desc',
            limit=5,
        )
        lowest = Product.search(
            [('rating_count', '>', 0)],
            order='rating_avg asc, rating_count desc',
            limit=5,
        )
        recent = Review.search([], order='review_date desc', limit=10)

        for dashboard in self:
            dashboard.pending_review_count = status_counts['pending']
            dashboard.approved_review_count = status_counts['approved']
            dashboard.rejected_review_count = status_counts['rejected']
            dashboard.total_review_count = total
            dashboard.average_rating = avg
            dashboard.top_rated_product_ids = top
            dashboard.lowest_rated_product_ids = lowest
            dashboard.recent_review_ids = recent

    def action_open_pending(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'customer_feedback.action_feedback_review_moderation')

    def action_open_approved(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'customer_feedback.action_feedback_review')
        action['domain'] = [('status', '=', 'approved')]
        return action

    def action_open_rejected(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'customer_feedback.action_feedback_review')
        action['domain'] = [('status', '=', 'rejected')]
        return action

    def action_open_all_reviews(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'customer_feedback.action_feedback_review')

    def action_open_top_rated(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'customer_feedback.action_feedback_top_rated_products')

    def action_open_lowest_rated(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'customer_feedback.action_feedback_lowest_rated_products')

    def action_open_report_export(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'customer_feedback.action_feedback_report_wizard')
