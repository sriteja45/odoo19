from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    xevoria_translation_ids = fields.One2many(
        "xevoria.product.translation",
        "product_id",
        string="Xevoria Translations",
        help="Marketplace-style cached translations for this product."
    )

    xevoria_translation_count = fields.Integer(
        string="Translation Count",
        compute="_compute_xevoria_translation_count"
    )

    xevoria_translation_pending = fields.Boolean(
        string="Translation Pending",
        default=True,
        copy=False,
        help="Checked when this product needs background translation generation."
    )

    xevoria_translation_last_generated = fields.Datetime(
        string="Last Translation Generated",
        copy=False,
        readonly=True,
    )

    def _compute_xevoria_translation_count(self):
        for product in self:
            product.xevoria_translation_count = len(product.xevoria_translation_ids)

    def xevoria_get_translation(self, lang=None):
        self.ensure_one()
        lang = lang or self.env.context.get("lang") or "en_US"
        lang_short = lang.split("_")[0] if lang else lang

        exact = self.xevoria_translation_ids.filtered(
            lambda tr: tr.active and tr.lang == lang
        )[:1]
        if exact:
            return exact

        short = self.xevoria_translation_ids.filtered(
            lambda tr: tr.active and tr.lang == lang_short
        )[:1]
        return short

    def _xevoria_translation_languages(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "xevoria.translation.languages",
            "hi_IN,te_IN,ta_IN,fr_FR,de_DE",
        )
        return [lang.strip() for lang in value.split(",") if lang.strip()]

    def _xevoria_write_native_website_translation(self, lang, translated_name=None, translated_description=None):
        self.ensure_one()
        if not lang or lang.split("_")[0].lower() == "en":
            return True

        vals = {}
        if translated_name:
            vals["name"] = translated_name
        if translated_description:
            vals["website_description"] = translated_description
        if not vals:
            return True

        try:
            self.with_context(lang=lang, xevoria_skip_translation_queue=True).sudo().write(vals)
        except Exception as error:
            _logger.warning(
                "Could not write native Odoo website translation for product %s / %s: %s",
                self.id, lang, error
            )
        return True

    def xevoria_generate_translations(self, force=False, langs=None):
        Translation = self.env["xevoria.product.translation"].sudo()
        Service = self.env["xevoria.translation.service"].sudo()
        target_langs = langs or self._xevoria_translation_languages()

        for product in self:
            source_name = product.name or ""
            source_description = product.website_description or product.description_sale or ""

            if not source_name and not source_description:
                product.with_context(xevoria_skip_translation_queue=True).write({
                    "xevoria_translation_pending": False,
                    "xevoria_translation_last_generated": fields.Datetime.now(),
                })
                continue

            for lang in target_langs:
                existing = Translation.search([
                    ("product_id", "=", product.id),
                    ("lang", "=", lang),
                ], limit=1)
                source_changed = bool(existing) and (
                    existing.source_name != source_name
                    or (existing.source_description or "") != (source_description or "")
                )
                if existing and not force and not source_changed:
                    continue

                translated_name = Service.translate_text(source_name, lang) if source_name else ""
                translated_description = Service.translate_text(source_description, lang) if source_description else ""
                vals = {
                    "product_id": product.id,
                    "lang": lang,
                    "source_name": source_name,
                    "translated_name": translated_name or source_name or product.display_name,
                    "source_description": source_description,
                    "translated_description": translated_description or source_description,
                    "active": True,
                }
                if existing:
                    existing.write(vals)
                else:
                    Translation.create(vals)
                product._xevoria_write_native_website_translation(
                    lang,
                    translated_name=vals.get("translated_name"),
                    translated_description=vals.get("translated_description"),
                )

            product.with_context(xevoria_skip_translation_queue=True).write({
                "xevoria_translation_pending": False,
                "xevoria_translation_last_generated": fields.Datetime.now(),
            })
        return True

    def xevoria_queue_translations(self):
        if not self:
            return True
        self.with_context(xevoria_skip_translation_queue=True).write({
            "xevoria_translation_pending": True,
        })
        return True

    @api.model
    def _cron_xevoria_generate_pending_translations(self, batch_size=20):
        batch_size = int(batch_size or 20)
        products = self.sudo().search([
            "|",
            ("xevoria_translation_pending", "=", True),
            ("xevoria_translation_ids", "=", False),
        ], limit=batch_size, order="write_date asc, id asc")

        if not products:
            _logger.info("Xevoria translation cron: no pending products found.")
            return True
        try:
            products.with_context(xevoria_skip_translation_queue=True).xevoria_generate_translations(force=False)
        except Exception as error:
            _logger.exception("Xevoria translation cron failed: %s", error)
            return False
        return True

    def action_xevoria_generate_translations(self):
        self.xevoria_generate_translations(force=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Xevoria Translations",
                "message": "Product translations generated/updated successfully.",
                "type": "success",
                "sticky": False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        try:
            products.xevoria_queue_translations()
        except Exception as error:
            _logger.warning("Xevoria translation queue failed after product create: %s", error)
        return products

    def write(self, vals):
        result = super().write(vals)
        watched_fields = {"name", "website_description", "description_sale"}
        if watched_fields.intersection(vals) and not self.env.context.get("xevoria_skip_translation_queue"):
            try:
                self.xevoria_queue_translations()
            except Exception as error:
                _logger.warning("Xevoria translation queue failed after product write: %s", error)
        return result
