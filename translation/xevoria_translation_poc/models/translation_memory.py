import hashlib
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class XevoriaTranslationMemory(models.Model):
    _name = 'xevoria.translation.memory'
    _description = 'Xevoria Translation Memory Cache'
    _order = 'write_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    source_lang = fields.Char(required=True, index=True, default='en_US')
    target_lang = fields.Char(required=True, index=True)
    provider = fields.Char(required=True, index=True, default='mock')
    source_hash = fields.Char(required=True, index=True)
    source_text = fields.Text(required=True)
    translated_text = fields.Text(required=True)
    is_html = fields.Boolean(default=False, index=True)
    hit_count = fields.Integer(default=0, readonly=True)
    last_hit_at = fields.Datetime(readonly=True)

    @api.depends('source_lang', 'target_lang', 'provider', 'source_text')
    def _compute_display_name(self):
        for rec in self:
            preview = (rec.source_text or '').replace('\n', ' ')[:45]
            rec.display_name = '%s → %s [%s] %s' % (
                rec.source_lang or '',
                rec.target_lang or '',
                rec.provider or '',
                preview,
            )

    @api.model
    def _normalize_source(self, source_text, is_html=False):
        value = source_text or ''
        # Keep HTML markup exactly as-is because tag/attribute changes can affect output.
        if is_html:
            return value.strip()
        return ' '.join(value.split())

    @api.model
    def compute_source_hash(self, source_text, is_html=False):
        normalized = self._normalize_source(source_text, is_html=is_html)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @api.model
    def get_cached_translation(self, source_text, target_lang, source_lang='en_US', provider='mock', is_html=False):
        if not source_text or not target_lang:
            return False
        source_hash = self.compute_source_hash(source_text, is_html=is_html)
        entry = self.sudo().search([
            ('source_lang', '=', source_lang or 'en_US'),
            ('target_lang', '=', target_lang),
            ('provider', '=', provider or 'mock'),
            ('source_hash', '=', source_hash),
            ('is_html', '=', bool(is_html)),
        ], limit=1)
        if not entry:
            return False
        entry.sudo().write({
            'hit_count': entry.hit_count + 1,
            'last_hit_at': fields.Datetime.now(),
        })
        return entry.translated_text

    @api.model
    def set_cached_translation(self, source_text, translated_text, target_lang, source_lang='en_US', provider='mock', is_html=False):
        if not source_text or not translated_text or not target_lang:
            return False
        source_hash = self.compute_source_hash(source_text, is_html=is_html)
        values = {
            'source_lang': source_lang or 'en_US',
            'target_lang': target_lang,
            'provider': provider or 'mock',
            'source_hash': source_hash,
            'source_text': source_text,
            'translated_text': translated_text,
            'is_html': bool(is_html),
        }
        existing = self.sudo().search([
            ('source_lang', '=', values['source_lang']),
            ('target_lang', '=', values['target_lang']),
            ('provider', '=', values['provider']),
            ('source_hash', '=', values['source_hash']),
            ('is_html', '=', values['is_html']),
        ], limit=1)
        if existing:
            existing.sudo().write({
                'source_text': source_text,
                'translated_text': translated_text,
            })
            return existing
        return self.sudo().create(values)
