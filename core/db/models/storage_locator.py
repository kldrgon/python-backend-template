from sqlalchemy import String, UniqueConstraint, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base
from core.db.mixins import TimestampMixin


class StorageLocatorModel(Base, TimestampMixin):
    """存储位置表，多个 Blob 可以共享同一个存储位置（通过 hash256 去重）。"""
    __tablename__ = "storage_locator"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 数据库自增主键，仅用于外键关联
    storage_locator_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)  # UUID hex 业务标识符
    storage_provider: Mapped[str] = mapped_column(String(255), nullable=False)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # SHA256 哈希值（从 Blob 同步）

    __table_args__ = (
        UniqueConstraint("storage_locator_id", name="uq_storage_locator_id"),
        Index("ix_storage_locator_provider_bucket", "storage_provider", "bucket"),
        Index("ix_storage_locator_sha256", "sha256"),
    )

