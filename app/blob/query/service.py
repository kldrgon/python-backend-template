from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .dto import BlobDetailDTO, GcCandidateDTO


class BlobQueryService(Protocol):
    """Blob 读侧查询服务接口。
    
    与写侧分离，直接使用 ORM 查询以获得最佳性能。
    """
    
    async def get(self, *, blob_id: str) -> BlobDetailDTO | None:
        """根据 ID 获取 Blob 详情"""
        ...

    async def get_by_hash(self, *, blob_sha256: str) -> BlobDetailDTO | None:
        """根据哈希获取 Blob 详情（返回第一个有 storage_locator 的）"""
        ...
    
    async def list_by_hash(self, *, blob_sha256: str) -> list[BlobDetailDTO]:
        """根据哈希获取所有 Blob"""
        ...

    async def list_gc_candidates(
        self, *, limit: int = 50, older_than: datetime | None = None
    ) -> list[GcCandidateDTO]:
        """列出垃圾回收候选"""
        ...
    


