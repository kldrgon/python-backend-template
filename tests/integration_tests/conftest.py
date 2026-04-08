"""
集成测试配置：需要真实数据库，每个测试前应用迁移并清空数据。
"""

import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio

from core.db.session import (
    set_session_context,
    reset_session_context,
    session as db_session,
)
from tests.support.test_db_coordinator import TestDbCoordinator

test_db_coordinator = TestDbCoordinator()


@pytest.fixture(scope="function", autouse=True)
def session_context():
    """每个集成测试独立的 session context，隔离 scoped session。"""
    session_id = str(uuid4())
    context = set_session_context(session_id=session_id)
    yield
    reset_session_context(context=context)


@pytest_asyncio.fixture
async def session():
    """提供干净数据库 session，测试前后均清空数据。"""
    test_db_coordinator.apply_alembic()
    test_db_coordinator.truncate_all()
    try:
        yield db_session
    finally:
        await db_session.remove()
        test_db_coordinator.truncate_all()
