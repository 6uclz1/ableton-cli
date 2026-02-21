from __future__ import annotations

from typing import Annotated

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    require_minus_one_or_non_negative,
    require_non_empty_string,
    require_non_negative,
)

scenes_app = typer.Typer(help="Scenes commands", no_args_is_help=True)
name_app = typer.Typer(help="Scenes naming commands", no_args_is_help=True)


@scenes_app.command("list")
def scenes_list(ctx: typer.Context) -> None:
    execute_command(
        ctx,
        command="scenes list",
        args={},
        action=lambda: get_client(ctx).scenes_list(),
    )


@scenes_app.command("create")
def scenes_create(
    ctx: typer.Context,
    index: Annotated[
        int,
        typer.Option(
            "--index",
            help="Insert index (-1 for append)",
        ),
    ] = -1,
) -> None:
    def _run() -> dict[str, object]:
        valid_index = require_minus_one_or_non_negative(
            "index",
            index,
            hint="Use -1 for append or a non-negative insertion index.",
        )
        return get_client(ctx).create_scene(valid_index)

    execute_command(
        ctx,
        command="scenes create",
        args={"index": index},
        action=_run,
    )


@name_app.command("set")
def scenes_name_set(
    ctx: typer.Context,
    scene: Annotated[int, typer.Argument(help="Scene index (0-based)")],
    name: Annotated[str, typer.Argument(help="New scene name")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative("scene", scene, hint="Use a valid scene index from 'scenes list'.")
        valid_name = require_non_empty_string("name", name, hint="Pass a non-empty scene name.")
        return get_client(ctx).set_scene_name(scene, valid_name)

    execute_command(
        ctx,
        command="scenes name set",
        args={"scene": scene, "name": name},
        action=_run,
    )


@scenes_app.command("fire")
def scenes_fire(
    ctx: typer.Context,
    scene: Annotated[int, typer.Argument(help="Scene index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative("scene", scene, hint="Use a valid scene index from 'scenes list'.")
        return get_client(ctx).fire_scene(scene)

    execute_command(
        ctx,
        command="scenes fire",
        args={"scene": scene},
        action=_run,
    )


@scenes_app.command("move")
def scenes_move(
    ctx: typer.Context,
    from_scene: Annotated[int, typer.Argument(help="Source scene index (0-based)")],
    to_scene: Annotated[int, typer.Argument(help="Destination scene index (0-based)")],
) -> None:
    def _run() -> dict[str, object]:
        require_non_negative(
            "from",
            from_scene,
            hint="Use a valid source scene index from 'scenes list'.",
        )
        require_non_negative(
            "to",
            to_scene,
            hint="Use a valid destination scene index from 'scenes list'.",
        )
        return get_client(ctx).scenes_move(from_scene, to_scene)

    execute_command(
        ctx,
        command="scenes move",
        args={"from": from_scene, "to": to_scene},
        action=_run,
    )


scenes_app.add_typer(name_app, name="name")


def register(app: typer.Typer) -> None:
    app.add_typer(scenes_app, name="scenes")
