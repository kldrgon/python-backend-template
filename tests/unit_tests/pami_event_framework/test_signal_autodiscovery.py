from pami_event_framework import autodiscovery as ad


def test_signal_handler_registers_and_filters_by_domain():
    original_registry = {key: value[:] for key, value in ad._SIGNAL_HANDLER_REGISTRY.items()}

    try:
        ad._SIGNAL_HANDLER_REGISTRY.clear()

        @ad.signal_handler(
            event_type="PAYMENT_CALLBACK_RECEIVED",
            signal_name="on_payment_callback",
            workflow_id_resolver=lambda event: f"payment:{event['payload']['order_id']}",
            payload_resolver=lambda event: event["payload"],
            domain="payment",
            tags=["critical"],
        )
        class PaymentWorkflow:
            pass

        mapping = ad.get_signal_handler_map()
        payment_mapping = ad.get_signal_handler_map(by_domain="payment")
        other_mapping = ad.get_signal_handler_map(by_domain="user")

        assert "PAYMENT_CALLBACK_RECEIVED" in mapping
        assert mapping["PAYMENT_CALLBACK_RECEIVED"]["workflow_class"] is PaymentWorkflow
        assert mapping["PAYMENT_CALLBACK_RECEIVED"]["signal_name"] == "on_payment_callback"
        assert mapping["PAYMENT_CALLBACK_RECEIVED"]["payload_resolver"]({"payload": {"foo": "bar"}}) == {
            "foo": "bar"
        }
        assert "PAYMENT_CALLBACK_RECEIVED" in payment_mapping
        assert other_mapping == {}
        assert "payment" in ad.get_all_domains()
    finally:
        ad._SIGNAL_HANDLER_REGISTRY.clear()
        ad._SIGNAL_HANDLER_REGISTRY.update(original_registry)
