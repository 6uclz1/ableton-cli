from __future__ import annotations

from typing import Any

from ..capabilities import read_only_remote_commands
from ..config import Settings
from ..errors import AppError, ErrorCode, ExitCode
from .backends import ClientBackend, LiveBackendClient, RecordingClient, ReplayClient


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
                error_code=ErrorCode.INVALID_ARGUMENT,
                message="--record and --replay cannot be used together",
                hint="Choose exactly one of --record or --replay.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )

        self._backend = self._build_backend(
            settings=settings,
            record_path=record_path,
            replay_path=replay_path,
        )
        # Keep direct transport access available for tests and fixtures.
        self.transport = self._backend.transport

    @staticmethod
    def _build_backend(
        *,
        settings: Settings,
        record_path: str | None,
        replay_path: str | None,
    ) -> ClientBackend:
        if replay_path is not None:
            return ReplayClient(settings, path=replay_path)
        if record_path is not None:
            return RecordingClient(settings, path=record_path)
        return LiveBackendClient(settings)

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.read_only and name not in self._read_only_commands:
            raise AppError(
                error_code=ErrorCode.READ_ONLY_VIOLATION,
                message=f"Command '{name}' is blocked in read-only mode",
                hint="Run without --read-only to execute write commands.",
                exit_code=ExitCode.EXECUTION_FAILED,
                details={"command": name},
            )
        return self._backend.dispatch(name, args)

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
