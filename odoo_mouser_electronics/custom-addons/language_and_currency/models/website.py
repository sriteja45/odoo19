# -*- coding: utf-8 -*-
"""Keep Odoo website_sale pricelist synced with the Xevoria currency selector.

Why this file exists:
The header dropdown can store INR/EUR/GBP in our own session/cookie, but
website_sale may rebuild the cart using the website/default pricelist again.
This model-level hook runs whenever website_sale asks for the cart/current
pricelist, so cart/product/checkout pages cannot fall back to USD after reload.
"""

from odoo import models, fields
from odoo.http import request


CURRENCY_PRICELIST_NAMES = {
    'INR': 'India Price List',
    'USD': 'USA Price List',
    'EUR': 'Europe Price List',
    'GBP': 'UK Price List',
    'CNY': 'China Price List',
    'RUB': 'Russia Price List',
}

CURRENCY_PRICELIST_XMLIDS = {
    'INR': ('language_and_currency.pricelist_india', 'Xevoria_electronics.pricelist_india', 'xevoria_electronics.pricelist_india'),
    'USD': ('language_and_currency.pricelist_usa', 'Xevoria_electronics.pricelist_usa', 'xevoria_electronics.pricelist_usa'),
    'EUR': ('language_and_currency.pricelist_europe', 'Xevoria_electronics.pricelist_europe', 'xevoria_electronics.pricelist_europe'),
    'GBP': ('language_and_currency.pricelist_uk', 'Xevoria_electronics.pricelist_uk', 'xevoria_electronics.pricelist_uk'),
}


def _session_currency():
    try:
        return (request.session.get('xevoria_currency') or request.httprequest.cookies.get('xevoria_currency') or '').upper()
    except Exception:
        return ''


class Website(models.Model):
    _inherit = 'website'

    def _xevoria_env_ref_any(self, xmlids):
        for xmlid in xmlids or []:
            rec = self.env.ref(xmlid, raise_if_not_found=False)
            if rec:
                return rec.sudo()
        return False

    def _xevoria_get_currency_pricelist(self, currency_code=None):
        currency_code = (currency_code or _session_currency() or 'INR').upper()
        Pricelist = self.env['product.pricelist'].sudo()
        Currency = self.env['res.currency'].sudo()

        pricelist = self._xevoria_env_ref_any(CURRENCY_PRICELIST_XMLIDS.get(currency_code))
        currency = Currency.search([('name', '=', currency_code)], limit=1)
        if not currency:
            return pricelist

        expected_name = CURRENCY_PRICELIST_NAMES.get(currency_code, '%s Price List' % currency_code)

        # Prefer our named website pricelist. Do NOT take the first random pricelist
        # with the same currency (ex: Benelux/EUR or USD Website Pricelist), because
        # that can make the header show INR/EUR while the cart still behaves like the
        # old website/default USD pricelist.
        named = Pricelist.search([('name', '=', expected_name), ('currency_id', '=', currency.id)], limit=1)
        if named:
            pricelist = named

        # If XMLID points to a wrong/old record, ignore it.
        if pricelist and pricelist.currency_id.id != currency.id:
            pricelist = False

        if not pricelist:
            vals = {'name': expected_name, 'currency_id': currency.id}
            if 'selectable' in Pricelist._fields:
                vals['selectable'] = True
            pricelist = Pricelist.create(vals)

        vals = {}
        if 'selectable' in Pricelist._fields and not pricelist.selectable:
            vals['selectable'] = True
        if 'active' in Pricelist._fields and not pricelist.active:
            vals['active'] = True
        if vals:
            pricelist.write(vals)

        if 'website_id' in Pricelist._fields and not pricelist.website_id and self[:1]:
            try:
                pricelist.write({'website_id': self[:1].id})
            except Exception:
                pass

        # Make the pricelist available on all websites when the field exists.
        for website in self.sudo().search([]):
            if 'pricelist_ids' in website._fields and pricelist.id not in website.pricelist_ids.ids:
                website.write({'pricelist_ids': [(4, pricelist.id)]})

        return pricelist.sudo()

    def _xevoria_line_uom(self, line):
        """Return sale line UoM safely across Odoo versions."""
        try:
            if 'product_uom' in line._fields:
                return line.product_uom
            if 'product_uom_id' in line._fields:
                return line.product_uom_id
        except Exception:
            pass
        return line.product_id.uom_id

    def _xevoria_sync_sale_order_currency(self, order=None, pricelist=None):
        pricelist = pricelist or self._xevoria_get_currency_pricelist()
        if not pricelist:
            return order

        try:
            request.session['website_sale_current_pl'] = pricelist.id
            request.session['sale_pricelist_id'] = pricelist.id
            request.session['xevoria_currency'] = pricelist.currency_id.name
        except Exception:
            pass

        if not order:
            return order

        order = order.sudo()
        if order.pricelist_id.id != pricelist.id:
            order.write({'pricelist_id': pricelist.id})

        # Reprice cart lines using native hooks first, with a safe fallback.
        try:
            if hasattr(order, 'action_update_prices'):
                order.action_update_prices()
            elif hasattr(order, '_recompute_prices'):
                order._recompute_prices()
            else:
                for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                    if hasattr(line, '_compute_price_unit'):
                        line._compute_price_unit()
                    else:
                        try:
                            price = pricelist._get_product_price(line.product_id, line.product_uom_qty or 1.0, order.partner_id, uom_id=self._xevoria_line_uom(line).id, date=order.date_order)
                        except TypeError:
                            price = pricelist._get_product_price(line.product_id, line.product_uom_qty or 1.0, order.partner_id)
                        line.write({'price_unit': price})
            # Force selected pricelist values onto existing cart lines.
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                try:
                    price = pricelist._get_product_price(line.product_id, line.product_uom_qty or 1.0, order.partner_id, uom_id=self._xevoria_line_uom(line).id, date=order.date_order)
                except TypeError:
                    try:
                        price = pricelist._get_product_price(line.product_id, line.product_uom_qty or 1.0, order.partner_id)
                    except Exception:
                        price = None
                except Exception:
                    price = None
                # If the selected pricelist has no proper item/rate, fall back to
                # Odoo currency conversion from the company currency. This is the
                # case shown in your screenshots: selector changes but amounts stay
                # as the USD list_price.
                if price is None or (pricelist.currency_id != order.company_id.currency_id and abs(price - (line.product_id.list_price or 0.0)) < 0.00001):
                    try:
                        price = order.company_id.currency_id._convert(
                            line.product_id.list_price or 0.0,
                            pricelist.currency_id,
                            order.company_id,
                            order.date_order or fields.Date.context_today(self),
                        )
                    except Exception:
                        fallback = {'INR': 83.0, 'USD': 1.0, 'EUR': 0.92, 'GBP': 0.79, 'CNY': 7.2, 'RUB': 90.0}
                        price = (line.product_id.list_price or 0.0) * fallback.get(pricelist.currency_id.name, 1.0)
                if price is not None:
                    line.sudo().write({'price_unit': round(price, 2)})

            if hasattr(order, '_compute_tax_id'):
                order._compute_tax_id()
            if hasattr(order, '_compute_amounts'):
                order._compute_amounts()
            elif hasattr(order, '_amount_all'):
                order._amount_all()
        except Exception:
            # Never break checkout because of a cosmetic currency sync error.
            pass
        return order

    def sale_get_order(self, *args, **kwargs):
        order = super().sale_get_order(*args, **kwargs)
        if _session_currency():
            self._xevoria_sync_sale_order_currency(order=order)
        return order

    def _get_current_pricelist(self):
        currency_code = _session_currency()
        if currency_code:
            pricelist = self._xevoria_get_currency_pricelist(currency_code)
            if pricelist:
                try:
                    request.session['website_sale_current_pl'] = pricelist.id
                    request.session['sale_pricelist_id'] = pricelist.id
                except Exception:
                    pass
                return pricelist
        return super()._get_current_pricelist()
