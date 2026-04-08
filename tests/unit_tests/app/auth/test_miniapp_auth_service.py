"""
MiniappAuthCommandService 单元测试

覆盖 bind_and_login 的主要分支：
  1. 按 openid 找到已有用户
  2. 按手机号找到已有用户（首次绑定 openid）
  3. 按手机号找到已有用户，但该手机号已绑定其它 openid → 409
  4. 全新用户，自动创建账号
  5. openid 找不到，手机号也被其它账号占用 → 409

所有 IO 依赖均通过 AsyncMock 注入，无 DB 无网络。
@Transactional() 通过 patch pami_event_framework.Transactional 为透传装饰器来绕过。
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.auth.application.port.user_account_port import UserAuthInfoDTO
from app.auth.domain.command.miniapp_bind import MiniappBindCommand
from core.response.rersponse_exception import ApiResponseException


@pytest.fixture(autouse=True)
def _bypass_transactional():
    """让 @Transactional() 内部 get_session 抛 LookupError，跳过 DB session。"""
    with patch(
        "pami_event_framework.persistence.session.get_session",
        side_effect=LookupError("no session in unit test"),
    ):
        yield


def _make_user(
    user_id: str = "u1",
    email: str = "test@example.com",
    nickname: str = "testuser",
    avatar: str | None = None,
    roles: list | None = None,
) -> UserAuthInfoDTO:
    return UserAuthInfoDTO(
        user_id=user_id,
        email=email,
        nickname=nickname,
        avatar=avatar,
        roles=roles or [],
    )


def _make_service(port: AsyncMock):
    from app.auth.application.service.miniapp_auth import MiniappAuthCommandService
    return MiniappAuthCommandService(user_account_port=port)


def _make_port(
    by_unionid: UserAuthInfoDTO | None = None,
    by_oauth: UserAuthInfoDTO | None = None,
    by_phone: UserAuthInfoDTO | None = None,
    oauth_binding_uid: str | None = None,
    created_user: UserAuthInfoDTO | None = None,
) -> AsyncMock:
    port = AsyncMock()
    port.find_by_unionid.return_value = by_unionid
    port.find_by_oauth.return_value = by_oauth
    port.find_by_phone.return_value = by_phone
    port.get_oauth_binding_uid.return_value = oauth_binding_uid
    port.create_user.return_value = created_user or _make_user(user_id="new_u")
    port.bind_phone_and_link_oauth.return_value = None
    return port


def _cmd(
    openid: str = "o_ABC",
    phone: str = "13800138000",
    unionid: str | None = None,
) -> MiniappBindCommand:
    return MiniappBindCommand(openid=openid, phone=phone, unionid=unionid)


# ── 分支 1：按 openid 找到已有用户 ────────────────────────────────────────


class TestBindByOpenid:
    @pytest.mark.asyncio
    async def test_returns_existing_user(self):
        existing = _make_user(user_id="existing_u", email="exist@example.com")
        port = _make_port(by_oauth=existing)
        service = _make_service(port)

        result = await service.bind_and_login(command=_cmd())

        assert result.user_id == "existing_u"
        assert result.access_token
        assert result.refresh_token

    @pytest.mark.asyncio
    async def test_bind_phone_called_with_link_oauth_false(self):
        """openid 已绑定时，link_oauth 应为 False（不重复写 linked_account）"""
        existing = _make_user(user_id="existing_u")
        port = _make_port(by_oauth=existing)
        service = _make_service(port)

        await service.bind_and_login(command=_cmd(openid="o_OLD"))

        port.bind_phone_and_link_oauth.assert_called_once()
        call_kwargs = port.bind_phone_and_link_oauth.call_args.kwargs
        assert call_kwargs["link_oauth"] is False


# ── 分支 2：按手机号找到已有用户（首次绑定 openid）────────────────────────


class TestBindByPhone:
    @pytest.mark.asyncio
    async def test_returns_phone_user(self):
        phone_user = _make_user(user_id="phone_u", email="phone@example.com")
        port = _make_port(by_oauth=None, by_phone=phone_user, oauth_binding_uid=None)
        service = _make_service(port)

        result = await service.bind_and_login(command=_cmd())

        assert result.user_id == "phone_u"

    @pytest.mark.asyncio
    async def test_bind_phone_called_with_link_oauth_true(self):
        """手机号用户首次绑定 openid，link_oauth 应为 True"""
        phone_user = _make_user(user_id="phone_u")
        port = _make_port(by_oauth=None, by_phone=phone_user, oauth_binding_uid=None)
        service = _make_service(port)

        await service.bind_and_login(command=_cmd(openid="o_NEW"))

        port.bind_phone_and_link_oauth.assert_called_once()
        call_kwargs = port.bind_phone_and_link_oauth.call_args.kwargs
        assert call_kwargs["link_oauth"] is True
        assert call_kwargs["external_uid"] == "o_NEW"


# ── 分支 3：手机号已绑定其它 openid → 409 ────────────────────────────────


class TestBindPhoneConflict:
    @pytest.mark.asyncio
    async def test_raises_409_when_phone_bound_to_different_openid(self):
        phone_user = _make_user(user_id="phone_u")
        port = _make_port(
            by_oauth=None,
            by_phone=phone_user,
            oauth_binding_uid="o_OTHER",  # 已绑定别的 openid
        )
        service = _make_service(port)

        with pytest.raises(ApiResponseException) as exc_info:
            await service.bind_and_login(command=_cmd(openid="o_NEW"))

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_no_error_when_same_openid_already_bound(self):
        """手机号绑定的 openid 与本次相同，应正常通过"""
        phone_user = _make_user(user_id="phone_u")
        port = _make_port(
            by_oauth=None,
            by_phone=phone_user,
            oauth_binding_uid="o_SAME",
        )
        service = _make_service(port)

        result = await service.bind_and_login(command=_cmd(openid="o_SAME"))
        assert result.user_id == "phone_u"


# ── 分支 4：全新用户，自动创建 ───────────────────────────────────────────


class TestBindNewUser:
    @pytest.mark.asyncio
    async def test_creates_new_user(self):
        new_user = _make_user(user_id="new_u", email="wx_o_ABC@miniapp.local")
        port = _make_port(by_oauth=None, by_phone=None, created_user=new_user)
        service = _make_service(port)

        result = await service.bind_and_login(command=_cmd(openid="o_ABC"))

        port.create_user.assert_called_once()
        assert result.user_id == "new_u"

    @pytest.mark.asyncio
    async def test_created_email_contains_openid(self):
        openid = "o_XYZ123"
        new_user = _make_user(user_id="new_u", email=f"wx_{openid}@miniapp.local")
        port = _make_port(by_oauth=None, by_phone=None, created_user=new_user)
        service = _make_service(port)

        await service.bind_and_login(command=_cmd(openid=openid))

        create_kwargs = port.create_user.call_args.kwargs
        assert openid in create_kwargs["email"]


# ── 分支 5：openid 找到用户，但手机号被其它账号占用 → 409 ─────────────────


class TestBindPhoneOccupied:
    @pytest.mark.asyncio
    async def test_raises_409_when_phone_taken_by_other(self):
        """
        场景：openid 找到用户 A，但该手机号已被用户 B 绑定。

        代码路径：find_by_oauth 返回 A → else 分支 →
        find_by_phone 返回 B（user_id != A.user_id）→ 409
        """
        user_a = _make_user(user_id="openid_u")
        user_b = _make_user(user_id="other_u")

        port = AsyncMock()
        port.find_by_oauth.return_value = user_a   # 按 openid 找到 A
        port.find_by_phone.return_value = user_b   # 手机号属于 B
        port.get_oauth_binding_uid.return_value = None
        port.create_user.return_value = user_a
        port.bind_phone_and_link_oauth.return_value = None

        service = _make_service(port)

        with pytest.raises(ApiResponseException) as exc_info:
            await service.bind_and_login(command=_cmd())

        assert exc_info.value.status_code == 409


class TestLoginOrRegister:
    @pytest.mark.asyncio
    async def test_creates_new_user_without_phone(self):
        port = _make_port(by_unionid=None, by_oauth=None)
        service = _make_service(port)

        result = await service.login_or_register(
            openid="o_NEW",
            unionid=None,
            session_meta={"openid": "o_NEW"},
        )

        assert result.user_id == "new_u"
        port.create_user.assert_called_once()
        call_kwargs = port.bind_phone_and_link_oauth.call_args.kwargs
        assert call_kwargs["phone"] is None
        assert call_kwargs["external_uid"] == "o_NEW"

    @pytest.mark.asyncio
    async def test_reuses_existing_user_by_unionid(self):
        existing = _make_user(user_id="union_u", email="union@example.com")
        port = _make_port(by_unionid=existing, by_oauth=None)
        service = _make_service(port)

        result = await service.login_or_register(
            openid="o_NEW",
            unionid="u_SHARED",
            session_meta={"unionid": "u_SHARED"},
        )

        assert result.user_id == "union_u"
        port.create_user.assert_not_called()
        call_kwargs = port.bind_phone_and_link_oauth.call_args.kwargs
        assert call_kwargs["link_oauth"] is True

    @pytest.mark.asyncio
    async def test_raises_409_when_unionid_and_openid_belong_to_different_users(self):
        union_user = _make_user(user_id="union_u")
        openid_user = _make_user(user_id="openid_u")
        port = _make_port(by_unionid=union_user, by_oauth=openid_user)
        service = _make_service(port)

        with pytest.raises(ApiResponseException) as exc_info:
            await service.login_or_register(openid="o_CONFLICT", unionid="u_CONFLICT")

        assert exc_info.value.status_code == 409
