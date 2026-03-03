from __future__ import annotations

from typing import Any, Protocol

from ..config import Settings
from ..errors import AppError, ErrorCode, ExitCode, remote_error_to_app_error
from .protocol import make_request, parse_response
from .transport import JsonTransport, RecordingTransport, ReplayTransport, TcpJsonlTransport


class ClientBackend(Protocol):
    transport: JsonTransport

    def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]: ...


class _TransportBackend:
    def __init__(self, settings: Settings, transport: JsonTransport) -> None:
        self._settings = settings
        self.transport = transport

    def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        request = make_request(
            name=name,
            args=args,
            protocol_version=self._settings.protocol_version,
            meta={"request_timeout_ms": self._settings.timeout_ms},
        )
        raw_response = self.transport.send(request.to_dict())
        response = parse_response(
            payload=raw_response,
            expected_request_id=request.request_id,
            expected_protocol=self._settings.protocol_version,
        )

        if response.ok:
            if response.result is None:
                return {}
            return response.result

        if response.error is None:
            raise AppError(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Remote command failed without structured error payload",
                hint="Update Remote Script error handling.",
                exit_code=ExitCode.EXECUTION_FAILED,
            )

        raise remote_error_to_app_error(response.error)


class LiveBackendClient(_TransportBackend):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings,
            TcpJsonlTransport(
                host=settings.host,
                port=settings.port,
                timeout_ms=settings.timeout_ms,
            ),
        )


class RecordingClient(_TransportBackend):
    def __init__(self, settings: Settings, *, path: str) -> None:
        super().__init__(
            settings,
            RecordingTransport(
                inner=TcpJsonlTransport(
                    host=settings.host,
                    port=settings.port,
                    timeout_ms=settings.timeout_ms,
                ),
                path=path,
            ),
        )


class ReplayClient(_TransportBackend):
    def __init__(self, settings: Settings, *, path: str) -> None:
        super().__init__(
            settings,
            ReplayTransport(path=path),
        )
