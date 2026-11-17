from odoo import _, api, fields, models
from odoo.exceptions import UserError


class XevoriaBulkTranslationWizard(models.TransientModel):
    _name = 'xevoria.bulk.translation.wizard'
    _description = 'Xevoria Bulk Product Translation Wizard'

    product_ids = fields.Many2many(
        'product.template',
        string='Products',
        required=True,
    )
    language_ids = fields.Many2many(
        'res.lang',
        string='Target Languages',
        required=True,
        domain=[('active', '=', True)],
    )
    only_missing_translations = fields.Boolean(
        string='Only Fill Missing Translation Rows',
        default=False,
        help='When enabled, existing translated values are not regenerated. New/missing language rows are still created.',
    )
    sync_native_fields = fields.Boolean(
        string='Sync to Odoo Native Translated Fields',
        default=True,
    )
    process_in_queue = fields.Boolean(
        string='Create Queue Jobs Instead of Translating Now',
        default=True,
        help='Recommended for many products. Queue jobs can be processed from Xevoria Translation → Translation Queue. Large batches are automatically queued to avoid browser timeouts.',
    )
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_counts',
    )
    language_count = fields.Integer(
        string='Language Count',
        compute='_compute_counts',
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []
        if active_model == 'product.template' and active_ids:
            values['product_ids'] = [(6, 0, active_ids)]
        languages = self.env['product.template']._xevoria_get_active_website_languages()
        if languages:
            values['language_ids'] = [(6, 0, languages.ids)]
        return values

    @api.depends('product_ids', 'language_ids')
    def _compute_counts(self):
        for wizard in self:
            wizard.product_count = len(wizard.product_ids)
            wizard.language_count = len(wizard.language_ids)

    def _xevoria_should_force_queue(self):
        """Return True when synchronous processing is unsafe for one RPC call.

        Bulk translation performs provider HTTP calls for every product/language
        pair and can easily exceed the browser/Odoo RPC timeout. Queueing large
        selections keeps the UI responsive and lets cron process jobs safely.
        """
        self.ensure_one()
        pair_count = len(self.product_ids) * len(self.language_ids)
        params = self.env['ir.config_parameter'].sudo()
        try:
            threshold = int(params.get_param('xevoria_translation_poc.bulk_sync_pair_limit', '5') or 5)
        except ValueError:
            threshold = 5
        threshold = max(1, min(threshold, 100))
        return pair_count > threshold

    def _xevoria_validate_provider_before_run(self):
        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        )
        self.env['xevoria.translation.service'].validate_language_pairs(
            self.language_ids,
            source_lang_code=source_lang,
        )

    def _xevoria_enqueue_bulk_jobs(self, forced=False):
        self._xevoria_validate_provider_before_run()
        summary = self.env['xevoria.translation.queue'].sudo().enqueue_products_with_summary(
            self.product_ids,
            languages=self.language_ids,
            sync_native_fields=self.sync_native_fields,
            only_missing_translations=self.only_missing_translations,
            created_from='bulk',
        )
        message = _(
            'Created %(created)s translation queue jobs. Skipped %(skipped)s duplicates/already-completed/source-language jobs. Process them from Xevoria Translation → Translation Queue, or wait for the scheduled cron.'
        ) % {
            'created': summary['created'],
            'skipped': summary['skipped_total'],
        }
        if forced:
            message = _(
                'This selection is too large for one browser request, so it was queued automatically. Created %(created)s translation queue jobs. Skipped %(skipped)s duplicates/already-completed/source-language jobs. Process them from Xevoria Translation → Translation Queue, or wait for the scheduled cron.'
            ) % {
                'created': summary['created'],
                'skipped': summary['skipped_total'],
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Product Translation'),
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_run_bulk_translation(self):
        self.ensure_one()
        if not self.product_ids:
            raise UserError(_('Please select at least one product.'))
        if not self.language_ids:
            raise UserError(_('Please select at least one target language.'))

        self._xevoria_validate_provider_before_run()
        forced_queue = self._xevoria_should_force_queue()
        if self.process_in_queue or forced_queue:
            return self._xevoria_enqueue_bulk_jobs(forced=forced_queue and not self.process_in_queue)

        Translation = self.env['xevoria.product.translation.poc'].sudo()
        service = self.env['xevoria.translation.service']
        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        )
        created_count = 0
        generated_count = 0
        synced_count = 0
        skipped_count = 0

        for product in self.product_ids:
            existing_by_lang = {
                translation.lang_id.id: translation
                for translation in product.xevoria_translation_poc_ids
            }
            source_product = product.with_context(lang=source_lang)
            source_name = source_product.name or product.name or _('New Product')
            source_description = source_product.description_sale or product.description_sale
            source_website_description = product._xevoria_get_website_description_value(source_lang) or product._xevoria_get_website_description_value()

            for lang in self.language_ids:
                if service._target_code(lang.code) == service._target_code(source_lang):
                    skipped_count += 1
                    continue
                translation = existing_by_lang.get(lang.id)
                if not translation:
                    translation = Translation.create({
                        'product_tmpl_id': product.id,
                        'lang_id': lang.id,
                        'translated_name': source_name,
                        'translated_description_sale': source_description or False,
                        'translated_website_description': source_website_description or False,
                    })
                    created_count += 1

                has_existing_values = bool(
                    translation.translated_name
                    and (translation.translated_description_sale or not source_description)
                    and (translation.translated_website_description or not source_website_description)
                )
                if self.only_missing_translations and has_existing_values:
                    skipped_count += 1
                else:
                    target_lang = translation.lang_code or lang.code
                    values_to_write = {
                        'translated_name': service.translate_text(source_name, target_lang, source_lang),
                        'translated_description_sale': service.translate_text(source_description, target_lang, source_lang),
                        'translated_website_description': service.translate_text(
                            source_website_description, target_lang, source_lang, html=True
                        ),
                    }
                    values_to_write = {key: value for key, value in values_to_write.items() if value}
                    translation.write(values_to_write)
                    generated_count += 1

                if self.sync_native_fields:
                    translation.action_apply_translation()
                    if translation.native_sync_status == 'synced':
                        synced_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Product Translation'),
                'message': _(
                    'Processed %(products)s products and %(languages)s languages. Created %(created)s rows, generated %(generated)s translations, synced %(synced)s rows, skipped %(skipped)s existing rows.'
                ) % {
                    'products': len(self.product_ids),
                    'languages': len(self.language_ids),
                    'created': created_count,
                    'generated': generated_count,
                    'synced': synced_count,
                    'skipped': skipped_count,
                },
                'type': 'success',
                'sticky': False,
            },
        }
