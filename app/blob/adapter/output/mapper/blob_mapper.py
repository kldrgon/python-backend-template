from typing import Optional

from core.db.models import BlobModel, StorageLocatorModel
from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.mime_type import MimeType
from app.blob.domain.vo.etag import Etag
from app.blob.domain.vo.hash import SHA256Hash
from app.blob.domain.vo.blob_status import BlobStatus
from app.blob.domain.vo.blob_kind import BlobKind


def orm_to_domain(orm: BlobModel) -> Blob:
    """将ORM模型转换为领域聚合根。"""
    storage_locator = None
    if orm.storage_locator:
        storage_locator = StorageLocator(
            storage_locator_id=orm.storage_locator.storage_locator_id,
            storage_provider=orm.storage_locator.storage_provider,
            bucket=orm.storage_locator.bucket,
            object_key=orm.storage_locator.object_key,
            region=orm.storage_locator.region,
            sha256=SHA256Hash(value=orm.storage_locator.sha256) if orm.storage_locator.sha256 else None,
        )
    
    return Blob(
        blob_id=orm.blob_id,
        blob_sha256=SHA256Hash(value=orm.blob_sha256) if orm.blob_sha256 else None,
        kind=BlobKind(orm.kind) if getattr(orm, "kind", None) else BlobKind.TEMPORARY,
        size_bytes=orm.size_bytes,
        mime_type=MimeType(value=orm.mime_type) if orm.mime_type else None,
        display_name=orm.display_name,
        storage_locator=storage_locator,
        etag=Etag(value=orm.etag) if orm.etag else None,
        storage_class=orm.storage_class,
        status=BlobStatus(orm.status) if orm.status else BlobStatus.PENDING,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def domain_to_orm(domain: Blob, target: Optional[BlobModel] = None, storage_locator_orm: Optional[StorageLocatorModel] = None) -> BlobModel:
    """将领域聚合根转换为ORM模型。"""
    orm = target or BlobModel()
    
    orm.blob_id = getattr(orm, "blob_id", None) or domain.blob_id
    orm.blob_sha256 = str(domain.blob_sha256) if domain.blob_sha256 else None
    orm.kind = domain.kind.value if getattr(domain, "kind", None) else BlobKind.TEMPORARY.value
    orm.size_bytes = domain.size_bytes
    orm.mime_type = str(domain.mime_type) if domain.mime_type else None
    orm.display_name = domain.display_name
    orm.status = domain.status.value if domain.status else "pending"
    orm.storage_class = domain.storage_class
    
    if storage_locator_orm:
        orm.storage_locator_id = storage_locator_orm.id
    elif domain.storage_locator:
        orm.storage_locator_id = None
    else:
        orm.storage_locator_id = None
    
    orm.etag = str(domain.etag) if domain.etag else None
    
    return orm
