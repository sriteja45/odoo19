from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestFeedbackMailTemplates(FeedbackTestCommon):
    """Rendering-only checks for the three mail templates.

    `mail.template.generate_email()` builds the fully rendered
    subject/body/recipients exactly as they would be sent, but does not
    open an SMTP connection or hit the network - so these tests catch
    QWeb/inline-template errors, missing fields, and broken links (the
    class of bug 'Email Testing' in the SRS is worried about) without
    requiring a configured mail server. Actual delivery, spam-filter
    behaviour, and how a real mail client renders the HTML still need a
    manual smoke test against a real SMTP relay on staging (see
    doc/STAGING_VALIDATION.md, section D, "Customer journey").
    """

    def test_01_invitation_template_renders(self):
        request = self._create_request()
        template = self.env.ref('customer_feedback.mail_template_feedback_invitation')
        rendered = template.generate_email(request.id, fields=['subject', 'body_html', 'email_to'])

        self.assertIn(self.product.name, rendered['subject'])
        self.assertIn(request.token, rendered['body_html'],
                       'The secure review link/token must be embedded in the invitation email.')
        self.assertIn('/feedback/review/', rendered['body_html'])
        self.assertEqual(rendered['email_to'], self.customer.email)

    def test_02_reminder_template_renders(self):
        request = self._create_request()
        template = self.env.ref('customer_feedback.mail_template_feedback_reminder')
        rendered = template.generate_email(request.id, fields=['subject', 'body_html', 'email_to'])

        self.assertIn(request.token, rendered['body_html'])
        self.assertIn('/feedback/review/', rendered['body_html'])
        self.assertEqual(rendered['email_to'], self.customer.email)

    def test_03_thankyou_template_renders(self):
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'rating': 5,
            'review_text': 'Great product, arrived quickly and well packaged.',
        })
        template = self.env.ref('customer_feedback.mail_template_feedback_thankyou')
        rendered = template.generate_email(review.id, fields=['subject', 'body_html', 'email_to'])

        self.assertIn(self.product.name, rendered['body_html'])
        self.assertEqual(rendered['email_to'], self.customer.email)

    def test_04_templates_render_without_optional_fields(self):
        """Templates must not error out when optional data (product image,
        review title/text) is absent - a common cause of send-time
        failures that only show up once real data is missing."""
        request = self._create_request()
        template = self.env.ref('customer_feedback.mail_template_feedback_invitation')
        # No image set on the test product - this should not raise.
        rendered = template.generate_email(request.id, fields=['subject', 'body_html'])
        self.assertTrue(rendered['body_html'])
