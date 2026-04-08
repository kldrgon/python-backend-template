"""Outbox发布器"""

import asyncio
import json
import structlog

from ..persistence.session import session_factory
from ..persistence.outbox_repository import OutboxRepository
from ..kafka.producer import KafkaEventProducer

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class OutboxPublisher:
    """
    Outbox发布器（异步）

    后台任务，负责将Outbox中的待发布事件发送到Kafka。
    作为 fire-and-forget 快速路径的兜底，轮询间隔可设置较长（默认30s）。
    """

    def __init__(
        self,
        kafka_producer: KafkaEventProducer,
        batch_size: int = 100,
        interval_seconds: int = 30,
    ):
        self.kafka_producer = kafka_producer
        self.batch_size = batch_size
        self.interval_seconds = interval_seconds
        self._running = False

    async def start(self):
        """启动发布器（阻塞）"""
        self._running = True
        started = await self.kafka_producer.start()
        if not started:
            logger.warning("outbox_publisher_startup_degraded_kafka_unavailable")
        logger.info("Outbox发布器已启动")

        try:
            while self._running:
                try:
                    await self.publish_once()
                except Exception as e:
                    logger.error("outbox_publish_once_error", error=str(e), exc_info=True)

                await asyncio.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            logger.info("收到停止信号")
        finally:
            await self.stop()

    async def stop(self):
        """停止发布器"""
        self._running = False
        await self.kafka_producer.stop()
        logger.info("Outbox发布器已停止")

    async def publish_once(self) -> int:
        """
        发布一批待处理事件（可手动触发或由轮询调用）

        Returns:
            成功发布的事件数量
        """
        if not self.kafka_producer.is_started:
            await self.kafka_producer.start()

        async with session_factory() as session:
            outbox_repo = OutboxRepository(session)
            pending_events = await outbox_repo.get_pending_events(self.batch_size)

            if not pending_events:
                return 0

            success_count = 0
            fail_count = 0

            for outbox_event in pending_events:
                try:
                    event_data = (
                        json.loads(outbox_event.event_data)
                        if isinstance(outbox_event.event_data, str)
                        else outbox_event.event_data
                    )
                    success = await self.kafka_producer.publish_dict(
                        event_data=event_data,
                        topic=outbox_event.event_type,
                        key=outbox_event.aggregate_id,
                    )
                    if success:
                        await outbox_repo.mark_as_published(outbox_event.event_id)
                        success_count += 1
                    else:
                        await outbox_repo.increment_retry_count(outbox_event.event_id)
                        fail_count += 1
                    logger.warning("outbox_event_kafka_failed_retry", event_id=outbox_event.event_id)
                except Exception as e:
                    await outbox_repo.increment_retry_count(outbox_event.event_id)
                    fail_count += 1
                    logger.error(
                        "outbox_event_publish_error",
                        event_id=outbox_event.event_id,
                        error=str(e),
                        exc_info=True,
                    )

            await session.commit()

            if success_count or fail_count:
                logger.info("outbox_batch_done", success=success_count, failed=fail_count)

            return success_count
