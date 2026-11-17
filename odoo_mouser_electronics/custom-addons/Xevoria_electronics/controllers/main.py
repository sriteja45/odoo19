from odoo import http
from odoo.http import request, Response
from odoo.osv import expression
import json



class XevoriaWebsite(http.Controller):

    @http.route('/services', auth='public', website=True)
    def services(self, **kw):
        return request.render('Xevoria_electronics.services_page')

    @http.route('/about-us', auth='public', website=True)
    def about_us(self, **kw):
        return request.render('Xevoria_electronics.about_page')

    @http.route('/contact-us', auth='public', website=True)
    def contact_us(self, **kw):
         return request.redirect('/contactus')
