"""UserQueryService 集成测试 - 真实 DB

测试目标：验证 SQLAlchemyUserQueryService 的分页查询、字段映射是否正确。
直接向 DB 写入 ORM 模型（make_user），绕过领域层，专注测试查询行为。
"""

import pytest

from app.user.adapter.output.query.user_query_service import SQLAlchemyUserQueryService
from tests.support.user_fixture import make_user


@pytest.fixture
def svc():
    return SQLAlchemyUserQueryService()


# ── TestUserQueryService ──────────────────────────────────────────────────


class TestUserQueryService:
    # ── list_users ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_users_empty(self, session, svc):
        items, total = await svc.list_users()

        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_users_returns_correct_total(self, session, svc):
        for i in range(3):
            session.add(
                make_user(
                    user_id=f"uid_{i}",
                    email=f"user{i}@example.com",
                    nickname=f"user{i}",
                )
            )
        await session.commit()

        items, total = await svc.list_users(limit=10, offset=0)

        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_list_users_limit(self, session, svc):
        for i in range(5):
            session.add(
                make_user(
                    user_id=f"uid_{i}",
                    email=f"user{i}@example.com",
                    nickname=f"user{i}",
                )
            )
        await session.commit()

        items, total = await svc.list_users(limit=2, offset=0)

        assert total == 5
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_list_users_offset_pagination(self, session, svc):
        for i in range(5):
            session.add(
                make_user(
                    user_id=f"uid_{i}",
                    email=f"user{i}@example.com",
                    nickname=f"user{i}",
                )
            )
        await session.commit()

        page1, total = await svc.list_users(limit=2, offset=0)
        page2, _ = await svc.list_users(limit=2, offset=2)
        page3, _ = await svc.list_users(limit=2, offset=4)

        assert total == 5
        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

        all_ids = {i.user_id for i in page1 + page2 + page3}
        assert len(all_ids) == 5

    @pytest.mark.asyncio
    async def test_list_users_offset_beyond_total_returns_empty(self, session, svc):
        session.add(make_user(user_id="uid_1", email="a@example.com", nickname="user1"))
        await session.commit()

        items, total = await svc.list_users(limit=10, offset=100)

        assert total == 1
        assert items == []

    @pytest.mark.asyncio
    async def test_list_users_item_fields(self, session, svc):
        session.add(
            make_user(
                user_id="uid_check",
                email="check@example.com",
                nickname="checkuser",
            )
        )
        await session.commit()

        items, _ = await svc.list_users(limit=10, offset=0)

        assert len(items) == 1
        item = items[0]
        assert item.user_id == "uid_check"
        assert item.email == "check@example.com"
        assert item.nickname == "checkuser"

    # ── get_user ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_user_returns_detail(self, session, svc):
        session.add(
            make_user(
                user_id="uid_detail",
                email="detail@example.com",
                nickname="detailuser",
            )
        )
        await session.commit()

        result = await svc.get_user(user_id="uid_detail")

        assert result is not None
        assert result.user_id == "uid_detail"
        assert result.email == "detail@example.com"
        assert result.nickname == "detailuser"
        assert result.is_admin is False
        assert result.roles == []

    @pytest.mark.asyncio
    async def test_get_user_admin_flag(self, session, svc):
        session.add(
            make_user(
                user_id="uid_admin",
                email="admin@example.com",
                nickname="adminuser",
                is_admin=True,
            )
        )
        await session.commit()

        result = await svc.get_user(user_id="uid_admin")

        assert result is not None
        assert result.is_admin is True

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, session, svc):
        result = await svc.get_user(user_id="nonexistent")
        assert result is None
