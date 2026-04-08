import structlog
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
from app.user.domain.vo.location import Address
from pami_event_framework import AggregateRoot
from app.user.domain.entity.linked_account import LinkedAccount
from app.user.domain.event.user_events import (
    UserCreatedEvent,
    UserEnabledEvent,
    UserDisabledEvent,
    UserRolesAssignedEvent,
    UserRolesRevokedEvent,
    UserProfileUpdatedEvent,
    UserPasswordSetEvent,
    UserThirdPartyLinkedEvent,
    UserThirdPartyUnlinkedEvent,
)
from core.helpers.password import hash_password
from app.user.domain.exception import (
    InvalidEmailError,
    WeakPasswordError,
    EmptyNicknameError,
    DisabledUserCannotBeAssignedRolesError,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class User(AggregateRoot, BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    # ── 身份 ──────────────────────────────────────────
    user_id: str
    email: str
    hashed_password: str
    phone: str | None = None
    enabled: bool = True
    is_admin: bool = False  # 超级管理员，平台级；业务角色用 roles

    # ── 档案 ──────────────────────────────────────────
    nickname: str
    org_name: str | None = None
    bio: str | None = None
    avatar: str | None = None          # 存 blob_id
    location: Address | None = None    # 省市区

    # ── 权限 ──────────────────────────────────────────
    roles: list[str] = Field(default_factory=list)  # TEACHER / STUDENT 等业务角色

    # ── 第三方绑定 ────────────────────────────────────
    linked_accounts: list[LinkedAccount] = Field(default_factory=list)

    _domain_events: list = PrivateAttr(default_factory=list)

    def __init__(self, **kwargs):
        AggregateRoot.__init__(self)
        BaseModel.__init__(self, **kwargs)

    def get_aggregate_id(self) -> str:
        return self.user_id

    @classmethod
    def create(
        cls, *, user_id: str, email: str, password: str, nickname: str, role: str
    ) -> "User":
        if not email or "@" not in email:
            raise InvalidEmailError(email=email)
        if not password or len(password) < 6:
            raise WeakPasswordError()
        if not nickname:
            raise EmptyNicknameError()

        logger.info("user_creating", user_id=user_id, email=email, nickname=nickname, role=role)
        instance = cls(
            user_id=user_id,
            email=email,
            hashed_password=hash_password(password),
            nickname=nickname,
            is_admin=False,
            roles=[],
            avatar=None,
        )

        if role:
            instance.assign_roles([role])

        instance.raise_event(UserCreatedEvent(user_id=user_id, email=email, nickname=nickname))
        return instance

    # ── 状态行为 ──────────────────────────────────────

    def enable(self) -> None:
        if not self.enabled:
            self.enabled = True
            self.raise_event(UserEnabledEvent(user_id=self.user_id))

    def disable(self) -> None:
        if self.enabled:
            self.enabled = False
            self.raise_event(UserDisabledEvent(user_id=self.user_id))

    # ── 权限行为 ──────────────────────────────────────

    def assign_roles(self, roles: list[str]) -> None:
        if not self.enabled:
            raise DisabledUserCannotBeAssignedRolesError(user_id=self.user_id)
        before = set(self.roles)
        after = sorted(before.union(roles))
        added = sorted(set(after) - before)
        self.roles = after
        if added:
            self.raise_event(UserRolesAssignedEvent(user_id=self.user_id, roles=added))

    def revoke_roles(self, roles: list[str]) -> None:
        before = set(self.roles)
        after = sorted(before - set(roles))
        removed = sorted(before - set(after))
        self.roles = after
        if removed:
            self.raise_event(UserRolesRevokedEvent(user_id=self.user_id, roles=removed))

    # ── 档案行为 ──────────────────────────────────────

    def update_profile(
        self,
        *,
        nickname: str | None = None,
        org_name: str | None = None,
        bio: str | None = None,
        location: Address | None = None,
    ) -> None:
        changed: dict[str, tuple] = {}

        if nickname is not None and nickname != self.nickname:
            changed["nickname"] = (self.nickname, nickname)
            self.nickname = nickname

        if org_name is not None and org_name != self.org_name:
            changed["org_name"] = (self.org_name, org_name)
            self.org_name = org_name

        if bio is not None and bio != self.bio:
            changed["bio"] = (self.bio, bio)
            self.bio = bio

        if location is not None:
            old = (self.location.province, self.location.city, self.location.district) if self.location else None
            new = (location.province, location.city, location.district)
            if old != new:
                changed["location"] = (old, new)
                self.location = location

        if changed:
            self.raise_event(UserProfileUpdatedEvent(user_id=self.user_id, changed=changed))

    def set_phone(self, *, phone: str) -> None:
        if phone != self.phone:
            changed = {"phone": (self.phone, phone)}
            self.phone = phone
            self.raise_event(UserProfileUpdatedEvent(user_id=self.user_id, changed=changed))

    def set_avatar(self, *, avatar: str) -> None:
        if avatar != self.avatar:
            changed = {"avatar": (self.avatar, avatar)}
            self.avatar = avatar
            self.raise_event(UserProfileUpdatedEvent(user_id=self.user_id, changed=changed))

    def set_password(self, *, password: str) -> None:
        if not password or len(password) < 6:
            raise WeakPasswordError()
        self.hashed_password = hash_password(password)
        self.raise_event(UserPasswordSetEvent(user_id=self.user_id))

    # ── 第三方账号绑定行为 ────────────────────────────

    def link_account(self, *, account: LinkedAccount) -> None:
        exists = next(
            (a for a in self.linked_accounts
             if a.provider == account.provider and a.provider_account_id == account.provider_account_id),
            None,
        )
        if exists:
            return
        self.linked_accounts.append(account)
        self.raise_event(
            UserThirdPartyLinkedEvent(
                user_id=self.user_id,
                provider=account.provider,
                external_uid=account.provider_account_id,
            )
        )

    def unlink_account(self, *, provider: str, provider_account_id: str) -> None:
        before_len = len(self.linked_accounts)
        self.linked_accounts = [
            a for a in self.linked_accounts
            if not (a.provider == provider and a.provider_account_id == provider_account_id)
        ]
        if len(self.linked_accounts) != before_len:
            self.raise_event(
                UserThirdPartyUnlinkedEvent(
                    user_id=self.user_id,
                    provider=provider,
                    external_uid=provider_account_id,
                )
            )


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    nickname: str
