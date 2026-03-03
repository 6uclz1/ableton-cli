from __future__ import annotations

from collections.abc import Callable

import typer

from ._arrangement_specs import ArrangementCommandSpec

RECORD_START_SPEC = ArrangementCommandSpec(
    command_name="arrangement record start",
    client_method="arrangement_record_start",
)

RECORD_STOP_SPEC = ArrangementCommandSpec(
    command_name="arrangement record stop",
    client_method="arrangement_record_stop",
)


def register_commands(
    record_app: typer.Typer,
    *,
    run_client_command_spec: Callable[..., None],
) -> None:
    @record_app.command("start")
    def arrangement_record_start(ctx: typer.Context) -> None:
        run_client_command_spec(
            ctx,
            spec=RECORD_START_SPEC,
            args={},
        )

    @record_app.command("stop")
    def arrangement_record_stop(ctx: typer.Context) -> None:
        run_client_command_spec(
            ctx,
            spec=RECORD_STOP_SPEC,
            args={},
        )
