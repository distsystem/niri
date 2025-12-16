#!/usr/bin/env python
"""Test script demonstrating niri IPC with multiple handlers."""

import logging
import random
import subprocess
import threading
from pathlib import Path

from niri import NiriRequests, logger

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


class TileManager:
    """Auto-tile windows when count <= N per workspace."""

    def __init__(self, n: int = 3, maximize_solos: bool = True):
        self.n = n
        self.maximize_solos = maximize_solos
        self.win_state: dict[int, dict] = {}
        self.wspace_state: dict[int, dict] = {}

    def _action(self, action_name: str, **params) -> tuple[bool, dict]:
        """Send action via separate connection (event stream blocks responses)."""
        with NiriRequests.connect() as conn:
            return conn.action(action_name, **params)

    def _set_width(self, wid: int, percent: float) -> None:
        ok, resp = self._action("SetWindowWidth", id=wid, change={"SetProportion": percent})
        logger.debug("SetWindowWidth wid=%d pct=%.0f%% -> ok=%s resp=%s", wid, percent, ok, resp)

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

                logger.debug(
                    "WindowOpenedOrChanged wid=%d is_new=%s floating=%s app=%s",
                    wid, is_new, win["is_floating"], win.get("app_id"),
                )

                if not is_new or win["is_floating"]:
                    return

                tiled = self._get_tiled_windows(win["workspace_id"])
                count = len(tiled)
                logger.info("New tiled window wid=%d, total tiled=%d", wid, count)

                if count == 1 and self.maximize_solos:
                    logger.info("Solo window -> 100%%")
                    self._set_width(wid, 100)
                elif count == 2:
                    logger.info("Two windows -> 50%% each")
                    for w in tiled:
                        self._set_width(w, 50)
                elif 2 < count <= self.n:
                    col = self._get_col_idx(win)
                    action = "ConsumeOrExpelWindowRight" if col == 2 else "ConsumeOrExpelWindowLeft"
                    logger.info("Consume/expel col=%s action=%s", col, action)
                    ok, resp = self._action(action, id=wid)
                    logger.debug("ConsumeOrExpel -> ok=%s resp=%s", ok, resp)

            case "WindowClosed":
                wid = data["id"]
                closed = self.win_state.pop(wid, None)
                logger.debug("WindowClosed wid=%d found=%s", wid, closed is not None)
                if not closed:
                    return

                tiled = self._get_tiled_windows(closed["workspace_id"])
                logger.debug("After close: tiled=%d", len(tiled))
                if len(tiled) == 1 and self.maximize_solos:
                    remaining = next(iter(tiled))
                    logger.info("One remaining -> 100%% wid=%d", remaining)
                    self._set_width(remaining, 100)

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
    tile_manager = TileManager(n=3)
    handlers: list = [tile_manager]
    if wallpapers_dir.is_dir():
        handlers.append(WallpaperManager(wallpapers_dir))

    logger.info("Starting handlers: %s", [type(h).__name__ for h in handlers])
    with NiriRequests.connect() as conn:
        logger.info("Connected, subscribing to events...")
        conn.subscribe(*handlers)
