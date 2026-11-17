# -*- coding: utf-8 -*-

import base64
import json

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase

from odoo.addons.website_product_3d.models.product_3d_model import (
    PARAM_MAX_SIZE,
    PARAM_WARN_SIZE,
    _decoded_size,
    _human_size,
)


def _b64(raw):
    return base64.b64encode(raw)


# A minimal but structurally plausible GLB: magic + version + length.
VALID_GLB = _b64(b"glTF" + b"\x02\x00\x00\x00" + b"\x20\x00\x00\x00" + b"\x00" * 16)
VALID_GLTF = _b64(json.dumps({"asset": {"version": "2.0"}}).encode())
VALID_USDZ = _b64(b"PK\x03\x04" + b"\x00" * 32)
NOT_A_MODEL = _b64(b"this is definitely not a 3d model at all")
BIG_GLB = _b64(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * (200 * 1024))


@tagged("post_install", "-at_install")
class TestProduct3D(TransactionCase):
    """Validation, size limits and default-model behaviour.

    Note: `SavepointCase` was removed after Odoo 15. `TransactionCase` is now
    class-scoped by default and is the correct base class on Odoo 19.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProductTemplate = cls.env["product.template"]
        cls.Model3D = cls.env["product.3d.model"]
        cls.Website = cls.env["website"]
        cls.product = cls.ProductTemplate.create({"name": "3D Test Product"})

    def _set_param(self, key, value):
        self.env["ir.config_parameter"].sudo().set_param(key, value)

    # ------------------------------------------------------------------
    # Website / defaults
    # ------------------------------------------------------------------

    def test_website_feature_enabled_by_default(self):
        website = self.Website.create({"name": "3D Test Website"})
        self.assertTrue(website.product_3d_viewer_enabled)
        self.assertTrue(website.product_3d_default_camera_orbit)

    # ------------------------------------------------------------------
    # Extension / magic-byte validation
    # ------------------------------------------------------------------

    def test_template_rejects_invalid_model_extension(self):
        with self.assertRaises(ValidationError):
            self.ProductTemplate.create({
                "name": "Invalid 3D Model",
                "product_3d_model": NOT_A_MODEL,
                "product_3d_model_filename": "model.txt",
            })

    def test_variant_rejects_invalid_model_extension(self):
        variant = self.product.product_variant_id
        with self.assertRaises(ValidationError):
            variant.write({
                "product_3d_model": NOT_A_MODEL,
                "product_3d_model_filename": "variant.txt",
            })

    def test_rejects_glb_extension_with_wrong_content(self):
        """A .glb name is not enough - the glTF magic header must be present."""
        with self.assertRaises(ValidationError):
            self.Model3D.create({
                "name": "Fake GLB",
                "product_tmpl_id": self.product.id,
                "model_file": NOT_A_MODEL,
                "model_filename": "fake.glb",
            })

    def test_rejects_gltf_extension_with_non_json_content(self):
        with self.assertRaises(ValidationError):
            self.Model3D.create({
                "name": "Fake GLTF",
                "product_tmpl_id": self.product.id,
                "model_file": _b64(b"\x00\x01\x02\x03 not json"),
                "model_filename": "fake.gltf",
            })

    def test_rejects_gltf_with_external_buffer(self):
        """Self-contained check: external buffer/image URIs must be rejected."""
        external = {
            "asset": {"version": "2.0"},
            "buffers": [{"uri": "model.bin", "byteLength": 100}],
        }
        with self.assertRaises(ValidationError):
            self.Model3D.create({
                "name": "External GLTF",
                "product_tmpl_id": self.product.id,
                "model_file": _b64(json.dumps(external).encode()),
                "model_filename": "external.gltf",
            })

    def test_rejects_usdz_extension_with_non_zip_content(self):
        with self.assertRaises(ValidationError):
            self.Model3D.create({
                "name": "Fake USDZ",
                "product_tmpl_id": self.product.id,
                "model_file": _b64(b"not-a-zip-archive-at-all"),
                "model_filename": "fake.usdz",
            })

    def test_accepts_valid_formats(self):
        for filename, content in (
            ("cube.glb", VALID_GLB),
            ("cube.gltf", VALID_GLTF),
            ("cube.usdz", VALID_USDZ),
        ):
            record = self.Model3D.create({
                "name": filename,
                "product_tmpl_id": self.product.id,
                "model_file": content,
                "model_filename": filename,
            })
            self.assertTrue(record.id, "%s should be accepted" % filename)

    def test_validation_also_runs_on_write(self):
        record = self.Model3D.create({
            "name": "Good model",
            "product_tmpl_id": self.product.id,
            "model_file": VALID_GLB,
            "model_filename": "good.glb",
        })
        with self.assertRaises(ValidationError):
            record.write({"model_file": NOT_A_MODEL, "model_filename": "bad.exe"})

    # ------------------------------------------------------------------
    # Size limit (performance guardrail)
    # ------------------------------------------------------------------

    def test_oversized_model_is_rejected(self):
        self._set_param(PARAM_MAX_SIZE, "0.001")
        with self.assertRaises(ValidationError):
            self.Model3D.create({
                "name": "Oversized",
                "product_tmpl_id": self.product.id,
                "model_file": BIG_GLB,
                "model_filename": "big.glb",
            })

    def test_size_limit_can_be_disabled(self):
        self._set_param(PARAM_MAX_SIZE, "0")
        record = self.Model3D.create({
            "name": "Oversized but allowed",
            "product_tmpl_id": self.product.id,
            "model_file": BIG_GLB,
            "model_filename": "big.glb",
        })
        self.assertTrue(record.id)

    def test_computed_size_and_warning(self):
        self._set_param(PARAM_MAX_SIZE, "0")
        self._set_param(PARAM_WARN_SIZE, "0.05")
        record = self.Model3D.create({
            "name": "Chunky",
            "product_tmpl_id": self.product.id,
            "model_file": BIG_GLB,
            "model_filename": "chunky.glb",
        })
        self.assertGreater(record.model_file_size, 0.1)
        self.assertTrue(record.size_warning)

    def test_small_model_has_no_warning(self):
        self._set_param(PARAM_MAX_SIZE, "0")
        self._set_param(PARAM_WARN_SIZE, "8")
        record = self.Model3D.create({
            "name": "Tiny",
            "product_tmpl_id": self.product.id,
            "model_file": VALID_GLB,
            "model_filename": "tiny.glb",
        })
        self.assertFalse(record.size_warning)

    def test_size_helpers(self):
        self.assertEqual(_decoded_size(_b64(b"a" * 1000)), 1000)
        self.assertEqual(_decoded_size(False), 0)
        self.assertIn("KB", _human_size(2048))

    # ------------------------------------------------------------------
    # Default-model logic
    # ------------------------------------------------------------------

    def test_first_model_becomes_default(self):
        first = self.Model3D.create({
            "name": "First",
            "product_tmpl_id": self.product.id,
            "model_file": VALID_GLB,
            "model_filename": "first.glb",
        })
        self.assertTrue(first.is_default)
        self.assertEqual(self.product._get_default_3d_model(), first)

    def test_only_one_default_per_product(self):
        first = self.Model3D.create({
            "name": "First",
            "product_tmpl_id": self.product.id,
            "model_file": VALID_GLB,
            "model_filename": "first.glb",
            "is_default": True,
        })
        second = self.Model3D.create({
            "name": "Second",
            "product_tmpl_id": self.product.id,
            "model_file": VALID_GLB,
            "model_filename": "second.glb",
        })
        second.write({"is_default": True})
        defaults = self.product.product_3d_model_ids.filtered("is_default")
        self.assertEqual(len(defaults), 1)
        self.assertTrue(defaults <= (first | second))

    def test_no_models_returns_false(self):
        empty = self.ProductTemplate.create({"name": "No 3D"})
        self.assertFalse(empty._get_default_3d_model())

    # ------------------------------------------------------------------
    # Simple rotate/zoom + product-level size hint
    # ------------------------------------------------------------------

    def test_simple_anim_field_defaults_false(self):
        product = self.ProductTemplate.create({"name": "Simple Anim Product"})
        self.assertFalse(product.product_3d_simple_anim_enable)

    def test_simple_anim_can_be_enabled(self):
        self.product.product_3d_simple_anim_enable = True
        self.assertTrue(self.product.product_3d_simple_anim_enable)

    def test_product_level_large_model_hint(self):
        self._set_param(PARAM_MAX_SIZE, "0")
        self._set_param(PARAM_WARN_SIZE, "0.05")
        self.Model3D.create({
            "name": "Large one",
            "product_tmpl_id": self.product.id,
            "model_file": BIG_GLB,
            "model_filename": "large.glb",
        })
        self.product.invalidate_recordset(["product_3d_has_large_model", "product_3d_size_hint"])
        self.assertTrue(self.product.product_3d_has_large_model)
        self.assertTrue(self.product.product_3d_size_hint)
        self.assertIn("MB", self.product.product_3d_size_hint)

    # ------------------------------------------------------------------
    # Dedicated 360° frames
    # ------------------------------------------------------------------

    def test_360_frame_model_exists_and_links(self):
        Frame = self.env["product.360.frame"]
        frame = Frame.create({
            "name": "Front",
            "product_tmpl_id": self.product.id,
            "image": _b64(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32),
            "image_filename": "front.png",
            "sequence": 10,
        })
        self.assertTrue(frame.id)
        self.assertEqual(frame.product_tmpl_id, self.product)
        self.assertIn(frame, self.product.product_360_frame_ids)

    def test_360_frames_ordered_by_sequence(self):
        Frame = self.env["product.360.frame"]
        f2 = Frame.create({
            "name": "Side",
            "product_tmpl_id": self.product.id,
            "image": _b64(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16),
            "sequence": 20,
        })
        f1 = Frame.create({
            "name": "Front",
            "product_tmpl_id": self.product.id,
            "image": _b64(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16),
            "sequence": 5,
        })
        frames = self.product.product_360_frame_ids
        self.assertEqual(frames[0], f1)
        self.assertEqual(frames[1], f2)

    def test_360_enable_defaults_false(self):
        product = self.ProductTemplate.create({"name": "360 Product"})
        self.assertFalse(product.product_3d_360_enable)
        self.assertFalse(product.product_360_frame_ids)


@tagged("post_install", "-at_install")
class TestProduct3DController(HttpCase):
    """The controller must not leak models of unpublished products."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(PARAM_MAX_SIZE, "50")
        cls.product = cls.env["product.template"].create({
            "name": "Controller Test Product",
            "is_published": False,
        })
        cls.model_3d = cls.env["product.3d.model"].create({
            "name": "Main",
            "product_tmpl_id": cls.product.id,
            "model_file": VALID_GLB,
            "model_filename": "main.glb",
        })

    @property
    def _model_url(self):
        return "/website_product_3d/model/product.3d.model/%s/model_file" % self.model_3d.id

    def test_unpublished_product_model_is_not_public(self):
        """Public visitors must get a 404 for an unpublished product's model."""
        response = self.url_open(self._model_url)
        self.assertEqual(
            response.status_code, 404,
            "Unpublished product 3D models must not be downloadable by the public.",
        )

    def test_published_product_model_is_served(self):
        self.product.is_published = True
        self.env.flush_all()
        response = self.url_open(self._model_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("model/gltf-binary", response.headers.get("Content-Type", ""))

    def test_unknown_field_is_rejected(self):
        url = "/website_product_3d/model/product.template/%s/name" % self.product.id
        self.assertEqual(self.url_open(url).status_code, 404)

    def test_default_model_route_is_not_public(self):
        """The backend preview route must require a logged-in user."""
        response = self.url_open(
            "/website_product_3d/default_model/%s" % self.product.id,
            allow_redirects=False,
        )
        self.assertNotEqual(
            response.status_code, 200,
            "The backend preview route should not serve anonymous visitors.",
        )
