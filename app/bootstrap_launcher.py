"""Workflow Launcher Bootstrap - 初始化 Launcher 组件"""

import asyncio
import structlog
from typing import Dict, Any
from temporalio.client import Client as TemporalClient

from pami_event_framework.config import EventFrameworkConfig, LauncherConfig
from pami_event_framework.launcher.workflow_launcher import WorkflowLauncher

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def start_workflow_launcher(
    config: EventFrameworkConfig,
    launcher_config: LauncherConfig,
    event_handler_map: Dict[str, Dict[str, Any]]
):
    """启动 Workflow Launcher
    
    Args:
        config: 框架配置
        launcher_config: Launcher 专用配置
        event_handler_map: 事件处理映射，格式: {event_type: {"workflow_class": ..., "task_queue": ...}}
    """
    while True:
        try:
            logger.info("Connecting to Temporal...")

            # 连接 Temporal
            temporal_client = await TemporalClient.connect(
                config.temporal.server_url,
                namespace=config.temporal.namespace,
                tls=config.temporal.tls_config,
            )
            logger.info("Temporal Client connected")

            # 创建 Launcher
            logger.info("Creating Workflow Launcher...")
            launcher = WorkflowLauncher(
                kafka_config=config.kafka,
                temporal_client=temporal_client,
                event_handler_map=event_handler_map,
                consumer_group_id=launcher_config.consumer_group_id,
                temporal_config=config.temporal,  # 传入temporal配置用于租户隔离
            )

            logger.info("workflow_launcher_created", event_type_count=len(event_handler_map))

            # 启动 Launcher（阻塞）
            logger.info("Starting Workflow Launcher...")
            await launcher.start()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("workflow_launcher_runtime_error_retrying", error=str(e), exc_info=True)
            await asyncio.sleep(3)
