from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.db.models.blob_reference import BlobReferenceModel
from app.blob.domain.aggregate.blob_reference import BlobReference
from app.blob.domain.repository.blob_reference import BlobReferenceRepository
from core.db.session import session


class SQLAlchemyBlobReferenceRepository(BlobReferenceRepository):
    """BlobReference 聚合根的 SQLAlchemy 仓储实现。"""

    async def save(self, *, ref: BlobReference) -> None:
        """
        Upsert 引用行。
        唯一约束 (owner_type, owner_id, edge_key)：若已存在则更新 blob_id 和 ref_id。
        """
        stmt = (
            pg_insert(BlobReferenceModel)
            .values(
                ref_id=ref.ref_id,
                blob_id=ref.blob_id,
                owner_type=ref.owner_type,
                owner_id=ref.owner_id,
                edge_key=ref.edge_key,
            )
            .on_conflict_do_update(
                constraint="uq_blob_reference_owner_edge",
                set_={
                    "ref_id": ref.ref_id,
                    "blob_id": ref.blob_id,
                },
            )
        )
        await session.execute(stmt)
        await session.flush()

    async def delete_by_edge(
        self,
        *,
        owner_type: str,
        owner_id: str,
        edge_key: str,
    ) -> bool:
        stmt = delete(BlobReferenceModel).where(
            BlobReferenceModel.owner_type == owner_type,
            BlobReferenceModel.owner_id == owner_id,
            BlobReferenceModel.edge_key == edge_key,
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0

    async def delete_all_by_owner(
        self,
        *,
        owner_type: str,
        owner_id: str,
    ) -> int:
        stmt = delete(BlobReferenceModel).where(
            BlobReferenceModel.owner_type == owner_type,
            BlobReferenceModel.owner_id == owner_id,
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount
