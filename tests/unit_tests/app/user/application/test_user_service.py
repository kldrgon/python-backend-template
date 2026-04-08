"""UserCommandService 单元测试 - mock repository，@Transactional() 无 SessionManager 自动透传"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.user.application.service.user import UserCommandService
from app.user.application.exception import (
    PasswordConfirmNotMatchException,
    AgreementRequiredException,
    DuplicateEmailOrNicknameException,
    UserNotFoundException,
    PasswordDoesNotMatchException,
)
from app.user.domain.command import (
    CreateUserCommand,
    UserRolesAssignCommand,
    UpdateUserProfileCommand,
    SetAvatarCommand,
)
from app.user.domain.command.user import UserGetByIdCommand
from app.user.domain.aggregate.user import User
from app.user.domain.exception import DuplicateEmailOrNicknameError
from app.user.domain.factory.user_factory import UserFactory
from app.user.domain.vo.user_role import UserRole


# ── 辅助工厂 ─────────────────────────────────────────────────────────────

def _make_user_stub(
    user_id: str = "u1",
    email: str = "test@example.com",
    nickname: str = "testuser",
    is_admin: bool = False,
    password: str = "password123",
    role: str = "",
) -> User:
    user = User.create(
        user_id=user_id,
        email=email,
        password=password,
        nickname=nickname,
        role=role,
    )
    if is_admin:
        user.is_admin = True
    return user


def _make_service(
    *,
    repo_return: User | None = None,
    repo_list_return: list[User] | None = None,
    domain_service=None,
    factory_return: User | None = None,
) -> tuple[UserCommandService, MagicMock, MagicMock]:
    mock_repo = AsyncMock()
    mock_repo.get_user_by_id.return_value = repo_return
    mock_repo.get_user_by_email_or_nickname.return_value = repo_return
    mock_repo.get_users.return_value = repo_list_return or []
    mock_repo.save.return_value = None

    mock_factory = MagicMock(spec=UserFactory)
    if factory_return is not None:
        mock_factory.create_user.return_value = factory_return

    service = UserCommandService(
        repository=mock_repo,
        user_factory=mock_factory,
        user_domain_service=domain_service,
    )
    return service, mock_repo, mock_factory


# ── create_user() ────────────────────────────────────────────────────────


class TestCreateUser:
    def _make_cmd(
        self,
        *,
        password: str = "password123",
        confirm: str = "password123",
        agreed: bool = True,
    ) -> CreateUserCommand:
        return CreateUserCommand(
            email="new@example.com",
            nickname="newuser",
            password=password,
            confirmPassword=confirm,
            role=UserRole.STUDENT,
            agreed=agreed,
        )

    @pytest.mark.asyncio
    async def test_create_user_success_calls_factory_and_save(self):
        stub_user = _make_user_stub()
        service, mock_repo, mock_factory = _make_service(factory_return=stub_user)
        cmd = self._make_cmd()

        result = await service.create_user(command=cmd)

        mock_factory.create_user.assert_called_once_with(
            email="new@example.com",
            password="password123",
            nickname="newuser",
            role=UserRole.STUDENT,
        )
        mock_repo.save.assert_called_once_with(user=stub_user)
        assert result is stub_user

    @pytest.mark.asyncio
    async def test_create_user_password_mismatch_raises(self):
        service, _, _ = _make_service()
        cmd = self._make_cmd(password="password123", confirm="different")
        with pytest.raises(PasswordConfirmNotMatchException):
            await service.create_user(command=cmd)

    @pytest.mark.asyncio
    async def test_create_user_not_agreed_raises(self):
        service, _, _ = _make_service()
        cmd = self._make_cmd(agreed=False)
        with pytest.raises(AgreementRequiredException):
            await service.create_user(command=cmd)

    @pytest.mark.asyncio
    async def test_create_user_duplicate_raises(self):
        mock_domain_service = AsyncMock()
        mock_domain_service.ensure_user_can_be_created.side_effect = DuplicateEmailOrNicknameError(
            email="new@example.com", nickname="newuser"
        )
        service, _, _ = _make_service(domain_service=mock_domain_service)
        cmd = self._make_cmd()
        with pytest.raises(DuplicateEmailOrNicknameException):
            await service.create_user(command=cmd)

    @pytest.mark.asyncio
    async def test_create_user_without_domain_service_skips_duplicate_check(self):
        stub_user = _make_user_stub()
        service, mock_repo, mock_factory = _make_service(
            factory_return=stub_user, domain_service=None
        )
        cmd = self._make_cmd()
        result = await service.create_user(command=cmd)
        assert result is stub_user
        mock_repo.save.assert_called_once()


# ── assign_roles() ───────────────────────────────────────────────────────


class TestAssignRoles:
    @pytest.mark.asyncio
    async def test_assign_roles_success(self):
        stub_user = _make_user_stub()
        service, mock_repo, _ = _make_service(repo_return=stub_user)
        cmd = UserRolesAssignCommand(user_id="u1", roles=["TEACHER"])

        result = await service.assign_roles(command=cmd)

        assert result is True
        mock_repo.save.assert_called_once_with(user=stub_user)
        assert "TEACHER" in stub_user.roles

    @pytest.mark.asyncio
    async def test_assign_roles_user_not_found_raises(self):
        service, _, _ = _make_service(repo_return=None)
        cmd = UserRolesAssignCommand(user_id="nonexistent", roles=["TEACHER"])
        with pytest.raises(UserNotFoundException):
            await service.assign_roles(command=cmd)


# ── update_profile() ─────────────────────────────────────────────────────


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_profile_success(self):
        stub_user = _make_user_stub()
        service, mock_repo, _ = _make_service(repo_return=stub_user)
        cmd = UpdateUserProfileCommand(user_id="u1", nickname="updated", bio="hello")

        result = await service.update_profile(command=cmd)

        assert result is stub_user
        assert stub_user.nickname == "updated"
        assert stub_user.bio == "hello"
        mock_repo.save.assert_called_once_with(user=stub_user)

    @pytest.mark.asyncio
    async def test_update_profile_user_not_found_raises(self):
        service, _, _ = _make_service(repo_return=None)
        cmd = UpdateUserProfileCommand(user_id="nonexistent")
        with pytest.raises(UserNotFoundException):
            await service.update_profile(command=cmd)


# ── set_avatar() ─────────────────────────────────────────────────────────


class TestSetAvatar:
    @pytest.mark.asyncio
    async def test_set_avatar_success(self):
        stub_user = _make_user_stub()
        service, mock_repo, _ = _make_service(repo_return=stub_user)
        cmd = SetAvatarCommand(user_id="u1", avatar="blob-999")

        result = await service.set_avatar(command=cmd)

        assert result is stub_user
        assert stub_user.avatar == "blob-999"
        mock_repo.save.assert_called_once_with(user=stub_user)

    @pytest.mark.asyncio
    async def test_set_avatar_user_not_found_raises(self):
        service, _, _ = _make_service(repo_return=None)
        cmd = SetAvatarCommand(user_id="nonexistent", avatar="blob-1")
        with pytest.raises(UserNotFoundException):
            await service.set_avatar(command=cmd)


# ── is_admin() ───────────────────────────────────────────────────────────


class TestIsAdmin:
    @pytest.mark.asyncio
    async def test_is_admin_returns_true_for_admin(self):
        stub_user = _make_user_stub(is_admin=True)
        service, _, _ = _make_service(repo_return=stub_user)
        result = await service.is_admin(user_id="u1")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_returns_false_for_normal_user(self):
        stub_user = _make_user_stub(is_admin=False)
        service, _, _ = _make_service(repo_return=stub_user)
        result = await service.is_admin(user_id="u1")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_returns_false_when_user_not_found(self):
        service, _, _ = _make_service(repo_return=None)
        result = await service.is_admin(user_id="nonexistent")
        assert result is False


# ── login() ──────────────────────────────────────────────────────────────


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success_returns_dto_with_tokens(self):
        stub_user = _make_user_stub(password="password123")
        service, _, _ = _make_service(repo_return=stub_user)

        from core.helpers.password import hash_password
        stub_user.hashed_password = hash_password("password123")

        result = await service.login(email="test@example.com", password="password123")

        assert result.access_token
        assert result.refresh_token
        assert result.user_id == "u1"
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_login_user_not_found_raises(self):
        service, _, _ = _make_service(repo_return=None)
        with pytest.raises(UserNotFoundException):
            await service.login(email="notfound@example.com", password="password123")

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(self):
        from core.helpers.password import hash_password
        stub_user = _make_user_stub()
        stub_user.hashed_password = hash_password("correct_password")
        service, _, _ = _make_service(repo_return=stub_user)

        with pytest.raises(PasswordDoesNotMatchException):
            await service.login(email="test@example.com", password="wrong_password")


# ── get_by_user_id() ─────────────────────────────────────────────────────


class TestGetByUserId:
    @pytest.mark.asyncio
    async def test_get_by_user_id_success(self):
        stub_user = _make_user_stub()
        service, _, _ = _make_service(repo_return=stub_user)
        cmd = UserGetByIdCommand(user_id="u1")

        result = await service.get_by_user_id(command=cmd)

        assert result.user_id == "u1"
        assert result.email == "test@example.com"
        assert result.nickname == "testuser"

    @pytest.mark.asyncio
    async def test_get_by_user_id_not_found_raises(self):
        service, _, _ = _make_service(repo_return=None)
        cmd = UserGetByIdCommand(user_id="nonexistent")
        with pytest.raises(UserNotFoundException):
            await service.get_by_user_id(command=cmd)


# ── get_by_username() ────────────────────────────────────────────────────


class TestGetByUsername:
    @pytest.mark.asyncio
    async def test_get_by_username_success(self):
        stub_user = _make_user_stub()
        service, _, _ = _make_service(repo_return=stub_user)

        from app.user.domain.command.user import UserGetByUsernameCommand
        cmd = UserGetByUsernameCommand(username="testuser")

        result = await service.get_by_username(command=cmd)

        assert result.user_id == "u1"
        assert result.email == "test@example.com"
        assert result.nickname == "testuser"

    @pytest.mark.asyncio
    async def test_get_by_username_not_found_raises(self):
        service, _, _ = _make_service(repo_return=None)

        from app.user.domain.command.user import UserGetByUsernameCommand
        cmd = UserGetByUsernameCommand(username="ghost")
        with pytest.raises(UserNotFoundException):
            await service.get_by_username(command=cmd)


# ── get_user_list() ──────────────────────────────────────────────────────


class TestGetUserList:
    @pytest.mark.asyncio
    async def test_get_user_list_returns_dto_list(self):
        users = [
            _make_user_stub(user_id="u1", email="a@example.com", nickname="alice"),
            _make_user_stub(user_id="u2", email="b@example.com", nickname="bob"),
        ]
        service, _, _ = _make_service(repo_list_return=users)

        result = await service.get_user_list(limit=10)

        assert len(result) == 2
        assert result[0].user_id == "u1"
        assert result[1].user_id == "u2"

    @pytest.mark.asyncio
    async def test_get_user_list_empty_returns_empty_list(self):
        service, _, _ = _make_service(repo_list_return=[])

        result = await service.get_user_list(limit=10)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_list_passes_limit_and_prev(self):
        service, mock_repo, _ = _make_service(repo_list_return=[])

        await service.get_user_list(limit=5, prev=100)

        mock_repo.get_users.assert_called_once_with(limit=5, prev=100)
