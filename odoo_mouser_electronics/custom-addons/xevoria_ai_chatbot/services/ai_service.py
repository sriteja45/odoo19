import logging
import os
import requests

_logger = logging.getLogger(__name__)


class AIService:
    """
    Handles communication with Xevoria AI Backend.
    """

    TIMEOUT = 60

    def __init__(self):
        self.base_url = os.getenv("AI_API_URL")
        self.bearer_token = os.getenv("AI_AUTH_TOKEN") or ""
        _logger.info(f"AI Service URL: {self.base_url}")
        _logger.info(f"AI Service Token Present: {bool(self.bearer_token)}")
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}" if self.bearer_token else "",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def ask(self, query):
        """
        Send the user query to AI backend.

        Returns:
            str
        """
        url = self.base_url or os.getenv("AI_API_URL")
        if not url:
            _logger.error("AI Service: Base URL is missing.")
            return "Sorry, the AI service URL is not configured."

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={
                    "query": query,
                    "limit": 10,
                    "page": 1,
                },
                timeout=self.TIMEOUT,
            )

            if not response.ok:
                _logger.error(
                    f"AI API HTTP Error status={response.status_code}: {response.text}"
                )

            response.raise_for_status()

            data = response.json()

            _logger.info("AI Response received successfully: %s", data)

            return self._extract_response(data)

        except requests.exceptions.Timeout:
            _logger.exception("AI API Timeout")
            return "Sorry, the AI service timed out."

        except requests.exceptions.ConnectionError:
            _logger.exception("Unable to connect to AI service.")
            return "Sorry, the AI service is currently unavailable."

        except requests.exceptions.HTTPError as ex:
            _logger.exception(f"AI API HTTP Error: {ex}")
            return "Sorry, an API error occurred."

        except Exception as ex:
            _logger.exception(f"Unexpected AI Service error: {ex}")
            return "Something went wrong."

    # ---------------------------------------------------------
    # Response Parser
    # ---------------------------------------------------------

    def _extract_response(self, data):
        """
        Parse AI backend response.
        """
        if not data:
            return "Sorry, I couldn't understand your request."

        # ------------------------------
        # General AI Answer / Response
        # ------------------------------
        if isinstance(data, dict):
            if data.get("answer"):
                return self._format_answer(data["answer"])
            if data.get("response"):
                return self._format_answer(data["response"])
            if data.get("message"):
                return self._format_answer(data["message"])

            # ------------------------------
            # Product Search
            # ------------------------------
            if data.get("results"):
                return self._format_products(data["results"])

        return "Sorry, I couldn't find any information."

    # ---------------------------------------------------------
    # Product Formatter
    # ---------------------------------------------------------

    def _format_products(self, products):
        if not products:
            return "No matching products found."

        lines = []

        for product in products:
            name = product.get("name", "")
            description = product.get("description", "")
            image = product.get("image_link", "")
            product_url = product.get("product_url", "")
            price = product.get("price") or product.get("list_price")

            html = f"<b>{name}</b><br/>"

            if price is not None:
                html += f"Price: <b>${price:.2f}</b><br/>" if isinstance(price, (int, float)) else f"Price: <b>{price}</b><br/>"

            if description:
                html += f"{description}<br/>"

            if image:
                html += f'<img src="{image}" width="180"/><br/>'

            if product_url:
                html += f'<a href="{product_url}" target="_blank">View Product</a>'

            lines.append(html)

        return "<hr/>".join(lines)

    def _format_answer(self, answer):
        """
        Format normal AI response.
        """
        return str(answer)
