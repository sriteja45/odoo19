from . import models
from . import controllers
from . import report


def post_init_hook(env):
    """Install/upgrade hooks for Step 1 + Step 2 architecture.

    1. Force website_sale.product_comment inactive (single submission path).
    2. Ensure rating ownership ICP defaults to shared when missing.
    3. Reconcile: bridge approved reviews + align linked consumed flags.
       Under shared (default) unowned native ratings are left untouched;
       exclusive deactivation runs only when explicitly configured.
    """
    # Step 1 — keep a single submission path (verified token flow only)
    product_comment = env.ref('website_sale.product_comment', raise_if_not_found=False)
    if product_comment and product_comment.active:
        product_comment.write({'active': False})

    # Default ownership mode to shared (additive) if not yet set.
    icp = env['ir.config_parameter'].sudo()
    if not icp.get_param('customer_feedback.rating_ownership'):
        icp.set_param('customer_feedback.rating_ownership', 'shared')

    # Step 2 — bridge + linked consumed alignment; deactivation only if exclusive
    env['feedback.review']._reconcile_product_native_ratings()
