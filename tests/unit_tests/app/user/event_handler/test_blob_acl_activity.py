"""on_blob_processing_completed_activity 单元测试

测试 User 域 ACL 的核心路由逻辑：
- owner_type == "user" && edge_key == "avatar" → 调用 set_avatar + 写 Redis
- owner_type 不匹配 → 跳过
- owner_id 为空 → 跳过（警告日志）
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── 辅助：构造事件 payload ─────────────────────────────────────────────────


def _avatar_payload(
    blob_id: str = "blob-001",
    owner_id: str = "user-001",
    owner_type: str = "user",
    edge_key: str = "avatar",
    blob_sha256: str = "a" * 64,
) -> dict:
    return {
        "blob_id": blob_id,
        "blob_sha256": blob_sha256,
        "owner_id": owner_id,
        "owner_type": owner_type,
        "edge_key": edge_key,
    }


# ── TestOnBlobProcessingCompletedActivity ────────────────────────────────


from app.user.event_handler.activities import on_user_blob_processing_completed_activity


class TestOnBlobProcessingCompletedActivity:
    @pytest.mark.asyncio
    async def test_sets_avatar_and_writes_redis_for_user_avatar(self):
        """owner_type=user + edge_key=avatar → set_avatar 被调用，avatar_status_port.set_approved 被调用"""
        mock_usecase = AsyncMock()
        mock_avatar_status_port = AsyncMock()

        await on_user_blob_processing_completed_activity(
            _avatar_payload(),
            usecase=mock_usecase,
            avatar_status_port=mock_avatar_status_port,
        )

        mock_usecase.set_avatar.assert_awaited_once()
        call_kwargs = mock_usecase.set_avatar.call_args.kwargs
        assert call_kwargs["command"].user_id == "user-001"
        assert call_kwargs["command"].avatar == "blob-001"

        mock_avatar_status_port.set_approved.assert_awaited_once_with(user_id="user-001")

    @pytest.mark.asyncio
    async def test_skips_when_owner_type_is_not_user(self):
        mock_usecase = AsyncMock()
        mock_avatar_status_port = AsyncMock()

        await on_user_blob_processing_completed_activity(
            _avatar_payload(owner_type="post"),
            usecase=mock_usecase,
            avatar_status_port=mock_avatar_status_port,
        )

        mock_usecase.set_avatar.assert_not_awaited()
        mock_avatar_status_port.set_approved.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_when_edge_key_is_not_avatar(self):
        mock_usecase = AsyncMock()
        mock_avatar_status_port = AsyncMock()

        await on_user_blob_processing_completed_activity(
            _avatar_payload(edge_key="cover"),
            usecase=mock_usecase,
            avatar_status_port=mock_avatar_status_port,
        )

        mock_usecase.set_avatar.assert_not_awaited()
        mock_avatar_status_port.set_approved.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_when_owner_id_is_missing(self):
        mock_usecase = AsyncMock()
        mock_avatar_status_port = AsyncMock()

        await on_user_blob_processing_completed_activity(
            _avatar_payload(owner_id=None),
            usecase=mock_usecase,
            avatar_status_port=mock_avatar_status_port,
        )

        mock_usecase.set_avatar.assert_not_awaited()
        mock_avatar_status_port.set_approved.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_when_owner_type_and_edge_key_both_none(self):
        mock_usecase = AsyncMock()
        mock_avatar_status_port = AsyncMock()

        await on_user_blob_processing_completed_activity(
            _avatar_payload(owner_type=None, edge_key=None),
            usecase=mock_usecase,
            avatar_status_port=mock_avatar_status_port,
        )

        mock_usecase.set_avatar.assert_not_awaited()
        mock_avatar_status_port.set_approved.assert_not_awaited()
