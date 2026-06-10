"""
可选 Redis 缓存模块。

当前缓存主要服务 ASR、评分和高频读取场景，用来降低重复模型调用和接口等待时间。Redis 在这个项目里只是加速层，不是数据真源：连接失败、读失败或写失败都只记录 warning 并返回空结果，主流程必须继续回源计算，避免缓存服务波动拖垮答题、转写或重点分析。

@param: 模块本身无入参；业务输入来自调用方传入的缓存 key、JSON 值和 TTL。
@return: 导出 Redis 连接、关闭、JSON 读写函数；缓存不可用时返回 None 或 False。
@raises ImportError: 缺少 redis.asyncio 或配置依赖时会在导入阶段失败。
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
    获取共享连接池上的 Redis 客户端。

    Redis URL 为空或连接池初始化失败时返回 None，而不是抛错；ASR 和评分链路必须能在没有缓存的环境
    继续运行。本函数只创建连接池，不主动验证每个 key 是否存在。

    @param: 无；读取 settings.redis_url 作为连接来源。
    @return: Redis 客户端；缓存未配置或初始化失败时返回 None。
    @raises: 不主动向上抛连接异常；异常会被记录为 warning 并降级。
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
    应用关闭时释放 Redis 连接池。

    FastAPI lifespan 会调用这里。显式断开连接池是为了让部署重启、测试进程和热更新不留下悬挂连接；
    未创建连接池时直接跳过。

    @param: 无；使用模块级连接池状态。
    @return: None。
    @raises Exception: Redis 客户端底层断开异常会向上抛出，lifespan 可统一处理。
    """
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


async def cache_get_json(key: str) -> Any | None:
    """
    从 Redis 读取 JSON 缓存并反序列化。

    读取失败、JSON 损坏或缓存未配置都返回 None，调用方应回源重新计算；这样可以避免一次坏缓存影响
    评分、转写或重点分析主流程。

    @param key: 缓存键；调用方负责包含业务前缀和版本号，避免不同结构共用同一键。
    @return: 反序列化后的 JSON 值；未命中或不可用时返回 None。
    @raises: 不主动向上抛缓存读取异常；异常会被记录为 warning 并降级。
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
    将可 JSON 序列化的结果写入 Redis。

    写缓存失败只返回 False，不回滚业务结果；缓存值必须能被 json.dumps 处理，复杂对象应先在调用处
    转成普通 dict/list，避免把 ORM 或文件句柄塞进缓存层。

    @param key: 缓存键；建议包含业务名和 schema 版本。
    @param value: 可 JSON 序列化的数据。
    @param ttl_seconds: 缓存秒数；小于 1 时按 1 秒兜底。
    @return: True 表示写入成功，False 表示缓存未配置或写入失败。
    @raises: 不主动向上抛缓存写入异常；异常会被记录为 warning 并降级。
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
