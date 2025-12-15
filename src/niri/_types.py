"""Type definitions for niri IPC."""

from typing import Literal

type EventName = Literal[
    "WorkspacesChanged",
    "WorkspaceActivated",
    "WorkspaceUrgencyChanged",
    "WorkspaceActiveWindowChanged",
    "WindowsChanged",
    "WindowOpenedOrChanged",
    "WindowClosed",
    "WindowFocusChanged",
    "WindowLayoutsChanged",
    "WindowUrgencyChanged",
    "KeyboardLayoutsChanged",
    "KeyboardLayoutSwitched",
    "OverviewOpenedOrClosed",
    "ConfigLoaded",
]
