from abc import ABC, abstractmethod
from app.user.domain.aggregate.user import User
from app.user.domain.command import CreateUserCommand
from app.user.domain.command.roles_assign import UserRolesAssignCommand
from app.user.domain.command.update_profile import UpdateUserProfileCommand
from app.user.domain.command.set_avatar import SetAvatarCommand
from app.user.domain.command.user import UserGetByUsernameCommand, UserGetByIdCommand
from app.user.application.dto import LoginResponseDTO
from app.user.application.dto.user import UserReadDTO


class UserUseCase(ABC):

    # ── 命令 ──────────────────────────────────────────

    @abstractmethod
    async def create_user(self, *, command: CreateUserCommand) -> User:
        """创建用户"""

    @abstractmethod
    async def is_admin(self, *, user_id: str) -> bool:
        """判断是否为超级管理员"""

    @abstractmethod
    async def assign_roles(self, *, command: UserRolesAssignCommand) -> bool:
        """分配业务角色"""

    @abstractmethod
    async def update_profile(self, *, command: UpdateUserProfileCommand) -> User:
        """更新用户档案"""

    @abstractmethod
    async def set_avatar(self, *, command: SetAvatarCommand) -> User:
        """设置用户头像"""

    @abstractmethod
    async def send_registration_captcha(self, *, email: str) -> int:
        """生成并发送注册验证码，含发送频率校验。返回验证码有效期（秒）。"""

    @abstractmethod
    async def register_with_captcha(self, *, command: CreateUserCommand, captcha_code: str) -> User:
        """校验验证码后创建用户，成功后删除验证码。"""

    # ── 查询 ──────────────────────────────────────────

    @abstractmethod
    async def login(self, *, email: str, password: str) -> LoginResponseDTO:
        """邮箱密码登录，返回 Token"""

    @abstractmethod
    async def get_by_user_id(self, *, command: UserGetByIdCommand) -> UserReadDTO:
        """按 user_id 查询用户档案"""

    @abstractmethod
    async def get_by_username(self, *, command: UserGetByUsernameCommand) -> UserReadDTO:
        """按昵称查询用户档案"""

    @abstractmethod
    async def get_user_list(self, *, limit: int, prev: int | None) -> list[UserReadDTO]:
        """分页获取用户列表"""
