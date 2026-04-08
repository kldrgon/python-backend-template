"""SQLAlchemyBlobRepository 集成测试 - 真实 DB，_flush_events mock"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.blob_kind import BlobKind
from app.blob.domain.vo.blob_status import BlobStatus
from app.blob.domain.vo.hash import SHA256Hash
from app.blob.domain.vo.mime_type import MimeType
from app.blob.adapter.output.repository.blob import SQLAlchemyBlobRepository


# ── 辅助工厂 ──────────────────────────────────────────────────────────────


def _locator(
    *,
    provider: str = "minio",
    bucket: str = "test-bucket",
    object_key: str | None = None,
) -> StorageLocator:
    return StorageLocator(
        storage_provider=provider,
        bucket=bucket,
        object_key=object_key or f"files/{uuid4().hex}",
    )


def _domain_blob(
    *,
    blob_id: str | None = None,
    sha256: str = "a" * 64,
    size_bytes: int = 1024,
    kind: BlobKind = BlobKind.TEMPORARY,
    locator: StorageLocator | None = None,
) -> Blob:
    blob = Blob.create(
        blob_id=blob_id or uuid4().hex,
        blob_sha256=SHA256Hash(value=sha256),
        kind=kind,
        size_bytes=size_bytes,
        mime_type=MimeType(value="image/jpeg"),
        storage_locator=locator or _locator(),
    )
    blob.clear_domain_events()
    return blob


async def _save(repo: SQLAlchemyBlobRepository, blob: Blob, session) -> None:
    with patch.object(repo, "_flush_events", new=AsyncMock()):
        await repo.save(blob=blob)
    await session.commit()


@pytest.fixture
def repo():
    return SQLAlchemyBlobRepository()


# ── TestBlobRepository ────────────────────────────────────────────────────


class TestBlobRepository:

    # ── save + get_by_id ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_save_and_get_by_id(self, session, repo):
        blob = _domain_blob(blob_id="b1")
        await _save(repo, blob, session)

        found = await repo.get_by_id(blob_id="b1")

        assert found is not None
        assert found.blob_id == "b1"
        assert found.size_bytes == 1024
        assert found.storage_locator is not None

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session, repo):
        found = await repo.get_by_id(blob_id="nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_save_updates_existing(self, session, repo):
        blob = _domain_blob(blob_id="b2", size_bytes=100)
        await _save(repo, blob, session)

        blob.size_bytes = 200
        await _save(repo, blob, session)

        found = await repo.get_by_id(blob_id="b2")
        assert found.size_bytes == 200

    # ── get_by_hash ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_by_hash_returns_blob_with_locator(self, session, repo):
        sha = "b" * 64
        blob = _domain_blob(sha256=sha)
        await _save(repo, blob, session)

        found = await repo.get_by_hash(blob_sha256=sha)

        assert found is not None
        assert str(found.blob_sha256) == sha
        assert found.storage_locator is not None

    @pytest.mark.asyncio
    async def test_get_by_hash_not_found(self, session, repo):
        found = await repo.get_by_hash(blob_sha256="c" * 64)
        assert found is None

    # ── list_by_hash ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_by_hash_returns_all_matching(self, session, repo):
        sha = "d" * 64
        blob1 = _domain_blob(sha256=sha, locator=_locator(object_key="files/1"))
        blob2 = _domain_blob(sha256=sha, locator=_locator(object_key="files/2"))
        await _save(repo, blob1, session)
        await _save(repo, blob2, session)

        results = await repo.list_by_hash(blob_sha256=sha)

        assert len(results) == 2
        assert all(str(b.blob_sha256) == sha for b in results)

    @pytest.mark.asyncio
    async def test_list_by_hash_empty(self, session, repo):
        results = await repo.list_by_hash(blob_sha256="e" * 64)
        assert results == []

    # ── exists_by_hash ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_exists_by_hash_true(self, session, repo):
        sha = "f" * 64
        blob = _domain_blob(sha256=sha)
        await _save(repo, blob, session)

        assert await repo.exists_by_hash(blob_sha256=sha) is True

    @pytest.mark.asyncio
    async def test_exists_by_hash_false(self, session, repo):
        assert await repo.exists_by_hash(blob_sha256="0" * 64) is False

    # ── exists_by_storage_key ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_exists_by_storage_key_true(self, session, repo):
        locator = _locator(provider="minio", bucket="test-bucket", object_key="files/key1")
        blob = _domain_blob(locator=locator)
        await _save(repo, blob, session)

        key = "minio::test-bucket::files/key1"
        assert await repo.exists_by_storage_key(storage_unique_key=key) is True

    @pytest.mark.asyncio
    async def test_exists_by_storage_key_false(self, session, repo):
        key = "minio::test-bucket::files/nonexistent"
        assert await repo.exists_by_storage_key(storage_unique_key=key) is False

    @pytest.mark.asyncio
    async def test_exists_by_storage_key_invalid_format(self, session, repo):
        assert await repo.exists_by_storage_key(storage_unique_key="bad-key") is False

    # ── get_by_storage_locator ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_by_storage_locator_found(self, session, repo):
        locator = _locator(provider="minio", bucket="test-bucket", object_key="files/loctest")
        blob = _domain_blob(locator=locator)
        await _save(repo, blob, session)

        found = await repo.get_by_storage_locator(
            storage_provider="minio",
            bucket="test-bucket",
            object_key="files/loctest",
        )

        assert found is not None
        assert found.blob_id == blob.blob_id

    @pytest.mark.asyncio
    async def test_get_by_storage_locator_not_found(self, session, repo):
        found = await repo.get_by_storage_locator(
            storage_provider="minio",
            bucket="test-bucket",
            object_key="files/does-not-exist",
        )
        assert found is None

    # ── delete ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_existing(self, session, repo):
        blob = _domain_blob(blob_id="del1")
        await _save(repo, blob, session)

        deleted = await repo.delete(blob_id="del1")
        await session.commit()

        assert deleted is True
        assert await repo.get_by_id(blob_id="del1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, session, repo):
        deleted = await repo.delete(blob_id="nope")
        assert deleted is False
