"""Signal Launcher 启动脚本 - 独立运行"""

import argparse
import asyncio

import structlog

from app.bootstrap_signal_launcher import start_signal_launcher
from core.config import EVENT_HANDLER_PACKAGES, config
from pami_event_framework.autodiscovery import autodiscover, get_signal_handler_map
from pami_event_framework.config import EventFrameworkConfig, LauncherConfig, OutboxConfig, TemporalConfig
from pami_event_framework.kafka.config import KafkaConfig

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Signal Launcher 启动脚本")

    parser.add_argument(
        "--domains",
        type=str,
        default=None,
        help="指定域名称列表，逗号分隔，不指定则启动所有域",
    )

    parser.add_argument(
        "--consumer-group",
        type=str,
        default=None,
        help="指定消费者组 ID，不指定则根据 domain 自动生成或使用配置默认值",
    )

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()

    logger.info("Starting autodiscovery...")
    autodiscover(packages=EVENT_HANDLER_PACKAGES)
    logger.info("Autodiscovery complete")

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

    if args.consumer_group:
        consumer_group_id = args.consumer_group
    elif args.domains:
        consumer_group_id = f"signal-launcher-{args.domains}"
    else:
        consumer_group_id = f"{config.framework.launcher_consumer_group_id}-signal"

    launcher_config = LauncherConfig(
        consumer_group_id=consumer_group_id,
        enable_canary_group=config.framework.launcher_enable_canary_group,
        canary_group_suffix=config.framework.launcher_canary_group_suffix,
    )

    if args.domains:
        domains = [d.strip() for d in args.domains.split(",")]
        signal_handler_map = {}
        for domain in domains:
            domain_map = get_signal_handler_map(by_domain=domain)
            signal_handler_map.update(domain_map)
    else:
        signal_handler_map = get_signal_handler_map()

    if not signal_handler_map:
        logger.error("no_signal_handlers_found", domains=args.domains)
        return

    logger.info(
        "signal_launcher_config",
        domain_filter=args.domains or "all",
        consumer_group=consumer_group_id,
        event_handler_count=len(signal_handler_map),
        events=list(signal_handler_map.keys()),
    )

    await start_signal_launcher(
        config=base_config,
        launcher_config=launcher_config,
        signal_handler_map=signal_handler_map,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("signal_launcher_interrupted")
    except Exception as e:
        logger.error("signal_launcher_failed", error=str(e), exc_info=True)
        raise
