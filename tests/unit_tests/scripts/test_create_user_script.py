import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.user.domain.aggregate.user import User
from app.user.domain.vo.user_role import UserRole
from scripts.create_user import (
    DEFAULT_OAUTH_PROVIDER,
    UserCreationInput,
    attach_optional_bindings,
    collect_user_input,
    create_user_from_input,
    main_async,
    normalize_role,
)


@pytest.fixture(autouse=True)
def _bypass_transactional():
    with patch(
        "pami_event_framework.persistence.session.get_session",
        side_effect=LookupError("no session in unit test"),
    ):
        yield


def _make_args(**overrides) -> argparse.Namespace:
    data = {
        "email": "demo@example.com",
        "nickname": "demo",
        "password": "password123",
        "password_confirm": None,
        "role": "student",
        "phone": None,
        "openid": None,
        "unionid": None,
        "provider": None,
        "interactive": False,
        "no_input": True,
        "agreed": True,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


def _make_user(
    *,
    user_id: str = "u1",
    email: str = "demo@example.com",
    nickname: str = "demo",
    password: str = "password123",
    role: str = "student",
) -> User:
    return User.create(
        user_id=user_id,
        email=email,
        password=password,
        nickname=nickname,
        role=role,
    )


class TestNormalizeRole:
    def test_accepts_uppercase_input(self):
        assert normalize_role("TEACHER") == UserRole.TEACHER

    def test_rejects_invalid_value(self):
        with pytest.raises(ValueError, match="teacher 或 student"):
            normalize_role("admin")


class TestCollectUserInput:
    def test_uses_cli_values_without_prompt(self):
        payload = collect_user_input(_make_args())
        assert payload == UserCreationInput(
            email="demo@example.com",
            nickname="demo",
            password="password123",
            role=UserRole.STUDENT,
            phone=None,
            openid=None,
            unionid=None,
            provider=None,
            agreed=True,
        )

    def test_prompts_for_missing_required_and_optional_values(self):
        args = _make_args(
            email=None,
            nickname=None,
            password=None,
            role=None,
            interactive=True,
            no_input=False,
        )
        input_values = iter(
            [
                "teacher@example.com",
                "teacher01",
                "teacher",
                "13800138000",
                "openid-123",
                "unionid-123",
            ]
        )
        password_values = iter(["secret123", "secret123"])

        payload = collect_user_input(
            args,
            input_fn=lambda _: next(input_values),
            password_fn=lambda _: next(password_values),
        )

        assert payload.email == "teacher@example.com"
        assert payload.nickname == "teacher01"
        assert payload.password == "secret123"
        assert payload.role == UserRole.TEACHER
        assert payload.phone == "13800138000"
        assert payload.openid == "openid-123"
        assert payload.unionid == "unionid-123"
        assert payload.provider == DEFAULT_OAUTH_PROVIDER

    def test_rejects_unionid_without_openid(self):
        with pytest.raises(ValueError, match="unionid"):
            collect_user_input(
                _make_args(openid=None, unionid="union-only", no_input=True)
            )

    def test_rejects_provider_without_openid(self):
        with pytest.raises(ValueError, match="provider"):
            collect_user_input(
                _make_args(openid=None, provider="wechat_miniapp", no_input=True)
            )


class TestAttachOptionalBindings:
    @pytest.mark.asyncio
    async def test_updates_phone_and_openid_then_saves(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_user_by_phone.return_value = None
        repo.get_user_by_linked_account.return_value = None
        repo.get_user_by_id.return_value = user

        await attach_optional_bindings(
            repository=repo,
            user_id="u1",
            phone="13800138000",
            openid="openid-123",
            unionid="unionid-123",
            provider=DEFAULT_OAUTH_PROVIDER,
        )

        assert user.phone == "13800138000"
        assert len(user.linked_accounts) == 1
        assert user.linked_accounts[0].provider == DEFAULT_OAUTH_PROVIDER
        assert user.linked_accounts[0].provider_account_id == "openid-123"
        assert user.linked_accounts[0].raw_data == {"union_id": "unionid-123"}
        repo.save.assert_called_once_with(user=user)

    @pytest.mark.asyncio
    async def test_raises_when_phone_is_occupied_by_other_user(self):
        owner = _make_user(user_id="u2", email="owner@example.com", nickname="owner")
        repo = AsyncMock()
        repo.get_user_by_phone.return_value = owner

        with pytest.raises(ValueError, match="手机号"):
            await attach_optional_bindings(
                repository=repo,
                user_id="u1",
                phone="13800138000",
                openid=None,
                unionid=None,
                provider=DEFAULT_OAUTH_PROVIDER,
            )


class TestCreateUserFromInput:
    @pytest.mark.asyncio
    async def test_calls_usecase_and_optional_binding(self):
        created_user = _make_user()
        usecase = AsyncMock()
        usecase.create_user.return_value = created_user
        repository = AsyncMock()
        payload = UserCreationInput(
            email="demo@example.com",
            nickname="demo",
            password="password123",
            role=UserRole.STUDENT,
            phone="13800138000",
            openid="openid-123",
        )

        with patch("scripts.create_user.attach_optional_bindings", new=AsyncMock()) as bind_mock:
            result = await create_user_from_input(
                user_usecase=usecase,
                user_repository=repository,
                payload=payload,
            )

        assert result is created_user
        usecase.create_user.assert_called_once()
        command = usecase.create_user.call_args.kwargs["command"]
        assert command.email == "demo@example.com"
        assert command.nickname == "demo"
        assert command.password == "password123"
        assert command.confirmPassword == "password123"
        assert command.role == UserRole.STUDENT
        bind_mock.assert_awaited_once_with(
            repository=repository,
            user_id="u1",
            phone="13800138000",
            openid="openid-123",
            unionid=None,
            provider=DEFAULT_OAUTH_PROVIDER,
        )


class TestMainAsyncContext:
    @pytest.mark.asyncio
    async def test_main_async_sets_and_resets_session_context(self):
        fake_user = _make_user()
        fake_container = MagicMock()
        fake_container.user_container.user_command_service.return_value = AsyncMock()
        fake_container.user_container.user_sqlalchemy_repo.return_value = AsyncMock()

        with patch("scripts.create_user.parse_args", return_value=_make_args()), \
            patch("scripts.create_user.collect_user_input", return_value=UserCreationInput(
                email="demo@example.com",
                nickname="demo",
                password="password123",
                role=UserRole.STUDENT,
            )), \
            patch("app.bootstrap_web.get_web_bootstrap", new=AsyncMock()), \
            patch("app.bootstrap_web.shutdown_web_bootstrap", new=AsyncMock()), \
            patch("app.container.Container", return_value=fake_container), \
            patch("scripts.create_user.create_user_from_input", new=AsyncMock(return_value=fake_user)), \
            patch("pami_event_framework.persistence.set_session_context", return_value="token-1") as set_ctx, \
            patch("pami_event_framework.persistence.reset_session_context") as reset_ctx:
            code = await main_async([])

        assert code == 0
        set_ctx.assert_called_once()
        reset_ctx.assert_called_once_with("token-1")
