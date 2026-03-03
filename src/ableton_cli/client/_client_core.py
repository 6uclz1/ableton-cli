from __future__ import annotations

from typing import Any

from ..capabilities import read_only_remote_commands
from ..config import Settings
from ..errors import AppError, ExitCode, remote_error_to_app_error
from .protocol import make_request, parse_response
from .transport import RecordingTransport, ReplayTransport, TcpJsonlTransport


class _AbletonClientCore:
    def __init__(
        self,
        settings: Settings,
        *,
        record_path: str | None = None,
        replay_path: str | None = None,
        read_only: bool = False,
    ) -> None:
        self.settings = settings
        self.read_only = read_only
        self._read_only_commands = read_only_remote_commands()
        if record_path is not None and replay_path is not None:
            raise AppError(
                error_code="INVALID_ARGUMENT",
                message="--record and --replay cannot be used together",
                hint="Choose exactly one of --record or --replay.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )

        base_transport = TcpJsonlTransport(
            host=settings.host,
            port=settings.port,
            timeout_ms=settings.timeout_ms,
        )
        if replay_path is not None:
            self.transport = ReplayTransport(path=replay_path)
        elif record_path is not None:
            self.transport = RecordingTransport(inner=base_transport, path=record_path)
        else:
            self.transport = base_transport

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.read_only and name not in self._read_only_commands:
            raise AppError(
                error_code="READ_ONLY_VIOLATION",
                message=f"Command '{name}' is blocked in read-only mode",
                hint="Run without --read-only to execute write commands.",
                exit_code=ExitCode.EXECUTION_FAILED,
                details={"command": name},
            )

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

    def execute_remote_command(
        self,
        name: str,
        args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
