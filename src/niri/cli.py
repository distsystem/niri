"""CLI fallback for niri actions with IPC issues.

Some actions (e.g., SetWindowWidth) have regressions in niri 25.11 where
they return Ok but don't actually work via socket IPC. This module provides
CLI-based alternatives using subprocess.
"""

import json
import subprocess


def set_window_width(window_id: int, width: str) -> None:
    """Set window width via CLI (IPC regression workaround)."""
    subprocess.run(
        ["niri", "msg", "action", "set-window-width", "--id", str(window_id), width],
        check=False,
    )


def action(action_name: str, window_id: int | None = None) -> None:
    """Execute niri action via CLI."""
    cmd = ["niri", "msg", "action", action_name]
    if window_id is not None:
        cmd.extend(["--id", str(window_id)])
    subprocess.run(cmd, check=False)


def query(request: str) -> dict:
    """Query niri state via CLI (JSON output)."""
    result = subprocess.run(
        ["niri", "msg", "--json", request],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def focus_window(window_id: int) -> None:
    """Focus window by ID."""
    subprocess.run(
        ["niri", "msg", "action", "focus-window", "--id", str(window_id)],
        check=False,
    )


def close_window(window_id: int) -> None:
    """Close window by ID."""
    subprocess.run(
        ["niri", "msg", "action", "close-window", "--id", str(window_id)],
        check=False,
    )
