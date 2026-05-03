from __future__ import annotations

from typing import Annotated

import typer

from ..errors import AppError, ErrorCode, ExitCode
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
    build_device_ref,
    build_parameter_ref,
)
from ..runtime import execute_command, get_client
from ._client_command_runner import CommandSpec
from ._client_command_runner import run_client_command_spec as run_client_command_spec_shared

master_app = typer.Typer(help="Master track commands", no_args_is_help=True)
volume_app = typer.Typer(help="Master volume commands", no_args_is_help=True)
panning_app = typer.Typer(help="Master panning commands", no_args_is_help=True)
devices_app = typer.Typer(help="Master device commands", no_args_is_help=True)
device_app = typer.Typer(help="Master device write commands", no_args_is_help=True)
device_parameters_app = typer.Typer(help="Master device parameter listing", no_args_is_help=True)
device_parameter_app = typer.Typer(help="Master device parameter writes", no_args_is_help=True)
effect_app = typer.Typer(help="Master effect wrapper commands", no_args_is_help=True)

MASTER_INFO_SPEC = CommandSpec(command_name="master info", client_method="master_info")
MASTER_VOLUME_GET_SPEC = CommandSpec(
    command_name="master volume get",
    client_method="master_volume_get",
)
MASTER_PANNING_GET_SPEC = CommandSpec(
    command_name="master panning get",
    client_method="master_panning_get",
)
MASTER_DEVICES_LIST_SPEC = CommandSpec(
    command_name="master devices list",
    client_method="master_devices_list",
)


def run_client_command_spec(
    ctx: typer.Context,
    *,
    spec: CommandSpec,
) -> None:
    run_client_command_spec_shared(
        ctx,
        spec=spec,
        args={},
        get_client_fn=get_client,
        execute_command_fn=execute_command,
    )


@master_app.command("info")
def master_info(ctx: typer.Context) -> None:
    run_client_command_spec(ctx, spec=MASTER_INFO_SPEC)


@volume_app.command("get")
def master_volume_get(ctx: typer.Context) -> None:
    run_client_command_spec(ctx, spec=MASTER_VOLUME_GET_SPEC)


@volume_app.command("set")
def master_volume_set(
    ctx: typer.Context,
    value: Annotated[float, typer.Argument(help="Master volume value")],
) -> None:
    execute_command(
        ctx,
        command="master volume set",
        args={"value": value},
        action=lambda: get_client(ctx).master_volume_set(value),
    )


@panning_app.command("get")
def master_panning_get(ctx: typer.Context) -> None:
    run_client_command_spec(ctx, spec=MASTER_PANNING_GET_SPEC)


@panning_app.command("set")
def master_panning_set(
    ctx: typer.Context,
    value: Annotated[float, typer.Argument(help="Master panning value")],
) -> None:
    execute_command(
        ctx,
        command="master panning set",
        args={"value": value},
        action=lambda: get_client(ctx).master_panning_set(value),
    )


@devices_app.command("list")
def master_devices_list(ctx: typer.Context) -> None:
    run_client_command_spec(ctx, spec=MASTER_DEVICES_LIST_SPEC)


@device_app.command("load")
def master_device_load(
    ctx: typer.Context,
    target: Annotated[str, typer.Argument(help="Browser uri/path/query target")],
    position: Annotated[str, typer.Option("--position", help="Insert position")] = "end",
) -> None:
    execute_command(
        ctx,
        command="master device load",
        args={"target": target, "position": position},
        action=lambda: get_client(ctx).master_device_load(target, position),
    )


@device_app.command("move")
def master_device_move(
    ctx: typer.Context,
    device_index: Annotated[int, typer.Option("--device-index", help="Device index")],
    to_index: Annotated[int, typer.Option("--to-index", help="Destination index")],
) -> None:
    execute_command(
        ctx,
        command="master device move",
        args={"device_index": device_index, "to_index": to_index},
        action=lambda: get_client(ctx).master_device_move(device_index, to_index),
    )


@device_app.command("delete")
def master_device_delete(
    ctx: typer.Context,
    device_index: Annotated[int, typer.Option("--device-index", help="Device index")],
    yes: Annotated[bool, typer.Option("--yes", help="Confirm device deletion")] = False,
) -> None:
    def _action() -> dict[str, object]:
        if not yes:
            raise AppError(
                error_code=ErrorCode.INVALID_ARGUMENT,
                message="master device delete requires --yes",
                hint="Pass --yes to confirm deleting a master device.",
                exit_code=ExitCode.INVALID_ARGUMENT,
            )
        return get_client(ctx).master_device_delete(device_index)

    execute_command(
        ctx,
        command="master device delete",
        args={"device_index": device_index, "yes": yes},
        action=_action,
    )


@device_parameters_app.command("list")
def master_device_parameters_list(
    ctx: typer.Context,
    device_index: DeviceIndexOption = None,
    device_name: DeviceNameOption = None,
    device_query: DeviceQueryOption = None,
    device_ref: DeviceStableRefOption = None,
) -> None:
    execute_command(
        ctx,
        command="master device parameters list",
        args={"device_ref": None},
        resolved_args=lambda: {
            "device_ref": _device_ref(device_index, device_name, device_query, device_ref)
        },
        action=lambda: get_client(ctx).master_device_parameters_list(
            _device_ref(device_index, device_name, device_query, device_ref)
        ),
    )


@device_parameter_app.command("set")
def master_device_parameter_set(
    ctx: typer.Context,
    value: Annotated[float, typer.Argument(help="Target parameter value")],
    device_index: DeviceIndexOption = None,
    device_name: DeviceNameOption = None,
    device_query: DeviceQueryOption = None,
    device_ref: DeviceStableRefOption = None,
    parameter_index: ParameterIndexOption = None,
    parameter_name: ParameterNameOption = None,
    parameter_query: ParameterQueryOption = None,
    parameter_key: ParameterKeyOption = None,
    parameter_ref: ParameterStableRefOption = None,
) -> None:
    execute_command(
        ctx,
        command="master device parameter set",
        args={"device_ref": None, "parameter_ref": None, "value": value},
        resolved_args=lambda: {
            "device_ref": _device_ref(device_index, device_name, device_query, device_ref),
            "parameter_ref": _parameter_ref(
                parameter_index,
                parameter_name,
                parameter_query,
                parameter_key,
                parameter_ref,
            ),
            "value": value,
        },
        action=lambda: get_client(ctx).master_device_parameter_set(
            _device_ref(device_index, device_name, device_query, device_ref),
            _parameter_ref(
                parameter_index,
                parameter_name,
                parameter_query,
                parameter_key,
                parameter_ref,
            ),
            value,
        ),
    )


def _build_effect_app(effect_type: str) -> typer.Typer:
    standard_app = typer.Typer(
        help=f"Master {effect_type} effect commands",
        no_args_is_help=True,
    )

    @standard_app.command("keys")
    def master_effect_keys(ctx: typer.Context) -> None:
        execute_command(
            ctx,
            command=f"master effect {effect_type} keys",
            args={"effect_type": effect_type},
            action=lambda: get_client(ctx).master_effect_keys(effect_type),
        )

    @standard_app.command("set")
    def master_effect_set(
        ctx: typer.Context,
        value: Annotated[float, typer.Argument(help="Target parameter value")],
        device_index: DeviceIndexOption = None,
        device_name: DeviceNameOption = None,
        device_query: DeviceQueryOption = None,
        device_ref: DeviceStableRefOption = None,
        parameter_index: ParameterIndexOption = None,
        parameter_name: ParameterNameOption = None,
        parameter_query: ParameterQueryOption = None,
        parameter_key: ParameterKeyOption = None,
        parameter_ref: ParameterStableRefOption = None,
    ) -> None:
        execute_command(
            ctx,
            command=f"master effect {effect_type} set",
            args={"device_ref": None, "parameter_ref": None, "value": value},
            resolved_args=lambda: {
                "device_ref": _device_ref(device_index, device_name, device_query, device_ref),
                "parameter_ref": _parameter_ref(
                    parameter_index,
                    parameter_name,
                    parameter_query,
                    parameter_key,
                    parameter_ref,
                ),
                "value": value,
            },
            action=lambda: get_client(ctx).master_effect_set(
                effect_type,
                _device_ref(device_index, device_name, device_query, device_ref),
                _parameter_ref(
                    parameter_index,
                    parameter_name,
                    parameter_query,
                    parameter_key,
                    parameter_ref,
                ),
                value,
            ),
        )

    @standard_app.command("observe")
    def master_effect_observe(
        ctx: typer.Context,
        device_index: DeviceIndexOption = None,
        device_name: DeviceNameOption = None,
        device_query: DeviceQueryOption = None,
        device_ref: DeviceStableRefOption = None,
    ) -> None:
        execute_command(
            ctx,
            command=f"master effect {effect_type} observe",
            args={"device_ref": None},
            resolved_args=lambda: {
                "device_ref": _device_ref(device_index, device_name, device_query, device_ref)
            },
            action=lambda: get_client(ctx).master_effect_observe(
                effect_type,
                _device_ref(device_index, device_name, device_query, device_ref),
            ),
        )

    return standard_app


def _device_ref(
    device_index: int | None,
    device_name: str | None,
    device_query: str | None,
    device_ref: str | None,
) -> dict[str, object]:
    return build_device_ref(
        device_index=device_index,
        device_name=device_name,
        selected_device=False,
        device_query=device_query,
        device_ref=device_ref,
    )


def _parameter_ref(
    parameter_index: int | None,
    parameter_name: str | None,
    parameter_query: str | None,
    parameter_key: str | None,
    parameter_ref: str | None,
) -> dict[str, object]:
    return build_parameter_ref(
        parameter_index=parameter_index,
        parameter_name=parameter_name,
        parameter_query=parameter_query,
        parameter_key=parameter_key,
        parameter_ref=parameter_ref,
    )


master_app.add_typer(volume_app, name="volume")
master_app.add_typer(panning_app, name="panning")
master_app.add_typer(devices_app, name="devices")
device_app.add_typer(device_parameters_app, name="parameters")
device_app.add_typer(device_parameter_app, name="parameter")
master_app.add_typer(device_app, name="device")
for _effect_type in ("eq8", "limiter", "compressor", "utility"):
    effect_app.add_typer(_build_effect_app(_effect_type), name=_effect_type)
master_app.add_typer(effect_app, name="effect")


def register(app: typer.Typer) -> None:
    app.add_typer(master_app, name="master")
