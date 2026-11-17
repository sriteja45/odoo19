import requests

from odoo import api, fields, models
from odoo.exceptions import UserError


class CurrencyRateUpdate(models.Model):
    _name = "currency.rate.update"
    _description = "Currency Rate Update"

    name = fields.Char(default="Currency Rate Update")
    last_update = fields.Datetime(string="Last Updated", readonly=True)

    @api.model
    def update_currency_rates(self):
        """
        Fetch latest exchange rates from ExchangeRate API
        and update Odoo currency rates.
        """

        url = "https://open.er-api.com/v6/latest/USD"

        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()

        except Exception as e:
            raise UserError(
                f"Unable to connect to Exchange Rate API.\n\n{e}"
            )

        if data.get("result") != "success":
            raise UserError("Exchange Rate API returned an invalid response.")

        rates = data.get("rates", {})

        currencies = self.env["res.currency"].search([
            ("name", "in", list(rates.keys()))
        ])

        today = fields.Date.today()

        for currency in currencies:

            rate = rates.get(currency.name)

            if not rate:
                continue

            existing_rate = self.env["res.currency.rate"].search([
                ("currency_id", "=", currency.id),
                ("name", "=", today),
            ], limit=1)

            values = {
                "company_rate": rate,
                "inverse_company_rate": 1 / rate,
            }

            if existing_rate:
                existing_rate.write(values)
            else:
                values.update({
                    "currency_id": currency.id,
                    "name": today,
                })
                self.env["res.currency.rate"].create(values)

        record = self.search([], limit=1)

        if record:
            record.last_update = fields.Datetime.now()

        return True

    def action_update_rates(self):
        self.update_currency_rates()

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }