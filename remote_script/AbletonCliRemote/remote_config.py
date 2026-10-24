from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
CONFIG_FILENAME = "remote_config.json"

_ENV_HOST = "ABLETON_CLI_REMOTE_HOST"
_ENV_PORT = "ABLETON_CLI_REMOTE_PORT"
_ENV_AUTH_TOKEN = "ABLETON_CLI_REMOTE_AUTH_TOKEN"

_ALLOWED_CONFIG_KEYS = frozenset({"host", "port", "auth_token"})


@dataclass(slots=True)
class RemoteConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    auth_token: str | None = None


def _validate_host(host: object) -> str:
    if not isinstance(host, str) or not host:
        raise ValueError(f"host must be a non-empty string, got {host!r}")
    return host


def _validate_port(port: object) -> int:
    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError(f"port must be an integer, got {port!r}")
    if not (1 <= port <= 65535):
        raise ValueError(f"port must be between 1 and 65535, got {port!r}")
    return port


def _validate_auth_token(auth_token: object) -> str | None:
    if auth_token is None:
        return None
    if not isinstance(auth_token, str) or not auth_token:
        raise ValueError(f"auth_token must be a non-empty string or null, got {auth_token!r}")
    return auth_token


def _load_config_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to read remote config file: {path}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"Remote config file root must be a JSON object: {path}")

    unknown = set(raw).difference(_ALLOWED_CONFIG_KEYS)
    if unknown:
        raise ValueError(f"Remote config file has unexpected keys: {sorted(unknown)} in {path}")

    return raw


def _parse_env_port(raw_port: str) -> int:
    try:
        return int(raw_port)
    except ValueError as exc:
        raise ValueError(f"{_ENV_PORT} must be an integer, got {raw_port!r}") from exc


def _load_env_values() -> dict[str, object]:
    values: dict[str, object] = {}

    host = os.environ.get(_ENV_HOST)
    if host is not None:
        values["host"] = host

    port = os.environ.get(_ENV_PORT)
    if port is not None:
        values["port"] = _parse_env_port(port)

    auth_token = os.environ.get(_ENV_AUTH_TOKEN)
    if auth_token is not None:
        values["auth_token"] = auth_token

    return values


def load_remote_config(package_dir: Path | None = None) -> RemoteConfig:
    """Resolve the Remote Script host/port/auth_token configuration.

    Precedence: environment variables > packaged remote_config.json > defaults.

    Invalid values (empty host, out-of-range port, non-string/empty auth_token,
    malformed JSON, or unknown config keys) fail explicitly with ValueError
    rather than silently falling back to defaults.
    """
    base_dir = package_dir if package_dir is not None else Path(__file__).resolve().parent
    file_values = _load_config_file(base_dir / CONFIG_FILENAME)
    env_values = _load_env_values()

    merged: dict[str, object] = {}
    merged.update(file_values)
    merged.update(env_values)

    host = _validate_host(merged.get("host", DEFAULT_HOST))
    port = _validate_port(merged.get("port", DEFAULT_PORT))
    auth_token = _validate_auth_token(merged.get("auth_token"))

    return RemoteConfig(host=host, port=port, auth_token=auth_token)
