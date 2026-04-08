from abc import ABC, abstractmethod
from app.user.domain.aggregate.user import User


class UserRepository(ABC):

    @abstractmethod
    async def get_users(self, *, limit: int = 12, prev: int | None = None) -> list[User]:
        """分页获取用户列表"""

    @abstractmethod
    async def get_user_by_email_or_nickname(
        self, *, email: str | None = None, nickname: str | None = None
    ) -> User | None:
        """按邮箱或昵称查找用户"""

    @abstractmethod
    async def get_user_by_id(self, *, user_id: str) -> User | None:
        """按 user_id 查找用户"""

    @abstractmethod
    async def get_user_by_phone(self, *, phone: str) -> User | None:
        """按手机号查找用户"""

    @abstractmethod
    async def get_user_by_email(self, *, email: str) -> User | None:
        """按邮箱精确查找用户"""

    @abstractmethod
    async def get_user_by_linked_account(
        self, *, provider: str, provider_account_id: str
    ) -> User | None:
        """按第三方账号查找用户"""

    @abstractmethod
    async def get_user_by_wechat_unionid(
        self, *, provider: str, union_id: str
    ) -> User | None:
        """按微信 unionid 查找用户"""

    @abstractmethod
    async def save(self, *, user: User) -> None:
        """保存用户（新增或更新）"""
