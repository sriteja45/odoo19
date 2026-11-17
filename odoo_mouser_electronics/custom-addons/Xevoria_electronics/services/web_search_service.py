from serpapi.google_search import GoogleSearch
import os
from dotenv import load_dotenv

load_dotenv()


def search_web_products(query, limit=10):
    """
    Fetch products from Google Shopping using SerpAPI
    fallback when no DB products found in Meilisearch
    """

    try:
        # Get API key from environment (recommended)
        serpapi_key = os.getenv("SERPAPI_KEY")
        print("SERPAPI_KEY =", os.getenv("SERPAPI_KEY"))

        

        # fallback (NOT recommended for production)
        if not serpapi_key:
            return []

        search = GoogleSearch({
            "engine": "google_shopping",
            "q": query,
            "api_key": serpapi_key
        })

        results = search.get_dict()

        products = []

        for item in results.get("shopping_results", [])[:limit]:

            products.append({
                "title": item.get("title"),
                "price": item.get("price"),
                "store": item.get("source"),
                "thumbnail": item.get("thumbnail"),
                "link": item.get("product_link") or item.get("link")
            })

        return products

    except Exception as e:
        print("Web Search Error:", str(e))
        return []