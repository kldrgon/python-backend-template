"""Blob aggregate root unit tests

Covers:
- create() / create_pending() factory methods
- State machine: PENDING -> PROCESSING -> READY / FAILED
- InvalidBlobStatusError on illegal transitions
- Domain event publishing
- verify_integrity()
- get_thumbnail_locator()
- is_stored / storage_unique_key properties
- update_storage_metadata()
- delete() event
"""

import pytest

from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.vo.blob_status import BlobStatus
from app.blob.domain.vo.blob_kind import BlobKind
from app.blob.domain.vo.hash import SHA256Hash
from app.blob.domain.vo.mime_type import MimeType
from app.blob.domain.vo.etag import Etag
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.exception.errors import InvalidBlobStatusError
from app.blob.domain.event.blob_events import (
    BlobCreatedEvent,
    BlobProcessingStartedEvent,
    BlobProcessingCompletedEvent,
    BlobProcessingFailedEvent,
    BlobDeletedEvent,
)


VALID_SHA256 = "a" * 64
VALID_SHA256_B = "b" * 64


def _make_locator(object_key: str = "uploads/file.png") -> StorageLocator:
    return StorageLocator(
        storage_provider="minio",
        bucket="test-bucket",
        object_key=object_key,
    )


def _make_sha256(value: str = VALID_SHA256) -> SHA256Hash:
    return SHA256Hash(value=value)


# --- create() ---


class TestBlobCreate:
    def test_creates_with_ready_status(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=1024,
            mime_type=MimeType(value="image/png"),
            storage_locator=_make_locator(),
        )
        assert blob.status == BlobStatus.READY
        assert blob.blob_id == "blob-001"
        assert blob.size_bytes == 1024

    def test_raises_blob_created_event(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=512,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        events = blob.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], BlobCreatedEvent)
        assert events[0].payload["blob_id"] == "blob-001"

    def test_default_kind_is_temporary(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        assert blob.kind == BlobKind.TEMPORARY

    def test_creates_with_permanent_kind(self):
        blob = Blob.create(
            blob_id="blob-002",
            blob_sha256=_make_sha256(),
            kind=BlobKind.PERMANENT,
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        assert blob.kind == BlobKind.PERMANENT


# --- create_pending() ---


class TestBlobCreatePending:
    def test_creates_with_pending_status(self):
        blob = Blob.create_pending(blob_id="blob-p1", size_bytes=2048)
        assert blob.status == BlobStatus.PENDING
        assert blob.blob_sha256 is None
        assert blob.storage_locator is None

    def test_no_events_raised(self):
        blob = Blob.create_pending(blob_id="blob-p1", size_bytes=100)
        events = blob.get_domain_events()
        assert events == []

    def test_is_stored_false(self):
        blob = Blob.create_pending(blob_id="blob-p1", size_bytes=100)
        assert blob.is_stored is False


# --- mark_processing() ---


class TestMarkProcessing:
    def test_transitions_pending_to_processing(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        blob.mark_processing()
        assert blob.status == BlobStatus.PROCESSING

    def test_raises_processing_started_event(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        blob.mark_processing()
        events = blob.get_domain_events()
        assert any(isinstance(e, BlobProcessingStartedEvent) for e in events)

    def test_raises_error_if_not_pending(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        with pytest.raises(InvalidBlobStatusError) as exc_info:
            blob.mark_processing()
        assert exc_info.value.blob_id == "blob-001"
        assert exc_info.value.current_status == BlobStatus.READY


# --- mark_ready() ---


class TestMarkReady:
    def _processing_blob(self) -> Blob:
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        blob.mark_processing()
        blob.clear_domain_events()
        return blob

    def test_transitions_processing_to_ready(self):
        blob = self._processing_blob()
        blob.mark_ready(
            blob_sha256=_make_sha256(),
            storage_locator=_make_locator(),
        )
        assert blob.status == BlobStatus.READY

    def test_updates_sha256_and_locator(self):
        blob = self._processing_blob()
        sha = _make_sha256()
        loc = _make_locator()
        blob.mark_ready(blob_sha256=sha, storage_locator=loc)
        assert blob.blob_sha256 == sha
        assert blob.storage_locator == loc

    def test_raises_processing_completed_event(self):
        blob = self._processing_blob()
        blob.mark_ready(blob_sha256=_make_sha256(), storage_locator=_make_locator())
        events = blob.get_domain_events()
        assert any(isinstance(e, BlobProcessingCompletedEvent) for e in events)

    def test_completed_event_carries_owner_info(self):
        blob = self._processing_blob()
        blob.mark_ready(
            blob_sha256=_make_sha256(),
            storage_locator=_make_locator(),
            owner_id="user-001",
            owner_type="user",
            edge_key="avatar",
        )
        events = blob.get_domain_events()
        completed = next(e for e in events if isinstance(e, BlobProcessingCompletedEvent))
        assert completed.payload["owner_id"] == "user-001"
        assert completed.payload["edge_key"] == "avatar"

    def test_raises_error_if_not_processing(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        with pytest.raises(InvalidBlobStatusError) as exc_info:
            blob.mark_ready(blob_sha256=_make_sha256(), storage_locator=_make_locator())
        assert exc_info.value.current_status == BlobStatus.PENDING

    def test_updates_etag_when_provided(self):
        blob = self._processing_blob()
        etag = Etag(value="abc123-def456")
        blob.mark_ready(
            blob_sha256=_make_sha256(),
            storage_locator=_make_locator(),
            etag=etag,
        )
        assert blob.etag == etag


# --- mark_failed() ---


class TestMarkFailed:
    def test_transitions_to_failed(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        blob.mark_processing()
        blob.mark_failed(reason="upload error")
        assert blob.status == BlobStatus.FAILED

    def test_raises_failed_event(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        blob.mark_processing()
        blob.clear_domain_events()
        blob.mark_failed(reason="disk full")
        events = blob.get_domain_events()
        assert any(isinstance(e, BlobProcessingFailedEvent) for e in events)

    def test_failed_event_carries_reason(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        blob.mark_processing()
        blob.clear_domain_events()
        blob.mark_failed(reason="timeout")
        events = blob.get_domain_events()
        failed = next(e for e in events if isinstance(e, BlobProcessingFailedEvent))
        assert failed.payload["reason"] == "timeout"

    def test_mark_failed_without_reason(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        blob.mark_processing()
        blob.mark_failed()
        assert blob.status == BlobStatus.FAILED


# --- verify_integrity() ---


class TestVerifyIntegrity:
    def test_returns_true_for_matching_hash(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(VALID_SHA256),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        assert blob.verify_integrity(content_sha256=VALID_SHA256) is True

    def test_returns_false_for_mismatched_hash(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(VALID_SHA256),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        assert blob.verify_integrity(content_sha256=VALID_SHA256_B) is False

    def test_returns_false_when_no_hash(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        assert blob.verify_integrity(content_sha256=VALID_SHA256) is False

    def test_case_insensitive(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(VALID_SHA256),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        assert blob.verify_integrity(content_sha256=VALID_SHA256.upper()) is True


# --- get_thumbnail_locator() ---


class TestGetThumbnailLocator:
    def test_returns_none_when_not_stored(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        assert blob.get_thumbnail_locator(max_bytes=50000) is None

    def test_returns_locator_with_cache_key(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        thumb = blob.get_thumbnail_locator(max_bytes=50000)
        assert thumb is not None
        assert "blob-001" in thumb.object_key
        assert "50000" in thumb.object_key

    def test_thumbnail_inherits_provider_and_bucket(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        thumb = blob.get_thumbnail_locator(max_bytes=10000)
        assert thumb.storage_provider == "minio"
        assert thumb.bucket == "test-bucket"


# --- is_stored / storage_unique_key ---


class TestBlobProperties:
    def test_is_stored_true_when_locator_present(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        assert blob.is_stored is True

    def test_storage_unique_key(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        assert blob.storage_unique_key == "minio:test-bucket:uploads/file.png"

    def test_storage_unique_key_none_when_not_stored(self):
        blob = Blob.create_pending(blob_id="blob-001", size_bytes=100)
        assert blob.storage_unique_key is None


# --- update_storage_metadata() ---


class TestUpdateStorageMetadata:
    def test_updates_etag(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        blob.update_storage_metadata(etag="abc123-456def")
        assert blob.etag is not None
        assert str(blob.etag) == "abc123-456def"

    def test_updates_storage_class(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        blob.update_storage_metadata(storage_class="GLACIER")
        assert blob.storage_class == "GLACIER"


# --- delete() ---


class TestBlobDelete:
    def test_raises_blob_deleted_event(self):
        blob = Blob.create(
            blob_id="blob-001",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        blob.clear_domain_events()
        blob.delete()
        events = blob.get_domain_events()
        assert any(isinstance(e, BlobDeletedEvent) for e in events)

    def test_deleted_event_carries_blob_id(self):
        blob = Blob.create(
            blob_id="blob-del-1",
            blob_sha256=_make_sha256(),
            size_bytes=100,
            mime_type=None,
            storage_locator=_make_locator(),
        )
        blob.clear_domain_events()
        blob.delete()
        events = blob.get_domain_events()
        deleted = next(e for e in events if isinstance(e, BlobDeletedEvent))
        assert deleted.payload["blob_id"] == "blob-del-1"
