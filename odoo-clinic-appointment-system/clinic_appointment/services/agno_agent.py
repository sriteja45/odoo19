import logging
import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.groq import Groq
from .db_config import get_pg_dsn
from .instructions import get_admin_instructions, get_user_instructions
from .tools import build_toolkit

load_dotenv()
_logger = logging.getLogger(__name__)


class ClinicAgnoAgent:
    def __init__(self, env, user_role='guest', session_id=None):
        self.env = env
        self.user_role = user_role
        self.session_id = session_id or 'default'
        self._last_tool_result = None
        self.agent = self._build_agent()

    def _build_agent(self):
        instructions = get_admin_instructions() if self.user_role == 'admin' else get_user_instructions()
        toolkit = build_toolkit(self.env, self.user_role == 'admin', agent_ref=self)
        db = PostgresDb(db_url=get_pg_dsn())
        return Agent(
            model=Groq(
                id=os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant'),
                api_key=os.getenv('GROQ_API_KEY'),
            ),
            instructions=instructions,
            tools=[toolkit],
            db=db,
            session_id=self.session_id,
            add_history_to_context=True,
            num_history_runs=1,
            markdown=False,
        )

    def chat(self, message: str) -> dict:
        try:
            self._last_tool_result = None
            response = self.agent.run(message)
            content = response.content or self._last_tool_result or 'Sorry, I could not process that.'
            return {
                'status': 'success',
                'response': content,
                'role': self.user_role,
                'session_id': self.session_id,
            }
        except Exception as e:
            _logger.exception('ClinicAgnoAgent.chat() error: %s', e)
            return {
                'status': 'error',
                'response': 'I had trouble processing that request. Please try again with doctor, slot, booking, lab test, timings, or contact details.',
                'role': self.user_role,
                'session_id': self.session_id,
            }