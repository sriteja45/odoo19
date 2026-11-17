# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RatingAspect(models.Model):
    """ NEW model: a configurable sub-rating dimension (e.g. "Comfort",
    "Value for Money", "Sound Quality"). No equivalent exists in core
    rating/portal_rating, which only ever stores a single overall 0-5
    value per rating.rating record - so, exactly as with rating.vote and
    product.question elsewhere in this module, a dedicated model is the
    correct extension point rather than trying to bend the core rating
    field into carrying several scores at once.

    Aspects are configured per product.public.category (see the
    public_category_ids field below and product_public_category.py) so
    different product families can be asked different questions
    ("Battery Life" for electronics, "Fit" for shoes) without a single
    hard-coded list. An aspect left with no categories applies to every
    product (e.g. a generic "Value for Money").
    """
    _name = 'rating.aspect'
    _description = 'Product Review Aspect'
    _order = 'sequence, id'

    name = fields.Char(string='Aspect', required=True, translate=True)
    category = fields.Char(
        string='Category Label',
        help="Free-text grouping label for this aspect, shown in the "
             "backend list only (e.g. 'Comfort', 'Performance'). Purely "
             "organisational - it does not restrict which products the "
             "aspect appears on; use 'Website Categories' below for that.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    public_category_ids = fields.Many2many(
        'product.public.category',
        'rating_aspect_public_category_rel',
        'aspect_id',
        'public_category_id',
        string='Website Categories',
        help="eCommerce categories on which shoppers will be asked to "
             "rate this aspect (child categories inherit it too). Leave "
             "empty to apply this aspect to every product.",
    )
    aspect_rating_count = fields.Integer(
        string='Ratings Given', compute='_compute_aspect_rating_count',
    )

    def _compute_aspect_rating_count(self):
        grouped = self.env['rating.aspect.rating']._read_group(
            [('aspect_id', 'in', self.ids)], ['aspect_id'], ['__count'],
        )
        counts = {aspect.id: count for aspect, count in grouped}
        for aspect in self:
            aspect.aspect_rating_count = counts.get(aspect.id, 0)


class RatingAspectRating(models.Model):
    """ NEW model: one (aspect, value) line per rating.rating, e.g.
    "Comfort: 4/5" attached to a single product review. A separate line
    model (rather than dynamic fields on rating.rating) means aspects
    can be added, removed or reconfigured over time with no schema
    migration on rating.rating itself, and a review can carry a
    different set of aspect scores than another review of the same
    product if the configuration changed in between.
    """
    _name = 'rating.aspect.rating'
    _description = 'Product Review Aspect Value'
    _rec_name = 'aspect_id'
    _order = 'id'

    aspect_id = fields.Many2one(
        'rating.aspect', string='Aspect', required=True,
        ondelete='cascade', index=True,
    )
    rating_id = fields.Many2one(
        'rating.rating', string='Review', required=True,
        ondelete='cascade', index=True,
    )
    value = fields.Float(
        string='Value', required=True,
        help="1 (worst) to 5 (best) stars for this specific aspect.",
    )

    _sql_constraints = [
        ('uniq_aspect_per_rating', 'unique(aspect_id, rating_id)',
         'This aspect has already been rated on this review.'),
    ]

    @api.constrains('value')
    def _check_value_range(self):
        for rec in self:
            if rec.value < 1 or rec.value > 5:
                raise ValidationError('Aspect ratings must be between 1 and 5.')
