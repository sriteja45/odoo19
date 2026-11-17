import json
import logging
import re
import time

import requests
from lxml import etree
from lxml import html as lxml_html

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class XevoriaTranslationService(models.AbstractModel):
    _name = 'xevoria.translation.service'
    _description = 'Xevoria Translation API Service'

    def _get_param(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(key, default)

    def _target_code(self, lang_code):
        return (lang_code or '').split('_')[0].lower()

    def _xevoria_rate_limit_sleep(self, seconds):
        """Centralized queue throttling hook. Kept in the service so tests can monkey-patch it."""
        try:
            seconds = float(seconds or 0)
        except (TypeError, ValueError):
            seconds = 0
        if seconds > 0:
            # Cap one sleep so a wrong setting cannot freeze a worker for a long time.
            time.sleep(min(seconds, 60))

    def _xevoria_provider_chain(self):
        """Return configured provider fallback chain with the selected provider first."""
        selected = self._get_param('xevoria_translation_poc.provider', 'libretranslate') or 'libretranslate'
        raw = self._get_param(
            'xevoria_translation_poc.fallback_providers',
            'libretranslate',
        ) or ''
        providers = []
        for provider in [selected] + [item.strip() for item in re.split(r'[,\n]+', raw)]:
            if provider and provider not in providers:
                providers.append(provider)
        return providers

    def _xevoria_provider_chain_display(self):
        return ' → '.join(self._xevoria_provider_chain())

    def _xevoria_api_key_for_provider(self, provider):
        # The current UI has one shared API key field. LibreTranslate local and mock do not need it.
        return self._get_param('xevoria_translation_poc.api_key')


    def _safe_response_json(self, response):
        """Read API JSON as UTF-8 to avoid mojibake in Indian language text.

        Some local LibreTranslate builds do not send a charset header. In that
        case requests may guess incorrectly, which can turn translated Hindi,
        Telugu, etc. into visible garbage such as `à¤...` or `ð...`. JSON is
        UTF-8 by default, so decode the raw bytes explicitly first.
        """
        try:
            return json.loads(response.content.decode('utf-8-sig'))
        except Exception:
            return response.json()

    def _fix_mojibake(self, value):
        """Repair common UTF-8 text that was accidentally decoded as Latin-1."""
        if not isinstance(value, str) or not value:
            return value
        markers = ('Ã', 'Â', 'â€', 'â€™', 'à¤', 'à¥', 'à°', 'à±', 'ð')
        if any(marker in value for marker in markers):
            try:
                repaired = value.encode('latin1').decode('utf-8')
                # Keep repaired text only when it actually removes mojibake markers.
                old_score = sum(value.count(marker) for marker in markers)
                new_score = sum(repaired.count(marker) for marker in markers)
                if new_score < old_score:
                    return repaired
            except Exception:
                pass
        return value


    def _contains_devanagari(self, value):
        return bool(re.search(r'[\u0900-\u097F]', value or ''))

    def _guard_mixed_language_output(self, original, translated, target_lang_code):
        """Reject obviously mixed provider output before it reaches Odoo.

        LibreTranslate/self-hosted models can sometimes return a sentence that
        mixes French/German/English words with Hindi/Devanagari words. Saving
        that bad HTML into Odoo makes every website language look corrupted.
        For non-Indic targets we prefer a safe fallback (the original English
        segment) over saving mixed Hindi text.
        """
        translated = self._fix_mojibake(translated or '')
        target = self._target_code(target_lang_code)
        if target not in ('hi', 'mr', 'ne', 'sa') and self._contains_devanagari(translated):
            _logger.warning(
                'Blocked mixed-language translation output for target=%s. original=%r translated=%r',
                target_lang_code, original, translated,
            )
            return original
        return translated


    def _get_protected_terms(self):
        """Return configured words/phrases that must not be translated.

        Keep this list configurable because every store has different brand names,
        SKU patterns, and technical words. Values are comma or newline separated.
        """
        default_terms = 'Xevoria, SKU, CPU, GPU, RAM, ROM, USB, USB-C, HDMI, SSD, HDD, Wi-Fi, Bluetooth, Intel, AMD, NVIDIA, Apple, Samsung, Dell, HP, Lenovo, ASUS, Acer'
        raw_terms = self._get_param('xevoria_translation_poc.protected_terms', default_terms) or ''
        terms = []
        for item in re.split(r'[,\n]+', raw_terms):
            term = item.strip()
            if term:
                terms.append(term)
        return sorted(set(terms), key=len, reverse=True)

    def _protect_text(self, text):
        """Replace protected terms in plain text with stable placeholders.

        Only ever called on plain text (no HTML tags). Brace-delimited tokens
        such as ``{{XEV0}}`` survive machine-translation round trips far more
        reliably than bare symbol/number tokens, because they resemble the
        variable-placeholder conventions (gettext/ICU style) that translation
        engines are trained to leave untouched.

        Protected terms and the technical/SKU pattern are matched in a single
        combined pass over the original text. Running them as two sequential
        passes (protected terms first, then the technical pattern) let the
        technical pattern's own regex re-match the placeholder tokens just
        inserted by the first pass (e.g. matching "XEV0" inside an already
        inserted ``{{XEV0}}`` token), corrupting it into a doubled token like
        ``{{{{XEV2}}}}``. Matching everything against the original text in one
        pass avoids that self-collision entirely.
        """
        if not text:
            return text, {}
        placeholders = {}

        def add_placeholder(value):
            key = '{{XEV%d}}' % len(placeholders)
            placeholders[key] = value
            return key

        term_patterns = [re.escape(term) for term in self._get_protected_terms()]
        # Common dynamic/technical patterns: SKU-like codes, dimensions, model numbers, and ports.
        technical_pattern = r'[A-Z]{2,}[A-Z0-9-]{1,}|\d+(?:GB|TB|MB|W|Hz|GHz|MHz|MP|mAh|inch|mm|cm)|USB-C|USB|HDMI|Wi-Fi'
        combined_pattern = r'(?<![\w-])(?:%s)(?![\w-])' % '|'.join(term_patterns + [technical_pattern])
        protected = re.sub(combined_pattern, lambda match: add_placeholder(match.group(0)), text)
        return protected, placeholders

    def _restore_protected_text(self, text, placeholders):
        """Restore placeholders after translation."""
        restored = text or ''
        for key, value in placeholders.items():
            restored = restored.replace(key, value)
        return restored

    def _extract_html_text_segments(self, html_value):
        """Parse HTML and return (tree, segments) where segments is an ordered
        list of (element, attr) pairs pointing at every non-empty text/tail
        node, in document order.

        Tags themselves are never touched or exposed outside this method:
        only the human-readable text inside/between them is ever sent to a
        translation provider. This avoids the previous approach of turning
        every tag into a bare numbered placeholder mixed directly into the
        text, which translation engines could reorder, duplicate, or drop.
        """
        tree = lxml_html.fragment_fromstring(html_value, create_parent='div')
        segments = []

        def walk(element):
            if element.text and element.text.strip():
                segments.append((element, 'text'))
            for child in element:
                walk(child)
                if child.tail and child.tail.strip():
                    segments.append((child, 'tail'))

        walk(tree)
        return tree, segments

    def _render_html_tree(self, tree):
        """Render a parsed fragment tree (created with create_parent='div')
        back to an HTML string, without the synthetic wrapper div.

        Any text appearing before the first child tag is stored by lxml as
        the wrapper's own ``.text`` rather than on a child element. That must
        be included explicitly, or content that is pure text with no leading
        tag (e.g. a plain sentence with no markup at all) is silently dropped
        from the output.
        """
        parts = [tree.text or '']
        parts.extend(
            etree.tostring(child, encoding='utf-8').decode('utf-8') for child in tree
        )
        return ''.join(parts)

    def _translate_html(self, html_value, translate_segment):
        """Translate an HTML fragment by translating only its text content.

        Each text/tail segment is translated independently (not joined into
        one combined payload). Machine-translation engines are typically
        sentence-based and are not guaranteed to preserve line breaks or a
        custom delimiter across a single combined request, which is what
        previously let segments merge, reorder, or vanish and produced
        corrupted, language-mixed website descriptions. Translating each
        segment on its own is slightly more expensive (one API call per
        paragraph/bullet) but guarantees every piece of text ends up back in
        its original tag, in the original order, with nothing lost.

        ``translate_segment`` is a callable that takes one plain-text string
        (already term-protected) and returns its translation.
        """
        if not html_value:
            return html_value
        tree, segments = self._extract_html_text_segments(html_value)
        if not segments:
            return html_value

        for element, attr in segments:
            original = getattr(element, attr)
            # translate_segment already routes through _translate_plain_text(),
            # which protects/restores brand names, SKUs, ports, and technical
            # terms. Protecting here as well would re-process placeholders like
            # {{XEV0}} and could corrupt them into nested placeholders in HTML
            # descriptions. Keep HTML parsing separate from term protection.
            translated = translate_segment(original)
            setattr(element, attr, translated)

        return self._render_html_tree(tree)



    def translate_text(self, text, target_lang_code, source_lang_code=None, html=False, queue_job=None):
        """Translate text using the configured provider.

        Provider `libretranslate` can be used with a self-hosted local server without API keys.
        Provider `mock` remains available for offline POC/demo testing.

        When ``html=True``, only the human-readable text inside the HTML is
        ever sent to the translation provider; tags are parsed out, the text
        segments are translated, and the original tags are reattached
        afterwards. This avoids exposing raw markup to providers, which could
        previously reorder, duplicate, or drop tag placeholders and corrupt
        the resulting website description (see Step 24 fix).
        """
        if not text:
            return False

        source_lang_code = source_lang_code or self._get_param(
            'xevoria_translation_poc.source_lang', 'en_US'
        )
        source_provider_code = self._target_code(source_lang_code)
        target_provider_code = self._target_code(target_lang_code)
        if target_provider_code and target_provider_code == source_provider_code:
            return text

        provider = self._get_param('xevoria_translation_poc.provider', 'libretranslate')
        cache_provider = self._xevoria_provider_chain_display()
        cache_enabled = self._get_param('xevoria_translation_poc.translation_memory_enabled', 'True') == 'True'
        memory = self.env['xevoria.translation.memory'].sudo()

        if cache_enabled:
            cached = memory.get_cached_translation(
                text,
                target_lang_code,
                source_lang=source_lang_code,
                provider=cache_provider,
                is_html=html,
            )
            if cached:
                return cached

        if html:
            translated = self._translate_html(
                text,
                lambda plain_text: self._translate_plain_text(plain_text, target_lang_code, source_lang_code, queue_job=queue_job),
            )
        else:
            translated = self._translate_plain_text(text, target_lang_code, source_lang_code, queue_job=queue_job)

        if cache_enabled and translated:
            memory.set_cached_translation(
                text,
                translated,
                target_lang_code,
                source_lang=source_lang_code,
                provider=cache_provider,
                is_html=html,
            )
        return translated

    def _translate_plain_text(self, text, target_lang_code, source_lang_code, queue_job=None):
        """Translate a plain-text string using provider failover.

        The selected provider is tried first. If it fails, configured fallback
        providers are tried in order. This keeps the queue moving when a local
        LibreTranslate server is down, a remote provider is rate-limited, or a
        language pair is temporarily unsupported.
        """
        if not text:
            return text

        protected_text, placeholders = self._protect_text(text)
        errors = []
        for provider in self._xevoria_provider_chain():
            try:
                translated = self._translate_plain_text_with_provider(
                    protected_text,
                    source_lang_code,
                    target_lang_code,
                    provider,
                )
                guarded = self._guard_mixed_language_output(protected_text, translated, target_lang_code)
                if queue_job:
                    queue_job.sudo().write({'provider_used': provider})
                    if errors:
                        queue_job._log_queue_event(
                            'failover',
                            _('Provider %(provider)s succeeded after previous provider failure(s).') % {'provider': provider},
                            'warning',
                        )
                return self._restore_protected_text(guarded, placeholders)
            except Exception as exc:
                errors.append('%s: %s' % (provider, exc))
                _logger.warning('Translation provider %s failed, trying next provider if available: %s', provider, exc)
                if queue_job:
                    queue_job._log_queue_event(
                        'failover',
                        _('Provider %(provider)s failed: %(error)s') % {'provider': provider, 'error': exc},
                        'warning',
                        exception=exc,
                    )
        raise UserError(_('All translation providers failed: %s') % ' | '.join(errors))

    def _translate_plain_text_with_provider(self, text, source_lang_code, target_lang_code, provider):
        provider = provider or 'libretranslate'
        if provider == 'mock':
            return '[%s] %s' % (target_lang_code or 'translated', text)

        api_key = self._xevoria_api_key_for_provider(provider)
        if provider == 'libretranslate':
            return self._translate_libretranslate(text, source_lang_code, target_lang_code, api_key)

        if not api_key:
            raise UserError(_('%s API key is missing.') % provider)

        if provider == 'google':
            return self._translate_google(text, source_lang_code, target_lang_code, api_key)
        if provider == 'deepl':
            return self._translate_deepl(text, source_lang_code, target_lang_code, api_key)
        if provider == 'azure':
            return self._translate_azure(text, source_lang_code, target_lang_code, api_key)

        raise UserError(_('Unsupported translation provider: %s') % provider)


    def _libretranslate_languages_url(self, translate_url):
        """Return the /languages endpoint for a LibreTranslate /translate URL."""
        url = (translate_url or '').strip()
        if url.endswith('/translate'):
            return url[:-len('/translate')] + '/languages'
        return url.rstrip('/') + '/languages'

    def _is_local_libretranslate_url(self, url):
        url = (url or '').lower()
        return (
            'localhost' in url
            or '127.0.0.1' in url
            or 'host.docker.internal' in url
        )

    def _get_libretranslate_supported_languages(self, translate_url):
        """Fetch supported LibreTranslate language pairs.

        Returns a dict like {'en': {'fr', 'de'}}. If the endpoint cannot be
        checked, return an empty dict so the real translate request can still
        report the provider error.
        """
        try:
            response = requests.get(self._libretranslate_languages_url(translate_url), timeout=15)
            if response.status_code != 200:
                _logger.warning(
                    'LibreTranslate /languages check failed with %s: %s',
                    response.status_code,
                    response.text,
                )
                return {}
            languages = response.json()
        except Exception as exc:
            _logger.warning('Unable to read LibreTranslate /languages endpoint: %s', exc)
            return {}

        supported = {}
        for lang in languages or []:
            code = (lang.get('code') or '').lower()
            targets = set((target or '').lower() for target in (lang.get('targets') or []))
            if code:
                supported[code] = targets
        return supported


    def validate_language_pairs(self, target_languages, source_lang_code=None):
        """Validate selected target languages before creating bulk queue jobs.

        This prevents large queues from being created for languages that the
        configured provider cannot translate, such as selecting Telugu while a
        local LibreTranslate server does not expose a `te` model.  Providers
        whose capabilities cannot be cheaply checked are allowed through and
        will still report normal provider errors during processing.
        """
        source_lang_code = source_lang_code or self._get_param('xevoria_translation_poc.source_lang', 'en_US')
        source_code = self._target_code(source_lang_code) or 'auto'
        provider_chain = self._xevoria_provider_chain()
        selected_provider = provider_chain[0] if provider_chain else 'libretranslate'

        # Mock never blocks validation. It is used only for demos/tests.
        if selected_provider == 'mock':
            return True

        # At the moment only LibreTranslate exposes a simple local /languages
        # endpoint we can reliably validate before queue creation.
        if 'libretranslate' not in provider_chain:
            return True

        url = (self._get_param(
            'xevoria_translation_poc.libretranslate_url',
            'http://localhost:5000/translate',
        ) or 'http://localhost:5000/translate').strip()
        supported = self._get_libretranslate_supported_languages(url)
        if not supported:
            # Fail fast only when LibreTranslate is the first/primary provider.
            # If it is just a fallback behind another provider, processing may
            # still succeed through the primary provider.
            if selected_provider == 'libretranslate':
                raise UserError(_(
                    'Unable to validate LibreTranslate languages from %(url)s. '
                    'Start LibreTranslate and verify the /languages endpoint before creating bulk queue jobs.'
                ) % {'url': self._libretranslate_languages_url(url)})
            return True

        if source_code == 'auto':
            return True

        source_targets = supported.get(source_code) or set()
        unsupported = []
        for lang in target_languages:
            target_code = self._target_code(lang.code)
            if not target_code or target_code == source_code:
                continue
            if target_code not in source_targets:
                unsupported.append('%s (%s)' % (lang.name or lang.code, target_code))

        if unsupported:
            available_targets = ', '.join(sorted(source_targets)) or _('none')
            raise UserError(_(
                'The configured LibreTranslate server does not support these selected target languages from %(source)s: %(languages)s. '
                'Available targets for %(source)s: %(available)s. Remove unsupported languages or install/load the required LibreTranslate models.'
            ) % {
                'source': source_code,
                'languages': ', '.join(unsupported),
                'available': available_targets,
            })
        return True

    def _translate_libretranslate(self, text, source_lang_code, target_lang_code, api_key=False):
        url = (self._get_param(
            'xevoria_translation_poc.libretranslate_url',
            'http://localhost:5000/translate',
        ) or 'http://localhost:5000/translate').strip()

        source_code = self._target_code(source_lang_code) or 'auto'
        target_code = self._target_code(target_lang_code)
        if not target_code:
            raise UserError(_('LibreTranslate target language is missing.'))

        supported = self._get_libretranslate_supported_languages(url)
        if supported and source_code != 'auto':
            source_targets = supported.get(source_code) or set()
            if target_code not in source_targets:
                available_targets = ', '.join(sorted(source_targets)) or _('none')
                raise UserError(_(
                    'LibreTranslate does not currently support %s -> %s on this server. '
                    'Install/load the required LibreTranslate model or choose a supported target. '
                    'Available targets for %s: %s'
                ) % (source_code, target_code, source_code, available_targets))

        payload = {
            'q': text,
            'source': source_code,
            'target': target_code,
            'format': 'text',
        }

        # Public/private instances may require api_key. Local Docker normally does
        # not, and sending a stale key can cause BAD REQUEST responses on some
        # LibreTranslate configurations.
        if api_key and not self._is_local_libretranslate_url(url):
            payload['api_key'] = api_key

        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                _logger.error(
                    'LibreTranslate response status=%s body=%s payload=%s',
                    response.status_code,
                    response.text,
                    {key: value for key, value in payload.items() if key != 'api_key'},
                )
            response.raise_for_status()
            data = self._safe_response_json(response)
            translated = self._fix_mojibake(data.get('translatedText') or data.get('translated_text'))
            if not translated:
                raise UserError(_('LibreTranslate response did not contain translated text: %s') % data)
            return translated
        except UserError:
            raise
        except Exception as exc:
            _logger.exception('LibreTranslate translation failed')
            raise UserError(_('LibreTranslate translation failed: %s') % exc)

    def _translate_google(self, text, source_lang_code, target_lang_code, api_key):
        url = 'https://translation.googleapis.com/language/translate/v2'
        payload = {
            'q': text,
            'source': self._target_code(source_lang_code),
            'target': self._target_code(target_lang_code),
            'format': 'text',
            'key': api_key,
        }
        try:
            response = requests.post(url, data=payload, timeout=20)
            response.raise_for_status()
            data = self._safe_response_json(response)
            return self._fix_mojibake(data['data']['translations'][0]['translatedText'])
        except Exception as exc:
            _logger.exception('Google translation failed')
            raise UserError(_('Google translation failed: %s') % exc)

    def _translate_deepl(self, text, source_lang_code, target_lang_code, api_key):
        url = 'https://api-free.deepl.com/v2/translate'
        payload = {
            'text': text,
            'target_lang': self._target_code(target_lang_code).upper(),
        }
        payload = {key: value for key, value in payload.items() if value}
        headers = {'Authorization': 'DeepL-Auth-Key %s' % api_key}
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = self._safe_response_json(response)
            return self._fix_mojibake(data['translations'][0]['text'])
        except Exception as exc:
            _logger.exception('DeepL translation failed')
            raise UserError(_('DeepL translation failed: %s') % exc)

    def _translate_azure(self, text, source_lang_code, target_lang_code, api_key):
        endpoint = self._get_param('xevoria_translation_poc.azure_endpoint') or 'https://api.cognitive.microsofttranslator.com'
        region = self._get_param('xevoria_translation_poc.azure_region')
        if not region:
            raise UserError(_('Azure Translator region is missing in Settings.'))
        url = endpoint.rstrip('/') + '/translate?api-version=3.0&from=%s&to=%s' % (
            self._target_code(source_lang_code),
            self._target_code(target_lang_code),
        )
        headers = {
            'Ocp-Apim-Subscription-Key': api_key,
            'Ocp-Apim-Subscription-Region': region,
            'Content-Type': 'application/json',
        }
        try:
            response = requests.post(url, json=[{'Text': text}], headers=headers, timeout=20)
            response.raise_for_status()
            data = self._safe_response_json(response)
            return self._fix_mojibake(data[0]['translations'][0]['text'])
        except Exception as exc:
            _logger.exception('Azure translation failed')
            raise UserError(_('Azure translation failed: %s') % exc)
