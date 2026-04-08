from app.user.domain.repository.user import UserRepository
from app.user.domain.exception import DuplicateEmailOrNicknameError


class UserDomainService:
    def __init__(self, *, user_repository: UserRepository):
        self.user_repository = user_repository

    async def ensure_user_can_be_created(self, *, email: str, nickname: str) -> None:
        existed = await self.user_repository.get_user_by_email_or_nickname(
            email=email, nickname=nickname
        )
        if existed:
            raise DuplicateEmailOrNicknameError(email=email, nickname=nickname)


