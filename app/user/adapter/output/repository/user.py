from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.db.models.user import UserModel, UserLinkedAccountModel
from app.user.domain.aggregate.user import User
from app.user.adapter.output.mapper.user_mapper import orm_to_domain, domain_to_orm
from app.user.domain.repository.user import UserRepository
from pami_event_framework.persistence.base_aggregate_repository import BaseAggregateRepository
from core.db.session import session, session_factory
from core.exceptions import RepositoryIntegrityError


def _with_relations(stmt):
    return stmt.options(
        selectinload(UserModel.linked_accounts_rel),
        selectinload(UserModel.roles_rel),
    )


class SQLAlchemyUserRepository(BaseAggregateRepository, UserRepository):

    async def get_users(
        self,
        *,
        limit: int = 12,
        prev: int | None = None,
    ) -> list[User]:
        query = select(UserModel)
        if prev:
            query = query.where(UserModel.id < prev)
        if limit > 12:
            limit = 12
        query = query.order_by(UserModel.id.asc()).limit(limit)
        async with session_factory() as read_session:
            result = await read_session.execute(query)
        return [orm_to_domain(r) for r in result.scalars().all()]

    async def get_user_by_email_or_nickname(
        self,
        *,
        email: str | None = None,
        nickname: str | None = None,
    ) -> User | None:
        async with session_factory() as read_session:
            stmt = await read_session.execute(
                _with_relations(select(UserModel).where(or_(UserModel.email == email, UserModel.nickname == nickname))),
            )
            orm = stmt.scalars().first()
            return orm_to_domain(orm) if orm else None

    async def get_user_by_id(self, *, user_id: str) -> User | None:
        stmt = await session.execute(
            _with_relations(select(UserModel).where(UserModel.user_id == user_id))
        )
        orm = stmt.scalars().first()
        return orm_to_domain(orm) if orm else None

    async def get_user_by_phone(self, *, phone: str) -> User | None:
        async with session_factory() as read_session:
            stmt = await read_session.execute(
                _with_relations(select(UserModel).where(UserModel.phone == phone))
            )
            orm = stmt.scalars().first()
            return orm_to_domain(orm) if orm else None

    async def get_user_by_email(self, *, email: str) -> User | None:
        async with session_factory() as read_session:
            stmt = await read_session.execute(
                select(UserModel).where(UserModel.email == email)
            )
            orm = stmt.scalars().first()
            return orm_to_domain(orm) if orm else None

    async def get_user_by_linked_account(
        self,
        *,
        provider: str,
        provider_account_id: str,
    ) -> User | None:
        async with session_factory() as read_session:
            stmt = await read_session.execute(
                _with_relations(
                    select(UserModel)
                    .join(UserLinkedAccountModel, UserLinkedAccountModel.user_id == UserModel.user_id)
                    .where(UserLinkedAccountModel.provider == provider)
                    .where(UserLinkedAccountModel.provider_account_id == provider_account_id)
                )
            )
            orm = stmt.scalars().first()
            return orm_to_domain(orm) if orm else None

    async def get_user_by_wechat_unionid(
        self,
        *,
        provider: str,
        union_id: str,
    ) -> User | None:
        async with session_factory() as read_session:
            stmt = await read_session.execute(
                _with_relations(
                    select(UserModel)
                    .join(UserLinkedAccountModel, UserLinkedAccountModel.user_id == UserModel.user_id)
                    .where(UserLinkedAccountModel.provider == provider)
                )
            )
            for orm in stmt.scalars().all():
                for linked_account in orm.linked_accounts_rel:
                    raw_data = linked_account.raw_data or {}
                    if (
                        linked_account.provider == provider
                        and raw_data.get("union_id") == union_id
                    ):
                        return orm_to_domain(orm)
            return None

    async def save(self, *, user: User) -> None:
        orm = await session.scalar(
            _with_relations(select(UserModel).where(UserModel.user_id == user.user_id))
        )
        if orm is None:
            orm = domain_to_orm(user, target=None)
            session.add(orm)
        else:
            orm = domain_to_orm(user, target=orm)
        try:
            await session.flush()
        except IntegrityError as e:
            raise RepositoryIntegrityError() from e
        await self._flush_events(user, session=session)
