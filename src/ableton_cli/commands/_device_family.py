from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

import typer

from ..refs import (
    DeviceIndexOption,
    DeviceNameOption,
    DeviceQueryOption,
    DeviceStableRefOption,
    ParameterIndexOption,
    ParameterKeyOption,
    ParameterNameOption,
    ParameterQueryOption,
    ParameterStableRefOption,
    RefPayload,
    SelectedDeviceOption,
    SelectedTrackOption,
    TrackIndexOption,
    TrackNameOption,
    TrackQueryOption,
    TrackStableRefOption,
    build_device_ref,
    build_parameter_ref,
    build_track_ref,
)
from ..runtime import execute_command, get_client
from ._validation import (
    invalid_argument,
    require_non_empty_string,
    require_optional_track_index,
)

TrackDeviceAction = Callable[[object, RefPayload, RefPayload], dict[str, object]]


@dataclass(frozen=True)
class DeviceFamily:
    """A group of Live devices (synths, effects) that share one command and client shape."""

    name: str
    standard_types: tuple[tuple[str, str], ...]
    """``(device type, CLI subcommand name)`` for every wrapped device."""

    @property
    def type_arg(self) -> str:
        return f"{self.name}_type"

    @property
    def type_names(self) -> tuple[str, ...]:
        return tuple(device_type for device_type, _ in self.standard_types)

    def method(self, template: str) -> str:
        return template.format(family=self.name)


def run_track_device_command(
    ctx: typer.Context,
    *,
    command_name: str,
    track_ref: Callable[[], RefPayload],
    device_ref: Callable[[], RefPayload],
    fn: TrackDeviceAction,
) -> None:
    def _run() -> dict[str, object]:
        valid_track_ref = track_ref()
        valid_device_ref = device_ref()
        return fn(get_client(ctx), valid_track_ref, valid_device_ref)

    execute_command(
        ctx,
        command=command_name,
        args={"track_ref": None, "device_ref": None},
        action=_run,
        resolved_args=lambda: {"track_ref": track_ref(), "device_ref": device_ref()},
    )


def _run_parameter_set(
    ctx: typer.Context,
    *,
    command_name: str,
    value: float,
    refs: Callable[[], tuple[RefPayload, RefPayload, RefPayload]],
    fn: Callable[[object, RefPayload, RefPayload, RefPayload], dict[str, object]],
) -> None:
    def _run() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref, resolved_parameter_ref = refs()
        return fn(get_client(ctx), resolved_track_ref, resolved_device_ref, resolved_parameter_ref)

    def _resolved_args() -> dict[str, object]:
        resolved_track_ref, resolved_device_ref, resolved_parameter_ref = refs()
        return {
            "track_ref": resolved_track_ref,
            "device_ref": resolved_device_ref,
            "parameter_ref": resolved_parameter_ref,
            "value": value,
        }

    execute_command(
        ctx,
        command=command_name,
        args={"track_ref": None, "device_ref": None, "parameter_ref": None, "value": value},
        resolved_args=_resolved_args,
        action=_run,
    )


def _track_device_refs(
    *,
    track_index: int | None,
    track_name: str | None,
    selected_track: bool,
    track_query: str | None,
    track_ref: str | None,
    device_index: int | None,
    device_name: str | None,
    selected_device: bool,
    device_query: str | None,
    device_ref: str | None,
) -> tuple[Callable[[], RefPayload], Callable[[], RefPayload]]:
    return (
        lambda: build_track_ref(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
        ),
        lambda: build_device_ref(
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        ),
    )


def _register_track_device_command(
    app: typer.Typer,
    name: str,
    *,
    command_name: str,
    fn: TrackDeviceAction,
) -> None:
    @app.command(name)
    def _command(
        ctx: typer.Context,
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
        device_index: DeviceIndexOption = None,
        device_name: DeviceNameOption = None,
        selected_device: SelectedDeviceOption = False,
        device_query: DeviceQueryOption = None,
        device_ref: DeviceStableRefOption = None,
    ) -> None:
        resolve_track_ref, resolve_device_ref = _track_device_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )
        run_track_device_command(
            ctx,
            command_name=command_name,
            track_ref=resolve_track_ref,
            device_ref=resolve_device_ref,
            fn=fn,
        )


def _normalize_device_type(family: DeviceFamily, value: str) -> str:
    parsed = require_non_empty_string(
        family.type_arg, value, hint=f"Pass a non-empty {family.name} type."
    )
    normalized = parsed.lower()
    if normalized not in family.type_names:
        raise invalid_argument(
            message=f"{family.type_arg} must be one of {', '.join(family.type_names)}",
            hint=f"Use a supported {family.name} type.",
        )
    return normalized


def run_find(
    ctx: typer.Context,
    family: DeviceFamily,
    *,
    track: int | None,
    device_type: str | None,
) -> None:
    def _run() -> dict[str, object]:
        valid_track = require_optional_track_index(track)
        valid_type = (
            _normalize_device_type(family, device_type) if device_type is not None else None
        )
        find = getattr(get_client(ctx), family.method("find_{family}_devices"))
        return find(**{"track": valid_track, family.type_arg: valid_type})

    execute_command(
        ctx,
        command=f"{family.name} find",
        args={"track": track, family.type_arg: device_type},
        action=_run,
    )


def type_filter_help(family: DeviceFamily) -> str:
    return f"Optional {family.name} type filter: {'|'.join(family.type_names)}"


def _register_parameter_set(family: DeviceFamily, app: typer.Typer) -> None:
    @app.command("set")
    def _parameter_set(
        ctx: typer.Context,
        value: Annotated[float, typer.Argument(help="Target parameter value")],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
        device_index: DeviceIndexOption = None,
        device_name: DeviceNameOption = None,
        selected_device: SelectedDeviceOption = False,
        device_query: DeviceQueryOption = None,
        device_ref: DeviceStableRefOption = None,
        parameter_index: ParameterIndexOption = None,
        parameter_name: ParameterNameOption = None,
        parameter_query: ParameterQueryOption = None,
        parameter_key: ParameterKeyOption = None,
        parameter_ref: ParameterStableRefOption = None,
    ) -> None:
        resolve_track_ref, resolve_device_ref = _track_device_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )
        _run_parameter_set(
            ctx,
            command_name=f"{family.name} parameter set",
            value=value,
            refs=lambda: (
                resolve_track_ref(),
                resolve_device_ref(),
                build_parameter_ref(
                    parameter_index=parameter_index,
                    parameter_name=parameter_name,
                    parameter_query=parameter_query,
                    parameter_key=parameter_key,
                    parameter_ref=parameter_ref,
                ),
            ),
            fn=lambda client, valid_track_ref, valid_device_ref, valid_parameter_ref: getattr(
                client, family.method("set_{family}_parameter_safe")
            )(
                track_ref=valid_track_ref,
                device_ref=valid_device_ref,
                parameter_ref=valid_parameter_ref,
                value=value,
            ),
        )


def _build_standard_app(family: DeviceFamily, device_type: str, cli_name: str) -> typer.Typer:
    standard_app = typer.Typer(
        help=f"{cli_name.title()} {family.name} wrapper commands",
        no_args_is_help=True,
    )
    type_kwargs = {family.type_arg: device_type}

    @standard_app.command("keys")
    def _keys(ctx: typer.Context) -> None:
        execute_command(
            ctx,
            command=f"{family.name} {cli_name} keys",
            args={},
            action=lambda: getattr(get_client(ctx), family.method("list_standard_{family}_keys"))(
                **type_kwargs
            ),
        )

    @standard_app.command("set")
    def _standard_set(
        ctx: typer.Context,
        value: Annotated[float, typer.Argument(help="Target parameter value")],
        track_index: TrackIndexOption = None,
        track_name: TrackNameOption = None,
        selected_track: SelectedTrackOption = False,
        track_query: TrackQueryOption = None,
        track_ref: TrackStableRefOption = None,
        device_index: DeviceIndexOption = None,
        device_name: DeviceNameOption = None,
        selected_device: SelectedDeviceOption = False,
        device_query: DeviceQueryOption = None,
        device_ref: DeviceStableRefOption = None,
        parameter_key: ParameterKeyOption = None,
    ) -> None:
        resolve_track_ref, resolve_device_ref = _track_device_refs(
            track_index=track_index,
            track_name=track_name,
            selected_track=selected_track,
            track_query=track_query,
            track_ref=track_ref,
            device_index=device_index,
            device_name=device_name,
            selected_device=selected_device,
            device_query=device_query,
            device_ref=device_ref,
        )
        _run_parameter_set(
            ctx,
            command_name=f"{family.name} {cli_name} set",
            value=value,
            refs=lambda: (
                resolve_track_ref(),
                resolve_device_ref(),
                build_parameter_ref(
                    parameter_index=None,
                    parameter_name=None,
                    parameter_query=None,
                    parameter_key=parameter_key,
                    parameter_ref=None,
                ),
            ),
            fn=lambda client, valid_track_ref, valid_device_ref, valid_parameter_ref: getattr(
                client, family.method("set_standard_{family}_parameter_safe")
            )(
                **type_kwargs,
                track_ref=valid_track_ref,
                device_ref=valid_device_ref,
                parameter_ref=valid_parameter_ref,
                key=str(valid_parameter_ref["key"]),
                value=value,
            ),
        )

    _register_track_device_command(
        standard_app,
        "observe",
        command_name=f"{family.name} {cli_name} observe",
        fn=lambda client, valid_track_ref, valid_device_ref: getattr(
            client, family.method("observe_standard_{family}_state")
        )(**type_kwargs, track_ref=valid_track_ref, device_ref=valid_device_ref),
    )
    return standard_app


def build_device_family_app(
    family: DeviceFamily, register_find: Callable[[typer.Typer], None]
) -> typer.Typer:
    """Build ``<family> ...``; ``find`` is per family because its ``--type`` parameter name is."""
    family_title = family.name.title()
    family_app = typer.Typer(help=f"{family_title} control commands", no_args_is_help=True)
    parameters_app = typer.Typer(
        help=f"{family_title} parameter listing commands", no_args_is_help=True
    )
    parameter_app = typer.Typer(
        help=f"{family_title} parameter write commands", no_args_is_help=True
    )

    register_find(family_app)
    _register_track_device_command(
        parameters_app,
        "list",
        command_name=f"{family.name} parameters list",
        fn=lambda client, valid_track_ref, valid_device_ref: getattr(
            client, family.method("list_{family}_parameters")
        )(track_ref=valid_track_ref, device_ref=valid_device_ref),
    )
    _register_parameter_set(family, parameter_app)
    _register_track_device_command(
        family_app,
        "observe",
        command_name=f"{family.name} observe",
        fn=lambda client, valid_track_ref, valid_device_ref: getattr(
            client, family.method("observe_{family}_parameters")
        )(track_ref=valid_track_ref, device_ref=valid_device_ref),
    )

    family_app.add_typer(parameters_app, name="parameters")
    family_app.add_typer(parameter_app, name="parameter")
    for device_type, cli_name in family.standard_types:
        family_app.add_typer(_build_standard_app(family, device_type, cli_name), name=cli_name)
    return family_app
