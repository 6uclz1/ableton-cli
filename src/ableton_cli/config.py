from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import tomli
from platformdirs import user_config_dir

from .errors import AppError, ExitCode

ENV_PREFIX = "ABLETON_CLI_"


@dataclass(slots=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8765
    timeout_ms: int = 15000
    log_level: str = "INFO"
    log_file: str | None = None
    protocol_version: int = 2
    config_path: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


DEFAULT_SETTINGS = Settings()
CONFIG_SET_KEYS = frozenset({"host", "port", "timeout_ms", "protocol_version"})


def default_config_path() -> Path:
    return Path(user_config_dir("ableton-cli", "ableton-cli")) / "config.toml"


def parse_env() -> dict[str, Any]:
    return {
        "host": os.getenv(f"{ENV_PREFIX}HOST"),
        "port": os.getenv(f"{ENV_PREFIX}PORT"),
        "timeout_ms": os.getenv(f"{ENV_PREFIX}TIMEOUT_MS"),
        "log_level": os.getenv(f"{ENV_PREFIX}LOG_LEVEL"),
        "log_file": os.getenv(f"{ENV_PREFIX}LOG_FILE"),
        "protocol_version": os.getenv(f"{ENV_PREFIX}PROTOCOL_VERSION"),
    }


def _normalize_int(name: str, value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"Invalid integer for '{name}': {value}",
            hint="Fix the config value or pass a valid CLI option.",
            exit_code=ExitCode.CONFIG_INVALID,
        ) from exc


def _normalize_str(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"Invalid string for '{name}': {value}",
            hint="Fix the config value or pass a valid CLI option.",
            exit_code=ExitCode.CONFIG_INVALID,
        )
    return value


def _load_file_values(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        raw = tomli.loads(path.read_text(encoding="utf-8"))
    except (tomli.TOMLDecodeError, OSError) as exc:
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"Failed to read config file: {path}",
            hint="Check the TOML syntax and file permissions.",
            exit_code=ExitCode.CONFIG_INVALID,
        ) from exc

    if not isinstance(raw, dict):
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"Config file root must be a table: {path}",
            hint="Use key/value pairs at the top level.",
            exit_code=ExitCode.CONFIG_INVALID,
        )

    return raw


def _settings_from_merged(merged: dict[str, Any], *, resolved_path: Path) -> Settings:
    host = _normalize_str("host", merged["host"]) if "host" in merged else DEFAULT_SETTINGS.host
    port = _normalize_int("port", merged["port"]) if "port" in merged else DEFAULT_SETTINGS.port
    timeout_ms = (
        _normalize_int("timeout_ms", merged["timeout_ms"])
        if "timeout_ms" in merged
        else DEFAULT_SETTINGS.timeout_ms
    )
    log_level = (
        _normalize_str("log_level", merged["log_level"])
        if "log_level" in merged
        else DEFAULT_SETTINGS.log_level
    )
    log_file = (
        _normalize_str("log_file", merged["log_file"])
        if "log_file" in merged and merged["log_file"] is not None
        else None
    )
    protocol_version = (
        _normalize_int("protocol_version", merged["protocol_version"])
        if "protocol_version" in merged
        else DEFAULT_SETTINGS.protocol_version
    )

    if not host:
        raise AppError(
            error_code="CONFIG_INVALID",
            message="host must not be empty",
            hint="Set host to a reachable IP or hostname.",
            exit_code=ExitCode.CONFIG_INVALID,
        )
    if not (1 <= port <= 65535):
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"port out of range: {port}",
            hint="Use a port between 1 and 65535.",
            exit_code=ExitCode.CONFIG_INVALID,
        )
    if timeout_ms <= 0:
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"timeout_ms must be positive: {timeout_ms}",
            hint="Use a positive timeout in milliseconds.",
            exit_code=ExitCode.CONFIG_INVALID,
        )
    if protocol_version <= 0:
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"protocol_version must be positive: {protocol_version}",
            hint="Set protocol_version to 2.",
            exit_code=ExitCode.CONFIG_INVALID,
        )

    return Settings(
        host=host,
        port=port,
        timeout_ms=timeout_ms,
        log_level=log_level,
        log_file=log_file,
        protocol_version=protocol_version,
        config_path=str(resolved_path),
    )


def _serialize_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    raise AppError(
        error_code="CONFIG_INVALID",
        message=f"Unsupported value type for config serialization: {type(value).__name__}",
        hint="Use scalar TOML values for config entries.",
        exit_code=ExitCode.CONFIG_INVALID,
    )


def _render_config_content(values: dict[str, Any]) -> str:
    ordered_keys = ["host", "port", "timeout_ms", "log_level", "log_file", "protocol_version"]
    lines: list[str] = []

    for key in ordered_keys:
        if key not in values:
            continue
        value = values[key]
        if value is None:
            continue
        lines.append(f"{key} = {_serialize_toml_value(value)}")

    for key in sorted(values):
        if key in ordered_keys:
            continue
        value = values[key]
        if value is None:
            continue
        lines.append(f"{key} = {_serialize_toml_value(value)}")

    lines.append("")
    return "\n".join(lines)


def resolve_settings(
    cli_overrides: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> Settings:
    cli_overrides = cli_overrides or {}
    resolved_path = config_path or default_config_path()

    file_values = _load_file_values(resolved_path)
    env_values = parse_env()

    merged: dict[str, Any] = {}
    merged.update(file_values)
    merged.update({k: v for k, v in env_values.items() if v is not None})
    merged.update({k: v for k, v in cli_overrides.items() if v is not None})
    return _settings_from_merged(merged, resolved_path=resolved_path)


def render_default_config() -> str:
    return "\n".join(
        [
            'host = "127.0.0.1"',
            "port = 8765",
            "timeout_ms = 15000",
            'log_level = "INFO"',
            "protocol_version = 2",
            "",
        ]
    )


def init_config_file(path: Path, dry_run: bool = False) -> dict[str, Any]:
    content = render_default_config()
    existed = path.exists()
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return {
        "path": str(path),
        "existed": existed,
        "written": not dry_run,
        "dry_run": dry_run,
    }


def update_config_value(path: Path, *, key: str, value: Any) -> dict[str, Any]:
    if key not in CONFIG_SET_KEYS:
        allowed = ", ".join(sorted(CONFIG_SET_KEYS))
        raise AppError(
            error_code="CONFIG_INVALID",
            message=f"Unsupported config key for updates: {key}",
            hint=f"Use one of: {allowed}",
            exit_code=ExitCode.CONFIG_INVALID,
        )

    existing = _load_file_values(path)
    merged = dict(existing)
    merged[key] = value
    settings = _settings_from_merged(merged, resolved_path=path)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_config_content(merged), encoding="utf-8")

    return {
        "path": str(path),
        "key": key,
        "value": settings.to_public_dict()[key],
        "settings": settings.to_public_dict(),
    }
