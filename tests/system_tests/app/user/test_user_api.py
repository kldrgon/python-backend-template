"""
User API 系统测试骨架

测试范围：HTTP 请求 → 中间件 → 路由 → Service → DB
外部依赖：Kafka（mock）、验证码（mock）、真实 DB
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4


# ── 注册 ─────────────────────────────────────────────────────────────────


class TestRegisterApi:
    async def test_register_success(self, client):
        email = f"new_{uuid4().hex[:8]}@example.com"
        with patch("app.user.application.service.user.CaptchaService.verify_code", return_value=True):
            with patch("app.user.application.service.user.CaptchaService.delete_code", return_value=True):
                resp = await client.post(
                    "/user/v1/register",
                    json={
                        "email": email,
                        "nickname": "newuser",
                        "password": "Password123",
                        "confirmPassword": "Password123",
                        "role": "student",
                        "captcha_code": "000000",
                    },
                )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == email
        assert data["nickname"] == "newuser"

    async def test_register_invalid_captcha(self, client):
        with patch("app.user.application.service.user.CaptchaService.verify_code", return_value=False):
            resp = await client.post(
                "/user/v1/register",
                json={
                    "email": "new@example.com",
                    "nickname": "newuser",
                    "password": "Password123",
                    "confirmPassword": "Password123",
                    "role": "student",
                    "captcha_code": "wrong",
                },
            )
        assert resp.status_code == 400

    async def test_register_duplicate_email(self, client, registered_user):
        with patch("app.user.application.service.user.CaptchaService.verify_code", return_value=True):
            with patch("app.user.application.service.user.CaptchaService.delete_code", return_value=True):
                resp = await client.post(
                    "/user/v1/register",
                    json={
                        "email": registered_user["email"],   # 已注册的邮箱
                        "nickname": "another",
                        "password": "Password123",
                        "confirmPassword": "Password123",
                        "role": "student",
                        "captcha_code": "000000",
                    },
                )
        assert resp.status_code == 409


# ── 登录 ─────────────────────────────────────────────────────────────────


class TestLoginApi:
    async def test_login_success(self, client, registered_user):
        resp = await client.post(
            "/user/v1/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == registered_user["email"]

    async def test_login_wrong_password(self, client, registered_user):
        resp = await client.post(
            "/user/v1/login",
            json={
                "email": registered_user["email"],
                "password": "wrong_password",
            },
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post(
            "/user/v1/login",
            json={"email": "ghost@example.com", "password": "Password123"},
        )
        assert resp.status_code == 404


# ── 用户档案 ──────────────────────────────────────────────────────────────


class TestUserProfileApi:
    async def test_get_profile_success(self, client, registered_user, auth_headers):
        resp = await client.get(
            f"/user/v1/profile",
            params={"user_id": registered_user["user_id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["user_id"] == registered_user["user_id"]
        assert data["email"] == registered_user["email"]

    async def test_get_profile_without_auth(self, client, registered_user):
        """无 Token 也可以访问（公开接口）"""
        resp = await client.get(
            "/user/v1/profile",
            params={"user_id": registered_user["user_id"]},
        )
        assert resp.status_code == 200

    async def test_update_profile(self, client, registered_user, auth_headers):
        resp = await client.patch(
            f"/user/v1/{registered_user['user_id']}",
            json={"nickname": "updated_nick", "bio": "hello world"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["nickname"] == "updated_nick"
        assert data["bio"] == "hello world"


# ── 角色管理 ──────────────────────────────────────────────────────────────


class TestRolesApi:
    async def test_assign_roles(self, client, registered_user, auth_headers):
        resp = await client.patch(
            "/user/v1/roles",
            json={
                "user_id": registered_user["user_id"],
                "roles": ["teacher"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] is True


# ── 发送验证码 ────────────────────────────────────────────────────────────


class TestSendCaptchaApi:
    async def test_send_captcha_success(self, client, session):
        with patch("core.helpers.email_sender.EmailSender.send_captcha_email", new_callable=AsyncMock, return_value=True):
            resp = await client.post(
                "/user/v1/send-captcha",
                params={"email": "captcha_test@example.com"},
            )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == "captcha_test@example.com"
        assert "expires_in" in data

    async def test_send_captcha_too_frequent(self, client, session, redis_container):
        email = "freq_test@example.com"
        redis_client = redis_container["client"]
        # TTL > 240 秒触发频率限制
        await redis_client.setex(f"captcha:{email}", 299, "000000")

        with patch("core.helpers.email_sender.EmailSender.send_captcha_email", new_callable=AsyncMock, return_value=True):
            resp = await client.post(
                "/user/v1/send-captcha",
                params={"email": email},
            )
        assert resp.status_code in (400, 429)


# ── 用户列表 ──────────────────────────────────────────────────────────────


class TestGetUserListApi:
    async def test_get_user_list_with_registered_user(
        self, client, session, registered_user
    ):
        resp = await client.get("/user/v1/", params={"limit": 10, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        user_ids = [u["user_id"] for u in data["items"]]
        assert registered_user["user_id"] in user_ids

    async def test_get_user_list_pagination(self, client, session, redis_container):
        # 注册 3 个用户
        for i in range(3):
            email = f"paged_{i}@example.com"
            await redis_container["client"].setex(f"captcha:{email}", 300, "000000")
            with patch(
                "app.user.application.service.user.CaptchaService.verify_code",
                return_value=True,
            ):
                with patch(
                    "app.user.application.service.user.CaptchaService.delete_code",
                    return_value=True,
                ):
                    await client.post(
                        "/user/v1/register",
                        json={
                            "email": email,
                            "nickname": f"pageduser{i}",
                            "password": "Password123",
                            "confirmPassword": "Password123",
                            "role": "student",
                            "captcha_code": "000000",
                        },
                    )

        resp = await client.get("/user/v1/", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 3
        assert len(data["items"]) == 2


# ── 完整异步流程 ──────────────────────────────────────────────────────────


class TestUserCompleteFlow:
    async def test_register_triggers_user_created_workflow(
        self, client, all_workers_running, redis_container, session
    ):
        """
        验证完整事件链：
        注册 → UserCreatedEvent → outbox → Kafka → Temporal → send_welcome_email_activity
        通过监控 outbox_events.status 从 PENDING 变为 PUBLISHED 来判断链路完成。
        """
        import asyncio
        from tests.support.async_utils import wait_until
        from core.db.session import session_factory
        from sqlalchemy import text

        email = "flow_test@example.com"
        captcha_code = "222222"
        redis_client = redis_container["client"]
        await redis_client.setex(f"captcha:{email}", 300, captcha_code)

        resp = await client.post(
            "/user/v1/register",
            json={
                "email": email,
                "nickname": "flowuser",
                "password": "Password123",
                "confirmPassword": "Password123",
                "role": "student",
                "captcha_code": captcha_code,
            },
        )
        assert resp.status_code == 200
        user_id = resp.json()["data"]["userId"]

        # 等待 outbox 事件被 OutboxPublisher 发布到 Kafka（状态变为 PUBLISHED）
        async def outbox_event_published() -> bool:
            async with session_factory() as s:
                result = await s.execute(
                    text(
                        "SELECT COUNT(*) FROM outbox_events "
                        "WHERE aggregate_id = :uid AND status = 'PUBLISHED'"
                    ),
                    {"uid": user_id},
                )
                count = result.scalar_one()
            return int(count) > 0

        await wait_until(outbox_event_published, timeout=30)

        # 额外等待 Temporal workflow + activity 完成
        await asyncio.sleep(3)

        # 验证用户仍可正常访问（链路中无异常导致数据损坏）
        from app.user.adapter.output.repository.user import SQLAlchemyUserRepository
        found = await SQLAlchemyUserRepository().get_user_by_id(user_id=user_id)
        assert found is not None
        assert found.email == email


# ── 头像状态轮询 ──────────────────────────────────────────────────────────


class TestAvatarStatusApi:
    async def test_get_avatar_status_default_pending(self, client, session, registered_user):
        """Redis 中无状态 key 时返回 PENDING"""
        resp = await client.get(
            f"/user/v1/{registered_user['user_id']}/avatar/status"
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "PENDING"

    async def test_get_avatar_status_approved(self, client, session, registered_user, redis_container):
        """Redis 中写入 APPROVED 后，端点返回 APPROVED"""
        from core.config import config
        avatar_key_prefix = config.user.avatar_status_key_prefix

        user_id = registered_user["user_id"]
        redis_client = redis_container["client"]
        await redis_client.setex(f"{avatar_key_prefix}{user_id}", 300, "APPROVED")

        resp = await client.get(f"/user/v1/{user_id}/avatar/status")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "APPROVED"

    async def test_get_avatar_status_rejected(self, client, session, registered_user, redis_container):
        """Redis 中写入 REJECTED 后，端点返回 REJECTED"""
        from core.config import config
        avatar_key_prefix = config.user.avatar_status_key_prefix

        user_id = registered_user["user_id"]
        redis_client = redis_container["client"]
        await redis_client.setex(f"{avatar_key_prefix}{user_id}", 300, "REJECTED")

        resp = await client.get(f"/user/v1/{user_id}/avatar/status")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "REJECTED"


# ── 头像完整异步流 ────────────────────────────────────────────────────────


class TestAvatarCompleteFlow:
    async def test_blob_processing_completed_sets_user_avatar(
        self, client, all_workers_running, redis_container, session, registered_user
    ):
        """
        验证完整头像绑定链路：
        手动插入 BLOB_PROCESSING_COMPLETED outbox 事件
        → OutboxPublisher → Kafka → OnBlobProcessingCompletedWorkflow（User 域）
        → on_blob_processing_completed_activity → set_avatar + Redis APPROVED
        → GET /users/{id}/avatar/status 返回 APPROVED
        """
        import asyncio
        import json
        import uuid
        from datetime import datetime, timezone
        from tests.support.async_utils import wait_until
        from core.db.session import session_factory
        from sqlalchemy import text
        from core.config import config
        avatar_key_prefix = config.user.avatar_status_key_prefix

        user_id = registered_user["user_id"]
        blob_id = f"test-blob-{uuid.uuid4().hex[:8]}"

        event_payload = {
            "blob_id": blob_id,
            "blob_sha256": "a" * 64,
            "owner_id": user_id,
            "owner_type": "user",
            "edge_key": "avatar",
        }

        # 直接向 outbox_events 插入 PENDING 事件，模拟 Blob context 发出的事件
        event_id = str(uuid.uuid4())
        async with session_factory() as s:
            await s.execute(
                text(
                    "INSERT INTO outbox_events "
                    "(event_id, event_type, event_data, aggregate_id, aggregate_type, status, retry_count, created_at) "
                    "VALUES (:eid, :etype, :edata, :aid, :atype, 'PENDING', 0, :ts)"
                ),
                {
                    "eid": event_id,
                    "etype": "BLOB_PROCESSING_COMPLETED",
                    "edata": json.dumps(
                        {
                            "event_id": event_id,
                            "event_type": "BLOB_PROCESSING_COMPLETED",
                            "payload": event_payload,
                        }
                    ),
                    "aid": blob_id,
                    "atype": "Blob",
                    "ts": datetime.now(timezone.utc),
                },
            )
            await s.commit()

        # 等待 OutboxPublisher 发布（status → PUBLISHED）
        async def outbox_published() -> bool:
            async with session_factory() as s:
                count = (
                    await s.execute(
                        text(
                            "SELECT COUNT(*) FROM outbox_events "
                            "WHERE aggregate_id = :aid AND status = 'PUBLISHED'"
                        ),
                        {"aid": blob_id},
                    )
                ).scalar_one()
            return int(count) > 0

        await wait_until(outbox_published, timeout=30)

        # 等待 Temporal workflow + activity 执行完成（Redis 写入 APPROVED）
        redis_client = redis_container["client"]

        async def avatar_approved() -> bool:
            val = await redis_client.get(f"{avatar_key_prefix}{user_id}")
            return val == "APPROVED"

        await wait_until(avatar_approved, timeout=30)

        # 验证 User 的 avatar 字段被更新
        from app.user.adapter.output.repository.user import SQLAlchemyUserRepository
        found = await SQLAlchemyUserRepository().get_user_by_id(user_id=user_id)
        assert found is not None
        assert found.avatar == blob_id

        # 验证轮询接口返回 APPROVED
        resp = await client.get(f"/user/v1/{user_id}/avatar/status")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "APPROVED"
