"""Blob Domain Activities"""

from temporalio import activity
from pami_event_framework.temporal import with_session_context
from pami_event_framework.autodiscovery import activity_of_handler
from app.blob.domain.event.blob_events import (
    BlobCreatedPayload,
    BlobProcessingStartedPayload,
    BlobProcessingCompletedPayload,
    BlobProcessingFailedPayload,
    BlobDeletedPayload,
    BlobGcRequestedPayload,
)
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


@activity.defn
@activity_of_handler()
@with_session_context
async def on_blob_created_activity(event_data: dict):
    """Blob创建事件处理器"""
    payload = BlobCreatedPayload(**event_data)
    logger.info(
        "blob_created",
        blob_id=payload.blob_id,
        sha256_prefix=payload.blob_sha256[:16],
        size_bytes=payload.size_bytes,
    )


@activity.defn
@activity_of_handler()
@with_session_context
async def on_blob_processing_started_activity(event_data: dict):
    """Blob处理开始事件处理器"""
    payload = BlobProcessingStartedPayload(**event_data)
    logger.info("blob_processing_started", blob_id=payload.blob_id)


@activity.defn
@activity_of_handler()
@with_session_context
async def on_blob_processing_completed_activity(event_data: dict):
    """Blob处理完成事件处理器"""
    payload = BlobProcessingCompletedPayload(**event_data)
    logger.info("blob_processing_completed", blob_id=payload.blob_id, sha256_prefix=payload.blob_sha256[:16])


@activity.defn
@activity_of_handler()
@with_session_context
async def on_blob_processing_failed_activity(event_data: dict):
    """Blob处理失败事件处理器"""
    payload = BlobProcessingFailedPayload(**event_data)
    logger.warning("blob_processing_failed", blob_id=payload.blob_id, reason=payload.reason or "unknown")


@activity.defn
@activity_of_handler()
@with_session_context
async def on_blob_deleted_activity(event_data: dict):
    """Blob删除事件处理器"""
    payload = BlobDeletedPayload(**event_data)
    logger.info("blob_deleted", blob_id=payload.blob_id)


@activity.defn
@activity_of_handler()
@with_session_context
async def on_blob_gc_requested_activity(event_data: dict):
    """Blob GC请求事件处理器"""
    payload = BlobGcRequestedPayload(**event_data)
    logger.info("blob_gc_requested", blob_id=payload.blob_id)
