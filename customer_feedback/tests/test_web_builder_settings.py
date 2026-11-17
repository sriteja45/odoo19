# -*- coding: utf-8 -*-
"""Step 7 — settings used by Website Builder / product-page injection."""
from odoo.tests.common import tagged
from odoo.addons.customer_feedback.tests.common import FeedbackTestCommon


@tagged('post_install', '-at_install', 'customer_feedback')
class TestWebBuilderSettings(FeedbackTestCommon):
    """Ensure show_on_product_page config defaults and round-trips correctly."""

    def test_show_on_product_page_default_true(self):
        """Default must be True so product pages keep auto-injecting reviews."""
        icp = self.env['ir.config_parameter'].sudo()
        existing = icp.search([('key', '=', 'customer_feedback.show_on_product_page')])
        existing.unlink()
        val = icp.get_param('customer_feedback.show_on_product_page', 'True')
        self.assertEqual(val, 'True')

    def test_show_on_product_page_set_false(self):
        icp = self.env['ir.config_parameter'].sudo()
        settings = self.env['res.config.settings'].create({
            'feedback_show_on_product_page': False,
        })
        settings.execute()
        self.assertEqual(
            icp.get_param('customer_feedback.show_on_product_page'),
            'False',
        )

    def test_show_on_product_page_set_true(self):
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('customer_feedback.show_on_product_page', 'False')
        settings = self.env['res.config.settings'].create({
            'feedback_show_on_product_page': True,
        })
        settings.execute()
        self.assertEqual(
            icp.get_param('customer_feedback.show_on_product_page'),
            'True',
        )

    def test_get_values_includes_show_on_product_page(self):
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('customer_feedback.show_on_product_page', 'False')
        vals = self.env['res.config.settings'].get_values()
        self.assertIn('feedback_show_on_product_page', vals)
        self.assertFalse(vals['feedback_show_on_product_page'])
        icp.set_param('customer_feedback.show_on_product_page', 'True')
        vals = self.env['res.config.settings'].get_values()
        self.assertTrue(vals['feedback_show_on_product_page'])
