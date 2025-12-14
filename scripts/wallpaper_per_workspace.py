#!/usr/bin/env python3
"""Random wallpaper per workspace with timed rotation using niri IPC and swww."""

import argparse
import json
import os
import random
import signal
import socket
import subprocess
import threading
from collections import deque
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
DEFAULT_INTERVAL_MINUTES = 15


# --- NiriSocket ---


class NiriSocket:
    """Helper used to read & write json messages to a niri socket connection."""

    def __init__(self, socket_path: str, buffer_size: int = 4096):
        if not socket_path:
            raise ValueError("Cannot connect to niri, no socket path given")

        self._skt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._skt.connect(socket_path)
        self._bufsize = buffer_size
        self._msg_queue: deque[str] = deque()
        self._inprog_str: str | None = None

    def _read_next(self) -> dict:
        if self._msg_queue:
            return json.loads(self._msg_queue.popleft())

        while True:
            resp_binstr = self._skt.recv(self._bufsize)
            if len(resp_binstr) == 0:
                return {}

            resp_str = resp_binstr.decode("utf-8")
            if self._inprog_str is not None:
                resp_str = self._inprog_str + resp_str
                self._inprog_str = None

            msg_list = resp_str.split("\n")
            last_msg_piece = msg_list.pop()
            self._inprog_str = last_msg_piece if last_msg_piece else None
            if msg_list:
                break

        if not msg_list:
            raise IOError("Error reading next message (empty message list)")

        out_msg_str = msg_list[0]
        if len(msg_list) > 1:
            self._msg_queue.extend(msg_list[1:])

        return json.loads(out_msg_str)

    def _send_string(self, string: str):
        return self._skt.sendall(f'"{string}"\n'.encode("utf-8"))

    def close(self):
        self._skt.close()

    @staticmethod
    def get_niri_socket_path() -> str | None:
        return os.environ.get("NIRI_SOCKET")


class NiriRequests(NiriSocket):
    """Helper used to make requests to niri."""

    def request(self, message: str) -> tuple[bool, dict]:
        self._send_string(message)
        resp_json = self._read_next()
        is_ok = "Ok" in resp_json
        return is_ok, resp_json.get("Ok" if is_ok else "Err", {})

    def read_eventstream(self):
        is_ok, resp = self.request("EventStream")
        if not is_ok:
            raise IOError(f"Error requesting EventStream: {resp}")

        while True:
            event_json = self._read_next()
            if not event_json:
                break
            event_name = next(iter(event_json.keys()))
            event_data = event_json.get(event_name)
            yield event_name, event_data


# --- Wallpaper Manager ---


class WallpaperManager:
    def __init__(self, wallpapers_dir: Path, interval_minutes: int):
        self.wallpapers_dir = wallpapers_dir
        self.interval_seconds = interval_minutes * 60
        self.all_wallpapers: list[Path] = []
        self.workspace_wallpapers: dict[int, Path] = {}  # workspace_id -> wallpaper
        self.workspace_outputs: dict[int, str] = {}  # workspace_id -> output
        self.active_workspaces: dict[str, int] = {}  # output -> active workspace_id
        self.current_workspace_id: int | None = None
        self.lock = threading.Lock()
        self.timer: threading.Timer | None = None

    def scan_wallpapers(self):
        """Scan directory for image files."""
        self.all_wallpapers = [
            f for f in self.wallpapers_dir.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ]
        if not self.all_wallpapers:
            raise ValueError(f"No wallpapers found in {self.wallpapers_dir}")

    def get_workspaces(self) -> list[dict]:
        """Fetch current workspaces from niri."""
        skt_path = NiriSocket.get_niri_socket_path()
        if not skt_path:
            return []
        try:
            req = NiriRequests(skt_path)
            is_ok, data = req.request("Workspaces")
            req.close()
            if not is_ok:
                return []
            # Response format: {"Ok": {"Workspaces": [...]}}
            return data.get("Workspaces", []) if isinstance(data, dict) else []
        except Exception:
            return []

    def assign_wallpapers(self):
        """Assign unique random wallpapers to all workspaces."""
        workspaces = self.get_workspaces()
        if not workspaces:
            return

        with self.lock:
            # Shuffle and assign wallpapers (cycle if more workspaces than wallpapers)
            shuffled = self.all_wallpapers.copy()
            random.shuffle(shuffled)

            for i, ws in enumerate(workspaces):
                ws_id = ws["id"]
                output = ws.get("output")
                if output:
                    self.workspace_outputs[ws_id] = output
                    self.workspace_wallpapers[ws_id] = shuffled[i % len(shuffled)]
                    if ws.get("is_active"):
                        self.active_workspaces[output] = ws_id
                    if ws.get("is_focused"):
                        self.current_workspace_id = ws_id

    def apply_wallpaper(self, ws_id: int):
        """Apply wallpaper for a specific workspace."""
        with self.lock:
            wallpaper = self.workspace_wallpapers.get(ws_id)
            output = self.workspace_outputs.get(ws_id)

        if not wallpaper or not output:
            return

        subprocess.run(
            [
                "swww", "img", str(wallpaper),
                "-o", output,
                "--transition-type", "fade",
                "--transition-duration", "0.4",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def apply_active_wallpapers(self):
        """Apply wallpapers to active workspaces (one per output)."""
        with self.lock:
            ws_ids = list(self.active_workspaces.values())

        for ws_id in ws_ids:
            self.apply_wallpaper(ws_id)

    def rotate_wallpapers(self):
        """Rotate wallpapers for all workspaces."""
        self.assign_wallpapers()
        self.apply_active_wallpapers()
        self.schedule_rotation()

    def schedule_rotation(self):
        """Schedule next rotation."""
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.interval_seconds, self.rotate_wallpapers)
        self.timer.daemon = True
        self.timer.start()

    def on_workspace_activated(self, ws_id: int, focused: bool):
        """Handle workspace activation."""
        if not focused:
            return

        with self.lock:
            if self.current_workspace_id == ws_id:
                return
            self.current_workspace_id = ws_id

            # Assign wallpaper if new workspace
            if ws_id not in self.workspace_wallpapers:
                used = set(self.workspace_wallpapers.values())
                available = [w for w in self.all_wallpapers if w not in used]
                if not available:
                    available = self.all_wallpapers
                self.workspace_wallpapers[ws_id] = random.choice(available)

        self.apply_wallpaper(ws_id)

    def on_workspaces_changed(self, workspaces: list[dict]):
        """Handle workspace list changes."""
        with self.lock:
            for ws in workspaces:
                ws_id = ws["id"]
                output = ws.get("output")
                if output:
                    self.workspace_outputs[ws_id] = output

                if ws_id not in self.workspace_wallpapers:
                    used = set(self.workspace_wallpapers.values())
                    available = [w for w in self.all_wallpapers if w not in used]
                    if not available:
                        available = self.all_wallpapers
                    self.workspace_wallpapers[ws_id] = random.choice(available)

                if ws.get("is_focused"):
                    self.current_workspace_id = ws_id

            # Clean up removed workspaces
            current_ids = {ws["id"] for ws in workspaces}
            for ws_id in list(self.workspace_wallpapers.keys()):
                if ws_id not in current_ids:
                    del self.workspace_wallpapers[ws_id]
                    self.workspace_outputs.pop(ws_id, None)

    def stop(self):
        if self.timer:
            self.timer.cancel()


# --- Main ---


def catch_sigterm(_signum, _frame):
    raise InterruptedError


def main():
    parser = argparse.ArgumentParser(description="Random wallpaper per workspace")
    parser.add_argument(
        "wallpapers_dir",
        nargs="?",
        default=os.environ.get("WALLPAPERS_DIR", str(Path.home() / ".wallpaper")),
        help="Directory containing wallpaper images",
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=DEFAULT_INTERVAL_MINUTES,
        help=f"Rotation interval in minutes (default: {DEFAULT_INTERVAL_MINUTES})",
    )
    args = parser.parse_args()

    wallpapers_dir = Path(args.wallpapers_dir)
    if not wallpapers_dir.is_dir():
        print(f"Wallpapers directory not found: {wallpapers_dir}")
        return 1

    skt_path = NiriSocket.get_niri_socket_path()
    if not skt_path:
        print("Couldn't find niri socket! (env: NIRI_SOCKET)")
        return 1

    manager = WallpaperManager(wallpapers_dir, args.interval)
    try:
        manager.scan_wallpapers()
    except ValueError as e:
        print(e)
        return 1

    # Initial assignment and apply
    manager.assign_wallpapers()
    manager.apply_active_wallpapers()
    manager.schedule_rotation()

    niri = NiriRequests(skt_path)
    signal.signal(signal.SIGTERM, catch_sigterm)

    try:
        for evt_name, evt_data in niri.read_eventstream():
            if evt_name == "WorkspaceActivated":
                manager.on_workspace_activated(
                    evt_data["id"], evt_data.get("focused", False)
                )
            elif evt_name == "WorkspacesChanged":
                manager.on_workspaces_changed(evt_data.get("workspaces", []))
    except (KeyboardInterrupt, InterruptedError):
        pass
    finally:
        manager.stop()
        niri.close()
        print(f"({Path(__file__).name}) - Closed niri IPC connection")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
