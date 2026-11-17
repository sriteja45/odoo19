from psycopg2 import IntegrityError

from odoo import api, fields, models


class FeedbackReviewVote(models.Model):
    """Phase 1 audit / Phase 4 cleanup note on access design (intentional,
    not a gap): portal and public groups have explicit perm=0 ACL rows
    (ir.model.access.csv) for this model. Voting is only ever reachable
    through FeedbackPortalController.feedback_review_vote(), which runs
    under sudo() after validating the review is approved and applying its
    own one-vote-per-visitor logic (apply_vote below). There is
    intentionally no other read/write path into this model for anonymous
    or portal users.
    """
    _name = 'feedback.review.vote'
    _description = 'Helpful / Not Helpful vote on a Customer Review'
    _order = 'create_date desc'

    review_id = fields.Many2one('feedback.review', string='Review', required=True,
                                 ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Voter (if logged in)')
    company_id = fields.Many2one('res.company', related='review_id.company_id', store=True, index=True, readonly=True)

    # Identifies one visitor for one review so the same person can't vote
    # twice. Logged-in users are keyed by partner ("partner-<id>"), anonymous
    # website visitors by their session id ("session-<sid>"). A single Char
    # field keeps this a plain unique(review_id, voter_key) constraint instead
    # of a conditional/partial index, which Odoo's simple Constraint helper
    # can't express.
    voter_key = fields.Char(string='Voter Key', required=True, index=True)

    vote = fields.Selection([
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
    ], string='Vote', required=True)

    _unique_voter_per_review = models.Constraint(
        'unique(review_id, voter_key)',
        'This visitor has already voted on this review.',
    )

    @api.model
    def apply_vote(self, review, voter_key, vote_value, partner_id=False):
        """Register, change, or retract (toggle off) a vote for one visitor
        on one review, then refresh the review's cached counters.

        Returns 'added', 'updated', or 'removed' so the caller/UI can react
        (e.g. highlight the active button) without a second round trip.
        """
        existing = self.search([
            ('review_id', '=', review.id),
            ('voter_key', '=', voter_key),
        ], limit=1)

        if existing:
            if existing.vote == vote_value:
                existing.unlink()
                action = 'removed'
            else:
                existing.write({'vote': vote_value})
                action = 'updated'
        else:
            try:
                with self.env.cr.savepoint():
                    self.create({
                        'review_id': review.id,
                        'voter_key': voter_key,
                        'vote': vote_value,
                        'partner_id': partner_id or False,
                    })
                action = 'added'
            except IntegrityError:
                # Another concurrent request won the unique constraint. Re-read
                # and apply the requested state rather than returning a 500.
                existing = self.search([
                    ('review_id', '=', review.id),
                    ('voter_key', '=', voter_key),
                ], limit=1)
                if existing.vote == vote_value:
                    existing.unlink()
                    action = 'removed'
                else:
                    existing.write({'vote': vote_value})
                    action = 'updated'

        review._recompute_vote_counts()
        return action
