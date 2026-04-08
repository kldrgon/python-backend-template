"""SignalLauncher 最小示例"""

import asyncio

from temporalio import workflow
from temporalio.client import Client as TemporalClient
from temporalio.worker import Worker as TemporalWorker

from pami_event_framework.autodiscovery import get_signal_handler_map, signal_handler
from pami_event_framework.config import TemporalConfig
from pami_event_framework.kafka.config import KafkaConfig
from pami_event_framework.launcher.signal_launcher import SignalLauncher


@workflow.defn
@signal_handler(
    event_type="PAYMENT_CALLBACK_RECEIVED",
    signal_name="on_payment_callback",
    workflow_id_resolver=lambda event: f"payment:{event['payload']['order_id']}",
    payload_resolver=lambda event: {
        "event_id": event["event_id"],
        "status": event["payload"]["status"],
        "order_id": event["payload"]["order_id"],
    },
    domain="payment",
)
class PaymentWorkflow:
    def __init__(self):
        self.received_callbacks = []

    @workflow.run
    async def run(self, order_id: str):
        await workflow.wait_condition(lambda: len(self.received_callbacks) > 0)
        return {
            "order_id": order_id,
            "callbacks": list(self.received_callbacks),
        }

    @workflow.signal
    def on_payment_callback(self, payload: dict) -> None:
        self.received_callbacks.append(payload)


async def start_signal_launcher_example():
    """启动 SignalLauncher 示例"""
    signal_handler_map = get_signal_handler_map(by_domain="payment")

    temporal_client = await TemporalClient.connect("localhost:7233", namespace="default")
    launcher = SignalLauncher(
        kafka_config=KafkaConfig(bootstrap_servers="localhost:9092"),
        temporal_client=temporal_client,
        signal_handler_map=signal_handler_map,
        consumer_group_id="example-signal-launcher",
        temporal_config=TemporalConfig(),
    )

    await launcher.start()


async def start_worker_example():
    """启动处理 signal 的 worker"""
    temporal_client = await TemporalClient.connect("localhost:7233", namespace="default")
    worker = TemporalWorker(
        temporal_client,
        task_queue="payment-task-queue",
        workflows=[PaymentWorkflow],
        activities=[],
    )
    await worker.run()


async def send_signal_direct_example():
    """直接发 signal 的最小示例，便于本地验证 workflow 侧逻辑"""
    temporal_client = await TemporalClient.connect("localhost:7233", namespace="default")
    handle = temporal_client.get_workflow_handle(workflow_id="payment:order-123")
    await handle.signal(
        "on_payment_callback",
        {"event_id": "evt-1", "status": "SUCCESS", "order_id": "order-123"},
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  uv run python pami_event_framework/examples/example_signal.py worker")
        print("  uv run python pami_event_framework/examples/example_signal.py launcher")
        print("  uv run python pami_event_framework/examples/example_signal.py signal")
        raise SystemExit(1)

    command = sys.argv[1]

    if command == "worker":
        asyncio.run(start_worker_example())
    elif command == "launcher":
        asyncio.run(start_signal_launcher_example())
    elif command == "signal":
        asyncio.run(send_signal_direct_example())
    else:
        print(f"未知命令: {command}")
        raise SystemExit(1)
