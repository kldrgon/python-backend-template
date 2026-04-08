from typing import Protocol

from .dto import UserListItemDTO, UserDetailDTO


class UserQueryService(Protocol):
    async def list_users(
        self,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[UserListItemDTO], int]:
        ...

    async def get_user(self, *, user_id: str) -> UserDetailDTO | None:
        ...


