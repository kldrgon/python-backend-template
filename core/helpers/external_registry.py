from __future__ import annotations

from typing import Any, Dict, Optional

from core.helpers.redis import get_redis_client


DEFAULT_TTL_SECONDS = 30 * 24 * 3600  # 30 days


def _ext_key(event_id: str, handler_key: str) -> str:
    return f"ext:{event_id}:{handler_key}"


async def save_external_artifact(
    *, event_id: str, handler_key: str, data: Dict[str, Any], ttl_seconds: int = DEFAULT_TTL_SECONDS
) -> None:
    redis_client = get_redis_client()
    key = _ext_key(event_id, handler_key)
    # 扁平化字典为字符串字段，使用 HMSET 存储
    mapping: Dict[str, str] = {}
    for k, v in (data or {}).items():
        if v is None:
            continue
        mapping[str(k)] = str(v)
    if mapping:
        await redis_client.hset(key, mapping=mapping)
    await redis_client.expire(key, ttl_seconds)


async def get_external_artifact(*, event_id: str, handler_key: str) -> Dict[str, str]:
    redis_client = get_redis_client()
    key = _ext_key(event_id, handler_key)
    res = await redis_client.hgetall(key)
    return res or {}


async def delete_external_artifact(*, event_id: str, handler_key: str) -> None:
    redis_client = get_redis_client()
    key = _ext_key(event_id, handler_key)
    try:
        await redis_client.delete(key)
    except Exception:
        # 清理失败不应影响主流程
        pass


