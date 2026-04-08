"""Kafka事件消费者"""

import asyncio
import json
import structlog
from typing import List, Dict, Any, Callable, Optional
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from .config import KafkaConfig

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class KafkaEventConsumer:
    """Kafka事件消费者基类（异步）
    
    负责从Kafka消费事件
    """
    
    def __init__(
        self,
        config: KafkaConfig,
        group_id: str,
        topics: List[str]
    ):
        """
        初始化Consumer
        
        Args:
            config: Kafka配置
            group_id: Consumer Group ID
            topics: 订阅的Topic列表
        """
        self.config = config
        self.group_id = group_id
        # 为所有topic添加环境前缀
        self.topics = [config.add_env_prefix(topic) for topic in topics]
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._started = False
    
    async def start(self) -> bool:
        """启动Consumer（失败时返回False，避免直接退出进程）"""
        if self._started:
            return True
        
        consumer_config = self.config.get_consumer_config(self.group_id)
        consumer = AIOKafkaConsumer(
            *self.topics,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            **consumer_config
        )
        self._consumer = consumer

        try:
            await consumer.start()
            self._started = True
            logger.info("kafka_consumer_started", group_id=self.group_id, topics=self.topics)
            return True
        except Exception as e:
            logger.error("kafka_consumer_start_failed", group_id=self.group_id, error=str(e))
            try:
                await consumer.stop()
            except Exception as stop_error:
                logger.warning("kafka_consumer_stop_after_start_failed", group_id=self.group_id, error=str(stop_error))
            self._consumer = None
            self._started = False
            return False
    
    async def stop(self):
        """停止Consumer"""
        if self._consumer and self._started:
            await self._consumer.stop()
            self._started = False
            self._consumer = None
            logger.info("kafka_consumer_stopped", group_id=self.group_id)

    async def _reset_broken_consumer(self):
        """重置异常连接的Consumer"""
        consumer = self._consumer
        self._started = False
        self._consumer = None
        if consumer is None:
            return
        try:
            await consumer.stop()
        except Exception as e:
            logger.warning("kafka_consumer_reset_stop_failed", group_id=self.group_id, error=str(e))
    
    async def consume(
        self,
        handler: Callable[[Dict[str, Any]], Any]
    ):
        """
        消费事件
        
        Args:
            handler: 事件处理函数（可以是同步或异步）
        """
        try:
            while True:
                if not self._started:
                    started = await self.start()
                    if not started:
                        logger.warning("kafka_consumer_startup_degraded_retrying", group_id=self.group_id)
                        await asyncio.sleep(2)
                        continue

                logger.info("kafka_consume_start", group_id=self.group_id)

                try:
                    async for message in self._consumer:
                        try:
                            event_data = message.value

                            logger.debug(
                                "kafka_message_received",
                                topic=message.topic,
                                partition=message.partition,
                                offset=message.offset,
                                event_id=event_data.get("event_id"),
                            )

                            if asyncio.iscoroutinefunction(handler):
                                await handler(event_data)
                            else:
                                handler(event_data)

                            # 手动提交offset
                            await self._consumer.commit()

                            logger.debug("kafka_message_handled", event_id=event_data.get("event_id"))

                        except KafkaError as e:
                            logger.error(
                                "kafka_message_consume_failed",
                                topic=message.topic,
                                offset=message.offset,
                                error=str(e),
                            )
                            raise
                        except Exception as e:
                            logger.error(
                                "kafka_message_handler_error",
                                topic=message.topic,
                                offset=message.offset,
                                error=str(e),
                                exc_info=True,
                            )
                            # 不提交offset，下次重试

                except KafkaError as e:
                    logger.warning("kafka_consume_reconnecting", group_id=self.group_id, error=str(e))
                    await self._reset_broken_consumer()
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error("kafka_consume_error_retrying", group_id=self.group_id, error=str(e), exc_info=True)
                    await self._reset_broken_consumer()
                    await asyncio.sleep(2)
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭...")
        except asyncio.CancelledError:
            raise
        finally:
            await self.stop()
    
    async def seek_to_beginning(self):
        """重置offset到最早"""
        if not self._started:
            await self.start()
        
        self._consumer.seek_to_beginning()
        logger.info("kafka_consumer_seek_to_beginning", group_id=self.group_id)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()

