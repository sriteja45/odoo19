# -*- coding: utf-8 -*-

import base64

from odoo import api, fields, models
from odoo.exceptions import ValidationError


ALLOWED_3D_EXTENSIONS = (".glb", ".gltf", ".usdz")

# System parameter names (configurable in Settings > Technical > Parameters)
PARAM_MAX_SIZE = "website_product_3d.max_model_size_mb"
PARAM_WARN_SIZE = "website_product_3d.warn_model_size_mb"

# Defaults, in MB. 0 for the hard limit means "no hard limit".
DEFAULT_MAX_SIZE_MB = 50.0
DEFAULT_WARN_SIZE_MB = 8.0


def _get_extension(filename):
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _get_size_limits(env):
    """Return (hard_limit_mb, warn_threshold_mb) from system parameters."""
    params = env["ir.config_parameter"].sudo()

    def _read(key, default):
        try:
            value = params.get_param(key)
            return float(value) if value not in (None, False, "") else default
        except (TypeError, ValueError):
            return default

    return _read(PARAM_MAX_SIZE, DEFAULT_MAX_SIZE_MB), _read(
        PARAM_WARN_SIZE, DEFAULT_WARN_SIZE_MB
    )


def _human_size(num_bytes):
    if not num_bytes:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} B"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} GB"


def _decoded_size(data_b64):
    """Approximate decoded byte size of a base64 payload without decoding it."""
    if not data_b64:
        return 0
    raw = data_b64 if isinstance(data_b64, bytes) else str(data_b64).encode()
    padding = raw.count(b"=")
    return max(0, (len(raw) * 3) // 4 - padding)


def _validate_3d_content(data_b64, filename, env=None):
    """Validate extension, magic bytes and file size."""
    if not data_b64:
        return
    ext = _get_extension(filename)
    if ext not in ALLOWED_3D_EXTENSIONS:
        raise ValidationError(
            "The 3D model must be a .glb, .gltf or .usdz file."
        )

    # Size check first: cheap, and avoids decoding a huge payload for nothing.
    if env is not None:
        max_mb, _warn_mb = _get_size_limits(env)
        if max_mb and _decoded_size(data_b64) > max_mb * 1024 * 1024:
            raise ValidationError(
                "This 3D model is %s, which exceeds the %s MB limit.\n\n"
                "Compress the model before uploading - gltf-transform or "
                "gltfpack (Draco / Meshopt compression) usually reduces a GLB "
                "by 70-90%% without a visible quality loss:\n"
                "    npx @gltf-transform/cli optimize in.glb out.glb --compress draco\n\n"
                "An administrator can change the limit in Settings > Technical > "
                "System Parameters (%s)."
                % (_human_size(_decoded_size(data_b64)), max_mb, PARAM_MAX_SIZE)
            )

    try:
        raw = base64.b64decode(data_b64)
    except Exception as e:
        raise ValidationError("Invalid binary data for the 3D model.") from e

    if len(raw) < 8:
        raise ValidationError("The uploaded file is too small to be a valid 3D model.")

    if ext == ".glb":
        # GLB magic: 'glTF' (0x67 0x6C 0x54 0x46)
        if raw[:4] != b"glTF":
            raise ValidationError(
                "The file extension is .glb but the content is not a valid GLB "
                "(missing glTF magic header)."
            )
    elif ext == ".gltf":
        # GLTF is JSON. Validate structure and reject files that depend on
        # external resources (buffers / images with a "uri" that is not
        # a data: URI). model-viewer can only load self-contained assets
        # when the file is served from a single URL.
        stripped = raw.lstrip()
        if not stripped.startswith(b"{") and not stripped.startswith(b"["):
            raise ValidationError(
                "The file extension is .gltf but the content does not look like JSON."
            )
        try:
            import json
            gltf = json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise ValidationError(
                "The .gltf file is not valid JSON and cannot be loaded."
            ) from e

        if not isinstance(gltf, dict):
            raise ValidationError("The .gltf file does not contain a valid glTF object.")

        # Minimal required keys for glTF 2.0
        if "asset" not in gltf:
            raise ValidationError(
                "The .gltf file is missing the required 'asset' property (not a valid glTF)."
            )

        external_refs = []
        for buffer in gltf.get("buffers") or []:
            uri = buffer.get("uri") if isinstance(buffer, dict) else None
            if uri and not str(uri).startswith("data:"):
                external_refs.append("buffer: %s" % uri)
        for image in gltf.get("images") or []:
            uri = image.get("uri") if isinstance(image, dict) else None
            if uri and not str(uri).startswith("data:"):
                external_refs.append("image: %s" % uri)

        if external_refs:
            raise ValidationError(
                "This .gltf file references external resources and cannot be "
                "displayed by the product viewer:\n  - %s\n\n"
                "Export a self-contained .glb (recommended) or embed all buffers "
                "and textures as data: URIs inside the .gltf."
                % "\n  - ".join(external_refs[:8])
            )
    elif ext == ".usdz":
        # USDZ is a ZIP container
        if raw[:4] != b"PK\x03\x04" and raw[:4] != b"PK\x05\x06":
            raise ValidationError(
                "The file extension is .usdz but the content is not a valid ZIP/USDZ archive."
            )


class Product3DModel(models.Model):
    _name = "product.3d.model"
    _description = "Product 3D Model"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(default=10)
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_file = fields.Binary(
        string="3D Model (GLB/GLTF/USDZ)",
        attachment=True,
        required=True,
        help="Upload a .glb (recommended), .gltf or .usdz file.\n"
             "Aim for under 8 MB for mobile. Compress with:\n"
             "  npx @gltf-transform/cli optimize in.glb out.glb --compress draco\n"
             "or --compress meshopt. Resize textures to 1024–2048 px.\n"
             "USDZ improves AR on iPhone/iPad. The MB column and yellow warning "
             "flag large files; a hard size limit is enforced on save.",
    )
    model_filename = fields.Char(string="Filename")
    model_file_size = fields.Float(
        string="Size (MB)",
        compute="_compute_model_file_size",
        store=True,
        digits=(10, 2),
        help="Decoded size of the uploaded 3D model.",
    )
    size_warning = fields.Char(
        string="Size Warning",
        compute="_compute_model_file_size",
        store=False,
        help="Shown when the model is large enough to slow down page loading.",
    )
    is_default = fields.Boolean(
        string="Default",
        default=False,
        help="If checked, this model is shown first on the website.",
    )
    camera_orbit = fields.Char(
        string="Camera Orbit",
        default="0deg 75deg 105%",
        help='Starting camera position, written as "azimuth elevation distance".\n'
             'Examples: "0deg 75deg 105%" (default, 105% of the auto distance) '
             'or "45deg 55deg 2.5m" (fixed 2.5 metre distance).',
    )
    field_of_view = fields.Char(
        string="Field of View",
        help='Optional zoom level, e.g. "30deg" for a tighter framing. '
             "Leave empty to let the viewer choose.",
    )
    auto_rotate = fields.Boolean(
        string="Auto-rotate",
        default=True,
        help="Slowly spin the model until the visitor interacts with it.",
    )
    enable_ar = fields.Boolean(
        string="Enable AR",
        default=True,
        help="Show the 'View in your space' button on supported phones. "
             "Upload a .usdz model for the best result on iOS.",
    )

    @api.depends("model_file")
    def _compute_model_file_size(self):
        _max_mb, warn_mb = _get_size_limits(self.env)
        for rec in self:
            size_mb = _decoded_size(rec.model_file) / (1024.0 * 1024.0)
            rec.model_file_size = size_mb
            if warn_mb and size_mb > warn_mb:
                rec.size_warning = (
                    "%.1f MB - large file, mobile visitors may wait a long time. "
                    "Consider Draco/Meshopt compression." % size_mb
                )
            else:
                rec.size_warning = False

    @api.constrains("model_file", "model_filename")
    def _check_model_file(self):
        for rec in self:
            if rec.model_file:
                _validate_3d_content(
                    rec.model_file, rec.model_filename or "", env=self.env
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("model_file"):
                _validate_3d_content(
                    vals["model_file"], vals.get("model_filename") or "", env=self.env
                )
        records = super().create(vals_list)
        records._ensure_one_default()
        return records

    def write(self, vals):
        if "model_file" in vals or "model_filename" in vals:
            # Validate the new content (use existing filename if not provided)
            for rec in self:
                data = vals.get("model_file", rec.model_file)
                filename = vals.get("model_filename", rec.model_filename)
                if data:
                    _validate_3d_content(data, filename or "", env=self.env)
        res = super().write(vals)
        if "is_default" in vals:
            self._ensure_one_default()
        return res

    def _ensure_one_default(self):
        """Make sure each product has at most one default 3D model."""
        for tmpl in self.mapped("product_tmpl_id"):
            defaults = tmpl.product_3d_model_ids.filtered("is_default")
            if len(defaults) > 1:
                (defaults - defaults[:1]).write({"is_default": False})
            elif not defaults and tmpl.product_3d_model_ids:
                tmpl.product_3d_model_ids[:1].is_default = True
