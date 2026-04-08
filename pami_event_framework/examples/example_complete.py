"""完整示例：订单事件处理"""

import asyncio
from temporalio import workflow
from temporalio.client import Client as TemporalClient
from temporalio.worker import Worker as TemporalWorker
from pami_event_framework import (
    DomainEvent,
    AggregateRoot,
    SessionManager,
    OutboxRepository,
    KafkaConfig,
    KafkaEventProducer,
    OutboxPublisher,
    WorkflowLauncher,
)


# 1. 定义领域事件
class OrderPlaced(DomainEvent):
    """订单已创建事件"""
    event_type = "ORDER_PLACED"
    strict = True


class OrderCancelled(DomainEvent):
    """订单已取消事件"""
    event_type = "ORDER_CANCELLED"
    strict = False


# 2. 定义聚合根
class Order(AggregateRoot):
    def __init__(self, order_id: str, amount: float):
        super().__init__()
        self.order_id = order_id
        self.amount = amount
        self.status = "pending"
    
    def get_aggregate_id(self) -> str:
        return self.order_id
    
    def place(self):
        """下单"""
        self.status = "placed"
        self.raise_event(OrderPlaced(
            order_id=self.order_id,
            amount=self.amount
        ))
    
    def cancel(self):
        """取消订单"""
        self.status = "cancelled"
        self.raise_event(OrderCancelled(order_id=self.order_id))


# 3. 定义Workflow
@workflow.defn
class InventoryWorkflow:
    """库存扣减Workflow"""
    
    @workflow.run
    async def run(self, event_data: dict):
        workflow.logger.info(f"Workflow开始: {event_data.get('event_id')}")
        
        try:
            order_id = event_data['payload']['order_id']
            amount = event_data['payload'].get('amount', 0)
            
            # 模拟业务逻辑
            print(f"处理库存扣减: order_id={order_id}, amount={amount}")
            await asyncio.sleep(1)  # 模拟处理时间
            
            workflow.logger.info("Workflow完成")
            return {"success": True}
            
        except Exception as e:
            workflow.logger.error(f"Workflow错误: {e}")
            raise


@workflow.defn
class EmailWorkflow:
    """邮件通知Workflow"""
    
    @workflow.run
    async def run(self, event_data: dict):
        workflow.logger.info(f"Workflow开始: {event_data.get('event_id')}")
        
        try:
            order_id = event_data['payload']['order_id']
            
            # 模拟发送邮件
            print(f"发送邮件通知: order_id={order_id}")
            await asyncio.sleep(0.5)
            
            workflow.logger.info("Workflow完成")
            return {"success": True}
            
        except Exception as e:
            workflow.logger.error(f"Workflow错误: {e}")
            raise


# 4. 事件映射配置（WorkflowLauncher 当前格式）
EVENT_HANDLER_MAP = {
    "ORDER_PLACED": [
        {
            "workflow_class": InventoryWorkflow,
            "task_queue": "inventory-queue",
        },
        {
            "workflow_class": EmailWorkflow,
            "task_queue": "email-queue",
        },
    ],
    "ORDER_CANCELLED": {
        "workflow_class": InventoryWorkflow,
        "task_queue": "inventory-queue",
    },
}


# 5. 业务操作（发布事件）
async def create_order_example():
    """创建订单示例"""
    print("=== 创建订单示例 ===")
    
    # 初始化
    session_manager = SessionManager(
        writer_db_url="postgresql://user:pass@localhost/db",
        reader_db_url="postgresql://user:pass@localhost/db",
    )
    
    # 创建订单
    order = Order(order_id="order-123", amount=100.0)
    order.place()
    
    # 保存到Outbox
    async with session_manager.session_factory() as session:
        outbox_repo = OutboxRepository(session)
        await outbox_repo.save_events(
            events=order.get_domain_events(),
            aggregate_id=order.get_aggregate_id(),
            aggregate_type="Order"
        )
        await session.commit()
    
    print(f"订单已创建并保存到Outbox: {order.order_id}")


# 6. 启动Outbox发布器
async def start_outbox_publisher_example():
    """启动Outbox发布器"""
    print("=== 启动Outbox发布器 ===")
    
    kafka_config = KafkaConfig(bootstrap_servers="localhost:9092")
    kafka_producer = KafkaEventProducer(kafka_config)
    
    publisher = OutboxPublisher(
        kafka_producer=kafka_producer,
        batch_size=100,
        interval_seconds=5
    )
    
    await publisher.start()


# 7. 启动WorkflowLauncher
async def start_workflow_launcher_example():
    """启动WorkflowLauncher"""
    print("=== 启动WorkflowLauncher ===")
    
    kafka_config = KafkaConfig(bootstrap_servers="localhost:9092")
    temporal_client = await TemporalClient.connect(
        "localhost:7233",
        namespace="default"
    )
    
    launcher = WorkflowLauncher(
        kafka_config=kafka_config,
        temporal_client=temporal_client,
        event_handler_map=EVENT_HANDLER_MAP,
        consumer_group_id="workflow-launcher"
    )
    
    await launcher.start()


# 8. 启动Temporal Worker
async def start_temporal_worker_example():
    """启动Temporal Worker"""
    print("=== 启动Temporal Worker ===")
    
    temporal_client = await TemporalClient.connect(
        "localhost:7233",
        namespace="default"
    )
    
    # Inventory Worker
    inventory_worker = TemporalWorker(
        temporal_client,
        task_queue="inventory-queue",
        workflows=[InventoryWorkflow],
        activities=[]
    )
    
    # Email Worker
    email_worker = TemporalWorker(
        temporal_client,
        task_queue="email-queue",
        workflows=[EmailWorkflow],
        activities=[]
    )
    
    # 并发运行
    await asyncio.gather(
        inventory_worker.run(),
        email_worker.run()
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python example_complete.py create_order")
        print("  python example_complete.py outbox_publisher")
        print("  python example_complete.py workflow_launcher")
        print("  python example_complete.py temporal_worker")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create_order":
        asyncio.run(create_order_example())
    elif command == "outbox_publisher":
        asyncio.run(start_outbox_publisher_example())
    elif command == "workflow_launcher":
        asyncio.run(start_workflow_launcher_example())
    elif command == "temporal_worker":
        asyncio.run(start_temporal_worker_example())
    else:
        print(f"未知命令: {command}")
