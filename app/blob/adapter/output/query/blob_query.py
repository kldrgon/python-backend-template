from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from core.db.session import session_factory, session

from core.db.models.blob import BlobModel
from core.db.models.storage_locator import StorageLocatorModel
from app.blob.query.dto import BlobDetailDTO, GcCandidateDTO, BlobBriefDTO
from app.blob.domain.domain_service.blob_domain_service import BlobDomainService
from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.vo.hash import SHA256Hash


class SQLAlchemyBlobQueryService:
    def __init__(self, blob_domain_service: BlobDomainService | None = None) -> None:
        """Blob 读侧查询服务的 SQLAlchemy 实现。

        当注入了 `blob_domain_service` 时，GC 候选的业务规则统一复用领域服务，
        否则回退到本地 SQL 计算逻辑（向后兼容）。
        """
        self._blob_domain_service = blob_domain_service

    async def get(self, *, blob_id: str) -> BlobDetailDTO | None:
        stmt = select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(BlobModel.blob_id == blob_id)
        async with session_factory() as read_session:
            row = (await read_session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_detail_dto(row)

    async def get_by_hash(self, *, blob_sha256: str) -> BlobDetailDTO | None:
        """返回第一个有 storage_locator 的 Blob（用于去重）。"""
        stmt = select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(
            and_(
                BlobModel.blob_sha256 == blob_sha256,
                BlobModel.storage_locator_id.isnot(None),
            )
        ).limit(1)
        async with session_factory() as read_session:
            row = (await read_session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_detail_dto(row)
    
    async def list_by_hash(self, *, blob_sha256: str) -> List[BlobDetailDTO]:
        """返回所有具有相同 hash256 的 Blob（用于查询 ref）。"""
        stmt = select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(BlobModel.blob_sha256 == blob_sha256)
        async with session_factory() as read_session:
            rows = (await read_session.execute(stmt)).scalars().all()
        return [self._to_detail_dto(r) for r in rows]

    async def list_gc_candidates(
        self, *, limit: int = 50, older_than: datetime | None = None
    ) -> List[GcCandidateDTO]:
        """查找垃圾回收候选。"""
        if self._blob_domain_service is not None:
            blobs = await self._blob_domain_service.find_gc_candidates(
                limit=limit,
                older_than=older_than,
            )
            return [
                GcCandidateDTO(
                    blob_id=b.blob_id,
                    blob_sha256=str(b.blob_sha256) if b.blob_sha256 else None,
                    size_bytes=b.size_bytes,
                    created_at=b.created_at,
                )
                for b in blobs
            ]

        stmt = select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(
            and_(
                BlobModel.storage_locator_id.isnot(None),
                BlobModel.kind == "temporary",
            )
        )
        if older_than is not None:
            stmt = stmt.where(BlobModel.created_at < older_than)
        stmt = stmt.order_by(BlobModel.id.asc()).limit(min(limit, 200))
        async with session_factory() as read_session:
            rows = (await read_session.execute(stmt)).scalars().all()
        return [
            GcCandidateDTO(
                blob_id=r.blob_id,
                blob_sha256=r.blob_sha256 or "",
                size_bytes=r.size_bytes,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def _to_detail_dto(self, r: BlobModel) -> BlobDetailDTO:
        return BlobDetailDTO(
            blob_id=r.blob_id,
            blob_sha256=r.blob_sha256,
            kind=getattr(r, "kind", None),
            size_bytes=r.size_bytes,
            mime_type=r.mime_type,
            display_name=r.display_name,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
