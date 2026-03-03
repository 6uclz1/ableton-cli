from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from ._arrangement_specs import ArrangementCommandSpec
from ._validation import require_non_empty_string
from .clip._parsers import parse_arrangement_scene_durations

FROM_SESSION_SPEC = ArrangementCommandSpec(
    command_name="arrangement from-session",
    client_method="arrangement_from_session",
)


def register_commands(
    arrangement_app: typer.Typer,
    *,
    run_client_command_spec: Callable[..., None],
) -> None:
    @arrangement_app.command("from-session")
    def arrangement_from_session(
        ctx: typer.Context,
        scenes: Annotated[
            str,
            typer.Option(
                "--scenes",
                help="Scene duration map as CSV (scene_index:duration_beats,...)",
            ),
        ],
    ) -> None:
        def _method_kwargs() -> dict[str, object]:
            parsed = parse_arrangement_scene_durations(scenes)
            return {"scenes": parsed}

        run_client_command_spec(
            ctx,
            spec=FROM_SESSION_SPEC,
            args={
                "scenes": require_non_empty_string(
                    "scenes",
                    scenes,
                    hint="Use --scenes 0:24,1:48.",
                )
            },
            method_kwargs=_method_kwargs,
        )
