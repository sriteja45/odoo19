# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError
from odoo.addons.website_sale_wishlist.controllers.main import WebsiteSaleWishlist


class XevoriaWishlistController(WebsiteSaleWishlist):
    """Require the visitor to be signed in before a product can be added
    to the wishlist.

    Odoo's stock ``website_sale_wishlist`` module allows public (not
    logged-in) visitors to add products to a session-based wishlist.
    Xevoria wants wishlist usage restricted to signed-in users only, so
    this override rejects the add-to-wishlist request for public users.
    The "Add to Cart" flow and everything else from website_sale_wishlist
    is left untouched.
    """

    @http.route('/shop/wishlist/add', type='jsonrpc', auth='public', website=True)
    def add_to_wishlist(self, product_id, **kw):
        if request.website.is_public_user():
            raise AccessError(_("Please sign in to add products to your wishlist."))
        return super().add_to_wishlist(product_id, **kw)