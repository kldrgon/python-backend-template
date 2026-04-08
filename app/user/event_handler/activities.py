"""User Domain Activities"""

from temporalio import activity
from dependency_injector.wiring import inject, Provide

from pami_event_framework.autodiscovery import activity_of_handler
from pami_event_framework.temporal import with_session_context
from app.user.domain.event.user_events import (
    UserCreatedPayload,
    UserRolesAssignedPayload,
    UserRolesRevokedPayload,
)
import structlog

from core.config import config
from app.container import Container
from app.user.application.port.avatar_status_port import AvatarStatusPort

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# 与上传协议的事件过滤契约：上传方在发起请求时写入这两个字段，Blob 上下文原样透传至事件
_AVATAR_OWNER_TYPE = "user"
_AVATAR_EDGE_KEY = "avatar"

# Redis 状态 key 前缀，供测试直接读写 Redis 时使用
AVATAR_STATUS_KEY_PREFIX: str = config.user.avatar_status_key_prefix


@activity.defn
@activity_of_handler()
@inject
async def send_welcome_email_activity(
    event_data: dict,
    usecase = Provide[Container.user_container.user_command_service]
):
    """用户创建事件处理 - 发送欢迎邮件"""
    payload = UserCreatedPayload(**event_data)
    logger.info("sending_welcome_email", user_id=payload.user_id, email=payload.email)
    # TODO: 实际发送邮件逻辑


@activity.defn
@activity_of_handler()
@inject
async def on_user_roles_assigned_activity(
    event_data: dict,
    usecase = Provide[Container.user_container.user_command_service]
):
    """用户角色分配事件处理"""
    payload = UserRolesAssignedPayload(**event_data)
    logger.info("user_roles_assigned", user_id=payload.user_id, roles=payload.roles)


@activity.defn
@activity_of_handler()
@inject
async def on_user_roles_revoked_activity(
    event_data: dict,
    usecase = Provide[Container.user_container.user_command_service]
):
    """用户角色撤销事件处理"""
    payload = UserRolesRevokedPayload(**event_data)
    logger.info("user_roles_revoked", user_id=payload.user_id, roles=payload.roles)


@activity.defn
@activity_of_handler()
@with_session_context
@inject
async def on_user_blob_processing_completed_activity(
    event_data: dict,
    usecase=Provide[Container.user_container.user_command_service],
    avatar_status_port: AvatarStatusPort = Provide[Container.user_container.avatar_status_port],
):
    """Blob 处理完成事件 ACL — 头像绑定

    仅当 owner_type == "user" 且 edge_key == "avatar" 时，
    将 blob_id 绑定到用户头像并写入状态。
    """
    blob_id = event_data.get("blob_id")
    owner_id = event_data.get("owner_id")
    owner_type = event_data.get("owner_type")
    edge_key = event_data.get("edge_key")

    if owner_type != _AVATAR_OWNER_TYPE or edge_key != _AVATAR_EDGE_KEY:
        logger.debug(
            "blob_processing_completed_skipped",
            blob_id=blob_id,
            owner_type=owner_type,
            edge_key=edge_key,
        )
        return

    if not owner_id:
        logger.warning("blob_processing_completed_missing_owner_id", blob_id=blob_id)
        return

    from app.user.domain.command import SetAvatarCommand

    await usecase.set_avatar(
        command=SetAvatarCommand(user_id=owner_id, avatar=blob_id)
    )

    await avatar_status_port.set_approved(user_id=owner_id)

    logger.info(
        "user_avatar_set",
        user_id=owner_id,
        blob_id=blob_id,
    )
