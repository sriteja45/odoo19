from odoo import models, fields, api


class XevoriaCurrencyConfig(models.Model):
    """
    Stores per-country currency mapping for Xevoria.
    Rates are updated via a scheduled cron job using Odoo's built-in
    res.currency system (which fetches live rates from ECB / Frankfurter API).
    """
    _name = 'xevoria.currency.config'
    _description = 'Xevoria Currency Configuration'

    country_code = fields.Char(
        string='Country Code (ISO 2)',
        required=True,
        help='e.g. IN, US, FR, DE, GB'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True
    )
    symbol = fields.Char(
        related='currency_id.symbol',
        readonly=True
    )

    _sql_constraints = [
        ('country_code_uniq', 'unique(country_code)',
         'Each country can have only one currency mapping.')
    ]
