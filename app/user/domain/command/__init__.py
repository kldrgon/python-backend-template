from pydantic import BaseModel
from .roles_assign import UserRolesAssignCommand
from .update_profile import UpdateUserProfileCommand
from .set_avatar import SetAvatarCommand
from app.user.domain.vo.user_role import UserRole

class CreateUserCommand(BaseModel):
    email: str
    nickname: str
    password: str
    confirmPassword: str
    role: UserRole
    agreed: bool 


__all__ = [
    "UserRolesAssignCommand",
    "CreateUserCommand",
    "UpdateUserProfileCommand",
    "SetAvatarCommand"
]