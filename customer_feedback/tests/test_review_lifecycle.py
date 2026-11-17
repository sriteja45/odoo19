from odoo.tests import HttpCase, tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestReviewLifecycle(HttpCase, FeedbackTestCommon):
    """Phase 5 (Review Workflow) closing test: exercises the full,
    documented lifecycle end to end in a single test, rather than relying
    on the coverage being merely the union of the other per-feature test
    files:

        verified purchase (delivery)
            -> feedback.request auto-created
            -> secure token
            -> public portal review submission
            -> moderation (pending -> approved)
            -> native rating.rating sync (rating_avg / rating_count)
            -> helpful vote
            -> product-page distribution stats (get_rating_distribution())

    Each stage already has dedicated unit coverage elsewhere
    (test_feedback_request.py, test_feedback_review.py, test_rating_bridge.py,
    test_review_votes.py, test_product_rating.py). This test's job is only to
    prove the stages actually chain together correctly for one customer/
    product journey, which is the acceptance criterion in
    doc/ACCEPTANCE_TESTS.md row 1 ("Full happy-path lifecycle").
    """

    def test_01_full_lifecycle_happy_path(self):
        # Enable moderation explicitly so the pending step is exercised.
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.moderation_enabled', 'True')

        # -- 1. Verified purchase -> invitation request auto-created on delivery
        feedback_request = self._create_request()
        self.assertTrue(feedback_request.token)
        self.assertEqual(feedback_request.status, 'pending')
        self.assertEqual(feedback_request.partner_id, self.customer)
        self.assertEqual(feedback_request.product_id, self.product)

        # -- 2. Token-secured public portal form is reachable and the
        #       invitation link resolves to it.
        self.assertEqual(feedback_request.get_portal_url(), '/feedback/review/%s' % feedback_request.token)
        response = self.url_open(feedback_request.get_portal_url())
        self.assertEqual(response.status_code, 200)

        # -- 3. Public review submission via the token-secured form (no login)
        submit_response = self.url_open(
            feedback_request.get_portal_url() + '/submit',
            data={
                'rating': '5',
                'review_title': 'Great purchase',
                'review_text': 'Exactly as described, arrived quickly, very happy overall.',
                'csrf_token': self._get_csrf_token(feedback_request.get_portal_url()),
            },
        )
        self.assertIn(submit_response.status_code, (200, 303))

        feedback_request.invalidate_recordset()
        self.assertEqual(feedback_request.status, 'submitted')
        review = feedback_request.review_id
        self.assertTrue(review)
        self.assertEqual(review.rating, 5)
        self.assertTrue(review.is_verified)

        # -- 4. Moderation: starts pending (moderation_enabled=True), not
        #       counted in native averages yet.
        self.assertEqual(review.status, 'pending')
        self.product.product_tmpl_id.invalidate_recordset()
        self.assertEqual(self.product.product_tmpl_id.rating_count, 0)

        # -- 5. Moderator approves -> bridged to native rating.rating
        review.action_approve()
        self.assertEqual(review.status, 'approved')
        self.assertTrue(review.rating_id)
        self.assertTrue(review.rating_id.consumed)

        self.product.product_tmpl_id.invalidate_recordset()
        tmpl = self.product.product_tmpl_id
        self.assertEqual(tmpl.rating_count, 1)
        self.assertEqual(tmpl.rating_avg, 5.0)
        self.assertEqual(tmpl.get_rating_distribution().get(5, 0), 1)

        # -- 6. Publication: the approved review appears in the public,
        #       verified review list used by the website snippet.
        self.assertIn(review, tmpl.review_ids)

        # -- 7. Helpful vote from an anonymous visitor
        vote_response = self.url_open(
            '/feedback/review/%s/vote' % review.id,
            data={'vote_type': 'helpful'},
        )
        self.assertEqual(vote_response.status_code, 200)
        review.invalidate_recordset()
        self.assertEqual(review.helpful_count, 1)

        # -- 8. Rejection later removes it from native averages but keeps
        #       the audit trail (rating_id row stays, just consumed=False).
        review.action_reject()
        self.assertFalse(review.rating_id.consumed)
        self.product.product_tmpl_id.invalidate_recordset()
        self.assertEqual(self.product.product_tmpl_id.rating_count, 0)

    def _get_csrf_token(self, url):
        # The portal review form is a plain website page; fetch it once to
        # obtain a valid csrf token for the POST, mirroring how a real
        # browser session would submit the form.
        import re
        html = self.url_open(url).text
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        return match.group(1) if match else ''
