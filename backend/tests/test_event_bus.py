from app.application.event_bus import EventBus


def test_event_bus_basic():
    bus = EventBus()
    received = []
    bus.subscribe("TestEvent", lambda payload: received.append(payload))
    bus.publish("TestEvent", {"data": "hello"})
    assert received == [{"data": "hello"}]

def test_event_bus_no_handlers():
    bus = EventBus()
    bus.publish("UnknownEvent", {"data": "test"})

def test_event_bus_handler_error_isolated():
    bus = EventBus()
    received = []
    bus.subscribe("Event", lambda _: 1/0)
    bus.subscribe("Event", lambda payload: received.append(payload))
    bus.publish("Event", {"data": "ok"})
    assert received == [{"data": "ok"}]

def test_event_bus_no_reentrant():
    bus = EventBus()
    call_count = [0]
    def handler(payload):
        call_count[0] += 1
        bus.publish("Event", {"retry": True})
    bus.subscribe("Event", handler)
    bus.publish("Event", {"start": True})
    assert call_count[0] == 1
