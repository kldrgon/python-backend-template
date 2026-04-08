"""Outbox Beat 启动脚本

职责：
- 定时扫描 Outbox 表中的 PENDING 事件
- 批量发布到 Kafka
- 兜底机制，确保事件不丢失

使用：
    python outbox_beat.py
"""

import asyncio
import structlog

from core.config import config
from pami_event_framework.config import EventFrameworkConfig, OutboxConfig, TemporalConfig
from pami_event_framework.kafka.config import KafkaConfig
from app.bootstrap_outbox import start_outbox_publisher

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def main():
    """主函数"""
    logger.info("outbox_beat_starting")
    
    # 1. 从 core.config 构建框架配置（正确处理 .env 中的引号）
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
    
    logger.info(
        "outbox_beat_config",
        batch_size=framework_config.outbox.batch_size,
        interval_seconds=framework_config.outbox.interval_seconds
    )
    
    # 2. 启动 Outbox Publisher
    await start_outbox_publisher(framework_config)


if __name__ == "__main__":
    # 日志已在 core.logger 初始化，无需 basicConfig
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("outbox_beat_interrupted")
    except Exception as e:
        logger.error("outbox_beat_failed", error=str(e), exc_info=True)
        raise
