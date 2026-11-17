# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .product_3d_model import _validate_3d_content, ALLOWED_3D_EXTENSIONS


class Product3DValidationMixin:
    @staticmethod
    def _validate_3d_filename(record, filename):
        if filename and not filename.strip().lower().endswith(ALLOWED_3D_EXTENSIONS):
            raise ValidationError(
                "The 3D model must be a .glb, .gltf or .usdz file."
            )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Legacy single-model field — DEPRECATED.
    # Kept only for backward compatibility with existing data.
    # New products and all new development must use product_3d_model_ids.
    # Fallback logic in templates/JS still reads this field when the multi-model
    # list is empty.
    product_3d_model = fields.Binary(
        string="3D Model (Legacy – Deprecated)",
        attachment=True,
        help="DEPRECATED. Use the '3D Models' list below instead.\n"
             "This single-model field is kept only so older data continues to work.\n"
             "It has no default selection, no per-model camera/AR settings, and no "
             "multi-model support. New uploads should go into product_3d_model_ids.",
    )
    product_3d_model_filename = fields.Char(string="3D Model Filename (Legacy)")

    # Multiple 3D models
    product_3d_model_ids = fields.One2many(
        "product.3d.model",
        "product_tmpl_id",
        string="3D Models",
    )

    # Dedicated poster
    product_3d_poster = fields.Binary(
        string="3D Poster Image",
        attachment=True,
        help="Image shown while the 3D model downloads. If empty, the product's "
             "main image is used. A still render of the model at its starting "
             "camera angle gives the smoothest transition.",
    )
    product_3d_poster_filename = fields.Char(string="Poster Filename")

    # Global viewer options (used when no specific model overrides them)
    product_3d_enable = fields.Boolean(
        string="Enable 3D / Animation Viewer",
        default=True,
        help="Master switch for this product. The viewer also needs to be enabled "
             "at website level (Website > Configuration > Websites).",
    )
    product_3d_auto_rotate = fields.Boolean(
        string="Auto-rotate 3D Model",
        default=True,
    )
    product_3d_ar = fields.Boolean(
        string="Enable AR (where supported)",
        default=True,
    )
    product_3d_360_enable = fields.Boolean(
        string="Enable 360° Image Viewer",
        default=False,
        help="Turns product photos into a drag-to-spin sequence - no 3D model "
             "needed. Prefer the dedicated 360° Frames list below (ordered). "
             "If that list is empty, the module falls back to the product's "
             "eCommerce images. At least 2 frames are required, otherwise the "
             "360° button stays hidden.",
    )
    product_360_frame_ids = fields.One2many(
        "product.360.frame",
        "product_tmpl_id",
        string="360° Frames",
        help="Dedicated ordered photos for the 360° viewer. Drag the handle to "
             "set rotation order. 24–36 frames (every 10–15°) work best. "
             "When this list has 2+ images it is used instead of the normal "
             "eCommerce media.",
    )
    product_3d_simple_anim_enable = fields.Boolean(
        string="Enable Simple Rotate / Zoom",
        default=False,
        help="Lightweight CSS/JS animation on the product's main image. "
             "Visitors can drag to rotate and scroll/pinch to zoom. "
             "Works with a single photo - no 3D model and no multi-angle "
             "photo set required. Ideal first step before investing in full 3D.",
    )

    # Default camera settings (applied when the model does not override them)
    product_3d_camera_orbit = fields.Char(
        string="Default Camera Orbit",
        default="0deg 75deg 105%",
        help='Starting camera position as "azimuth elevation distance", e.g. '
             '"0deg 75deg 105%" or "45deg 55deg 2.5m".\n'
             "Leave empty to use the website-level default. A model can override this.",
    )
    product_3d_field_of_view = fields.Char(
        string="Default Field of View",
        help='Optional zoom level, e.g. "30deg" for tighter framing. '
             "Leave empty to use the website-level default.",
    )

    # Performance helper: warn when any linked 3D model is large
    product_3d_has_large_model = fields.Boolean(
        string="Has Large 3D Model",
        compute="_compute_product_3d_has_large_model",
        help="True when at least one 3D model exceeds the warning size threshold.",
    )
    product_3d_size_hint = fields.Char(
        string="3D Size Hint",
        compute="_compute_product_3d_has_large_model",
    )

    @api.depends("product_3d_model_ids.model_file_size")
    def _compute_product_3d_has_large_model(self):
        from .product_3d_model import _get_size_limits
        _max_mb, warn_mb = _get_size_limits(self.env)
        for product in self:
            large = product.product_3d_model_ids.filtered(
                lambda m: bool(warn_mb) and (m.model_file_size or 0.0) > warn_mb
            )
            product.product_3d_has_large_model = bool(large)
            if large:
                sizes = ", ".join("%.1f MB" % m.model_file_size for m in large[:3])
                product.product_3d_size_hint = (
                    "Large model(s): %s. Compress with Draco/Meshopt for faster mobile load."
                    % sizes
                )
            else:
                product.product_3d_size_hint = False

    @api.constrains("product_3d_model", "product_3d_model_filename")
    def _check_product_3d_model(self):
        for product in self:
            if product.product_3d_model:
                Product3DValidationMixin._validate_3d_filename(
                    product, product.product_3d_model_filename
                )
                _validate_3d_content(
                    product.product_3d_model,
                    product.product_3d_model_filename or "",
                    env=self.env,
                )

    def _get_default_3d_model(self):
        """Return the default product.3d.model record or False."""
        self.ensure_one()
        models = self.product_3d_model_ids
        if not models:
            return False
        return models.filtered("is_default")[:1] or models[:1]


class ProductProduct(models.Model):
    _inherit = "product.product"

    product_3d_model = fields.Binary(
        string="Variant 3D Model (GLB/GLTF/USDZ)",
        attachment=True,
        help="Optional model shown only for this variant (e.g. a different colour).\n"
             "If empty, the template's default model is used. Switching variant on "
             "the website swaps the model without reloading the page.",
    )
    product_3d_model_filename = fields.Char(string="Variant 3D Model Filename")
    product_3d_enable = fields.Boolean(
        string="Enable Variant 3D Viewer",
        default=True,
    )
    product_3d_auto_rotate = fields.Boolean(
        string="Auto-rotate Variant 3D Model",
        default=True,
    )
    product_3d_ar = fields.Boolean(
        string="Enable Variant AR",
        default=True,
    )

    @api.constrains("product_3d_model", "product_3d_model_filename")
    def _check_variant_3d_model(self):
        for product in self:
            if product.product_3d_model:
                Product3DValidationMixin._validate_3d_filename(
                    product, product.product_3d_model_filename
                )
                _validate_3d_content(
                    product.product_3d_model,
                    product.product_3d_model_filename or "",
                    env=self.env,
                )


class Website(models.Model):
    _inherit = "website"

    product_3d_viewer_enabled = fields.Boolean(
        string="Enable Product 3D / 360 Viewer",
        default=True,
        help="Master switch for this website. Defaults to ON so the feature is "
             "available as soon as the module is installed. Turn off only if you "
             "want to disable the viewer on this specific website.",
    )
    product_3d_default_camera_orbit = fields.Char(
        string="Default 3D Camera Orbit",
        default="0deg 75deg 105%",
        help='Website-wide default camera orbit used when a product does not define its own. '
             'Example: "0deg 75deg 105%" or "45deg 55deg 2.5m".',
    )
    product_3d_default_field_of_view = fields.Char(
        string="Default 3D Field of View",
        help='Website-wide default field of view (e.g. "30deg"). '
             "Used when a product does not define its own.",
    )
