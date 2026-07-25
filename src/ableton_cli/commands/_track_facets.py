"""Typer commands generated from the declarative track facet table.

``track volume|panning|mute|solo|arm|name`` used to be seven near-identical
modules: same five selector options, same ``build_track_ref`` lambda, same
two-command shape, differing only in the command name, the client method,
the value type and the validator. They are generated from
:data:`ableton_cli.track_facets.TRACK_FACET_SPECS` here — adding a facet is
a row in that table, not a new file.

This module deliberately does *not* use ``from __future__ import
annotations``: the generated commands build their ``Annotated`` value
argument from per-facet help/metavar strings at registration time, which
only works while annotations are evaluated eagerly.
"""

from collections.abc import Callable, Sequence
from typing import Annotated, Any

import typer

from ..refs import (
    RefPayload,
    SelectedTrackOption,
    TrackIndexOption,
    TrackNameOption,
    TrackQueryOption,
    TrackStableRefOption,
    build_track_ref,
)
from ..track_facets import (
    TRACK_FACET_SPECS,
    TRACK_INFO_CLIENT_METHOD,
    TRACK_INFO_COMMAND,
    TrackFacetSpec,
)
from ._track_shared import ValueValidator
from ._track_specs import TrackCommandSpec, TrackValueCommandSpec
from ._validation import require_non_empty_string, require_pan_value, require_volume_value

CommandRunner = Callable[..., None]
TrackRefFactory = Callable[[], RefPayload]

#: Validators live here, not in the core table: they raise CLI errors.
FACET_VALIDATORS: dict[str, Sequence[ValueValidator[Any]]] = {
    "volume": (require_volume_value,),
    "panning": (require_pan_value,),
    "name": (
        lambda value: require_non_empty_string("name", value, hint="Pass a non-empty track name."),
    ),
}


def get_spec(facet: TrackFacetSpec) -> TrackCommandSpec | None:
    command_name = facet.get_command_name
    if command_name is None or facet.client_get is None:
        return None
    return TrackCommandSpec(command_name=command_name, client_method=facet.client_get)


def set_spec(facet: TrackFacetSpec) -> TrackValueCommandSpec[Any] | None:
    command_name = facet.set_command_name
    if command_name is None or facet.client_set is None:
        return None
    return TrackValueCommandSpec(
        command_name=command_name,
        client_method=facet.client_set,
        value_name=facet.value_arg_name,
        validators=tuple(FACET_VALIDATORS.get(facet.name, ())) or None,
    )


def _track_ref_factory(
    *,
    track_index: int | None,
    track_name: str | None,
    selected_track: bool,
    track_query: str | None,
    track_ref: str | None,
) -> TrackRefFactory:
    return lambda: build_track_ref(
        track_index=track_index,
        track_name=track_name,
        selected_track=selected_track,
        track_query=track_query,
        track_ref=track_ref,
    )


def register_getter(
    app: typer.Typer,
    *,
    subcommand: str,
    spec: TrackCommandSpec,
    run_track_command_spec: CommandRunner,
) -> None:
    @app.command(subcommand)
    def _get(
        ctx: typer.Context,
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_command_spec(
            ctx,
            spec=spec,
            track_ref=_track_ref_factory(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
        )


def _register_bool_setter(
    app: typer.Typer, facet: TrackFacetSpec, run_track_value_command_spec: CommandRunner
) -> None:
    spec = set_spec(facet)

    @app.command("set")
    def _set(
        ctx: typer.Context,
        value: Annotated[bool, typer.Argument(help=facet.value_help, metavar=facet.value_metavar)],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=spec,
            track_ref=_track_ref_factory(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            value=value,
        )


def _register_float_setter(
    app: typer.Typer, facet: TrackFacetSpec, run_track_value_command_spec: CommandRunner
) -> None:
    spec = set_spec(facet)

    @app.command("set")
    def _set(
        ctx: typer.Context,
        value: Annotated[float, typer.Argument(help=facet.value_help, metavar=facet.value_metavar)],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=spec,
            track_ref=_track_ref_factory(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            value=value,
        )


def _register_str_setter(
    app: typer.Typer, facet: TrackFacetSpec, run_track_value_command_spec: CommandRunner
) -> None:
    spec = set_spec(facet)

    @app.command("set")
    def _set(
        ctx: typer.Context,
        value: Annotated[str, typer.Argument(help=facet.value_help, metavar=facet.value_metavar)],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
    ) -> None:
        run_track_value_command_spec(
            ctx,
            spec=spec,
            track_ref=_track_ref_factory(
                track_index=track_index,
                track_name=track_name,
                selected_track=selected_track,
                track_query=track_query,
                track_ref=track_ref,
            ),
            value=value,
        )


_SETTER_REGISTRARS: dict[str, Callable[[typer.Typer, TrackFacetSpec, CommandRunner], None]] = {
    "bool": _register_bool_setter,
    "float": _register_float_setter,
    "str": _register_str_setter,
}


def register_track_facets(
    track_app: typer.Typer,
    *,
    run_track_command_spec: CommandRunner,
    run_track_value_command_spec: CommandRunner,
) -> dict[str, typer.Typer]:
    """Attach ``track info`` and one sub-app per facet to ``track_app``."""
    register_getter(
        track_app,
        subcommand="info",
        spec=TrackCommandSpec(
            command_name=TRACK_INFO_COMMAND,
            client_method=TRACK_INFO_CLIENT_METHOD,
        ),
        run_track_command_spec=run_track_command_spec,
    )

    facet_apps: dict[str, typer.Typer] = {}
    for facet in TRACK_FACET_SPECS:
        app = typer.Typer(help=facet.help, no_args_is_help=True)
        getter = get_spec(facet)
        if getter is not None:
            register_getter(
                app,
                subcommand="get",
                spec=getter,
                run_track_command_spec=run_track_command_spec,
            )
        if facet.client_set is not None:
            registrar = _SETTER_REGISTRARS.get(facet.value_kind)
            if registrar is None:
                raise ValueError(f"unknown track facet value kind: {facet.value_kind!r}")
            registrar(app, facet, run_track_value_command_spec)
        track_app.add_typer(app, name=facet.name)
        facet_apps[facet.name] = app
    return facet_apps
