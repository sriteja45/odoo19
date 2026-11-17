from odoo import http
from odoo.http import request


class ComboOfferController(http.Controller):

    @http.route(
        '/combo-offers',
        auth='public',
        website=True
    )
    def combo_offers(self):

        offers = request.env[
            'combo.offer'
        ].sudo().search([
            ('active', '=', True)
        ])

        return request.render(
            'Xevoria_electronics.combo_offer_page',
            {
                'offers': offers
            }
        )