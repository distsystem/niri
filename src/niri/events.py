"""Event handling and dispatch for niri IPC."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from ._socket import NiriRequests
from ._types import EventName

type EventHandler = Callable[[str, dict], None]


@dataclass
class Event:
    """Event wrapper with name and data."""

    name: EventName
    data: dict


@dataclass
class EventDispatcher:
    """Multi-handler event dispatcher with decorator registration."""

    _handlers: dict[str, list[EventHandler]] = field(
        default_factory=dict, init=False, repr=False
    )
    _global_handlers: list[EventHandler] = field(
        default_factory=list, init=False, repr=False
    )

    def on(self, event_name: EventName) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register handler for specific event type.

        Usage:
            @dispatcher.on("WindowOpenedOrChanged")
            def handle_window(name, data):
                ...
        """

        def decorator(handler: EventHandler) -> EventHandler:
            self._handlers.setdefault(event_name, []).append(handler)
            return handler

        return decorator

    def on_any(self, handler: EventHandler) -> EventHandler:
        """Register handler for all events."""
        self._global_handlers.append(handler)
        return handler

    def add_handler(self, event_name: EventName, handler: EventHandler) -> None:
        """Programmatically add handler for specific event type."""
        self._handlers.setdefault(event_name, []).append(handler)

    def dispatch(self, event_name: str, event_data: dict) -> None:
        """Dispatch event to all registered handlers."""
        for handler in self._global_handlers:
            handler(event_name, event_data)
        for handler in self._handlers.get(event_name, []):
            handler(event_name, event_data)


def event_stream(conn: NiriRequests) -> Iterator[tuple[str, dict]]:
    """Generate events from niri EventStream.

    This is a thin wrapper around conn.read_eventstream() for convenience.
    """
    yield from conn.read_eventstream()
