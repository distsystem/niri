"""CLI fallback for niri actions with IPC issues.

Some actions (e.g., SetWindowWidth) have regressions in niri 25.11 where
they return Ok but don't actually work via socket IPC.
"""

import json
import subprocess


def _run_action(action_name: str, *args: str) -> None:
    subprocess.run(["niri", "msg", "action", action_name, *args], check=False)


def action(action_name: str, window_id: int | None = None) -> None:
    args = ["--id", str(window_id)] if window_id is not None else []
    _run_action(action_name, *args)


def query(request: str) -> dict:
    result = subprocess.run(
        ["niri", "msg", "--json", request],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def set_window_width(window_id: int, width: str) -> None:
    _run_action("set-window-width", "--id", str(window_id), width)


def focus_window(window_id: int) -> None:
    _run_action("focus-window", "--id", str(window_id))


def close_window(window_id: int) -> None:
    _run_action("close-window", "--id", str(window_id))
