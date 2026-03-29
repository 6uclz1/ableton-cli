from __future__ import annotations

from typing import Annotated, Any

import typer

from .errors import AppError, ErrorCode, ExitCode

RefPayload = dict[str, Any]

TrackIndexOption = Annotated[
    int | None, typer.Option("--track-index", help="Track index (0-based)")
]
TrackNameOption = Annotated[str | None, typer.Option("--track-name", help="Exact track name")]
SelectedTrackOption = Annotated[
    bool,
    typer.Option("--selected-track", help="Use the currently selected track"),
]
TrackStableRefOption = Annotated[
    str | None,
    typer.Option("--track-ref", help="Session-local stable track reference"),
]
TrackQueryOption = Annotated[
    str | None,
    typer.Option("--track-query", help="Unique case-insensitive track query"),
]

DeviceIndexOption = Annotated[
    int | None, typer.Option("--device-index", help="Device index (0-based)")
]
DeviceNameOption = Annotated[str | None, typer.Option("--device-name", help="Exact device name")]
SelectedDeviceOption = Annotated[
    bool,
    typer.Option("--selected-device", help="Use the currently selected device on the target track"),
]
DeviceStableRefOption = Annotated[
    str | None,
    typer.Option("--device-ref", help="Session-local stable device reference"),
]
DeviceQueryOption = Annotated[
    str | None,
    typer.Option("--device-query", help="Unique case-insensitive device query"),
]

ParameterIndexOption = Annotated[
    int | None,
    typer.Option("--parameter-index", help="Parameter index (0-based)"),
]
ParameterNameOption = Annotated[
    str | None,
    typer.Option("--parameter-name", help="Exact parameter name"),
]
ParameterStableRefOption = Annotated[
    str | None,
    typer.Option("--parameter-ref", help="Session-local stable parameter reference"),
]
ParameterQueryOption = Annotated[
    str | None,
    typer.Option("--parameter-query", help="Unique case-insensitive parameter query"),
]
ParameterKeyOption = Annotated[
    str | None,
    typer.Option("--parameter-key", help="Stable synth/effect parameter key"),
]


def _invalid_argument(message: str, hint: str) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
    )


def _require_non_negative(name: str, value: int) -> int:
    if value < 0:
        raise _invalid_argument(
            message=f"{name} must be >= 0, got {value}",
            hint=f"Use a non-negative {name} selector.",
        )
    return value


def _require_non_empty(name: str, value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise _invalid_argument(
            message=f"{name} must not be empty",
            hint=f"Pass a non-empty {name}.",
        )
    return stripped


def _select_one(kind: str, selectors: list[RefPayload]) -> RefPayload:
    if len(selectors) != 1:
        raise _invalid_argument(
            message=f"Exactly one {kind} selector must be provided",
            hint=(
                f"Choose exactly one of --{kind}-index, --{kind}-name, "
                f"--selected-{kind}, --{kind}-query, or --{kind}-ref."
            )
            if kind != "parameter"
            else (
                "Choose exactly one of --parameter-index, --parameter-name, "
                "--parameter-query, --parameter-key, or --parameter-ref."
            ),
        )
    return selectors[0]


def build_track_ref(
    *,
    track_index: int | None,
    track_name: str | None,
    selected_track: bool,
    track_query: str | None,
    track_ref: str | None,
) -> RefPayload:
    selectors: list[RefPayload] = []
    if track_index is not None:
        selectors.append(
            {"mode": "index", "index": _require_non_negative("track_index", track_index)}
        )
    if track_name is not None:
        selectors.append({"mode": "name", "name": _require_non_empty("track_name", track_name)})
    if selected_track:
        selectors.append({"mode": "selected"})
    if track_query is not None:
        selectors.append({"mode": "query", "query": _require_non_empty("track_query", track_query)})
    if track_ref is not None:
        selectors.append(
            {"mode": "stable_ref", "stable_ref": _require_non_empty("track_ref", track_ref)}
        )
    return _select_one("track", selectors)


def build_device_ref(
    *,
    device_index: int | None,
    device_name: str | None,
    selected_device: bool,
    device_query: str | None,
    device_ref: str | None,
) -> RefPayload:
    selectors: list[RefPayload] = []
    if device_index is not None:
        selectors.append(
            {"mode": "index", "index": _require_non_negative("device_index", device_index)}
        )
    if device_name is not None:
        selectors.append({"mode": "name", "name": _require_non_empty("device_name", device_name)})
    if selected_device:
        selectors.append({"mode": "selected"})
    if device_query is not None:
        selectors.append(
            {"mode": "query", "query": _require_non_empty("device_query", device_query)}
        )
    if device_ref is not None:
        selectors.append(
            {"mode": "stable_ref", "stable_ref": _require_non_empty("device_ref", device_ref)}
        )
    return _select_one("device", selectors)


def build_parameter_ref(
    *,
    parameter_index: int | None,
    parameter_name: str | None,
    parameter_query: str | None,
    parameter_key: str | None,
    parameter_ref: str | None,
) -> RefPayload:
    selectors: list[RefPayload] = []
    if parameter_index is not None:
        selectors.append(
            {"mode": "index", "index": _require_non_negative("parameter_index", parameter_index)}
        )
    if parameter_name is not None:
        selectors.append(
            {"mode": "name", "name": _require_non_empty("parameter_name", parameter_name)}
        )
    if parameter_query is not None:
        selectors.append(
            {"mode": "query", "query": _require_non_empty("parameter_query", parameter_query)}
        )
    if parameter_key is not None:
        selectors.append({"mode": "key", "key": _require_non_empty("parameter_key", parameter_key)})
    if parameter_ref is not None:
        selectors.append(
            {
                "mode": "stable_ref",
                "stable_ref": _require_non_empty("parameter_ref", parameter_ref),
            }
        )
    return _select_one("parameter", selectors)
