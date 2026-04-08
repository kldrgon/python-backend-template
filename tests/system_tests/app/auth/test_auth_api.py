"""
Auth API 系统测试

测试范围：HTTP 请求 → 中间件 → 路由 → Service → DB
外部依赖：微信 API（mock）
"""

from unittest.mock import AsyncMock, patch

from core.helpers.token import TokenHelper


# ── 刷新 Token ────────────────────────────────────────────────────────────


class TestRefreshTokenApi:
    async def test_refresh_token_success(self, client, registered_user):
        """使用合法 refresh token 换取新 access token"""
        login_resp = await client.post(
            "/user/v1/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["data"]["refresh_token"]

        resp = await client.post(
            "/auth/v1/refresh-token",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data

    async def test_refresh_token_with_access_token_fails(self, client, registered_user):
        """用 access token 调 refresh 接口应当失败"""
        login_resp = await client.post(
            "/user/v1/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        access_token = login_resp.json()["data"]["access_token"]

        resp = await client.post(
            "/auth/v1/refresh-token",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code in (400, 401, 422)

    async def test_refresh_token_missing_header(self, client, session):
        """缺少 Authorization 头返回 4xx"""
        resp = await client.post("/auth/v1/refresh-token")
        assert resp.status_code in (400, 422)

    async def test_refresh_token_invalid_token(self, client, session):
        """无效 token 返回 4xx"""
        resp = await client.post(
            "/auth/v1/refresh-token",
            headers={"Authorization": "Bearer this.is.invalid"},
        )
        assert resp.status_code in (400, 401, 422)

    async def test_refresh_token_wrong_scheme(self, client, session):
        """Authorization 非 Bearer 格式返回 4xx"""
        resp = await client.post(
            "/auth/v1/refresh-token",
            headers={"Authorization": "Basic sometoken"},
        )
        assert resp.status_code in (400, 422)


# ── 验证 Token ────────────────────────────────────────────────────────────


class TestVerifyTokenApi:
    async def test_verify_valid_access_token(self, client, registered_user):
        """合法 access token 验证返回 true"""
        login_resp = await client.post(
            "/user/v1/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        access_token = login_resp.json()["data"]["access_token"]

        resp = await client.post(
            "/auth/v1/verify",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] is True

    async def test_verify_invalid_token(self, client, session):
        """无效 token 返回 4xx"""
        resp = await client.post(
            "/auth/v1/verify",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code in (400, 401, 422)

    async def test_verify_missing_header(self, client, session):
        """缺少 Authorization 头返回 4xx"""
        resp = await client.post("/auth/v1/verify")
        assert resp.status_code in (400, 422)


# ── 小程序绑定登录 ─────────────────────────────────────────────────────────


FAKE_OPENID = "oABC123456789"
FAKE_PHONE = "13800138000"
FAKE_SESSION_KEY = "fake_session_key"

WECHAT_JSCODE2SESSION_PATH = "app.auth.adapter.input.api.v1.miniapp.wechat_jscode2session"
WECHAT_ACCESS_TOKEN_PATH = "app.auth.adapter.input.api.v1.miniapp.wechat_access_token"
WECHAT_GET_PHONE_PATH = "app.auth.adapter.input.api.v1.miniapp.wechat_get_user_phone_number"


def _mock_jscode2session(openid: str = FAKE_OPENID, unionid: str | None = None):
    return AsyncMock(
        return_value={
            "openid": openid,
            "session_key": FAKE_SESSION_KEY,
            "unionid": unionid,
        }
    )


def _mock_get_phone(phone: str = FAKE_PHONE):
    return AsyncMock(
        return_value={
            "phone_info": {"purePhoneNumber": phone}
        }
    )


class TestMiniappBindApi:
    async def test_bind_new_user_success(self, client, session):
        """全新用户首次绑定，自动创建账号并返回 token"""
        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session()):
            with patch(WECHAT_ACCESS_TOKEN_PATH, new=AsyncMock(return_value="fake_access_token")):
                with patch(WECHAT_GET_PHONE_PATH, new=_mock_get_phone()):
                    resp = await client.post(
                        "/auth/v1/miniapp/bind",
                        json={"login_code": "fake_code", "phone_code": "fake_phone_code"},
                    )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user_id"] is not None

    async def test_bind_existing_user_by_openid(self, client, session):
        """已绑定 openid 的用户再次调用，返回同一用户的 token"""
        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session()):
            with patch(WECHAT_ACCESS_TOKEN_PATH, new=AsyncMock(return_value="fake_access_token")):
                with patch(WECHAT_GET_PHONE_PATH, new=_mock_get_phone()):
                    resp1 = await client.post(
                        "/auth/v1/miniapp/bind",
                        json={"login_code": "fake_code", "phone_code": "fake_phone_code"},
                    )
        user_id_1 = resp1.json()["data"]["user_id"]

        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session()):
            with patch(WECHAT_ACCESS_TOKEN_PATH, new=AsyncMock(return_value="fake_access_token")):
                with patch(WECHAT_GET_PHONE_PATH, new=_mock_get_phone()):
                    resp2 = await client.post(
                        "/auth/v1/miniapp/bind",
                        json={"login_code": "fake_code", "phone_code": "fake_phone_code"},
                    )
        user_id_2 = resp2.json()["data"]["user_id"]

        assert resp2.status_code == 200
        assert user_id_1 == user_id_2

    async def test_bind_different_openid_same_phone_returns_409(self, client, session):
        """不同微信号绑定同一手机号 → 409 拒绝"""
        phone = "13900139001"
        first_openid = "oFIRST_PHONE_BIND"
        second_openid = "oSECOND_PHONE_BIND"

        # Step 1: 第一次 bind，创建账号并绑定手机号
        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session(openid=first_openid)):
            with patch(WECHAT_ACCESS_TOKEN_PATH, new=AsyncMock(return_value="fake_access_token")):
                with patch(WECHAT_GET_PHONE_PATH, new=_mock_get_phone(phone=phone)):
                    resp1 = await client.post(
                        "/auth/v1/miniapp/bind",
                        json={"login_code": "fake_code", "phone_code": "fake_phone_code"},
                    )
        assert resp1.status_code == 200

        # Step 2: 不同 openid 携相同手机号，应被拒绝
        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session(openid=second_openid)):
            with patch(WECHAT_ACCESS_TOKEN_PATH, new=AsyncMock(return_value="fake_access_token")):
                with patch(WECHAT_GET_PHONE_PATH, new=_mock_get_phone(phone=phone)):
                    resp2 = await client.post(
                        "/auth/v1/miniapp/bind",
                        json={"login_code": "fake_code", "phone_code": "fake_phone_code"},
                    )
        assert resp2.status_code == 409

    async def test_bind_missing_login_code(self, client, session):
        """缺少 login_code 返回 422"""
        resp = await client.post(
            "/auth/v1/miniapp/bind",
            json={"phone_code": "fake_phone_code"},
        )
        assert resp.status_code == 422

    async def test_bind_missing_phone_payload(self, client, session):
        """缺少 phone_code 且无 encrypted_data/iv 返回 422"""
        resp = await client.post(
            "/auth/v1/miniapp/bind",
            json={"login_code": "fake_code"},
        )
        assert resp.status_code == 422

    async def test_bind_wechat_api_failure(self, client, session):
        """微信接口返回异常，接口返回 4xx"""
        from core.helpers.wechat_miniapp import WechatMiniappApiError

        with patch(
            WECHAT_JSCODE2SESSION_PATH,
            new=AsyncMock(side_effect=WechatMiniappApiError("mock error")),
        ):
            resp = await client.post(
                "/auth/v1/miniapp/bind",
                json={"login_code": "bad_code", "phone_code": "fake_phone_code"},
            )
        assert resp.status_code in (400, 422)


# ── 小程序重新登录（relogin）─────────────────────────────────────────────


class TestMiniappReloginApi:
    async def _bind(self, client, openid: str = FAKE_OPENID):
        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session(openid=openid)):
            with patch(WECHAT_ACCESS_TOKEN_PATH, new=AsyncMock(return_value="fake_access_token")):
                with patch(WECHAT_GET_PHONE_PATH, new=_mock_get_phone()):
                    return await client.post(
                        "/auth/v1/miniapp/bind",
                        json={"login_code": "fake_code", "phone_code": "fake_phone_code"},
                    )

    async def test_relogin_success(self, client, session):
        """已绑定 openid 的用户 relogin，返回新 token"""
        bind_resp = await self._bind(client)
        assert bind_resp.status_code == 200

        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session()):
            resp = await client.post(
                "/auth/v1/miniapp/relogin",
                json={"login_code": "fake_code"},
            )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user_id"] == bind_resp.json()["data"]["user_id"]

    async def test_relogin_unbound_openid_returns_404(self, client, session):
        """未绑定的 openid relogin 返回 404"""
        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session(openid="oUNKNOWN_RELOGIN")):
            resp = await client.post(
                "/auth/v1/miniapp/relogin",
                json={"login_code": "fake_code"},
            )
        assert resp.status_code == 404

    async def test_relogin_missing_login_code(self, client, session):
        """缺少 login_code 返回 422"""
        resp = await client.post("/auth/v1/miniapp/relogin", json={})
        assert resp.status_code == 422

    async def test_relogin_wechat_api_failure(self, client, session):
        """微信接口失败返回 4xx"""
        from core.helpers.wechat_miniapp import WechatMiniappApiError

        with patch(
            WECHAT_JSCODE2SESSION_PATH,
            new=AsyncMock(side_effect=WechatMiniappApiError("mock error")),
        ):
            resp = await client.post(
                "/auth/v1/miniapp/relogin",
                json={"login_code": "bad_code"},
            )
        assert resp.status_code in (400, 422)


# ── 小程序自动登录（login）───────────────────────────────────────────────


class TestMiniappAutoLoginApi:
    async def _bind(self, client, openid: str = FAKE_OPENID):
        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session(openid=openid)):
            with patch(WECHAT_ACCESS_TOKEN_PATH, new=AsyncMock(return_value="fake_access_token")):
                with patch(WECHAT_GET_PHONE_PATH, new=_mock_get_phone()):
                    return await client.post(
                        "/auth/v1/miniapp/bind",
                        json={"login_code": "fake_code", "phone_code": "fake_phone_code"},
                    )

    async def test_auto_login_success(self, client, session):
        """未绑定用户也可直接 login，自动创建账号并返回 token"""
        with patch(WECHAT_JSCODE2SESSION_PATH, new=_mock_jscode2session()):
            resp = await client.post(
                "/auth/v1/miniapp/login",
                json={"login_code": "fake_code"},
            )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user_id"] is not None

    async def test_auto_login_reuses_existing_user_by_unionid(self, client, session):
        """同一 unionid 更换 openid 时，仍应复用同一用户"""
        first_openid = "oFIRST_LOGIN"
        second_openid = "oSECOND_LOGIN"
        unionid = "uSHARED_LOGIN"

        with patch(
            WECHAT_JSCODE2SESSION_PATH,
            new=_mock_jscode2session(openid=first_openid, unionid=unionid),
        ):
            first_resp = await client.post(
                "/auth/v1/miniapp/login",
                json={"login_code": "fake_code"},
            )
        assert first_resp.status_code == 200

        with patch(
            WECHAT_JSCODE2SESSION_PATH,
            new=_mock_jscode2session(openid=second_openid, unionid=unionid),
        ):
            second_resp = await client.post(
                "/auth/v1/miniapp/login",
                json={"login_code": "fake_code"},
            )
        assert second_resp.status_code == 200
        assert second_resp.json()["data"]["user_id"] == first_resp.json()["data"]["user_id"]

    async def test_auto_login_missing_login_code(self, client, session):
        """缺少 login_code 返回 422"""
        resp = await client.post("/auth/v1/miniapp/login", json={})
        assert resp.status_code == 422

    async def test_auto_login_wechat_api_failure(self, client, session):
        """微信接口失败返回 4xx"""
        from core.helpers.wechat_miniapp import WechatMiniappApiError

        with patch(
            WECHAT_JSCODE2SESSION_PATH,
            new=AsyncMock(side_effect=WechatMiniappApiError("mock error")),
        ):
            resp = await client.post(
                "/auth/v1/miniapp/login",
                json={"login_code": "bad_code"},
            )
        assert resp.status_code in (400, 422)
