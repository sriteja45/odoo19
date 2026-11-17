import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class ProductTemplateSeoTranslation(models.Model):
    _inherit = 'product.template'

    def _xevoria_seo_product_field_candidates(self):
        """SEO fields that may exist on product.template depending on Odoo build/addons.

        Odoo website_sale normally inherits website.seo.metadata, which provides
        website_meta_title, website_meta_description, and website_meta_keywords.
        Some builds also expose seo_name as a translatable slug/search-name helper.
        Every field is checked at runtime to keep installation safe across Odoo 19
        builds and custom themes.
        """
        return (
            'website_meta_title',
            'website_meta_description',
            'website_meta_keywords',
            'seo_name',
        )

    def _xevoria_seo_translatable_fields(self, record):
        """Return safe SEO/image fields to machine-translate for a record."""
        candidates_by_model = {
            'product.template': self._xevoria_seo_product_field_candidates(),
            # product.image.name is the common source for product gallery image
            # labels/alt text in website_sale themes. The binary image itself is
            # intentionally never touched.
            'product.image': ('name',),
            # Some custom product media addons use ir.attachment name/description
            # as image labels. Only translate them when fields are explicitly
            # translatable in the installed Odoo build.
            'ir.attachment': ('name', 'description'),
        }
        result = []
        for field_name in candidates_by_model.get(record._name, ()):  # optional model-safe
            field = record._fields.get(field_name)
            if field and getattr(field, 'translate', False):
                result.append(field_name)
        return result

    def _xevoria_collect_seo_records(self):
        """Collect SEO-related records for selected products.

        Covers product template SEO metadata plus optional product gallery image
        labels. Slugs are handled by translating seo_name when that field exists;
        if an Odoo build computes slugs directly from translated product names,
        the existing product name translation already improves localized URLs.
        """
        records_by_model = {}

        def add(recordset):
            for rec in recordset.exists():
                records_by_model.setdefault(rec._name, self.env[rec._name])
                records_by_model[rec._name] |= rec

        add(self)

        if 'product.image' in self.env:
            for product in self:
                for field_name in ('product_template_image_ids', 'product_variant_image_ids'):
                    if field_name in product._fields:
                        add(product[field_name])

        # Conservative support for custom website image attachments. Only include
        # attachments explicitly linked to these product templates and only when
        # attachment label fields are translatable.
        if 'ir.attachment' in self.env:
            attachments = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'product.template'),
                ('res_id', 'in', self.ids),
                ('mimetype', 'ilike', 'image/'),
            ])
            if attachments:
                add(attachments)

        return records_by_model

    def _xevoria_write_seo_translation(self, record, field_name, lang_code, translated_value, source_lang, source_value):
        """Write one translated SEO/media field without changing source text."""
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
                    'Xevoria SEO update_field_translations failed: model=%s id=%s field=%s lang=%s',
                    record._name, record.id, field_name, lang_code,
                )
        record.with_context(lang=lang_code, xevoria_skip_auto_translation=True).write({field_name: translated_value})
        return True

    def _xevoria_translate_seo_records(self, languages=None, source_lang=None):
        """Translate SEO metadata and image labels related to these products."""
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
        records_by_model = self._xevoria_collect_seo_records()

        translated_records = 0
        translated_fields = 0
        for model_name, records in records_by_model.items():
            for record in records:
                field_names = self._xevoria_seo_translatable_fields(record)
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
                        if self._xevoria_write_seo_translation(
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

    def action_xevoria_translate_seo_components(self):
        """Manual button: translate product SEO metadata and image labels."""
        result = self._xevoria_translate_seo_records(
            languages=self._xevoria_get_active_website_languages(),
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('SEO Translation'),
                'message': _(
                    'Translated %(records)s SEO/media records across %(languages)s target languages (%(fields)s field writes).'
                ) % result,
                'type': 'success',
                'sticky': False,
            },
        }
