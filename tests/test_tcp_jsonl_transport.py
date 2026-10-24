from __future__ import annotations

import json
import socket
import threading
from collections.abc import Iterator

import pytest

from ableton_cli.client.transport import TcpJsonlTransport, socket_timeout_ms


class _FakeJsonlServer:
    """A minimal threaded TCP JSONL echo server used to observe connection reuse."""

    def __init__(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(1)
        self.port = self._socket.getsockname()[1]
        self.accept_count = 0
        self._connections: list[socket.socket] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        self._socket.settimeout(0.1)
        while not self._stop.is_set():
            try:
                conn, _addr = self._socket.accept()
            except TimeoutError:
                continue
            self.accept_count += 1
            self._connections.append(conn)
            threading.Thread(target=self._handle_connection, args=(conn,), daemon=True).start()

    def _handle_connection(self, conn: socket.socket) -> None:
        with conn, conn.makefile("rwb") as file_obj:
            while True:
                raw = file_obj.readline()
                if not raw:
                    return
                request = json.loads(raw.decode("utf-8"))
                response = {
                    "ok": True,
                    "request_id": request.get("request_id"),
                    "protocol_version": request.get("protocol_version"),
                    "result": {"echo": request.get("name")},
                    "error": None,
                }
                file_obj.write((json.dumps(response) + "\n").encode("utf-8"))
                file_obj.flush()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        for conn in self._connections:
            try:
                conn.close()
            except OSError:
                pass
        self._socket.close()


@pytest.fixture
def fake_server() -> Iterator[_FakeJsonlServer]:
    server = _FakeJsonlServer()
    try:
        yield server
    finally:
        server.stop()


def _request(request_id: str, name: str = "ping") -> dict[str, object]:
    return {
        "type": "command",
        "name": name,
        "args": {},
        "meta": {},
        "request_id": request_id,
        "protocol_version": 2,
    }


def test_send_reuses_a_single_connection_across_calls(fake_server: _FakeJsonlServer) -> None:
    transport = TcpJsonlTransport(host="127.0.0.1", port=fake_server.port, timeout_ms=2000)
    try:
        first = transport.send(_request("request-1"))
        second = transport.send(_request("request-2"))
    finally:
        transport.close()

    assert first["result"] == {"echo": "ping"}
    assert second["result"] == {"echo": "ping"}
    assert fake_server.accept_count == 1


def test_socket_read_deadline_outlives_the_request_deadline() -> None:
    transport = TcpJsonlTransport(host="127.0.0.1", port=1, timeout_ms=5000)

    assert transport.request_timeout_s == 5.0
    assert transport.socket_timeout_s > transport.request_timeout_s


def test_socket_timeout_is_derived_in_one_place() -> None:
    transport = TcpJsonlTransport(host="127.0.0.1", port=1, timeout_ms=5000)

    assert transport.socket_timeout_s == socket_timeout_ms(5000) / 1000


def test_established_socket_uses_the_grace_extended_deadline(
    fake_server: _FakeJsonlServer,
) -> None:
    transport = TcpJsonlTransport(host="127.0.0.1", port=fake_server.port, timeout_ms=2000)
    try:
        transport.send(_request("request-1"))
        assert transport._sock is not None
        assert transport._sock.gettimeout() == transport.socket_timeout_s
    finally:
        transport.close()


def test_close_then_send_opens_a_new_connection(fake_server: _FakeJsonlServer) -> None:
    transport = TcpJsonlTransport(host="127.0.0.1", port=fake_server.port, timeout_ms=2000)
    try:
        transport.send(_request("request-1"))
        transport.close()
        transport.send(_request("request-2"))
    finally:
        transport.close()

    assert fake_server.accept_count == 2
