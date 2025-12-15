"""Unified niri IPC client library.

Usage:
    from niri import NiriRequests, EventDispatcher
    from niri import cli

    # Create connection
    socket_path = NiriRequests.get_socket_path()
    conn = NiriRequests(socket_path)

    # Setup event handlers
    dispatcher = EventDispatcher()

    @dispatcher.on("WindowOpenedOrChanged")
    def handle_window(name, data):
        window = data["window"]
        # ... handle window event

    # Event loop
    for event_name, event_data in conn.read_eventstream():
        dispatcher.dispatch(event_name, event_data)

    # CLI fallback for actions with IPC issues
    cli.set_window_width(window_id, "50%")
"""

from ._socket import NiriRequests, NiriSocket
from ._types import EventName
from .events import Event, EventDispatcher, event_stream
from . import cli

__all__ = [
    "NiriSocket",
    "NiriRequests",
    "EventName",
    "Event",
    "EventDispatcher",
    "event_stream",
    "cli",
]
