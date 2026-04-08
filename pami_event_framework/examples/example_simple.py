"""简单示例：基础事件发布和消费"""

import asyncio
from pami_event_framework import (
    ApplicationEvent,
    KafkaConfig,
    KafkaEventProducer,
    KafkaEventConsumer,
)


# 定义事件
# 这个简单示例没有领域模型，因此使用 ApplicationEvent 更符合语义。
class UserRegistered(ApplicationEvent):
    event_type = "USER_REGISTERED"
    strict = True


# 发布事件
async def publish_example():
    """发布事件示例"""
    print("=== 发布事件示例 ===")
    
    kafka_config = KafkaConfig(bootstrap_servers="localhost:9092")
    producer = KafkaEventProducer(kafka_config)
    
    async with producer:  # 使用上下文管理器自动启动和停止
        # 创建事件
        event = UserRegistered(
            user_id="user-123",
            email="test@example.com"
        )
        
        # 发布到Kafka
        success = await producer.publish(event)
        
        if success:
            print(f"事件已发布: {event.event_id}")
        else:
            print("事件发布失败")


# 消费事件
async def consume_example():
    """消费事件示例"""
    print("=== 消费事件示例 ===")
    
    kafka_config = KafkaConfig(bootstrap_servers="localhost:9092")
    consumer = KafkaEventConsumer(
        config=kafka_config,
        group_id="example-consumer",
        topics=["USER_REGISTERED"]
    )
    
    async def handle_event(event_data: dict):
        """处理事件"""
        print(f"收到事件: {event_data['event_type']}")
        print(f"  event_id: {event_data['event_id']}")
        print(f"  payload: {event_data['payload']}")
    
    # 消费事件（阻塞）
    await consumer.consume(handler=handle_event)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python example_simple.py publish")
        print("  python example_simple.py consume")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "publish":
        asyncio.run(publish_example())
    elif command == "consume":
        asyncio.run(consume_example())
    else:
        print(f"未知命令: {command}")
