from odoo import models, fields
from odoo.exceptions import UserError


class QevrixaBlogReview(models.Model):
    _name = 'qevrixa.blog.review'
    _description = 'Qevrixa Blog Review'
    _order = 'create_date desc'

    blog_id = fields.Many2one(
        'qevrixa.blog',
        string='Blog',
        required=True,
        ondelete='cascade'
    )

    reviewer_id = fields.Many2one(
        'res.users',
        string='Reviewer',
        required=True
    )

    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('changes_required', 'Changes Required'),
    ], string='Review Status', default='pending', required=True)

    comments = fields.Text(
        string='Review Comments'
    )

    reviewed_date = fields.Datetime(
        string='Reviewed Date'
    )

    # ==========================================================
    # APPROVE REVIEW
    # ==========================================================

    def action_approve(self):
        for review in self:

            if review.reviewer_id != self.env.user:
                raise UserError(
                    "You can only review blogs assigned to you."
                )

            if review.status != 'pending':
                raise UserError(
                    "This review has already been completed."
                )

            if not review.comments:
                raise UserError(
                    "Please enter review comments before approving."
                )

            review.write({
                'status': 'approved',
                'reviewed_date': fields.Datetime.now(),
            })

            review.blog_id._update_review_status()

        return True

    # ==========================================================
    # REQUEST CHANGES
    # ==========================================================

    def action_request_changes(self):
        for review in self:

            if review.reviewer_id != self.env.user:
                raise UserError(
                    "You can only review blogs assigned to you."
                )

            if review.status != 'pending':
                raise UserError(
                    "This review has already been completed."
                )

            if not review.comments:
                raise UserError(
                    "Please enter comments explaining the required changes."
                )

            review.write({
                'status': 'changes_required',
                'reviewed_date': fields.Datetime.now(),
            })

            review.blog_id._update_review_status()

        return True