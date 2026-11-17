from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    xevoria_translation_provider = fields.Selection(
        [
            ('mock', 'Mock / POC'),
            ('google', 'Google Translate'),
            ('deepl', 'DeepL'),
            ('azure', 'Azure Translator'),
            ('libretranslate', 'LibreTranslate'),
        ],
        string='Xevoria Translation Provider',
        default='libretranslate',
        config_parameter='xevoria_translation_poc.provider',
    )
    xevoria_translation_api_key = fields.Char(
        string='Translation API Key',
        config_parameter='xevoria_translation_poc.api_key',
    )
    xevoria_libretranslate_url = fields.Char(
        string='LibreTranslate URL',
        default='http://localhost:5000/translate',
        config_parameter='xevoria_translation_poc.libretranslate_url',
        help='LibreTranslate /translate endpoint. Use http://localhost:5000/translate when Odoo runs on Windows/host, or http://host.docker.internal:5000/translate when Odoo itself runs in Docker.',
    )
    xevoria_translation_source_lang = fields.Char(
        string='Source Language Code',
        default='en_US',
        config_parameter='xevoria_translation_poc.source_lang',
    )
    xevoria_protected_terms = fields.Char(
        string='Protected Technical Words',
        default='Xevoria, SKU, CPU, GPU, RAM, ROM, USB, USB-C, HDMI, SSD, HDD, Wi-Fi, Bluetooth, Intel, AMD, NVIDIA, Apple, Samsung, Dell, HP, Lenovo, ASUS, Acer',
        config_parameter='xevoria_translation_poc.protected_terms',
        help='Comma or newline separated words/phrases that should not be translated, such as brands, SKU labels, ports, model names, and technical terms.',
    )
    xevoria_translation_azure_region = fields.Char(
        string='Azure Region',
        config_parameter='xevoria_translation_poc.azure_region',
    )
    xevoria_translation_azure_endpoint = fields.Char(
        string='Azure Endpoint',
        config_parameter='xevoria_translation_poc.azure_endpoint',
    )
    xevoria_auto_translate_on_create = fields.Boolean(
        string='Auto Translate New Products',
        config_parameter='xevoria_translation_poc.auto_translate_on_create',
        help='When enabled, newly created products are automatically translated for active website languages.',
    )
    xevoria_auto_translate_on_update = fields.Boolean(
        string='Auto Translate Updated Products',
        config_parameter='xevoria_translation_poc.auto_translate_on_update',
        help='When enabled, products are automatically re-translated when name, sales description, or website description changes.',
    )


    xevoria_translation_review_required = fields.Boolean(
        string='Require Translation Review Before Publish',
        default=False,
        config_parameter='xevoria_translation_poc.review_required',
        help='When enabled, generated translations are kept in Pending Review. A user must approve and publish them before they are synced to native Odoo translated fields.',
    )

    xevoria_queue_cron_enabled = fields.Boolean(
        string='Enable Translation Queue Cron',
        default=True,
        config_parameter='xevoria_translation_poc.queue_cron_enabled',
        help='When enabled, Odoo scheduled action processes pending translation queue jobs automatically.',
    )
    xevoria_queue_cron_batch_size = fields.Integer(
        string='Queue Batch Size',
        default=20,
        config_parameter='xevoria_translation_poc.queue_cron_batch_size',
        help='Maximum number of pending translation jobs processed per scheduled cron/manual dashboard run.',
    )

    xevoria_translation_fallback_providers = fields.Char(
        string='Fallback Provider Chain',
        default='libretranslate',
        config_parameter='xevoria_translation_poc.fallback_providers',
        help='Comma-separated provider fallback order. The selected provider is tried first; remaining providers are tried only when the previous provider fails.',
    )
    xevoria_queue_throttle_seconds = fields.Float(
        string='Queue Throttle Seconds',
        default=0.0,
        config_parameter='xevoria_translation_poc.queue_throttle_seconds',
        help='Optional delay between jobs to avoid provider rate-limit errors. Use 0 for no delay.',
    )
    xevoria_retry_backoff_minutes = fields.Integer(
        string='Retry Backoff Minutes',
        default=5,
        config_parameter='xevoria_translation_poc.retry_backoff_minutes',
        help='Base retry delay for failed jobs. Actual delay grows exponentially per attempt.',
    )

    xevoria_translation_memory_enabled = fields.Boolean(
        string='Enable Translation Memory Cache',
        default=True,
        config_parameter='xevoria_translation_poc.translation_memory_enabled',
        help='Reuse previously translated identical source text to avoid duplicate API calls.',
    )
