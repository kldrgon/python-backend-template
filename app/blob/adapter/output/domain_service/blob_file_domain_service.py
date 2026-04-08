from __future__ import annotations

from typing import BinaryIO, Optional
import tempfile

from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.domain_service.blob_file_domain_service import BlobFileDomainService
from app.blob.domain.domain_service.storage_adapter import StorageAdapter, ObjectMetadata
from app.blob.domain.factory.blob_factory import BlobFactory
from app.blob.domain.repository.blob import BlobRepository
from app.blob.domain.vo.mime_type import MimeType
from app.blob.domain.vo.blob_kind import BlobKind
from core.config import config


class SQLAlchemyBlobFileDomainService(BlobFileDomainService):
    """基于 SQLAlchemy 的 Blob 文件领域服务实现。"""

    def __init__(
        self,
        *,
        blob_repository: BlobRepository,
        blob_factory: BlobFactory,
        storage_adapter: StorageAdapter,
    ) -> None:
        self._blob_repository = blob_repository
        self._blob_factory = blob_factory
        self._storage_adapter = storage_adapter

    async def create_blob_from_stream(
        self,
        *,
        fileobj: BinaryIO,
        content_type: Optional[str],
        kind: BlobKind = BlobKind.PERMANENT,
        display_name: Optional[str] = None,
    ) -> Blob:
        if isinstance(kind, str):
            kind = BlobKind(kind)
        eff_provider = config.blob_storage.storage_provider
        eff_bucket = config.blob_storage.default_bucket
        if hasattr(fileobj, "seek"):
            fileobj.seek(0)
        blob, _, _ = await self._blob_factory.create_from_stream(
            fileobj=fileobj,
            content_type=content_type,
            storage_provider=eff_provider,
            default_bucket=eff_bucket,
            kind=kind,
            display_name=display_name,
        )
        if hasattr(fileobj, "seek"):
            fileobj.seek(0)

        obj_meta: ObjectMetadata = await self._storage_adapter.put_object(
            blob.storage_locator,  # type: ignore[arg-type]
            fileobj,
            mime_type=MimeType(value=content_type) if content_type else None,
            metadata=None,
            storage_class=None,
        )
        blob.update_storage_metadata(
            etag=str(obj_meta.etag) if obj_meta.etag else None,
            storage_class=obj_meta.storage_class,
        )

        await self._blob_repository.save(blob=blob)

        return blob

    async def promote_temp_to_permanent(self, *, blob_id: str) -> Blob | None:
        blob = await self._blob_repository.get_by_id(blob_id=blob_id)
        if blob is None:
            return None
        if getattr(blob, "kind", None) == BlobKind.PERMANENT:
            return blob
        if blob.storage_locator is None:
            return blob

        old_locator = blob.storage_locator
        target_locator = self._blob_factory.build_storage_locator(
            storage_provider=old_locator.storage_provider,
            default_bucket=old_locator.bucket,
            kind=BlobKind.PERMANENT,
            region=old_locator.region,
        )

        if self._storage_adapter.supports_copy():
            obj_meta = await self._storage_adapter.copy_object(source=old_locator, target=target_locator)
        else:
            meta, iterator = await self._storage_adapter.get_object_stream(old_locator, chunk_size=1024 * 1024)
            tmp = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024)
            async for chunk in iterator:
                tmp.write(chunk)
            tmp.seek(0)
            obj_meta = await self._storage_adapter.put_object(
                target_locator,
                tmp,
                mime_type=meta.mime_type,
                metadata=meta.custom_metadata,
                storage_class=meta.storage_class,
            )

        blob.kind = BlobKind.PERMANENT
        blob.storage_locator = target_locator
        blob.update_storage_metadata(
            etag=str(obj_meta.etag) if obj_meta.etag else None,
            storage_class=obj_meta.storage_class,
        )
        await self._blob_repository.save(blob=blob)

        await self._storage_adapter.delete_object(old_locator)
        return blob
