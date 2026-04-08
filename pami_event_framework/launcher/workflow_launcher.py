"""WorkflowLauncher - 监听Kafka事件并启动Temporal Workflow"""

import structlog
import asyncio
from typing import Dict, Any
from temporalio.client import Client as TemporalClient
from ..kafka.consumer import KafkaEventConsumer
from ..kafka.config import KafkaConfig
from ..config import TemporalConfig
logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class WorkflowLauncher:
    """
    WorkflowLauncher - 轻量桥接层（异步）
    
    职责：
    1. 监听Kafka事件
    2. 根据映射启动对应的Temporal Workflow
    3. 不包含业务逻辑
    
    事件映射格式:
    {
        "EVENT_TYPE": {
            "workflow_class": WorkflowClass,
            "task_queue": "task-queue-name"
        }
    }
    """
    
    def __init__(
        self,
        kafka_config: KafkaConfig,
        temporal_client: TemporalClient,
        event_handler_map: Dict[str, Dict[str, Any]],
        consumer_group_id: str = "workflow-launcher",
        temporal_config: TemporalConfig = None
    ):
        """
        初始化WorkflowLauncher
        
        Args:
            kafka_config: Kafka配置
            temporal_client: Temporal客户端
            event_handler_map: 事件到Workflow的映射
            consumer_group_id: Consumer Group ID
            temporal_config: Temporal配置（用于租户隔离）
        """
        self.kafka_config = kafka_config
        self.temporal_client = temporal_client
        self.event_handler_map = event_handler_map
        self.consumer_group_id = consumer_group_id
        self.temporal_config = temporal_config or TemporalConfig()
        
        # 收集所有需要订阅的事件
        self.subscribed_events = list(event_handler_map.keys())
        
        logger.info("workflow_launcher_init", event_count=len(self.subscribed_events))
    
    async def _handle_event(self, event_data: Dict[str, Any]):
        """
        处理单个事件
        
        Args:
            event_data: 事件数据
        """
        event_type = event_data.get('event_type')
        event_id = event_data.get('event_id')
        
        if not event_type:
            logger.warning("event_missing_event_type", event_data=event_data)
            return

        if not event_id:
            logger.warning("event_missing_event_id", event_data=event_data)
            return
        
        # 查找对应的Handler配置
        handler_config = self.event_handler_map.get(event_type)
        
        if not handler_config:
            logger.debug("event_no_handler", event_type=event_type)
            return

        logger.info("event_handling", event_type=event_type, event_id=event_id)
        
        # 支持单个或多个 workflow
        # handler_config 可能是 dict 或 list[dict]
        if isinstance(handler_config, list):
            # 多个 workflow，并行启动
            tasks = []
            for cfg in handler_config:
                workflow_class = cfg['workflow_class']
                workflow_name = self._get_workflow_name(workflow_class)
                tasks.append(self._start_workflow(event_data, cfg, workflow_name))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(
                        "workflow_parallel_start_failed",
                        event_type=event_type,
                        event_id=event_id,
                        error=str(result),
                        exc_info=result,
                    )
        else:
            # 单个 workflow
            workflow_class = handler_config['workflow_class']
            workflow_name = self._get_workflow_name(workflow_class)
            try:
                await self._start_workflow(event_data, handler_config, workflow_name)
            except Exception as e:
                logger.error(
                    "workflow_start_failed",
                    event_type=event_type,
                    event_id=event_id,
                    error=str(e),
                    exc_info=True,
                )
    
    def _get_workflow_name(self, workflow_class) -> str:
        """获取 workflow 的名称"""
        defn = getattr(workflow_class, '__temporal_workflow_definition', None)
        if defn and hasattr(defn, 'name') and defn.name:
            return defn.name
        return workflow_class.__name__
    
    async def _start_workflow(
        self,
        event_data: Dict[str, Any],
        handler_config: Dict[str, Any],
        workflow_name: str
    ):
        """
        启动Workflow
        
        Args:
            event_data: 事件数据
            handler_config: Handler配置
            workflow_name: Workflow名称（用于生成唯一ID）
        """
        workflow_class = handler_config['workflow_class']
        task_queue = handler_config['task_queue']
        event_type = event_data['event_type']
        event_id = event_data['event_id']
        
        # 添加环境前缀到task_queue
        task_queue = self.temporal_config.add_env_prefix(task_queue)
        
        # 生成Workflow ID（幂等性保证）
        # 对于同一事件的多个workflow，使用workflow name区分
        workflow_id = f"{event_type}:{workflow_name}:{event_id}"
        # 添加环境前缀到workflow_id
        workflow_id = self.temporal_config.add_env_prefix(workflow_id)
        
        # 启动Workflow
        try:
            await self.temporal_client.start_workflow(
                workflow_class,
                event_data,
                id=workflow_id,
                task_queue=task_queue
            )
            
            logger.info("workflow_started", event_type=event_type, workflow_id=workflow_id)
            
        except Exception as e:
            # Workflow ID已存在是正常的（幂等性）
            error_msg = str(e).lower()
            if "already started" in error_msg or "already exists" in error_msg:
                logger.debug("workflow_already_exists_idempotent", workflow_id=workflow_id)
            else:
                logger.error(
                    "workflow_start_error",
                    event_type=event_type,
                    workflow_id=workflow_id,
                    error=str(e),
                    exc_info=True,
                )
                raise
    
    async def start(self):
        """
        启动WorkflowLauncher（阻塞）
        
        开始监听Kafka并启动Workflow
        """
        if not self.subscribed_events:
            logger.warning("没有需要订阅的事件，WorkflowLauncher不启动")
            return
        
        logger.info(
            "workflow_launcher_starting",
            group_id=self.consumer_group_id,
            events=self.subscribed_events,
        )
        
        # 创建Kafka Consumer
        consumer = KafkaEventConsumer(
            config=self.kafka_config,
            group_id=self.consumer_group_id,
            topics=self.subscribed_events
        )
        
        # 开始消费（异步）
        await consumer.consume(handler=self._handle_event)

