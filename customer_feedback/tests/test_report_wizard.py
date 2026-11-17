import base64

from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestReportWizard(FeedbackTestCommon):

    def _approve_one_review(self, rating=5):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.moderation_enabled', 'False')
        request = self._create_request()
        return self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': rating,
            'review_text': 'Great build quality and arrived earlier than expected.',
        })

    def test_01_xlsx_export_generates_file(self):
        self._approve_one_review()
        wizard = self.env['feedback.report.wizard'].create({})
        action = wizard.action_export_xlsx()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertTrue(wizard.xlsx_file)
        self.assertTrue(wizard.xlsx_filename.endswith('.xlsx'))
        # A valid xlsx is a zip archive - confirm the magic bytes.
        raw = base64.b64decode(wizard.xlsx_file)
        self.assertEqual(raw[:2], b'PK')

    def test_02_pdf_export_returns_report_action(self):
        self._approve_one_review()
        wizard = self.env['feedback.report.wizard'].create({})
        action = wizard.action_export_pdf()
        self.assertEqual(action.get('report_name'), 'customer_feedback.report_product_ratings_document')

    def test_03_pdf_export_without_reviews_raises(self):
        wizard = self.env['feedback.report.wizard'].create({})
        with self.assertRaises(Exception):
            wizard.action_export_pdf()

    def test_04_date_filter_excludes_out_of_range_reviews(self):
        review = self._approve_one_review()
        # Push the review date out of range, then confirm the wizard's
        # own domain helper excludes it.
        review.write({'review_date': '2000-01-01 00:00:00'})
        wizard = self.env['feedback.report.wizard'].create({
            'date_from': '2099-01-01',
            'date_to': '2099-12-31',
        })
        domain = wizard._review_domain([('status', '=', 'approved')])
        matches = self.env['feedback.review'].search(domain)
        self.assertNotIn(review, matches)
