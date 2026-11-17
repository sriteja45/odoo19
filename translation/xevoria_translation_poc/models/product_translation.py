import json
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTranslationPoc(models.Model):
    _name = 'xevoria.product.translation.poc'
    _description = 'Product Translation POC'
    _rec_name = 'display_name'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        ondelete='cascade',
        index=True,
    )
    lang_id = fields.Many2one(
        'res.lang',
        string='Language',
        required=True,
        domain=[('active', '=', True)],
    )
    lang_code = fields.Char(
        related='lang_id.code',
        string='Language Code',
        store=True,
        readonly=True,
    )
    translated_name = fields.Char(string='Translated Product Name', required=True)
    translated_description_sale = fields.Text(string='Translated Sales Description')
    translated_website_description = fields.Html(string='Translated Website Description')
    display_name = fields.Char(compute='_compute_display_name', store=False)
    applied = fields.Boolean(string='Applied', readonly=True, copy=False)
    native_sync_status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('synced', 'Synced'),
            ('mismatch', 'Mismatch'),
        ],
        string='Native Sync Status',
        default='draft',
        readonly=True,
        copy=False,
    )
    last_applied_date = fields.Datetime(string='Last Applied On', readonly=True, copy=False)
    review_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('generated', 'Generated'),
            ('pending_review', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('published', 'Published'),
        ],
        string='Review Status',
        default='draft',
        required=True,
        index=True,
        copy=False,
        help='Quality-control workflow for generated translations before publishing them to Odoo native translated fields.',
    )
    generated_at = fields.Datetime(string='Generated On', readonly=True, copy=False)
    reviewed_at = fields.Datetime(string='Reviewed On', readonly=True, copy=False)
    reviewed_by = fields.Many2one('res.users', string='Reviewed By', readonly=True, copy=False)
    published_at = fields.Datetime(string='Published On', readonly=True, copy=False)
    reviewer_note = fields.Text(string='Reviewer Note', copy=False)

    _unique_product_language_poc = models.Constraint(
        'unique(product_tmpl_id, lang_id)',
        'Only one POC translation is allowed per product and language.',
    )

    @api.depends('product_tmpl_id', 'lang_id')
    def _compute_display_name(self):
        for rec in self:
            product = rec.product_tmpl_id.display_name or _('Product')
            lang = rec.lang_id.name or rec.lang_code or _('Language')
            rec.display_name = f'{product} - {lang}'

    def _xevoria_review_required(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.review_required', 'False'
        ) == 'True'

    def action_mark_pending_review(self):
        self.write({
            'review_state': 'pending_review',
            'generated_at': fields.Datetime.now(),
        })
        return True

    def action_approve_translation(self):
        now = fields.Datetime.now()
        self.write({
            'review_state': 'approved',
            'reviewed_at': now,
            'reviewed_by': self.env.user.id,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Review'),
                'message': _('Selected translations were approved. Use Publish to sync them to the website/native fields.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_reject_translation(self):
        self.write({
            'review_state': 'rejected',
            'reviewed_at': fields.Datetime.now(),
            'reviewed_by': self.env.user.id,
            'applied': False,
            'native_sync_status': 'draft',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Review'),
                'message': _('Selected translations were rejected and will not be published.'),
                'type': 'warning',
                'sticky': False,
            },
        }

    def action_publish_translation(self):
        for rec in self:
            if rec._xevoria_review_required() and rec.review_state not in ('approved', 'published'):
                raise UserError(_('Please approve the translation before publishing it.'))
            rec.action_apply_translation()
            rec.product_tmpl_id._xevoria_translate_catalog_records(
                languages=rec.lang_id,
                source_lang=self.env['ir.config_parameter'].sudo().get_param('xevoria_translation_poc.source_lang', 'en_US'),
            )
            rec.product_tmpl_id._xevoria_translate_seo_records(
                languages=rec.lang_id,
                source_lang=self.env['ir.config_parameter'].sudo().get_param('xevoria_translation_poc.source_lang', 'en_US'),
            )
            rec.write({'review_state': 'published', 'published_at': fields.Datetime.now()})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Published'),
                'message': _('Approved translations were published to Odoo native translated fields.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_reset_to_review(self):
        self.write({'review_state': 'pending_review', 'reviewed_at': False, 'reviewed_by': False})
        return True

    def action_apply_translation(self):
        for rec in self:
            if rec._xevoria_review_required() and rec.review_state not in ('approved', 'published'):
                raise UserError(_('This translation requires review approval before applying it to native fields.'))
            if not rec.lang_code:
                raise UserError(_('Please select an active language before applying translation.'))

            service = self.env['xevoria.translation.service']
            source_lang = self.env['ir.config_parameter'].sudo().get_param(
                'xevoria_translation_poc.source_lang', 'en_US'
            )
            if service._target_code(rec.lang_code) == service._target_code(source_lang):
                # Never write translated values into the source/base language.
                # This prevents the English eCommerce Description from being overwritten
                # when English is also configured as an active website language.
                rec.write({
                    'applied': False,
                    'native_sync_status': 'draft',
                    'last_applied_date': fields.Datetime.now(),
                })
                continue

            values = {
                'name': rec.translated_name,
            }
            target_product = rec.product_tmpl_id.with_context(
                lang=rec.lang_code,
                xevoria_skip_auto_translation=True,
                xevoria_skip_translation_queue=True,
            )
            # Second safety net: refuse if the active write context ever
            # resolves to the source language (see _xevoria_assert_not_writing_source_language).
            target_product._xevoria_assert_not_writing_source_language()
            # Capture the source/base website description before any translated
            # value is applied. This source snapshot is pinned back into the
            # JSONB translation dictionary below, so English cannot be replaced
            # by the last target language (Hindi/French/German).
            source_website_description = rec.product_tmpl_id.with_context(
                lang=source_lang
            )._xevoria_get_native_website_description_value(source_lang)
            target_product.write(values)

            # In Odoo 19 translated Text/Html values are stored as JSONB
            # dictionaries.  The website product page can still show the source
            # quotation description if description_sale is only written through
            # the ORM context in some website/cache flows.  Apply it with the
            # same JSONB-safe path used for the eCommerce description so the
            # product page, sale quotation line, and native field all read the
            # target-language value.
            source_description_sale = rec.product_tmpl_id.with_context(
                lang=source_lang
            ).description_sale
            rec._xevoria_apply_translated_field_jsonb(
                'description_sale',
                rec.translated_description_sale or False,
                source_value=source_description_sale,
            )

            rec._xevoria_apply_website_description(
                target_product,
                source_website_description=source_website_description,
            )
            # Flush so the verification read-back below cannot see a stale
            # cached value for translated Text/Html fields.
            rec.product_tmpl_id.flush_recordset(['name', 'description_sale'])
            rec._xevoria_verify_native_translation_sync()
            if rec.native_sync_status == 'synced' and rec.review_state in ('draft', 'generated', 'approved'):
                rec.write({'review_state': 'published', 'published_at': fields.Datetime.now()})
        return True

    def _xevoria_apply_website_description(self, target_product, source_website_description=False):
        """Safely write website/eCommerce HTML translations per language.

        Odoo 19 stores translated Html fields such as ``description_ecommerce``
        as a JSONB dictionary on ``product_template``. In some builds/provider
        flows, ORM/context writes or partial ``update_field_translations`` calls
        can make the last translated HTML value become the fallback/source value,
        which is exactly what caused English/French/German pages to show the
        Hindi eCommerce description.

        This method therefore updates the JSONB dictionary directly and only for
        explicit language keys:

        * source language is pinned to the captured source HTML,
        * every prepared POC row gets its own language key,
        * the current row wins for its language,
        * other languages already present in JSONB are preserved by ``||`` merge.

        No translated website description is ever written through a source-lang
        ORM context here.
        """
        self.ensure_one()
        product = self.product_tmpl_id
        field_name = product._xevoria_website_description_sync_field_name()
        if not field_name or field_name not in product._fields:
            return

        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        ) or 'en_US'
        current_value = self.translated_website_description or False

        # Pin source/base language. Prefer the snapshot captured before applying
        # the current translation. If unavailable, read the source language now.
        source_value = source_website_description
        if source_value is False:
            source_value = product.with_context(
                lang=source_lang
            )._xevoria_get_native_website_description_value(source_lang)
        if source_value is False:
            source_value = product._xevoria_get_website_description_value() or False

        translations = {}
        if source_lang:
            translations[source_lang] = source_value or False

        for row in product.xevoria_translation_poc_ids.filtered(lambda r: r.lang_code):
            if row.lang_code == source_lang:
                continue
            translations[row.lang_code] = row.translated_website_description or False

        if self.lang_code and self.lang_code != source_lang:
            translations[self.lang_code] = current_value

        # Remove empty target values so an empty draft row cannot erase a valid
        # website description for that language. Keep source key even if empty.
        translations = {
            lang: value for lang, value in translations.items()
            if lang == source_lang or value
        }
        if not translations:
            return

        # Direct JSONB merge is safer than a translated-field ORM write here.
        # Field names come from _fields, not user input.
        self.env.cr.execute(
            'UPDATE product_template '
            'SET "%s" = COALESCE("%s", %s::jsonb) || %s::jsonb '
            'WHERE id = %s' % (field_name, field_name, '%s', '%s', '%s'),
            [json.dumps({}), json.dumps(translations), product.id],
        )
        product.invalidate_recordset([field_name])

    def _xevoria_apply_translated_field_jsonb(self, field_name, translated_value, source_value=False):
        """Write a translated product.template field with source-language lock.

        This is used for plain Text fields such as ``description_sale``.  It
        mirrors the website/eCommerce HTML JSONB merge and prevents the source
        language value from being replaced by a target language.  If a future
        Odoo build exposes the field as non-translatable, the method exits
        safely instead of touching the column.
        """
        self.ensure_one()
        product = self.product_tmpl_id
        field = product._fields.get(field_name)
        if not field or not getattr(field, 'translate', False):
            return

        source_lang = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        ) or 'en_US'
        translations = {}
        if source_lang:
            translations[source_lang] = source_value or False
        if self.lang_code and self.lang_code != source_lang and translated_value:
            translations[self.lang_code] = translated_value

        if not translations:
            return

        self.env.cr.execute(
            'UPDATE product_template '
            'SET "%s" = COALESCE("%s", %%s::jsonb) || %%s::jsonb '
            'WHERE id = %%s' % (field_name, field_name),
            [json.dumps({}), json.dumps(translations), product.id],
        )
        product.invalidate_recordset([field_name])

    def _xevoria_normalize_text(self, value):
        """Normalize whitespace before comparing plain-text translated values.

        Translation providers frequently return text with different leading,
        trailing, or internal whitespace than what gets stored. Without this,
        description_sale comparisons report a false 'mismatch' even though the
        value written to Odoo is correct and the website displays it properly.
        """
        return re.sub(r'\s+', ' ', value or '').strip()

    def _xevoria_normalize_html(self, value):
        """Normalize simple HTML differences before sync comparison.

        Odoo may normalize/sanitize HTML fields during write. Comparing stripped
        whitespace avoids false mismatch statuses for equivalent website HTML.
        """
        return re.sub(r'\s+', ' ', value or '').strip()

    def _xevoria_verify_native_translation_sync(self):
        """Confirm that Odoo native translated fields contain this row's values.

        Step 4 stores translations in the standard Odoo translated fields using
        the language context, then reads them back in the same language. This
        keeps website rendering native: the website language switch displays
        product.name, description_sale, and website_description from Odoo itself.
        """
        for rec in self:
            website_field_name = rec.product_tmpl_id._xevoria_website_description_sync_field_name()
            if website_field_name:
                rec.product_tmpl_id.invalidate_recordset([website_field_name])
            product_in_lang = rec.product_tmpl_id.with_context(lang=rec.lang_code)
            name_ok = rec._xevoria_normalize_text(product_in_lang.name) == rec._xevoria_normalize_text(rec.translated_name)
            sale_ok = rec._xevoria_normalize_text(product_in_lang.description_sale) == rec._xevoria_normalize_text(rec.translated_description_sale)
            website_ok = rec._xevoria_normalize_html(
                rec.product_tmpl_id._xevoria_get_native_website_description_value(rec.lang_code)
            ) == rec._xevoria_normalize_html(rec.translated_website_description)
            rec.write({
                'applied': bool(name_ok and sale_ok and website_ok),
                'native_sync_status': 'synced' if name_ok and sale_ok and website_ok else 'mismatch',
                'last_applied_date': fields.Datetime.now(),
            })

    def action_sync_native_translation(self):
        # Push the POC row values into Odoo native translated fields.
        # Do not pull native values first: if the native HTML dictionary is already
        # corrupted, reading it here would overwrite the correct POC row value.
        self.action_apply_translation()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Native Translation Sync'),
                'message': _('Translation values were saved into Odoo native translated product fields.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_preview_translation(self):
        self.ensure_one()
        if not self.lang_code:
            raise UserError(_('Please select a language first.'))
        product = self.product_tmpl_id.with_context(lang=self.lang_code)
        url = product.website_url or '/shop/product/%s' % product.id
        website = self.env['website'].get_current_website()
        if website and hasattr(website, '_get_url_localized'):
            try:
                url = website._get_url_localized(url, lang_code=self.lang_code)
            except Exception:
                pass
        return {
            'type': 'ir.actions.act_url',
            'name': _('Product Translation Preview'),
            'url': url,
            'target': 'self',
        }
