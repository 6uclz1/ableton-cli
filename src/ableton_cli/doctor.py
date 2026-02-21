from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .capabilities import (
    missing_required_commands,
    parse_supported_commands,
    required_remote_commands,
)
from .client.ableton_client import AbletonClient
from .config import Settings
from .errors import AppError
from .installer import REMOTE_SCRIPT_DIR_NAME, remote_script_candidate_dirs


@dataclass(slots=True)
class DoctorCheck:
    name: str
    status: str
    hint: str | None
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "hint": self.hint,
            "details": self.details,
        }


def _pass(name: str, details: dict[str, Any]) -> DoctorCheck:
    return DoctorCheck(name=name, status="PASS", hint=None, details=details)


def _warn(name: str, hint: str, details: dict[str, Any]) -> DoctorCheck:
    return DoctorCheck(name=name, status="WARN", hint=hint, details=details)


def _fail(name: str, hint: str, details: dict[str, Any]) -> DoctorCheck:
    return DoctorCheck(name=name, status="FAIL", hint=hint, details=details)


def run_doctor(settings: Settings) -> dict[str, Any]:
    checks: list[DoctorCheck] = []

    config_path = Path(settings.config_path) if settings.config_path else None
    if config_path and config_path.exists():
        checks.append(_pass("config_file", {"path": str(config_path), "exists": True}))
    else:
        checks.append(
            _warn(
                "config_file",
                "Run 'ableton-cli config init' to create a config file.",
                {"path": str(config_path) if config_path else None, "exists": False},
            )
        )

    if 1 <= settings.port <= 65535:
        checks.append(
            _pass(
                "host_port",
                {"host": settings.host, "port": settings.port, "timeout_ms": settings.timeout_ms},
            )
        )
    else:
        checks.append(
            _fail(
                "host_port",
                "Fix host/port configuration before retrying.",
                {"host": settings.host, "port": settings.port, "timeout_ms": settings.timeout_ms},
            )
        )

    if settings.timeout_ms < 5000:
        checks.append(
            _warn(
                "timeout_ms",
                (
                    "Configured timeout is low for heavy/batch workflows. "
                    "Use --timeout-ms >= 5000 or run 'ableton-cli config set timeout_ms 15000'."
                ),
                {"timeout_ms": settings.timeout_ms, "recommended_min_timeout_ms": 5000},
            )
        )
    else:
        checks.append(_pass("timeout_ms", {"timeout_ms": settings.timeout_ms}))

    candidates = remote_script_candidate_dirs()
    installed_paths = [
        str(path / REMOTE_SCRIPT_DIR_NAME)
        for path in candidates
        if (path / REMOTE_SCRIPT_DIR_NAME).exists()
    ]
    if installed_paths:
        checks.append(_pass("remote_script_files", {"installed_paths": installed_paths}))
    else:
        checks.append(
            _warn(
                "remote_script_files",
                "Run 'ableton-cli install-remote-script --yes' to install the Remote Script.",
                {
                    "installed_paths": [],
                    "candidates": [str(path / REMOTE_SCRIPT_DIR_NAME) for path in candidates],
                },
            )
        )

    if installed_paths:
        invalid_entrypoints: list[str] = []
        valid_entrypoints: list[str] = []
        for installed_path in installed_paths:
            init_py = Path(installed_path) / "__init__.py"
            if not init_py.exists():
                invalid_entrypoints.append(f"{installed_path} (__init__.py missing)")
                continue

            try:
                init_source = init_py.read_text(encoding="utf-8")
            except OSError:
                invalid_entrypoints.append(f"{installed_path} (__init__.py unreadable)")
                continue

            if "def create_instance" not in init_source:
                invalid_entrypoints.append(f"{installed_path} (create_instance missing)")
            else:
                valid_entrypoints.append(installed_path)

        if invalid_entrypoints:
            checks.append(
                _fail(
                    "remote_script_entrypoint",
                    (
                        "Remote Script entrypoint is invalid. "
                        "Re-run 'ableton-cli install-remote-script --yes' and restart Ableton Live."
                    ),
                    {"invalid_paths": invalid_entrypoints, "valid_paths": valid_entrypoints},
                )
            )
        else:
            checks.append(
                _pass(
                    "remote_script_entrypoint",
                    {"valid_paths": valid_entrypoints},
                )
            )
    else:
        checks.append(
            _warn(
                "remote_script_entrypoint",
                "Entrypoint check skipped because Remote Script files were not found.",
                {},
            )
        )

    client = AbletonClient(settings)
    try:
        ping_result = client.ping()
        checks.append(
            _pass(
                "remote_ping",
                {
                    "host": settings.host,
                    "port": settings.port,
                    "protocol_version": ping_result.get("protocol_version"),
                    "remote_script_version": ping_result.get("remote_script_version"),
                },
            )
        )

        remote_protocol = ping_result.get("protocol_version")
        if remote_protocol != settings.protocol_version:
            checks.append(
                _fail(
                    "protocol_version",
                    (
                        "Align protocol_version between CLI and Remote Script "
                        "(use --protocol-version or 'ableton-cli config set protocol_version <n>')."
                    ),
                    {
                        "cli_protocol_version": settings.protocol_version,
                        "remote_protocol_version": remote_protocol,
                    },
                )
            )
        else:
            checks.append(
                _pass(
                    "protocol_version",
                    {
                        "cli_protocol_version": settings.protocol_version,
                        "remote_protocol_version": remote_protocol,
                    },
                )
            )

        try:
            supported_commands = parse_supported_commands(ping_result)
            missing_commands = missing_required_commands(supported_commands)
            details = {
                "required_command_count": len(required_remote_commands()),
                "supported_command_count": len(supported_commands),
                "missing_commands": missing_commands,
                "supported_commands": sorted(supported_commands),
                "command_set_hash": ping_result.get("command_set_hash"),
            }
            if missing_commands:
                checks.append(
                    _fail(
                        "remote_capabilities",
                        (
                            "Remote Script command set is incomplete. "
                            "Reinstall Remote Script and restart Ableton Live."
                        ),
                        details,
                    )
                )
            else:
                checks.append(_pass("remote_capabilities", details))
        except AppError as exc:
            checks.append(
                _fail(
                    "remote_capabilities",
                    exc.hint
                    or "Remote Script capability payload is incompatible with this CLI version.",
                    {
                        "error_code": exc.error_code,
                        "message": exc.message,
                        "supported_commands": [],
                    },
                )
            )

    except AppError as exc:
        checks.append(
            _fail(
                "remote_ping",
                exc.hint or "Start Ableton Live and enable the Remote Script.",
                {
                    "error_code": exc.error_code,
                    "message": exc.message,
                    "host": settings.host,
                    "port": settings.port,
                },
            )
        )
        checks.append(
            _warn(
                "protocol_version",
                "Protocol check skipped because remote endpoint was unreachable.",
                {
                    "cli_protocol_version": settings.protocol_version,
                },
            )
        )
        checks.append(
            _warn(
                "remote_capabilities",
                "Capability check skipped because remote endpoint was unreachable.",
                {},
            )
        )

    counts = {
        "pass": sum(1 for check in checks if check.status == "PASS"),
        "warn": sum(1 for check in checks if check.status == "WARN"),
        "fail": sum(1 for check in checks if check.status == "FAIL"),
    }

    return {
        "summary": counts,
        "checks": [check.to_dict() for check in checks],
    }
