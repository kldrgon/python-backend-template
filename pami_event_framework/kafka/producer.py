"""Kafka事件发布器"""

import json
import structlog
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from .config import KafkaConfig
from ..domain.domain_event import DomainEvent

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class KafkaEventProducer:
    """Kafka事件发布器（异步）
    
    负责将领域事件发布到Kafka
    """
    
    def __init__(self, config: KafkaConfig):
        """
        初始化Producer
        
        Args:
            config: Kafka配置
        """
        self.config = config
        self._producer: Optional[AIOKafkaProducer] = None
        self._started = False
    
    @property
    def is_started(self) -> bool:
        """Producer 是否已启动"""
        return self._started

    async def start(self) -> bool:
        """启动Producer（失败时降级，不抛出致命异常）"""
        if self._started:
            return True
        
        producer_config = self.config.get_producer_config()
        producer = AIOKafkaProducer(
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            **producer_config
        )
        self._producer = producer

        try:
            await producer.start()
            self._started = True
            logger.info("Kafka Producer已启动")
            return True
        except Exception as e:
            logger.error("kafka_producer_start_failed", error=str(e))
            # 避免启动失败后残留未关闭 producer 对象
            try:
                await producer.stop()
            except Exception as stop_error:
                logger.warning("kafka_producer_stop_after_start_failed", error=str(stop_error))
            self._producer = None
            self._started = False
            return False
    
    async def stop(self):
        """停止Producer"""
        if self._producer and self._started:
            await self._producer.stop()
            self._started = False
            self._producer = None
            logger.info("Kafka Producer已停止")

    async def _reset_broken_producer(self):
        """重置已断开的Producer连接"""
        producer = self._producer
        self._started = False
        self._producer = None
        if producer is None:
            return
        try:
            await producer.stop()
        except Exception as e:
            logger.warning("kafka_producer_reset_stop_failed", error=str(e))
    
    async def publish(
        self,
        event: DomainEvent,
        topic: Optional[str] = None,
        key: Optional[str] = None
    ) -> bool:
        """
        发布事件到Kafka（异步）
        
        Args:
            event: 领域事件
            topic: Topic名称，默认使用event_type
            key: 分区键（相同key的消息进入同一partition）
            
        Returns:
            是否发送成功
        """
        if not self._started:
            started = await self.start()
            if not started:
                logger.warning("kafka_event_publish_skipped_producer_unavailable", event_id=event.event_id)
                return False
        
        try:
            # 默认使用event_type作为topic
            topic_name = topic or event.event_type
            # 添加环境前缀
            topic_name = self.config.add_env_prefix(topic_name)
            
            # 序列化事件
            event_data = event.to_dict()
            
            # 异步发送
            result = await self._producer.send_and_wait(
                topic_name,
                value=event_data,
                key=key
            )
            
            logger.info(
                "kafka_event_published",
                topic=topic_name,
                partition=result.partition,
                offset=result.offset,
                event_id=event.event_id,
            )
            return True

        except KafkaError as e:
            logger.error(
                "kafka_event_publish_failed",
                topic=topic_name,
                event_id=event.event_id,
                error=str(e),
            )
            await self._reset_broken_producer()
            restart_ok = await self.start()
            if not restart_ok:
                return False
            try:
                retry_result = await self._producer.send_and_wait(
                    topic_name,
                    value=event_data,
                    key=key
                )
                logger.info(
                    "kafka_event_published_after_retry",
                    topic=topic_name,
                    partition=retry_result.partition,
                    offset=retry_result.offset,
                    event_id=event.event_id,
                )
                return True
            except Exception as retry_error:
                logger.error(
                    "kafka_event_publish_retry_failed",
                    topic=topic_name,
                    event_id=event.event_id,
                    error=str(retry_error),
                )
                return False
        except Exception as e:
            logger.error(
                "kafka_event_publish_error",
                topic=topic_name,
                event_id=event.event_id,
                error=str(e),
            )
            return False
    
    async def publish_dict(
        self,
        event_data: Dict[str, Any],
        topic: str,
        key: Optional[str] = None
    ) -> bool:
        """
        直接发布字典数据到Kafka
        
        Args:
            event_data: 事件数据字典
            topic: Topic名称
            key: 分区键
            
        Returns:
            是否发送成功
        """
        if not self._started:
            started = await self.start()
            if not started:
                logger.warning("kafka_dict_publish_skipped_producer_unavailable", topic=topic)
                return False
        
        try:
            # 添加环境前缀
            topic = self.config.add_env_prefix(topic)
            
            result = await self._producer.send_and_wait(
                topic,
                value=event_data,
                key=key
            )
            
            logger.info(
                "kafka_dict_published",
                topic=topic,
                partition=result.partition,
                offset=result.offset,
            )
            return True

        except KafkaError as e:
            logger.error("kafka_dict_publish_failed", topic=topic, error=str(e))
            await self._reset_broken_producer()
            restart_ok = await self.start()
            if not restart_ok:
                return False
            try:
                retry_result = await self._producer.send_and_wait(
                    topic,
                    value=event_data,
                    key=key
                )
                logger.info(
                    "kafka_dict_published_after_retry",
                    topic=topic,
                    partition=retry_result.partition,
                    offset=retry_result.offset,
                )
                return True
            except Exception as retry_error:
                logger.error("kafka_dict_publish_retry_failed", topic=topic, error=str(retry_error))
                return False
        except Exception as e:
            logger.error("kafka_dict_publish_error", topic=topic, error=str(e))
            return False
    
    async def flush(self):
        """刷新缓冲区，确保所有消息发送完成"""
        if self._producer and self._started:
            await self._producer.flush()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()

