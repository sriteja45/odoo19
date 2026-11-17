import json
import logging
from datetime import timedelta

import psycopg2
from psycopg2 import errors as pg_errors

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class XevoriaTranslationQueue(models.Model):
    _name = 'xevoria.translation.queue'
    _description = 'Xevoria Product Translation Queue'
    _order = 'priority desc, id asc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name')
    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade', index=True)
    lang_id = fields.Many2one('res.lang', string='Target Language', required=True, domain=[('active', '=', True)], index=True)
    lang_code = fields.Char(related='lang_id.code', store=True, readonly=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, index=True, copy=False)
    priority = fields.Integer(default=10)
    attempts = fields.Integer(default=0, copy=False)
    max_attempts = fields.Integer(default=3)
    last_error = fields.Text(readonly=True, copy=False)
    generated_translation_id = fields.Many2one('xevoria.product.translation.poc', string='Generated Translation', readonly=True, copy=False)
    sync_native_fields = fields.Boolean(string='Sync Native Fields', default=True)
    only_missing_translations = fields.Boolean(
        string='Only Fill Missing Translation Rows',
        default=False,
        help='When enabled, a queued job skips provider calls if all translated values already exist.',
    )
    source_lang = fields.Char(string='Source Language', default='en_US')
    source_hash = fields.Char(string='Source Hash', readonly=True, copy=False, index=True)
    cache_hit = fields.Boolean(string='Cache Hit / Skipped Duplicate', readonly=True, copy=False)
    skipped_reason = fields.Char(string='Skipped Reason', readonly=True, copy=False)
    created_from = fields.Selection([
        ('manual', 'Manual'),
        ('bulk', 'Bulk Wizard'),
        ('create', 'Product Create'),
        ('update', 'Product Update'),
    ], default='manual', required=True)
    started_at = fields.Datetime(readonly=True, copy=False)
    completed_at = fields.Datetime(readonly=True, copy=False)
    next_retry_at = fields.Datetime(string='Next Retry At', readonly=True, copy=False, index=True)
    provider_used = fields.Char(string='Provider Used', readonly=True, copy=False)
    log_ids = fields.One2many('xevoria.translation.log', 'queue_id', string='Logs', readonly=True)

    def _log_queue_event(self, action, message, level='info', exception=None):
        provider = self.env['ir.config_parameter'].sudo().get_param('xevoria_translation_poc.provider', 'mock')
        for job in self:
            self.env['xevoria.translation.log'].sudo().create({
                'queue_id': job.id,
                'product_tmpl_id': job.product_tmpl_id.id,
                'lang_id': job.lang_id.id,
                'level': level,
                'action': action,
                'message': message,
                'attempts': job.attempts,
                'provider': provider,
                'exception_type': exception.__class__.__name__ if exception else False,
            })

    @api.depends('product_tmpl_id', 'lang_id', 'state')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s → %s [%s]' % (
                rec.product_tmpl_id.display_name or _('Product'),
                rec.lang_id.name or rec.lang_code or _('Language'),
                dict(rec._fields['state'].selection).get(rec.state, rec.state),
            )

    def _xevoria_queue_source_payload(self, product, source_lang='en_US'):
        """Return a stable text payload representing all source content this job translates.

        This powers change detection. If this hash is unchanged, the queue can skip
        duplicate jobs/API calls while still preserving all existing translations.
        """
        product = product.with_context(lang=source_lang or 'en_US')
        website_field = product._xevoria_website_description_field_name()
        payload = {
            'name': product.name or '',
            'description_sale': product.description_sale or '',
            'website_description': product[website_field] if website_field else '',
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _xevoria_compute_queue_source_hash(self, product, source_lang='en_US'):
        payload = self._xevoria_queue_source_payload(product, source_lang=source_lang)
        return self.env['xevoria.translation.memory'].sudo().compute_source_hash(payload, is_html=False)

    @api.model
    def enqueue_products(self, products, languages=None, sync_native_fields=True, only_missing_translations=False, created_from='manual'):
        return self.enqueue_products_with_summary(
            products,
            languages=languages,
            sync_native_fields=sync_native_fields,
            only_missing_translations=only_missing_translations,
            created_from=created_from,
        )['jobs']

    @api.model
    def enqueue_products_with_summary(self, products, languages=None, sync_native_fields=True, only_missing_translations=False, created_from='manual'):
        """Create queue jobs with strict duplicate prevention and counters.

        A duplicate means the same product/language is already pending/running,
        or the same unchanged source hash was already completed.  Returning the
        counters lets the bulk wizard explain why a run created 0 jobs instead
        of silently doing nothing.
        """
        languages = languages or self.env['product.template']._xevoria_get_active_website_languages()
        source_lang = self.env['ir.config_parameter'].sudo().get_param('xevoria_translation_poc.source_lang', 'en_US')
        created = self.env[self._name]
        service = self.env['xevoria.translation.service']
        source_provider_code = service._target_code(source_lang)
        skipped_source = 0
        skipped_existing = 0
        skipped_done = 0

        for product in products:
            current_hash = self._xevoria_compute_queue_source_hash(product, source_lang=source_lang)
            for lang in languages:
                if service._target_code(lang.code) == source_provider_code:
                    skipped_source += 1
                    continue
                existing = self.search([
                    ('product_tmpl_id', '=', product.id),
                    ('lang_id', '=', lang.id),
                    ('state', 'in', ['pending', 'running']),
                ], limit=1)
                if existing:
                    skipped_existing += 1
                    continue
                previous_done = self.search([
                    ('product_tmpl_id', '=', product.id),
                    ('lang_id', '=', lang.id),
                    ('state', '=', 'done'),
                    ('source_hash', '=', current_hash),
                ], limit=1)
                if previous_done:
                    skipped_done += 1
                    continue
                job = self.create({
                    'product_tmpl_id': product.id,
                    'lang_id': lang.id,
                    'source_lang': source_lang,
                    'source_hash': current_hash,
                    'sync_native_fields': sync_native_fields,
                    'only_missing_translations': only_missing_translations,
                    'created_from': created_from,
                })
                job._log_queue_event('enqueue', _('Translation job created.'), 'info')
                created |= job
        return {
            'jobs': created,
            'created': len(created),
            'skipped_source': skipped_source,
            'skipped_existing': skipped_existing,
            'skipped_done': skipped_done,
            'skipped_total': skipped_source + skipped_existing + skipped_done,
        }


    @api.model
    def _xevoria_get_configured_batch_size(self):
        """Return the configured queue batch size with safe bounds.

        Step 44 centralizes batch-size handling so cron, manual buttons, and
        dashboard actions all process the same configured number of jobs.
        """
        params = self.env['ir.config_parameter'].sudo()
        try:
            batch_size = int(params.get_param('xevoria_translation_poc.queue_cron_batch_size', '20') or 20)
        except (TypeError, ValueError):
            batch_size = 20
        return max(1, min(batch_size, 200))

    @api.model
    def cron_process_pending_queue(self):
        """Process pending translation jobs from scheduled action."""
        params = self.env['ir.config_parameter'].sudo()
        cron_enabled = params.get_param('xevoria_translation_poc.queue_cron_enabled', 'True') == 'True'
        if not cron_enabled:
            _logger.info('Xevoria translation queue cron is disabled by settings.')
            return {'processed': 0, 'failed': 0, 'skipped': True}
        batch_size = self._xevoria_get_configured_batch_size()
        result = self.process_queue(limit=batch_size)
        _logger.info('Xevoria translation queue cron completed: %s', result)
        self.env['xevoria.translation.log'].sudo().create({
            'level': 'info',
            'action': 'cron',
            'message': _('Cron processed %(processed)s jobs and failed %(failed)s jobs.') % result,
        })
        return result

    def action_process_queue(self):
        """Process selected queue jobs and return a valid client action.

        Odoo object buttons should return False/True or a valid action dict.
        Returning the raw result dictionary can break the web client, so this
        wraps the processing result in a display notification.
        """
        jobs = self.filtered(lambda job: job.state in ('pending', 'failed'))
        result = self._process_jobs(jobs) if jobs else self.process_queue(limit=self._xevoria_get_configured_batch_size())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Queue'),
                'message': _('Processed %(processed)s jobs and failed %(failed)s jobs.') % result,
                'type': 'success' if not result.get('failed') else 'warning',
                'sticky': False,
            },
        }

    def action_process_next_configured_batch(self):
        """Process the next pending batch using the configured batch size."""
        batch_size = self._xevoria_get_configured_batch_size()
        result = self.process_queue(limit=batch_size)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Queue'),
                'message': _('Processed next batch of up to %(batch)s jobs: %(processed)s done, %(failed)s failed, %(skipped)s skipped.') % {
                    'batch': batch_size,
                    'processed': result.get('processed', 0),
                    'failed': result.get('failed', 0),
                    'skipped': result.get('skipped', 0),
                },
                'type': 'success' if not result.get('failed') else 'warning',
                'sticky': False,
            },
        }

    @api.model
    def process_queue(self, limit=50):
        """Fetch pending jobs with row-level locks so parallel cron/manual runs
        cannot process the same product/language rows at the same time.

        The previous ORM search could let two workers pick the same pending jobs
        when max_cron_threads/manual Run Manually overlapped.  That made native
        product writes collide and PostgreSQL raised SerializationFailure.
        """
        now = fields.Datetime.now()
        limit = max(1, int(limit or 50))
        self.env.cr.execute(
            f"""
            SELECT id
              FROM {self._table}
             WHERE state = 'pending'
               AND (next_retry_at IS NULL OR next_retry_at <= %s)
             ORDER BY priority DESC, id ASC
             LIMIT %s
             FOR UPDATE SKIP LOCKED
            """,
            [now, limit],
        )
        job_ids = [row[0] for row in self.env.cr.fetchall()]
        return self._process_jobs(self.browse(job_ids))

    def _xevoria_format_queue_error(self, exc, retryable=False):
        """Return a user-friendly queue error with an actionable hint.

        Raw provider/DB exceptions are useful for logs, but queue users need to
        know what to do next: start LibreTranslate, choose a supported language,
        or wait for the automatic retry.
        """
        raw = str(exc or '').strip()
        lowered = raw.lower()
        if retryable:
            return _(
                'Temporary database concurrency issue while saving product translations. '
                'The job was kept retryable and will run again automatically. Technical details: %s'
            ) % raw
        if 'does not currently support' in lowered or 'unsupported language' in lowered:
            return _(
                'Selected target language is not supported by the configured translation provider. '
                'Check LibreTranslate /languages or remove that language from the bulk run. Technical details: %s'
            ) % raw
        if 'connection refused' in lowered or 'failed to establish a new connection' in lowered:
            return _(
                'Translation provider is not reachable. Start LibreTranslate or verify the provider URL in settings. '
                'Technical details: %s'
            ) % raw
        if 'read timed out' in lowered or 'timeout' in lowered:
            return _(
                'Translation provider timed out. The job can be retried after the provider is healthy. '
                'Technical details: %s'
            ) % raw
        if 'api key is missing' in lowered:
            return _(
                'Translation provider API key is missing. Add the API key in settings or switch provider. '
                'Technical details: %s'
            ) % raw
        if 'all translation providers failed' in lowered:
            return _(
                'All configured translation providers failed. Check provider URL/API key and supported language pairs. '
                'Technical details: %s'
            ) % raw
        return raw or _('Unknown translation queue error.')

    def _xevoria_mark_job_failure(self, job, exc, old_attempts=0, retryable=False):
        """Persist failure/retry state after a per-job savepoint rollback.

        This method intentionally avoids reading computed display_name after a DB
        exception.  Reading related product fields after a failed SQL statement can
        trigger InFailedSqlTransaction and crash the whole cron.
        """
        job.invalidate_recordset()
        attempts = int(old_attempts or 0) + 1
        max_attempts = int(job.max_attempts or 3)
        backoff_minutes = job._xevoria_next_retry_minutes(attempts)
        next_retry_at = fields.Datetime.now() + timedelta(minutes=backoff_minutes) if attempts < max_attempts else False
        error_message = self._xevoria_format_queue_error(exc, retryable=retryable)
        values = {
            'attempts': attempts,
            'last_error': error_message,
            'state': 'failed' if attempts >= max_attempts else 'pending',
            'next_retry_at': next_retry_at,
            'started_at': False,
        }
        job.sudo().write(values)
        job._log_queue_event('failed', error_message, 'error', exception=exc)
        if next_retry_at:
            job._log_queue_event(
                'backoff',
                _('Job will retry after %(minutes)s minutes.') % {'minutes': backoff_minutes},
                'warning',
            )
        return values

    def _process_jobs(self, jobs):
        processed = 0
        failed = 0
        skipped = 0
        params = self.env['ir.config_parameter'].sudo()
        try:
            throttle_seconds = float(params.get_param('xevoria_translation_poc.queue_throttle_seconds', '0') or 0)
        except ValueError:
            throttle_seconds = 0

        retryable_db_errors = (
            pg_errors.SerializationFailure,
            pg_errors.DeadlockDetected,
            psycopg2.OperationalError,
        )

        for job in jobs:
            old_attempts = int(job.attempts or 0)
            if old_attempts >= int(job.max_attempts or 3):
                job.write({'state': 'failed', 'last_error': _('Maximum attempts reached.')})
                failed += 1
                continue
            try:
                before_state = job.state
                # Isolate every job. If one product write fails because another
                # transaction touched the same product, the savepoint rolls back
                # only this job instead of aborting the entire cron transaction.
                with self.env.cr.savepoint():
                    job._process_one_job()
                if job.state in ('done', 'cancelled'):
                    processed += 1
                elif before_state == job.state:
                    skipped += 1
            except retryable_db_errors as exc:
                failed += 1
                _logger.warning(
                    'Retryable database concurrency error while processing queue job id=%s: %s',
                    job.id, exc,
                )
                self._xevoria_mark_job_failure(job, exc, old_attempts=old_attempts, retryable=True)
            except Exception as exc:
                failed += 1
                _logger.exception('Xevoria translation queue job failed: id=%s', job.id)
                self._xevoria_mark_job_failure(job, exc, old_attempts=old_attempts, retryable=False)
            if throttle_seconds > 0:
                self.env['xevoria.translation.service']._xevoria_rate_limit_sleep(throttle_seconds)
        return {'processed': processed, 'failed': failed, 'skipped': skipped}

    def _xevoria_next_retry_minutes(self, attempts):
        params = self.env['ir.config_parameter'].sudo()
        try:
            base_delay = int(params.get_param('xevoria_translation_poc.retry_backoff_minutes', '5') or 5)
        except ValueError:
            base_delay = 5
        base_delay = max(1, min(base_delay, 240))
        # Exponential backoff: 5, 10, 20... minutes by default.
        multiplier = 2 ** max(0, attempts - 1)
        return min(base_delay * multiplier, 24 * 60)

    def _process_one_job(self):
        self.ensure_one()
        if self.state not in ('pending', 'failed'):
            return True
        self.write({'state': 'running', 'started_at': fields.Datetime.now(), 'attempts': self.attempts + 1, 'last_error': False, 'next_retry_at': False})
        self._log_queue_event('start', _('Translation job started.'), 'info')
        service = self.env['xevoria.translation.service']
        Translation = self.env['xevoria.product.translation.poc'].sudo()
        product = self.product_tmpl_id
        source_product = product.with_context(lang=self.source_lang or 'en_US')
        source_name = source_product.name or product.name or _('New Product')
        source_description = source_product.description_sale or product.description_sale
        source_website_description = product._xevoria_get_website_description_value(self.source_lang) or product._xevoria_get_website_description_value()
        current_hash = self._xevoria_compute_queue_source_hash(product, source_lang=self.source_lang or 'en_US')
        if not self.source_hash or self.source_hash != current_hash:
            self.write({'source_hash': current_hash})
        duplicate_done = self.search([
            ('id', '!=', self.id),
            ('product_tmpl_id', '=', product.id),
            ('lang_id', '=', self.lang_id.id),
            ('state', '=', 'done'),
            ('source_hash', '=', current_hash),
        ], limit=1)
        if duplicate_done:
            self.write({
                'state': 'done',
                'cache_hit': True,
                'skipped_reason': _('Skipped because the source text hash was already translated.'),
                'generated_translation_id': duplicate_done.generated_translation_id.id if duplicate_done.generated_translation_id else False,
                'completed_at': fields.Datetime.now(),
            })
            self._log_queue_event('skip', _('Skipped unchanged source text; previous done translation reused.'), 'info')
            return True

        translation = Translation.search([
            ('product_tmpl_id', '=', product.id),
            ('lang_id', '=', self.lang_id.id),
        ], limit=1)
        if not translation:
            translation = Translation.create({
                'product_tmpl_id': product.id,
                'lang_id': self.lang_id.id,
                'translated_name': source_name,
                'translated_description_sale': source_description or False,
                'translated_website_description': source_website_description or False,
            })

        has_existing_values = bool(
            translation.translated_name
            and (translation.translated_description_sale or not source_description)
            and (translation.translated_website_description or not source_website_description)
        )
        if self.only_missing_translations and has_existing_values:
            self.write({
                'state': 'done',
                'cache_hit': True,
                'skipped_reason': _('Skipped because translated values already exist.'),
                'generated_translation_id': translation.id,
                'completed_at': fields.Datetime.now(),
            })
            self._log_queue_event('skip', _('Skipped existing translation values.'), 'info')
            return True

        target_lang = self.lang_code or self.lang_id.code
        if service._target_code(target_lang) == service._target_code(self.source_lang):
            self.write({
                'state': 'cancelled',
                'last_error': _('Skipped source language; native source fields are not overwritten.'),
                'completed_at': fields.Datetime.now(),
            })
            self._log_queue_event('skip', _('Skipped source language job.'), 'info')
            return True
        values_to_write = {
            'translated_name': service.translate_text(source_name, target_lang, self.source_lang, queue_job=self),
            'translated_description_sale': service.translate_text(source_description, target_lang, self.source_lang, queue_job=self),
            'translated_website_description': service.translate_text(source_website_description, target_lang, self.source_lang, html=True, queue_job=self),
        }
        translation.write({key: value for key, value in values_to_write.items() if value})

        review_required = self.env['ir.config_parameter'].sudo().get_param(
            'xevoria_translation_poc.review_required', 'False'
        ) == 'True'
        if review_required:
            translation.action_mark_pending_review()
            success_message = _('Translation generated and moved to Pending Review. Native fields were not published yet.')
        elif self.sync_native_fields:
            translation.write({'review_state': 'generated', 'generated_at': fields.Datetime.now()})
            translation.action_apply_translation()
            product._xevoria_translate_catalog_records(
                languages=self.lang_id,
                source_lang=self.source_lang or 'en_US',
            )
            product._xevoria_translate_seo_records(
                languages=self.lang_id,
                source_lang=self.source_lang or 'en_US',
            )
            success_message = _('Translation generated and native fields synced.')
        else:
            translation.write({'review_state': 'generated', 'generated_at': fields.Datetime.now()})
            success_message = _('Translation generated. Native field sync was disabled for this job.')

        self.write({
            'state': 'done',
            'generated_translation_id': translation.id,
            'completed_at': fields.Datetime.now(),
            # Keep the actual provider recorded by translation_service. If the
            # job translated only from cache or no segment wrote provider_used,
            # fall back to the configured chain for diagnostics.
            'provider_used': self.provider_used or service._xevoria_provider_chain_display(),
        })
        self._log_queue_event('success', success_message, 'info')
        return True

    def action_retry(self):
        # Reset attempts so a manually retried job is not immediately blocked
        # after reaching max_attempts. This keeps the Retry button useful after
        # fixing provider settings or starting LibreTranslate.
        jobs = self.filtered(lambda job: job.state == 'failed')
        jobs.write({
            'state': 'pending',
            'last_error': False,
            'attempts': 0,
            'next_retry_at': False,
            'started_at': False,
        })
        jobs._log_queue_event('retry', _('Failed job moved back to pending.'), 'warning')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Queue'),
                'message': _('%(count)s failed job(s) were reset and moved back to pending.') % {'count': len(jobs)},
                'type': 'success',
                'sticky': False,
            },
        }

    def action_retry_all_failed(self):
        """Retry every failed queue job after fixing provider/settings issues."""
        jobs = self.search([('state', '=', 'failed')])
        return jobs.action_retry()

    def action_cancel(self):
        cancellable = self.filtered(lambda job: job.state in ('pending', 'running', 'failed'))
        ignored = len(self) - len(cancellable)
        cancellable.write({
            'state': 'cancelled',
            'started_at': False,
            'next_retry_at': False,
            'last_error': False,
            'completed_at': fields.Datetime.now(),
        })
        if cancellable:
            cancellable._log_queue_event('cancel', _('Translation job cancelled by user.'), 'warning')
        message = _('%(cancelled)s job(s) cancelled.') % {'cancelled': len(cancellable)}
        if ignored:
            message += _(' %(ignored)s already completed/cancelled job(s) were skipped.') % {'ignored': ignored}
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Translation Queue'),
                'message': message,
                'type': 'warning' if cancellable else 'info',
                'sticky': False,
            },
        }

    def action_cancel_all_pending(self):
        jobs = self.search([('state', 'in', ['pending', 'running'])])
        return jobs.action_cancel()
