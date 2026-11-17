# -*- coding: utf-8 -*-

from odoo import models


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    def xevoria_translated_name(self, lang=None):
        self.ensure_one()
        return self.env["xevoria.translation.cache"].sudo().get_or_create_translation(self, "name", lang)


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    def xevoria_translated_name(self, lang=None):
        self.ensure_one()
        return self.env["xevoria.translation.cache"].sudo().get_or_create_translation(self, "name", lang)


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    def xevoria_translated_name(self, lang=None):
        self.ensure_one()
        return self.env["xevoria.translation.cache"].sudo().get_or_create_translation(self, "name", lang)
