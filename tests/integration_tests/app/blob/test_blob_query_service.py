"""SQLAlchemyBlobQueryService 集成测试 - 真实 DB"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.blob.domain.aggregate.blob import Blob
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.blob_kind import BlobKind
from app.blob.domain.vo.hash import SHA256Hash
from app.blob.domain.vo.mime_type import MimeType
from app.blob.adapter.output.repository.blob import SQLAlchemyBlobRepository
from app.blob.adapter.output.query.blob_query import SQLAlchemyBlobQueryService


# ── 辅助工厂 ──────────────────────────────────────────────────────────────


def _domain_blob(
    *,
    blob_id: str | None = None,
    sha256: str = "a" * 64,
    size_bytes: int = 512,
    kind: BlobKind = BlobKind.TEMPORARY,
    object_key: str | None = None,
) -> Blob:
    blob = Blob.create(
        blob_id=blob_id or uuid4().hex,
        blob_sha256=SHA256Hash(value=sha256),
        kind=kind,
        size_bytes=size_bytes,
        mime_type=MimeType(value="application/octet-stream"),
        storage_locator=StorageLocator(
            storage_provider="minio",
            bucket="test-bucket",
            object_key=object_key or f"files/{uuid4().hex}",
        ),
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


@pytest.fixture
def query_svc():
    return SQLAlchemyBlobQueryService()


# ── TestBlobQueryService ──────────────────────────────────────────────────


class TestBlobQueryService:

    # ── get ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_existing(self, session, repo, query_svc):
        blob = _domain_blob(blob_id="q1")
        await _save(repo, blob, session)

        dto = await query_svc.get(blob_id="q1")

        assert dto is not None
        assert dto.blob_id == "q1"
        assert dto.size_bytes == 512

    @pytest.mark.asyncio
    async def test_get_not_found(self, session, query_svc):
        dto = await query_svc.get(blob_id="does-not-exist")
        assert dto is None

    # ── get_by_hash ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_by_hash_returns_first_with_locator(self, session, repo, query_svc):
        sha = "b" * 64
        blob = _domain_blob(sha256=sha)
        await _save(repo, blob, session)

        dto = await query_svc.get_by_hash(blob_sha256=sha)

        assert dto is not None
        assert dto.blob_sha256 == sha

    @pytest.mark.asyncio
    async def test_get_by_hash_not_found(self, session, query_svc):
        dto = await query_svc.get_by_hash(blob_sha256="c" * 64)
        assert dto is None

    # ── list_by_hash ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_by_hash_multiple(self, session, repo, query_svc):
        sha = "d" * 64
        b1 = _domain_blob(sha256=sha, object_key="files/qa")
        b2 = _domain_blob(sha256=sha, object_key="files/qb")
        await _save(repo, b1, session)
        await _save(repo, b2, session)

        dtos = await query_svc.list_by_hash(blob_sha256=sha)

        assert len(dtos) == 2

    @pytest.mark.asyncio
    async def test_list_by_hash_empty(self, session, query_svc):
        dtos = await query_svc.list_by_hash(blob_sha256="e" * 64)
        assert dtos == []

    # ── list_gc_candidates ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_gc_candidates_returns_temporary_blobs(self, session, repo, query_svc):
        b_temp = _domain_blob(kind=BlobKind.TEMPORARY)
        b_perm = _domain_blob(kind=BlobKind.PERMANENT)
        await _save(repo, b_temp, session)
        await _save(repo, b_perm, session)

        candidates = await query_svc.list_gc_candidates(limit=50)

        candidate_ids = {c.blob_id for c in candidates}
        assert b_temp.blob_id in candidate_ids
        assert b_perm.blob_id not in candidate_ids

    @pytest.mark.asyncio
    async def test_list_gc_candidates_older_than_filter(self, session, repo, query_svc):
        b_old = _domain_blob(kind=BlobKind.TEMPORARY)
        await _save(repo, b_old, session)

        future = datetime.now(timezone.utc) + timedelta(hours=1)
        candidates = await query_svc.list_gc_candidates(older_than=future)
        assert any(c.blob_id == b_old.blob_id for c in candidates)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        candidates_past = await query_svc.list_gc_candidates(older_than=past)
        assert not any(c.blob_id == b_old.blob_id for c in candidates_past)
