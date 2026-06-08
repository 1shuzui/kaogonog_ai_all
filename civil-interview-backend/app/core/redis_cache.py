"""
这个文件把 Redis 当作加速层使用；缓存命中能省时间，缓存失败也不能影响题库、ASR 或评分主流程。

@param: 无；导入文件时不会主动处理业务请求，真正输入来自路由函数、脚本入口或测试用例。
@return: 无直接返回；调用方通过本文件公开的函数、类或路由继续业务流程。
@raises ImportError: 依赖包、配置模块或路径不完整时，文件导入会立即失败。
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
    """
    get_redis 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    缓存模块把 Redis 作为可选加速层，注释需要说明缓存失败不应影响主流程。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
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
    """
    close_redis 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    缓存模块把 Redis 作为可选加速层，注释需要说明缓存失败不应影响主流程。

    @param: 无；该入口依赖模块级配置、框架注入或固定测试上下文。
    @return: None；函数通过写库、注册路由、落盘或抛错体现结果。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


async def cache_get_json(key: str) -> Any | None:
    """
    cache_get_json 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    缓存模块把 Redis 作为可选加速层，注释需要说明缓存失败不应影响主流程。

    @param key: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
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
    """
    cache_set_json 集中封装这段业务边界，是为了让调用方复用同一套校验、降级或兼容策略。

    缓存模块把 Redis 作为可选加速层，注释需要说明缓存失败不应影响主流程。

    @param key: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @param value: 待规范化的原始值；兼容旧数据时应优先保留可解释结果。
    @param ttl_seconds: 调用方传入的原始值；字段名保持不变，方便旧路由、脚本和测试继续复用。
    @return: 返回可直接交给接口、页面或脚本继续使用的数据结构。
    @raises: 不主动包装底层错误；文件、数据库或网络异常会沿调用栈向上传递。
    """
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
