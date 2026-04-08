from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from app.blob.domain.domain_service.blob_domain_service import BlobDomainService
from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.repository.blob import BlobRepository
from app.blob.domain.vo.hash import SHA256Hash
from app.blob.adapter.output.mapper.blob_mapper import orm_to_domain
from core.db.models import BlobModel
from core.db.session import session_factory


class SQLAlchemyBlobDomainService(BlobDomainService):
    """Blob领域服务的SQLAlchemy实现。"""

    def __init__(self, *, blob_repository: BlobRepository | None = None) -> None:
        self._blob_repository = blob_repository

    async def has_blob(self, *, blob_id: str) -> bool:
        if self._blob_repository is not None:
            blob = await self._blob_repository.get_by_id(blob_id=blob_id)
            return blob is not None
        async with session_factory() as read_session:
            row = (
                await read_session.execute(
                    select(BlobModel.id).where(BlobModel.blob_id == blob_id).limit(1)
                )
            ).scalar_one_or_none()
            return row is not None
    
    async def find_gc_candidates(
        self, 
        *, 
        limit: Optional[int] = None, 
        older_than: Optional[datetime] = None
    ) -> List[Blob]:
        """查找符合垃圾回收条件的 Blob。"""
        query = select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(
            and_(
                BlobModel.storage_locator_id.isnot(None),
                BlobModel.kind == "temporary",
            )
        ).order_by(BlobModel.created_at.asc())
        
        if older_than is not None:
            query = query.where(BlobModel.created_at <= older_than)
        if limit:
            query = query.limit(limit)
            
        async with session_factory() as read_session:
            rows = (await read_session.execute(query)).scalars().all()

        return [orm_to_domain(r) for r in rows]
    
    async def get_storage_locator_by_hash(self, *, sha256: str) -> Optional[StorageLocator]:
        """通过 SHA256 哈希查找 StorageLocator。"""
        from core.db.models.storage_locator import StorageLocatorModel
        
        async with session_factory() as read_session:
            locator_orm = await read_session.scalar(
                select(StorageLocatorModel).where(
                    StorageLocatorModel.sha256 == sha256
                ).order_by(StorageLocatorModel.created_at.desc()).limit(1)
            )
            
            if not locator_orm:
                return None
            
            return StorageLocator(
                storage_locator_id=locator_orm.storage_locator_id,
                storage_provider=locator_orm.storage_provider,
                bucket=locator_orm.bucket,
                object_key=locator_orm.object_key,
                region=locator_orm.region,
                sha256=SHA256Hash(value=locator_orm.sha256) if locator_orm.sha256 else None,
            )
    
    async def find_unreferenced_permanent_candidates(
        self,
        *,
        limit: Optional[int] = None,
    ) -> List[Blob]:
        """查找无引用的 PERMANENT Blob（GC 候选）。adapter 层直接 LEFT JOIN blob_reference 表。"""
        from core.db.models.blob_reference import BlobReferenceModel
        from sqlalchemy.orm import outerjoin

        query = (
            select(BlobModel)
            .options(joinedload(BlobModel.storage_locator))
            .outerjoin(BlobReferenceModel, BlobModel.blob_id == BlobReferenceModel.blob_id)
            .where(
                BlobModel.kind == "permanent",
                BlobModel.storage_locator_id.isnot(None),
                BlobReferenceModel.blob_id.is_(None),
            )
            .order_by(BlobModel.created_at.asc())
        )
        if limit:
            query = query.limit(limit)

        async with session_factory() as read_session:
            rows = (await read_session.execute(query)).scalars().all()

        return [orm_to_domain(r) for r in rows]

    async def get_storage_locator(self, *, blob_id: str) -> Optional[StorageLocator]:
        """获取指定 blob 的存储定位信息。"""
        async with session_factory() as read_session:
            row = (await read_session.execute(
                select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(BlobModel.blob_id == blob_id)
            )).scalar_one_or_none()
            if row is None or not row.storage_locator:
                return None
            return StorageLocator(
                storage_locator_id=row.storage_locator.storage_locator_id,
                storage_provider=row.storage_locator.storage_provider,
                bucket=row.storage_locator.bucket,
                object_key=row.storage_locator.object_key,
                region=row.storage_locator.region,
                sha256=SHA256Hash(value=row.storage_locator.sha256) if row.storage_locator.sha256 else None,
            )
