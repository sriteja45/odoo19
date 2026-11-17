from odoo import api, fields, models, _
from odoo.exceptions import UserError


class XevoriaTranslationValidationWizard(models.TransientModel):
    _name = 'xevoria.translation.validation.wizard'
    _description = 'Xevoria Translation Production Validation Wizard'

    lang_id = fields.Many2one(
        'res.lang',
        string='Target Language',
        required=True,
        domain=[('active', '=', True)],
        default=lambda self: self.env['res.lang'].search([('active', '=', True), ('code', '!=', self._default_source_lang())], limit=1),
    )
    sample_limit = fields.Integer(string='Sample Products', default=20)
    include_catalog = fields.Boolean(string='Validate Catalog Components', default=True)
    include_seo = fields.Boolean(string='Validate SEO Fields', default=True)
    include_search_terms = fields.Boolean(string='Validate Search Terms', default=True)
    include_rtl_hint = fields.Boolean(string='Include RTL Layout Hint', default=True)
    result_html = fields.Html(string='Validation Result', readonly=True)

    def _default_source_lang(self):
        return self.env['ir.config_parameter'].sudo().get_param('xevoria_translation_poc.source_lang', 'en_US')

    def _ok(self, text):
        return '<li class="text-success">✅ %s</li>' % text

    def _warn(self, text):
        return '<li class="text-warning">⚠️ %s</li>' % text

    def _bad(self, text):
        return '<li class="text-danger">❌ %s</li>' % text

    def _count_missing_product_translations(self, products, lang):
        Translation = self.env['xevoria.product.translation.poc'].sudo()
        missing = 0
        not_published = 0
        for product in products:
            row = Translation.search([('product_tmpl_id', '=', product.id), ('lang_id', '=', lang.id)], limit=1)
            if not row:
                missing += 1
            elif row.review_state not in ('published', 'approved', 'generated', 'pending_review'):
                not_published += 1
        return missing, not_published

    def _translated_value_exists(self, record, field_name, lang_code):
        if not record or field_name not in record._fields:
            return True
        value = record.with_context(lang=lang_code)[field_name]
        source_lang = self._default_source_lang()
        source_value = record.with_context(lang=source_lang)[field_name]
        if not source_value:
            return True
        return bool(value) and value != source_value

    def _validate_catalog_records(self, products, lang):
        warnings = []
        checked = 0
        missing = 0
        for product in products:
            records = []
            if product.categ_id:
                records.append((product.categ_id, 'name', _('Product Category')))
            if 'public_categ_ids' in product._fields:
                records += [(cat, 'name', _('Website Category')) for cat in product.public_categ_ids]
            if 'attribute_line_ids' in product._fields:
                for line in product.attribute_line_ids:
                    if line.attribute_id:
                        records.append((line.attribute_id, 'name', _('Attribute')))
                    records += [(value, 'name', _('Attribute Value')) for value in line.value_ids]
            if 'product_tag_ids' in product._fields:
                records += [(tag, 'name', _('Product Tag')) for tag in product.product_tag_ids]
            for record, field_name, label in records:
                checked += 1
                if not self._translated_value_exists(record, field_name, lang.code):
                    missing += 1
        if checked and missing:
            warnings.append(self._warn(_('%(missing)s of %(checked)s sampled catalog values still look untranslated for %(lang)s.') % {
                'missing': missing, 'checked': checked, 'lang': lang.code,
            }))
        elif checked:
            warnings.append(self._ok(_('Sampled catalog values have target-language values.')))
        else:
            warnings.append(self._warn(_('No catalog components were found on sampled products.')))
        return warnings

    def _validate_seo_records(self, products, lang):
        warnings = []
        seo_fields = ['website_meta_title', 'website_meta_description', 'website_meta_keywords', 'seo_name']
        checked = 0
        missing = 0
        for product in products:
            for field_name in seo_fields:
                if field_name in product._fields:
                    checked += 1
                    if not self._translated_value_exists(product, field_name, lang.code):
                        missing += 1
            if 'product_template_image_ids' in product._fields:
                for image in product.product_template_image_ids:
                    for field_name in ['name', 'alt']:
                        if field_name in image._fields:
                            checked += 1
                            if not self._translated_value_exists(image, field_name, lang.code):
                                missing += 1
        if checked and missing:
            warnings.append(self._warn(_('%(missing)s of %(checked)s sampled SEO/image values still look untranslated for %(lang)s.') % {
                'missing': missing, 'checked': checked, 'lang': lang.code,
            }))
        elif checked:
            warnings.append(self._ok(_('Sampled SEO/image values have target-language values.')))
        else:
            warnings.append(self._warn(_('No SEO/image translatable fields were detected on sampled products.')))
        return warnings

    def _validate_queue_health(self):
        Queue = self.env['xevoria.translation.queue'].sudo()
        pending = Queue.search_count([('state', '=', 'pending')])
        failed = Queue.search_count([('state', '=', 'failed')])
        running = Queue.search_count([('state', '=', 'running')])
        done = Queue.search_count([('state', '=', 'done')])
        items = []
        items.append(self._ok(_('Queue done jobs: %s') % done))
        if pending:
            items.append(self._warn(_('Pending queue jobs: %s') % pending))
        else:
            items.append(self._ok(_('No pending queue jobs.')))
        if running:
            items.append(self._warn(_('Running queue jobs found: %s') % running))
        if failed:
            items.append(self._bad(_('Failed queue jobs need review: %s') % failed))
        else:
            items.append(self._ok(_('No failed queue jobs.')))
        return items

    def _validate_memory_health(self):
        Memory = self.env['xevoria.translation.memory'].sudo()
        count = Memory.search_count([])
        hits = sum(Memory.search([]).mapped('hit_count')) if 'hit_count' in Memory._fields else 0
        if count:
            return [self._ok(_('Translation memory entries: %(count)s; cache hits: %(hits)s') % {'count': count, 'hits': hits})]
        return [self._warn(_('Translation memory is empty. Run translations once to build cache.'))]

    def action_run_validation(self):
        self.ensure_one()
        if self.sample_limit <= 0:
            raise UserError(_('Sample Products must be greater than zero.'))
        Product = self.env['product.template'].sudo()
        products = Product.search([('sale_ok', '=', True)], limit=min(self.sample_limit, 200))
        lines = ['<h3>%s</h3><ul>' % _('Xevoria Translation Production Validation')]
        lines += self._validate_queue_health()
        lines += self._validate_memory_health()
        if not products:
            lines.append(self._bad(_('No saleable products found for validation.')))
        else:
            missing, weak_state = self._count_missing_product_translations(products, self.lang_id)
            if missing:
                lines.append(self._warn(_('%(missing)s of %(count)s sampled products do not have a translation row for %(lang)s.') % {
                    'missing': missing, 'count': len(products), 'lang': self.lang_id.code,
                }))
            else:
                lines.append(self._ok(_('All sampled products have translation rows for %s.') % self.lang_id.code))
            if weak_state:
                lines.append(self._warn(_('%s sampled translation rows are still in early draft/rejected states.') % weak_state))
            if self.include_catalog:
                lines += self._validate_catalog_records(products, self.lang_id)
            if self.include_seo:
                lines += self._validate_seo_records(products, self.lang_id)
        if self.include_search_terms:
            lines.append(self._warn(_('Search validation note: test translated keywords manually on the website after Odoo search indexing/cache refresh.')))
        if self.include_rtl_hint and self.lang_id.direction == 'rtl':
            lines.append(self._warn(_('RTL language selected. Verify header, product grid, filters, cart, and checkout alignment in the website frontend.')))
        elif self.include_rtl_hint:
            lines.append(self._ok(_('Selected language is not RTL.')))
        lines.append('</ul>')
        self.result_html = ''.join(lines)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Validation'),
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
