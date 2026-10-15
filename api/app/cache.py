"""Redis-backed JSON cache + a small fixed-window rate limiter."""
import json
import time
from typing import Any, Awaitable, Callable, Optional

import redis.asyncio as redis

from .config import settings

_pool: Optional[redis.Redis] = None


def client() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _pool


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def ping() -> bool:
    try:
        return bool(await client().ping())
    except Exception:
        return False


async def get_json(key: str) -> Optional[Any]:
    try:
        raw = await client().get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def set_json(key: str, value: Any, ttl: int) -> None:
    try:
        await client().set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass


async def cached_json(
    key: str,
    ttl: int,
    producer: Callable[[], Awaitable[Any]],
) -> tuple[Any, bool]:
    """Return (value, cache_hit). Falls back to producer on any Redis error."""
    hit = await get_json(key)
    if hit is not None:
        return hit, True
    value = await producer()
    if value is not None:
        await set_json(key, value, ttl)
    return value, False


async def rate_limit_ok(identity: str) -> bool:
    """Fixed-window limiter: at most N requests per window per identity."""
    if settings.rate_limit_requests <= 0:
        return True
    window = int(time.time()) // settings.rate_limit_window
    key = f"ratelimit:{identity}:{window}"
    try:
        n = await client().incr(key)
        if n == 1:
            await client().expire(key, settings.rate_limit_window)
        return n <= settings.rate_limit_requests
    except Exception:
        return True  # fail-open if Redis is unavailable
