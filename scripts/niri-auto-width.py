#!/usr/bin/env python3
"""Auto-adjust window width: 100% for single window, default for multiple."""

import json
import subprocess

# Match default-column-width in conf.d/layout.kdl
DEFAULT_WIDTH = "67%"


def niri_msg(*args: str) -> str:
    return subprocess.run(
        ["niri", "msg", "-j", *args], capture_output=True, text=True
    ).stdout


def get_workspace_windows(workspace_id: int) -> list[int]:
    windows = json.loads(niri_msg("windows"))
    return [
        w["id"]
        for w in windows
        if w["workspace_id"] == workspace_id and not w["is_floating"]
    ]


def set_window_width(window_id: int, width: str) -> None:
    subprocess.run(
        ["niri", "msg", "action", "set-window-width", "--id", str(window_id), width]
    )


def main() -> None:
    stream = subprocess.Popen(
        ["niri", "msg", "-j", "event-stream"], stdout=subprocess.PIPE, text=True
    )

    for line in stream.stdout:
        event = json.loads(line)

        if "WindowOpenedOrChanged" in event:
            window = event["WindowOpenedOrChanged"]["window"]
            if window["is_floating"]:
                continue
            if workspace_id := window.get("workspace_id"):
                window_ids = get_workspace_windows(workspace_id)
                count = len(window_ids)
                if count == 1:
                    set_window_width(window["id"], "100%")
                elif count == 2:
                    for wid in window_ids:
                        set_window_width(wid, DEFAULT_WIDTH)

        elif "WindowClosed" in event:
            focused = niri_msg("focused-window")
            if not focused or focused.strip() == "null":
                continue
            if workspace_id := json.loads(focused).get("workspace_id"):
                window_ids = get_workspace_windows(workspace_id)
                count = len(window_ids)
                if count == 1:
                    set_window_width(window_ids[0], "100%")


if __name__ == "__main__":
    main()
