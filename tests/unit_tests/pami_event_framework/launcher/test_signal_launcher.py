import pytest

from pami_event_framework.launcher.signal_launcher import SignalLauncher


class _FakeHandle:
    def __init__(self):
        self.calls = []

    async def signal(self, signal_name, payload):
        self.calls.append((signal_name, payload))


class _FakeTemporalClient:
    def __init__(self):
        self.handles = {}

    def get_workflow_handle(self, workflow_id):
        handle = self.handles.setdefault(workflow_id, _FakeHandle())
        return handle


class _FakeTemporalConfig:
    def add_env_prefix(self, value: str) -> str:
        return f"test-{value}"


@pytest.mark.asyncio
async def test_signal_launcher_resolves_workflow_and_sends_signal():
    client = _FakeTemporalClient()
    launcher = SignalLauncher(
        kafka_config=None,
        temporal_client=client,
        signal_handler_map={
            "PAYMENT_CALLBACK_RECEIVED": {
                "workflow_class": type("PaymentWorkflow", (), {}),
                "signal_name": "on_payment_callback",
                "workflow_id_resolver": lambda event: f"payment:{event['payload']['order_id']}",
                "payload_resolver": lambda event: {
                    "event_id": event["event_id"],
                    "payload": event["payload"],
                },
            }
        },
        temporal_config=_FakeTemporalConfig(),
    )

    await launcher._handle_event(
        {
            "event_type": "PAYMENT_CALLBACK_RECEIVED",
            "event_id": "evt-1",
            "payload": {"order_id": "ord-1", "status": "SUCCESS"},
        }
    )

    handle = client.handles["test-payment:ord-1"]
    assert handle.calls == [
        (
            "on_payment_callback",
            {
                "event_id": "evt-1",
                "payload": {"order_id": "ord-1", "status": "SUCCESS"},
            },
        )
    ]
