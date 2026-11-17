from .common import FeedbackTestCommon


class TestFeedbackReviewVotes(FeedbackTestCommon):

    def _make_review(self):
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'rating': 5,
            'review_text': 'Great product, exactly as described.',
        })
        review.action_approve()
        return review

    def test_vote_added_and_counted(self):
        review = self._make_review()
        self.env['feedback.review.vote'].apply_vote(review, 'session-abc', 'helpful')
        self.assertEqual(review.helpful_count, 1)
        self.assertEqual(review.not_helpful_count, 0)

    def test_same_voter_toggles_vote_off(self):
        review = self._make_review()
        Vote = self.env['feedback.review.vote']
        Vote.apply_vote(review, 'session-abc', 'helpful')
        action = Vote.apply_vote(review, 'session-abc', 'helpful')
        self.assertEqual(action, 'removed')
        self.assertEqual(review.helpful_count, 0)

    def test_same_voter_switches_vote(self):
        review = self._make_review()
        Vote = self.env['feedback.review.vote']
        Vote.apply_vote(review, 'session-abc', 'helpful')
        action = Vote.apply_vote(review, 'session-abc', 'not_helpful')
        self.assertEqual(action, 'updated')
        self.assertEqual(review.helpful_count, 0)
        self.assertEqual(review.not_helpful_count, 1)

    def test_two_voters_counted_independently(self):
        review = self._make_review()
        Vote = self.env['feedback.review.vote']
        Vote.apply_vote(review, 'session-abc', 'helpful')
        Vote.apply_vote(review, 'partner-%s' % self.customer.id, 'not_helpful', self.customer.id)
        self.assertEqual(review.helpful_count, 1)
        self.assertEqual(review.not_helpful_count, 1)

    def test_duplicate_voter_key_constraint(self):
        review = self._make_review()
        self.env['feedback.review.vote'].create({
            'review_id': review.id,
            'voter_key': 'session-dup',
            'vote': 'helpful',
        })
        with self.assertRaises(Exception):
            self.env['feedback.review.vote'].create({
                'review_id': review.id,
                'voter_key': 'session-dup',
                'vote': 'not_helpful',
            })
