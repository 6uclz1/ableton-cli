from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Annotated, TypeVar

import typer

from ..runtime import execute_command, get_client
from ._validation import (
    require_scene_and_name,
    require_scene_and_value,
    require_scene_index,
    require_scene_insert_index,
    require_scene_move,
)

scenes_app = typer.Typer(help="Scenes commands", no_args_is_help=True)
name_app = typer.Typer(help="Scenes naming commands", no_args_is_help=True)

TValue = TypeVar("TValue")

SceneValidator = Callable[[int], int]
SceneValueValidator = Callable[[int, TValue], tuple[int, TValue]]
SceneMoveValidator = Callable[[int, int], tuple[int, int]]

SceneAction = Callable[[object, int], dict[str, object]]
SceneValueAction = Callable[[object, int, TValue], dict[str, object]]
SceneMoveAction = Callable[[object, int, int], dict[str, object]]


def run_scene_command(
    ctx: typer.Context,
    *,
    command_name: str,
    scene: int,
    fn: SceneAction,
    validators: Sequence[SceneValidator] | None = None,
) -> None:
    active_validators = validators if validators is not None else (require_scene_index,)

    def _run() -> dict[str, object]:
        valid_scene = scene
        for validator in active_validators:
            valid_scene = validator(valid_scene)
        client = get_client(ctx)
        return fn(client, valid_scene)

    execute_command(
        ctx,
        command=command_name,
        args={"scene": scene},
        action=_run,
    )


def run_scene_value_command(
    ctx: typer.Context,
    *,
    command_name: str,
    scene: int,
    value: TValue,
    fn: SceneValueAction[TValue],
    value_name: str = "value",
    validators: Sequence[SceneValueValidator[TValue]] | None = None,
) -> None:
    active_validators = validators if validators is not None else (require_scene_and_value,)

    def _run() -> dict[str, object]:
        valid_scene = scene
        valid_value = value
        for validator in active_validators:
            valid_scene, valid_value = validator(valid_scene, valid_value)
        client = get_client(ctx)
        return fn(client, valid_scene, valid_value)

    execute_command(
        ctx,
        command=command_name,
        args={"scene": scene, value_name: value},
        action=_run,
    )


def run_scene_move_command(
    ctx: typer.Context,
    *,
    command_name: str,
    from_scene: int,
    to_scene: int,
    fn: SceneMoveAction,
    validators: Sequence[SceneMoveValidator] | None = None,
) -> None:
    active_validators = validators if validators is not None else (require_scene_move,)

    def _run() -> dict[str, object]:
        valid_from_scene = from_scene
        valid_to_scene = to_scene
        for validator in active_validators:
            valid_from_scene, valid_to_scene = validator(valid_from_scene, valid_to_scene)
        client = get_client(ctx)
        return fn(client, valid_from_scene, valid_to_scene)

    execute_command(
        ctx,
        command=command_name,
        args={"from": from_scene, "to": to_scene},
        action=_run,
    )


@scenes_app.command("list")
def scenes_list(ctx: typer.Context) -> None:
    def _run() -> dict[str, object]:
        client = get_client(ctx)
        return client.scenes_list()

    execute_command(
        ctx,
        command="scenes list",
        args={},
        action=_run,
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
        valid_index = require_scene_insert_index(index)
        client = get_client(ctx)
        return client.create_scene(valid_index)

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
    run_scene_value_command(
        ctx,
        command_name="scenes name set",
        scene=scene,
        value=name,
        value_name="name",
        validators=[require_scene_and_name],
        fn=lambda client, valid_scene, valid_name: client.set_scene_name(valid_scene, valid_name),
    )


@scenes_app.command("fire")
def scenes_fire(
    ctx: typer.Context,
    scene: Annotated[int, typer.Argument(help="Scene index (0-based)")],
) -> None:
    run_scene_command(
        ctx,
        command_name="scenes fire",
        scene=scene,
        fn=lambda client, valid_scene: client.fire_scene(valid_scene),
    )


@scenes_app.command("move")
def scenes_move(
    ctx: typer.Context,
    from_scene: Annotated[int, typer.Argument(help="Source scene index (0-based)")],
    to_scene: Annotated[int, typer.Argument(help="Destination scene index (0-based)")],
) -> None:
    run_scene_move_command(
        ctx,
        command_name="scenes move",
        from_scene=from_scene,
        to_scene=to_scene,
        fn=lambda client, valid_from_scene, valid_to_scene: client.scenes_move(
            valid_from_scene, valid_to_scene
        ),
    )


scenes_app.add_typer(name_app, name="name")


def register(app: typer.Typer) -> None:
    app.add_typer(scenes_app, name="scenes")
