from __future__ import annotations

from pathlib import Path

from ableton_cli.capabilities import compute_command_set_hash, required_remote_commands
from ableton_cli.config import Settings
from ableton_cli.doctor import run_doctor
from ableton_cli.errors import AppError, ExitCode


class _PlatformPathsStub:
    def __init__(self, candidates: list[str] | None = None) -> None:
        self._candidates = [Path(path) for path in (candidates or [])]

    def remote_script_candidate_dirs(self) -> list[Path]:
        return self._candidates

    def claude_home_dir(self) -> Path:
        return Path("/unused")

    def cursor_home_dir(self) -> Path:
        return Path("/unused")


class _ClientStub:
    def __init__(self, ping_payload: dict[str, object] | None = None) -> None:
        self._ping_payload = ping_payload

    def ping(self):  # noqa: ANN201
        if self._ping_payload is not None:
            return self._ping_payload
        raise AppError(
            error_code="ABLETON_NOT_REACHABLE",
            message="not reachable",
            hint="start ableton",
            exit_code=ExitCode.ABLETON_NOT_CONNECTED,
        )


def test_doctor_handles_unreachable_remote(monkeypatch) -> None:
    monkeypatch.setattr("ableton_cli.doctor.AbletonClient", lambda settings: _ClientStub())

    result = run_doctor(
        Settings(
            host="127.0.0.1",
            port=8765,
            timeout_ms=2000,
            log_level="INFO",
            log_file=None,
            protocol_version=2,
            config_path="/tmp/not-found.toml",
        ),
        platform_paths=_PlatformPathsStub(),
    )

    assert "summary" in result
    assert "checks" in result
    checks = {item["name"]: item for item in result["checks"]}
    assert checks["remote_ping"]["status"] == "FAIL"
    assert "start ableton" in checks["remote_ping"]["hint"].lower()
    assert checks["timeout_ms"]["status"] == "WARN"


def test_doctor_fails_when_ping_has_no_supported_commands(monkeypatch) -> None:
    ping_payload = {
        "protocol_version": 2,
        "remote_script_version": "0.2.0",
    }
    monkeypatch.setattr(
        "ableton_cli.doctor.AbletonClient",
        lambda settings: _ClientStub(ping_payload=ping_payload),
    )

    result = run_doctor(
        Settings(
            host="127.0.0.1",
            port=8765,
            timeout_ms=2000,
            log_level="INFO",
            log_file=None,
            protocol_version=2,
            config_path="/tmp/not-found.toml",
        ),
        platform_paths=_PlatformPathsStub(),
    )

    checks = {item["name"]: item for item in result["checks"]}
    assert checks["remote_ping"]["status"] == "PASS"
    assert checks["remote_capabilities"]["status"] == "FAIL"
    assert checks["remote_capabilities"]["details"]["supported_commands"] == []


def test_doctor_fails_when_remote_is_missing_required_commands(monkeypatch) -> None:
    supported_commands = ["ping", "transport_play"]
    ping_payload = {
        "protocol_version": 2,
        "remote_script_version": "0.2.0",
        "supported_commands": supported_commands,
        "command_set_hash": compute_command_set_hash(supported_commands),
    }
    monkeypatch.setattr(
        "ableton_cli.doctor.AbletonClient",
        lambda settings: _ClientStub(ping_payload=ping_payload),
    )

    result = run_doctor(
        Settings(
            host="127.0.0.1",
            port=8765,
            timeout_ms=2000,
            log_level="INFO",
            log_file=None,
            protocol_version=2,
            config_path="/tmp/not-found.toml",
        ),
        platform_paths=_PlatformPathsStub(),
    )

    checks = {item["name"]: item for item in result["checks"]}
    assert checks["remote_capabilities"]["status"] == "FAIL"
    missing = checks["remote_capabilities"]["details"]["missing_commands"]
    assert "get_clip_notes" in missing
    assert len(missing) == len(required_remote_commands()) - len(supported_commands)


def test_doctor_protocol_mismatch_hint_mentions_protocol_setter(monkeypatch) -> None:
    supported_commands = sorted(required_remote_commands())
    ping_payload = {
        "protocol_version": 99,
        "remote_script_version": "0.2.0",
        "supported_commands": supported_commands,
        "command_set_hash": compute_command_set_hash(supported_commands),
    }
    monkeypatch.setattr(
        "ableton_cli.doctor.AbletonClient",
        lambda settings: _ClientStub(ping_payload=ping_payload),
    )

    result = run_doctor(
        Settings(
            host="127.0.0.1",
            port=8765,
            timeout_ms=15000,
            log_level="INFO",
            log_file=None,
            protocol_version=2,
            config_path="/tmp/not-found.toml",
        ),
        platform_paths=_PlatformPathsStub(),
    )
    checks = {item["name"]: item for item in result["checks"]}
    assert checks["protocol_version"]["status"] == "FAIL"
    assert "config set protocol_version" in (checks["protocol_version"]["hint"] or "")
