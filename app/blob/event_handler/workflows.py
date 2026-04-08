"""Blob Domain Workflows"""

from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
from pami_event_framework.autodiscovery import event_handler


@workflow.defn
@event_handler()
class OnBlobCreatedWorkflow:
    """事件: BLOB_CREATED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_blob_created_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )


@workflow.defn
@event_handler()
class OnBlobProcessingStartedWorkflow:
    """事件: BLOB_PROCESSING_STARTED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_blob_processing_started_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )


@workflow.defn
@event_handler()
class OnBlobProcessingCompletedWorkflow:
    """事件: BLOB_PROCESSING_COMPLETED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_blob_processing_completed_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )


@workflow.defn
@event_handler()
class OnBlobProcessingFailedWorkflow:
    """事件: BLOB_PROCESSING_FAILED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_blob_processing_failed_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )


@workflow.defn
@event_handler()
class OnBlobDeletedWorkflow:
    """事件: BLOB_DELETED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_blob_deleted_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )


@workflow.defn
@event_handler()
class OnBlobGcRequestedWorkflow:
    """事件: BLOB_GC_REQUESTED"""
    
    @workflow.run
    async def run(self, event_data: dict):
        await workflow.execute_activity(
            "on_blob_gc_requested_activity",
            args=[event_data.get('payload', event_data)],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=0)  # 0 = 无限重试
        )
