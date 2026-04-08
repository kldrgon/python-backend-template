from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Factory

from app.auth.adapter.output.user_account_adapter import UserAccountAdapter
from app.auth.application.service.jwt import JwtCommandService
from app.auth.application.service.miniapp_auth import MiniappAuthCommandService
from app.blob.container import BlobContainer
from app.user.container import UserContainer


class Container(DeclarativeContainer):
    """模板默认保留 user/auth/blob 三个基础域。此container作用是跨界限上下文提供依赖注入服务"""

    blob_container = providers.Container(BlobContainer)
    user_container = providers.Container(UserContainer)

    jwt_command_service = Factory[JwtCommandService](JwtCommandService)

    user_account_adapter = Factory(
        UserAccountAdapter,
        repository=user_container.user_sqlalchemy_repo,
        user_factory=user_container.user_factory,
    )

    miniapp_auth_command_service = Factory(
        MiniappAuthCommandService,
        user_account_port=user_account_adapter,
    )

    # 兼容部分依赖函数的旧访问方式。
    user_domain_service = user_container.user_domain_service
    user_command_service = user_container.user_command_service
