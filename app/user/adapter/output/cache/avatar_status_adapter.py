from app.user.application.port.avatar_status_port import AvatarStatusPort
from core.helpers.redis import get_redis_client
from core.config import config


class RedisAvatarStatusAdapter(AvatarStatusPort):
    """用 Redis 实现头像状态的读写。"""

    async def set_approved(self, *, user_id: str) -> None:
        redis = get_redis_client()
        await redis.setex(
            f"{config.user.avatar_status_key_prefix}{user_id}",
            config.user.avatar_status_ttl,
            "APPROVED",
        )

    async def get_status(self, *, user_id: str) -> str:
        redis = get_redis_client()
        status = await redis.get(f"{config.user.avatar_status_key_prefix}{user_id}")
        return status or "PENDING"
