from odoo import http
from odoo.http import request

from ..services.role_detector import RoleDetector
from ..services.intent_router import (
    detect_intent,
    detect_module,
    check_access,
    get_access_denied_message
)
from ..services.agno_agent import ClinicAgnoAgent


class ClinicChatbot(http.Controller):

    @http.route(
        '/clinic/chat/welcome',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def clinic_chat_welcome(self, **kwargs):
        return {
            "response": "Hello 👋 Welcome to our Clinic Assistant! How can I help you today?"
        }

    @http.route(
        '/clinic/chat',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def clinic_chat(self, **kwargs):

        message = (kwargs.get('message') or '').strip()

        # =====================================================
        # CUSTOM COMMANDS
        # =====================================================

        if message == '@hello':
            return {
                "response": "Hello 👋 Welcome to Clinic Assistant"
            }

        if message == '@help':
            return {
                "response": """
Available Commands:

@hello
@help
@status
@time
@date
@about
@contact
@doctorslist
@specialization
"""
            }

        if message == '@status':
            return {
                "response": "✅ Clinic Assistant is Active"
            }

        if message == '@time':
            from datetime import datetime

            current_time = datetime.now().strftime('%I:%M %p')

            return {
                "response": f"🕒 Current Time: {current_time}"
            }

        if message == '@date':
            from datetime import datetime

            current_date = datetime.now().strftime('%d-%m-%Y')

            return {
                "response": f"📅 Today's Date: {current_date}"
            }

        if message == '@about':
            return {
                "response": "🏥 This is Clinic Assistant developed in Odoo."
            }

        if message == '@contact':
            return {
                "response": "📞 Contact: +91 9876543210"
            }

        # =====================================================
        # DOCTORS LIST
        # =====================================================

        if message == '@doctorslist':

            env = request.env

            doctors = env['clinic.employee'].sudo().search([
                ('role', '=', 'doctor'),
                ('active', '=', True)
            ])

            if not doctors:
                return {
                    "response": "❌ No doctors found."
                }

            response = "👨‍⚕️ Doctors List\n\n"

            for idx, doctor in enumerate(doctors, 1):

                specialization = (
                    doctor.specialization_id.name
                    if doctor.specialization_id else 'General'
                )

                response += (
                    f"{idx}. Dr. {doctor.name}\n"
                    f"   Specialization: {specialization}\n\n"
                )

            return {
                "response": response
            }

        # =====================================================
        # SPECIALIZATION LIST
        # =====================================================

        if message == '@specialization':

            env = request.env

            specializations = env['clinic.specialization'].sudo().search([])

            if not specializations:
                return {
                    "response": "❌ No specializations found."
                }

            response = "🏥 Available Specializations\n\n"

            for idx, spec in enumerate(specializations, 1):

                response += (
                    f"{idx}. {spec.name}\n"
                )

            return {
                "response": response
            }

        # =====================================================
        # EMPTY MESSAGE CHECK
        # =====================================================

        if not message:
            return {
                "response": "Please type your question."
            }

        env = request.env
        user = env.user

        # =====================================================
        # ROLE DETECTION
        # =====================================================

        role_detector = RoleDetector()
        user_role = role_detector.detect_from_request(request)

        # =====================================================
        # INTENT & MODULE DETECTION
        # =====================================================

        intent = detect_intent(message)
        module = detect_module(message)

        # =====================================================
        # ACCESS CHECK
        # =====================================================

        if not check_access(user_role, module):
            return {
                "response": get_access_denied_message(
                    user_role,
                    module
                )
            }

        # =====================================================
        # SESSION KEY
        # =====================================================

        session_key = (
            kwargs.get('session_key')
            or request.session.sid
            or 'website_public_session'
        )

        # =====================================================
        # FIND ACTIVE SESSION
        # =====================================================

        db_session = env['clinic.chatbot.session'].sudo().search([
            ('agno_thread_id', '=', session_key),
            ('state', '=', 'active')
        ], limit=1)

        # =====================================================
        # CREATE SESSION
        # =====================================================

        if not db_session:

            db_session = env['clinic.chatbot.session'].sudo().create({
                'user_id': user.id if not user._is_public() else False,
                'visitor_name': (
                    getattr(request, 'httprequest', None)
                    and request.httprequest.remote_addr
                    or 'Website Visitor'
                ),
                'user_role': user_role,
                'active_module': module,
                'agno_thread_id': session_key,
            })

        # =====================================================
        # SAVE USER MESSAGE
        # =====================================================

        env['clinic.chatbot.message'].sudo().create({
            'session_id': db_session.id,
            'sender_type': 'user',
            'user_id': user.id if not user._is_public() else False,
            'content': message,
            'detected_module': module,
            'detected_intent': intent,
            'user_role_at_time': user_role,
        })

        # =====================================================
        # AGNO AGENT
        # =====================================================

        agent = ClinicAgnoAgent(
            env=env,
            user_role=user_role,
            session_id=session_key
        )

        result = agent.chat(message)

        bot_response = (
            result.get('response')
            or 'Sorry, I could not process that.'
        )

        # =====================================================
        # SAVE BOT RESPONSE
        # =====================================================

        env['clinic.chatbot.message'].sudo().create({
            'session_id': db_session.id,
            'sender_type': 'bot',
            'content': bot_response,
            'detected_module': module,
            'detected_intent': intent,
            'user_role_at_time': user_role,
        })

        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        return {
            "response": bot_response
        }