"""Temporal Worker 启动脚本"""

import argparse
import asyncio
import structlog
import signal

from core.config import config, EVENT_HANDLER_PACKAGES
from pami_event_framework.config import EventFrameworkConfig, OutboxConfig, TemporalConfig, LauncherConfig
from pami_event_framework.kafka.config import KafkaConfig
from app.container import Container
from pami_event_framework.autodiscovery import autodiscover, get_workflows_by_queue, get_activities_by_domain, get_all_task_queues
from app.bootstrap_worker import start_temporal_workers

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Temporal Worker 启动脚本')
    
    parser.add_argument(
        '--task-queues',
        type=str,
        default=None,
        help='Task Queue 列表，逗号分隔 (默认: 启动所有 task queues，可指定 "all" 启动单个全能 worker)'
    )
    
    return parser.parse_args()


def filter_by_task_queues(task_queues: list[str]) -> dict:
    """根据 task queues 过滤 workflows 和 activities
    
    Args:
        task_queues: task queue 列表，可包含特殊值 "all"
        
    Returns:
        dict: {task_queue: {"workflows": [...], "activities": [...]}}
    """
    result = {}
    
    for task_queue in task_queues:
        # 特殊处理 "all" - 启动一个全能 worker
        if task_queue == "all":
            from pami_event_framework.autodiscovery import get_workflow_mappings, get_all_activities
            all_workflows = []
            for wf_list in get_workflow_mappings().values():
                if isinstance(wf_list, list):
                    all_workflows.extend([wf for wf, _ in wf_list])
                else:
                    all_workflows.append(wf_list[0])
            
            result["all-task-queue"] = {
                "workflows": all_workflows,
                "activities": get_all_activities(),
            }
            continue
        
        workflows = get_workflows_by_queue(task_queue)
        
        if task_queue == "default-event-handler-queue":
            from pami_event_framework.autodiscovery import get_all_activities
            activities = get_all_activities()
        else:
            domain = task_queue.replace('-task-queue', '')
            activities = get_activities_by_domain(domain)
        
        result[task_queue] = {
            "workflows": workflows,
            "activities": activities,
        }
    
    return result


async def main():
    """主函数"""
    args = parse_args()
    container = None
    
    try:
        # 1. 初始化依赖注入容器
        logger.info("Initializing DI Container...")
        container = Container()
        container.init_resources()
        container.wire(packages=["app"])
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
        
        # 4. 解析 task_queues
        if args.task_queues:
            task_queues = [q.strip() for q in args.task_queues.split(',')]
        else:
            # 默认启动所有独立的 task queues
            task_queues = get_all_task_queues()
        
        # 5. 按 task_queue 过滤 workflows 和 activities
        worker_configs = filter_by_task_queues(task_queues)
            
        logger.info(f"Starting workers for task queues: {list(worker_configs.keys())}")
        for tq, cfg in worker_configs.items():
            logger.info(f"  - {tq}: {len(cfg['workflows'])} workflows, {len(cfg['activities'])} activities")
        
        # 6. 启动 Temporal Workers（每个 task_queue 一个 worker）
        await start_temporal_workers(
            config=framework_config,
            worker_configs=worker_configs
        )
    finally:
        # 清理资源
        if container is not None:
            logger.info("Shutting down DI Container...")
            try:
                container.shutdown_resources()
                logger.info("DI Container shutdown complete")
            except Exception as e:
                logger.error(f"Error during container shutdown: {e}", exc_info=True)


if __name__ == "__main__":
    # 日志已在 core.logger 初始化，无需 basicConfig
    
    # 创建事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 主任务
    main_task = None
    
    def handle_shutdown(signum, frame):
        """处理关闭信号"""
        signame = signal.Signals(signum).name
        logger.info(f"Received {signame}, initiating graceful shutdown...")
        if main_task and not main_task.done():
            main_task.cancel()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        main_task = loop.create_task(main())
        loop.run_until_complete(main_task)
        logger.info("Worker shutdown complete")
    except asyncio.CancelledError:
        logger.info("Worker shutdown by signal")
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        raise
    finally:
        # 清理事件循环
        try:
            # 取消所有剩余任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # 等待所有任务完成取消
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            loop.close()
            logger.info("Event loop closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
