from __future__ import annotations

from app.blob.domain.domain_service.blob_attachment_service import BlobAttachmentDomainService
from app.blob.domain.aggregate.blob_reference import BlobReference
from app.blob.domain.repository.blob_reference import BlobReferenceRepository


class SQLAlchemyBlobAttachmentDomainService(BlobAttachmentDomainService):
    """BlobAttachmentDomainService 的 SQLAlchemy 实现（防腐层）。"""

    def __init__(self, *, blob_reference_repository: BlobReferenceRepository) -> None:
        self._ref_repo = blob_reference_repository

    async def attach(
        self,
        *,
        blob_id: str,
        owner_type: str,
        owner_id: str,
        edge_key: str,
    ) -> None:
        ref = BlobReference.create(
            blob_id=blob_id,
            owner_type=owner_type,
            owner_id=owner_id,
            edge_key=edge_key,
        )
        await self._ref_repo.save(ref=ref)

    async def detach(
        self,
        *,
        owner_type: str,
        owner_id: str,
        edge_key: str,
    ) -> bool:
        return await self._ref_repo.delete_by_edge(
            owner_type=owner_type,
            owner_id=owner_id,
            edge_key=edge_key,
        )

    async def detach_all(
        self,
        *,
        owner_type: str,
        owner_id: str,
    ) -> int:
        return await self._ref_repo.delete_all_by_owner(
            owner_type=owner_type,
            owner_id=owner_id,
        )
