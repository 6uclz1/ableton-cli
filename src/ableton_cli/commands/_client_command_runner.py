from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

import typer

MethodKwargs = dict[str, object] | Callable[[], dict[str, object]] | None
ClientAction = Callable[[object], dict[str, object]]
GetClientFn = Callable[[typer.Context], object]
ExecuteCommandFn = Callable[..., None]


class ClientCommandSpec(Protocol):
    command_name: str
    client_method: str


@dataclass(frozen=True)
class CommandSpec:
    command_name: str
    client_method: str


def _resolve_method_kwargs(method_kwargs: MethodKwargs) -> dict[str, object]:
    if callable(method_kwargs):
        return method_kwargs()
    if method_kwargs is None:
        return {}
    return method_kwargs


def run_client_command(
    ctx: typer.Context,
    *,
    command_name: str,
    args: dict[str, object],
    fn: ClientAction,
    get_client_fn: GetClientFn,
    execute_command_fn: ExecuteCommandFn,
) -> None:
    execute_command_fn(
        ctx,
        command=command_name,
        args=args,
        action=lambda: fn(get_client_fn(ctx)),
    )


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: ClientCommandSpec,
    args: dict[str, object],
    get_client_fn: GetClientFn,
    execute_command_fn: ExecuteCommandFn,
    method_kwargs: MethodKwargs = None,
) -> None:
    run_client_command(
        ctx,
        command_name=spec.command_name,
        args=args,
        fn=lambda client: cast(
            dict[str, object],
            getattr(client, spec.client_method)(**_resolve_method_kwargs(method_kwargs)),
        ),
        get_client_fn=get_client_fn,
        execute_command_fn=execute_command_fn,
    )
