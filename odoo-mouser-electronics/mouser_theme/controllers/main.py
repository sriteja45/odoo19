from odoo import http
from odoo.http import request
import os
from urllib.parse import quote


# ── Mouser Popular Categories: name → URL slug mapping ───────────────────────
# These match the exact slugs used on mouser.in
POPULAR_CATEGORY_SLUGS = {
    'Automotive Connectors':        '/c/connectors/automotive-connectors/',
    'Capacitors':                   '/c/passive-components/capacitors/',
    'Connectors':                   '/c/connectors/',
    'DC/DC Converters':             '/c/power/dc-dc-converters/',
    'Discrete Semiconductors':      '/c/semiconductors/discrete-semiconductors/',
    'Embedded Solutions':           '/c/embedded-solutions/',
    'Enclosures, Boxes & Cases':    '/c/enclosures/enclosures-boxes-cases/',
    'Headers & Wire Housings':      '/c/connectors/headers-wire-housings/',
    'Inductors, Chokes & Coils':    '/c/passive-components/inductors-chokes-coils/',
    'Industrial Automation':        '/c/industrial-automation/',
    'Passive Components':           '/c/passive-components/',
    'Pin & Socket Connectors':      '/c/connectors/pin-socket-connectors/',
    'Power Supplies':               '/c/power/power-supplies/',
    'Relays, Contactors & Solenoids': '/c/electromechanical/relays-contactors-solenoids/',
    'Resistors':                    '/c/passive-components/resistors/',
    'Semiconductors':               '/c/semiconductors/',
    'Switches':                     '/c/electromechanical/switches/',
    'USB Connectors':               '/c/connectors/usb-connectors/',
    # Additional categories the API might return
    'Circuit Protection':           '/c/circuit-protection/',
    'Electromechanical':            '/c/electromechanical/',
    'Enclosures':                   '/c/enclosures/',
    'Engineering Tools':            '/c/engineering-development-tools/',
    'LED Lighting':                 '/c/led-lighting/',
    'Memory & Data Storage':        '/c/embedded-solutions/memory-data-storage/',
    'Opto-electronics':             '/c/opto-electronics/',
    'Power':                        '/c/power/',
    'RF & Wireless':                '/c/rf-wireless/',
    'Sensors':                      '/c/sensors/',
    'Test & Measurement':           '/c/test-measurement/',
    'Thermal Management':           '/c/thermal-management/',
    'Tools & Supplies':             '/c/tools-supplies/',
    'Wire & Cable':                 '/c/wire-cable/',
}

# Exact 18 popular categories shown on mouser.in — used as fallback
POPULAR_CATEGORIES_DEFAULT = [
    {'name': 'Automotive Connectors',       'url': '/c/connectors/automotive-connectors/'},
    {'name': 'Capacitors',                  'url': '/c/passive-components/capacitors/'},
    {'name': 'Connectors',                  'url': '/c/connectors/'},
    {'name': 'DC/DC Converters',            'url': '/c/power/dc-dc-converters/'},
    {'name': 'Discrete Semiconductors',     'url': '/c/semiconductors/discrete-semiconductors/'},
    {'name': 'Embedded Solutions',          'url': '/c/embedded-solutions/'},
    {'name': 'Enclosures, Boxes & Cases',   'url': '/c/enclosures/enclosures-boxes-cases/'},
    {'name': 'Headers & Wire Housings',     'url': '/c/connectors/headers-wire-housings/'},
    {'name': 'Inductors, Chokes & Coils',   'url': '/c/passive-components/inductors-chokes-coils/'},
    {'name': 'Industrial Automation',       'url': '/c/industrial-automation/'},
    {'name': 'Passive Components',          'url': '/c/passive-components/'},
    {'name': 'Pin & Socket Connectors',     'url': '/c/connectors/pin-socket-connectors/'},
    {'name': 'Power Supplies',              'url': '/c/power/power-supplies/'},
    {'name': 'Relays, Contactors & Solenoids', 'url': '/c/electromechanical/relays-contactors-solenoids/'},
    {'name': 'Resistors',                   'url': '/c/passive-components/resistors/'},
    {'name': 'Semiconductors',              'url': '/c/semiconductors/'},
    {'name': 'Switches',                    'url': '/c/electromechanical/switches/'},
    {'name': 'USB Connectors',              'url': '/c/connectors/usb-connectors/'},
]


def _fetch_popular_categories(api_key):
    """Fetch live popular categories from Mouser API.
    Returns list of {name, url} dicts. Falls back gracefully."""
    try:
        import requests as req
        # Try the categories search endpoint
        url = f"https://api.mouser.com/api/v2/search/categories?apiKey={api_key}"
        resp = req.get(url, headers={"Content-Type": "application/json"}, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            cats_raw = data.get('CategoriesResults', [])
            if cats_raw:
                result = []
                seen = set()
                for cat in cats_raw:
                    name = cat.get('Name', '').strip()
                    if name and name not in seen:
                        seen.add(name)
                        slug = POPULAR_CATEGORY_SLUGS.get(name)
                        if slug:
                            result.append({'name': name, 'url': slug})
                if len(result) >= 6:
                    return result
    except Exception:
        pass
    return POPULAR_CATEGORIES_DEFAULT


class MouserHomepageController(http.Controller):

    @http.route(['/', '/mouser-home'], type='http', auth='public', website=True, sitemap=True)
    def mouser_home(self, **kwargs):
        values = {
            'categories': [
                {'name': 'Newest Products',       'slug': 'newest-products'},
                {'name': 'Circuit Protection',    'slug': 'circuit-protection'},
                {'name': 'Connectors',            'slug': 'connectors'},
                {'name': 'Electromechanical',     'slug': 'electromechanical'},
                {'name': 'Embedded Solutions',    'slug': 'embedded-solutions'},
                {'name': 'Enclosures',            'slug': 'enclosures'},
                {'name': 'Engineering Tools',     'slug': 'engineering-development-tools'},
                {'name': 'Industrial Automation', 'slug': 'industrial-automation'},
                {'name': 'LED Lighting',          'slug': 'led-lighting'},
                {'name': 'Memory & Data Storage', 'slug': 'embedded-solutions/memory-data-storage'},
                {'name': 'Opto-electronics',      'slug': 'opto-electronics'},
                {'name': 'Passive Components',    'slug': 'passive-components'},
                {'name': 'Power',                 'slug': 'power'},
                {'name': 'RF & Wireless',         'slug': 'rf-wireless'},
                {'name': 'Semiconductors',        'slug': 'semiconductors'},
                {'name': 'Sensors',               'slug': 'sensors'},
                {'name': 'Test & Measurement',    'slug': 'test-measurement'},
                {'name': 'Thermal Management',    'slug': 'thermal-management'},
                {'name': 'Tools & Supplies',      'slug': 'tools-supplies'},
                {'name': 'Wire & Cable',          'slug': 'wire-cable'},
            ],
            'newest_products': [
                {'brand': 'SENSIRION', 'name': 'SEN62 Air Quality Sensor', 'code': 'SEN62', 'img': '/mouser_theme/static/src/img/prod_sensirion.png', 'url': '/new/sensirion/sen62-air-quality-sensor'},
                {'brand': 'Littelfuse', 'name': 'SP1120-01WTG Unidirectional Discrete TVS Diode', 'code': 'SP1120-01WTG', 'img': '/mouser_theme/static/src/img/prod_littelfuse.png', 'url': '/new/littelfuse/sp1120-01wtg-tvs-diode'},
                {'brand': 'TE', 'name': 'Dynamic HV Connector System', 'code': 'DYNAMIC-HV', 'img': '/mouser_theme/static/src/img/prod_te.png', 'url': '/new/te-connectivity/dynamic-hv-connector-system'},
                {'brand': 'ST', 'name': 'STM32MP215x-DK Discovery Kit', 'code': 'STM32MP215X-DK', 'img': '/mouser_theme/static/src/img/prod_st.png', 'url': '/new/stmicroelectronics/stm32mp215x-dk-discovery-kit'},
            ],
            'manufacturers': [
                {'name': 'Analog Devices', 'img': '/mouser_theme/static/src/img/brand_analog.png'},
                {'name': 'Vishay', 'img': '/mouser_theme/static/src/img/brand_vishay.png'},
                {'name': 'Microchip', 'img': '/mouser_theme/static/src/img/brand_microchip.png'},
                {'name': 'Amphenol', 'img': '/mouser_theme/static/src/img/brand_amphenol.png'},
                {'name': 'NXP', 'img': '/mouser_theme/static/src/img/brand_nxp.png'},
                {'name': 'Murata', 'img': '/mouser_theme/static/src/img/brand_murata.png'},
            ],
            'services_tools': [
                {
                    'title': 'FORTE - The Intelligent BOM Tool',
                    'desc': 'Powered by FORTE, our intelligent tool will save you days!',
                    'img': '/mouser_theme/static/src/img/service_forte.png',
                    'url': '/services-tools/login?redirect=/services-tools/bom',
                },
                {
                    'title': 'Request Quote',
                    'desc': "Need a quick quote? Tell us what you're after.",
                    'img': '/mouser_theme/static/src/img/service_quote.png',
                    'url': '/services-tools/request-quote',
                },
                {
                    'title': 'Price and Availability Assistant',
                    'desc': 'Quickly view product availability and price while purchasing for your designs.',
                    'img': '/mouser_theme/static/src/img/service_pa.png',
                    'url': '/services-tools/price-availability',
                },
                {
                    'title': 'Project Manager',
                    'desc': 'Share your projects and invite your colleagues.',
                    'img': '/mouser_theme/static/src/img/service_project.png',
                    'url': '/services-tools/login?redirect=/services-tools/project-manager',
                },
                {
                    'title': 'Basket/Project Share',
                    'desc': 'Share baskets with colleagues to review and order.',
                    'img': '/mouser_theme/static/src/img/service_basket.png',
                    'url': '/services-tools/cart-share',
                },
            ],
            'popular_categories': _fetch_popular_categories(
                request.env['ir.config_parameter'].sudo().get_param('mouser_theme.mouser_api_key', '')
            ),
            'resources': [
                {'title': 'Technical Resource Library', 'desc': 'Expand your knowledge with industry trends, applications, and more.', 'img': '/mouser_theme/static/img/mouser-technicalresourcecenter-technicalresourcelibrary-image-200x200px-en.webp'},
                {'title': 'Empowering Innovation Together', 'desc': 'Examine the technology shaping our future.', 'img': '/mouser_theme/static/img/mouser-technicalresourcecenter-eit-image-200x200px-en.webp'},
                {'title': 'Purchasing Resource Library', 'desc': 'Exclusive content for purchasing professionals.', 'img': '/mouser_theme/static/img/mouser-technicalresourcecenter-purchasingresourcelibrary-image-200x200px-en.webp'},
                {'title': 'Bench Talk Blog', 'desc': 'Explore insights and commentary on engineering and technology.', 'img': '/mouser_theme/static/img/mouser-technicalresourcecenter-benchtalkblog-image-200x200px-en.webp'},
                {'title': 'Subscription Centre', 'desc': 'Enhance your sources of inspiration by updating your preferences.', 'img': '/mouser_theme/static/img/mouser-technicalresourcecenter-subscriptioncenter-image-200x200px-en.webp'},
            ],
        }
        return request.render('mouser_theme.mouser_homepage', values)
    

    @http.route(['/new', '/new/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_newest_products(self, **kwargs):
        values = {
            'newest_products': [
                {'brand': 'SENSIRION', 'name': 'SEN62 Air Quality Sensor', 'code': 'SEN62', 'img': '/mouser_theme/static/src/img/prod_sensirion.png', 'url': '/new/sensirion/sen62-air-quality-sensor'},
                {'brand': 'Littelfuse', 'name': 'SP1120-01WTG Unidirectional Discrete TVS Diode', 'code': 'SP1120-01WTG', 'img': '/mouser_theme/static/src/img/prod_littelfuse.png', 'url': '/new/littelfuse/sp1120-01wtg-tvs-diode'},
                {'brand': 'TE', 'name': 'Dynamic HV Connector System', 'code': 'DYNAMIC-HV', 'img': '/mouser_theme/static/src/img/prod_te.png', 'url': '/new/te-connectivity/dynamic-hv-connector-system'},
                {'brand': 'ST', 'name': 'STM32MP215x-DK Discovery Kit', 'code': 'STM32MP215X-DK', 'img': '/mouser_theme/static/src/img/prod_st.png', 'url': '/new/stmicroelectronics/stm32mp215x-dk-discovery-kit'},
            ],
        }
        return request.render('mouser_theme.mouser_newest_products', values)

    @http.route(['/help/orders-shipping/gst-bill-format', '/help/orders-shipping/gst-bill-format/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_gst_bill_format(self, **kwargs):
        return request.render('mouser_theme.gst_bill_format_page', {})




    @http.route(['/help/credit-sales-and-tax', '/help/credit-sales-and-tax/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_credit_sales_tax(self, **kwargs):
        return request.render('mouser_theme.credit_sales_tax_page', {})


    @http.route(['/help/credit-sales-and-tax/methods-of-payment', '/help/credit-sales-and-tax/methods-of-payment/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_methods_of_payment(self, **kwargs):
        return request.render('mouser_theme.methods_of_payment_page', {})








    @http.route(['/help/credit-sales-and-tax/sales-tax', '/help/credit-sales-and-tax/sales-tax/', '/help/sales-tax', '/help/sales-tax/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_sales_tax(self, **kwargs):
        return request.render('mouser_theme.sales_tax_page', {})



    @http.route(['/help/credit-sales-and-tax/vat-gst-consumption-tax', '/help/credit-sales-and-tax/vat-gst-consumption-tax/', '/help/credit-sales-and-tax/vat', '/help/credit-sales-and-tax/vat/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_vat_gst_consumption_tax(self, **kwargs):
        return request.render('mouser_theme.vat_gst_consumption_tax_page', {})



    @http.route(['/sales-tax-information', '/sales-tax-information/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_sales_tax_information(self, **kwargs):
        return request.render('mouser_theme.sales_tax_information_page', {})

    @http.route(['/pdfdocs/UK-Tax-Strategy.pdf'], type='http', auth='public', website=True, sitemap=False)
    def mouser_uk_tax_strategy_pdf(self, **kwargs):
        return request.redirect('/mouser_theme/static/pdfdocs/UK-Tax-Strategy.pdf')


    @http.route([
        '/pdfDocs/taxforms/<path:filename>',
        '/pdfdocs/taxforms/<path:filename>',
    ], type='http', auth='public', website=True, sitemap=False)
    def mouser_taxforms_pdf(self, filename=None, **kwargs):
        """Serve Mouser tax form PDFs using the same URL style as original Mouser."""
        if not filename or '..' in filename or filename.startswith(('/', '\\')):
            return request.not_found()

        pdf_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'static', 'pdfdocs', 'taxforms', filename
        ))
        taxforms_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'static', 'pdfdocs', 'taxforms'
        ))

        if (not pdf_path.startswith(taxforms_dir)) or (not os.path.isfile(pdf_path)):
            # Forgiving fallback for Mouser-style PDF names: browsers/Odoo may decode
            # %20 to spaces and older links may use hyphenated or shortened names.
            requested = os.path.basename(filename).lower().replace('-', ' ').replace('_', ' ')
            requested = ' '.join(requested.split())
            matched_path = None
            for existing in os.listdir(taxforms_dir):
                normalized = existing.lower().replace('-', ' ').replace('_', ' ')
                normalized = ' '.join(normalized.split())
                if normalized == requested:
                    matched_path = os.path.join(taxforms_dir, existing)
                    break
            if not matched_path:
                aliases = {
                    'wa exemption form.pdf': 'WA-TaxExempt.pdf',
                    'washington tax exemption certificate.pdf': 'WA-TaxExempt.pdf',
                    'wv resale and exemption form.pdf': 'West Virginia Streamlined Sales Tax Agreement Certificate of Exemption.pdf',
                    'westvirginiaresaleexemption.pdf': 'West Virginia Streamlined Sales Tax Agreement Certificate of Exemption.pdf',
                }
                alias_name = aliases.get(requested)
                if alias_name:
                    candidate = os.path.join(taxforms_dir, alias_name)
                    if os.path.isfile(candidate):
                        matched_path = candidate
            if not matched_path:
                return request.not_found()
            pdf_path = matched_path

        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()

        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="%s"' % os.path.basename(filename)),
            ('Content-Length', str(len(pdf_data))),
        ]
        return request.make_response(pdf_data, headers=headers)

    @http.route(['/creditapplication', '/creditapplication/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_credit_application_landing(self, **kwargs):
        return request.render('mouser_theme.credit_application_landing_page', {})


    @http.route(['/creditapplication/ApplicationForCredit', '/creditapplication/ApplicationForCredit/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_credit_application_form(self, **kwargs):
        return request.render('mouser_theme.credit_application_form_page', {})



    @http.route(['/accessibility', '/accessibility/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_accessibility_statement(self, **kwargs):
        return request.render('mouser_theme.accessibility_statement_page', {})

    @http.route(['/privacypolicy', '/privacypolicy/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_privacy_policy_custom(self, **kwargs):
        return request.render('mouser_theme.privacy_policy_page', {})

    @http.route([
        '/about-tti',
        '/about-tti/',
        '/technical-roadshow',
        '/technical-roadshow/',
        '/quality',
        '/quality/',
        '/new/amphenol',
        '/new/amphenol/',
        '/new/te-connectivity',
        '/new/te-connectivity/',
        '/solutions/industrial-automation',
        '/solutions/industrial-automation/',
    ], type='http', auth='public', website=True, sitemap=True)
    def mouser_home_promo_page(self, **kwargs):
        path = request.httprequest.path.rstrip('/') or '/'
        if path == '/about-tti':
            return request.render('mouser_theme.about_tti_original_page', {})
        if path == '/quality':
            return request.render('mouser_theme.quality_original_page', {})
        if path == '/technical-roadshow':
            return request.render('mouser_theme.technical_roadshow_original_page', {})
        pages = {
            '/technical-roadshow': {'title': 'Technical Roadshow 2026', 'subtitle': 'Join Mouser at Technical Roadshow', 'image': '/mouser_theme/static/src/img/technical_roadshow_hero.png', 'text': 'Discover the newest products and engineering solutions with Mouser. Dates: June 12 - July 3. Locations: Pune, Bengaluru, Chennai.', 'button': 'Back to Homepage', 'button_url': '/mouser-home'},
            '/quality': {'title': 'Trust the Source. Choose Mouser.', 'subtitle': 'Quality, reliability, and authentic components.', 'image': '/mouser_theme/static/src/img/hero_trust.png', 'text': 'Mouser helps engineers source genuine electronic components from trusted manufacturers.', 'button': 'Back to Homepage', 'button_url': '/mouser-home'},
            '/about-tti': {'title': 'The TTI Family of Specialists', 'subtitle': 'Trust the source. Choose Mouser.', 'image': '/mouser_theme/static/src/img/hero_trust.png', 'text': 'TTI and Mouser help engineers source genuine electronic components from trusted manufacturers.', 'button': 'Back to Homepage', 'button_url': '/mouser-home'},
            '/new/te-connectivity': {'title': 'Authorized Source for TE Connectivity Products', 'subtitle': 'Explore TE Connectivity components and interconnect solutions.', 'image': '/mouser_theme/static/src/img/hero_te.png', 'text': 'Find TE Connectivity parts for electronic designs, prototyping, and production workflows.', 'button': 'Back to Homepage', 'button_url': '/mouser-home'},
            '/new/amphenol': {'title': 'Broadest Portfolio of Amphenol Products', 'subtitle': 'Explore Amphenol connectors, antennas, sensors, and interconnect solutions.', 'image': '/mouser_theme/static/src/img/hero_amphenol.png', 'text': 'Find Amphenol parts for electronic designs, prototyping, and production workflows.', 'button': 'Back to Homepage', 'button_url': '/mouser-home'},
            '/solutions/industrial-automation': {'title': 'Industrial Automation Made Simple', 'subtitle': 'Smart factory devices and technologies.', 'image': '/mouser_theme/static/src/img/hero_industrial.png', 'text': 'Explore automation products and solutions for connected industrial systems.', 'button': 'Back to Homepage', 'button_url': '/mouser-home'},
        }
        return request.render('mouser_theme.home_promo_detail_page', pages.get(path, pages['/technical-roadshow']))


    @http.route(['/cs/localsites', '/cs/localsites/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_local_sites(self, **kwargs):
        values = {
            'regions': [
                {'title': 'Africa, India and Middle East', 'countries': [
                    {'flag': '🇮🇳', 'name': 'India', 'currencies': ['INR', 'USD']},
                    {'flag': '🇮🇱', 'name': 'Israel', 'currencies': ['USD', 'ILS']},
                    {'flag': '🇿🇦', 'name': 'South Africa', 'currencies': ['USD', 'EUR', 'ZAR', 'GBP']},
                    {'flag': '🇹🇷', 'name': 'Turkey', 'currencies': ['EUR', 'USD']},
                ]},
                {'title': 'Americas', 'countries': [
                    {'flag': '🇺🇸', 'name': 'United States', 'currencies': ['USD']},
                    {'flag': '🇦🇷', 'name': 'Argentina', 'currencies': ['ARS', 'USD']},
                    {'flag': '🇧🇷', 'name': 'Brazil', 'currencies': ['USD']},
                    {'flag': '🇨🇦', 'name': 'Canada', 'currencies': ['CAD', 'USD']},
                    {'flag': '🇨🇱', 'name': 'Chile', 'currencies': ['CLP', 'USD']},
                    {'flag': '🇨🇴', 'name': 'Colombia', 'currencies': ['COP', 'USD']},
                    {'flag': '🇨🇷', 'name': 'Costa Rica', 'currencies': ['CRC', 'USD']},
                    {'flag': '🇩🇴', 'name': 'Dominican Republic', 'currencies': ['USD']},
                    {'flag': '🇪🇨', 'name': 'Ecuador', 'currencies': ['USD']},
                    {'flag': '🇬🇹', 'name': 'Guatemala', 'currencies': ['USD']},
                    {'flag': '🇭🇳', 'name': 'Honduras', 'currencies': ['USD']},
                    {'flag': '🇲🇽', 'name': 'Mexico', 'currencies': ['USD']},
                    {'flag': '🇵🇪', 'name': 'Peru', 'currencies': ['PEN', 'USD']},
                    {'flag': '🇵🇷', 'name': 'Puerto Rico', 'currencies': ['USD']},
                    {'flag': '🇺🇾', 'name': 'Uruguay', 'currencies': ['UYU', 'USD']},
                ]},
                {'title': 'Asia/Pacific', 'countries': [
                    {'flag': '🇦🇺', 'name': 'Australia', 'currencies': ['AUD', 'USD']},
                    {'flag': '🇨🇳', 'name': 'China', 'currencies': ['RMB', 'USD']},
                    {'flag': '🇭🇰', 'name': 'Hong Kong', 'currencies': ['HKD', 'USD']},
                    {'flag': '🇮🇩', 'name': 'Indonesia', 'currencies': ['IDR', 'USD']},
                    {'flag': '🇯🇵', 'name': 'Japan', 'currencies': ['JPY', 'USD']},
                    {'flag': '🇰🇷', 'name': 'Korea, Republic of', 'currencies': ['KRW', 'USD']},
                    {'flag': '🇲🇾', 'name': 'Malaysia', 'currencies': ['MYR', 'USD']},
                    {'flag': '🇳🇿', 'name': 'New Zealand', 'currencies': ['NZD', 'USD']},
                    {'flag': '🇵🇭', 'name': 'Philippines', 'currencies': ['PHP', 'USD']},
                    {'flag': '🇸🇬', 'name': 'Singapore', 'currencies': ['SGD', 'USD']},
                    {'flag': '🇹🇼', 'name': 'Taiwan', 'currencies': ['TWD', 'USD']},
                    {'flag': '🇹🇭', 'name': 'Thailand', 'currencies': ['THB', 'USD']},
                    {'flag': '🇻🇳', 'name': 'Vietnam', 'currencies': ['USD']},
                ]},
                {'title': 'Europe', 'countries': [
                    {'flag': '🇦🇹', 'name': 'Austria', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇧🇪', 'name': 'Belgium', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇧🇬', 'name': 'Bulgaria', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇭🇷', 'name': 'Croatia', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇨🇿', 'name': 'Czech Republic', 'currencies': ['CZK', 'EUR', 'USD']},
                    {'flag': '🇩🇰', 'name': 'Denmark', 'currencies': ['DKK', 'EUR', 'USD']},
                    {'flag': '🇪🇪', 'name': 'Estonia', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇫🇮', 'name': 'Finland', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇫🇷', 'name': 'France', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇩🇪', 'name': 'Germany', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇬🇷', 'name': 'Greece', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇭🇺', 'name': 'Hungary', 'currencies': ['HUF', 'EUR', 'USD']},
                    {'flag': '🇮🇪', 'name': 'Ireland', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇮🇹', 'name': 'Italy', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇱🇻', 'name': 'Latvia', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇱🇮', 'name': 'Liechtenstein', 'currencies': ['CHF', 'EUR', 'USD']},
                    {'flag': '🇱🇹', 'name': 'Lithuania', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇱🇺', 'name': 'Luxembourg', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇳🇱', 'name': 'Netherlands', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇳🇴', 'name': 'Norway', 'currencies': ['NOK', 'EUR', 'USD']},
                    {'flag': '🇵🇱', 'name': 'Poland', 'currencies': ['PLN', 'EUR', 'USD']},
                    {'flag': '🇵🇹', 'name': 'Portugal', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇷🇴', 'name': 'Romania', 'currencies': ['RON', 'EUR', 'USD']},
                    {'flag': '🇸🇰', 'name': 'Slovakia', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇪🇸', 'name': 'Spain', 'currencies': ['EUR', 'USD']},
                    {'flag': '🇸🇪', 'name': 'Sweden', 'currencies': ['SEK', 'EUR', 'USD']},
                    {'flag': '🇨🇭', 'name': 'Switzerland', 'currencies': ['CHF', 'EUR', 'USD']},
                    {'flag': '🇬🇧', 'name': 'United Kingdom', 'currencies': ['GBP', 'EUR', 'USD']},
                ]},
            ]
        }
        return request.render('mouser_theme.mouser_local_sites_page', values)

    @http.route(['/services-tools', '/servicesandtools/'], type='http', auth='public', website=True, sitemap=True)
    def services_tools(self, **kwargs):
        values = {
            'top_tools': [
                {'title': 'BOM Tool', 'img': '/mouser_theme/static/img/st-bom.jpg', 'img_class': 'bom-logo', 'url': '/services-tools/login?redirect=/services-tools/bom'},
                {'title': 'Price and Availability Assistant', 'img': '/mouser_theme/static/img/st-paa.png', 'img_class': '', 'url': '/services-tools/price-availability'},
                {'title': 'Project Manager', 'img': '/mouser_theme/static/img/st-project-manager.png', 'img_class': '', 'url': '/services-tools/login?redirect=/services-tools/project-manager'},
                {'title': 'APIs', 'img': '/mouser_theme/static/img/st-api.png', 'img_class': '', 'url': '/services-tools/apis'},
                {'title': 'Cart/Project share', 'img': '/mouser_theme/static/img/st-share.png', 'img_class': '', 'url': '/services-tools/cart-share'},
                {'title': 'Request a Quote', 'img': '/mouser_theme/static/img/st-quote.png', 'img_class': '', 'url': '/services-tools/request-quote'},
            ],
            'design_tools': [
                {'title': 'BOM Tool', 'img': '/mouser_theme/static/img/st-bom.jpg', 'url': '/services-tools/login?redirect=/services-tools/bom', 'desc': "Our self-service BOM tool lets you import parts straight from your files. View price and availability for your parts with confidence."},
                {'title': 'Basket / Project Share', 'img': '/mouser_theme/static/img/st-share.png', 'url': '/services-tools/cart-share', 'desc': 'Share and collaborate on your part lists with colleagues. Generate link sharing here.'},
                {'title': 'Project Manager', 'img': '/mouser_theme/static/img/st-project-manager.png', 'url': '/services-tools/login?redirect=/services-tools/project-manager', 'desc': 'Create projects and keep track of ordered parts, price, and availability for each item.'},
                {'title': 'ECAD Design Library', 'img': '/mouser_theme/static/img/st-ecad.png', 'url': '/services-tools/ecad-library', 'desc': 'Download schematic symbols, PCB footprints and 3D models into your preferred design tool.'},
                {'title': 'Conversion Calculators', 'img': '/mouser_theme/static/img/st-calculator.png', 'url': '/services-tools/conversion-calculators', 'desc': 'Get quick resources while designing with our suite of calculator tools.'},
            ],
            'purchase_tools': [
                {'title': 'Price and Availability Assistant', 'img': '/mouser_theme/static/img/st-paa.png', 'url': '/services-tools/price-availability', 'desc': 'Upload your data for a fast and accurate view of prices and stock.'},
                {'title': 'Request a Quote', 'img': '/mouser_theme/static/img/st-quote.png', 'url': '/services-tools/request-quote', 'desc': 'Let our expert team take care of your part list using our quote form.'},
                {'title': 'Scheduled Orders', 'img': '/mouser_theme/static/img/st-schedule.png', 'url': '/services-tools/scheduled-orders', 'desc': 'Purchase products upfront and meet your requested delivery schedule.'},
                {'title': 'Part List Import Tool', 'img': '/mouser_theme/static/img/st-part-import.webp', 'url': '/services-tools/login?redirect=/services-tools/part-list-import', 'desc': 'Bulk add parts to your basket for faster checkout.'},
            ],
            'business_tools': [
                {'title': 'APIs', 'img': '/mouser_theme/static/img/st-api.png', 'url': '/services-tools/apis', 'desc': 'Plug in our API services to make your process more efficient.'},
                {'title': 'Order Automation', 'img': '/mouser_theme/static/img/st-automation.png', 'url': '/services-tools/order-automation', 'desc': 'Process, track, and archive orders through one secure centralized platform.'},
            ],
            'productivity_tools': [
                {'title': 'Subscription Centre', 'img': '/mouser_theme/static/img/st-subscription.png', 'url': '/services-tools/subscription-centre', 'desc': "Subscribe to Mouser's technical newsletters."},
            ],
        }
        return request.render('mouser_theme.services_tools_page', values)

    @http.route(['/services-tools/login', '/MyAccount/MouserLogin'], type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def services_tools_login(self, redirect=None, qs=None, **post):
        """Mouser-styled login page. Handles redirect back after login."""
        message = False
        # Determine where to redirect after successful login
        redirect_url = redirect or '/mouser-home'
        if request.httprequest.method == 'POST':
            login = post.get('login', '').strip()
            password = post.get('password', '').strip()
            if login and password:
                # Attempt real Odoo authentication
                try:
                    credentials = {
                        'login': login,
                        'password': password,
                        'type': 'password'
                    }
                    uid = request.session.authenticate(request.db, credentials)
                    if uid:
                        return request.redirect(redirect_url)
                except Exception:
                    pass
            message = 'Invalid username or password. Please try again.'
        return request.render('mouser_theme.services_tools_login_page', {
            'redirect': redirect_url,
            'message': message,
        })




    @http.route(['/MyAccount/RetrieveUserName', '/retrieve-username'], type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def retrieve_username(self, **post):
        """Forgot Username page - matching mouser.in /MyAccount/RetrieveUserName"""
        message = False
        success = False
        if request.httprequest.method == 'POST':
            email = post.get('email', '').strip()
            if email:
                success = True
                message = 'If an account exists for %s, your username will be emailed to you.' % email
            else:
                message = 'Please enter a valid email address.'
        return request.render('mouser_theme.forgot_username_page', {
            'message': message,
            'success': success,
        })

    @http.route(['/MyAccount/RetrievePassword', '/retrieve-password'], type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def retrieve_password(self, **post):
        """Forgot Password page - matching mouser.in /MyAccount/RetrievePassword"""
        message = False
        success = False
        if request.httprequest.method == 'POST':
            email = post.get('email', '').strip()
            if email:
                success = True
                message = 'If an account exists for %s, a password reset link will be emailed to you.' % email
            else:
                message = 'Please enter a valid email address.'
        return request.render('mouser_theme.forgot_password_page', {
            'message': message,
            'success': success,
        })

    @http.route(['/account/orders', '/account/orders/'], type='http', auth='public', website=True, sitemap=False)
    def account_orders(self, **kwargs):
        """Order History - Mouser-styled page. Redirects to login if not authenticated."""
        if request.env.user and request.env.user.id and not request.env.user._is_public():
            # Logged in — fetch their sale orders
            orders = request.env['sale.order'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', 'in', ['sale', 'done', 'cancel']),
            ], order='date_order desc', limit=50)
            return request.render('mouser_theme.account_orders_page', {
                'orders': orders,
                'user': request.env.user,
            })
        # Not logged in → redirect to Mouser login with redirect back
        return request.redirect('/MyAccount/MouserLogin?redirect=/account/orders')

    @http.route(['/web/signup', '/MyAccount/Create', '/signup'], type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def mouser_signup_page(self, **post):
        """Mouser-styled registration page matching mouser.in /MyAccount/Create"""
        message = False
        success = False

        if request.httprequest.method == 'POST':
            firstname  = post.get('firstname', '').strip()
            lastname   = post.get('lastname', '').strip()
            email      = post.get('email', '').strip()
            login      = post.get('login', '').strip()
            password   = post.get('password', '').strip()
            confirm_pw = post.get('confirm_password', '').strip()

            # Validation
            if not all([firstname, lastname, email, login, password, confirm_pw]):
                message = 'All fields are mandatory. Please fill in the complete form.'
            elif password != confirm_pw:
                message = 'Passwords do not match. Please re-enter your password.'
            elif len(password) < 6:
                message = 'Password must be at least 6 characters long.'
            else:
                try:
                    # Check if login/email already exists
                    existing = request.env['res.users'].sudo().search([
                        '|', ('login', '=', login), ('email', '=', email)
                    ], limit=1)
                    if existing:
                        message = 'An account with this username or email already exists.'
                    else:
                        # Create new Odoo user
                        name = '%s %s' % (firstname, lastname)
                        new_user = request.env['res.users'].sudo().create({
                            'name': name,
                            'login': login,
                            'email': email,
                            'password': password,
                            'groups_id': [(6, 0, [
                                request.env.ref('base.group_portal').id
                            ])],
                        })
                        if new_user:
                            # Auto-login the new user
                            uid = request.session.authenticate(
                                request.env.cr.dbname, login, password
                            )
                            if uid:
                                return request.redirect('/mouser-home')
                            success = True
                            message = 'Account created successfully! You can now log in.'
                except Exception as e:
                    message = 'Registration failed. Please try again or contact support.'

        return request.render('mouser_theme.mouser_register_page', {
            'message': message,
            'success': success,
        })



    @http.route(['/privacy', '/privacy/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_privacy_page(self, **kwargs):
        return request.render('mouser_theme.mouser_privacy_page', {})

    @http.route(['/saleterms', '/saleterms/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_sale_terms_page(self, **kwargs):
        return request.render('mouser_theme.mouser_sale_terms_page', {})

    @http.route(['/feedback', '/feedback/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_feedback_page(self, **kwargs):
        return request.render('mouser_theme.mouser_feedback_page', {})

    @http.route(['/feedback/thanks'], type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def mouser_feedback_thanks_page(self, **kwargs):
        return request.render('mouser_theme.mouser_feedback_thanks_page', {})

    @http.route(['/contact', '/contact/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_contact_page(self, **kwargs):
        return request.render('mouser_theme.mouser_contact_original_page', {})

    @http.route([
        '/services-tools/bom',
        '/services-tools/project-manager',
        '/services-tools/part-list-import',
    ], type='http', auth='public', website=True, sitemap=False)
    def services_tools_protected(self, **kwargs):
        if request.env.user._is_public():
            return request.redirect('/services-tools/login?redirect=' + request.httprequest.path)
        return self.services_tools_tool_page(**kwargs)

    @http.route(['/api', '/api/', '/api-hub', '/api-hub/', '/services-tools/apis', '/services-tools/apis/'], type='http', auth='public', website=True, sitemap=True)
    def api_hub(self, **kwargs):
        return request.render('mouser_theme.api_hub_page')

    @http.route([
        '/services-tools/price-availability',
        '/services-tools/request-quote',
        '/services-tools/cart-share',
        '/tools/projectcartsharing/',
        '/tools/projectcartsharing',
        '/services-tools/ecad-library',
        '/services-tools/conversion-calculators',
        '/services-tools/scheduled-orders',
        '/services-tools/order-automation',
        '/services-tools/subscription-centre',
        '/services-tools/subscription-center',
    ], type='http', auth='public', website=True, sitemap=False)
    def services_tools_tool_page(self, **kwargs):
        key = request.httprequest.path.rstrip('/').split('/')[-1]
        tool_data = {
            'bom': ('BOM Tool', 'Import your bill of materials, review availability, and prepare your parts list.'),
            'project-manager': ('Project Manager', 'Save part lists, organize projects, and collaborate with your team.'),
            'cart-share': ('Cart / Project Share', 'Share carts and project lists with colleagues for review and ordering.'),
            'request-quote': ('Request a Quote', 'Submit your part list and get help with quotation and purchasing.'),
            'scheduled-orders': ('Scheduled Orders', 'Plan orders and delivery schedules for your projects.'),
            'part-list-import': ('Part List Import Tool', 'Bulk add part numbers to your basket for faster checkout.'),
            'price-availability': ('Price and Availability Assistant', 'Check pricing and availability for multiple parts quickly.'),
            'apis': ('APIs', 'Connect product, pricing, and inventory information with your systems.'),
            'ecad-library': ('ECAD Design Library', 'Find schematic symbols, PCB footprints, and 3D models.'),
            'conversion-calculators': ('Conversion Calculators', 'Use engineering calculators and quick conversion tools.'),
            'order-automation': ('Order Automation', 'Automate purchasing workflows and order tracking.'),
            'subscription-centre': ('Subscription Centre', 'Manage newsletters and technical updates.'),
        }
        if key == 'price-availability':
            return request.render('mouser_theme.price_availability_assistant_page')
        if key == 'request-quote':
            return request.render('mouser_theme.quote_request_page')
        if key == 'apis':
            return request.render('mouser_theme.api_hub_page')
        if key == 'ecad-library':
            return request.render('mouser_theme.ecad_design_library_page')
        if key == 'conversion-calculators':
            return request.render('mouser_theme.conversion_calculators_page')
        if key == 'scheduled-orders':
            return request.render('mouser_theme.scheduled_orders_help_page')
        if key == 'order-automation':
            return request.render('mouser_theme.order_automation_page')
        if key in ('subscription-centre', 'subscription-center', 'signup'):
            return request.render('mouser_theme.subscription_centre_page')
        if key in ('cart-share', 'projectcartsharing') or request.httprequest.path.rstrip('/') in ['/tools/projectcartsharing']:
            return request.render('mouser_theme.project_basket_sharing_page')

        title, description = tool_data.get(key, ('Mouser Tool', 'This tool page is available in your custom module.'))
        return request.render('mouser_theme.services_tool_detail_page', {
            'tool_title': title,
            'tool_description': description,
        })


    @http.route(['/pdfDocs/Authorization_Letter.pdf', '/pdfdocs/Authorization_Letter.pdf'], type='http', auth='public', website=True, sitemap=False)
    def mouser_authorization_letter_pdf(self, **kwargs):
        pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'pdfdocs', 'Authorization_Letter.pdf'))
        if not os.path.isfile(pdf_path):
            return request.not_found()
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="Authorization_Letter.pdf"'),
            ('Content-Length', str(len(pdf_data))),
        ]
        return request.make_response(pdf_data, headers=headers)


    @http.route(['/pdfDocs/SO-B0-xxx-DS-1223-EN-01.pdf', '/pdfdocs/SO-B0-xxx-DS-1223-EN-01.pdf'], type='http', auth='public', website=True, sitemap=False)
    def mouser_sensore_so_b0_pdf(self, **kwargs):
        pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'pdfdocs', 'SO-B0-xxx-DS-1223-EN-01.pdf'))
        if not os.path.isfile(pdf_path):
            return request.not_found()
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="SO-B0-xxx-DS-1223-EN-01.pdf"'),
            ('Content-Length', str(len(pdf_data))),
        ]
        return request.make_response(pdf_data, headers=headers)

    @http.route(['/pdfDocs/SO-B1-xxx-DS-1223-EN-01.pdf', '/pdfdocs/SO-B1-xxx-DS-1223-EN-01.pdf'], type='http', auth='public', website=True, sitemap=False)
    def mouser_sensore_so_b1_pdf(self, **kwargs):
        pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'pdfdocs', 'SO-B1-xxx-DS-1223-EN-01.pdf'))
        if not os.path.isfile(pdf_path):
            return request.not_found()
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="SO-B1-xxx-DS-1223-EN-01.pdf"'),
            ('Content-Length', str(len(pdf_data))),
        ]
        return request.make_response(pdf_data, headers=headers)

    @http.route(['/ecia', '/ecia/', '/ecia-member', '/ecia-member/', '/ecia-authorised', '/ecia-authorised/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_ecia_page(self, **kwargs):
        return request.render('mouser_theme.ecia_authorised_page', {})

    @http.route(['/ecia-video', '/ecia-video/'], type='http', auth='public', website=True, sitemap=False)
    def mouser_ecia_video_page(self, **kwargs):
        return request.render('mouser_theme.ecia_authorised_page', {})


    # ─── Electronic Components Page ───────────────────────────────────────────
    @http.route(['/electronic-components', '/electronic-components/'], type='http', auth='public', website=True, sitemap=True)
    def electronic_components(self, **kwargs):
        """Full electronic-components category directory, mirroring mouser.in/electronic-components/"""
        categories = [
            {
                'name': 'Semiconductors',
                'url': '/c/semiconductors/',
                'subcategories': [
                    {'name': 'Discrete Semiconductors', 'url': '/c/discrete-semiconductors/'},
                    {'name': 'Embedded Processors & Controllers', 'url': '/c/embedded-processors-controllers/'},
                    {'name': 'Integrated Circuits - ICs', 'url': '/c/integrated-circuits-ics/'},
                    {'name': 'Memory ICs', 'url': '/c/memory-ics/'},
                    {'name': 'Wireless & RF Semiconductors', 'url': '/c/wireless-rf-semiconductors/'},
                ],
            },
            {
                'name': 'Circuit Protection',
                'url': '/c/circuit-protection/',
                'subcategories': [
                    {'name': 'Circuit Breakers & Accessories', 'url': '/c/circuit-breakers/'},
                    {'name': 'Circuit Protection Kits', 'url': '/c/circuit-protection-kits/'},
                    {'name': 'ESD Protection Diodes / TVS Diodes', 'url': '/c/esd-protection/'},
                    {'name': 'Fuse Holders', 'url': '/c/fuse-holders/'},
                    {'name': 'Fuses', 'url': '/c/fuses/'},
                    {'name': 'Gas Discharge Tubes - GDTs / Gas Plasma Arrestors', 'url': '/c/gas-discharge-tubes/'},
                    {'name': 'LED Protection Devices', 'url': '/c/led-protection/'},
                    {'name': 'Meter Sockets', 'url': '/c/meter-sockets/'},
                    {'name': 'Panelboards & Load Centre Accessories', 'url': '/c/panelboards/'},
                    {'name': 'Panelboards & Load Centres', 'url': '/c/panelboards-load-centres/'},
                    {'name': 'Power Outlet Strips', 'url': '/c/power-outlet-strips/'},
                    {'name': 'Resettable Fuses - PPTC', 'url': '/c/resettable-fuses/'},
                    {'name': 'Surge Protective Devices - SPD', 'url': '/c/surge-protection/'},
                    {'name': 'Thermal Cut-offs', 'url': '/c/thermal-cutoffs/'},
                    {'name': 'Thermistors', 'url': '/c/thermistors/'},
                    {'name': 'Thyristors', 'url': '/c/thyristors/'},
                    {'name': 'Varistors', 'url': '/c/varistors/'},
                ],
            },
            {
                'name': 'Connectors',
                'url': '/c/connectors/',
                'subcategories': [
                    {'name': 'Audio & Video Connectors', 'url': '/c/audio-video-connectors/'},
                    {'name': 'Automotive Connectors', 'url': '/c/automotive-connectors/'},
                    {'name': 'Backplane Connectors', 'url': '/c/backplane-connectors/'},
                    {'name': 'Board to Board & Mezzanine Connectors', 'url': '/c/board-to-board/'},
                    {'name': 'Cable Assemblies', 'url': '/c/cable-assemblies/'},
                    {'name': 'Card Edge Connectors', 'url': '/c/card-edge-connectors/'},
                    {'name': 'Circular Connectors', 'url': '/c/circular-connectors/'},
                    {'name': 'Contact Probes', 'url': '/c/contact-probes/'},
                    {'name': 'D-Sub Connectors', 'url': '/c/d-sub-connectors/'},
                    {'name': 'Data Bus Components', 'url': '/c/data-bus/'},
                    {'name': 'EV Connectors', 'url': '/c/ev-connectors/'},
                    {'name': 'FFC / FPC', 'url': '/c/ffc-fpc/'},
                    {'name': 'Fibre Optic Connectors', 'url': '/c/fibre-optic-connectors/'},
                    {'name': 'Fibre Optic MIL Spec Connectors', 'url': '/c/fibre-optic-mil/'},
                    {'name': 'Headers & Wire Housings', 'url': '/c/headers-wire-housings/'},
                    {'name': 'I/O Connectors', 'url': '/c/io-connectors/'},
                    {'name': 'IC & Component Sockets', 'url': '/c/ic-sockets/'},
                    {'name': 'IEEE 1394 Connectors', 'url': '/c/ieee-1394/'},
                    {'name': 'Junction Systems', 'url': '/c/junction-systems/'},
                    {'name': 'Lighting Connectors', 'url': '/c/lighting-connectors/'},
                    {'name': 'Memory Connectors', 'url': '/c/memory-connectors/'},
                    {'name': 'MIL-Spec / MIL-Type', 'url': '/c/mil-spec/'},
                    {'name': 'Modular Connectors / Ethernet Connectors', 'url': '/c/modular-connectors/'},
                    {'name': 'Pin & Socket Connectors', 'url': '/c/pin-socket-connectors/'},
                    {'name': 'Power Connectors', 'url': '/c/power-connectors/'},
                    {'name': 'RF Interconnects', 'url': '/c/rf-interconnects/'},
                    {'name': 'Solar Connectors / Photovoltaic Connectors', 'url': '/c/solar-connectors/'},
                    {'name': 'Terminal Blocks', 'url': '/c/terminal-blocks/'},
                    {'name': 'Terminals', 'url': '/c/terminals/'},
                    {'name': 'Unspecified Connectors', 'url': '/c/unspecified-connectors/'},
                    {'name': 'USB Connectors', 'url': '/c/usb-connectors/'},
                    {'name': 'Wire & Cable', 'url': '/c/wire-cable/'},
                ],
            },
            {
                'name': 'Electromechanical',
                'url': '/c/electromechanical/',
                'subcategories': [
                    {'name': 'Audio Devices', 'url': '/c/audio-devices/'},
                    {'name': 'Circuit Breakers', 'url': '/c/circuit-breakers-em/'},
                    {'name': 'Encoders', 'url': '/c/encoders/'},
                    {'name': 'Hardware', 'url': '/c/hardware/'},
                    {'name': 'Knobs & Dials', 'url': '/c/knobs-dials/'},
                    {'name': 'Motors & Drives', 'url': '/c/motors-drives/'},
                    {'name': 'Printers', 'url': '/c/printers/'},
                    {'name': 'Relays, Contactors & Solenoids', 'url': '/c/relays/'},
                    {'name': 'Switches', 'url': '/c/switches/'},
                ],
            },
            {
                'name': 'Embedded Solutions',
                'url': '/c/embedded-solutions/',
                'subcategories': [
                    {'name': 'Accelerator Cards', 'url': '/c/accelerator-cards/'},
                    {'name': 'Audio Modules', 'url': '/c/audio-modules/'},
                    {'name': 'Computing', 'url': '/c/computing/'},
                    {'name': 'Data Conversion Modules', 'url': '/c/data-conversion/'},
                    {'name': 'Display Modules', 'url': '/c/display-modules/'},
                    {'name': 'Energy Harvesting Modules', 'url': '/c/energy-harvesting/'},
                    {'name': 'Engineering Tools', 'url': '/c/engineering-tools-em/'},
                    {'name': 'Ethernet & Communication Modules', 'url': '/c/ethernet-comms/'},
                    {'name': 'Interface Modules', 'url': '/c/interface-modules/'},
                    {'name': 'Memory & Data Storage', 'url': '/c/memory-data-storage/'},
                    {'name': 'Modules Accessories', 'url': '/c/module-accessories/'},
                    {'name': 'Other Modules', 'url': '/c/other-modules/'},
                    {'name': 'Power Management Modules', 'url': '/c/power-management-modules/'},
                    {'name': 'Sensor Modules', 'url': '/c/sensor-modules/'},
                    {'name': 'Software', 'url': '/c/software/'},
                    {'name': 'Video Modules', 'url': '/c/video-modules/'},
                    {'name': 'Wireless & RF Modules', 'url': '/c/wireless-rf-modules/'},
                ],
            },
            {
                'name': 'Enclosures',
                'url': '/c/enclosures/',
                'subcategories': [
                    {'name': 'Battery Enclosures', 'url': '/c/battery-enclosures/'},
                    {'name': 'Desktop & Rack Mount Panel Enclosures', 'url': '/c/desktop-rack-enclosures/'},
                    {'name': 'Din Rail Mount Enclosures', 'url': '/c/din-rail-enclosures/'},
                    {'name': 'Electrical Enclosure Accessories', 'url': '/c/enclosure-accessories/'},
                    {'name': 'Enclosures for Single Board Computing', 'url': '/c/sbc-enclosures/'},
                    {'name': 'Enclosures, Boxes & Cases', 'url': '/c/enclosures-boxes/'},
                    {'name': 'Floor Mounted Panel Enclosures', 'url': '/c/floor-panel-enclosures/'},
                    {'name': 'Freestanding Panel Enclosures', 'url': '/c/freestanding-enclosures/'},
                    {'name': 'Junction Boxes', 'url': '/c/junction-boxes/'},
                    {'name': 'Miniature Cases – Industrial', 'url': '/c/miniature-cases/'},
                    {'name': 'Operator Console Enclosures', 'url': '/c/operator-console/'},
                    {'name': 'Push-button Enclosures', 'url': '/c/pushbutton-enclosures/'},
                    {'name': 'Racks & Cabinets', 'url': '/c/racks-cabinets/'},
                    {'name': 'Splice Enclosures', 'url': '/c/splice-enclosures/'},
                    {'name': 'Storage Boxes & Cases', 'url': '/c/storage-boxes/'},
                    {'name': 'Wall Mounted Panel Enclosures', 'url': '/c/wall-panel-enclosures/'},
                ],
            },
            {
                'name': 'Engineering Development Tools',
                'url': '/c/engineering-development-tools/',
                'subcategories': [
                    {'name': 'Analogue & Digital IC Development Tools', 'url': '/c/ic-dev-tools/'},
                    {'name': 'Assortment Kits', 'url': '/c/assortment-kits/'},
                    {'name': 'Communication Development Tools', 'url': '/c/comm-dev-tools/'},
                    {'name': 'Development Software', 'url': '/c/dev-software/'},
                    {'name': 'Display Development Tools', 'url': '/c/display-dev-tools/'},
                    {'name': 'Embedded Processor Development Kits', 'url': '/c/embedded-dev-kits/'},
                    {'name': 'Embedded Tools & Accessories', 'url': '/c/embedded-tools/'},
                    {'name': 'Fibre Optic Development Tools', 'url': '/c/fibre-optic-dev/'},
                    {'name': 'LED Lighting Development Tools', 'url': '/c/led-dev-tools/'},
                    {'name': 'Memory IC Development Tools', 'url': '/c/memory-dev-tools/'},
                    {'name': 'Optoelectronic Development Tools', 'url': '/c/opto-dev-tools/'},
                    {'name': 'Power Management IC Development Tools', 'url': '/c/power-ic-dev-tools/'},
                    {'name': 'Programmable Logic IC Development Tools', 'url': '/c/pld-dev-tools/'},
                    {'name': 'RF / Wireless Development Tools', 'url': '/c/rf-dev-tools/'},
                    {'name': 'Security/Authentication Development Tools', 'url': '/c/security-dev-tools/'},
                    {'name': 'Sensor Development Tools', 'url': '/c/sensor-dev-tools/'},
                ],
            },
            {
                'name': 'Industrial Automation',
                'url': '/c/industrial-automation/',
                'subcategories': [
                    {'name': 'Circuit Breakers, Surge Protectors & Fuses', 'url': '/c/ia-circuit-breakers/'},
                    {'name': 'Contactors & Relays', 'url': '/c/contactors-relays/'},
                    {'name': 'Controllers', 'url': '/c/controllers/'},
                    {'name': 'Enclosures & Racks', 'url': '/c/ia-enclosures/'},
                    {'name': 'Field I/O', 'url': '/c/field-io/'},
                    {'name': 'HMI & Industrial PCs', 'url': '/c/hmi-industrial-pcs/'},
                    {'name': 'Lighting & Indication', 'url': '/c/lighting-indication/'},
                    {'name': 'Motors & Motor Drives', 'url': '/c/motors-motor-drives/'},
                    {'name': 'Network & Communications', 'url': '/c/network-comms/'},
                    {'name': 'Panel Meters', 'url': '/c/panel-meters/'},
                    {'name': 'Power Products', 'url': '/c/power-products/'},
                    {'name': 'Pushbuttons & Electromechanical Switches', 'url': '/c/pushbuttons/'},
                    {'name': 'Robotics', 'url': '/c/robotics/'},
                    {'name': 'Sensors & Transducers', 'url': '/c/sensors-transducers/'},
                    {'name': 'Terminal Blocks & Connectors', 'url': '/c/ia-terminal-blocks/'},
                    {'name': 'Thermal Management Products', 'url': '/c/thermal-mgmt-products/'},
                    {'name': 'Tools, Test Equipment & Hardware', 'url': '/c/tools-test-hardware/'},
                    {'name': 'Valves', 'url': '/c/valves/'},
                    {'name': 'Wire & Cable Assemblies', 'url': '/c/wire-cable-assemblies/'},
                    {'name': 'Wire & Cable Management', 'url': '/c/wire-cable-mgmt/'},
                ],
            },
            {
                'name': 'LED Lighting',
                'url': '/c/led-lighting/',
                'subcategories': [
                    {'name': 'LED Bulbs & Modules', 'url': '/c/led-bulbs/'},
                    {'name': 'LED Lighting Electronics', 'url': '/c/led-electronics/'},
                    {'name': 'LED Lighting Mechanical', 'url': '/c/led-mechanical/'},
                    {'name': 'LED Lighting Optics', 'url': '/c/led-optics/'},
                    {'name': 'LEDs - Light Emitting Diodes', 'url': '/c/leds/'},
                    {'name': 'Lighting Connectors', 'url': '/c/lighting-conn/'},
                ],
            },
            {
                'name': 'Opto-electronics',
                'url': '/c/opto-electronics/',
                'subcategories': [
                    {'name': 'Backlighting Components', 'url': '/c/backlighting/'},
                    {'name': 'Cameras & Accessories', 'url': '/c/cameras/'},
                    {'name': 'Displays', 'url': '/c/displays/'},
                    {'name': 'Drivers', 'url': '/c/opto-drivers/'},
                    {'name': 'Fibre Optics', 'url': '/c/fibre-optics/'},
                    {'name': 'Infrared Communications', 'url': '/c/infrared/'},
                    {'name': 'Lamps, Holders & Accessories', 'url': '/c/lamps/'},
                    {'name': 'Lasers', 'url': '/c/lasers/'},
                    {'name': 'LED Indication', 'url': '/c/led-indication/'},
                    {'name': 'LED Lighting', 'url': '/c/led-lighting-opto/'},
                    {'name': 'LEDs', 'url': '/c/leds-opto/'},
                    {'name': 'Optical Detectors & Sensors', 'url': '/c/optical-detectors/'},
                    {'name': 'Optical Switches', 'url': '/c/optical-switches/'},
                    {'name': 'Optocouplers/Photocouplers', 'url': '/c/optocouplers/'},
                ],
            },
            {
                'name': 'Passive Components',
                'url': '/c/passive-components/',
                'subcategories': [
                    {'name': 'Antenna Accessories', 'url': '/c/antenna-accessories/'},
                    {'name': 'Antennas', 'url': '/c/antennas/'},
                    {'name': 'Audio Transformers / Signal Transformers', 'url': '/c/audio-transformers/'},
                    {'name': 'Capacitors', 'url': '/c/capacitors/'},
                    {'name': 'EMI Filters / EMI Suppression', 'url': '/c/emi-filters/'},
                    {'name': 'Encoders', 'url': '/c/passive-encoders/'},
                    {'name': 'Ferrites', 'url': '/c/ferrites/'},
                    {'name': 'Filters', 'url': '/c/filters/'},
                    {'name': 'Frequency Control & Timing Devices', 'url': '/c/frequency-control/'},
                    {'name': 'Inductors, Chokes & Coils', 'url': '/c/inductors/'},
                    {'name': 'Potentiometers, Trimmers & Rheostats', 'url': '/c/potentiometers/'},
                    {'name': 'Resistors', 'url': '/c/resistors/'},
                    {'name': 'Signal Conditioning', 'url': '/c/signal-conditioning/'},
                    {'name': 'Thermistors - NTC', 'url': '/c/thermistors-ntc/'},
                    {'name': 'Thermistors - PTC', 'url': '/c/thermistors-ptc/'},
                    {'name': 'Varistors', 'url': '/c/passive-varistors/'},
                ],
            },
            {
                'name': 'Power',
                'url': '/c/power/',
                'subcategories': [
                    {'name': 'AC Power Entry Modules', 'url': '/c/ac-power-entry/'},
                    {'name': 'AC Power Leads', 'url': '/c/ac-power-leads/'},
                    {'name': 'AC Power Plugs & Receptacles', 'url': '/c/ac-plugs/'},
                    {'name': 'Batteries', 'url': '/c/batteries/'},
                    {'name': 'Battery Chargers', 'url': '/c/battery-chargers/'},
                    {'name': 'Battery Holders, Clips & Contacts', 'url': '/c/battery-holders/'},
                    {'name': 'Buffer Modules', 'url': '/c/buffer-modules/'},
                    {'name': 'DC Power Connectors', 'url': '/c/dc-power-connectors/'},
                    {'name': 'DC Power Cords', 'url': '/c/dc-power-cords/'},
                    {'name': 'DC/DC Converters', 'url': '/c/dc-dc-converters/'},
                    {'name': 'E-Mobility', 'url': '/c/e-mobility/'},
                    {'name': 'Power Condition', 'url': '/c/power-condition/'},
                    {'name': 'Power Inverters', 'url': '/c/power-inverters/'},
                    {'name': 'Power Management ICs', 'url': '/c/power-management-ics/'},
                    {'name': 'Power Supplies', 'url': '/c/power-supplies/'},
                    {'name': 'Redundancy Modules', 'url': '/c/redundancy-modules/'},
                    {'name': 'Solar Panels & Solar Cells', 'url': '/c/solar/'},
                    {'name': 'Supercapacitors', 'url': '/c/supercapacitors/'},
                    {'name': 'Transformers', 'url': '/c/transformers/'},
                ],
            },
            {
                'name': 'RF & Wireless',
                'url': '/c/rf-wireless/',
                'subcategories': [
                    {'name': 'Antennas & Accessories', 'url': '/c/antennas-accessories/'},
                    {'name': 'NFC/RFID Solutions', 'url': '/c/nfc-rfid/'},
                    {'name': 'RF / Wireless Development Tools', 'url': '/c/rf-wireless-dev/'},
                    {'name': 'RF Cables & Connectors', 'url': '/c/rf-cables/'},
                    {'name': 'RF Capacitors', 'url': '/c/rf-capacitors/'},
                    {'name': 'RF Inductors', 'url': '/c/rf-inductors/'},
                    {'name': 'RF Integrated Circuits', 'url': '/c/rf-ics/'},
                    {'name': 'RF Relays', 'url': '/c/rf-relays/'},
                    {'name': 'RF Resistors', 'url': '/c/rf-resistors/'},
                    {'name': 'RF Test Equipment', 'url': '/c/rf-test/'},
                    {'name': 'RF Transistors', 'url': '/c/rf-transistors/'},
                    {'name': 'Wireless Modules', 'url': '/c/wireless-modules/'},
                ],
            },
            {
                'name': 'Sensors',
                'url': '/c/sensors/',
                'subcategories': [
                    {'name': 'Audio Sensors', 'url': '/c/audio-sensors/'},
                    {'name': 'Barcode Readers', 'url': '/c/barcode-readers/'},
                    {'name': 'Biometric Sensors', 'url': '/c/biometric-sensors/'},
                    {'name': 'Capacitive Touch Sensors', 'url': '/c/capacitive-touch/'},
                    {'name': 'Current Sensors', 'url': '/c/current-sensors/'},
                    {'name': 'Encoders', 'url': '/c/sensor-encoders/'},
                    {'name': 'Environmental Sensors', 'url': '/c/environmental-sensors/'},
                    {'name': 'Flow Sensors', 'url': '/c/flow-sensors/'},
                    {'name': 'Flow Sensors – Industrial', 'url': '/c/flow-sensors-industrial/'},
                    {'name': 'Force Sensors & Load Cells', 'url': '/c/force-sensors/'},
                    {'name': 'Force Sensors & Load Cells - Industrial', 'url': '/c/force-sensors-industrial/'},
                    {'name': 'Level Sensors', 'url': '/c/level-sensors/'},
                    {'name': 'Linear Displacement Sensors', 'url': '/c/linear-displacement/'},
                    {'name': 'Magnetic Sensors', 'url': '/c/magnetic-sensors/'},
                    {'name': 'Motion & Position Sensors', 'url': '/c/motion-position/'},
                    {'name': 'Optical Sensors', 'url': '/c/optical-sensors/'},
                    {'name': 'Pressure Sensors', 'url': '/c/pressure-sensors/'},
                    {'name': 'Proximity Sensors', 'url': '/c/proximity-sensors/'},
                    {'name': 'Proximity Sensors - Industrial', 'url': '/c/proximity-industrial/'},
                    {'name': 'Sensor Development Tools', 'url': '/c/sensor-dev/'},
                    {'name': 'Sensor Fixings & Accessories', 'url': '/c/sensor-fixings/'},
                    {'name': 'Temperature Sensors', 'url': '/c/temperature-sensors/'},
                    {'name': 'Vision Sensors', 'url': '/c/vision-sensors/'},
                ],
            },
            {
                'name': 'Test & Measurement',
                'url': '/c/test-measurement/',
                'subcategories': [
                    {'name': 'Analysers', 'url': '/c/analysers/'},
                    {'name': 'Audio/Video Test Equipment', 'url': '/c/av-test/'},
                    {'name': 'Battery Testers', 'url': '/c/battery-testers/'},
                    {'name': 'Calibration Equipment', 'url': '/c/calibration/'},
                    {'name': 'Calibration, Warranties, & Service Plans', 'url': '/c/calibration-plans/'},
                    {'name': 'Component Testers', 'url': '/c/component-testers/'},
                    {'name': 'Data Logging & Acquisition', 'url': '/c/data-logging/'},
                    {'name': 'DC Electronic Loads', 'url': '/c/dc-loads/'},
                    {'name': 'Decade Boxes', 'url': '/c/decade-boxes/'},
                    {'name': 'Environmental Test Equipment', 'url': '/c/environmental-test/'},
                    {'name': 'Fibre Optic Testing', 'url': '/c/fibre-optic-testing/'},
                    {'name': 'Frequency Counters', 'url': '/c/frequency-counters/'},
                    {'name': 'Function Generators & Synthesisers', 'url': '/c/function-generators/'},
                    {'name': 'Insulation Testers/Megohmmeters', 'url': '/c/insulation-testers/'},
                    {'name': 'LAN/Telecom/Cable Testing', 'url': '/c/lan-testing/'},
                    {'name': 'Multimeters & Voltmeters', 'url': '/c/multimeters/'},
                    {'name': 'Oscilloscopes', 'url': '/c/oscilloscopes/'},
                    {'name': 'Panel Meters', 'url': '/c/panel-meters-test/'},
                    {'name': 'Power Supplies - Bench Top', 'url': '/c/bench-power-supplies/'},
                    {'name': 'RF Test Cables', 'url': '/c/rf-test-cables/'},
                    {'name': 'RF Test Equipment', 'url': '/c/rf-test-equip/'},
                    {'name': 'Source Measure Units - SMUs', 'url': '/c/smus/'},
                    {'name': 'Test Equipment Accessories', 'url': '/c/test-accessories/'},
                    {'name': 'Test Equipment Power Cords', 'url': '/c/test-power-cords/'},
                    {'name': 'Thermal Imaging Cameras', 'url': '/c/thermal-cameras/'},
                ],
            },
            {
                'name': 'Thermal Management',
                'url': '/c/thermal-management/',
                'subcategories': [
                    {'name': 'Fans & Blowers', 'url': '/c/fans-blowers/'},
                    {'name': 'Heat Exchangers', 'url': '/c/heat-exchangers/'},
                    {'name': 'Heat Sinks', 'url': '/c/heat-sinks/'},
                    {'name': 'LED Heat Sinks & Thermal Substrates', 'url': '/c/led-heat-sinks/'},
                    {'name': 'Liquid Cold Plates, Liquid Cooling & Heat Pipes', 'url': '/c/liquid-cooling/'},
                    {'name': 'Liquid Cooling Connectors & Accessories', 'url': '/c/liquid-cooling-conn/'},
                    {'name': 'Recirculating Chillers', 'url': '/c/chillers/'},
                    {'name': 'Temperature Sensors', 'url': '/c/temp-sensors-thermal/'},
                    {'name': 'Thermal Cut-offs', 'url': '/c/thermal-cutoffs-mgmt/'},
                    {'name': 'Thermal Interface Products', 'url': '/c/thermal-interface/'},
                    {'name': 'Thermoelectric Assemblies', 'url': '/c/thermoelectric/'},
                    {'name': 'Thermoelectric Peltier Modules', 'url': '/c/peltier-modules/'},
                    {'name': 'Thermistors', 'url': '/c/thermal-thermistors/'},
                ],
            },
            {
                'name': 'Tools & Supplies',
                'url': '/c/tools-supplies/',
                'subcategories': [
                    {'name': '3D Printing & Accessories', 'url': '/c/3d-printing/'},
                    {'name': 'Accessories', 'url': '/c/accessories/'},
                    {'name': 'Adhesive Tapes', 'url': '/c/adhesive-tapes/'},
                    {'name': 'Antistatic Control Products', 'url': '/c/antistatic/'},
                    {'name': 'Brushes', 'url': '/c/brushes/'},
                    {'name': 'Chemicals', 'url': '/c/chemicals/'},
                    {'name': 'Dry Wipes', 'url': '/c/dry-wipes/'},
                    {'name': 'Labels & Industrial Warning Signs', 'url': '/c/labels/'},
                    {'name': 'Liquid Dispensers & Bottles', 'url': '/c/liquid-dispensers/'},
                    {'name': 'Maker/DIY, Educational', 'url': '/c/maker-diy/'},
                    {'name': 'Pre-Saturated Wipes', 'url': '/c/pre-saturated-wipes/'},
                    {'name': 'Prototyping Products', 'url': '/c/prototyping/'},
                    {'name': 'Soldering', 'url': '/c/soldering/'},
                    {'name': 'Storage Boxes & Cases', 'url': '/c/storage/'},
                    {'name': 'Swabs', 'url': '/c/swabs/'},
                    {'name': 'Tools', 'url': '/c/tools/'},
                ],
            },
            {
                'name': 'Wire & Cable',
                'url': '/c/wire-cable/',
                'subcategories': [
                    {'name': 'Bus Bar Wire', 'url': '/c/bus-bar-wire/'},
                    {'name': 'Cable Assemblies', 'url': '/c/cable-assemblies-wc/'},
                    {'name': 'Coaxial Cables', 'url': '/c/coaxial-cables/'},
                    {'name': 'FFC / FPC Jumper Cables', 'url': '/c/ffc-fpc-jumper/'},
                    {'name': 'Fibre Optic', 'url': '/c/fibre-optic-wc/'},
                    {'name': 'Fibre Optic Cables', 'url': '/c/fibre-optic-cables/'},
                    {'name': 'Flat Cables', 'url': '/c/flat-cables/'},
                    {'name': 'Ground Wire & Ground Braid', 'url': '/c/ground-wire/'},
                    {'name': 'Hook-up Wire', 'url': '/c/hookup-wire/'},
                    {'name': 'Magnet Wire', 'url': '/c/magnet-wire/'},
                    {'name': 'Multi-Conductor Cables', 'url': '/c/multi-conductor/'},
                    {'name': 'Solar Cable', 'url': '/c/solar-cable/'},
                    {'name': 'Test Lead Wire', 'url': '/c/test-lead-wire/'},
                    {'name': 'Wire & Cable Management', 'url': '/c/wire-mgmt/'},
                    {'name': 'Wire Wrap Wire', 'url': '/c/wire-wrap/'},
                ],
            },
        ]

        # Fetch live total results count from Mouser API
        total_results = '1,00,08,796'  # default fallback
        try:
            import requests as req
            api_key = request.env['ir.config_parameter'].sudo().get_param('mouser_theme.mouser_api_key')
            if api_key:
                url = f"https://api.mouser.com/api/v2/search/keyword?apiKey={api_key}"
                payload = {"SearchByKeywordRequest": {"keyword": "", "records": 1, "startingRecord": 0, "searchOptions": "string"}}
                resp = req.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    n = data.get('SearchResults', {}).get('NumberOfResult', 0)
                    if n:
                        total_results = f"{int(n):,}"
        except Exception:
            pass

        return request.render('mouser_theme.electronic_components_page', {
            'categories': categories,
            'total_results': total_results,
        })


    @http.route(['/c/semiconductors', '/c/semiconductors/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_semiconductors_category(self, **kwargs):
        """Mouser-style Semiconductors category landing page."""
        return request.render('mouser_theme.mouser_semiconductors_category_page', {})

    # ─── Category product listing via Mouser API ──────────────────────────────
    # Known acronyms/abbreviations that should stay uppercase
    # ── Newest Products by Category (/new/products/) ────────────────────────

    # Map of category slug → display data for the "New by Category" grid
    _NEW_CATEGORIES = [
        {'slug': 'circuit-protection',    'name': 'Circuit Protection',    'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'connectors',            'name': 'Connectors',            'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'electromechanical',     'name': 'Electromechanical',     'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'embedded-solutions',    'name': 'Embedded Solutions',    'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'enclosures',            'name': 'Enclosures',            'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'industrial-automation', 'name': 'Industrial Automation', 'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'opto-electronics',      'name': 'Opto-electronics',      'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'passive-components',    'name': 'Passive Components',    'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'power',                 'name': 'Power',                 'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'rf-wireless',           'name': 'RF &amp; Wireless',     'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'semiconductors',        'name': 'Semiconductors',        'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'sensors',               'name': 'Sensors',               'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'test-measurement',      'name': 'Test &amp; Measurement','mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'thermal-management',    'name': 'Thermal Management',    'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'tools-supplies',        'name': 'Tools &amp; Supplies',  'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
        {'slug': 'wire-cable',            'name': 'Wire &amp; Cable',      'mouser_id': 'n-5g73', 'img': '/mouser_theme/static/img/new-by-category.webp'},
    ]

    # Category slug → real product image from static img folder
    _NEW_CAT_IMAGES = {
        'circuit-protection':    '/mouser_theme/static/img/109736695.webp',
        'connectors':            '/mouser_theme/static/img/155856283.webp',
        'electromechanical':     '/mouser_theme/static/img/192110917.webp',
        'embedded-solutions':    '/mouser_theme/static/img/139818694.webp',
        'enclosures':            '/mouser_theme/static/img/156214960.webp',
        'industrial-automation': '/mouser_theme/static/img/139020416.webp',
        'opto-electronics':      '/mouser_theme/static/img/101680247.webp',
        'passive-components':    '/mouser_theme/static/img/157597313.webp',
        'power':                 '/mouser_theme/static/img/117163481.webp',
        'rf-wireless':           '/mouser_theme/static/img/163466725.webp',
        'semiconductors':        '/mouser_theme/static/img/189044646.webp',
        'sensors':               '/mouser_theme/static/img/174707379.webp',
        'test-measurement':      '/mouser_theme/static/img/102208513.webp',
        'thermal-management':    '/mouser_theme/static/img/189521717.webp',
        'tools-supplies':        '/mouser_theme/static/img/121893047.webp',
        'wire-cable':            '/mouser_theme/static/img/112929815.webp',
    }

    @http.route(['/new/products', '/new/products/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_new_products_by_category(self, **kwargs):
        """Newest Products by Category grid page — clone of mouser.in/new/products/"""
        cats = []
        for c in self._NEW_CATEGORIES:
            cats.append({
                'slug':  c['slug'],
                'name':  c['name'],
                'url':   '/new/products/' + c['slug'],
                'img':   self._NEW_CAT_IMAGES.get(c['slug'], '/mouser_theme/static/img/new-by-category.webp'),
            })
        return request.render('mouser_theme.mouser_new_products_by_category', {
            'categories': cats,
        })

    @http.route(['/new/products/<string:cat_slug>', '/new/products/<string:cat_slug>/'], type='http', auth='public', website=True, sitemap=False)
    def mouser_new_products_category_detail(self, cat_slug, **kwargs):
        """Newest products within a specific category, fetched via Mouser Search API."""
        import requests as req

        # Find display name for the category
        cat_info = next((c for c in self._NEW_CATEGORIES if c['slug'] == cat_slug), None)
        cat_name = cat_info['name'].replace('&amp;', '&') if cat_info else cat_slug.replace('-', ' ').title()
        # Search keyword: use category name (strip HTML entities)
        search_keyword = cat_name
        page    = int(kwargs.get('page', 1))
        per_page = 25
        starting = (page - 1) * per_page

        products = []
        total    = 0
        api_error = None

        try:
            api_key = request.env['ir.config_parameter'].sudo().get_param('mouser_theme.mouser_api_key')
            if api_key:
                url = 'https://api.mouser.com/api/v2/search/keyword'
                payload = {
                    'SearchByKeywordRequest': {
                        'keyword': search_keyword,
                        'records': per_page,
                        'startingRecord': starting,
                        'searchOptions': 'New',          # show newest products
                        'searchWithYourSignUpLanguage': False,
                    }
                }
                resp = req.post(url, json=payload,
                                params={'apiKey': api_key},
                                headers={'Content-Type': 'application/json'},
                                timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    sr   = (data.get('SearchResults') or {})
                    total = int(sr.get('NumberOfResult') or 0)
                    for p in (sr.get('Parts') or []):
                        pb = (p.get('PriceBreaks') or [])
                        price_str = pb[0].get('Price', '') if pb else ''
                        products.append({
                            'manufacturer': p.get('Manufacturer', ''),
                            'mpn':          p.get('ManufacturerPartNumber', ''),
                            'mouser_no':    p.get('MouserPartNumber', ''),
                            'description':  p.get('Description', ''),
                            'availability': p.get('Availability', ''),
                            'image':        p.get('ImagePath', ''),
                            'datasheet':    p.get('DataSheetUrl', ''),
                            'detail_url':   p.get('ProductDetailUrl', '#'),
                            'price':        price_str,
                            'rohs':         p.get('ROHSStatus', ''),
                            'lifecycle':    p.get('LifecycleStatus', ''),
                        })
                else:
                    api_error = 'API error: %s' % resp.status_code
            else:
                api_error = 'API key not configured.'
        except Exception as exc:
            api_error = str(exc)

        total_pages = max(1, -(-total // per_page))
        # Build sibling category list for sidebar
        all_cats = [{'slug': c['slug'], 'name': c['name'].replace('&amp;', '&'), 'url': '/new/products/' + c['slug']} for c in self._NEW_CATEGORIES]

        return request.render('mouser_theme.mouser_new_products_category_detail', {
            'cat_name':    cat_name,
            'cat_slug':    cat_slug,
            'products':    products,
            'total':       total,
            'page':        page,
            'total_pages': total_pages,
            'per_page':    per_page,
            'api_error':   api_error,
            'all_cats':    all_cats,
            'cat_img':     self._NEW_CAT_IMAGES.get(cat_slug, '/mouser_theme/static/img/new-by-category.webp'),
        })

    _CAT_ACRONYMS = {
        'usb', 'dc', 'ac', 'ic', 'ics', 'fpga', 'mcu', 'cpu', 'rf', 'pcb',
        'led', 'lcd', 'smd', 'smt', 'emi', 'esd', 'ffc', 'fpc', 'soc',
        'dsp', 'dac', 'adc', 'spd', 'pptc', 'gdts', 'tvs', 'spld', 'cpld',
        'plc', 'hvac', 'eia', 'rohs', 'iso', 'bom'
    }

    def _smart_title(self, text):
        """Title-case a slug-derived string, keeping known acronyms uppercase."""
        words = text.split()
        result = []
        for w in words:
            if w.lower() in self._CAT_ACRONYMS:
                result.append(w.upper())
            else:
                result.append(w.capitalize())
        return ' '.join(result)

    @http.route(['/c/<path:category_slug>', '/c/<path:category_slug>/'], type='http', auth='public', website=True, sitemap=False)
    def category_products(self, category_slug, **kwargs):
        """Show products for a category using Mouser API keyword search"""
        # Use the last segment of the slug as the search keyword for better results
        # e.g. 'connectors/automotive-connectors' → 'automotive connectors'
        slug_parts = [p for p in category_slug.replace('/', ' ').split() if p]
        # Take the last meaningful segment
        last_segment = slug_parts[-1].replace('-', ' ') if slug_parts else category_slug
        keyword = kwargs.get('keyword', '') or last_segment
        page = int(kwargs.get('page', 1))
        per_page = 25
        starting = (page - 1) * per_page

        products = []
        total = 0
        error = None

        try:
            import requests as req
            api_key = request.env['ir.config_parameter'].sudo().get_param('mouser_theme.mouser_api_key')
            if api_key:
                url = f"https://api.mouser.com/api/v2/search/keyword?apiKey={api_key}"
                payload = {
                    "SearchByKeywordRequest": {
                        "keyword": keyword,
                        "records": per_page,
                        "startingRecord": starting,
                        "searchOptions": "string",
                    }
                }
                resp = req.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    sr = data.get('SearchResults', {})
                    total = int(sr.get('NumberOfResult', 0))
                    for p in sr.get('Parts', []):
                        price_str = ''
                        pb = p.get('PriceBreaks', [])
                        if pb:
                            price_str = pb[0].get('Price', '')
                        products.append({
                            'manufacturer': p.get('Manufacturer', ''),
                            'mpn': p.get('ManufacturerPartNumber', ''),
                            'mouser_no': p.get('MouserPartNumber', ''),
                            'description': p.get('Description', ''),
                            'availability': p.get('Availability', ''),
                            'image': p.get('ImagePath', ''),
                            'datasheet': p.get('DataSheetUrl', ''),
                            'detail_url': p.get('ProductDetailUrl', ''),
                            'price': price_str,
                            'rohs': p.get('ROHSStatus', ''),
                        })
                else:
                    error = f"API error: {resp.status_code}"
            else:
                error = 'API key not configured.'
        except Exception as e:
            error = str(e)

        total_pages = max(1, -(-total // per_page))  # ceiling division

        return request.render('mouser_theme.category_products_page', {
            'category_name': self._smart_title(last_segment),
            'category_slug': category_slug,
            'products': products,
            'total': total,
            'page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'keyword': keyword,
            'error': error,
        })

    @http.route(['/automation-india-expo', '/automation-india-expo/'], type='http', auth='public', website=True, sitemap=True)
    def mouser_automation_expo_2026(self, **kwargs):
        return request.render('mouser_theme.automation_expo_2026_page', {})
