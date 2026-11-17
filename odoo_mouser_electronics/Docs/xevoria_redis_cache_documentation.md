# Xevoria Redis Cache Module Documentation

## 1. Overview
The **Xevoria Redis Cache** (`xevoria_redis_cache`) module is designed for **Odoo 19.0** to optimize the performance of the E-commerce website (`website_sale`). By offloading expensive database operations—such as multi-criteria product catalog lookups and frequent user session metadata resolution—to an in-memory Redis datastore, the module significantly reduces database load, minimizes page latency, and speeds up product searches.

### Key Capabilities:
* **Shop Product Lookup Caching:** Elements like search terms, filters (categories, tags, attributes), price ranges, and current context (website, company, pricelist, language) are hashed into a deterministic key. The matching `product.template` IDs are stored in Redis with a 1-hour Time-to-Live (TTL).
* **User Session Caching:** Caches high-frequency user environment data (User ID, Partner ID, Company ID, Website, Language, Timezone, and Security Groups) for authenticated users to bypass recurring database reads.
* **Automated Invalidation (Cache Coherency):** Hooks into standard Odoo CRUD operations (`create`, `write`, `unlink`) on core models (`product.template`, `res.users`, `res.partner`) to transparently purge relevant Redis keys when data changes.
* **Singleton Client Pattern:** Utilizes a thread-safe singleton connection pool driven by native Odoo configurations configuration parameters.

---

## 2. Architecture & Design

### Data Flow & Cache Strategy
1. **Cache Lookups:** When a shopper navigates the catalog, the module constructs a unique MD5 signature of all active query parameters. If a Redis key matches, it retrieves the primitive list of IDs, executes an optimized Odoo `browse()` query with `bin_size=True`, and returns the recordset.
2. **Cache Generation:** On a cache miss, the module delegates execution back to the standard database-backed controller `super()._shop_lookup_products()`. The resulting product list IDs and totals are saved back to Redis.
3. **Write-Through Invalidation:** To prevent stale cache issues, modifications to products trigger an atomic scan and delete routine across predefined shop keys. Updates to partners or users clear their specific session keys.

### Module Structure
```text
xevoria_redis_cache/
│
├── __init__.py                # Global package initialization and lazy imports
├── __manifest__.py            # Odoo module metadata, dependencies, and parameters
├── requirements.txt           # Python library dependencies
│
├── controllers/
│   ├── __init__.py
│   └── shop.py                # Overrides WebsiteSale controller to inject caching
│
├── models/
│   ├── __init__.py
│   ├── product_template.py    # Auto-invalidation logic for products
│   ├── res_partner.py         # Auto-invalidation logic for partner relations
│   └── res_users.py           # Auto-invalidation logic for application users
│
└── services/
    ├── __init__.py
    ├── redis_client.py        # Singleton connection manager wrapping redis-py
    ├── cache_service.py       # Base abstraction layer for generic key-value actions
    └── user_session_cache.py  # Layer managing marshalled user authentication records
```

---

## 3. Core Implementation Details

### A. Connection Layer: `redis_client.py`
This class implements a thread-safe implementation of a singleton wrapper around `redis.Redis`. It reads authentication properties directly from the global Odoo config engine (`odoo.tools.config`).

```python
import redis
import os
from dotenv import load_dotenv
from odoo.tools import config
load_dotenv()

class RedisClient:
    _client = None

    @classmethod
    def get_client(cls):
        """
        Singleton Redis Connection
        """
        if cls._client:
            return cls._client
            
        print("Config", config.get("redis_host"))
        cls._client = redis.Redis(
            host=config.get("redis_host"),
            port=int(config.get("redis_port")),
            db=int(config.get("redis_db")),
            password=config.get("redis_password"),
            decode_responses=True,
        )
        if cls._client:
            print("Redis Client initialized")
            print("Client", cls._client)
            print("Client ping", cls._client.ping())

        return cls._client
```

### B. Controller Injection: `shop.py`
This overrides `WebsiteSale` to short-circuit the default product lookup engine when cached results exist.

```python
import hashlib
import json
import logging
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from ..services.cache_service import CacheService
from ..services.user_session_cache import UserSessionCache

_logger = logging.getLogger(__name__)

class WebsiteSaleRedis(WebsiteSale):

    def _load_user_session(self):
        if request.env.user._is_public():
            return None
        session_cache = UserSessionCache()
        return session_cache.get_or_create(request.env.user)

    def _generate_shop_cache_key(self, search, options, post):
        cache_data = {
            "search": search or "",
            "category": options.get("category"),
            "tags": options.get("tags"),
            "min_price": options.get("min_price"),
            "max_price": options.get("max_price"),
            "attributes": options.get("attribute_value_dict"),
            "order": post.get("order", ""),
            "website": request.website.id,
            "company": request.website.company_id.id,
            "pricelist": request.pricelist.id,
            "language": request.lang.code,
        }
        cache_string = json.dumps(cache_data, sort_keys=True, default=str)
        return "shop:" + hashlib.md5(cache_string.encode()).hexdigest()

    def _shop_lookup_products(self, options, post, search, website):
        session = self._load_user_session()
        if session:
            _logger.info("Using Cached User Session : %s", session["uid"])

        cache = CacheService()
        cache_key = self._generate_shop_cache_key(search, options, post)
        cached = cache.get(cache_key)

        if cached:
            products = request.env["product.template"].browse(
                cached["product_ids"]
            ).with_context(bin_size=True)
            return (cached["fuzzy"], cached["count"], products)

        fuzzy_search_term, product_count, search_result = super()._shop_lookup_products(
            options, post, search, website
        )

        cache.set(
            cache_key,
            {
                "count": product_count,
                "fuzzy": fuzzy_search_term,
                "product_ids": search_result.ids,
            },
            ttl=3600,  # 1 hour TTL
        )
        return fuzzy_search_term, product_count, search_result
```

### C. Invalidation Hook: `product_template.py`
To avoid serving outdated pricing, search terms, or images, modifying any `product.template` record triggers structural pattern-matching deletions via Redis `SCAN`.

```python
import logging
from odoo import api, models
from ..services.cache_service import CacheService

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _clear_shop_cache(self):
        cache = CacheService()
        try:
            client = cache.client
            patterns = ["shop:*", "product:*", "category:*", "featured_products", "new_products"]
            total_deleted = 0

            for pattern in patterns:
                cursor = 0
                while True:
                    cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        client.delete(*keys)
                        total_deleted += len(keys)
                    if cursor == 0:
                        break
            _logger.info("Redis Cache Cleared (%s keys)", total_deleted)
        except Exception as ex:
            _logger.exception(ex)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._clear_shop_cache()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._clear_shop_cache()
        return result

    def unlink(self):
        self._clear_shop_cache()
        return super().unlink()
```

---

## 4. Setup & Deployment Guide

Follow these sequential steps to integrate and activate the Redis caching layer within your target environment.

### Step 1: Install Redis dependencies
Ensure a Redis Server instance (version 6.2 or higher recommended) is accessible to your Odoo host environment.

* **Ubuntu / Debian Installation:**
    ```bash
    sudo apt update
    sudo apt install redis-server -y
    ```

* **Verification:** Ensure the system service is active and running:
    ```bash
    sudo systemctl status redis-server
    ```
### Step 1 is mandatory if you want to use Redis caching in server side setup, otherwise you can skip this step for local setup. If you need to setup redis on local machine, you can use the following command:

```bash
docker run -d --name redis -p 6379:6379 redis
```
# If you want to check whether data is stored in redis or not, you can download redis insight from https://redis.io/insight/ and configure and connect to the local redis instance running through docker.

### Step 2: Configure Python Environment Dependencies
The module requires the native `redis` library to act as an interface driver.
Navigate to your Odoo installation path or activate your environment and execute:

```bash
pip install redis
```

### Step 3: Inject Configuration in Odoo Settings File
Add the Redis connection settings to your active Odoo configuration file (`odoo.conf`). The `RedisClient` class relies explicitly on these specific parameter keys:

```ini
[options]
; Existing Odoo parameters...
addons_path = [custom_addons_path]
redis_host = 127.0.0.1
redis_port = 6379
redis_db = 0
redis_password = your_secure_redis_password_here
```
*Note: If testing locally without an authentication password layer set up on Redis, pass an empty string or match your server configuration settings.*

### Step 4: Deploy Module Package
1. Transfer the entire `xevoria_redis_cache` module directory into your Odoo custom addons directory (e.g., `/opt/odoo/custom_addons/`).
2. Update permissions to allow the execution system user (`odoo`) read/write access.
3. Restart your active Odoo Application Server to bind the updated configurations:
   ```bash
   python odoo-bin -c odoo.conf -d [db_name]-u [module_name]
   ```

### Step 5: Module Installation
1. Access the Odoo Web Interface with **Administrator privileges**.
2. Activate **Developer Mode** (via Settings or the URL query string).
3. Navigate to the **Apps** app menu section.
4. Click **Update Apps List** from the top action menu bar to detect the custom path additions.
5. In the search bar, remove the default `Apps` filter token and look up `Xevoria Redis Cache`.
6. Click **Activate / Install**.

---

## 5. Verification & Troubleshooting

### Operational Testing
To confirm that caching operates correctly, navigate to your front-end e-commerce shop page (`/shop`) and interact with search elements or page attributes. Inspect your standard Odoo application server log stream. You should see entries matching the expected log fingerprints:

```text
INFO database_name odoo.addons.xevoria_redis_cache.services.cache_service: Redis Cache MISS : shop:a7b8c9...
INFO database_name odoo.addons.xevoria_redis_cache.services.cache_service: Redis Cache Stored : shop:a7b8c9...
```

Subsequent duplicate page refreshes or filter hits with identical arguments will trigger immediate cache hit log signals:

```text
INFO database_name odoo.addons.xevoria_redis_cache.services.cache_service: Redis Cache HIT : shop:a7b8c9...
```

### Common Error Resolutions
1. **`KeyError` during initial boot sequence:** Ensure that all configuration lines (`redis_host`, `redis_port`, etc.) are defined under the central `[options]` block in your Odoo server config file.
2. **Connection Timeout or Socket Errors:** Check network infrastructure rules, firewalls, or bind address constraints in your `/etc/redis/redis.conf` configuration file (e.g., ensure `bind 127.0.0.1` matches your structural access layout).
