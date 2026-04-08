from sqlalchemy import select, func

from core.db.models import UserModel
from core.db.session import session_factory
from app.user.query.dto import UserListItemDTO, UserDetailDTO
from app.user.query.service import UserQueryService


class SQLAlchemyUserQueryService(UserQueryService):
    async def list_users(
        self,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[UserListItemDTO], int]:
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
        if offset < 0:
            offset = 0

        stmt = select(UserModel).order_by(UserModel.id.asc()).limit(limit).offset(offset)
        count_stmt = select(func.count(UserModel.id))

        async with session_factory() as s:
            rows = (await s.execute(stmt)).scalars().all()
            total = (await s.execute(count_stmt)).scalar_one()

        items = [UserListItemDTO(user_id=r.user_id, email=r.email, nickname=r.nickname) for r in rows]
        return items, int(total or 0)

    async def get_user(self, *, user_id: str) -> UserDetailDTO | None:
        async with session_factory() as s:
            row = (await s.execute(select(UserModel).where(UserModel.user_id == user_id))).scalars().first()
        if not row:
            return None
        roles = sorted([rel.role for rel in getattr(row, "roles_rel", [])])
        return UserDetailDTO(
            user_id=row.user_id,
            email=row.email,
            nickname=row.nickname,
            roles=roles,
            is_admin=row.is_admin,
        )
