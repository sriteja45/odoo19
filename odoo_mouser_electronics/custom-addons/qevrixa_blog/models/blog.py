# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class QevrixaBlog(models.Model):
    _name = "qevrixa.blog"
    _description = "Qevrixa Blog"
    _order = "publish_date desc"

    # ==========================================================
    # BASIC BLOG INFORMATION
    # ==========================================================

    name = fields.Char(
        string="Blog Title",
        required=True,
    )

    slug = fields.Char(
        string="Slug",
    )

    image = fields.Image(
        string="Cover Image",
    )

    short_description = fields.Text(
        string="Short Description",
    )

    content = fields.Html(
        string="Blog Content",
    )

    category_id = fields.Many2one(
        "product.public.category",
        string="Product Category",
    )

    author_id = fields.Many2one(
        "res.users",
        string="Author",
        default=lambda self: self.env.user,
    )

    publish_date = fields.Date(
        string="Publish Date",
        default=fields.Date.today,
    )

    # ==========================================================
    # PUBLISHING
    # ==========================================================

    published = fields.Boolean(
        string="Published",
        default=False,
    )

    featured = fields.Boolean(
        string="Featured Blog",
        default=False,
    )

    # ==========================================================
    # BLOG WORKFLOW
    # ==========================================================

    workflow_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("review_completed", "Review Completed"),
            ("changes_required", "Changes Required"),
            ("ready_to_publish", "Ready to Publish"),
            ("published", "Published"),
        ],
        string="Workflow Status",
        default="draft",
        required=True,
        tracking=True,
    )

    # ==========================================================
    # REVIEWERS
    # ==========================================================

    reviewer_ids = fields.Many2many(
        "res.users",
        "qevrixa_blog_reviewer_rel",
        "blog_id",
        "user_id",
        string="Reviewers",
    )

    review_ids = fields.One2many(
        "qevrixa.blog.review",
        "blog_id",
        string="Reviews",
    )

    review_summary = fields.Text(
        string="Admin Review Summary",
    )

    # ==========================================================
    # BLOG STATISTICS
    # ==========================================================

    likes = fields.Integer(
        string="Likes",
        default=0,
    )

    dislikes = fields.Integer(
        string="Dislikes",
        default=0,
    )

    views = fields.Integer(
        string="Views",
        default=0,
    )

    comment_ids = fields.One2many(
        "qevrixa.blog.comment",
        "blog_id",
        string="Comments",
    )

    comments_count = fields.Integer(
        string="Comments",
        compute="_compute_comments_count",
        store=True,
    )

    # ==========================================================
    # COMPUTE METHODS
    # ==========================================================

    @api.depends("comment_ids")
    def _compute_comments_count(self):
        for blog in self:
            blog.comments_count = len(blog.comment_ids)

    # ==========================================================
    # REVIEW STATUS UPDATE
    # ==========================================================

    def _update_review_status(self):
        """
        Automatically update the blog workflow status
        based on reviewer decisions.
        """

        for blog in self:

            reviews = blog.review_ids

            if not reviews:
                continue

            # --------------------------------------------------
            # ANY REVIEWER REQUESTED CHANGES
            # --------------------------------------------------

            if any(
                review.status == "changes_required"
                for review in reviews
            ):
                blog.write({
                    "workflow_state": "changes_required",
                    "published": False,
                })
                continue

            # --------------------------------------------------
            # ALL REVIEWERS APPROVED
            # --------------------------------------------------

            if all(
                review.status == "approved"
                for review in reviews
            ):
                blog.write({
                    "workflow_state": "review_completed",
                    "published": False,
                })

    # ==========================================================
    # STEP 1 - SUBMIT FOR REVIEW
    # ==========================================================

    def action_submit_for_review(self):
        for blog in self:

            if not blog.content:
                raise UserError(
                    "Blog content is required before submitting for review."
                )

            if blog.workflow_state not in [
                "draft",
                "changes_required",
            ]:
                raise UserError(
                    "This blog cannot be submitted from its current state."
                )

            # Remove old review records when submitting again
            if blog.workflow_state == "changes_required":
                blog.review_ids.unlink()

            blog.write({
                "workflow_state": "submitted",
                "published": False,
            })

        return True

    # ==========================================================
    # STEP 2 - ADMIN SENDS TO REVIEWERS
    # ==========================================================

    def action_send_for_review(self):
        Review = self.env["qevrixa.blog.review"]

        for blog in self:

            if blog.workflow_state != "submitted":
                raise UserError(
                    "Only submitted blogs can be sent for review."
                )

            if not blog.reviewer_ids:
                raise UserError(
                    "Please assign at least one reviewer before "
                    "sending the blog for review."
                )

            # Remove old pending reviews
            old_reviews = Review.search([
                ("blog_id", "=", blog.id),
                ("status", "=", "pending"),
            ])

            if old_reviews:
                old_reviews.unlink()

            # Create one review for every reviewer
            for reviewer in blog.reviewer_ids:
                Review.create({
                    "blog_id": blog.id,
                    "reviewer_id": reviewer.id,
                    "status": "pending",
                })

            blog.write({
                "workflow_state": "under_review",
                "published": False,
            })

        return True

    # ==========================================================
    # STEP 3 - READY TO PUBLISH
    # ==========================================================

    def action_ready_to_publish(self):
        for blog in self:

            if blog.workflow_state != "review_completed":
                raise UserError(
                    "The blog must be approved by all reviewers "
                    "before it can be marked as Ready to Publish."
                )

            blog.write({
                "workflow_state": "ready_to_publish",
                "published": False,
            })

        return True

    # ==========================================================
    # STEP 4 - FINAL PUBLISH
    # ==========================================================

    def action_publish_blog(self):
        for blog in self:

            if blog.workflow_state != "ready_to_publish":
                raise UserError(
                    "Only blogs marked as 'Ready to Publish' "
                    "can be published."
                )

            blog.write({
                "workflow_state": "published",
                "published": True,
                "publish_date": fields.Date.today(),
            })

        return True

    # ==========================================================
    # ADMIN REQUESTS CHANGES
    # ==========================================================

    def action_request_changes(self):
        for blog in self:

            if blog.workflow_state not in [
                "under_review",
                "review_completed",
            ]:
                raise UserError(
                    "Changes cannot be requested from the current state."
                )

            blog.write({
                "workflow_state": "changes_required",
                "published": False,
            })

        return True