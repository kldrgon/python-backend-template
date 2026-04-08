"""Temporal Worker Bootstrap - 初始化 Worker 组件"""

import asyncio
import structlog
from typing import Dict, List
from temporalio.client import Client as TemporalClient
from temporalio.worker import Worker as TemporalWorker

from pami_event_framework.config import EventFrameworkConfig
from pami_event_framework.persistence.session import close_session_manager

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def start_temporal_workers(
    config: EventFrameworkConfig,
    worker_configs: Dict[str, Dict[str, List]]
):
    """启动多个 Temporal Workers，每个 task_queue 一个

    Args:
        config: 框架配置
        worker_configs: {task_queue: {"workflows": [...], "activities": [...]}}
    """
    try:
        if not worker_configs:
            logger.warning("no_worker_configs_found")
            return

        while True:
            try:
                logger.info("Initializing Temporal Workers...")

                # 1. 连接 Temporal
                logger.info("Connecting to Temporal...")
                temporal_client = await TemporalClient.connect(
                    config.temporal.server_url,
                    namespace=config.temporal.namespace,
                    tls=config.temporal.tls_config,
                )
                logger.info("Temporal Client connected")

                # 2. 为每个 task_queue 创建 Worker
                workers = []
                for task_queue, cfg in worker_configs.items():
                    workflows = cfg["workflows"]
                    activities = cfg["activities"]

                    task_queue_with_prefix = config.temporal.add_env_prefix(task_queue)

                    logger.info(
                        "creating_worker",
                        task_queue=task_queue_with_prefix,
                        workflows=len(workflows),
                        activities=len(activities),
                    )

                    worker = TemporalWorker(
                        temporal_client,
                        task_queue=task_queue_with_prefix,
                        workflows=workflows,
                        activities=activities,
                    )
                    workers.append((task_queue_with_prefix, worker))

                # 3. 并发启动所有 Workers
                logger.info("starting_temporal_workers", count=len(workers))

                tasks = [
                    asyncio.create_task(worker.run(), name=f"worker-{task_queue}")
                    for task_queue, worker in workers
                ]

                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                logger.info("Workers cancelled, shutting down gracefully...")
                raise
            except Exception as e:
                logger.error("temporal_workers_runtime_error_retrying", error=str(e), exc_info=True)
                await asyncio.sleep(3)
    finally:
        logger.info("Closing session runtime...")
        try:
            await close_session_manager()
            logger.info("Session runtime closed")
        except Exception as e:
            logger.error("session_runtime_close_error", error=str(e), exc_info=True)

        logger.info("Worker cleanup complete")
