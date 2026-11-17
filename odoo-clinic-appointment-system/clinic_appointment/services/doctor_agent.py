"""
doctor_agent.py
───────────────
DoctorAgent assists the doctor side of a live chat consultation.

Responsibilities:
  1. When a doctor accepts a session, produce a compact briefing note:
     patient name, specialization, symptoms collected so far.
  2. After each doctor message, optionally suggest follow-up actions
     (future: prescriptions, lab tests, booking follow-up appointment).
"""

import logging
try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

_logger = logging.getLogger(__name__)


class DoctorAgent:
    """
    Wraps the Agno Agent for the doctor side.
    Falls back to structured text briefing when Agno/LLM is unavailable.
    """

    def __init__(self, env, session, doctor):
        self.env = env
        self.session = session
        self.doctor = doctor
        self._agent = None

        if AGNO_AVAILABLE:
            try:
                self._agent = Agent(
                    model=OpenAIChat(id='gpt-4o-mini'),
                    description=(
                        'You are a clinical assistant helping a doctor review a new patient '
                        'chat session. Summarise the patient\'s reported symptoms concisely '
                        'and flag anything urgent. Be clinical, brief, and factual.'
                    ),
                    markdown=False,
                )
            except Exception as e:
                _logger.warning('Could not initialise Agno DoctorAgent: %s', e)
                self._agent = None

    def on_session_start(self) -> str | None:
        """
        Called when the doctor accepts the session.
        Returns a briefing note as a string, or None if nothing to report.
        This is stored as a 'system' message visible in the doctor's chat window.
        """
        history = self._get_patient_messages()

        if not history:
            return (
                '📋 New patient: %s | Specialization: %s\n'
                'No messages yet — patient has just joined.'
                % (self.session.patient_name or 'Unknown', self.session.specialization or 'General')
            )

        # Build history summary
        patient_messages = '\n'.join('• ' + m for m in history)

        if self._agent:
            prompt = (
                'Patient: %s | Specialization: %s\n\n'
                'Patient messages so far:\n%s\n\n'
                'Write a 2–3 sentence clinical briefing for the doctor. '
                'Include: chief complaint, duration (if mentioned), severity (if mentioned), '
                'and any red flags. Start with "📋 Patient Briefing:"'
                % (
                    self.session.patient_name or 'Unknown',
                    self.session.specialization or 'General',
                    patient_messages,
                )
            )
            result = self._run(prompt)
            if result:
                return result

        # Fallback: structured plain-text briefing
        return (
            '📋 Patient Briefing:\n'
            'Patient: %s | Dept: %s\n'
            'Reported symptoms:\n%s'
            % (
                self.session.patient_name or 'Unknown',
                self.session.specialization or 'General',
                patient_messages,
            )
        )

    def on_message_sent(self, message: str) -> None:
        """
        Called after the doctor sends a message.
        Currently a hook for future extensions (auto-suggest prescriptions,
        lab tests, follow-up booking). No-op for now.
        """
        pass

    # ──────────────────────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────────────────────

    def _run(self, prompt: str) -> str | None:
        """Run the Agno agent and return the text response."""
        if not self._agent:
            return None
        try:
            result = self._agent.run(prompt)
            if hasattr(result, 'content'):
                return str(result.content).strip() or None
            return str(result).strip() or None
        except Exception as e:
            _logger.error('DoctorAgent._run error: %s', e)
            return None

    def _get_patient_messages(self) -> list[str]:
        """Return all patient messages for this session as a list of strings."""
        messages = self.env['clinic.chat.message'].sudo().search([
            ('session_id', '=', self.session.id),
            ('sender_type', '=', 'patient'),
        ], order='create_date asc')
        return [m.message for m in messages]