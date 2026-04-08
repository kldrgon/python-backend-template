from sqlalchemy import String, ForeignKey, JSON, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base
from core.db.mixins import TimestampMixin


class UserModel(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column("hashed_password", String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True, index=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    enabled: Mapped[bool] = mapped_column(default=True)

    # 档案
    org_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # 省市区地址，JSON存储：{"province": "", "city": "", "district": ""}
    location: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # relationships
    roles_rel: Mapped[list["UserRoleModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
        primaryjoin="UserRoleModel.user_id==UserModel.user_id",
        foreign_keys="UserRoleModel.user_id",
    )
    linked_accounts_rel: Mapped[list["UserLinkedAccountModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
        primaryjoin="UserLinkedAccountModel.user_id==UserModel.user_id",
        foreign_keys="UserLinkedAccountModel.user_id",
    )


class UserRoleModel(Base, TimestampMixin):
    __tablename__ = "user_role"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    user: Mapped["UserModel"] = relationship(back_populates="roles_rel")
    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_user_role_user_id_role"),
    )


class UserLinkedAccountModel(Base, TimestampMixin):
    __tablename__ = "user_linked_account"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # OAuth 登录预留字段
    access_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    id_token: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    # 平台特有原始数据（如微信 union_id 等）
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped["UserModel"] = relationship(back_populates="linked_accounts_rel")
    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uq_linked_account_provider_account"),
    )
