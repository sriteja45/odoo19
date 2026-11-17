# -*- coding: utf-8 -*-

from odoo import models, fields, api
import hashlib


class XevoriaTranslationCache(models.Model):
    _name = "xevoria.translation.cache"
    _description = "Xevoria Generic Translation Cache"
    _rec_name = "source_text"

    source_model = fields.Char(required=True, index=True)
    source_id = fields.Integer(required=True, index=True)
    source_field = fields.Char(required=True, index=True)
    lang = fields.Char(required=True, index=True)
    source_text = fields.Text(required=True)
    translated_text = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "xevoria_generic_translation_unique",
            "unique(source_model, source_id, source_field, lang)",
            "A cached translation already exists for this record, field, and language.",
        )
    ]

    @api.model
    def get_or_create_translation(self, record, field_name, lang, force=False):
        """Return a cached translation for any translatable Odoo record field.

        This is used for categories, attribute/filter labels, and common UI labels.
        It intentionally returns the original text if the translation provider is disabled,
        so the website never breaks.
        """
        if not record or not field_name or field_name not in record._fields:
            return ""

        lang = lang or self.env.context.get("lang") or "en_US"
        source_text = record[field_name] or ""
        if not source_text:
            return ""

        existing = self.sudo().search([
            ("source_model", "=", record._name),
            ("source_id", "=", record.id),
            ("source_field", "=", field_name),
            ("lang", "=", lang),
        ], limit=1)

        if existing and not force and existing.source_text == source_text:
            return existing.translated_text or source_text

        translated = self.env["xevoria.translation.service"].sudo().translate_text(source_text, lang) or source_text
        vals = {
            "source_model": record._name,
            "source_id": record.id,
            "source_field": field_name,
            "lang": lang,
            "source_text": source_text,
            "translated_text": translated,
            "active": True,
        }
        if existing:
            existing.write(vals)
        else:
            existing = self.sudo().create(vals)
        return existing.translated_text or source_text

    @api.model
    def get_or_create_label(self, key, text, lang, force=False):
        """Cache simple UI labels using source_model='xevoria.ui.label'."""
        lang = lang or self.env.context.get("lang") or "en_US"
        key = key or text
        text = text or ""
        if not text:
            return ""

        # Stable pseudo-id from key. Using an integer keeps the generic unique constraint simple.
        source_id = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16) % 2147483647
        existing = self.sudo().search([
            ("source_model", "=", "xevoria.ui.label"),
            ("source_id", "=", source_id),
            ("source_field", "=", key),
            ("lang", "=", lang),
        ], limit=1)

        if existing and not force and existing.source_text == text:
            return existing.translated_text or text

        translated = self.env["xevoria.translation.service"].sudo().translate_text(text, lang) or text
        vals = {
            "source_model": "xevoria.ui.label",
            "source_id": source_id,
            "source_field": key,
            "lang": lang,
            "source_text": text,
            "translated_text": translated,
            "active": True,
        }
        if existing:
            existing.write(vals)
        else:
            existing = self.sudo().create(vals)
        return existing.translated_text or text
