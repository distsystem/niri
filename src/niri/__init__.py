"""Niri IPC client library."""

from .ipc import EventName, NiriRequests, NiriSocket
from . import cli

__all__ = [
    "NiriSocket",
    "NiriRequests",
    "EventName",
    "cli",
]
