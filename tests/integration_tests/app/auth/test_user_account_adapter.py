"""UserAccountAdapter 集成测试 - 真实 DB，验证 ACL 适配器的持久化行为"""

import pytest
from unittest.mock import AsyncMock, patch

from app.auth.adapter.output.user_account_adapter import UserAccountAdapter
from app.user.adapter.output.repository.user import SQLAlchemyUserRepository
from app.user.domain.factory.user_factory import UserFactory


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def user_repo():
    return SQLAlchemyUserRepository()


@pytest.fixture
def adapter(user_repo):
    return UserAccountAdapter(
        repository=user_repo,
        user_factory=UserFactory(),
    )


async def _flush(repo, user, session):
    """mock _flush_events 后提交，令 session_factory 可见。"""
    with patch.object(repo, "_flush_events", new=AsyncMock()):
        await repo.save(user=user)
    await session.commit()


# ── TestUserAccountAdapter ────────────────────────────────────────────────


class TestUserAccountAdapter:

    # ── find_by_oauth ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_find_by_oauth_returns_dto(self, session, adapter, user_repo):
        user = await adapter.create_user(
            email="wx@test.com",
            password="password123",
            nickname="wxtester",
            role="student",
        )
        await session.commit()

        await adapter.bind_phone_and_link_oauth(
            user_id=user.user_id,
            phone="13800000001",
            provider="wechat_miniapp",
            external_uid="openid_001",
            union_id=None,
            meta={},
            link_oauth=True,
        )
        await session.commit()

        found = await adapter.find_by_oauth(
            provider="wechat_miniapp", external_uid="openid_001"
        )

        assert found is not None
        assert found.user_id == user.user_id
        assert found.email == "wx@test.com"

    @pytest.mark.asyncio
    async def test_find_by_oauth_not_found(self, session, adapter):
        found = await adapter.find_by_oauth(
            provider="wechat_miniapp", external_uid="nonexistent_openid"
        )
        assert found is None

    # ── find_by_phone ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_find_by_phone_returns_dto(self, session, adapter):
        user = await adapter.create_user(
            email="phone@test.com",
            password="password123",
            nickname="phonetester",
            role="student",
        )
        await session.commit()

        await adapter.bind_phone_and_link_oauth(
            user_id=user.user_id,
            phone="13900000001",
            provider="wechat_miniapp",
            external_uid="openid_phone",
            union_id=None,
            meta={},
            link_oauth=False,
        )
        await session.commit()

        found = await adapter.find_by_phone(phone="13900000001")

        assert found is not None
        assert found.user_id == user.user_id

    @pytest.mark.asyncio
    async def test_find_by_phone_not_found(self, session, adapter):
        found = await adapter.find_by_phone(phone="00000000000")
        assert found is None

    # ── get_oauth_binding_uid ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_oauth_binding_uid_found(self, session, adapter):
        user = await adapter.create_user(
            email="oauth@test.com",
            password="password123",
            nickname="oauthtester",
            role="student",
        )
        await session.commit()

        await adapter.bind_phone_and_link_oauth(
            user_id=user.user_id,
            phone="13700000001",
            provider="wechat_miniapp",
            external_uid="openid_bound",
            union_id=None,
            meta={},
            link_oauth=True,
        )
        await session.commit()

        uid = await adapter.get_oauth_binding_uid(
            user_id=user.user_id, provider="wechat_miniapp"
        )
        assert uid == "openid_bound"

    @pytest.mark.asyncio
    async def test_get_oauth_binding_uid_not_bound(self, session, adapter):
        user = await adapter.create_user(
            email="unbound@test.com",
            password="password123",
            nickname="unboundtester",
            role="student",
        )
        await session.commit()

        uid = await adapter.get_oauth_binding_uid(
            user_id=user.user_id, provider="wechat_miniapp"
        )
        assert uid is None

    @pytest.mark.asyncio
    async def test_get_oauth_binding_uid_user_not_found(self, session, adapter):
        uid = await adapter.get_oauth_binding_uid(
            user_id="nonexistent_user", provider="wechat_miniapp"
        )
        assert uid is None

    # ── create_user ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_user_persists_and_returns_dto(self, session, adapter, user_repo):
        dto = await adapter.create_user(
            email="new@test.com",
            password="secret",
            nickname="newuser",
            role="student",
        )
        await session.commit()

        assert dto.email == "new@test.com"
        assert dto.nickname == "newuser"
        assert "student" in dto.roles

        persisted = await user_repo.get_user_by_id(user_id=dto.user_id)
        assert persisted is not None
        assert persisted.email == "new@test.com"

    # ── bind_phone_and_link_oauth ─────────────────────────────────────

    @pytest.mark.asyncio
    async def test_bind_phone_and_link_oauth_links_both(self, session, adapter):
        user = await adapter.create_user(
            email="bind@test.com",
            password="password123",
            nickname="bindtester",
            role="student",
        )
        await session.commit()

        await adapter.bind_phone_and_link_oauth(
            user_id=user.user_id,
            phone="13600000001",
            provider="wechat_miniapp",
            external_uid="openid_bind",
            union_id="unionid_bind",
            meta={"session": {}},
            link_oauth=True,
        )
        await session.commit()

        by_phone = await adapter.find_by_phone(phone="13600000001")
        assert by_phone is not None

        by_oauth = await adapter.find_by_oauth(
            provider="wechat_miniapp", external_uid="openid_bind"
        )
        assert by_oauth is not None
        assert by_phone.user_id == by_oauth.user_id

    @pytest.mark.asyncio
    async def test_bind_phone_without_link_oauth(self, session, adapter):
        user = await adapter.create_user(
            email="phoneonly@test.com",
            password="password123",
            nickname="phoneonlytester",
            role="student",
        )
        await session.commit()

        await adapter.bind_phone_and_link_oauth(
            user_id=user.user_id,
            phone="13500000001",
            provider="wechat_miniapp",
            external_uid="openid_noop",
            union_id=None,
            meta={},
            link_oauth=False,
        )
        await session.commit()

        by_phone = await adapter.find_by_phone(phone="13500000001")
        assert by_phone is not None

        by_oauth = await adapter.find_by_oauth(
            provider="wechat_miniapp", external_uid="openid_noop"
        )
        assert by_oauth is None
