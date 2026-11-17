from odoo import models
from markupsafe import Markup
import re
from datetime import date, timedelta


class DiscussChannelExt(models.Model):
    _inherit = 'discuss.channel'

    def message_post(self, **kwargs):
        msg = super().message_post(**kwargs)

        # Only for livechat
        if self.channel_type != 'livechat':
            return msg

        body = kwargs.get('body', '')
        if not body:
            return msg

        # Only normal comment messages
        if kwargs.get('message_type') and kwargs.get('message_type') != 'comment':
            return msg

        bot_partner = self.env.ref('base.partner_root', raise_if_not_found=False)

        author_id = kwargs.get('author_id')
        author_partner = self.env['res.partner'].sudo().browse(author_id) if author_id else False

        # Skip bot own messages
        if bot_partner and author_id == bot_partner.id:
            return msg

        # Skip internal users / operators
        if author_partner and author_partner.user_ids:
            return msg

        message = self._clean_message(body)
        if not message:
            return msg

        # Skip email/system validation messages
        blocked_phrases = [
            'does not look like a valid email',
            'please try again',
            'valid email',
            'email address',
        ]
        if any(phrase in message for phrase in blocked_phrases):
            return msg

        response = self._generate_clinic_response(message)

        if response and bot_partner:
            super(DiscussChannelExt, self).message_post(
                body=Markup(response),
                author_id=bot_partner.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        return msg

    def _clean_message(self, body):
        text = re.sub(r'<[^>]+>', '', body or '')
        text = text.replace('&nbsp;', ' ')
        text = text.strip().lower()
        return text

    def _generate_clinic_response(self, message):
        message = message.lower()

        # Call history PDF filter feature
        if 'call history' in message or 'download call history' in message or 'download pdf' in message:
            return Markup("""
        <p>Select a call history range and click to download PDF:</p>

        <p><a class="btn btn-success" href="/clinic/call_history/pdf?range_key=2days" target="_blank">Last 2 Days</a></p>
        <p><a class="btn btn-success" href="/clinic/call_history/pdf?range_key=1week" target="_blank">Last 1 Week</a></p>
        <p><a class="btn btn-success" href="/clinic/call_history/pdf?range_key=10days" target="_blank">Last 10 Days</a></p>
        <p><a class="btn btn-success" href="/clinic/call_history/pdf?range_key=1month" target="_blank">Last 1 Month</a></p>
        <p><a class="btn btn-success" href="/clinic/call_history/pdf?range_key=2months" target="_blank">Last 2 Months</a></p>
        <p><a class="btn btn-success" href="/clinic/call_history/pdf?range_key=3months" target="_blank">Last 3 Months</a></p>
        <p><a class="btn btn-success" href="/clinic/call_history/pdf?range_key=6months" target="_blank">Last 6 Months</a></p>
        <p><a class="btn btn-success" href="/clinic/call_history/pdf?range_key=1year" target="_blank">Last 1 Year</a></p>
        """)
        # Clinic timings
        if 'timing' in message or 'open' in message or 'working hours' in message:
            return self._get_clinic_timings()

        # Contact info
        if 'contact' in message or 'phone' in message or 'email' in message or 'address' in message:
            return self._get_contact_info()

        # Booking help
        if 'book' in message or 'appointment' in message:
            return (
                "To book an appointment, please go to the Book Appointment page, "
                "select specialization, choose doctor, date, and available time slot, "
                "then submit the form."
            )

        # Specializations
        if 'specialization' in message or 'department' in message:
            return self._get_specializations_info()

        # Lab Tests
        if 'lab test' in message or 'tests' in message:
            return self._get_lab_tests_info()

        
        
        # Doctor availability
        if 'available' in message or 'slot' in message or 'tomorrow' in message or 'today' in message:
            return self._handle_doctor_availability(message)

        # Doctor list
        if 'doctor' in message or 'doctors' in message or 'dr' in message:
            return self._get_doctors_info()

        return (
            "Welcome to our clinic. I can help you with clinic timings, contact details, "
            "doctor information, specializations, appointment booking, and call history."
        )

    def _get_clinic_timings(self):
        timings = self.env['ir.config_parameter'].sudo().get_param(
            'clinic_appointment.clinic_timings',
            default='Monday to Saturday: 9:00 AM to 6:00 PM'
        )
        return f"Our clinic timings are: {timings}"

    def _get_contact_info(self):
        params = self.env['ir.config_parameter'].sudo()
        phone = params.get_param('clinic_appointment.contact_phone', default='Not available')
        email = params.get_param('clinic_appointment.contact_email', default='Not available')
        address = params.get_param('clinic_appointment.contact_address', default='Not available')

        return (
            f"Contact details:\n"
            f"- Phone: {phone}\n"
            f"- Email: {email}\n"
            f"- Address: {address}"
        )

    def _get_doctors_info(self):
        doctors = self.env['clinic.employee'].sudo().search([
            ('role', '=', 'doctor'),
            ('active', '=', True)
        ])
        if not doctors:
            return "Doctor information is not available right now."

        names = doctors.mapped('name')
        return "Available doctors: " + ", ".join(names)

    def _get_specializations_info(self):
        specializations = self.env['clinic.specialization'].sudo().search([])
        if not specializations:
            return "Specializations are not available right now."

        names = specializations.mapped('name')
        return "Available specializations: " + ", ".join(names)

    def _get_lab_tests_info(self):
        tests = self.env['clinic.lab.test'].sudo().search([])
        if not tests:
            return "No lab tests available."

        names = tests.mapped('name')
        return "Available lab tests:\n" + "\n".join(f"- {name}" for name in names)

    

    def _handle_doctor_availability(self, message):
        return "Please check availability on the booking page."