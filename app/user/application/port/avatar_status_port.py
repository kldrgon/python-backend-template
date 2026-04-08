from abc import ABC, abstractmethod


class AvatarStatusPort(ABC):
    """头像处理状态的读写能力端口。"""

    @abstractmethod
    async def set_approved(self, *, user_id: str) -> None:
        """将指定用户的头像状态标记为 APPROVED。"""

    @abstractmethod
    async def get_status(self, *, user_id: str) -> str:
        """获取指定用户的头像处理状态，未设置时返回 'PENDING'。"""
