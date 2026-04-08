from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class BlobBriefDTO(BaseModel):
    blob_id: str
    blob_sha256: str | None = None  # 可能尚未计算
    kind: str | None = None
    size_bytes: int
    mime_type: str | None = None
    display_name: str | None = None
    status: str | None = None  # 处理状态


class BlobDetailDTO(BlobBriefDTO):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GcCandidateDTO(BaseModel):
    blob_id: str
    blob_sha256: str
    size_bytes: int
    created_at: datetime | None = None

