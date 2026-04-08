"""Web Server Bootstrap - 初始化 Web 相关组件"""

import structlog
from typing import Optional

from pami_event_framework.config import EventFrameworkConfig, TemporalConfig, OutboxConfig, LauncherConfig
from pami_event_framework.kafka.config import KafkaConfig
from pami_event_framework.kafka.producer import KafkaEventProducer
from pami_event_framework.persistence.session import get_session, close_session_manager
from pami_event_framework.persistence.transactional import set_event_publisher
from pami_event_framework.tasks.outbox_publisher import OutboxPublisher

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def create_framework_config_from_app_config() -> EventFrameworkConfig:
    """从 core.config 创建 EventFrameworkConfig"""
    from core.config import config as app_config

    return EventFrameworkConfig(
        database_url=app_config.db.writer_db_url,
        db_pool_size=10,
        db_max_overflow=20,
        kafka=KafkaConfig(
            bootstrap_servers=app_config.framework.kafka_bootstrap_servers,
            default_num_partitions=app_config.framework.kafka_default_partitions,
            env_prefix=app_config.framework.kafka_env_prefix or None,
        ),
        temporal=TemporalConfig(
            server_url=app_config.framework.temporal_host,
            namespace=app_config.framework.temporal_namespace,
            env_prefix=app_config.framework.temporal_env_prefix or app_config.framework.kafka_env_prefix or None,
        ),
        outbox=OutboxConfig(
            batch_size=app_config.framework.outbox_batch_size,
            interval_seconds=app_config.framework.outbox_publish_interval_seconds,
        ),
        launcher=LauncherConfig(
            consumer_group_id=app_config.framework.launcher_consumer_group_id,
            enable_canary_group=app_config.framework.launcher_enable_canary_group,
            canary_group_suffix=app_config.framework.launcher_canary_group_suffix,
        ),
    )


class WebBootstrap:
    """Web Server 启动器"""

    def __init__(self, config: Optional[EventFrameworkConfig] = None):
        if config is None:
            config = create_framework_config_from_app_config()

        self.config = config
        self._initialized = False
        self._kafka_producer: Optional[KafkaEventProducer] = None
        self._outbox_publisher: Optional[OutboxPublisher] = None

    async def initialize(self):
        """初始化 Web 所需组件"""
        if self._initialized:
            logger.warning("WebBootstrap already initialized")
            return

        logger.info("Initializing Web components...")

        # 1. 预热 Session（使用统一懒加载实例）
        _ = get_session()
        logger.info("Session initialized")

        # 2. Kafka Producer + OutboxPublisher（用于事务提交后 fire-and-forget 发布）
        self._kafka_producer = KafkaEventProducer(config=self.config.kafka)
        producer_started = await self._kafka_producer.start()
        if not producer_started:
            logger.warning("Kafka unavailable at startup, web service continues in degraded mode")
        self._outbox_publisher = OutboxPublisher(
            kafka_producer=self._kafka_producer,
            batch_size=self.config.outbox.batch_size,
            interval_seconds=self.config.outbox.interval_seconds,
        )
        set_event_publisher(self._outbox_publisher)
        logger.info("OutboxPublisher registered for post-commit publish")

        self._initialized = True
        logger.info("Web components initialized successfully")

    async def shutdown(self):
        """关闭组件"""
        logger.info("Shutting down Web components...")

        set_event_publisher(None)
        if self._kafka_producer:
            await self._kafka_producer.stop()

        await close_session_manager()

        self._initialized = False
        logger.info("Web components shut down successfully")

# 全局实例
_web_bootstrap: Optional[WebBootstrap] = None


async def get_web_bootstrap(config: Optional[EventFrameworkConfig] = None) -> WebBootstrap:
    """获取全局 WebBootstrap 实例"""
    global _web_bootstrap

    if _web_bootstrap is None:
        _web_bootstrap = WebBootstrap(config)
        await _web_bootstrap.initialize()

    return _web_bootstrap


async def shutdown_web_bootstrap():
    """关闭全局 WebBootstrap 实例"""
    global _web_bootstrap

    if _web_bootstrap:
        await _web_bootstrap.shutdown()
        _web_bootstrap = None
