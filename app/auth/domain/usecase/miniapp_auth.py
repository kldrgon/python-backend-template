from abc import ABC, abstractmethod

from app.auth.application.dto.miniapp_auth import MiniappBindResponseDTO
from app.auth.domain.command.miniapp_bind import MiniappBindCommand


class MiniappAuthUseCase(ABC):
    """小程序认证用例接口：绑定登录、openid 重登录。"""

    @abstractmethod
    async def bind_and_login(self, *, command: MiniappBindCommand) -> MiniappBindResponseDTO:
        """小程序首次绑定并登录（openid + 手机号）。"""

    @abstractmethod
    async def login_or_register(
        self,
        *,
        openid: str,
        unionid: str | None = None,
        session_meta: dict | None = None,
    ) -> MiniappBindResponseDTO:
        """按微信身份登录，不存在则自动创建无手机号账号。"""

    @abstractmethod
    async def login_by_openid(self, *, openid: str) -> MiniappBindResponseDTO:
        """按 openid 登录（需已完成 bind）。"""
