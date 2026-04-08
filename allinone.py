"""All-in-One 启动脚本 - Worker + Outbox Publisher + Workflow Launcher + Outbox Beat"""

import asyncio
import structlog
import signal
from typing import Optional

from pami_event_framework.config import EventFrameworkConfig, LauncherConfig
from app.container import Container
from core.config import config, EVENT_HANDLER_PACKAGES
from pami_event_framework.kafka.config import KafkaConfig
from pami_event_framework.config import OutboxConfig, TemporalConfig
from pami_event_framework.autodiscovery import (
    autodiscover,
    get_activities_by_domain,
    get_all_task_queues,
    get_event_handler_map,
    get_signal_handler_map,
    get_workflows_by_queue,
)
from app.bootstrap_worker import start_temporal_workers
from app.bootstrap_launcher import start_workflow_launcher
from app.bootstrap_signal_launcher import start_signal_launcher
from app.bootstrap_outbox import start_outbox_publisher

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# 全局容器实例
_container: Optional[Container] = None


def filter_by_task_queues(task_queues: list[str]) -> dict:
    """根据 task queues 过滤 workflows 和 activities"""
    result = {}
    
    for task_queue in task_queues:
        # 从 queue 推断 domain: user-task-queue -> user
        domain = task_queue.replace('-task-queue', '')
        
        # 使用自动发现 API
        workflows = get_workflows_by_queue(task_queue)
        activities = get_activities_by_domain(domain)
        
        result[task_queue] = {
            "workflows": workflows,
            "activities": activities,
        }
    
    return result


async def main():
    """主函数"""
    global _container
    
    try:
        # 1. 初始化依赖注入容器
        logger.info("Initializing DI Container...")
        _container = Container()
        _container.init_resources()
        _container.wire(packages=["app"])
        logger.info("DI Container initialized")
        
        # 2. 自动发现 workflows 和 activities
        logger.info("Starting autodiscovery...")
        autodiscover(packages=EVENT_HANDLER_PACKAGES)
        logger.info("Autodiscovery complete")
        
        # 3. 从 core.config 构建框架配置
        framework_config = EventFrameworkConfig(
            database_url=config.db.writer_db_url,
            db_pool_size=10,
            db_max_overflow=20,
            kafka=KafkaConfig(
                bootstrap_servers=config.framework.kafka_bootstrap_servers,
                default_num_partitions=config.framework.kafka_default_partitions,
                env_prefix=config.framework.kafka_env_prefix or None,
            ),
            temporal=TemporalConfig(
                server_url=config.framework.temporal_host,
                namespace=config.framework.temporal_namespace,
                env_prefix=config.framework.temporal_env_prefix or config.framework.kafka_env_prefix or None,
            ),
            outbox=OutboxConfig(
                batch_size=config.framework.outbox_batch_size,
                interval_seconds=config.framework.outbox_publish_interval_seconds,
            ),
        )
        
        # 4. 为每个域创建独立的 launcher
        task_queues = get_all_task_queues()
        domains = [tq.replace('-task-queue', '') for tq in task_queues]

        launcher_tasks = []
        signal_launcher_tasks = []
        for domain_name in domains:
            domain_event_handler_map = get_event_handler_map(by_domain=domain_name)
            if domain_event_handler_map:
                domain_launcher_config = LauncherConfig(
                    consumer_group_id=f"workflow-launcher-{domain_name}",
                    enable_canary_group=config.framework.launcher_enable_canary_group,
                    canary_group_suffix=config.framework.launcher_canary_group_suffix,
                )

                logger.info(
                    "launcher_creating",
                    domain=domain_name,
                    events=list(domain_event_handler_map.keys()),
                )

                launcher_tasks.append(
                    start_workflow_launcher(framework_config, domain_launcher_config, domain_event_handler_map)
                )

            domain_signal_handler_map = get_signal_handler_map(by_domain=domain_name)
            if domain_signal_handler_map:
                domain_signal_launcher_config = LauncherConfig(
                    consumer_group_id=f"signal-launcher-{domain_name}",
                    enable_canary_group=config.framework.launcher_enable_canary_group,
                    canary_group_suffix=config.framework.launcher_canary_group_suffix,
                )

                logger.info(
                    "signal_launcher_creating",
                    domain=domain_name,
                    events=list(domain_signal_handler_map.keys()),
                )

                signal_launcher_tasks.append(
                    start_signal_launcher(
                        framework_config,
                        domain_signal_launcher_config,
                        domain_signal_handler_map,
                    )
                )

        # 5. 提取所有 task_queues 并过滤 workflows/activities
        worker_configs = filter_by_task_queues(task_queues)
        
        logger.info("workers_starting", task_queues=list(worker_configs.keys()))
        for tq, cfg in worker_configs.items():
            logger.info(
                "worker_config",
                task_queue=tq,
                workflow_count=len(cfg["workflows"]),
                activity_count=len(cfg["activities"]),
            )

        logger.info("components_starting")

        # 6. 启动所有组件（并发）
        await asyncio.gather(
            start_outbox_publisher(framework_config),
            *launcher_tasks,  # 多个域的 launcher
            *signal_launcher_tasks,
            start_temporal_workers(framework_config, worker_configs)
        )
        
    except asyncio.CancelledError:
        logger.info("allinone_cancelled")
        raise
    finally:
        # 清理资源
        if _container is not None:
            logger.info("di_container_shutting_down")
            try:
                _container.shutdown_resources()
                logger.info("di_container_shutdown_complete")
            except Exception as e:
                logger.error("di_container_shutdown_error", error=str(e), exc_info=True)


if __name__ == "__main__":
    # 日志已在 core.logger 初始化，无需 basicConfig
    
    # 创建事件循环（Windows 下更稳）
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    main_task = None

    def handle_shutdown(signum, frame):
        """处理关闭信号"""
        signame = signal.Signals(signum).name
        logger.info("shutdown_signal_received", signal=signame)
        if main_task and not main_task.done():
            main_task.cancel()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        main_task = loop.create_task(main())
        loop.run_until_complete(main_task)
        logger.info("allinone_shutdown_complete")
    except asyncio.CancelledError:
        logger.info("All-in-One shutdown by signal")
    except KeyboardInterrupt:
        logger.info("All-in-One interrupted by user")
    except Exception as e:
        logger.error(f"All-in-One process failed: {e}", exc_info=True)
        raise
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
            logger.info("Event loop closed")
