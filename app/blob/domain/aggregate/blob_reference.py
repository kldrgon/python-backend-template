from __future__ import annotations

from typing import Optional
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict
from pami_event_framework import AggregateRoot


class BlobReference(AggregateRoot, BaseModel):
    """
    Blob 引用聚合根。

    记录哪个业务主体（owner）通过哪个语义键（edge_key）引用了某个 Blob。
    生命周期独立于 Blob：引用可以先于 Blob 被清理，也可以在 Blob 存在期间任意增减。

    GC 通过查询"无引用的 PERMANENT Blob"来决定哪些文件可以被删除。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    ref_id: str = Field(..., description="聚合根 ID（UUID hex）")
    blob_id: str = Field(..., description="关联 Blob 的 ID（通过 ID 引用，不持有对象）")
    owner_type: str = Field(..., description="引用方类型，如 'user'、'post'")
    owner_id: str = Field(..., description="引用方 ID")
    edge_key: str = Field(..., description="语义键，如 'avatar'、'cover'、'attachment'")
    created_at: Optional[datetime] = None

    def __init__(self, **kwargs):
        AggregateRoot.__init__(self)
        BaseModel.__init__(self, **kwargs)

    def get_aggregate_id(self) -> str:
        return self.ref_id

    @classmethod
    def create(
        cls,
        *,
        blob_id: str,
        owner_type: str,
        owner_id: str,
        edge_key: str,
    ) -> "BlobReference":
        """创建新的 BlobReference。"""
        return cls(
            ref_id=uuid4().hex,
            blob_id=blob_id,
            owner_type=owner_type,
            owner_id=owner_id,
            edge_key=edge_key,
        )

    def __str__(self) -> str:
        return (
            f"BlobReference(ref_id={self.ref_id}, blob_id={self.blob_id}, "
            f"owner={self.owner_type}:{self.owner_id}, edge_key={self.edge_key})"
        )
