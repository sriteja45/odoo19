from odoo import http
from odoo.http import request
import json
import logging

from ..services.web_search_service import search_web_products
from ..services.llm_service import extract_search_query

_logger = logging.getLogger(__name__)


class ProductAgent(http.Controller):

    @http.route(
        '/api/product-agent',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def product_agent(self, **kwargs):

        try:
            # -----------------------------
            # READ INPUT
            # -----------------------------
            data = json.loads(request.httprequest.data or "{}")
            user_query = data.get("query", "").strip()

            if not user_query:
                return request.make_json_response({
                    "status": "error",
                    "message": "Query is required"
                })

            # -----------------------------
            # FRIENDLY GREETING HANDLING
            # -----------------------------
            greetings = ["hi", "hello", "hey", "good morning", "good evening"]

            if user_query.lower() in greetings:
                return request.make_json_response({
                    "status": "success",
                    "source": "chat",
                    "answer": "👋 Hello! I’m your product assistant. Ask me about any product like laptops, mobiles, or electronics.",
                    "products": []
                })

            # -----------------------------
            # STEP 1: LLM QUERY CLEANING
            # -----------------------------
            search_query = extract_search_query(user_query)

            if not search_query:
                search_query = user_query

            _logger.info(f"User Query: {user_query}")
            _logger.info(f"Search Query: {search_query}")

            # -----------------------------
            # STEP 2: WEB SEARCH ONLY
            # -----------------------------
            try:
                products = search_web_products(search_query)
            except Exception as e:
                _logger.warning(f"Web search failed: {e}")
                products = []

            # -----------------------------
            # STEP 3: SUCCESS RESPONSE
            # -----------------------------
            if products and len(products) > 0:
                return request.make_json_response({
                    "status": "success",
                    "source": "web",
                    "answer": "Here are some products I found for you 🔍",
                    "products": products
                })

            # -----------------------------
            # STEP 4: NO RESULTS MESSAGE
            # -----------------------------
            return request.make_json_response({
                "status": "success",
                "source": "none",
                "answer": "Sorry 😕 I couldn’t find any products for your request. Try something like 'HP laptop' or 'Samsung phone'.",
                "products": []
            })

        except Exception as e:
            _logger.exception("Product agent error")
            return request.make_json_response({
                "status": "error",
                "message": str(e)
            })