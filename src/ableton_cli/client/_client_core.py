from __future__ import annotations

from typing import Any

from ..config import Settings
from ..errors import AppError, ExitCode, remote_error_to_app_error
from .protocol import make_request, parse_response
from .transport import TcpJsonlTransport


class _AbletonClientCore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.transport = TcpJsonlTransport(
            host=settings.host,
            port=settings.port,
            timeout_ms=settings.timeout_ms,
        )

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        request = make_request(
            name=name,
            args=args,
            protocol_version=self.settings.protocol_version,
            meta={"request_timeout_ms": self.settings.timeout_ms},
        )
        raw_response = self.transport.send(request.to_dict())
        response = parse_response(
            payload=raw_response,
            expected_request_id=request.request_id,
            expected_protocol=self.settings.protocol_version,
        )

        if response.ok:
            if response.result is None:
                return {}
            return response.result

        if response.error is None:
            raise AppError(
                error_code="INTERNAL_ERROR",
                message="Remote command failed without structured error payload",
                hint="Update Remote Script error handling.",
                exit_code=ExitCode.EXECUTION_FAILED,
            )

        raise remote_error_to_app_error(response.error)

    def _call(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {} if args is None else dict(args)
        return self._dispatch(name, payload)

    @staticmethod
    def _add_if_not_none(args: dict[str, Any], key: str, value: Any) -> None:
        if value is not None:
            args[key] = value

    def _build_clip_note_args(
        self,
        *,
        track: int,
        clip: int,
        notes: list[dict[str, Any]] | None,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "clip": clip}
        self._add_if_not_none(args, "notes", notes)
        self._add_if_not_none(args, "start_time", start_time)
        self._add_if_not_none(args, "end_time", end_time)
        self._add_if_not_none(args, "pitch", pitch)
        return args

    def _call_parameter_command(
        self,
        command_name: str,
        *,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        return self._call(
            command_name,
            {
                "track": track,
                "device": device,
                "parameter": parameter,
                "value": value,
            },
        )
