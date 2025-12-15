"""Low-level socket communication with niri IPC."""

import json
import os
import socket
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass
class NiriSocket:
    """Unix socket connection to niri compositor."""

    socket_path: str
    buffer_size: int = 4096
    _socket: socket.socket = field(init=False, repr=False)
    _msg_queue: deque[str] = field(default_factory=deque, init=False, repr=False)
    _incomplete: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.socket_path:
            raise ValueError("Cannot connect to niri, no socket path given")
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.connect(self.socket_path)

    def close(self) -> None:
        self._socket.close()

    def _read_next(self) -> dict:
        """Read next JSON message from socket, handling buffering."""
        if self._msg_queue:
            return json.loads(self._msg_queue.popleft())

        while True:
            resp_bytes = self._socket.recv(self.buffer_size)
            if len(resp_bytes) == 0:
                return {}

            resp_str = resp_bytes.decode("utf-8")
            if self._incomplete is not None:
                resp_str = self._incomplete + resp_str
                self._incomplete = None

            msg_list = resp_str.split("\n")
            last_piece = msg_list.pop()
            self._incomplete = last_piece if last_piece else None
            if msg_list:
                break

        if not msg_list:
            raise IOError("Error reading next message (empty message list)")

        out_msg = msg_list[0]
        if len(msg_list) > 1:
            self._msg_queue.extend(msg_list[1:])

        return json.loads(out_msg)

    def _send_string(self, string: str) -> None:
        """Send a string request to niri."""
        self._socket.sendall(f'"{string}"\n'.encode("utf-8"))

    def _send_json(self, obj: dict) -> None:
        """Send a JSON object to niri."""
        self._socket.sendall((json.dumps(obj) + "\n").encode("utf-8"))

    @staticmethod
    def get_socket_path() -> str | None:
        """Get niri socket path from environment."""
        return os.environ.get("NIRI_SOCKET")


@dataclass
class NiriRequests(NiriSocket):
    """Request-response and event stream interface."""

    def request(self, message: str) -> tuple[bool, dict]:
        """Send request and return (is_ok, response_data)."""
        self._send_string(message)
        resp = self._read_next()
        is_ok = "Ok" in resp
        return is_ok, resp.get("Ok" if is_ok else "Err", {})

    def action(self, action_name: str, **params) -> tuple[bool, dict]:
        """Send action request."""
        action_obj = {action_name: params} if params else action_name
        self._send_json({"Action": action_obj})
        resp = self._read_next()
        is_ok = "Ok" in resp
        return is_ok, resp.get("Ok" if is_ok else "Err", {})

    def read_eventstream(self) -> Iterator[tuple[str, dict]]:
        """Start EventStream and yield (event_name, event_data) tuples."""
        is_ok, resp = self.request("EventStream")
        if not is_ok:
            raise IOError(f"Failed to start EventStream: {resp}")

        while True:
            event = self._read_next()
            if not event:
                break
            name = next(iter(event.keys()))
            yield name, event.get(name)
