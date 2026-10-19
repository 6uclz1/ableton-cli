from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ..music_theory import root_pitch_class
from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command as run_client_command_shared
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared
from ._validation import invalid_argument, require_non_empty_string

song_app = typer.Typer(help="Song and session information", no_args_is_help=True)
song_export_app = typer.Typer(help="Song export commands", no_args_is_help=True)
song_scale_app = typer.Typer(help="Song scale commands", no_args_is_help=True)


SongCommandSpec = CommandSpec


SONG_INFO_SPEC = SongCommandSpec(
    command_name="song info",
    client_method="song_info",
)
SONG_NEW_SPEC = SongCommandSpec(
    command_name="song new",
    client_method="song_new",
)
SONG_UNDO_SPEC = SongCommandSpec(
    command_name="song undo",
    client_method="song_undo",
)
SONG_REDO_SPEC = SongCommandSpec(
    command_name="song redo",
    client_method="song_redo",
)
SONG_SAVE_SPEC = SongCommandSpec(
    command_name="song save",
    client_method="song_save",
)
SONG_SCALE_GET_SPEC = SongCommandSpec(
    command_name="song scale get",
    client_method="song_scale_get",
)
SONG_SCALE_SET_SPEC = SongCommandSpec(
    command_name="song scale set",
    client_method="song_scale_set",
)
SONG_EXPORT_AUDIO_SPEC = SongCommandSpec(
    command_name="song export audio",
    client_method="song_export_audio",
)


def run_client_command(
    ctx: typer.Context,
    *,
    command_name: str,
    args: dict[str, object],
    fn: Callable[[object], dict[str, object]],
) -> None:
    run_client_command_shared(
        ctx,
        command_name=command_name,
        args=args,
        fn=fn,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: SongCommandSpec,
    args: dict[str, object],
    method_kwargs: dict[str, object] | Callable[[], dict[str, object]] | None = None,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args=args,
        method_kwargs=method_kwargs,
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


@song_app.command("info")
def song_info(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=SONG_INFO_SPEC,
        args={},
    )


@song_app.command("new")
def song_new(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=SONG_NEW_SPEC,
        args={},
    )


@song_app.command("undo")
def song_undo(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=SONG_UNDO_SPEC,
        args={},
    )


@song_app.command("redo")
def song_redo(ctx: typer.Context) -> None:
    run_client_command_spec(
        ctx,
        spec=SONG_REDO_SPEC,
        args={},
    )


@song_app.command("save")
def song_save(
    ctx: typer.Context,
    path: Annotated[str, typer.Option("--path", help="Destination .als path")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_path = require_non_empty_string(
            "path",
            path,
            hint="Pass a non-empty --path for the destination .als file.",
        )
        return {"path": valid_path}

    run_client_command_spec(
        ctx,
        spec=SONG_SAVE_SPEC,
        args={"path": path},
        method_kwargs=_method_kwargs,
    )


@song_export_app.command("audio")
def song_export_audio(
    ctx: typer.Context,
    path: Annotated[str, typer.Option("--path", help="Destination audio path (for example .wav)")],
) -> None:
    def _method_kwargs() -> dict[str, object]:
        valid_path = require_non_empty_string(
            "path",
            path,
            hint="Pass a non-empty --path for exported audio.",
        )
        return {"path": valid_path}

    run_client_command_spec(
        ctx,
        spec=SONG_EXPORT_AUDIO_SPEC,
        args={"path": path},
        method_kwargs=_method_kwargs,
    )


def _parse_root_note(root: str) -> int:
    stripped = root.strip()
    if stripped.lstrip("-").isdigit():
        value = int(stripped)
        if not 0 <= value <= 11:
            raise invalid_argument(
                message=f"root must be 0..11 or a note name, got {root}",
                hint="Use a pitch class 0..11 (0 = C) or a note name such as C, F#, Bb.",
            )
        return value
    try:
        return root_pitch_class(stripped)
    except ValueError as exc:
        raise invalid_argument(
            message=f"Unknown root note: {root}",
            hint="Use a pitch class 0..11 (0 = C) or a note name such as C, F#, Bb.",
        ) from exc


@song_scale_app.command("get")
def song_scale_get(ctx: typer.Context) -> None:
    """Read the Set's root note, scale name and Scale Mode."""
    run_client_command_spec(ctx, spec=SONG_SCALE_GET_SPEC, args={})


@song_scale_app.command("set")
def song_scale_set(
    ctx: typer.Context,
    root: Annotated[
        str | None, typer.Option("--root", help="Root note: 0..11 or a name like C, F#, Bb")
    ] = None,
    name: Annotated[
        str | None, typer.Option("--name", help="Scale name as shown in Live, e.g. Minor")
    ] = None,
    mode: Annotated[
        bool | None, typer.Option("--mode/--no-mode", help="Turn Scale Mode on or off")
    ] = None,
) -> None:
    """Change the Set's scale, which scale-aware devices such as Auto Shift can follow."""

    def _method_kwargs() -> dict[str, object]:
        if root is None and name is None and mode is None:
            raise invalid_argument(
                message="song scale set requires at least one of --root, --name, --mode",
                hint="Pass the scale fields to change.",
            )
        scale_name = (
            None
            if name is None
            else require_non_empty_string("name", name, hint="Pass a non-empty scale name.")
        )
        return {
            "root_note": None if root is None else _parse_root_note(root),
            "scale_name": scale_name,
            "scale_mode": mode,
        }

    run_client_command_spec(
        ctx,
        spec=SONG_SCALE_SET_SPEC,
        args={"root": root, "name": name, "mode": mode},
        method_kwargs=_method_kwargs,
    )


song_app.add_typer(song_export_app, name="export")
song_app.add_typer(song_scale_app, name="scale")


def register(app: typer.Typer) -> None:
    app.add_typer(song_app, name="song")
