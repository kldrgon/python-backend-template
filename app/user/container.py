from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Factory, Singleton

from app.user.adapter.output.repository.user import SQLAlchemyUserRepository
from app.user.application.service.user import UserCommandService
from app.user.adapter.output.domain_service.user_domain_service import SQLAlchemyUserDomainService
from app.user.domain.factory.user_factory import UserFactory
from app.user.adapter.output.query.user_query_service import SQLAlchemyUserQueryService
from app.user.adapter.output.cache.avatar_status_adapter import RedisAvatarStatusAdapter


class UserContainer(DeclarativeContainer):
    wiring_config = WiringConfiguration(modules=["app"])

    # 仓储
    user_sqlalchemy_repo = Singleton(SQLAlchemyUserRepository)

    # 领域服务
    user_domain_service = Factory(
        SQLAlchemyUserDomainService,
        user_repository=user_sqlalchemy_repo
    )

    # 工厂
    user_factory = Factory(UserFactory)

    # 缓存适配器
    avatar_status_port = Singleton(RedisAvatarStatusAdapter)

    # 应用服务
    user_command_service = Factory(
        UserCommandService,
        repository=user_sqlalchemy_repo,
        user_factory=user_factory,
        user_domain_service=user_domain_service,
        avatar_status_port=avatar_status_port,
    )

    # 查询服务
    user_query_service = Factory(SQLAlchemyUserQueryService)
