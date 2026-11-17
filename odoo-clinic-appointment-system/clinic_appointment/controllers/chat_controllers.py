from odoo import http, fields
from odoo.http import request
import json
import logging
import re
from datetime import date

_logger = logging.getLogger(__name__)


def _clean_name(name):
    return re.sub(r'^Dr\.?\s*', '', name or '', flags=re.IGNORECASE).strip()


def _find_available_doctor(specialization):
    """Least-busy online doctor for specialization."""
    Employee    = request.env['clinic.employee'].sudo()
    ChatSession = request.env['clinic.chat.session'].sudo()
    base        = [('role', '=', 'doctor'), ('online_status', '=', 'online')]

    candidates = Employee.browse()
    if specialization:
        candidates = Employee.search(
            base + [('specialization_id.name', 'ilike', specialization)])
    if not candidates:
        candidates = Employee.search(base)
    if not candidates:
        return None

    best, min_load = None, float('inf')
    for doc in candidates:
        load = ChatSession.search_count([('doctor_id', '=', doc.id), ('status', '=', 'active')])
        if load < min_load:
            min_load, best = load, doc
    return best


# ============================================================
#  DOCTOR CHAT CONTROLLER
# ============================================================
class DoctorChatController(http.Controller):

    @http.route('/clinic/doctor/chat/list', type='http', auth='user', website=True)
    def chat_list(self):
        user   = request.env.user
        doctor = request.env['clinic.employee'].sudo().search([
            ('user_id', '=', user.id), ('role', '=', 'doctor')
        ], limit=1)

        if not doctor:
            return "<h2>Access Denied: No doctor profile found.</h2>"

        spec_waiting = request.env['clinic.chat.session'].sudo().search([
            ('status', '=', 'waiting'),
            ('specialization', 'ilike', doctor.specialization_id.name or ''),
        ])
        if spec_waiting:
            waiting = spec_waiting
        else:
            waiting = request.env['clinic.chat.session'].sudo().search([
                ('status', '=', 'waiting')
            ])

        active = request.env['clinic.chat.session'].sudo().search([
            ('doctor_id', '=', doctor.id), ('status', '=', 'active')
        ])

        return request.render('clinic_appointment.doctor_chat_list_template', {
            'doctor':           doctor,
            'waiting_sessions': waiting,
            'active_sessions':  active,
        })

    @http.route('/clinic/doctor/chat/accept', type='json', auth='user', methods=['POST'])
    def accept_chat(self, **kwargs):
        data       = json.loads(request.httprequest.data)
        session_id = data.get('session_id')

        try:
            session_id = int(session_id)
        except (TypeError, ValueError):
            return {'error': 'Invalid session ID: %s' % session_id}

        doctor = request.env['clinic.employee'].sudo().search([
            ('user_id', '=', request.env.user.id), ('role', '=', 'doctor')
        ], limit=1)

        if not doctor:
            return {'error': 'Doctor profile not found'}
        if doctor.online_status != 'online':
            return {'error': 'You must be Online to accept chats. Click "Go Online" first.'}

        session = request.env['clinic.chat.session'].sudo().browse(session_id)
        if not session.exists():
            return {'error': 'Session not found (id=%s)' % session_id}
        if session.doctor_id:
            if session.doctor_id.id == doctor.id:
                return {'status': 'accepted', 'session_id': session.session_id}
            return {'error': 'Session already accepted by another doctor'}

        # activate=True → moves session to 'active' immediately
        session.action_assign_doctor(doctor.id, activate=True)

        return {'status': 'accepted', 'session_id': session.session_id}

    @http.route('/clinic/doctor/chat/send', type='json', auth='user', methods=['POST'])
    def send_message(self, **kwargs):
        data       = json.loads(request.httprequest.data)
        session_id = data.get('session_id')
        message    = data.get('message', '').strip()

        if not message:
            return {'error': 'Empty message'}

        doctor = request.env['clinic.employee'].sudo().search([
            ('user_id', '=', request.env.user.id), ('role', '=', 'doctor')
        ], limit=1)
        if not doctor:
            return {'error': 'Doctor not found'}

        session = request.env['clinic.chat.session'].sudo().search(
            [('session_id', '=', session_id)], limit=1)
        if not session:
            return {'error': 'Session not found'}
        if session.doctor_id.id != doctor.id:
            return {'error': 'Unauthorized'}

        request.env['clinic.chat.message'].sudo().create({
            'session_id':  session.id,
            'sender_type': 'doctor',
            'sender_name': doctor.name,
            'message':     message,
        })
        return {'status': 'sent'}

    @http.route('/clinic/doctor/chat/poll', type='json', auth='user', methods=['POST'])
    def poll_messages(self, **kwargs):
        data       = json.loads(request.httprequest.data)
        session_id = data.get('session_id')
        last_id    = int(data.get('last_id', 0))

        doctor = request.env['clinic.employee'].sudo().search([
            ('user_id', '=', request.env.user.id), ('role', '=', 'doctor')
        ], limit=1)
        if not doctor:
            return {'messages': []}

        session = request.env['clinic.chat.session'].sudo().search(
            [('session_id', '=', session_id)], limit=1)
        if not session or session.doctor_id.id != doctor.id:
            return {'messages': []}

        msgs = request.env['clinic.chat.message'].sudo().search([
            ('session_id', '=', session.id),
            ('id', '>', last_id),
            ('sender_type', 'in', ['patient', 'system']),
        ], order='create_date asc')

        return {
            'messages': [{
                'id':          m.id,
                'message':     m.message,
                'sender_name': m.sender_name or 'Patient',
                'sender_type': m.sender_type,
                'timestamp':   m.create_date.strftime('%H:%M'),
            } for m in msgs]
        }

    @http.route('/clinic/doctor/chat/end', type='json', auth='user', methods=['POST'])
    def end_chat(self, **kwargs):
        data       = json.loads(request.httprequest.data)
        session_id = data.get('session_id')

        doctor = request.env['clinic.employee'].sudo().search([
            ('user_id', '=', request.env.user.id), ('role', '=', 'doctor')
        ], limit=1)
        if not doctor:
            return {'error': 'Doctor not found'}

        session = request.env['clinic.chat.session'].sudo().search(
            [('session_id', '=', session_id)], limit=1)
        if not session or session.doctor_id.id != doctor.id:
            return {'error': 'Unauthorized'}

        session.action_end_session()
        return {'status': 'ended'}

    @http.route('/clinic/doctor/online/toggle', type='json', auth='user', methods=['POST'])
    def toggle_online(self, **kwargs):
        data      = json.loads(request.httprequest.data)
        is_online = data.get('is_online', False)
        doctor    = request.env['clinic.employee'].sudo().search([
            ('user_id', '=', request.env.user.id), ('role', '=', 'doctor')
        ], limit=1)
        if not doctor:
            return {'is_online': False}
        doctor.online_status = 'online' if is_online else 'offline'
        return {'is_online': is_online}

    @http.route('/clinic/doctor/online/status', type='json', auth='user', methods=['POST'])
    def get_online_status(self, **kwargs):
        doctor = request.env['clinic.employee'].sudo().search([
            ('user_id', '=', request.env.user.id), ('role', '=', 'doctor')
        ], limit=1)
        return {'is_online': doctor.online_status == 'online'} if doctor else {'is_online': False}

    @http.route('/clinic/doctor/chat/waiting', type='json', auth='user', methods=['POST'])
    def get_waiting_sessions(self, **kwargs):
        doctor = request.env['clinic.employee'].sudo().search([
            ('user_id', '=', request.env.user.id), ('role', '=', 'doctor')
        ], limit=1)

        if doctor and doctor.specialization_id:
            waiting = request.env['clinic.chat.session'].sudo().search([
                ('status', '=', 'waiting'),
                ('specialization', 'ilike', doctor.specialization_id.name),
            ])
            if not waiting:
                waiting = request.env['clinic.chat.session'].sudo().search([
                    ('status', '=', 'waiting')
                ])
        else:
            waiting = request.env['clinic.chat.session'].sudo().search([
                ('status', '=', 'waiting')
            ])

        return {
            'sessions': [{
                'id':             s.id,
                'session_id':     s.session_id,
                'patient_name':   s.patient_name or 'Unknown',
                'specialization': s.specialization or 'General',
            } for s in waiting]
        }


# ============================================================
#  PATIENT CHAT CONTROLLER
# ============================================================
class PatientChatController(http.Controller):

    @http.route('/clinic/patient/chat', type='http', auth='public', website=True)
    def chat_page(self):
        specializations = request.env['clinic.specialization'].sudo().search([])
        return request.render('clinic_appointment.patient_chat_template', {
            'specializations': specializations,
        })

    @http.route('/clinic/patient/chat/start', type='json', auth='public', methods=['POST'])
    def start_chat(self, **kwargs):
        """
        Creates session and puts patient in WAITING queue.
        Doctor manually accepts from dashboard — no auto-assign.
        """
        data           = json.loads(request.httprequest.data)
        patient_name   = (data.get('patient_name')  or '').strip()
        patient_phone  = (data.get('patient_phone') or '').strip()
        specialization = (data.get('specialization') or '').strip()
        preferred_slot = (data.get('preferred_slot') or '').strip()

        if not patient_name or not patient_phone:
            return {'error': 'Please provide your full name and phone number.'}
        if not specialization:
            return {'error': 'Please select a specialization.'}

        # ── Resolve or create patient record ────────────────────────────
        Patient = request.env['clinic.patient'].sudo()

        patient = Patient.search([
            ('phone', '=', patient_phone),
            ('name', '=ilike', patient_name),
        ], limit=1)

        if not patient:
            patient = Patient.search([('phone', '=', patient_phone)], limit=1)
            if patient:
                patient.sudo().write({'name': patient_name})

        if not patient:
            try:
                patient = Patient.create({
                    'name':       patient_name,
                    'phone':      patient_phone,
                    'birth_date': '1900-01-01',
                })
            except Exception as e:
                _logger.error('start_chat: could not create patient: %s', e)
                return {'error': 'Could not register patient. Please try again.'}

        # ── Check if this patient already has an open session ────────────
        ChatSession = request.env['clinic.chat.session'].sudo()
        session = ChatSession.search([
            ('patient_id', '=', patient.id),
            ('status', 'in', ['waiting', 'active']),
        ], order='create_date desc', limit=1)

        is_new = not session

        if is_new and preferred_slot:
            conflict = ChatSession.search([
                ('specialization', 'ilike', specialization),
                ('preferred_slot', '=', preferred_slot),
                ('status', 'in', ['waiting', 'active']),
            ], limit=1)
            if conflict:
                _logger.info(
                    'start_chat: slot conflict — slot "%s" for "%s" already held by session %s (patient: %s)',
                    preferred_slot, specialization, conflict.id, conflict.patient_name,
                )
                return {
                    'error': (
                        'The time slot "%s" for %s is already booked. '
                        'Please go back and select a different time slot.'
                        % (preferred_slot, specialization)
                    )
                }

        # ── Create new session ───────────────────────────────────────────
        if is_new:
            session = ChatSession.create({
                'patient_id':        patient.id,
                'specialization':    specialization,
                'preferred_slot':    preferred_slot,
                'status':            'waiting',
                'consultation_type': 'online',
            })

        # ── Build greeting message ───────────────────────────────────────
        if session.doctor_id:
            clean    = _clean_name(session.doctor_id.name)
            greeting = '🟢 Dr. %s is attending your consultation.' % clean
        else:
            slot_note = (' Your preferred time: %s.' % preferred_slot) if preferred_slot else ''
            greeting  = (
                'You are now in the queue for %s.%s\n'
                'A doctor will join shortly — please describe your symptoms below '
                'so they can review your case immediately.' % (specialization, slot_note)
            )

        if is_new:
            greeting_msg = request.env['clinic.chat.message'].sudo().create({
                'session_id':  session.id,
                'sender_type': 'system',
                'sender_name': 'System',
                'message':     greeting,
            })
            last_message_id = greeting_msg.id
        else:
            last_msg = request.env['clinic.chat.message'].sudo().search(
                [('session_id', '=', session.id)],
                order='id desc', limit=1
            )
            last_message_id = last_msg.id if last_msg else 0

        return {
            'session_id':      session.session_id,
            'status':          session.status,
            'doctor_assigned': bool(session.doctor_id),
            'doctor_name':     session.doctor_id.name if session.doctor_id else None,
            'greeting':        greeting,
            'last_message_id': last_message_id,
        }

    @http.route('/clinic/patient/chat/send', type='json', auth='public', methods=['POST'])
    def send_message(self, **kwargs):
        data         = json.loads(request.httprequest.data)
        session_id   = data.get('session_id')
        message      = (data.get('message') or '').strip()
        patient_name = (data.get('patient_name') or '').strip()

        if not message:    return {'error': 'Empty message'}
        if not session_id: return {'error': 'No active session.'}

        session = request.env['clinic.chat.session'].sudo().search(
            [('session_id', '=', session_id)], limit=1)
        if not session:
            return {'error': 'Session not found'}
        if session.status in ('closed', 'ended'):
            return {'error': 'Consultation has ended.', 'status': session.status}

        request.env['clinic.chat.message'].sudo().create({
            'session_id':  session.id,
            'sender_type': 'patient',
            'sender_name': patient_name or session.patient_name or 'Patient',
            'message':     message,
        })

        return {
            'session_id':      session.session_id,
            'status':          session.status,
            'doctor_assigned': bool(session.doctor_id),
            'doctor_name':     session.doctor_id.name if session.doctor_id else None,
        }

    @http.route('/clinic/patient/chat/poll', type='json', auth='public', methods=['POST'])
    def poll_messages(self, **kwargs):
        data       = json.loads(request.httprequest.data)
        session_id = data.get('session_id')
        last_id    = int(data.get('last_id', 0))

        if not session_id:
            return {'messages': [], 'status': 'unknown'}

        session = request.env['clinic.chat.session'].sudo().search(
            [('session_id', '=', session_id)], limit=1)
        if not session:
            return {'messages': [], 'status': 'unknown'}

        msgs = request.env['clinic.chat.message'].sudo().search([
            ('session_id', '=', session.id),
            ('id', '>', last_id),
            ('sender_type', 'in', ['doctor', 'system']),
        ], order='create_date asc')

        return {
            'messages': [{
                'id':          m.id,
                'sender':      m.sender_type,
                'sender_name': m.sender_name or 'Doctor',
                'message':     m.message,
                'timestamp':   m.create_date.strftime('%H:%M'),
            } for m in msgs],
            'status':          session.status,
            'doctor_assigned': bool(session.doctor_id),
            'doctor_name':     session.doctor_id.name if session.doctor_id else None,
        }

    @http.route('/clinic/doctor/chat/session-info', type='json', auth='user', methods=['POST'])
    def session_info(self, **kwargs):
        """Returns session info by UUID — used for auto-open after accept."""
        data         = json.loads(request.httprequest.data)
        session_uuid = data.get('session_uuid')
        session = request.env['clinic.chat.session'].sudo().search(
            [('session_id', '=', session_uuid)], limit=1)
        if not session:
            return {'error': 'Not found'}
        return {
            'db_id':        session.id,
            'session_id':   session.session_id,
            'patient_name': session.patient_name or 'Patient',
        }

    @http.route('/get_chat_slots', type='json', auth='public', methods=['POST'], csrf=False)
    def get_chat_slots(self, **kwargs):
        """
        Return today's available time slots for the given specialization.

        A slot is excluded from results if:
          1. is_booked = True on clinic.appointment.slot (booked via appointment), OR
          2. An active/waiting clinic.chat.session already holds that slot name
             for the same specialization (booked via chat).

        slot.name format: "HH:MM AM/PM - HH:MM AM/PM"  (e.g. "11:30 AM - 12:00 PM")
        session.preferred_slot stores the same string verbatim from the frontend,
        which receives it directly from slot.name — so the string comparison is exact.
        """
        try:
            data           = json.loads(request.httprequest.data)
            specialization = (data.get('specialization') or '').strip()

            if not specialization:
                return {'slots': []}

            today = date.today()

            # Prefer online doctors; fall back to any doctor for the specialization
            doctors = request.env['clinic.employee'].sudo().search([
                ('role', '=', 'doctor'),
                ('specialization_id.name', 'ilike', specialization),
                ('online_status', '=', 'online'),
            ])
            if not doctors:
                doctors = request.env['clinic.employee'].sudo().search([
                    ('role', '=', 'doctor'),
                    ('specialization_id.name', 'ilike', specialization),
                ])

            if not doctors:
                _logger.info('get_chat_slots: no doctors found for "%s"', specialization)
                return {'slots': []}

            # Ensure today's slots exist
            SlotModel = request.env['clinic.appointment.slot'].sudo()
            for doctor in doctors:
                try:
                    SlotModel.generate_slots(doctor, today)
                except Exception as e:
                    _logger.warning(
                        'get_chat_slots: generate_slots failed for doctor %s: %s',
                        doctor.id, e
                    )
                    
            occupied_sessions = request.env['clinic.chat.session'].sudo().search([
                ('specialization', 'ilike', specialization),
                ('status', 'in', ['waiting', 'active']),
                ('preferred_slot', '!=', False),
                ('preferred_slot', '!=', ''),
            ])
            occupied_slots = set(
                s.preferred_slot.strip()
                for s in occupied_sessions
                if s.preferred_slot
            )

            if occupied_slots:
                _logger.info(
                    'get_chat_slots: occupied slots for "%s": %s',
                    specialization, occupied_slots
                )

            # Fetch appointment-model slots that are not booked
            slots = SlotModel.search([
                ('doctor_id', 'in', doctors.ids),
                ('slot_date', '=', today),
                ('is_booked', '=', False),
            ], order='start_time asc')

            if not slots:
                return {'slots': []}

            seen   = set()
            result = []
            for slot in slots:
                if not slot.name or slot.name in seen:
                    continue
                # Exclude slots already held by a chat session
                if slot.name.strip() in occupied_slots:
                    _logger.info(
                        'get_chat_slots: hiding slot "%s" — held by active/waiting chat session',
                        slot.name
                    )
                    continue
                seen.add(slot.name)
                result.append({'id': slot.id, 'name': slot.name})

            return {'slots': result}

        except Exception:
            _logger.error('get_chat_slots: unexpected error', exc_info=True)
            return {'slots': []}