from odoo import models, api, fields
import json
import logging
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

_logger = logging.getLogger(__name__)


class ProductPricelistGenerator(models.AbstractModel):
    _name = 'mouser.pricelist.generator'
    _description = 'Generate Pricelist Items'

    # Fallback rates are expressed as: 1 USD = X target currency.
    # Your database company/main currency is USD, so product.list_price values
    # like 4850 are USD amounts. The old code treated list_price as INR, so
    # INR/EUR/GBP pricelist items could stay wrong or unchanged.
    DEFAULT_RATES_FROM_USD = {
        'USD': 1.00,
        'INR': 83.00,
        'EUR': 0.92,
        'GBP': 0.79,
        'CNY': 7.20,
        'RUB': 90.00,
    }

    PRICELIST_CURRENCY = {
        'India Price List': 'INR',
        'USA Price List': 'USD',
        'Europe Price List': 'EUR',
        'UK Price List': 'GBP',
        'China Price List': 'CNY',
        'Russia Price List': 'RUB',
    }

    @api.model
    def _fetch_live_rates_from_usd(self):
        """Fetch public exchange rates. Falls back silently when offline."""
        target_codes = ','.join(sorted(set(self.PRICELIST_CURRENCY.values()) - {'USD'}))
        url = 'https://api.frankfurter.app/latest?from=USD&to=%s' % target_codes
        try:
            with urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode('utf-8'))
            rates = {'USD': 1.0}
            rates.update({code: float(value) for code, value in payload.get('rates', {}).items()})
            return rates
        except (URLError, HTTPError, ValueError, TimeoutError, Exception) as exc:
            _logger.info('Could not fetch live Xevoria currency rates, using fallback USD rates: %s', exc)
            return dict(self.DEFAULT_RATES_FROM_USD)

    @api.model
    def _convert_company_amount(self, amount, target_currency):
        company = self.env.company
        company_currency = company.currency_id
        amount = amount or 0.0
        if company_currency and target_currency and company_currency.id != target_currency.id:
            try:
                return company_currency._convert(amount, target_currency, company, self.env.context.get('date') or fields.Date.context_today(self))
            except Exception:
                pass
        if target_currency and target_currency.name != 'USD':
            return amount * self.DEFAULT_RATES_FROM_USD.get(target_currency.name, 1.0)
        return amount

    @api.model
    def generate_pricelist_items(self, use_live_rates=False):
        products = self.env['product.template'].search([])

        for pricelist_name, currency_code in self.PRICELIST_CURRENCY.items():
            pricelist = self.env['product.pricelist'].search([('name', '=', pricelist_name), ('currency_id.name', '=', currency_code)], limit=1)
            if not pricelist:
                currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
                if not currency:
                    continue
                vals = {'name': pricelist_name, 'currency_id': currency.id}
                if 'selectable' in self.env['product.pricelist']._fields:
                    vals['selectable'] = True
                pricelist = self.env['product.pricelist'].create(vals)

            if 'selectable' in pricelist._fields and not pricelist.selectable:
                pricelist.write({'selectable': True})

            for product in products:
                fixed_price = round(self._convert_company_amount(product.list_price, pricelist.currency_id), 2)
                existing = self.env['product.pricelist.item'].search([
                    ('pricelist_id', '=', pricelist.id),
                    ('product_tmpl_id', '=', product.id),
                    ('applied_on', '=', '1_product'),
                ], limit=1)

                values = {
                    'pricelist_id': pricelist.id,
                    'applied_on': '1_product',
                    'product_tmpl_id': product.id,
                    'compute_price': 'fixed',
                    'fixed_price': fixed_price,
                }
                if existing:
                    existing.write({'fixed_price': fixed_price})
                else:
                    self.env['product.pricelist.item'].create(values)
        return True

