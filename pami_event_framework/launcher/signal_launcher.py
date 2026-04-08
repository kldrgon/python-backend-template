"""SignalLauncher - 监听 Kafka 事件并发送 Temporal Signal"""

import asyncio
from typing import Any, Dict

import structlog
from temporalio.client import Client as TemporalClient

from ..config import TemporalConfig
from ..kafka.config import KafkaConfig
from ..kafka.consumer import KafkaEventConsumer

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class SignalLauncher:
    """
    SignalLauncher - 轻量桥接层（异步）

    职责：
    1. 监听 Kafka 事件
    2. 根据映射定位已存在的 Workflow
    3. 发送对应的 Signal
    """

    def __init__(
        self,
        kafka_config: KafkaConfig,
        temporal_client: TemporalClient,
        signal_handler_map: Dict[str, Dict[str, Any]],
        consumer_group_id: str = "signal-launcher",
        temporal_config: TemporalConfig = None,
    ):
        self.kafka_config = kafka_config
        self.temporal_client = temporal_client
        self.signal_handler_map = signal_handler_map
        self.consumer_group_id = consumer_group_id
        self.temporal_config = temporal_config or TemporalConfig()

        self.subscribed_events = list(signal_handler_map.keys())

        logger.info("signal_launcher_init", event_count=len(self.subscribed_events))

    async def _handle_event(self, event_data: Dict[str, Any]):
        """处理单个事件并发送 signal"""
        event_type = event_data.get("event_type")
        event_id = event_data.get("event_id")

        if not event_type:
            logger.warning("signal_event_missing_event_type", event_data=event_data)
            return

        if not event_id:
            logger.warning("signal_event_missing_event_id", event_data=event_data)
            return

        handler_config = self.signal_handler_map.get(event_type)
        if not handler_config:
            logger.debug("signal_event_no_handler", event_type=event_type)
            return

        logger.info("signal_event_handling", event_type=event_type, event_id=event_id)

        if isinstance(handler_config, list):
            tasks = [self._signal_workflow(event_data, cfg) for cfg in handler_config]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(
                        "workflow_parallel_signal_failed",
                        event_type=event_type,
                        event_id=event_id,
                        error=str(result),
                        exc_info=result,
                    )
        else:
            try:
                await self._signal_workflow(event_data, handler_config)
            except Exception as e:
                logger.error(
                    "workflow_signal_failed",
                    event_type=event_type,
                    event_id=event_id,
                    error=str(e),
                    exc_info=True,
                )
                raise

    async def _signal_workflow(self, event_data: Dict[str, Any], handler_config: Dict[str, Any]):
        """向目标 workflow 发送 signal"""
        workflow_class = handler_config["workflow_class"]
        signal_name = handler_config["signal_name"]
        workflow_id_resolver = handler_config["workflow_id_resolver"]
        payload_resolver = handler_config["payload_resolver"]

        workflow_id = workflow_id_resolver(event_data)
        if not workflow_id:
            raise ValueError("signal handler returned empty workflow_id")

        signal_payload = payload_resolver(event_data)
        workflow_id = self.temporal_config.add_env_prefix(workflow_id)
        workflow_handle = self.temporal_client.get_workflow_handle(workflow_id=workflow_id)

        await workflow_handle.signal(signal_name, signal_payload)

        logger.info(
            "workflow_signaled",
            workflow_class=workflow_class.__name__,
            workflow_id=workflow_id,
            signal_name=signal_name,
            event_type=event_data["event_type"],
            event_id=event_data["event_id"],
        )

    async def start(self):
        """启动 SignalLauncher（阻塞）"""
        if not self.subscribed_events:
            logger.warning("没有需要订阅的 signal 事件，SignalLauncher 不启动")
            return

        logger.info(
            "signal_launcher_starting",
            group_id=self.consumer_group_id,
            events=self.subscribed_events,
        )

        consumer = KafkaEventConsumer(
            config=self.kafka_config,
            group_id=self.consumer_group_id,
            topics=self.subscribed_events,
        )

        await consumer.consume(handler=self._handle_event)
