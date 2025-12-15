#!/usr/bin/env python3
"""Test script demonstrating niri IPC with multiple handlers."""

import random
import subprocess
import threading
from pathlib import Path

from niri import NiriRequests, cli

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


class TileManager:
    """Auto-tile windows when count <= N per workspace."""

    def __init__(self, n: int = 3, maximize_solos: bool = True):
        self.n = n
        self.maximize_solos = maximize_solos
        self.win_state: dict[int, dict] = {}
        self.wspace_state: dict[int, dict] = {}

    def _get_tiled_windows(self, workspace_id: int) -> dict[int, dict]:
        return {
            wid: w for wid, w in self.win_state.items()
            if w["workspace_id"] == workspace_id and not w["is_floating"]
        }

    def _get_col_idx(self, win: dict) -> int | None:
        pos = win["layout"]["pos_in_scrolling_layout"]
        return pos[0] if pos else None

    def __call__(self, name: str, data: dict) -> None:
        match name:
            case "WorkspacesChanged":
                self.wspace_state = {ws["id"]: ws for ws in data["workspaces"]}

            case "WindowsChanged":
                self.win_state = {w["id"]: w for w in data["windows"]}

            case "WindowOpenedOrChanged":
                win = data["window"]
                wid = win["id"]
                is_new = wid not in self.win_state
                self.win_state[wid] = win

                if not is_new or win["is_floating"]:
                    return

                tiled = self._get_tiled_windows(win["workspace_id"])
                count = len(tiled)

                if count == 1 and self.maximize_solos:
                    cli.set_window_width(wid, "100%")
                elif count == 2:
                    for w in tiled:
                        cli.set_window_width(w, "50%")
                elif 2 < count <= self.n:
                    col = self._get_col_idx(win)
                    action = "consume-or-expel-window-right" if col == 2 else "consume-or-expel-window-left"
                    cli.action(action, wid)

            case "WindowClosed":
                wid = data["id"]
                closed = self.win_state.pop(wid, None)
                if not closed:
                    return

                tiled = self._get_tiled_windows(closed["workspace_id"])
                if len(tiled) == 1 and self.maximize_solos:
                    cli.set_window_width(next(iter(tiled)), "100%")

            case "WindowLayoutsChanged":
                for wid, layout in data["changes"]:
                    if wid in self.win_state:
                        self.win_state[wid]["layout"] = layout


class WallpaperManager:
    """Random wallpaper per workspace with timed rotation."""

    def __init__(self, wallpapers_dir: Path, interval_minutes: int = 15):
        self.interval_seconds = interval_minutes * 60
        self.all_wallpapers = [
            f for f in wallpapers_dir.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ]
        self.workspace_wallpapers: dict[int, Path] = {}
        self.workspace_outputs: dict[int, str] = {}
        self.current_ws_id: int | None = None
        self.lock = threading.Lock()
        self.timer: threading.Timer | None = None
        if self.all_wallpapers:
            self._schedule_rotation()

    def _apply(self, ws_id: int) -> None:
        with self.lock:
            wallpaper = self.workspace_wallpapers.get(ws_id)
            output = self.workspace_outputs.get(ws_id)
        if not wallpaper or not output:
            return
        subprocess.run(
            ["swww", "img", str(wallpaper), "-o", output,
             "--transition-type", "fade", "--transition-duration", "0.4"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _assign_wallpaper(self, ws_id: int) -> None:
        with self.lock:
            if ws_id in self.workspace_wallpapers:
                return
            used = set(self.workspace_wallpapers.values())
            available = [w for w in self.all_wallpapers if w not in used] or self.all_wallpapers
            self.workspace_wallpapers[ws_id] = random.choice(available)

    def _rotate(self) -> None:
        with self.lock:
            shuffled = self.all_wallpapers.copy()
            random.shuffle(shuffled)
            for i, ws_id in enumerate(self.workspace_outputs):
                self.workspace_wallpapers[ws_id] = shuffled[i % len(shuffled)]
            ws_ids = list(self.workspace_outputs.keys())
        for ws_id in ws_ids:
            self._apply(ws_id)
        self._schedule_rotation()

    def _schedule_rotation(self) -> None:
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.interval_seconds, self._rotate)
        self.timer.daemon = True
        self.timer.start()

    def __call__(self, name: str, data: dict) -> None:
        match name:
            case "WorkspacesChanged":
                with self.lock:
                    current_ids = set()
                    for ws in data["workspaces"]:
                        ws_id = ws["id"]
                        current_ids.add(ws_id)
                        if output := ws.get("output"):
                            self.workspace_outputs[ws_id] = output
                        if ws.get("is_focused"):
                            self.current_ws_id = ws_id
                    # cleanup removed
                    for ws_id in list(self.workspace_wallpapers):
                        if ws_id not in current_ids:
                            del self.workspace_wallpapers[ws_id]
                            self.workspace_outputs.pop(ws_id, None)

            case "WorkspaceActivated":
                if not data.get("focused"):
                    return
                ws_id = data["id"]
                with self.lock:
                    if self.current_ws_id == ws_id:
                        return
                    self.current_ws_id = ws_id
                self._assign_wallpaper(ws_id)
                self._apply(ws_id)


if __name__ == "__main__":
    wallpapers_dir = Path.home() / ".wallpaper"
    handlers = [TileManager(n=3)]
    if wallpapers_dir.is_dir():
        handlers.append(WallpaperManager(wallpapers_dir))

    with NiriRequests.connect() as conn:
        conn.subscribe(*handlers)
