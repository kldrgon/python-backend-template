from typing import Optional
from pydantic import BaseModel
from pami_event_framework import DomainEvent


# ============ BlobCreated ============
class BlobCreatedPayload(BaseModel):
    blob_id: str
    blob_sha256: str
    size_bytes: int
    storage_provider: str | None = None
    bucket: str | None = None
    object_key: str | None = None
    region: str | None = None


class BlobCreatedEvent(DomainEvent):
    """Blob创建事件 - 柔性"""
    event_type = "BLOB_CREATED"
    strict = False

    def __init__(
        self,
        *,
        blob_id: str,
        blob_sha256: str,
        size_bytes: int,
        storage_provider: str | None = None,
        bucket: str | None = None,
        object_key: str | None = None,
        region: str | None = None,
    ):
        super().__init__(
            blob_id=blob_id,
            blob_sha256=blob_sha256,
            size_bytes=size_bytes,
            storage_provider=storage_provider,
            bucket=bucket,
            object_key=object_key,
            region=region,
        )


# ============ BlobProcessingStarted ============
class BlobProcessingStartedPayload(BaseModel):
    blob_id: str


class BlobProcessingStartedEvent(DomainEvent):
    """Blob处理开始事件 - 柔性"""
    event_type = "BLOB_PROCESSING_STARTED"
    strict = False

    def __init__(self, *, blob_id: str):
        super().__init__(blob_id=blob_id)


# ============ BlobProcessingCompleted ============
class BlobProcessingCompletedPayload(BaseModel):
    blob_id: str
    blob_sha256: str
    storage_provider: str | None = None
    bucket: str | None = None
    object_key: str | None = None
    region: str | None = None
    owner_id: str | None = None
    owner_type: str | None = None
    edge_key: str | None = None


class BlobProcessingCompletedEvent(DomainEvent):
    """Blob处理完成事件 - 柔性"""
    event_type = "BLOB_PROCESSING_COMPLETED"
    strict = False

    def __init__(
        self,
        *,
        blob_id: str,
        blob_sha256: str,
        storage_provider: str | None = None,
        bucket: str | None = None,
        object_key: str | None = None,
        region: str | None = None,
        owner_id: str | None = None,
        owner_type: str | None = None,
        edge_key: str | None = None,
    ):
        super().__init__(
            blob_id=blob_id,
            blob_sha256=blob_sha256,
            storage_provider=storage_provider,
            bucket=bucket,
            object_key=object_key,
            region=region,
            owner_id=owner_id,
            owner_type=owner_type,
            edge_key=edge_key,
        )


# ============ BlobProcessingFailed ============
class BlobProcessingFailedPayload(BaseModel):
    blob_id: str
    reason: str | None = None


class BlobProcessingFailedEvent(DomainEvent):
    """Blob处理失败事件 - 柔性"""
    event_type = "BLOB_PROCESSING_FAILED"
    strict = False

    def __init__(self, *, blob_id: str, reason: str | None = None):
        super().__init__(blob_id=blob_id, reason=reason)


# ============ BlobDeleted ============
class BlobDeletedPayload(BaseModel):
    blob_id: str


class BlobDeletedEvent(DomainEvent):
    """Blob删除事件 - 柔性"""
    event_type = "BLOB_DELETED"
    strict = False

    def __init__(self, *, blob_id: str):
        super().__init__(blob_id=blob_id)


# ============ BlobGcRequested ============
class BlobGcRequestedPayload(BaseModel):
    blob_id: str


class BlobGcRequestedEvent(DomainEvent):
    """Blob GC请求事件 - 柔性"""
    event_type = "BLOB_GC_REQUESTED"
    strict = False

    def __init__(self, *, blob_id: str):
        super().__init__(blob_id=blob_id)
