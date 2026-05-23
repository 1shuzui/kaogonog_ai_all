"""Best-effort Redis cache helpers.

Redis must never be a hard dependency for scoring or ASR. These helpers return
None/False when Redis is unavailable so callers can continue with the normal
database/model path.
"""
import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[aioredis.ConnectionPool] = None


def _redis_url() -> str:
    return str(settings.redis_url or "").strip()


async def get_redis() -> Optional[aioredis.Redis]:
    global _pool
    redis_url = _redis_url()
    if not redis_url:
        return None
    try:
        if _pool is None:
            _pool = aioredis.ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.8,
            )
        return aioredis.Redis(connection_pool=_pool)
    except Exception as exc:
        logger.warning("Redis cache init skipped: %s", exc)
        return None


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


async def cache_get_json(key: str) -> Any | None:
    client = await get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("Redis cache read skipped for %s: %s", key, exc)
        return None


async def cache_set_json(key: str, value: Any, ttl_seconds: int) -> bool:
    client = await get_redis()
    if client is None:
        return False
    try:
        await client.setex(
            key,
            max(1, int(ttl_seconds or 1)),
            json.dumps(value, ensure_ascii=False, separators=(",", ":")),
        )
        return True
    except Exception as exc:
        logger.warning("Redis cache write skipped for %s: %s", key, exc)
        return False
