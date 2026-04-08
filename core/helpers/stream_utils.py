from __future__ import annotations

import structlog

from core.helpers.redis import get_redis_client

_logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def ensure_consumer_group(*, stream: str, group: str, start_id: str = "$", setid_on_exists: str | None = None) -> None:
    """确保 Redis Stream 的消费组存在。

    - 若消费组不存在：使用给定的 `start_id` 创建（`"$"` 表示仅从新消息开始，`"0"` 表示从头开始）
    - 若消费组已存在且提供了 `setid_on_exists`：将组的游标（last-delivered-id）重置为该 ID
    """
    redis_client = get_redis_client()
    try:
        await redis_client.xgroup_create(name=stream, groupname=group, id=start_id, mkstream=True)
        _logger.info("redis_stream_group_created", stream=stream, group=group, start_id=start_id)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise
        if setid_on_exists:
            try:
                await redis_client.xgroup_setid(name=stream, groupname=group, id=setid_on_exists)
                _logger.info("redis_stream_group_cursor_reset", stream=stream, group=group, setid=setid_on_exists)
            except Exception as se:
                _logger.warning("redis_stream_group_setid_failed", stream=stream, group=group, error=str(se))


