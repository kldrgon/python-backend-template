from abc import ABC, abstractmethod


class AvatarUrlPort(ABC):
    """获取头像可访问 URL 的能力端口。"""

    @abstractmethod
    async def get_avatar_url(self, *, blob_id: str) -> str | None:
        """根据 blob_id 返回可访问的头像 URL，不存在时返回 None。"""
