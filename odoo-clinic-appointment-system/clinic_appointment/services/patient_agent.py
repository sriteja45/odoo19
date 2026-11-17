"""
patient_agent.py
────────────────
PatientAgent handles the patient side of a live chat consultation.

Responsibilities:
  1. Greet the patient and collect intake info (symptoms, duration, etc.)
  2. When no doctor is assigned yet, respond intelligently to keep the
     patient engaged and gather relevant medical context.
  3. Once a doctor joins, go silent — the doctor takes over.

The agent maintains its context via the clinic.chat.message history
in the Odoo DB (no in-process state between requests).
"""

import logging
try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

_logger = logging.getLogger(__name__)

# Intake questions asked in order if the patient hasn't answered them yet
INTAKE_QUESTIONS = [
    'Could you describe your main symptom or concern?',
    'How long have you been experiencing this?',
    'Is the symptom constant or does it come and go?',
    'On a scale of 1–10, how would you rate your discomfort?',
    'Are you currently taking any medications?',
]


class PatientAgent:
    """
    Wraps the Agno Agent for the patient side.
    Falls back to rule-based responses when Agno/LLM is not available.
    """

    def __init__(self, env, session):
        self.env = env
        self.session = session
        self._agent = None

        if AGNO_AVAILABLE:
            try:
                self._agent = Agent(
                    model=OpenAIChat(id='gpt-4o-mini'),
                    description=(
                        'You are a friendly medical intake assistant for a clinic. '
                        'Your job is to collect the patient\'s symptoms and medical '
                        'history before a doctor joins the chat. Be warm, concise, '
                        'and ask one question at a time. Never diagnose.'
                    ),
                    markdown=False,
                )
            except Exception as e:
                _logger.warning('Could not initialise Agno PatientAgent: %s', e)
                self._agent = None

    def greet(self, patient_name: str, specialization: str) -> str:
        """Generate the opening greeting message."""
        prompt = (
            'A patient named %s has started a %s consultation. '
            'Write a short, warm greeting (2 sentences max) and ask '
            'them to describe their main concern.' % (patient_name, specialization)
        )
        response = self._run(prompt)
        if response:
            return response
        # Fallback
        return (
            'Hello %s! 👋 Welcome to your %s consultation. '
            'Please describe your main concern and a doctor will be with you shortly.'
            % (patient_name, specialization)
        )

    def respond(self, message: str) -> str | None:
        """
        Respond to a patient message while they are waiting for a doctor.
        Returns a string response, or None to stay silent.
        """
        # Build chat history context
        history = self._get_chat_history()
        intake_answered = len([m for m in history if m['sender_type'] == 'patient'])

        if self._agent:
            # Build a prompt with history context
            context = '\n'.join(
                '[%s] %s' % (m['sender_type'].upper(), m['message'])
                for m in history[-10:]  # last 10 messages for context window
            )
            prompt = (
                'Chat history so far:\n%s\n\n'
                'Patient just said: "%s"\n\n'
                'Respond as the intake assistant. '
                'If they\'ve described their symptom, ask the next intake question. '
                'If they are asking about wait times or doctor availability, '
                'reassure them. Never diagnose. Keep response under 3 sentences.'
                % (context, message)
            )
            response = self._run(prompt)
            if response:
                return response

        # Rule-based fallback
        msg_lower = message.lower()

        # Detect common intents
        if any(w in msg_lower for w in ['how long', 'wait', 'when', 'doctor']):
            return (
                '⏳ A doctor will accept your chat as soon as one is available online. '
                'In the meantime, please describe your symptoms so they can review your '
                'case immediately when they join.'
            )

        if any(w in msg_lower for w in ['thank', 'ok', 'okay', 'sure', 'yes', 'no']):
            # Acknowledgement — ask the next unanswered intake question
            if intake_answered < len(INTAKE_QUESTIONS):
                return '📋 ' + INTAKE_QUESTIONS[intake_answered]
            return None  # All intake questions answered — stay silent

        # Default: ask next intake question
        if intake_answered < len(INTAKE_QUESTIONS):
            return '📋 ' + INTAKE_QUESTIONS[min(intake_answered, len(INTAKE_QUESTIONS) - 1)]

        return None

    # ──────────────────────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────────────────────

    def _run(self, prompt: str) -> str | None:
        """Run the Agno agent and return the text response."""
        if not self._agent:
            return None
        try:
            result = self._agent.run(prompt)
            # Agno returns a RunResponse; extract content
            if hasattr(result, 'content'):
                return str(result.content).strip() or None
            return str(result).strip() or None
        except Exception as e:
            _logger.error('PatientAgent._run error: %s', e)
            return None

    def _get_chat_history(self) -> list[dict]:
        """Fetch all messages for this session from the DB."""
        messages = self.env['clinic.chat.message'].sudo().search(
            [('session_id', '=', self.session.id)],
            order='create_date asc',
        )
        return [
            {
                'sender_type': m.sender_type,
                'sender_name': m.sender_name or m.sender_type,
                'message': m.message,
            }
            for m in messages
        ]