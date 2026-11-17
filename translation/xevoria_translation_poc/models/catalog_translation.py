import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class ProductTemplateCatalogTranslation(models.Model):
    _inherit = 'product.template'

    def _xevoria_catalog_supported_models(self):
        """Return optional catalog models available in this database.

        The module depends on website_sale, product.category, product.public.category,
        product.attribute, and product.attribute.value are normally available.  Product
        tags/brands can differ between Odoo editions/custom addons, so every optional
        model/field is checked at runtime instead of hard failing during install.
        """
        supported = set()
        for model_name in (
            'product.category',
            'product.public.category',
            'product.attribute',
            'product.attribute.value',
            'product.tag',
            'product.brand',
        ):
            if model_name in self.env:
                supported.add(model_name)
        return supported

    def _xevoria_catalog_translatable_fields(self, record):
        """Catalog fields safe to machine-translate for the given record."""
        candidates_by_model = {
            'product.category': ('name',),
            'product.public.category': ('name', 'website_description'),
            'product.attribute': ('name',),
            'product.attribute.value': ('name',),
            'product.tag': ('name',),
            'product.brand': ('name', 'description'),
        }
        result = []
        for field_name in candidates_by_model.get(record._name, ()):  # optional model-safe
            field = record._fields.get(field_name)
            if field and getattr(field, 'translate', False):
                result.append(field_name)
        return result

    def _xevoria_collect_catalog_records(self):
        """Collect catalog records used by selected products.

        Covers:
        - internal product categories (product.category)
        - website/eCommerce categories (product.public.category)
        - attributes and attribute values used by variants
        - product tags when available
        - brand records when a supported brand field/custom model exists
        """
        supported = self._xevoria_catalog_supported_models()
        records_by_model = {}

        def add(recordset):
            for rec in recordset.exists():
                if rec._name in supported:
                    records_by_model.setdefault(rec._name, self.env[rec._name])
                    records_by_model[rec._name] |= rec

        for product in self:
            if 'product.category' in supported and 'categ_id' in product._fields:
                add(product.categ_id)
            if 'product.public.category' in supported and 'public_categ_ids' in product._fields:
                add(product.public_categ_ids)
            if 'attribute_line_ids' in product._fields:
                lines = product.attribute_line_ids
                if 'product.attribute' in supported:
                    add(lines.mapped('attribute_id'))
                if 'product.attribute.value' in supported:
                    add(lines.mapped('value_ids'))
            if 'product.tag' in supported and 'product_tag_ids' in product._fields:
                add(product.product_tag_ids)
            if 'product.brand' in supported:
                for brand_field in ('brand_id', 'product_brand_id'):
                    if brand_field in product._fields:
                        add(product[brand_field])

        return records_by_model

    def _xevoria_write_catalog_translation(self, record, field_name, lang_code, translated_value, source_lang, source_value):
        """Write one translated catalog field without touching the source value."""
        if not translated_value:
            return False
        if hasattr(record, 'update_field_translations'):
            try:
                record.update_field_translations(field_name, {
                    source_lang: source_value or False,
                    lang_code: translated_value,
                })
                record.invalidate_recordset([field_name])
                return True
            except Exception:
                _logger.exception(
                    'Xevoria catalog update_field_translations failed: model=%s id=%s field=%s lang=%s',
                    record._name, record.id, field_name, lang_code,
                )
        record.with_context(lang=lang_code, xevoria_skip_auto_translation=True).write({field_name: translated_value})
        return True

    def _xevoria_translate_catalog_records(self, languages=None, source_lang=None):
        """Translate catalog records related to these products into target languages."""
        self = self.exists()
        if not self:
            return {'records': 0, 'fields': 0, 'languages': 0}

        languages = languages or self._xevoria_get_active_website_languages()
        source_lang = source_lang or self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        ) or 'en_US'
        service = self.env['xevoria.translation.service']
        source_provider_code = service._target_code(source_lang)
        target_languages = languages.filtered(lambda lang: service._target_code(lang.code) != source_provider_code)
        records_by_model = self._xevoria_collect_catalog_records()

        translated_records = 0
        translated_fields = 0
        for model_name, records in records_by_model.items():
            for record in records:
                field_names = self._xevoria_catalog_translatable_fields(record)
                if not field_names:
                    continue
                record_had_translation = False
                for lang in target_languages:
                    for field_name in field_names:
                        source_record = record.with_context(lang=source_lang)
                        source_value = source_record[field_name]
                        if not source_value:
                            continue
                        translated_value = service.translate_text(
                            source_value,
                            lang.code,
                            source_lang,
                            html=record._fields[field_name].type == 'html',
                        )
                        if self._xevoria_write_catalog_translation(
                            record, field_name, lang.code, translated_value, source_lang, source_value
                        ):
                            translated_fields += 1
                            record_had_translation = True
                if record_had_translation:
                    translated_records += 1
        return {
            'records': translated_records,
            'fields': translated_fields,
            'languages': len(target_languages),
        }

    def action_xevoria_translate_catalog_components(self):
        """Manual button: translate categories, attributes, values, tags, and brands."""
        result = self._xevoria_translate_catalog_records(
            languages=self._xevoria_get_active_website_languages(),
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Catalog Translation'),
                'message': _(
                    'Translated %(records)s catalog records across %(languages)s target languages (%(fields)s field writes).'
                ) % result,
                'type': 'success',
                'sticky': False,
            },
        }
