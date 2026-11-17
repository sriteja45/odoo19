"""
agno_service.py
───────────────
Bridge between Odoo chat sessions and the Agno agent framework.

Architecture:
  PatientAgent  ←──── AgnoService ────→  DoctorAgent
        │                                      │
        └──────── clinic.chat.session ─────────┘

Hooks called from chat_controllers.py:
  • patient_greeting(session, name, spec)   — fired when patient starts chat
  • patient_message(session, message)       — fired on every patient message
  • on_doctor_accepted(session, doctor)     — fired when doctor accepts chat
  • on_doctor_message(session, doctor, msg) — fired on every doctor message
"""

import logging
from .patient_agent import PatientAgent
from .doctor_agent import DoctorAgent

_logger = logging.getLogger(__name__)


class AgnoService:
    """
    Stateless service — instantiated per request.
    All state lives in the Odoo DB (clinic.chat.session + clinic.chat.message).
    """

    def __init__(self, env):
        self.env = env

    # ──────────────────────────────────────────────────────────────
    #  PATIENT SIDE
    # ──────────────────────────────────────────────────────────────

    def patient_greeting(self, session, patient_name: str, specialization: str) -> str:
        """
        Called when a patient starts a new chat session.
        PatientAgent produces a personalised greeting / intake message.
        Returns the greeting string (stored by caller as a system message).
        """
        try:
            agent = PatientAgent(env=self.env, session=session)
            greeting = agent.greet(patient_name=patient_name, specialization=specialization)
            return greeting or self._default_greeting(patient_name, specialization)
        except Exception as e:
            _logger.error('PatientAgent.greet failed: %s', e)
            return self._default_greeting(patient_name, specialization)

    def patient_message(self, session, message: str) -> str | None:
        """
        Called on every patient message.
        PatientAgent may return a response string (intake questions, symptom
        collection, appointment suggestion) or None if silent.

        If the session already has a doctor, the agent defers and returns None
        so the doctor's real response is not overridden.
        """
        if session.doctor_id:
            # Doctor is present — agent stays silent, doctor responds directly
            return None
        try:
            agent = PatientAgent(env=self.env, session=session)
            return agent.respond(message=message)
        except Exception as e:
            _logger.error('PatientAgent.respond failed: %s', e)
            return None

    # ──────────────────────────────────────────────────────────────
    #  DOCTOR SIDE
    # ──────────────────────────────────────────────────────────────

    def on_doctor_accepted(self, session, doctor) -> None:
        """
        Called when a doctor accepts a waiting chat.
        DoctorAgent receives the full session context (patient name,
        specialization, all prior messages) so the doctor gets a
        briefing note as a system message.
        """
        try:
            agent = DoctorAgent(env=self.env, session=session, doctor=doctor)
            briefing = agent.on_session_start()
            if briefing:
                self.env['clinic.chat.message'].sudo().create({
                    'session_id': session.id,
                    'sender_type': 'system',
                    'sender_name': 'AI Briefing',
                    'message': briefing,
                })
        except Exception as e:
            _logger.error('DoctorAgent.on_session_start failed: %s', e)

    def on_doctor_message(self, session, doctor, message: str) -> None:
        """
        Called after a doctor sends a message.
        DoctorAgent can optionally suggest follow-up actions (prescriptions,
        lab tests, appointment scheduling) — returned as a private system
        note visible only on the doctor side (future feature).
        Currently a no-op hook for extensibility.
        """
        try:
            agent = DoctorAgent(env=self.env, session=session, doctor=doctor)
            agent.on_message_sent(message=message)
        except Exception as e:
            _logger.warning('DoctorAgent.on_message_sent failed: %s', e)

    # ──────────────────────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _default_greeting(patient_name: str, specialization: str) -> str:
        return (
            'Hello %s! 👋 Welcome to the %s consultation queue. '
            'Please describe your main symptoms or concern and a doctor '
            'will be with you shortly.' % (patient_name, specialization)
        )