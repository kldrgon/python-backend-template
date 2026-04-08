from app.auth.application.port.user_account_port import UserAccountPort, UserAuthInfoDTO
from app.user.domain.aggregate.user import User
from app.user.domain.entity.linked_account import LinkedAccount
from app.user.domain.factory.user_factory import UserFactory
from app.user.domain.repository.user import UserRepository


class UserAccountAdapter(UserAccountPort):
    """ACL：Auth 上下文对 User 上下文的防腐层适配器。"""

    def __init__(self, *, repository: UserRepository, user_factory: UserFactory):
        self._repo = repository
        self._factory = user_factory

    async def find_by_oauth(
        self, *, provider: str, external_uid: str
    ) -> UserAuthInfoDTO | None:
        user = await self._repo.get_user_by_linked_account(
            provider=provider, provider_account_id=external_uid
        )
        return self._to_dto(user) if user else None

    async def find_by_phone(self, *, phone: str) -> UserAuthInfoDTO | None:
        user = await self._repo.get_user_by_phone(phone=phone)
        return self._to_dto(user) if user else None

    async def find_by_unionid(
        self, *, provider: str, union_id: str
    ) -> UserAuthInfoDTO | None:
        user = await self._repo.get_user_by_wechat_unionid(
            provider=provider, union_id=union_id
        )
        return self._to_dto(user) if user else None

    async def get_oauth_binding_uid(
        self, *, user_id: str, provider: str
    ) -> str | None:
        user = await self._repo.get_user_by_id(user_id=user_id)
        if user is None:
            return None
        linked = next(
            (a for a in user.linked_accounts if a.provider == provider), None
        )
        return linked.provider_account_id if linked else None

    async def create_user(
        self, *, email: str, password: str, nickname: str, role: str
    ) -> UserAuthInfoDTO:
        user = self._factory.create_user(
            email=email, password=password, nickname=nickname, role=role
        )
        await self._repo.save(user=user)
        return self._to_dto(user)

    async def bind_phone_and_link_oauth(
        self,
        *,
        user_id: str,
        phone: str | None,
        provider: str,
        external_uid: str,
        union_id: str | None,
        meta: dict,
        link_oauth: bool = True,
    ) -> None:
        user = await self._repo.get_user_by_id(user_id=user_id)
        if phone:
            user.set_phone(phone=phone)
        if link_oauth:
            user.link_account(
                account=LinkedAccount(
                    provider=provider,
                    provider_account_id=external_uid,
                    raw_data={"union_id": union_id, **meta},
                )
            )
        await self._repo.save(user=user)

    @staticmethod
    def _to_dto(user: User) -> UserAuthInfoDTO:
        return UserAuthInfoDTO(
            user_id=user.user_id,
            nickname=user.nickname,
            email=user.email,
            avatar=user.avatar,
            roles=list(user.roles or []),
        )
