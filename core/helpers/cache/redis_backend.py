import pickle
from typing import Any

import ujson

from core.helpers.cache.base import BaseBackend
from core.helpers.redis import get_redis_client


class RedisBackend(BaseBackend):
    async def get(self, *, key: str) -> Any:
        result = await get_redis_client().get(key)
        if not result:
            return

        return ujson.loads(result)

    async def set(self, *, response: Any, key: str, ttl: int = 60) -> None:
        if isinstance(response, dict):
            response = ujson.dumps(response)
        else:
            response = pickle.dumps(response)

        await get_redis_client().set(name=key, value=response, ex=ttl)

    async def delete_startswith(self, *, value: str) -> None:
        client = get_redis_client()
        async for key in client.scan_iter(f"{value}*"):
            await client.delete(key)
