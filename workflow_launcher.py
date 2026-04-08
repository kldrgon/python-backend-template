"""Workflow Launcher 启动脚本 - 独立运行"""

import asyncio
import structlog
import argparse

from core.config import config, EVENT_HANDLER_PACKAGES
from pami_event_framework.config import EventFrameworkConfig, LauncherConfig, TemporalConfig, OutboxConfig
from pami_event_framework.kafka.config import KafkaConfig
from pami_event_framework.autodiscovery import autodiscover, get_event_handler_map
from app.bootstrap_launcher import start_workflow_launcher

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Workflow Launcher 启动脚本')
    
    parser.add_argument(
        '--domains',
        type=str,
        default=None,
        help='指定域名称列表，逗号分隔 (user,blob,activity,page)，不指定则启动所有域'
    )
    
    parser.add_argument(
        '--consumer-group',
        type=str,
        default=None,
        help='指定消费者组 ID，不指定则根据 domain 自动生成或使用配置默认值'
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()
    
    # 0. 自动发现 workflows
    logger.info("Starting autodiscovery...")
    autodiscover(packages=EVENT_HANDLER_PACKAGES)
    logger.info("Autodiscovery complete")
    
    # 1. 从 core.config 构建基础框架配置
    base_config = EventFrameworkConfig(
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

    # 2. 根据 args 构建 launcher 配置
    if args.consumer_group:
        consumer_group_id = args.consumer_group
    elif args.domains:
        consumer_group_id = f"workflow-launcher-{args.domains}"
    else:
        consumer_group_id = config.framework.launcher_consumer_group_id

    launcher_config = LauncherConfig(
        consumer_group_id=consumer_group_id,
        enable_canary_group=config.framework.launcher_enable_canary_group,
        canary_group_suffix=config.framework.launcher_canary_group_suffix,
    )
    
    # 3. 过滤 handlers (使用自动发现 API)
    if args.domains:
        # 支持多域: user,blob
        domains = [d.strip() for d in args.domains.split(',')]
        event_handler_map = {}
        for domain in domains:
            domain_map = get_event_handler_map(by_domain=domain)
            event_handler_map.update(domain_map)
    else:
        # 所有域
        event_handler_map = get_event_handler_map()
    
    if not event_handler_map:
        logger.error("no_handlers_found", domains=args.domains)
        return
    
    logger.info(
        "launcher_config",
        domain_filter=args.domains or "all",
        consumer_group=consumer_group_id,
        event_handler_count=len(event_handler_map),
        events=list(event_handler_map.keys())
    )
    
    # 4. 启动 Workflow Launcher
    await start_workflow_launcher(
        config=base_config,
        launcher_config=launcher_config,
        event_handler_map=event_handler_map
    )


if __name__ == "__main__":
    # 日志已在 core.logger 初始化，无需 basicConfig
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("workflow_launcher_interrupted")
    except Exception as e:
        logger.error("workflow_launcher_failed", error=str(e), exc_info=True)
        raise
