/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { AddProductToWishlistButton } from "@website_sale_wishlist/interactions/add_product_to_wishlist_button";

/**
 * Xevoria: require sign-in before adding a product to the wishlist.
 *
 * By default website_sale_wishlist lets a public (not logged-in) visitor
 * add products to a session-based wishlist. Xevoria wants the "Add to
 * wishlist" action to require an authenticated user, so we intercept the
 * click here: if the visitor is public, we send them to the login page
 * (bringing them straight back to the page they were on) instead of
 * firing the /shop/wishlist/add RPC. The backend also blocks the same
 * request server-side, so this is purely for a clean UX.
 */
patch(AddProductToWishlistButton.prototype, {
    async addProduct(ev) {
        const isPublicUser = await user.hasGroup("base.group_public");
        if (isPublicUser) {
            const redirectTo = window.location.pathname + window.location.search;
            window.location.href = "/web/login?redirect=" + encodeURIComponent(redirectTo);
            return;
        }
        return super.addProduct(ev);
    },
});