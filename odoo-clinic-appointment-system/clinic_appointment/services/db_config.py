import logging
import os
from odoo.tools import config

_logger = logging.getLogger(__name__)


def _clean(val, default: str) -> str:
    if not val:
        return default
    if isinstance(val, list):
        val = val[0] if val else default
    return str(val).strip("[]'\" ") or default


def get_pg_dsn() -> str:
    host = os.environ.get('PGHOST', 'localhost')
    port = os.environ.get('PGPORT', '5432')
    dbname = os.environ.get('PGDATABASE', 'odoo')
    user = os.environ.get('PGUSER', 'odoo')
    pw = os.environ.get('PGPASSWORD', '')

    try:
        host = _clean(config.get('db_host'), host)
        port = _clean(config.get('db_port'), port)
        dbname = _clean(config.get('db_name'), dbname)
        user = _clean(config.get('db_user'), user)
        pw = _clean(config.get('db_password'), pw)
    except Exception as e:
        _logger.warning('Could not read Odoo db config: %s', e)

    return f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{dbname}" if pw else f"postgresql+psycopg://{user}@{host}:{port}/{dbname}"
