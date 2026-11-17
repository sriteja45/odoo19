import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    xevoria_translation_poc_ids = fields.One2many(
        'xevoria.product.translation.poc',
        'product_tmpl_id',
        string='POC Translations',
    )
    xevoria_website_language_ids = fields.Many2many(
        'res.lang',
        string='Active Website Languages',
        compute='_compute_xevoria_website_languages',
    )
    xevoria_website_language_count = fields.Integer(
        string='Website Language Count',
        compute='_compute_xevoria_website_languages',
    )


    def _xevoria_get_website_sale_description_display_value(self):
        """Return the product sales/quotation description for the active website language.

        Some website_sale/theme templates can render ``description_sale`` from a
        product record that was created before the website language context was
        applied. To make the frontend deterministic, the QWeb view calls this
        helper directly. It prefers the POC row for the active language because
        that is the value the user sees in Translation POC, then falls back to
        Odoo's native translated ``description_sale`` value.
        """
        self.ensure_one()
        lang = self.env.context.get('lang')
        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        ) or 'en_US'

        if lang:
            service = self.env['xevoria.translation.service']
            if service._target_code(lang) != service._target_code(source_lang):
                translation = self.xevoria_translation_poc_ids.filtered(
                    lambda row: row.lang_code == lang and row.translated_description_sale
                )[:1]
                if translation:
                    return translation.translated_description_sale

        product = self.with_context(lang=lang) if lang else self
        return product.description_sale or False

    def _xevoria_website_description_field_name(self):
        """Return the visible eCommerce description field for this Odoo build."""
        for field_name in ('description_ecommerce', 'website_description'):
            if field_name in self._fields:
                return field_name
        return False

    def _xevoria_is_translatable_field(self, field_name):
        field = self._fields.get(field_name)
        return bool(field and getattr(field, 'translate', False))

    def _xevoria_website_description_sync_field_name(self):
        """Return the native field that should receive translated website/eCommerce
        description values.

        Earlier (Step 22) this returned False because writes to the Ecommerce
        Description field appeared to bleed into the English source. The real
        cause was not the field itself: ``action_apply_translation`` already
        refuses to write when the target language resolves to the same
        provider code as the source language (see the guard at the top of that
        method), and the auto-translate hooks pass
        ``xevoria_skip_auto_translation`` to stop recursive re-translation.
        Odoo's ORM writes a translated Html/Text field only for the language in
        the active context, so a write with ``lang=<target>`` cannot touch the
        ``en_US`` stored value as long as the source language is never the
        write's context lang. With that guard confirmed correct, it's safe to
        resume syncing the website description into Odoo's native field so the
        website language switch displays it without any extra step.
        """
        return self._xevoria_website_description_field_name()

    def _xevoria_get_website_description_value(self, lang_code=False):
        product = self.with_context(lang=lang_code) if lang_code else self
        field_name = product._xevoria_website_description_field_name()
        return product[field_name] if field_name else False

    def _xevoria_get_native_website_description_value(self, lang_code=False):
        product = self.with_context(lang=lang_code) if lang_code else self
        field_name = product._xevoria_website_description_sync_field_name()
        return product[field_name] if field_name else False

    def _xevoria_assert_not_writing_source_language(self):
        """Safety net: refuse to apply a translation while the source language
        is active in context.

        ``action_apply_translation`` already skips the source language before
        calling write(), but this second check protects against any future
        caller (custom code, server action, RPC) that might invoke the same
        write path without going through that guard. It guarantees translated
        values are physically incapable of overwriting the English source
        record through this code path.
        """
        lang = self.env.context.get('lang')
        if not lang:
            return
        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        )
        service = self.env['xevoria.translation.service']
        if service._target_code(lang) == service._target_code(source_lang):
            raise UserError(_(
                'Xevoria translation sync refused: the active language context '
                'resolves to the source language (%s). Translated values are '
                'never written into the source language record.'
            ) % source_lang)


    @api.model_create_multi
    def create(self, vals_list):
        """Step 5: optionally auto-translate products right after creation.

        The trigger is controlled from Settings so normal product creation remains
        fast and safe unless the POC automation is enabled. Translation errors
        are logged and do not block product creation.
        """
        products = super().create(vals_list)
        auto_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.auto_translate_on_create', 'False'
        ) == 'True'
        if auto_enabled and not self.env.context.get('xevoria_skip_auto_translation'):
            products.with_context(xevoria_skip_auto_translation=True)._xevoria_enqueue_auto_translate_created_products()
        return products

    def write(self, vals):
        """Step 6: optionally re-translate products after source text updates.

        This watches only product source text fields used by the website. It is
        protected by a context flag so native language sync does not recursively
        trigger another translation run. Errors are logged and never block the
        product save.
        """
        monitored_fields = {'name', 'description_sale', 'website_description', 'description_ecommerce'}
        should_translate = bool(monitored_fields.intersection(vals))
        result = super().write(vals)

        auto_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.auto_translate_on_update', 'False'
        ) == 'True'
        if (
            should_translate
            and auto_enabled
            and not self.env.context.get('xevoria_skip_auto_translation')
        ):
            self.with_context(xevoria_skip_auto_translation=True)._xevoria_enqueue_auto_translate_updated_products()
        return result

    def _xevoria_enqueue_auto_translate_created_products(self):
        """Create queue jobs for newly created products instead of translating inline.

        Production-safe flow: product create -> queue jobs -> cron/manual process.
        This avoids slow product saves and API failures blocking product creation.
        """
        try:
            self.env['xevoria.translation.queue'].sudo().enqueue_products(
                self,
                languages=self._xevoria_get_active_website_languages(),
                sync_native_fields=True,
                created_from='create',
            )
        except Exception:
            _logger.exception('Xevoria auto translation queue creation failed on product creation')
        return True

    def _xevoria_enqueue_auto_translate_updated_products(self):
        """Create queue jobs when product source text changes."""
        try:
            self.env['xevoria.translation.queue'].sudo().enqueue_products(
                self,
                languages=self._xevoria_get_active_website_languages(),
                sync_native_fields=True,
                created_from='update',
            )
        except Exception:
            _logger.exception('Xevoria auto translation queue creation failed on product update')
        return True

    def _xevoria_get_active_website_languages(self):
        """Return active languages configured on websites.

        In backend screens there may be no current website context, so we use all
        configured websites and collect their active languages. If no website
        language is configured yet, we fall back to active res.lang records so the
        POC still works in a fresh database.
        """
        websites = self.env['website'].sudo().search([])
        languages = websites.mapped('language_ids').filtered(lambda lang: lang.active)
        if not languages:
            languages = self.env['res.lang'].sudo().search([('active', '=', True)])
        return languages.sorted(lambda lang: lang.name or lang.code or '')

    def _compute_xevoria_website_languages(self):
        languages = self._xevoria_get_active_website_languages()
        for product in self:
            product.xevoria_website_language_ids = languages
            product.xevoria_website_language_count = len(languages)

    def action_xevoria_prepare_website_language_translations(self):
        """Create one POC translation row for every active website language.

        This is Step 1 foundation for automation: before calling any translation
        API, the module can identify which languages need translated values.
        Existing rows are kept as-is and are not overwritten.
        """
        Translation = self.env['xevoria.product.translation.poc'].sudo()
        languages = self._xevoria_get_active_website_languages()
        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        )
        source_provider_code = self.env['xevoria.translation.service']._target_code(source_lang)
        for product in self:
            existing_lang_ids = set(product.xevoria_translation_poc_ids.mapped('lang_id').ids)
            for lang in languages:
                if lang.id in existing_lang_ids:
                    continue
                if self.env['xevoria.translation.service']._target_code(lang.code) == source_provider_code:
                    continue
                Translation.create({
                    'product_tmpl_id': product.id,
                    'lang_id': lang.id,
                    'translated_name': product.name or _('New Product'),
                    'translated_description_sale': product.description_sale or False,
                    'translated_website_description': product._xevoria_get_website_description_value() or False,
                })
        return True

    def action_xevoria_translate_all_active_languages(self):
        """Step 3: generate translations using configured API provider.

        The default provider is Mock / POC, so the module can be installed and
        demonstrated without external credentials. When Google, DeepL, or Azure
        is configured in Settings, this same workflow calls that provider.
        """
        self.action_xevoria_prepare_website_language_translations()
        languages = self._xevoria_get_active_website_languages()
        active_lang_ids = set(languages.ids)
        service = self.env['xevoria.translation.service']
        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        )
        applied_count = 0
        synced_count = 0

        for product in self:
            translations = product.xevoria_translation_poc_ids.filtered(
                lambda rec: rec.lang_id.id in active_lang_ids
            )
            source_name = product.with_context(lang=source_lang).name or product.name or _('New Product')
            source_description = product.with_context(lang=source_lang).description_sale or product.description_sale
            source_website_description = product._xevoria_get_website_description_value(source_lang) or product._xevoria_get_website_description_value()

            for translation in translations:
                target_lang = translation.lang_code
                if service._target_code(target_lang) == service._target_code(source_lang):
                    continue
                values_to_write = {
                    'translated_name': service.translate_text(source_name, target_lang, source_lang),
                    'translated_description_sale': service.translate_text(source_description, target_lang, source_lang),
                    'translated_website_description': service.translate_text(
                        source_website_description, target_lang, source_lang, html=True
                    ),
                }
                values_to_write = {key: value for key, value in values_to_write.items() if value}
                translation.write(values_to_write)
                review_required = self.env['ir.config_parameter'].sudo().get_param(
                    'xevoria_translation_poc.review_required', 'False'
                ) == 'True'
                if review_required:
                    translation.action_mark_pending_review()
                else:
                    translation.write({'review_state': 'generated', 'generated_at': fields.Datetime.now()})
                    translation.action_apply_translation()
                applied_count += 1
                if translation.native_sync_status == 'synced':
                    synced_count += 1

        catalog_result = {'records': 0, 'fields': 0, 'languages': 0}
        seo_result = {'records': 0, 'fields': 0, 'languages': 0}
        if not self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.review_required', 'False'
        ) == 'True':
            catalog_result = self._xevoria_translate_catalog_records(
                languages=languages,
                source_lang=source_lang,
            )
            seo_result = self._xevoria_translate_seo_records(
                languages=languages,
                source_lang=source_lang,
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation POC'),
                'message': _(
                    'Generated translations for %(product_records)s product-language records, synced %(synced_records)s records, and translated %(catalog_records)s related catalog records.'
                ) % {
                    'product_records': applied_count,
                    'synced_records': synced_count,
                    'catalog_records': catalog_result.get('records', 0),
                },
                'type': 'success',
                'sticky': False,
            },
        }

    def action_xevoria_sync_all_native_translations(self):
        """Step 4: save all prepared rows into Odoo native translated fields."""
        synced_count = 0
        for product in self:
            for translation in product.xevoria_translation_poc_ids:
                translation.action_apply_translation()
                if translation.native_sync_status == 'synced':
                    synced_count += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Native Translation Sync'),
                'message': _('Synced %s product-language records into Odoo native translated fields.') % synced_count,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_xevoria_enqueue_active_language_translations(self):
        """Step 8: create queue jobs for active website languages.

        This does not translate immediately. It creates controlled queue rows that
        can be processed manually now and by cron in the next production step.
        """
        jobs = self.env['xevoria.translation.queue'].sudo().enqueue_products(
            self,
            languages=self._xevoria_get_active_website_languages(),
            sync_native_fields=True,
            created_from='manual',
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Queue'),
                'message': _('Created %s pending translation queue jobs.') % len(jobs),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_xevoria_repair_source_website_description(self):
        """Step 24 repair tool: re-pin the source-language website description.

        Earlier versions of this module could let the English/source website
        description drift or become overwritten with mixed-language, corrupted
        text (placeholder leftovers, wrong-language fragments) due to a bug in
        how HTML was sent to the translation provider and a missing source-
        language pin in update_field_translations calls. Both root causes are
        fixed going forward, but data already corrupted by the old code must
        be repaired once by hand: edit the Website/eCommerce Description field
        on this form (in the source language) with the correct English text,
        then run this action to write it back through update_field_translations
        so it bypasses the same html_translate similarity-check limitation
        that can otherwise silently reject the correction.
        """
        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        )
        field_name = self._xevoria_website_description_sync_field_name()
        if not field_name:
            raise UserError(_('No website/eCommerce description field is available to repair on this Odoo build.'))
        repaired_count = 0
        for product in self:
            current_value = product.with_context(
                lang=source_lang
            )._xevoria_get_native_website_description_value(source_lang)
            if hasattr(product, 'update_field_translations'):
                try:
                    product.update_field_translations(field_name, {source_lang: current_value or False})
                    repaired_count += 1
                    continue
                except Exception:
                    _logger.exception('Xevoria source description repair failed for product %s', product.id)
            product.with_context(lang=source_lang).write({field_name: current_value or False})
            repaired_count += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Source Description Repair'),
                'message': _(
                    'Re-pinned the source-language website description for %s product(s). '
                    'Make sure the field showed the correct English text before running this.'
                ) % repaired_count,
                'type': 'success',
                'sticky': False,
            },
        }
