from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend, CommandError, RemoteErrorCode
from .command_backend_handlers_batch import make_execute_batch_handler
from .command_backend_handlers_browser import BROWSER_HANDLERS
from .command_backend_handlers_devices import DEVICE_HANDLERS
from .command_backend_handlers_song_transport import SONG_TRANSPORT_HANDLERS
from .command_backend_handlers_tracks_clips import TRACKS_CLIPS_HANDLERS

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _supported_command_names() -> list[str]:
    return sorted(_HANDLERS.keys())


def _command_set_hash(commands: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update("\n".join(commands).encode("utf-8"))
    return digest.hexdigest()


def _handle_ping(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    result = dict(backend.ping_info())
    supported_commands = _supported_command_names()
    result["supported_commands"] = supported_commands
    result["command_set_hash"] = _command_set_hash(supported_commands)
    return result


def _build_handlers() -> dict[str, Handler]:
    handlers: dict[str, Handler] = {
        "ping": _handle_ping,
    }
    handlers.update(SONG_TRANSPORT_HANDLERS)
    handlers.update(TRACKS_CLIPS_HANDLERS)
    handlers.update(BROWSER_HANDLERS)
    handlers.update(DEVICE_HANDLERS)
    handlers["execute_batch"] = make_execute_batch_handler(dispatch_command)
    return handlers


def dispatch_command(backend: CommandBackend, name: str, args: dict[str, Any]) -> dict[str, Any]:
    handler = _HANDLERS.get(name)
    if handler is None:
        raise CommandError(
            code=RemoteErrorCode.INVALID_ARGUMENT,
            message=f"Unknown command: {name}",
            hint="Use a supported command name.",
        )
    return handler(backend, args)


_HANDLERS: dict[str, Handler] = {}
_HANDLERS.update(_build_handlers())
