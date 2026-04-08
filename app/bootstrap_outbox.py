"""Outbox Publisher Bootstrap - 初始化 Outbox Beat 组件"""

import structlog

from pami_event_framework.config import EventFrameworkConfig
from pami_event_framework.kafka.producer import KafkaEventProducer
from pami_event_framework.tasks.outbox_publisher import OutboxPublisher

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def start_outbox_publisher(config: EventFrameworkConfig):
    """启动 Outbox Publisher
    
    Args:
        config: 框架配置
    """
    logger.info("Initializing Outbox Publisher components...")
    
    # 1. Kafka Producer
    kafka_producer = KafkaEventProducer(
        config=config.kafka,
    )
    await kafka_producer.start()
    logger.info("KafkaEventProducer initialized")
    
    # 2. Outbox Publisher
    publisher = OutboxPublisher(
        kafka_producer=kafka_producer,
        batch_size=config.outbox.batch_size,
        interval_seconds=config.outbox.interval_seconds,
    )
    
    logger.info("Outbox Publisher created")
    
    # 启动（阻塞）
    logger.info("Starting Outbox Publisher...")
    await publisher.start()
