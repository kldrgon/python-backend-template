"""User Domain Workflows"""

from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
from pami_event_framework.autodiscovery import event_handler


@workflow.defn
@event_handler()
class OnUserCreatedWorkflow:
    """事件: USER_CREATED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "send_welcome_email_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )


@workflow.defn
@event_handler()
class OnUserRolesAssignedWorkflow:
    """事件: USER_ROLES_ASSIGNED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_user_roles_assigned_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )


@workflow.defn
@event_handler()
class OnUserRolesRevokedWorkflow:
    """事件: USER_ROLES_REVOKED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_user_roles_revoked_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )


@workflow.defn(name="UserOnBlobProcessingCompletedWorkflow")
@event_handler()
class OnBlobProcessingCompletedWorkflow:
    """事件: BLOB_PROCESSING_COMPLETED — 头像绑定 ACL"""

    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_user_blob_processing_completed_activity",
            args=[event_data.get("payload", event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
