from groq import Groq
import os
import logging
from dotenv import load_dotenv

load_dotenv()

_logger = logging.getLogger(__name__)

api_key = os.getenv("GROQ_API_KEY")

client = Groq(
    api_key=api_key
)

def extract_search_query(user_query):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """
You are an product search assistant.

Convert the user's message into the most relevant product search query.

Return only the search query.
Do not explain.
Do not answer the user.
Return plain text only.
"""
                },
                {
                    "role": "user",
                    "content": user_query
                }
            ],
            temperature=0
        )

        query = response.choices[0].message.content.strip()

        _logger.info(f"LLM Search Query: {query}")

        return query or user_query

    except Exception as e:
        _logger.error(f"LLM Error: {e}")
        return user_query