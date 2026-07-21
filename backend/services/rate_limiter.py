"""
rate_limiter.py — Redis-based sliding-window rate limiter.

30 prompts / hour / session (configurable via RATE_LIMIT_PROMPTS_PER_HOUR).
Key: ratelimit:session:{session_id}:{hour_bucket}  TTL = 3600 s

Fix: INCR + EXPIRE are now executed atomically via a Lua script.
The previous pipeline approach had a race: if the connection dropped after
INCR but before EXPIRE on a brand-new key, that key would persist forever
without an expiry, effectively blocking the user permanently.
The Lua script runs server-side and cannot be interrupted mid-execution.
"""
from __future__ import annotations

from datetime import datetime, timezone

import redis

from backend.core.config import get_settings

settings = get_settings()

_redis_client: redis.Redis | None = None

# Lua script: atomically increment a counter and set its TTL only on first use.
# KEYS[1] = the rate-limit key
# ARGV[1] = TTL in seconds (3600)
_INCR_AND_EXPIRE_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
end
return count
"""


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _bucket_key(user_id: str) -> str:
    hour_bucket = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H")
    return f"ratelimit:user:{user_id}:{hour_bucket}"


def check_and_increment(user_id: str) -> tuple[bool, int]:
    """
    Check if the user is within rate limit, then increment atomically.
    Returns (allowed: bool, current_count: int).
    Falls back to (True, 0) if Redis is unavailable (local dev).
    """
    try:
        r = _get_redis()
        key = _bucket_key(user_id)
        limit = settings.rate_limit_prompts_per_hour

        # Atomic increment + conditional TTL-set via Lua
        current_count = int(r.eval(_INCR_AND_EXPIRE_LUA, 1, key, 3600))

        if current_count > limit:
            return False, current_count
        return True, current_count
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Redis unavailable — rate limiting disabled: %s", exc
        )
        return True, 0


def get_current_count(user_id: str) -> int:
    """Return current prompt count for this user in the current hour."""
    try:
        r = _get_redis()
        key = _bucket_key(user_id)
        val = r.get(key)
        return int(val) if val else 0
    except Exception:
        return 0
