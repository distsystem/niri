"""Niri IPC client library."""

import logging

from .ipc import EventName, NiriRequests, NiriSocket
from . import cli

logger = logging.getLogger(__name__)

__all__ = [
    "NiriSocket",
    "NiriRequests",
    "EventName",
    "cli",
    "logger",
]
