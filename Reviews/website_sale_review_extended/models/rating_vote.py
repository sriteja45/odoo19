# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RatingVote(models.Model):
    """ NEW supporting model.

    Technical justification for NOT extending an existing model instead:
    Odoo core has no concept of "another customer found this review
    helpful". There is no field, mixin or table anywhere in 'rating' or
    'portal_rating' that tracks a per-(review, voter) opinion, so there is
    nothing to extend. A tiny join model is the standard Odoo pattern for
    this (mirrors how e.g. 'mail.message.reaction' is modelled in core).
    Everything this model reports through (helpful_count/unhelpful_count)
    is exposed back onto the EXISTING rating.rating record, not a parallel
    review system.
    """
    _name = 'rating.vote'
    _description = "Review Helpful/Unhelpful Vote"
    _rec_name = 'rating_id'

    rating_id = fields.Many2one('rating.rating', string="Review", required=True,
                                 ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string="Voter", required=True,
                                  ondelete='cascade', index=True)
    vote_type = fields.Selection(
        selection=[('helpful', 'Helpful'), ('unhelpful', 'Not Helpful')],
        string="Vote", required=True,
    )

    _sql_constraints = [
        ('uniq_partner_vote_per_rating',
         'unique(rating_id, partner_id)',
         "You have already voted on this review."),
    ]

    @api.model
    def _get_user_vote(self, rating_id):
        """Return the current user's vote_type ('helpful'/'unhelpful'/False)
        for a given review, used by the frontend to show the button as
        already-pressed."""
        partner = self.env.user.partner_id
        if self.env.user._is_public() or not rating_id:
            return False
        vote = self.sudo().search([
            ('rating_id', '=', rating_id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        return vote.vote_type if vote else False

    @api.model
    def set_vote(self, rating_id, vote_type):
        """Create/update/toggle-off the current portal user's vote on a
        review. Called from the frontend controller (see
        controllers/review_controller.py)."""
        if self.env.user._is_public():
            raise UserError(_("You must be logged in to vote on a review."))
        if vote_type not in ('helpful', 'unhelpful'):
            raise UserError(_("Invalid vote type."))

        rating = self.env['rating.rating'].sudo().browse(int(rating_id))
        if not rating.exists():
            raise UserError(_("Review not found."))

        partner = self.env.user.partner_id
        # A customer cannot vote on their own review.
        if rating.partner_id and rating.partner_id.commercial_partner_id == partner.commercial_partner_id:
            raise UserError(_("You cannot vote on your own review."))

        existing = self.sudo().search([
            ('rating_id', '=', rating.id),
            ('partner_id', '=', partner.id),
        ], limit=1)

        if existing and existing.vote_type == vote_type:
            # Clicking the same button again removes the vote (toggle off).
            existing.unlink()
            new_vote = False
        elif existing:
            existing.vote_type = vote_type
            new_vote = vote_type
        else:
            self.sudo().create({
                'rating_id': rating.id,
                'partner_id': partner.id,
                'vote_type': vote_type,
            })
            new_vote = vote_type

        rating.invalidate_recordset(['helpful_count', 'unhelpful_count'])
        return {
            'helpful_count': rating.helpful_count,
            'unhelpful_count': rating.unhelpful_count,
            'user_vote': new_vote,
        }
