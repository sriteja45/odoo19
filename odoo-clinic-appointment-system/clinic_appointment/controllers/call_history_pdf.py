from odoo import http, SUPERUSER_ID, fields
from odoo.http import request
from datetime import timedelta, datetime, time
from dateutil.relativedelta import relativedelta


class CallHistoryPDFController(http.Controller):

    @http.route('/clinic/call_history/pdf', type='http', auth='public', website=True)
    def download_call_history_pdf(self, range_key=None, **kwargs):
        env = request.env(user=SUPERUSER_ID)

        now = fields.Datetime.now()
        today = datetime.combine(now.date(), time.min)

        domain = [('duration_seconds', '>', 0)]
        title = "Call History"

        if range_key == "2days":
            date_from = today - timedelta(days=1)
            domain.append(("call_datetime", ">=", date_from))
            title = "Call History - Last 2 Days"

        elif range_key == "1week":
            date_from = today - timedelta(days=6)
            domain.append(("call_datetime", ">=", date_from))
            title = "Call History - Last 1 Week"

        elif range_key == "10days":
            date_from = today - timedelta(days=9)
            domain.append(("call_datetime", ">=", date_from))
            title = "Call History - Last 10 Days"

        elif range_key == "1month":
            date_from = today - relativedelta(months=1)
            domain.append(("call_datetime", ">=", date_from))
            title = "Call History - Last 1 Month"

        elif range_key == "2months":
            date_from = today - relativedelta(months=2)
            domain.append(("call_datetime", ">=", date_from))
            title = "Call History - Last 2 Months"

        elif range_key == "3months":
            date_from = today - relativedelta(months=3)
            domain.append(("call_datetime", ">=", date_from))
            title = "Call History - Last 3 Months"

        elif range_key == "6months":
            date_from = today - relativedelta(months=6)
            domain.append(("call_datetime", ">=", date_from))
            title = "Call History - Last 6 Months"

        elif range_key == "1year":
            date_from = today - relativedelta(years=1)
            domain.append(("call_datetime", ">=", date_from))
            title = "Call History - Last 1 Year"

        records = env['clinic.call.history'].search(domain, order='call_datetime desc')

        if not records:
            return request.make_response(
                f"No Call History Available for {title}.",
                headers=[('Content-Type', 'text/plain; charset=utf-8')]
            )

        pdf, _ = env['ir.actions.report']._render_qweb_pdf(
            'clinic_appointment.action_report_clinic_call_history',
            records.ids,
            data={'report_title': title}
        )

        filename = title.replace(" ", "_") + ".pdf"

        return request.make_response(
            pdf,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )