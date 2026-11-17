# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductPublicCategory(models.Model):
    """ EXTENSION of product.public.category (core 'website_sale' model
    for the eShop category tree). We add only the inverse side of the
    rating.aspect.public_category_ids relation, so a shop manager can
    configure aspects from whichever screen is more convenient - the
    aspect form or the category form - without introducing a second
    storage mechanism.
    """
    _inherit = 'product.public.category'

    aspect_ids = fields.Many2many(
        'rating.aspect',
        'rating_aspect_public_category_rel',
        'public_category_id',
        'aspect_id',
        string='Review Aspects',
        help="Extra rating dimensions (e.g. 'Comfort', 'Battery Life') "
             "shoppers are asked about when reviewing a product in this "
             "category. Inherited by child categories.",
    )
