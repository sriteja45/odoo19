from odoo import http, fields
from odoo.http import request, Response
from odoo.osv import expression

try:
    from odoo.addons.website_sale.controllers.main import WebsiteSale
except Exception:
    WebsiteSale = object

import json


# ---------------------------------------------------------------------------
# Xevoria language and currency switching helpers
# ---------------------------------------------------------------------------

SUPPORTED_LANGS = {
    'en': 'en_US',
    'hi': 'hi_IN',
    'te': 'te_IN',
    'ta': 'ta_IN',
    'fr': 'fr_FR',
    'de': 'de_DE',
}

COUNTRY_LANGUAGE = {
    'IN': 'hi',
    'FR': 'fr',
    'DE': 'de',
}

COUNTRY_CURRENCY = {
    'IN': 'INR',
    'US': 'USD',
    'FR': 'EUR',
    'DE': 'EUR',
    'GB': 'GBP',
}

CURRENCY_PRICELIST_XMLIDS = {
    'INR': (
        'language_and_currency.pricelist_india',
        'Xevoria_electronics.pricelist_india',
        'xevoria_electronics.pricelist_india'
    ),
    'USD': (
        'language_and_currency.pricelist_usa',
        'Xevoria_electronics.pricelist_usa',
        'xevoria_electronics.pricelist_usa'
    ),
    'EUR': (
        'language_and_currency.pricelist_europe',
        'Xevoria_electronics.pricelist_europe',
        'xevoria_electronics.pricelist_europe'
    ),
    'GBP': (
        'language_and_currency.pricelist_uk',
        'Xevoria_electronics.pricelist_uk',
        'xevoria_electronics.pricelist_uk'
    ),
}


def _safe_redirect_url(url):
    if not url or not isinstance(url, str) or not url.startswith('/') or url.startswith('//'):
        return '/'
    return url


def _detect_country_code():
    geoip = getattr(request, 'geoip', None) or {}
    country_code = (geoip.get('country_code') or geoip.get('country_code2') or '').upper()
    return country_code or ''


def _detect_browser_language():
    accept_language = request.httprequest.headers.get('Accept-Language', '')
    for item in accept_language.split(','):
        code = item.split(';')[0].strip().lower()
        short = code.split('-')[0]
        if short in SUPPORTED_LANGS:
            return short
    return 'en'


class XevoriaLanguageCurrency(http.Controller):
    """Website language/currency helpers that preserve Odoo website_sale behavior."""
    """Safe website language/currency switcher for website_sale.

    It sets Odoo's standard website_sale session pricelist key
    (website_sale_current_pl), so shop pages, product pages, cart, and
    checkout use the selected currency/pricelist consistently.
    """

    def _apply_language(self, short_code):
        short_code = (short_code or 'en')[:2].lower()
        full_code = SUPPORTED_LANGS.get(short_code, 'en_US')
        installed = request.env['res.lang'].sudo().search([
            ('code', '=', full_code),
            ('active', '=', True),
        ], limit=1)
        if installed:
            request.session['frontend_lang'] = installed.code
            request.session['xevoria_lang'] = short_code
            return installed.code
        request.session['xevoria_lang'] = short_code
        request.session['xevoria_lang'] = short_code
        if installed:
            request.session['frontend_lang'] = installed.code
            return installed.code
        return False

    def _env_ref_any(self, xmlids):
        for xmlid in xmlids or []:
            record = request.env.ref(xmlid, raise_if_not_found=False)
            if record:
                return record.sudo()
        return False

    def _get_or_create_pricelist(self, currency_code):
        currency_code = (currency_code or 'INR').upper()

        # Use the website model helper when loaded. It also makes the pricelist
        # selectable/available on the website, which prevents website_sale from
        # falling back to the default USD pricelist on /shop/cart reload.
        website = getattr(request, 'website', False)
        if website and hasattr(website, '_xevoria_get_currency_pricelist'):
            pricelist = website._xevoria_get_currency_pricelist(currency_code)
            if pricelist:
                return pricelist

        xmlids = CURRENCY_PRICELIST_XMLIDS.get(currency_code)
        pricelist = self._env_ref_any(xmlids) if isinstance(xmlids, (tuple, list)) else False
        if pricelist:
            return pricelist.sudo()

        currency = request.env['res.currency'].sudo().search([('name', '=', currency_code)], limit=1)
        if not currency:
            return False

        names = {'INR': 'India Price List', 'USD': 'USA Price List', 'EUR': 'Europe Price List', 'GBP': 'UK Price List', 'CNY': 'China Price List', 'RUB': 'Russia Price List'}
        expected_name = names.get(currency_code, '%s Price List' % currency_code)
        Pricelist = request.env['product.pricelist'].sudo()
        pricelist = Pricelist.search([('name', '=', expected_name), ('currency_id', '=', currency.id)], limit=1)
        if pricelist:
            if 'selectable' in Pricelist._fields and not pricelist.selectable:
                pricelist.write({'selectable': True})
            return pricelist

        vals = {'name': expected_name, 'currency_id': currency.id}
        if 'selectable' in Pricelist._fields:
            vals['selectable'] = True
        return Pricelist.create(vals)

    def _xevoria_line_uom(self, line):
        """Return sale line UoM safely across Odoo versions.

        Odoo 19 can expose the field as product_uom_id instead of the older
        product_uom. Accessing line.product_uom directly caused the 500 error
        in /xevoria/set_currency.
        """
        try:
            if 'product_uom' in line._fields:
                return line.product_uom
            if 'product_uom_id' in line._fields:
                return line.product_uom_id
        except Exception:
            pass
        return line.product_id.uom_id

    def _set_line_price_from_pricelist(self, order, line, pricelist):
        """Fallback repricing for Odoo versions where action_update_prices is absent."""
        product = line.product_id
        qty = line.product_uom_qty or 1.0
        partner = order.partner_id
        price = False

        for args, kwargs in (
            ((product, qty, partner), {'uom_id': self._xevoria_line_uom(line).id, 'date': order.date_order}),
            ((product, qty, partner), {'uom': self._xevoria_line_uom(line), 'date': order.date_order}),
            ((product, qty, partner), {}),
        ):
            try:
                price = pricelist._get_product_price(*args, **kwargs)
                break
            except TypeError:
                continue

        if price is not False:
            line.write({'price_unit': price})

    def _xevoria_force_convert_cart_lines(self, order, pricelist):
        """Last-resort cart repricing when native website_sale hooks keep old USD.

        Some imported electronic products have fixed order-line prices.  When the
        customer changes the website pricelist, Odoo updates the dropdown/session
        but existing order lines can keep their previous price_unit.  This method
        writes the selected pricelist price directly to each normal product line.
        """
        if not order or not pricelist:
            return
        for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
            product = line.product_id
            qty = line.product_uom_qty or 1.0
            price = None
            # 1) Odoo native pricelist engine.
            for args, kwargs in (
                ((product, qty, order.partner_id), {'uom_id': self._xevoria_line_uom(line).id, 'date': order.date_order}),
                ((product, qty, order.partner_id), {'uom': self._xevoria_line_uom(line), 'date': order.date_order}),
                ((product, qty, order.partner_id), {}),
            ):
                try:
                    price = pricelist._get_product_price(*args, **kwargs)
                    break
                except TypeError:
                    continue
                except Exception:
                    price = None
                    break
            # 2) Explicit fixed-price item fallback.
            if price is None:
                item = request.env['product.pricelist.item'].sudo().search([
                    ('pricelist_id', '=', pricelist.id),
                    '|', ('product_id', '=', product.id), ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ], order='product_id desc, min_quantity desc, id desc', limit=1)
                if item and item.compute_price == 'fixed':
                    price = item.fixed_price
            if price is None or (pricelist.currency_id != order.company_id.currency_id and abs((price or 0.0) - (product.list_price or 0.0)) < 0.00001):
                try:
                    price = order.company_id.currency_id._convert(
                        product.list_price or 0.0,
                        pricelist.currency_id,
                        order.company_id,
                        order.date_order or fields.Date.context_today(request.env['sale.order']),
                    )
                except Exception:
                    fallback = {'INR': 83.0, 'USD': 1.0, 'EUR': 0.92, 'GBP': 0.79, 'CNY': 7.2, 'RUB': 90.0}
                    price = (product.list_price or 0.0) * fallback.get(pricelist.currency_id.name, 1.0)
            if price is not None:
                line.sudo().write({'price_unit': round(price, 2)})

    def _sync_open_cart_pricelist(self, pricelist):
        """Update the already-created website cart/order to the selected pricelist.

        Setting only request.session['website_sale_current_pl'] changes the dropdown
        value, but an existing cart keeps its old sale.order.pricelist_id. That is
        why the screenshots showed INR/EUR/GBP selected while cart totals remained
        in USD. This method updates the active cart and reprices its lines.
        """
        if not pricelist or not getattr(request, 'website', False):
            return False

        try:
            order = request.website.sale_get_order(force_create=False)
        except Exception:
            order = False

        if not order:
            # In some Odoo versions/custom website customizations, sale_get_order(False)
            # can miss the current cart after the session pricelist changed.  The
            # active cart id is still kept in the session, so update that order
            # directly before redirecting back to /shop/cart.
            order_id = (request.session.get('sale_order_id')
                        or request.session.get('website_sale_order_id')
                        or request.session.get('website_order_id'))
            if order_id:
                order = request.env['sale.order'].sudo().browse(int(order_id)).exists()

        if not order:
            return False

        order = order.sudo().with_context(website_id=request.website.id)
        if order.pricelist_id.id != pricelist.id:
            order.write({'pricelist_id': pricelist.id})

        # Prefer Odoo's native repricing hooks when present.
        if hasattr(order, 'action_update_prices'):
            order.action_update_prices()
        elif hasattr(order, '_recompute_prices'):
            order._recompute_prices()
        else:
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                if hasattr(line, '_compute_price_unit'):
                    line._compute_price_unit()
                else:
                    self._set_line_price_from_pricelist(order, line, pricelist)

        # Always force line prices from selected pricelist after native hooks, because
        # existing cart lines are the part that was staying in USD in the screenshots.
        self._xevoria_force_convert_cart_lines(order, pricelist)

        if hasattr(order, '_compute_tax_id'):
            order._compute_tax_id()
        if hasattr(order, '_compute_amounts'):
            order._compute_amounts()
        elif hasattr(order, '_amount_all'):
            order._amount_all()
        return True

    def _apply_currency(self, currency_code):
        currency_code = (currency_code or 'INR').upper()
        pricelist = self._get_or_create_pricelist(currency_code)
        if not pricelist:
            return False

        request.session['xevoria_currency'] = currency_code
        request.session['website_sale_current_pl'] = pricelist.id
        # Keep common website_sale keys synced for compatibility across Odoo versions/customizations.
        request.session['sale_pricelist_id'] = pricelist.id

        # Ensure converted fixed-price items exist for newly-created products too.
        try:
            request.env['mouser.pricelist.generator'].sudo().generate_pricelist_items(use_live_rates=True)
        except Exception:
            pass

        # IMPORTANT: website._xevoria_sync_sale_order_currency(pricelist=...) only
        # syncs session when no order is passed.  The real cart/order must be
        # updated before redirecting back to /shop/cart, otherwise the dropdown
        # changes to INR/EUR/GBP but the existing sale.order stays on the old
        # USD pricelist and Odoo renders $ amounts.
        self._sync_open_cart_pricelist(pricelist)

        website = getattr(request, 'website', False)
        if website and hasattr(website, '_xevoria_sync_sale_order_currency'):
            try:
                order = request.website.sale_get_order(force_create=False)
                if order:
                    website._xevoria_sync_sale_order_currency(order=order, pricelist=pricelist)
            except Exception:
                pass
        return pricelist

    @http.route('/xevoria/auto_detect', type='http', auth='public', website=True, csrf=False)
    def auto_detect(self, redirect='/', **kw):
        country_code = _detect_country_code()
        browser_lang = _detect_browser_language()

        currency = COUNTRY_CURRENCY.get(country_code, 'INR')
        language = browser_lang if browser_lang != 'en' else COUNTRY_LANGUAGE.get(country_code, 'en')

        installed_code = self._apply_language(language)
        self._apply_currency(currency)

        response = request.redirect(_safe_redirect_url(redirect))
        response.set_cookie('xevoria_auto_done', '1', max_age=60 * 60 * 24 * 30, samesite='Lax')
        response.set_cookie('xevoria_currency', currency, max_age=60 * 60 * 24 * 30, samesite='Lax')
        response.set_cookie('xevoria_lang', language, max_age=60 * 60 * 24 * 30, samesite='Lax')
        if installed_code:
            response.set_cookie('frontend_lang', installed_code, max_age=60 * 60 * 24 * 30, samesite='Lax')
        return response

    @http.route('/xevoria/set_language', type='http', auth='public', website=True, csrf=False)
    def set_language(self, lang='en', redirect='/', **kw):
        installed_code = self._apply_language(lang)
        response = request.redirect(_safe_redirect_url(redirect))
        response.set_cookie('xevoria_auto_done', '1', max_age=60 * 60 * 24 * 30, samesite='Lax')
        response.set_cookie('xevoria_lang', (lang or 'en')[:2].lower(), max_age=60 * 60 * 24 * 30, samesite='Lax')
        if installed_code:
            response.set_cookie('frontend_lang', installed_code, max_age=60 * 60 * 24 * 30, samesite='Lax')
        return response

    @http.route('/xevoria/set_currency', type='http', auth='public', website=True, csrf=False)
    def set_currency(self, currency='INR', redirect='/', **kw):
        currency = (currency or 'INR').upper()
        self._apply_currency(currency)
        response = request.redirect(_safe_redirect_url(redirect))
        response.set_cookie('xevoria_auto_done', '1', max_age=60 * 60 * 24 * 30, samesite='Lax')
        response.set_cookie('xevoria_currency', currency, max_age=60 * 60 * 24 * 30, samesite='Lax')
        return response




class XevoriaWebsiteSaleCartCurrency(WebsiteSale):
    """Sync selected currency immediately before cart/checkout pages render."""

    def _xevoria_selected_pricelist(self):
        currency = (request.session.get('xevoria_currency') or request.httprequest.cookies.get('xevoria_currency') or '').upper()
        if not currency:
            return False
        helper = XevoriaLanguageCurrency()
        return helper._get_or_create_pricelist(currency)

    def _xevoria_sync_before_render(self):
        pricelist = self._xevoria_selected_pricelist()
        if pricelist:
            helper = XevoriaLanguageCurrency()
            request.session['website_sale_current_pl'] = pricelist.id
            request.session['sale_pricelist_id'] = pricelist.id
            helper._sync_open_cart_pricelist(pricelist)
        return pricelist

    @http.route(['/shop/cart'], type='http', auth='public', website=True, sitemap=False)
    def cart(self, **post):
        self._xevoria_sync_before_render()
        return super().cart(**post)


    @http.route(['/shop/checkout'], type='http', auth='public', website=True, sitemap=False)
    def checkout(self, **post):
        """Keep selected pricelist synced on checkout without assuming Odoo has checkout().

        Odoo 19 no longer exposes WebsiteSale.checkout() in some builds. Calling
        super().checkout(**post) then raises: AttributeError: 'super' object has
        no attribute 'checkout'.  We still sync currency/pricelist first, then
        delegate to whichever checkout/payment handler exists in the installed
        website_sale version.  If none is available, redirect to the standard
        payment step so the customer is not blocked by a 500 page.
        """
        self._xevoria_sync_before_render()

        parent = super()
        for method_name in ('checkout', 'shop_checkout', 'shop_payment', 'payment'):
            method = getattr(parent, method_name, None)
            if method:
                return method(**post)

        return request.redirect('/shop/payment?try_skip_step=true')

    @http.route(['/shop/checkout'], type='http', auth='public', website=True, sitemap=False)
    def checkout(self, **post):
        """Keep selected pricelist synced on checkout without assuming Odoo has checkout().

        Odoo 19 no longer exposes WebsiteSale.checkout() in some builds. Calling
        super().checkout(**post) then raises: AttributeError: 'super' object has
        no attribute 'checkout'.  We still sync currency/pricelist first, then
        delegate to whichever checkout/payment handler exists in the installed
        website_sale version.  If none is available, redirect to the standard
        payment step so the customer is not blocked by a 500 page.
        """

        # If the user is not logged in, redirect to Login/Sign Up page
        if request.env.user._is_public():
         return request.redirect('/web/login?redirect=/shop/checkout')

        self._xevoria_sync_before_render()


        parent = super()
        for method_name in ('checkout', 'shop_checkout', 'shop_payment', 'payment'):
            method = getattr(parent, method_name, None)
            if method:
                return method(**post)

        return request.redirect('/shop/payment?try_skip_step=true')

        return request.redirect('/shop/cart')


# ---------------------------------------------------------------------------
# Product API with cached translation support - Step 5
# ---------------------------------------------------------------------------

class XevoriaProductApi(http.Controller):
    """Language-aware product API for the custom Xevoria frontend.

    The route uses Step 4 cache records from xevoria.product.translation.
    It does not translate during the website request, so pages stay fast.
    """

    def _json_response(self, payload, status=200):
        return Response(
            json.dumps(payload, ensure_ascii=False),
            status=status,
            content_type="application/json; charset=utf-8",
        )

    def _get_current_lang(self, lang=None):
        requested = (lang or "").strip()
        if requested:
            return SUPPORTED_LANGS.get(requested[:2].lower(), requested)

        session_lang = request.session.get("xevoria_lang") or request.session.get("frontend_lang")
        cookie_lang = request.httprequest.cookies.get("xevoria_lang") or request.httprequest.cookies.get("frontend_lang")
        detected = session_lang or cookie_lang or "en_US"

        if len(detected) == 2:
            return SUPPORTED_LANGS.get(detected.lower(), detected.lower())
        return detected

    def _translated_product_values(self, product, lang):
        translation = product.xevoria_get_translation(lang)
        name = product.name or product.display_name
        description = product.website_description or product.description_sale or ""

        if translation:
            name = translation.translated_name or name
            description = translation.translated_description or description

        categories = []
        for category in product.public_categ_ids:
            translated_category = category.xevoria_translated_name(lang) if hasattr(category, "xevoria_translated_name") else category.name
            categories.append({
                "id": category.id,
                "name": translated_category or category.name,
                "original_name": category.name,
            })

        return {
            "id": product.id,
            "name": name,
            "description": description,
            "original_name": product.name or product.display_name,
            "lang": lang,
            "has_translation": bool(translation),
            "price": product.list_price,
            "currency": request.session.get("xevoria_currency") or "INR",
            "image": "/web/image/product.template/%s/image_512" % product.id,
            "url": "/shop/product/%s" % product.id,
            "manufacturer": product.manufacturer or "",
            "manufacturer_part_no": product.manufacturer_part_no or "",
            "part_number": product.part_number or "",
            "categories": categories,
        }

    def _translate_search_query_to_english(self, query, lang):
        """Translate user search text to English for matching original catalog data.

        Example: user searches Hindi/Telugu text, but product names are stored in
        English. This helper lets the API search English catalog fields while still
        returning localized cached results. If no provider is configured, it safely
        returns the original query.
        """
        query = (query or "").strip()
        if not query:
            return ""

        source = (lang or "en_US").split("_")[0].lower()
        if source == "en":
            return query

        service = request.env["xevoria.translation.service"].sudo()
        return service.translate_text(query, "en", source_lang=source).strip() or query

    def _product_search_domain(self, base_domain, query, lang):
        """Build a multilingual product search domain.

        It searches:
        1. Original user query in English product fields.
        2. English-translated query in English product fields.
        3. Cached translated product rows in xevoria.product.translation.
        """
        query = (query or "").strip()
        if not query:
            return base_domain, ""

        Product = request.env["product.template"].sudo()
        translated_query = self._translate_search_query_to_english(query, lang)

        search_terms = [query]
        if translated_query and translated_query.lower() != query.lower():
            search_terms.append(translated_query)

        or_parts = []
        searchable_fields = [
            "name",
            "description_sale",
            "website_description",
            "default_code",
            "manufacturer",
            "manufacturer_part_no",
            "part_number",
        ]

        for term in search_terms:
            for field_name in searchable_fields:
                if field_name in Product._fields:
                    or_parts.append([(field_name, "ilike", term)])

        Translation = request.env["xevoria.product.translation"].sudo()
        translated_records = Translation.search([
            ("lang", "=", lang),
            "|",
            ("translated_name", "ilike", query),
            ("translated_description", "ilike", query),
        ], limit=300)
        translated_product_ids = translated_records.mapped("product_id").ids
        if translated_product_ids:
            or_parts.append([("id", "in", translated_product_ids)])

        if not or_parts:
            return base_domain, translated_query

        return expression.AND([base_domain, expression.OR(or_parts)]), translated_query


    def _translated_ui_labels(self, lang):
        Cache = request.env["xevoria.translation.cache"].sudo()
        labels = {
            "search_placeholder": "Search products in any language",
            "search_button": "Search",
            "no_products": "No products found",
            "translated": "Translated",
            "price": "Price",
            "category": "Category",
            "filters": "Filters",
            "add_to_cart": "Add to Cart",
            "buy_now": "Buy Now",
            "wishlist": "Wishlist",
        }
        return {key: Cache.get_or_create_label(key, text, lang) for key, text in labels.items()}

    def _translated_categories(self, lang, limit=100):
        Category = request.env["product.public.category"].sudo()
        categories = Category.search([], limit=limit, order="sequence, name")
        return [{
            "id": cat.id,
            "name": cat.xevoria_translated_name(lang) if hasattr(cat, "xevoria_translated_name") else cat.name,
            "original_name": cat.name,
            "parent_id": cat.parent_id.id if cat.parent_id else False,
        } for cat in categories]

    def _translated_filters(self, lang, limit=100):
        Attribute = request.env["product.attribute"].sudo()
        attributes = Attribute.search([], limit=limit, order="sequence, name")
        result = []
        for attr in attributes:
            values = []
            for val in attr.value_ids:
                values.append({
                    "id": val.id,
                    "name": val.xevoria_translated_name(lang) if hasattr(val, "xevoria_translated_name") else val.name,
                    "original_name": val.name,
                })
            result.append({
                "id": attr.id,
                "name": attr.xevoria_translated_name(lang) if hasattr(attr, "xevoria_translated_name") else attr.name,
                "original_name": attr.name,
                "values": values,
            })
        return result

    @http.route('/api/products', type='http', auth='public', website=True, csrf=False)
    def api_products(self, lang=None, limit=24, q=None, search=None, **kw):
        try:
            limit = min(max(int(limit or 24), 1), 100)
        except Exception:
            limit = 24

        current_lang = self._get_current_lang(lang)
        query = (q or search or "").strip()

        base_domain = [('sale_ok', '=', True)]
        if 'website_published' in request.env['product.template']._fields:
            base_domain.append(('website_published', '=', True))

        domain, translated_query = self._product_search_domain(base_domain, query, current_lang)

        products = request.env['product.template'].sudo().search(domain, limit=limit, order='id desc')
        values = [self._translated_product_values(product, current_lang) for product in products]

        return self._json_response({
            "lang": current_lang,
            "query": query,
            "translated_query": translated_query,
            "count": len(values),
            "products": values,
            "categories": self._translated_categories(current_lang),
            "filters": self._translated_filters(current_lang),
            "labels": self._translated_ui_labels(current_lang),
        })

    @http.route('/api/products/search', type='http', auth='public', website=True, csrf=False)
    def api_products_search(self, **kw):
        """Alias route for frontend search boxes."""
        return self.api_products(**kw)


    @http.route('/api/categories', type='http', auth='public', website=True, csrf=False)
    def api_categories(self, lang=None, **kw):
        current_lang = self._get_current_lang(lang)
        return self._json_response({
            "lang": current_lang,
            "categories": self._translated_categories(current_lang),
        })

    @http.route('/api/filters', type='http', auth='public', website=True, csrf=False)
    def api_filters(self, lang=None, **kw):
        current_lang = self._get_current_lang(lang)
        return self._json_response({
            "lang": current_lang,
            "filters": self._translated_filters(current_lang),
            "labels": self._translated_ui_labels(current_lang),
        })

    @http.route('/api/ui-labels', type='http', auth='public', website=True, csrf=False)
    def api_ui_labels(self, lang=None, **kw):
        current_lang = self._get_current_lang(lang)
        return self._json_response({
            "lang": current_lang,
            "labels": self._translated_ui_labels(current_lang),
        })


class XevoriaNativeShopTranslationApi(http.Controller):
    """Tiny JSON endpoint used by frontend JS to localize Odoo native /shop cards.

    Odoo website_sale renders the native shop page before our /api/products code
    is used. This endpoint lets the existing /shop DOM replace product titles
    with cached or freshly generated Xevoria translations.
    """

    @http.route('/xevoria/native-shop/product-translations', type='http', auth='public', website=True, csrf=False)
    def product_translations(self, ids='', lang='', **kw):
        def json_response(payload, status=200):
            return Response(json.dumps(payload, ensure_ascii=False), status=status, content_type='application/json; charset=utf-8')

        id_list = []
        for part in (ids or '').split(','):
            part = part.strip()
            if part.isdigit():
                id_list.append(int(part))
        if not id_list:
            return json_response({'products': {}})

        # Reuse API language detection when possible.
        lang = lang or request.session.get('frontend_lang') or request.httprequest.cookies.get('frontend_lang') or 'en_US'
        if len(lang) == 2:
            lang = SUPPORTED_LANGS.get(lang.lower(), lang)

        Product = request.env['product.template'].sudo()
        Service = request.env['xevoria.translation.service'].sudo()
        Translation = request.env['xevoria.product.translation'].sudo()
        products = Product.browse(id_list).exists()
        result = {}

        for product in products:
            original_name = product.name or product.display_name
            name = original_name
            translated = ""
            translation = product.xevoria_get_translation(lang) if hasattr(product, 'xevoria_get_translation') else False
            if translation and translation.translated_name:
                name = translation.translated_name
            else:
                # If cache/native translation is missing, generate just this title now.
                # This is a fallback for existing products that were created before
                # the cron/cache existed. It keeps /shop useful immediately.
                translated = Service.translate_text(original_name, lang)
                if translated and translated != original_name:
                    name = translated
                    existing = Translation.search([('product_id', '=', product.id), ('lang', '=', lang)], limit=1)
                    vals = {
                        'product_id': product.id,
                        'lang': lang,
                        'source_name': original_name,
                        'translated_name': translated,
                        'active': True,
                    }
                    if existing:
                        existing.write(vals)
                    else:
                        Translation.create(vals)
                    if hasattr(product, '_xevoria_write_native_website_translation'):
                        product._xevoria_write_native_website_translation(lang, translated_name=translated)

            # Also get/translate the short description (description_sale)
            original_desc = product.description_sale or ''
            translated_desc = original_desc
            if translation and translation.translated_description:
                translated_desc = translation.translated_description
            elif original_desc:
                # Translate the description even when the name translation already existed
                # or when the product name did not need a new fallback translation.
                translated_desc_text = Service.translate_text(original_desc, lang)
                if translated_desc_text and translated_desc_text != original_desc:
                    translated_desc = translated_desc_text
                    existing = Translation.search([('product_id', '=', product.id), ('lang', '=', lang)], limit=1)
                    if existing:
                        existing.write({'translated_description': translated_desc_text})

            result[str(product.id)] = {
                'id': product.id,
                'name': name,
                'description': translated_desc,
                'original_name': original_name,
                'translated': bool(name and name != original_name),
            }

        return json_response({'lang': lang, 'products': result})
