import base64
import io

from odoo import fields, models
from odoo.exceptions import UserError


class FeedbackReportWizard(models.TransientModel):
    """Ad-hoc export wizard covering FR-12 (Reporting): lets an administrator
    pick a date range and generate either the PDF ratings report or a
    multi-sheet Excel workbook (Average Rating by Product, Reviews by Month,
    Customer Satisfaction, Rating Distribution, Most/Least Reviewed Products,
    Pending Moderation)."""
    _name = 'feedback.report.wizard'
    _description = 'Customer Feedback Report Export'

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    xlsx_file = fields.Binary(string='Excel Report', readonly=True)
    xlsx_filename = fields.Char(string='Filename', readonly=True)

    def _review_domain(self, extra=None):
        domain = list(extra or [])
        if self.date_from:
            domain.append(('review_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('review_date', '<=', self.date_to))
        return domain

    def action_export_pdf(self):
        """Print the Product Ratings PDF report for every rated product,
        scoped to the selected date range."""
        self.ensure_one()
        products = self.env['product.template'].search([('rating_count', '>', 0)])
        if not products:
            raise UserError("There are no rated products to report on yet.")
        data = {
            'date_from': fields.Date.to_string(self.date_from) if self.date_from else False,
            'date_to': fields.Date.to_string(self.date_to) if self.date_to else False,
        }
        return self.env.ref('customer_feedback.action_report_product_ratings').report_action(products, data=data)

    def action_export_xlsx(self):
        """Build the Excel workbook and return a download action for it."""
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(
                "The 'xlsxwriter' Python library is required to export Excel "
                "reports. Please install it on the server (pip install xlsxwriter).")

        Review = self.env['feedback.review']
        Product = self.env['product.template']

        approved_reviews = Review.search(
            self._review_domain([('status', '=', 'approved')]), order='review_date asc')
        pending_reviews = Review.search(
            self._review_domain([('status', '=', 'pending')]), order='review_date asc')

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        bold = workbook.add_format({'bold': True})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1})
        pct_fmt = workbook.add_format({'num_format': '0.0%'})
        date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        self._write_rating_by_product_sheet(workbook, Product, header_fmt, date_fmt)
        self._write_reviews_by_month_sheet(workbook, approved_reviews, header_fmt)
        self._write_satisfaction_sheet(workbook, approved_reviews, pending_reviews, bold, pct_fmt)
        self._write_distribution_sheet(workbook, approved_reviews, header_fmt, pct_fmt)
        self._write_most_least_reviewed_sheet(workbook, Product, bold, header_fmt)
        self._write_pending_moderation_sheet(workbook, pending_reviews, header_fmt, date_fmt)

        workbook.close()
        output.seek(0)

        filename = 'Customer_Feedback_Report_%s.xlsx' % fields.Date.to_string(fields.Date.context_today(self))
        self.write({
            'xlsx_file': base64.b64encode(output.read()),
            'xlsx_filename': filename,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/feedback.report.wizard/%s/xlsx_file/%s?download=true' % (self.id, filename),
            'target': 'self',
        }

    # -- sheet builders -----------------------------------------------

    def _write_rating_by_product_sheet(self, workbook, Product, header_fmt, date_fmt):
        sheet = workbook.add_worksheet('Rating by Product')
        headers = ['Product', 'Average Rating', 'Total Reviews', '5*', '4*', '3*', '2*', '1*', 'Last Review Date']
        for col, title in enumerate(headers):
            sheet.write(0, col, title, header_fmt)
        products = Product.search([('rating_count', '>', 0)], order='rating_avg desc')
        for row, product in enumerate(products, start=1):
            sheet.write(row, 0, product.display_name)
            sheet.write(row, 1, product.rating_avg)
            sheet.write(row, 2, product.rating_count)
            sheet.write(row, 3, product.get_rating_distribution().get(5, 0))
            sheet.write(row, 4, product.get_rating_distribution().get(4, 0))
            sheet.write(row, 5, product.get_rating_distribution().get(3, 0))
            sheet.write(row, 6, product.get_rating_distribution().get(2, 0))
            sheet.write(row, 7, product.get_rating_distribution().get(1, 0))
            if product.get_last_review_date():
                sheet.write_datetime(row, 8, product.get_last_review_date(), date_fmt)
        sheet.set_column(0, 0, 32)

    def _write_reviews_by_month_sheet(self, workbook, approved_reviews, header_fmt):
        sheet = workbook.add_worksheet('Reviews by Month')
        for col, title in enumerate(['Month', 'Approved Reviews', 'Average Rating']):
            sheet.write(0, col, title, header_fmt)
        by_month = {}
        for review in approved_reviews:
            key = review.review_date.strftime('%Y-%m') if review.review_date else 'Unknown'
            by_month.setdefault(key, []).append(review.rating)
        for row, key in enumerate(sorted(by_month.keys()), start=1):
            ratings = by_month[key]
            sheet.write(row, 0, key)
            sheet.write(row, 1, len(ratings))
            sheet.write(row, 2, round(sum(ratings) / len(ratings), 2))
        sheet.set_column(0, 0, 14)

    def _write_satisfaction_sheet(self, workbook, approved_reviews, pending_reviews, bold, pct_fmt):
        sheet = workbook.add_worksheet('Customer Satisfaction')
        total = len(approved_reviews)
        positive = len(approved_reviews.filtered(lambda r: r.rating >= 4))
        negative = len(approved_reviews.filtered(lambda r: r.rating <= 2))
        avg = round(sum(approved_reviews.mapped('rating')) / total, 2) if total else 0.0
        rows = [
            ('Total Approved Reviews', total, False),
            ('Average Rating', avg, False),
            ('Satisfied (4-5 Stars)', positive, False),
            ('Satisfaction Rate', (positive / total) if total else 0.0, True),
            ('Dissatisfied (1-2 Stars)', negative, False),
            ('Dissatisfaction Rate', (negative / total) if total else 0.0, True),
            ('Pending Moderation', len(pending_reviews), False),
        ]
        for row, (label, value, is_pct) in enumerate(rows):
            sheet.write(row, 0, label, bold)
            sheet.write(row, 1, value, pct_fmt if is_pct else None)
        sheet.set_column(0, 0, 28)

    def _write_distribution_sheet(self, workbook, approved_reviews, header_fmt, pct_fmt):
        sheet = workbook.add_worksheet('Rating Distribution')
        for col, title in enumerate(['Stars', 'Reviews', 'Percentage']):
            sheet.write(0, col, title, header_fmt)
        total = len(approved_reviews)
        counts = {i: len(approved_reviews.filtered(lambda r, i=i: r.rating == i)) for i in range(1, 6)}
        for row, stars in enumerate(range(5, 0, -1), start=1):
            sheet.write(row, 0, '%s Star%s' % (stars, '' if stars == 1 else 's'))
            sheet.write(row, 1, counts[stars])
            sheet.write(row, 2, (counts[stars] / total) if total else 0.0, pct_fmt)
        sheet.set_column(0, 0, 14)

    def _write_most_least_reviewed_sheet(self, workbook, Product, bold, header_fmt):
        sheet = workbook.add_worksheet('Most & Least Reviewed')
        sheet.write(0, 0, 'Most Reviewed Products', bold)
        sheet.write(0, 2, 'Least Reviewed Products', bold)
        for col, title in enumerate(['Product', 'Reviews', 'Product', 'Reviews']):
            sheet.write(1, col, title, header_fmt)
        most = Product.search([('rating_count', '>', 0)], order='rating_count desc', limit=10)
        least = Product.search([('rating_count', '>', 0)], order='rating_count asc', limit=10)
        for row, product in enumerate(most, start=2):
            sheet.write(row, 0, product.display_name)
            sheet.write(row, 1, product.rating_count)
        for row, product in enumerate(least, start=2):
            sheet.write(row, 2, product.display_name)
            sheet.write(row, 3, product.rating_count)
        sheet.set_column(0, 0, 28)
        sheet.set_column(2, 2, 28)

    def _write_pending_moderation_sheet(self, workbook, pending_reviews, header_fmt, date_fmt):
        sheet = workbook.add_worksheet('Pending Moderation')
        headers = ['Submitted', 'Customer', 'Product', 'Rating', 'Title']
        for col, title in enumerate(headers):
            sheet.write(0, col, title, header_fmt)
        for row, review in enumerate(pending_reviews, start=1):
            if review.review_date:
                sheet.write_datetime(row, 0, review.review_date, date_fmt)
            sheet.write(row, 1, review.customer_id.display_name)
            sheet.write(row, 2, review.product_id.display_name)
            sheet.write(row, 3, review.rating)
            sheet.write(row, 4, review.review_title or '')
        sheet.set_column(1, 2, 26)
