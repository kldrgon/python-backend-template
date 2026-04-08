from sqlalchemy import String, BigInteger, UniqueConstraint, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from core.db import Base
from core.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from core.db.models.storage_locator import StorageLocatorModel


class BlobModel(Base, TimestampMixin):
    __tablename__ = "blob"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    blob_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    blob_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # 改为可空，移除唯一约束
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="temporary", index=True)

    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    storage_locator_id: Mapped[int | None] = mapped_column(ForeignKey("storage_locator.id"), nullable=True, index=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_class: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)  # 添加状态字段

    # 关系
    storage_locator: Mapped["StorageLocatorModel | None"] = relationship("StorageLocatorModel", lazy="joined")  # 一对一关系，使用 JOIN 自动加载

    __table_args__ = (
        Index("ix_blob_created_at", "created_at"),
        Index("ix_blob_status", "status"),
        Index("ix_blob_sha256", "blob_sha256"),
        Index("ix_blob_kind", "kind"),
    )


