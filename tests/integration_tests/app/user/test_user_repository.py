"""User Repository 集成测试 - 真实 DB，_flush_events mock

测试目标：验证 SQLAlchemyUserRepository 的 SQL 查询行为是否正确。
_flush_events 写入 outbox 的逻辑需要 pami_event_framework SessionManager，
集成测试不关心事件发布，统一 mock 掉。
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.user.domain.aggregate.user import User
from app.user.domain.entity.linked_account import LinkedAccount
from app.user.adapter.output.repository.user import SQLAlchemyUserRepository


# ── 辅助工厂 ─────────────────────────────────────────────────────────────


def _domain_user(
    *,
    user_id: str = "u1",
    email: str = "test@example.com",
    nickname: str = "testuser",
    role: str = "",
    phone: str | None = None,
) -> User:
    user = User.create(
        user_id=user_id,
        email=email,
        password="password123",
        nickname=nickname,
        role=role,
    )
    if phone:
        user.phone = phone
    user.clear_domain_events()
    return user


async def _save(repo: SQLAlchemyUserRepository, user: User, session) -> None:
    """mock _flush_events 后保存并提交，确保 session_factory 读取时可见。"""
    with patch.object(repo, "_flush_events", new=AsyncMock()):
        await repo.save(user=user)
    await session.commit()


@pytest.fixture
def repo():
    return SQLAlchemyUserRepository()


# ── TestUserRepository ────────────────────────────────────────────────────


class TestUserRepository:
    # ── save + get_by_id ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_save_and_get_by_id(self, session, repo):
        user = _domain_user()
        await _save(repo, user, session)

        found = await repo.get_user_by_id(user_id="u1")

        assert found is not None
        assert found.user_id == "u1"
        assert found.email == "test@example.com"
        assert found.nickname == "testuser"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found_returns_none(self, session, repo):
        found = await repo.get_user_by_id(user_id="nonexistent")
        assert found is None

    # ── get_by_email_or_nickname ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_by_email_or_nickname_by_email(self, session, repo):
        user = _domain_user()
        await _save(repo, user, session)

        found = await repo.get_user_by_email_or_nickname(email="test@example.com")

        assert found is not None
        assert found.user_id == "u1"

    @pytest.mark.asyncio
    async def test_get_by_email_or_nickname_by_nickname(self, session, repo):
        user = _domain_user()
        await _save(repo, user, session)

        found = await repo.get_user_by_email_or_nickname(nickname="testuser")

        assert found is not None
        assert found.user_id == "u1"

    @pytest.mark.asyncio
    async def test_get_by_email_or_nickname_not_found(self, session, repo):
        found = await repo.get_user_by_email_or_nickname(
            email="ghost@example.com", nickname="ghost"
        )
        assert found is None

    # ── get_user_by_email ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, session, repo):
        user = _domain_user()
        await _save(repo, user, session)

        found = await repo.get_user_by_email(email="test@example.com")

        assert found is not None
        assert found.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, session, repo):
        found = await repo.get_user_by_email(email="nobody@example.com")
        assert found is None

    # ── get_user_by_phone ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_user_by_phone(self, session, repo):
        user = _domain_user(phone="+8613800138000")
        await _save(repo, user, session)

        found = await repo.get_user_by_phone(phone="+8613800138000")

        assert found is not None
        assert found.phone == "+8613800138000"

    @pytest.mark.asyncio
    async def test_get_user_by_phone_not_found(self, session, repo):
        found = await repo.get_user_by_phone(phone="+99999999999")
        assert found is None

    # ── get_user_by_linked_account ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_user_by_linked_account(self, session, repo):
        user = _domain_user()
        user.link_account(
            account=LinkedAccount(provider="wechat", provider_account_id="wx_999")
        )
        user.clear_domain_events()
        await _save(repo, user, session)

        found = await repo.get_user_by_linked_account(
            provider="wechat", provider_account_id="wx_999"
        )

        assert found is not None
        assert found.user_id == "u1"
        assert any(
            a.provider == "wechat" and a.provider_account_id == "wx_999"
            for a in found.linked_accounts
        )

    @pytest.mark.asyncio
    async def test_get_user_by_linked_account_not_found(self, session, repo):
        found = await repo.get_user_by_linked_account(
            provider="wechat", provider_account_id="nonexistent"
        )
        assert found is None

    # ── get_users ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_users_returns_all(self, session, repo):
        for i in range(3):
            user = _domain_user(
                user_id=f"uid_{i}",
                email=f"user{i}@example.com",
                nickname=f"user{i}",
            )
            await _save(repo, user, session)

        users = await repo.get_users(limit=10)

        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_get_users_respects_limit(self, session, repo):
        for i in range(5):
            user = _domain_user(
                user_id=f"uid_{i}",
                email=f"user{i}@example.com",
                nickname=f"user{i}",
            )
            await _save(repo, user, session)

        users = await repo.get_users(limit=2)

        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_get_users_empty(self, session, repo):
        users = await repo.get_users(limit=10)
        assert users == []

    # ── save (update existing) ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_save_updates_existing_record(self, session, repo):
        user = _domain_user()
        await _save(repo, user, session)

        user.update_profile(nickname="updated_nick", bio="new bio")
        user.clear_domain_events()
        await _save(repo, user, session)

        found = await repo.get_user_by_id(user_id="u1")

        assert found is not None
        assert found.nickname == "updated_nick"
        assert found.bio == "new bio"

    @pytest.mark.asyncio
    async def test_save_with_role_persists_role(self, session, repo):
        user = _domain_user(role="STUDENT")
        await _save(repo, user, session)

        found = await repo.get_user_by_id(user_id="u1")

        assert found is not None
        assert "STUDENT" in found.roles
