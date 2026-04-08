from sqlalchemy import String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.db.mixins import TimestampMixin


class BlobReferenceModel(Base, TimestampMixin):
    """Blob 引用表。记录哪个业务主体通过哪个语义键引用了某个 Blob，供 GC 判断文件是否仍被使用。"""

    __tablename__ = "blob_reference"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ref_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    blob_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    edge_key: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", "edge_key", name="uq_blob_reference_owner_edge"),
        Index("ix_blob_reference_blob_id", "blob_id"),
        Index("ix_blob_reference_owner", "owner_type", "owner_id"),
    )
