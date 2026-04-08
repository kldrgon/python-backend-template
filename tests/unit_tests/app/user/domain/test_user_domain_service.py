"""UserDomainService 单元测试"""

import pytest
from unittest.mock import AsyncMock

from app.user.domain.domain_service.user_domain_service import UserDomainService
from app.user.domain.exception import DuplicateEmailOrNicknameError
from app.user.domain.aggregate.user import User


def _make_user_stub(user_id: str = "u1") -> User:
    return User.create(
        user_id=user_id,
        email="exist@example.com",
        password="password123",
        nickname="existuser",
        role="",
    )


class TestUserDomainService:
    def _make_service(self, repo_return: User | None) -> UserDomainService:
        mock_repo = AsyncMock()
        mock_repo.get_user_by_email_or_nickname.return_value = repo_return
        return UserDomainService(user_repository=mock_repo)

    @pytest.mark.asyncio
    async def test_user_can_be_created_when_not_exists(self):
        service = self._make_service(repo_return=None)
        # 不应该抛出任何异常
        await service.ensure_user_can_be_created(email="new@example.com", nickname="newuser")

    @pytest.mark.asyncio
    async def test_raises_when_email_already_exists(self):
        service = self._make_service(repo_return=_make_user_stub())
        with pytest.raises(DuplicateEmailOrNicknameError):
            await service.ensure_user_can_be_created(
                email="exist@example.com", nickname="anotheruser"
            )

    @pytest.mark.asyncio
    async def test_raises_when_nickname_already_exists(self):
        service = self._make_service(repo_return=_make_user_stub())
        with pytest.raises(DuplicateEmailOrNicknameError):
            await service.ensure_user_can_be_created(
                email="another@example.com", nickname="existuser"
            )

    @pytest.mark.asyncio
    async def test_repository_called_with_correct_args(self):
        mock_repo = AsyncMock()
        mock_repo.get_user_by_email_or_nickname.return_value = None
        service = UserDomainService(user_repository=mock_repo)

        await service.ensure_user_can_be_created(email="foo@bar.com", nickname="foo")

        mock_repo.get_user_by_email_or_nickname.assert_called_once_with(
            email="foo@bar.com", nickname="foo"
        )
