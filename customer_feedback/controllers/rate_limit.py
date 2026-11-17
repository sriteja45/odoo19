# -*- coding: utf-8 -*-
"""Lightweight in-process rate limiter for public feedback routes.

Uses Odoo's registry-level cache (shared per worker process). This is not a
distributed rate limiter: multi-worker deployments get per-worker budgets,
which is still enough to blunt casual abuse and token-guessing without
introducing Redis/external dependencies.

Limits are configurable via ir.config_parameter (integers, requests per window):
  customer_feedback.rate_limit_token_per_min      (default 30)
  customer_feedback.rate_limit_submit_per_min     (default 10)
  customer_feedback.rate_limit_vote_per_min       (default 60)
  customer_feedback.rate_limit_public_get_per_min (default 120)
"""
import logging
import time

from odoo.http import request

_logger = logging.getLogger(__name__)

# route_key -> default max requests per 60-second window
_DEFAULTS = {
    'token': 30,
    'submit': 10,
    'vote': 60,
    'public_get': 120,
}

_PARAM_KEYS = {
    'token': 'customer_feedback.rate_limit_token_per_min',
    'submit': 'customer_feedback.rate_limit_submit_per_min',
    'vote': 'customer_feedback.rate_limit_vote_per_min',
    'public_get': 'customer_feedback.rate_limit_public_get_per_min',
}

_WINDOW_SECONDS = 60


def _client_ip():
    """Best-effort client IP (respect common reverse-proxy header once)."""
    try:
        httprequest = request.httprequest
        forwarded = httprequest.environ.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            # First hop only — do not trust arbitrary chain depth.
            return forwarded.split(',')[0].strip() or httprequest.remote_addr
        return httprequest.remote_addr or 'unknown'
    except Exception:
        return 'unknown'


def _limit_for(route_key):
    default = _DEFAULTS.get(route_key, 60)
    param = _PARAM_KEYS.get(route_key)
    if not param:
        return default
    try:
        raw = request.env['ir.config_parameter'].sudo().get_param(param, default)
        value = int(raw)
        # Clamp to a sane range so a misconfiguration cannot open a floodgate
        # or lock everyone out with 0.
        return max(5, min(value, 10000))
    except (TypeError, ValueError):
        return default


def check_rate_limit(route_key, extra_key=None):
    """Return None if allowed, or a short reason string if limited.

    ``extra_key`` can bind the bucket to a token or review id so one abused
    token does not exhaust the whole IP budget for unrelated traffic.
    """
    ip = _client_ip()
    limit = _limit_for(route_key)
    now = int(time.time())
    window = now // _WINDOW_SECONDS
    parts = ['cf_rl', route_key, ip, str(window)]
    if extra_key:
        parts.append(str(extra_key)[:64])
    cache_key = '|'.join(parts)

    try:
        # Registry cache is process-local and survives across requests in the
        # same worker — adequate for abuse damping without external deps.
        cache = request.env.registry._customer_feedback_rate_limit_cache
    except AttributeError:
        cache = {}
        request.env.registry._customer_feedback_rate_limit_cache = cache

    # Opportunistic prune of old windows to avoid unbounded growth.
    if len(cache) > 5000:
        stale_prefix_end = str(window - 2)
        for key in list(cache.keys()):
            # keys look like cf_rl|route|ip|window|...
            bits = key.split('|')
            if len(bits) >= 4 and bits[3].isdigit() and int(bits[3]) < window - 1:
                cache.pop(key, None)

    count = cache.get(cache_key, 0) + 1
    cache[cache_key] = count
    if count > limit:
        _logger.warning(
            'Customer Feedback rate limit hit: route=%s ip=%s count=%s limit=%s',
            route_key, ip, count, limit,
        )
        return 'Rate limit exceeded. Please try again later.'
    return None
