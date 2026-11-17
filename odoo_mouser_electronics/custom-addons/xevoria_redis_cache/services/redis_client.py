import logging

import redis
from redis import ConnectionPool
from redis.exceptions import ConnectionError

from odoo.tools import config


_logger = logging.getLogger(__name__)


class RedisClient:

    _client = None
    _pool = None

    @classmethod
    def get_client(cls):

        # Reuse existing Redis connection
        if cls._client:
            return cls._client

        host = config.get("redis_host")
        port = int(config.get("redis_port", 6379))
        db = int(config.get("redis_db", 0))
        password = config.get("redis_password")

        if not host:
            _logger.warning(
                "redis_host is not configured"
            )
            return None

        _logger.info(
            "Redis Host: %s",
            host,
        )

        _logger.info(
            "Redis Port: %s",
            port,
        )

        _logger.info(
            "Redis DB: %s",
            db,
        )

        _logger.info(
            "Redis Password configured: %s",
            bool(password),
        )

        try:

            cls._pool = ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )

            cls._client = redis.Redis(
                connection_pool=cls._pool
            )

            # Test Redis connection
            cls._client.ping()

            _logger.info(
                "========== REDIS CONNECTION SUCCESS =========="
            )

            _logger.info(
                "Redis connected successfully "
                "(%s:%s, DB=%s)",
                host,
                port,
                db,
            )

            return cls._client

        except ConnectionError as ex:

            _logger.warning(
                "Unable to connect to Redis: %s",
                ex,
            )

            cls._client = None
            cls._pool = None

            return None

        except Exception as ex:

            _logger.exception(
                "Redis connection failed: %s",
                ex,
            )

            cls._client = None
            cls._pool = None

            return None