from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
import re

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

_logger = logging.getLogger(__name__)


class MouserManufacturer(models.Model):
    _name = 'mouser.manufacturer'
    _description = 'Manufacturer'
    _order = 'name asc'

    name = fields.Char(required=True, translate=False, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_published = fields.Boolean(default=True, string='Published on Website')
    logo = fields.Image(max_width=512, max_height=512)
    banner_image = fields.Image(max_width=1920, max_height=500)
    short_description = fields.Char()
    website_description = fields.Html(sanitize=True)
    product_tmpl_ids = fields.One2many('product.template', 'manufacturer_id', string='Products')
    product_count = fields.Integer(compute='_compute_product_count', string='Products')
    category_ids = fields.Many2many(
        'product.public.category',
        'mouser_manufacturer_public_category_rel',
        'manufacturer_id',
        'category_id',
        string='Website Categories',
    )
    first_letter = fields.Char(compute='_compute_first_letter', store=True, index=True)
    website_slug = fields.Char(compute='_compute_website_slug', store=True, index=True)
    website_url = fields.Char(compute='_compute_website_url')
    mouser_api_source = fields.Boolean(string='Created/Updated from Mouser API', default=False)
    mouser_last_sync = fields.Datetime(string='Last Mouser API Sync', readonly=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Manufacturer name must be unique.'),
    ]

    @api.depends('name')
    def _compute_first_letter(self):
        for record in self:
            if record.name:
                first = record.name[0].upper()
                record.first_letter = first if first.isalpha() else '#'
            else:
                record.first_letter = '#'

    @api.depends('product_tmpl_ids.website_published', 'product_tmpl_ids.sale_ok', 'mouser_api_source')
    def _compute_product_count(self):
        for record in self:
            local_count = len(
                record.product_tmpl_ids.filtered(lambda p: p.website_published and p.sale_ok)
            )
            record.product_count = local_count

    @api.depends('name')
    def _compute_website_slug(self):
        # Explicit slug overrides for manufacturers whose name contains characters
        # that would produce ugly auto-generated slugs (e.g. slashes, spaces).
        SLUG_OVERRIDES = {
            'Maxim Integrated / Analog Devices': 'maxim-integrated',
        }
        for record in self:
            if record.name and record.name in SLUG_OVERRIDES:
                record.website_slug = SLUG_OVERRIDES[record.name]
                continue
            name = (record.name or '').strip().lower()
            slug = re.sub(r'[^a-z0-9]+', '-', name).strip('-')
            record.website_slug = slug or str(record.id or '')

    @api.depends('website_slug')
    def _compute_website_url(self):
        for record in self:
            record.website_url = '/manufacturer/%s/' % (record.website_slug or record.id)

    def _mouser_api_key(self):
        return self.env['ir.config_parameter'].sudo().get_param('mouser_theme.mouser_api_key')

    def _mouser_search_keyword(self, keyword, records=25, starting_record=0):
        """Call Mouser Search API v2 keyword endpoint and return Parts safely."""
        data = self._mouser_search_keyword_raw(keyword, records=records, starting_record=starting_record)
        errors = data.get('Errors') or []
        if errors:
            _logger.warning('Mouser API returned errors for keyword %s: %s', keyword, errors)
        return ((data.get('SearchResults') or {}).get('Parts') or [])

    def _mouser_search_keyword_raw(self, keyword, records=25, starting_record=0):
        """Return raw Mouser API response JSON.

        This helper is also used by the website API test route so that API
        problems can be checked without crashing the website page.
        """
        if requests is None:
            raise UserError(_('Python requests library is not available on this Odoo server.'))
        api_key = self._mouser_api_key()
        if not api_key:
            raise UserError(_('Please set Mouser API key in Settings > Technical > System Parameters: mouser_theme.mouser_api_key'))

        url = 'https://api.mouser.com/api/v2/search/keyword'
        payload = {
            'SearchByKeywordRequest': {
                'keyword': keyword,
                'records': int(records),
                'startingRecord': int(starting_record),
                'searchOptions': '',
                'searchWithYourSignUpLanguage': False,
            }
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Odoo-Mouser-Theme/1.2',
        }

        # Mouser docs/examples have used both apiKey and apikey casing across
        # versions. Try the documented v2 casing first, then fallback to lower
        # casing before reporting an auth problem.
        last_response = None
        for key_name in ('apiKey', 'apikey'):
            response = requests.post(
                url,
                params={key_name: api_key},
                json=payload,
                timeout=20,
                headers=headers,
            )
            last_response = response
            if response.status_code != 403:
                response.raise_for_status()
                return response.json() or {}

        # Keep the real HTTP details in the error, but never log/print the API key.
        body_preview = (last_response.text or '')[:500] if last_response is not None else ''
        raise UserError(_('Mouser API request is forbidden (403). Please verify that this API key is active and approved for Search API. Response: %s') % body_preview)

    def fetch_mouser_products(self, limit=24):
        """Return normalized Mouser API product dictionaries for the website page."""
        self.ensure_one()
        # For compound names (e.g. 'Maxim Integrated / Analog Devices') use the
        # primary brand name so the API returns relevant results.
        API_KEYWORD_OVERRIDES = {
            'Maxim Integrated / Analog Devices': 'Maxim Integrated',
            'Hittite / Analog Devices': 'Hittite Microwave',
            'Linear Technology / Analog Devices': 'Linear Technology',
            'Power by Linear / Analog Devices': 'Power by Linear',
            'Trinamic / Analog Devices': 'Trinamic',
        }
        keyword = API_KEYWORD_OVERRIDES.get(self.name, self.name)
        parts = self._mouser_search_keyword(keyword, records=limit, starting_record=0)
        normalized = []
        wanted = (self.name or '').strip().lower()
        for part in parts:
            manufacturer = (part.get('Manufacturer') or '').strip()
            if wanted and manufacturer and wanted not in manufacturer.lower() and manufacturer.lower() not in wanted:
                # For overridden keywords also accept the override keyword itself
                override_kw = API_KEYWORD_OVERRIDES.get(self.name, '').strip().lower()
                if override_kw and override_kw not in manufacturer.lower():
                    continue
            normalized.append({
                'name': part.get('Description') or part.get('ManufacturerPartNumber') or part.get('MouserPartNumber') or 'Mouser Product',
                'manufacturer_part_number': part.get('ManufacturerPartNumber') or '',
                'mouser_part_number': part.get('MouserPartNumber') or '',
                'availability': part.get('Availability') or '',
                'datasheet_url': part.get('DataSheetUrl') or '',
                'product_url': part.get('ProductDetailUrl') or '#',
                'image_url': part.get('ImagePath') or '',
                'category': part.get('Category') or '',
            })
        self.sudo().write({'mouser_last_sync': fields.Datetime.now()})
        return normalized[:limit]

    def action_sync_manufacturers_from_mouser(self):
        """Create/update manufacturer records by sampling Mouser Search API results A-Z."""
        Manufacturer = self.sudo()
        found_names = set()
        # There is no public manufacturer-list endpoint in the Search API pages; sampling A-Z keeps the list dynamic.
        for keyword in [chr(code) for code in range(65, 91)]:
            try:
                parts = Manufacturer._mouser_search_keyword(keyword, records=50, starting_record=0)
            except Exception as exc:
                _logger.exception('Mouser manufacturer sync failed on keyword %s', keyword)
                raise UserError(_('Mouser API sync failed: %s') % exc)
            for part in parts:
                name = (part.get('Manufacturer') or '').strip()
                if name:
                    found_names.add(name)

        created = updated = 0
        for name in sorted(found_names):
            manufacturer = Manufacturer.search([('name', '=ilike', name)], limit=1)
            vals = {'name': name, 'active': True, 'is_published': True, 'mouser_api_source': True, 'mouser_last_sync': fields.Datetime.now()}
            if manufacturer:
                manufacturer.write(vals)
                updated += 1
            else:
                Manufacturer.create(vals)
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mouser API Sync Completed'),
                'message': _('Created %s manufacturers and updated %s manufacturers.') % (created, updated),
                'sticky': False,
                'type': 'success',
            }
        }
