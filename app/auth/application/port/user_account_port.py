from abc import ABC, abstractmethod

from pydantic import BaseModel


class UserAuthInfoDTO(BaseModel):
    """Auth 上下文对用户信息的视图，只含登录所需字段。"""
    user_id: str
    nickname: str
    email: str
    avatar: str | None = None
    roles: list[str] = []


class UserAccountPort(ABC):
    """Auth 上下文对 User 上下文能力的端口接口。"""

    @abstractmethod
    async def find_by_oauth(
        self, *, provider: str, external_uid: str
    ) -> UserAuthInfoDTO | None:
        """按第三方账号查找用户。"""

    @abstractmethod
    async def find_by_unionid(
        self, *, provider: str, union_id: str
    ) -> UserAuthInfoDTO | None:
        """按微信 unionid 查找用户。"""

    @abstractmethod
    async def find_by_phone(self, *, phone: str) -> UserAuthInfoDTO | None:
        """按手机号查找用户。"""

    @abstractmethod
    async def get_oauth_binding_uid(
        self, *, user_id: str, provider: str
    ) -> str | None:
        """返回用户在指定 provider 下已绑定的 external_uid，未绑定返回 None。"""

    @abstractmethod
    async def create_user(
        self, *, email: str, password: str, nickname: str, role: str
    ) -> UserAuthInfoDTO:
        """创建新用户并持久化。"""

    @abstractmethod
    async def bind_phone_and_link_oauth(
        self,
        *,
        user_id: str,
        phone: str | None,
        provider: str,
        external_uid: str,
        union_id: str | None,
        meta: dict,
        link_oauth: bool = True,
    ) -> None:
        """在同一次 load-mutate-save 中完成手机号绑定和第三方账号绑定。
        phone=None 时仅维护第三方绑定。
        link_oauth=False 时不新增第三方绑定。
        """
