# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class ProductQuestion(models.Model):
    """ NEW model: customer question on a product.template.

    No equivalent exists in core rating/portal_rating/website_sale, so a
    dedicated model is required (same justification as rating.vote).
    """
    _name = 'product.question'
    _description = 'Product Question'
    _order = 'create_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Question',
        required=True,
        help='Short summary / first line of the question.',
    )
    body = fields.Text(
        string='Details',
        help='Optional longer question body.',
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Variant',
        ondelete='set null',
        index=True,
        help='Optional specific variant the question is about.',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Asked By',
        required=True,
        ondelete='cascade',
        index=True,
        default=lambda self: self.env.user.partner_id,
    )
    is_anonymous = fields.Boolean(string='Post Anonymously', default=False)
    state = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('answered', 'Answered'),
            ('closed', 'Closed'),
        ],
        string='Status',
        default='open',
        index=True,
        required=True,
    )
    answer_ids = fields.One2many('product.answer', 'question_id', string='Answers')
    answer_count = fields.Integer(compute='_compute_answer_count', store=True)
    upvote_count = fields.Integer(string='Upvotes', default=0, copy=False)
    website_published = fields.Boolean(
        string='Published',
        default=True,
        help='Unpublish to hide from the public product page without deleting.',
    )

    @api.depends('answer_ids', 'answer_ids.website_published')
    def _compute_answer_count(self):
        for q in self:
            q.answer_count = len(q.answer_ids.filtered('website_published'))

    @api.constrains('name')
    def _check_name_length(self):
        for q in self:
            if q.name and len(q.name.strip()) < 5:
                raise ValidationError(_('Please write a question of at least 5 characters.'))

    def get_display_author_name(self):
        self.ensure_one()
        if not self.is_anonymous or not self.partner_id:
            return self.partner_id.name or _('Anonymous')
        name = self.partner_id.name or ''
        parts = name.split()
        if not parts:
            return _('Anonymous')
        masked = parts[0][0] + '*' * max(len(parts[0]) - 1, 1)
        if len(parts) > 1:
            masked += ' ' + parts[-1][0] + '.'
        return masked

    def action_mark_answered(self):
        self.write({'state': 'answered'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'open'})

    @api.model_create_multi
    def create(self, vals_list):
        questions = super().create(vals_list)
        questions._notify_new_question()
        return questions

    def _notify_new_question(self):
        """Email the product responsible / company about a new question.

        Reuses the standard mail.template pattern already used for review
        request emails in this module.
        """
        template = self.env.ref(
            'website_sale_review_extended.mail_template_product_question',
            raise_if_not_found=False,
        )
        if not template:
            return
        for question in self:
            try:
                template.send_mail(question.id, force_send=False, raise_exception=False)
            except Exception:
                # Never block question creation on mail failure
                pass

    def upvote(self, partner=None):
        """Increment upvote; one logical upvote per partner via product.question.vote."""
        self.ensure_one()
        partner = partner or self.env.user.partner_id
        if self.env.user._is_public() or not partner:
            raise UserError(_('Please sign in to upvote a question.'))
        Vote = self.env['product.question.vote'].sudo()
        existing = Vote.search([
            ('question_id', '=', self.id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        if existing:
            # Toggle off
            existing.unlink()
            self.sudo().write({'upvote_count': max(0, self.upvote_count - 1)})
            return {'upvote_count': self.upvote_count, 'user_voted': False}
        Vote.create({
            'question_id': self.id,
            'partner_id': partner.id,
        })
        self.sudo().write({'upvote_count': self.upvote_count + 1})
        return {'upvote_count': self.upvote_count, 'user_voted': True}

    def to_public_dict(self, partner=None):
        """Serialise for the product-page Q&A widget."""
        self.ensure_one()
        partner = partner or self.env.user.partner_id
        user_voted = False
        if partner and not self.env.user._is_public():
            user_voted = bool(self.env['product.question.vote'].sudo().search([
                ('question_id', '=', self.id),
                ('partner_id', '=', partner.id),
            ], limit=1))
        return {
            'id': self.id,
            'name': self.name,
            'body': self.body or '',
            'author': self.get_display_author_name(),
            'is_anonymous': self.is_anonymous,
            'state': self.state,
            'answer_count': self.answer_count,
            'upvote_count': self.upvote_count,
            'user_voted': user_voted,
            'create_date': fields.Datetime.to_string(self.create_date) if self.create_date else '',
            'product_id': self.product_id.id if self.product_id else False,
            'answers': [
                a.to_public_dict(partner=partner)
                for a in self.answer_ids.filtered('website_published').sorted('create_date')
            ],
        }


class ProductAnswer(models.Model):
    """ NEW model: answer to a product.question (from seller or customer)."""
    _name = 'product.answer'
    _description = 'Product Answer'
    _order = 'create_date asc, id asc'
    _rec_name = 'body'

    question_id = fields.Many2one(
        'product.question',
        string='Question',
        required=True,
        ondelete='cascade',
        index=True,
    )
    body = fields.Text(string='Answer', required=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Answered By',
        required=True,
        ondelete='cascade',
        index=True,
        default=lambda self: self.env.user.partner_id,
    )
    is_seller = fields.Boolean(
        string='Seller Answer',
        compute='_compute_is_seller',
        store=True,
        help='True when the answerer is an internal user (staff/seller).',
    )
    is_verified_buyer = fields.Boolean(
        string='Verified Buyer',
        compute='_compute_is_verified_buyer',
        store=True,
    )
    website_published = fields.Boolean(string='Published', default=True)
    upvote_count = fields.Integer(string='Upvotes', default=0, copy=False)

    @api.depends('partner_id', 'partner_id.user_ids')
    def _compute_is_seller(self):
        for ans in self:
            users = ans.partner_id.user_ids if ans.partner_id else self.env['res.users']
            ans.is_seller = any(not u.share for u in users)

    @api.depends('partner_id', 'question_id.product_tmpl_id')
    def _compute_is_verified_buyer(self):
        SaleOrderLine = self.env['sale.order.line'].sudo()
        for ans in self:
            verified = False
            q = ans.question_id
            if ans.partner_id and q.product_tmpl_id:
                verified = bool(SaleOrderLine.search([
                    ('order_id.state', '=', 'sale'),
                    ('qty_delivered', '>', 0),
                    ('product_id.product_tmpl_id', '=', q.product_tmpl_id.id),
                    ('order_partner_id.commercial_partner_id', '=',
                     ans.partner_id.commercial_partner_id.id),
                ], limit=1))
            ans.is_verified_buyer = verified

    @api.constrains('body')
    def _check_body(self):
        for ans in self:
            if ans.body and len(ans.body.strip()) < 2:
                raise ValidationError(_('Answer is too short.'))

    @api.model_create_multi
    def create(self, vals_list):
        answers = super().create(vals_list)
        # Mark parent question as answered
        questions = answers.mapped('question_id').filtered(lambda q: q.state == 'open')
        if questions:
            questions.action_mark_answered()
        return answers

    def upvote(self, partner=None):
        self.ensure_one()
        partner = partner or self.env.user.partner_id
        if self.env.user._is_public() or not partner:
            raise UserError(_('Please sign in to upvote an answer.'))
        Vote = self.env['product.answer.vote'].sudo()
        existing = Vote.search([
            ('answer_id', '=', self.id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        if existing:
            existing.unlink()
            self.sudo().write({'upvote_count': max(0, self.upvote_count - 1)})
            return {'upvote_count': self.upvote_count, 'user_voted': False}
        Vote.create({
            'answer_id': self.id,
            'partner_id': partner.id,
        })
        self.sudo().write({'upvote_count': self.upvote_count + 1})
        return {'upvote_count': self.upvote_count, 'user_voted': True}

    def to_public_dict(self, partner=None):
        self.ensure_one()
        partner = partner or self.env.user.partner_id
        user_voted = False
        if partner and not self.env.user._is_public():
            user_voted = bool(self.env['product.answer.vote'].sudo().search([
                ('answer_id', '=', self.id),
                ('partner_id', '=', partner.id),
            ], limit=1))
        return {
            'id': self.id,
            'body': self.body,
            'author': self.partner_id.name or _('Anonymous'),
            'is_seller': self.is_seller,
            'is_verified_buyer': self.is_verified_buyer,
            'upvote_count': self.upvote_count,
            'user_voted': user_voted,
            'create_date': fields.Datetime.to_string(self.create_date) if self.create_date else '',
        }


class ProductQuestionVote(models.Model):
    _name = 'product.question.vote'
    _description = 'Product Question Upvote'
    _rec_name = 'question_id'

    question_id = fields.Many2one('product.question', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)

    _sql_constraints = [
        ('uniq_partner_question_vote', 'unique(question_id, partner_id)',
         'You have already voted on this question.'),
    ]


class ProductAnswerVote(models.Model):
    _name = 'product.answer.vote'
    _description = 'Product Answer Upvote'
    _rec_name = 'answer_id'

    answer_id = fields.Many2one('product.answer', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)

    _sql_constraints = [
        ('uniq_partner_answer_vote', 'unique(answer_id, partner_id)',
         'You have already voted on this answer.'),
    ]
