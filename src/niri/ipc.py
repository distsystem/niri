"""Niri IPC socket communication."""

import json
import os
import socket
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
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

type EventHandler = Callable[[str, dict], None]


@dataclass
class NiriSocket:
    """Unix socket connection to niri compositor."""

    socket_path: str
    buffer_size: int = 4096
    _socket: socket.socket = field(init=False, repr=False)
    _msg_queue: deque[str] = field(default_factory=deque, init=False, repr=False)
    _incomplete: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.connect(self.socket_path)

    def close(self) -> None:
        self._socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        self.close()

    @classmethod
    def connect(cls):
        path = cls.get_socket_path()
        if not path:
            raise RuntimeError("NIRI_SOCKET not set")
        return cls(path)

    def _read_next(self) -> dict:
        if self._msg_queue:
            return json.loads(self._msg_queue.popleft())

        while True:
            resp_bytes = self._socket.recv(self.buffer_size)
            if not resp_bytes:
                return {}

            resp_str = self._incomplete + resp_bytes.decode("utf-8")
            self._incomplete = ""

            msg_list = resp_str.split("\n")
            self._incomplete = msg_list.pop()
            if msg_list:
                break

        out_msg = msg_list[0]
        self._msg_queue.extend(msg_list[1:])
        return json.loads(out_msg)

    def _send_string(self, string: str) -> None:
        self._socket.sendall(f'"{string}"\n'.encode("utf-8"))

    def _send_json(self, obj: dict) -> None:
        self._socket.sendall((json.dumps(obj) + "\n").encode("utf-8"))

    @staticmethod
    def get_socket_path() -> str | None:
        return os.environ.get("NIRI_SOCKET")


@dataclass
class NiriRequests(NiriSocket):
    """Request-response and event stream interface."""

    def request(self, message: str) -> tuple[bool, dict]:
        self._send_string(message)
        resp = self._read_next()
        is_ok = "Ok" in resp
        return is_ok, resp.get("Ok" if is_ok else "Err", {})

    def action(self, action_name: str, **params) -> tuple[bool, dict]:
        action_obj = {action_name: params} if params else action_name
        self._send_json({"Action": action_obj})
        resp = self._read_next()
        is_ok = "Ok" in resp
        return is_ok, resp.get("Ok" if is_ok else "Err", {})

    def read_eventstream(self) -> Iterator[tuple[str, dict]]:
        is_ok, resp = self.request("EventStream")
        if not is_ok:
            raise IOError(f"Failed to start EventStream: {resp}")

        while True:
            event = self._read_next()
            if not event:
                break
            name = next(iter(event.keys()))
            yield name, event.get(name)

    def subscribe(self, *handlers: EventHandler) -> None:
        for name, data in self.read_eventstream():
            for handler in handlers:
                handler(name, data)
