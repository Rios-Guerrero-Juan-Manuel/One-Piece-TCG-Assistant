import logging
from collections import defaultdict
from collections.abc import Callable

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._publishing: set[str] = set()

    def subscribe(self, event_name: str, handler: Callable):
        self._handlers[event_name].append(handler)

    def publish(self, event_name: str, payload=None):
        if event_name in self._publishing:
            logger.warning("Reentrant publish prevented for %s", event_name)
            return
        self._publishing.add(event_name)
        try:
            for handler in self._handlers.get(event_name, []):
                try:
                    handler(payload)
                except Exception:
                    logger.exception("Handler failed for event %s", event_name)
        finally:
            self._publishing.discard(event_name)

_event_bus = EventBus()

def get_event_bus() -> EventBus:
    return _event_bus
