# -*- coding: utf-8 -*-

"""Translation helper service for Xevoria marketplace translations.

Step 3 only adds the reusable service. Later steps can call this service from
product creation, cron jobs, website APIs, and search controllers.
"""

import importlib
import logging
import re

from odoo import api, models

_logger = logging.getLogger(__name__)


class XevoriaTranslationService(models.AbstractModel):
    _name = "xevoria.translation.service"
    _description = "Xevoria Translation Service"

    # Basic protected patterns for electronics/catalog text.
    # These are kept unchanged during machine translation.
    _PROTECTED_PATTERNS = [
        r"\b[A-Z0-9][A-Z0-9\-_/]{2,}\b",      # SKUs/model codes like M35, RTX-4060, HA240Y
        r"\b\d+(?:\.\d+)?\s?(?:GB|TB|MB|KB|RAM|ROM|Hz|kHz|MHz|GHz|W|V|A|mAh|inch|Inch|INCH|cm|mm|kg|g|MP|K|UHD|FHD|HD|SSD|HDD)\b",
        r"\b(?:5G|4G|3G|WiFi|Bluetooth|USB|HDMI|SSD|HDD|LED|LCD|OLED|AMOLED|IPS|DDR\d?|RTX|GTX|Core i\d|Ryzen \d)\b",
    ]

    _COMMON_BRANDS = [
        "Samsung", "Apple", "Dell", "HP", "Lenovo", "Acer", "Asus", "Sony", "LG",
        "MI", "Xiaomi", "Redmi", "Realme", "Vivo", "Oppo", "OnePlus", "Motorola",
        "Intel", "AMD", "Nvidia", "Logitech", "Canon", "Epson", "Boat", "JBL",
    ]

    @api.model
    def normalize_lang(self, lang):
        """Convert Odoo language codes to API-friendly target codes."""
        if not lang:
            return "en"
        return lang.split("_")[0].lower()

    @api.model
    def protect_catalog_terms(self, text):
        """Replace brand/model/spec tokens with placeholders before translation."""
        if not text:
            return "", {}

        protected = {}
        result = text

        def add_placeholder(value):
            key = "__XEVORIA_PROTECTED_%03d__" % len(protected)
            protected[key] = value
            return key

        # Protect known brand names first.
        for brand in sorted(self._COMMON_BRANDS, key=len, reverse=True):
            pattern = r"\b%s\b" % re.escape(brand)
            result = re.sub(pattern, lambda match: add_placeholder(match.group(0)), result)

        # Protect specs, SKUs, and model-like tokens.
        for pattern in self._PROTECTED_PATTERNS:
            result = re.sub(pattern, lambda match: add_placeholder(match.group(0)), result)

        return result, protected

    @api.model
    def restore_catalog_terms(self, text, protected):
        """Restore placeholders after translation."""
        result = text or ""
        for key, value in protected.items():
            result = result.replace(key, value)
            # Some translation engines alter underscores/spaces; try a soft fallback.
            result = result.replace(key.lower(), value)
        return result

    @api.model
    def translate_text(self, text, target_lang, source_lang="en"):
        """Translate text with safe fallback.

        Provider priority:
        1. xevoria.translation.provider system parameter
           - googletrans
           - libretranslate
           - dictionary
           - disabled
        2. If provider is missing/disabled, use a small safe catalog dictionary.

        This keeps Odoo stable even before you configure a real API.
        """
        if not text:
            return ""

        target = self.normalize_lang(target_lang)
        source = self.normalize_lang(source_lang)
        if target == source:
            return text

        protected_text, protected = self.protect_catalog_terms(text)

        provider = self.env["ir.config_parameter"].sudo().get_param(
            "xevoria.translation.provider", "disabled"
        )

        translated = protected_text
        try:
            if provider == "googletrans":
                translated = self._translate_with_googletrans(protected_text, target, source)
            elif provider == "libretranslate":
                translated = self._translate_with_libretranslate(protected_text, target, source)
            elif provider in ("dictionary", "disabled", ""):
                translated = self._translate_with_local_dictionary(protected_text, target)
            else:
                _logger.info("Unknown Xevoria translation provider %s; using local dictionary.", provider)
                translated = self._translate_with_local_dictionary(protected_text, target)
        except Exception as error:
            _logger.warning("Xevoria translation failed, returning original text: %s", error)
            translated = protected_text

        return self.restore_catalog_terms(translated, protected)

    @api.model
    def _translate_with_googletrans(self, text, target, source="en"):
        """Use googletrans if installed. Good for testing, not ideal for production."""
        try:
            googletrans = importlib.import_module("googletrans")
            Translator = getattr(googletrans, "Translator")
        except Exception as error:
            raise RuntimeError("googletrans is not installed. Run: pip install googletrans==4.0.0rc1") from error

        translator = Translator()
        return translator.translate(text, src=source, dest=target).text

    @api.model
    def _translate_with_libretranslate(self, text, target, source="en"):
        """Use a LibreTranslate server configured in Odoo system parameters."""
        try:
            import requests
        except Exception as error:
            raise RuntimeError("Python requests package is required for LibreTranslate.") from error

        params = self.env["ir.config_parameter"].sudo()
        base_url = params.get_param("xevoria.libretranslate.url", "").rstrip("/")
        api_key = params.get_param("xevoria.libretranslate.api_key", "")

        if not base_url:
            raise RuntimeError("Set xevoria.libretranslate.url in System Parameters.")

        payload = {
            "q": text,
            "source": source,
            "target": target,
            "format": "html" if "<" in text and ">" in text else "text",
        }
        if api_key:
            payload["api_key"] = api_key

        response = requests.post("%s/translate" % base_url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        return data.get("translatedText") or text


    @api.model
    def _translate_with_local_dictionary(self, text, target):
        """Very small offline catalog dictionary.

        This is not a replacement for Google/LibreTranslate, but it makes the
        native Odoo /shop page visibly localize common electronics/catalog words
        even when no external translation provider is configured yet.
        """
        if not text:
            return ""

        dictionaries = {
            "hi": {
                "module": "मॉड्यूल",
                "transceiver": "ट्रांसीवर",
                "receiver": "रिसीवर",
                "transmitter": "ट्रांसमीटर",
                "power": "पावर",
                "channel": "चैनल",
                "physical layer": "फिजिकल लेयर",
                "layer": "लेयर",
                "mosfet": "MOSFET",
                "mos": "MOS",
                "dual": "डुअल",
                "single": "सिंगल",
                "converter": "कन्वर्टर",
                "controller": "कंट्रोलर",
                "sensor": "सेंसर",
                "monitor": "मॉनिटर",
                "laptop": "लैपटॉप",
                "smart monitor": "स्मार्ट मॉनिटर",
                "gaming monitor": "गेमिंग मॉनिटर",
                "curved monitor": "कर्व्ड मॉनिटर",
                "development kit": "डेवलपमेंट किट",
                "kit": "किट",
                "connector": "कनेक्टर",
                "inductor": "इंडक्टर",
                "capacitor": "कैपेसिटर",
                "resistor": "रेसिस्टर",
                "microcontroller": "माइक्रोकंट्रोलर",
                "processor": "प्रोसेसर",
                "display": "डिस्प्ले",
                "board": "बोर्ड",
                "wire housing": "वायर हाउसिंग",
                "humidity": "ह्यूमिडिटी",
                "temperature": "तापमान",
                "pressure": "प्रेशर",
                "gas": "गैस",
                "battery": "बैटरी",
                "fuel gauge": "फ्यूल गेज",
                "buck": "बक",
                "boost": "बूस्ट",
            },
            "te": {
                "module": "మాడ్యూల్",
                "transceiver": "ట్రాన్సీవర్",
                "power": "పవర్",
                "channel": "చానల్",
                "sensor": "సెన్సర్",
                "monitor": "మానిటర్",
                "laptop": "ల్యాప్‌టాప్",
                "connector": "కనెక్టర్",
                "controller": "కంట్రోలర్",
                "display": "డిస్‌ప్లే",
                "board": "బోర్డ్",
            },
        }
        mapping = dictionaries.get(target)
        if not mapping:
            return text

        result = text
        # Longer phrases first so "physical layer" wins before "layer".
        for src, dst in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
            result = re.sub(r"\b%s\b" % re.escape(src), dst, result, flags=re.IGNORECASE)
        return result
