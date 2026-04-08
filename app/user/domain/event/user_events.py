from pydantic import BaseModel
from pami_event_framework import DomainEvent


# ============ UserCreated ============
class UserCreatedPayload(BaseModel):
    user_id: str
    email: str
    nickname: str


class UserCreatedEvent(DomainEvent):
    """用户创建事件 - 柔性（失败不影响核心流程）"""
    event_type = "USER_CREATED"
    strict = False  # 柔性：处理器失败后有限重试
    
    def __init__(self, *, user_id: str, email: str, nickname: str):
        super().__init__(user_id=user_id, email=email, nickname=nickname)


# ============ UserThirdPartyLinked ============
class UserThirdPartyLinkedPayload(BaseModel):
    user_id: str
    provider: str
    external_uid: str


class UserThirdPartyLinkedEvent(DomainEvent):
    """用户绑定第三方账号事件 - 柔性"""
    event_type = "USER_THIRD_PARTY_LINKED"
    strict = False
    
    def __init__(self, *, user_id: str, provider: str, external_uid: str):
        super().__init__(user_id=user_id, provider=provider, external_uid=external_uid)


# ============ UserThirdPartyUnlinked ============
class UserThirdPartyUnlinkedPayload(BaseModel):
    user_id: str
    provider: str
    external_uid: str


class UserThirdPartyUnlinkedEvent(DomainEvent):
    """用户解绑第三方账号事件 - 柔性"""
    event_type = "USER_THIRD_PARTY_UNLINKED"
    strict = False
    
    def __init__(self, *, user_id: str, provider: str, external_uid: str):
        super().__init__(user_id=user_id, provider=provider, external_uid=external_uid)


# ============ UserEnabled ============
class UserEnabledPayload(BaseModel):
    user_id: str


class UserEnabledEvent(DomainEvent):
    """用户启用事件 - 柔性"""
    event_type = "USER_ENABLED"
    strict = False
    
    def __init__(self, *, user_id: str):
        super().__init__(user_id=user_id)


# ============ UserDisabled ============
class UserDisabledPayload(BaseModel):
    user_id: str


class UserDisabledEvent(DomainEvent):
    """用户禁用事件 - 柔性"""
    event_type = "USER_DISABLED"
    strict = False
    
    def __init__(self, *, user_id: str):
        super().__init__(user_id=user_id)


# ============ UserRolesAssigned ============
class UserRolesAssignedPayload(BaseModel):
    user_id: str
    roles: list[str]


class UserRolesAssignedEvent(DomainEvent):
    """用户角色分配事件 - 柔性"""
    event_type = "USER_ROLES_ASSIGNED"
    strict = False
    
    def __init__(self, *, user_id: str, roles: list[str]):
        super().__init__(user_id=user_id, roles=roles)


# ============ UserRolesRevoked ============
class UserRolesRevokedPayload(BaseModel):
    user_id: str
    roles: list[str]


class UserRolesRevokedEvent(DomainEvent):
    """用户角色撤销事件 - 柔性"""
    event_type = "USER_ROLES_REVOKED"
    strict = False
    
    def __init__(self, *, user_id: str, roles: list[str]):
        super().__init__(user_id=user_id, roles=roles)


# ============ UserProfileUpdated ============
class UserProfileUpdatedPayload(BaseModel):
    user_id: str
    changed: dict[str, tuple[str | None, str | None]]


class UserProfileUpdatedEvent(DomainEvent):
    """用户资料更新事件 - 柔性"""
    event_type = "USER_PROFILE_UPDATED"
    strict = False
    
    def __init__(self, *, user_id: str, changed: dict[str, tuple[str | None, str | None]]):
        super().__init__(user_id=user_id, changed=changed)


# ============ UserPasswordSet ============
class UserPasswordSetPayload(BaseModel):
    user_id: str


class UserPasswordSetEvent(DomainEvent):
    """用户密码设置事件 - 柔性"""
    event_type = "USER_PASSWORD_SET"
    strict = False
    
    def __init__(self, *, user_id: str):
        super().__init__(user_id=user_id)
