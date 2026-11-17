from odoo import api, fields, models


class XevoriaTranslationLog(models.Model):
    _name = 'xevoria.translation.log'
    _description = 'Xevoria Product Translation Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    queue_id = fields.Many2one('xevoria.translation.queue', string='Queue Job', ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product', index=True)
    lang_id = fields.Many2one('res.lang', string='Language', index=True)
    level = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], string='Level', default='info', required=True, index=True)
    action = fields.Selection([
        ('enqueue', 'Enqueued'),
        ('start', 'Started'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retry', 'Retry'),
        ('cancel', 'Cancel'),
        ('cron', 'Cron'),
        ('skip', 'Skipped'),
        ('backoff', 'Backoff'),
        ('failover', 'Provider Failover'),
        ('rate_limit', 'Rate Limit'),
    ], string='Action', required=True, index=True)
    message = fields.Text(required=True)
    attempts = fields.Integer(string='Attempts')
    provider = fields.Char(string='Provider')
    exception_type = fields.Char(string='Exception Type')

    @api.depends('action', 'product_tmpl_id', 'lang_id', 'level')
    def _compute_display_name(self):
        for rec in self:
            parts = [dict(rec._fields['action'].selection).get(rec.action, rec.action or '')]
            if rec.product_tmpl_id:
                parts.append(rec.product_tmpl_id.display_name)
            if rec.lang_id:
                parts.append(rec.lang_id.code or rec.lang_id.name)
            if rec.level:
                parts.append(rec.level.upper())
            rec.display_name = ' - '.join([p for p in parts if p])
