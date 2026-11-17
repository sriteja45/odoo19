from markupsafe import Markup

from odoo import _, api, fields, models


class XevoriaTranslationQueueDashboard(models.TransientModel):
    _name = 'xevoria.translation.queue.dashboard'
    _description = 'Xevoria Translation Queue Dashboard'

    total_jobs = fields.Integer(string='Total Jobs', compute='_compute_stats')
    pending_jobs = fields.Integer(string='Pending', compute='_compute_stats')
    running_jobs = fields.Integer(string='Running', compute='_compute_stats')
    completed_jobs = fields.Integer(string='Completed', compute='_compute_stats')
    failed_jobs = fields.Integer(string='Failed', compute='_compute_stats')
    cancelled_jobs = fields.Integer(string='Cancelled', compute='_compute_stats')
    remaining_jobs = fields.Integer(string='Remaining', compute='_compute_stats')
    progress_percent = fields.Float(string='Progress %', compute='_compute_stats')
    progress_label = fields.Char(string='Progress', compute='_compute_stats')
    dashboard_html = fields.Html(string='Dashboard', compute='_compute_stats', sanitize=False)
    configured_batch_size = fields.Integer(string='Configured Batch Size', compute='_compute_stats')

    @api.depends_context('uid')
    def _compute_stats(self):
        Queue = self.env['xevoria.translation.queue'].sudo()
        configured_batch_size = Queue._xevoria_get_configured_batch_size()
        grouped = Queue.read_group([], ['id:count'], ['state'])
        counts = {row['state']: row['state_count'] for row in grouped}
        total = sum(counts.values())
        pending = counts.get('pending', 0)
        running = counts.get('running', 0)
        done = counts.get('done', 0)
        failed = counts.get('failed', 0)
        cancelled = counts.get('cancelled', 0)
        remaining = pending + running + failed
        progress = (done / total * 100.0) if total else 0.0
        progress_label = _('%(done)s / %(total)s completed (%(progress).1f%%)') % {
            'done': done,
            'total': total,
            'progress': progress,
        }
        progress_width = max(0, min(int(progress), 100))
        html = Markup('''
            <div style="padding: 12px 0;">
                <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;">
                    <div style="min-width:150px; padding:14px; border:1px solid #ddd; border-radius:8px;"><b>Total Jobs</b><br/><span style="font-size:24px;">%(total)s</span></div>
                    <div style="min-width:150px; padding:14px; border:1px solid #ddd; border-radius:8px;"><b>Pending</b><br/><span style="font-size:24px;">%(pending)s</span></div>
                    <div style="min-width:150px; padding:14px; border:1px solid #ddd; border-radius:8px;"><b>Running</b><br/><span style="font-size:24px;">%(running)s</span></div>
                    <div style="min-width:150px; padding:14px; border:1px solid #ddd; border-radius:8px;"><b>Completed</b><br/><span style="font-size:24px;">%(done)s</span></div>
                    <div style="min-width:150px; padding:14px; border:1px solid #ddd; border-radius:8px;"><b>Failed</b><br/><span style="font-size:24px;">%(failed)s</span></div>
                    <div style="min-width:150px; padding:14px; border:1px solid #ddd; border-radius:8px;"><b>Remaining</b><br/><span style="font-size:24px;">%(remaining)s</span></div>
                </div>
                <div style="margin-top:10px;">
                    <b>Progress:</b> %(label)s<br/>
                    <b>Configured Batch Size:</b> %(batch_size)s job(s) per manual/cron run
                    <div style="height:18px; background:#e9ecef; border-radius:10px; overflow:hidden; margin-top:6px; max-width:700px;">
                        <div style="height:18px; width:%(width)s%%; background:#28a745;"></div>
                    </div>
                </div>
            </div>
        ''') % {
            'total': total,
            'pending': pending,
            'running': running,
            'done': done,
            'failed': failed,
            'remaining': remaining,
            'label': progress_label,
            'width': progress_width,
            'batch_size': configured_batch_size,
        }
        for rec in self:
            rec.total_jobs = total
            rec.pending_jobs = pending
            rec.running_jobs = running
            rec.completed_jobs = done
            rec.failed_jobs = failed
            rec.cancelled_jobs = cancelled
            rec.remaining_jobs = remaining
            rec.progress_percent = progress
            rec.progress_label = progress_label
            rec.dashboard_html = html
            rec.configured_batch_size = configured_batch_size

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        return values

    def action_refresh_dashboard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Queue Progress Dashboard'),
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.id,
        }

    def _open_queue(self, domain, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'xevoria.translation.queue',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def action_open_pending_jobs(self):
        return self._open_queue([('state', '=', 'pending')], _('Pending Translation Jobs'))

    def action_open_running_jobs(self):
        return self._open_queue([('state', '=', 'running')], _('Running Translation Jobs'))

    def action_open_completed_jobs(self):
        return self._open_queue([('state', '=', 'done')], _('Completed Translation Jobs'))

    def action_open_failed_jobs(self):
        return self._open_queue([('state', '=', 'failed')], _('Failed Translation Jobs'))

    def action_open_all_jobs(self):
        return self._open_queue([], _('All Translation Jobs'))

    def action_process_pending_jobs(self):
        Queue = self.env['xevoria.translation.queue']
        batch_size = Queue._xevoria_get_configured_batch_size()
        result = Queue.process_queue(limit=batch_size)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Queue'),
                'message': _('Processed next batch of up to %(batch)s jobs: %(processed)s done and %(failed)s failed.') % {
                    'batch': batch_size,
                    'processed': result.get('processed', 0),
                    'failed': result.get('failed', 0),
                },
                'type': 'success' if not result.get('failed') else 'warning',
                'sticky': False,
                'next': self.action_refresh_dashboard(),
            },
        }


    def action_cancel_pending_jobs(self):
        jobs = self.env['xevoria.translation.queue'].search([('state', 'in', ['pending', 'running'])])
        return jobs.action_cancel()
