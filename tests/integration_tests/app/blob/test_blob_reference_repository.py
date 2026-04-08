"""SQLAlchemyBlobReferenceRepository 集成测试 - 真实 DB"""

import pytest
from uuid import uuid4

from app.blob.domain.aggregate.blob_reference import BlobReference
from app.blob.adapter.output.repository.blob_reference import SQLAlchemyBlobReferenceRepository


# ── 辅助工厂 ──────────────────────────────────────────────────────────────


def _ref(
    *,
    blob_id: str = "blob1",
    owner_type: str = "user",
    owner_id: str = "owner1",
    edge_key: str = "avatar",
) -> BlobReference:
    return BlobReference.create(
        blob_id=blob_id,
        owner_type=owner_type,
        owner_id=owner_id,
        edge_key=edge_key,
    )


@pytest.fixture
def repo():
    return SQLAlchemyBlobReferenceRepository()


# ── TestBlobReferenceRepository ───────────────────────────────────────────


class TestBlobReferenceRepository:

    # ── save (upsert) ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_save_creates_new_reference(self, session, repo):
        ref = _ref(blob_id="b1", owner_id="u1", edge_key="avatar")
        await repo.save(ref=ref)
        await session.commit()

        from core.db.models.blob_reference import BlobReferenceModel
        from sqlalchemy import select
        from core.db.session import session as db_session

        row = (await db_session.execute(
            select(BlobReferenceModel).where(
                BlobReferenceModel.owner_type == "user",
                BlobReferenceModel.owner_id == "u1",
                BlobReferenceModel.edge_key == "avatar",
            )
        )).scalar_one_or_none()

        assert row is not None
        assert row.blob_id == "b1"

    @pytest.mark.asyncio
    async def test_save_upsert_updates_blob_id(self, session, repo):
        ref1 = _ref(blob_id="old_blob", owner_id="u2", edge_key="avatar")
        await repo.save(ref=ref1)
        await session.commit()

        ref2 = BlobReference.create(
            blob_id="new_blob",
            owner_type="user",
            owner_id="u2",
            edge_key="avatar",
        )
        await repo.save(ref=ref2)
        await session.commit()

        from core.db.models.blob_reference import BlobReferenceModel
        from sqlalchemy import select
        from core.db.session import session as db_session

        rows = (await db_session.execute(
            select(BlobReferenceModel).where(
                BlobReferenceModel.owner_type == "user",
                BlobReferenceModel.owner_id == "u2",
                BlobReferenceModel.edge_key == "avatar",
            )
        )).scalars().all()

        assert len(rows) == 1
        assert rows[0].blob_id == "new_blob"

    # ── delete_by_edge ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_by_edge_existing(self, session, repo):
        ref = _ref(owner_id="u3", edge_key="cover")
        await repo.save(ref=ref)
        await session.commit()

        deleted = await repo.delete_by_edge(owner_type="user", owner_id="u3", edge_key="cover")
        await session.commit()

        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_by_edge_nonexistent(self, session, repo):
        deleted = await repo.delete_by_edge(owner_type="user", owner_id="nobody", edge_key="avatar")
        assert deleted is False

    # ── delete_all_by_owner ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_all_by_owner(self, session, repo):
        owner_id = "u4"
        ref1 = _ref(owner_id=owner_id, edge_key="avatar")
        ref2 = _ref(owner_id=owner_id, edge_key="cover")
        ref3 = _ref(owner_id="other", edge_key="avatar")
        for r in (ref1, ref2, ref3):
            await repo.save(ref=r)
        await session.commit()

        count = await repo.delete_all_by_owner(owner_type="user", owner_id=owner_id)
        await session.commit()

        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_all_by_owner_no_rows(self, session, repo):
        count = await repo.delete_all_by_owner(owner_type="user", owner_id="ghost")
        assert count == 0
