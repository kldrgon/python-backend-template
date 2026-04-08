from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.orm import joinedload

from core.db.models import BlobModel, StorageLocatorModel
from app.blob.domain.aggregate.blob import Blob
from app.blob.adapter.output.mapper.blob_mapper import orm_to_domain, domain_to_orm
from app.blob.domain.repository.blob import BlobRepository
from pami_event_framework.persistence.base_aggregate_repository import BaseAggregateRepository
from core.db.session import session, session_factory


class SQLAlchemyBlobRepository(BaseAggregateRepository, BlobRepository):
    """Blob聚合根的SQLAlchemy仓储实现。"""
    
    async def get_by_id(self, *, blob_id: str) -> Optional[Blob]:
        stmt = select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(BlobModel.blob_id == blob_id)
        orm = (await session.execute(stmt)).scalar_one_or_none()
        return orm_to_domain(orm) if orm else None

    async def get_by_hash(self, *, blob_sha256: str) -> Optional[Blob]:
        """返回第一个有 storage_locator 的 Blob（用于去重）。"""
        stmt = select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(
            and_(
                BlobModel.blob_sha256 == blob_sha256,
                BlobModel.storage_locator_id.isnot(None),
            )
        ).limit(1)
        orm = (await session.execute(stmt)).scalar_one_or_none()
        return orm_to_domain(orm) if orm else None
    
    async def list_by_hash(self, *, blob_sha256: str) -> List[Blob]:
        """返回所有具有相同 hash256 的 Blob（用于查询 ref）。"""
        stmt = select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(BlobModel.blob_sha256 == blob_sha256)
        result = await session.execute(stmt)
        orms = result.scalars().all()
        return [orm_to_domain(orm) for orm in orms]

    async def exists_by_hash(self, *, blob_sha256: str) -> bool:
        stmt = await session.scalar(select(func.count()).select_from(BlobModel).where(BlobModel.blob_sha256 == blob_sha256))
        return (stmt or 0) > 0
    
    async def exists_by_storage_key(self, *, storage_unique_key: str) -> bool:
        """通过 storage_unique_key（格式：provider::bucket::object_key）判断是否存在。"""
        parts = storage_unique_key.split("::", 2)
        if len(parts) != 3:
            return False
        provider, bucket, object_key = parts
        stmt = select(func.count()).select_from(StorageLocatorModel).where(
            and_(
                StorageLocatorModel.storage_provider == provider,
                StorageLocatorModel.bucket == bucket,
                StorageLocatorModel.object_key == object_key,
            )
        )
        count = await session.scalar(stmt)
        return (count or 0) > 0

    async def get_by_storage_locator(
        self,
        *,
        storage_provider: str,
        bucket: str,
        object_key: str,
    ) -> Optional[Blob]:
        stmt = (
            select(BlobModel)
            .options(joinedload(BlobModel.storage_locator))
            .join(StorageLocatorModel, BlobModel.storage_locator_id == StorageLocatorModel.id)
            .where(
                and_(
                    StorageLocatorModel.storage_provider == storage_provider,
                    StorageLocatorModel.bucket == bucket,
                    StorageLocatorModel.object_key == object_key,
                )
            )
            .limit(1)
        )
        orm = (await session.execute(stmt)).scalar_one_or_none()
        return orm_to_domain(orm) if orm else None

    async def save(self, *, blob: Blob) -> None:
        """保存blob聚合根。"""
        orm = await session.scalar(select(BlobModel).options(joinedload(BlobModel.storage_locator)).where(BlobModel.blob_id == blob.blob_id))
        
        storage_locator_orm = None
        if blob.storage_locator:
            from uuid import uuid4

            storage_locator_id = blob.storage_locator.storage_locator_id or uuid4().hex
            blob.storage_locator.storage_locator_id = storage_locator_id

            existing_locator = await session.scalar(
                select(StorageLocatorModel).where(
                    StorageLocatorModel.storage_locator_id == storage_locator_id
                ).limit(1)
            )

            if existing_locator:
                storage_locator_orm = existing_locator
                storage_locator_orm.storage_provider = blob.storage_locator.storage_provider
                storage_locator_orm.bucket = blob.storage_locator.bucket
                storage_locator_orm.object_key = blob.storage_locator.object_key
                storage_locator_orm.region = blob.storage_locator.region
                storage_locator_orm.sha256 = str(blob.blob_sha256) if blob.blob_sha256 else None
            else:
                storage_locator_orm = StorageLocatorModel(
                    storage_locator_id=storage_locator_id,
                    storage_provider=blob.storage_locator.storage_provider,
                    bucket=blob.storage_locator.bucket,
                    object_key=blob.storage_locator.object_key,
                    region=blob.storage_locator.region,
                    sha256=str(blob.blob_sha256) if blob.blob_sha256 else None,
                )
                session.add(storage_locator_orm)
                await session.flush()

            if blob.blob_sha256:
                blob.storage_locator.sha256 = blob.blob_sha256
        
        if orm is None:
            orm = domain_to_orm(blob, target=None, storage_locator_orm=storage_locator_orm)
            session.add(orm)
        else:
            orm = domain_to_orm(blob, target=orm, storage_locator_orm=storage_locator_orm)
        
        await session.flush()
        await self._flush_events(blob)

    async def delete(self, *, blob_id: str) -> bool:
        """删除blob。"""
        orm = await session.scalar(select(BlobModel).where(BlobModel.blob_id == blob_id))
        if not orm:
            return False
        
        await session.delete(orm)
        await session.flush()
        return True
