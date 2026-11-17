from odoo import models


class FeedbackRatingsReport(models.AbstractModel):
    _name = 'report.customer_feedback.report_product_ratings_document'
    _description = 'Product Ratings PDF Report'

    def _get_report_values(self, docids, data=None):
        data = data or {}
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        products = self.env['product.template'].browse(docids)
        recent_reviews_by_product = {}
        for product in products:
            domain = [
                ('product_id.product_tmpl_id', '=', product.id),
                ('status', '=', 'approved'),
            ]
            if date_from:
                domain.append(('review_date', '>=', date_from))
            if date_to:
                domain.append(('review_date', '<=', date_to))
            recent_reviews_by_product[product.id] = self.env['feedback.review'].search(
                domain, order='review_date desc', limit=5)
        return {
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': products,
            'recent_reviews_by_product': recent_reviews_by_product,
            'date_from': date_from,
            'date_to': date_to,
        }
