from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, TypeVar

from ..errors import AppError, ErrorCode, ExitCode
from ..note_fields import NOTE_FIELD_SPECS, NoteFieldSpec
from ..pattern_notation import PatternSyntaxError, compile_pattern
from ..pattern_notation import parse as parse_pattern

NOTE_KEYS = frozenset(spec.name for spec in NOTE_FIELD_SPECS if spec.required)
_OPTIONAL_NOTE_KEYS = frozenset(spec.name for spec in NOTE_FIELD_SPECS if not spec.required)
_ALL_NOTE_KEYS = NOTE_KEYS | _OPTIONAL_NOTE_KEYS
_NOTE_FIELD_HINTS: dict[str, str] = {
    "pitch": "Use a valid MIDI pitch.",
    "start_time": "Use a non-negative note start time.",
    "duration": "Use a positive note duration.",
    "velocity": "Use a valid MIDI velocity.",
    "mute": "Set mute to true or false.",
    "probability": "Use a probability in [0.0, 1.0].",
    "velocity_deviation": "Use a velocity deviation in [-127, 127].",
    "release_velocity": "Use a valid MIDI release velocity.",
}
TRACK_INDEX_HINT = "Use a valid track index from 'ableton-cli tracks list'."
SEND_INDEX_HINT = "Use a valid 0-based send index."
DEVICE_INDEX_HINT = "Use a valid device index from 'ableton-cli track info'."
SCENE_INDEX_HINT = "Use a valid scene index from 'scenes list'."
SCENE_SOURCE_HINT = "Use a valid source scene index from 'scenes list'."
SCENE_DESTINATION_HINT = "Use a valid destination scene index from 'scenes list'."
SCENE_NAME_HINT = "Pass a non-empty scene name."
SCENE_INSERT_INDEX_HINT = "Use -1 for append or a non-negative insertion index."
TRACK_NAME_HINT = "Pass a non-empty track name."
VOLUME_VALUE_HINT = "Use a normalized volume value such as 0.75."
PAN_VALUE_HINT = "Use a normalized panning value such as -0.25."

TValue = TypeVar("TValue")


def invalid_argument(message: str, hint: str) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
    )


def require_non_negative(name: str, value: int, *, hint: str) -> int:
    if value < 0:
        raise invalid_argument(message=f"{name} must be >= 0, got {value}", hint=hint)
    return value


def require_track_index(value: int, *, hint: str = TRACK_INDEX_HINT) -> int:
    return require_non_negative("track", value, hint=hint)


def require_device_index(value: int, *, hint: str = DEVICE_INDEX_HINT) -> int:
    return require_non_negative("device", value, hint=hint)


def require_send_index(value: int, *, hint: str = SEND_INDEX_HINT) -> int:
    return require_non_negative("send", value, hint=hint)


def require_scene_index(value: int, *, hint: str = SCENE_INDEX_HINT) -> int:
    return require_non_negative("scene", value, hint=hint)


def require_parameter_index(value: int, *, hint: str) -> int:
    return require_non_negative("parameter", value, hint=hint)


def require_minus_one_or_non_negative(name: str, value: int, *, hint: str) -> int:
    if value < -1:
        raise invalid_argument(message=f"{name} must be >= -1, got {value}", hint=hint)
    return value


def require_positive_float(name: str, value: float, *, hint: str) -> float:
    if value <= 0:
        raise invalid_argument(message=f"{name} must be > 0, got {value}", hint=hint)
    return value


def require_non_negative_float(name: str, value: float, *, hint: str) -> float:
    if value < 0:
        raise invalid_argument(message=f"{name} must be >= 0, got {value}", hint=hint)
    return value


def require_float_in_range(
    name: str,
    value: float,
    *,
    minimum: float,
    maximum: float,
    hint: str,
) -> float:
    if value < minimum or value > maximum:
        raise invalid_argument(
            message=f"{name} must be between {minimum} and {maximum}, got {value}",
            hint=hint,
        )
    return value


def require_track_and_value(track: int, value: TValue) -> tuple[int, TValue]:
    return require_track_index(track), value


def require_optional_track_index(track: int | None) -> int | None:
    if track is None:
        return None
    return require_track_index(track)


def require_track_and_device(track: int, device: int) -> tuple[int, int]:
    return require_track_index(track), require_device_index(device)


def require_scene_and_value(scene: int, value: TValue) -> tuple[int, TValue]:
    return require_scene_index(scene), value


def require_track_and_name(track: int, value: str) -> tuple[int, str]:
    valid_track = require_track_index(track)
    valid_name = require_non_empty_string("name", value, hint=TRACK_NAME_HINT)
    return valid_track, valid_name


def require_scene_and_name(scene: int, value: str) -> tuple[int, str]:
    valid_scene = require_scene_index(scene)
    valid_name = require_non_empty_string("name", value, hint=SCENE_NAME_HINT)
    return valid_scene, valid_name


def require_scene_move(from_scene: int, to_scene: int) -> tuple[int, int]:
    valid_from_scene = require_non_negative("from", from_scene, hint=SCENE_SOURCE_HINT)
    valid_to_scene = require_non_negative("to", to_scene, hint=SCENE_DESTINATION_HINT)
    return valid_from_scene, valid_to_scene


def require_scene_insert_index(index: int) -> int:
    return require_minus_one_or_non_negative("index", index, hint=SCENE_INSERT_INDEX_HINT)


def require_track_and_volume(track: int, value: float) -> tuple[int, float]:
    valid_track = require_track_index(track)
    valid_value = require_float_in_range(
        "value",
        value,
        minimum=0.0,
        maximum=1.0,
        hint=VOLUME_VALUE_HINT,
    )
    return valid_track, valid_value


def require_volume_value(value: float) -> float:
    return require_float_in_range(
        "value",
        value,
        minimum=0.0,
        maximum=1.0,
        hint=VOLUME_VALUE_HINT,
    )


def require_track_and_pan(track: int, value: float) -> tuple[int, float]:
    valid_track = require_track_index(track)
    valid_value = require_float_in_range(
        "value",
        value,
        minimum=-1.0,
        maximum=1.0,
        hint=PAN_VALUE_HINT,
    )
    return valid_track, valid_value


def require_pan_value(value: float) -> float:
    return require_float_in_range(
        "value",
        value,
        minimum=-1.0,
        maximum=1.0,
        hint=PAN_VALUE_HINT,
    )


def require_track_send(track: int, send: int) -> tuple[int, int]:
    return require_track_index(track), require_send_index(send)


def require_track_send_and_volume(track: int, send: int, value: float) -> tuple[int, int, float]:
    valid_track, valid_send = require_track_send(track, send)
    valid_value = require_float_in_range(
        "value",
        value,
        minimum=0.0,
        maximum=1.0,
        hint=VOLUME_VALUE_HINT,
    )
    return valid_track, valid_send, valid_value


def require_non_empty_string(name: str, value: str, *, hint: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise invalid_argument(message=f"{name} must not be empty", hint=hint)
    return stripped


def _is_absolute_filesystem_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def require_absolute_path(name: str, value: str, *, hint: str) -> str:
    parsed = require_non_empty_string(name, value, hint=hint)
    if not _is_absolute_filesystem_path(parsed):
        raise invalid_argument(
            message=f"{name} must be an absolute path, got {parsed!r}",
            hint=hint,
        )
    return parsed


def resolve_uri_or_path_target(
    *,
    target: str,
    name: str = "target",
    hint: str = ("Use a browser path like instruments/Operator or URI like query:Synths#Operator."),
) -> tuple[str | None, str | None]:
    parsed = require_non_empty_string(name, target, hint=f"Pass a non-empty {name}.")
    first_colon = parsed.find(":")
    first_slash = parsed.find("/")
    if first_colon >= 0 and (first_slash < 0 or first_colon < first_slash):
        return parsed, None
    if "/" in parsed:
        return None, parsed
    if ":" in parsed:
        return parsed, None
    raise invalid_argument(
        message=f"{name} must include '/' (path) or ':' (uri), got {parsed!r}",
        hint=hint,
    )


def validate_clip_note_filters(
    *,
    start_time: float | None,
    end_time: float | None,
    pitch: int | None,
) -> dict[str, float | int | None]:
    if start_time is not None and start_time < 0:
        raise invalid_argument(
            message=f"start_time must be >= 0, got {start_time}",
            hint="Use a non-negative --start-time value.",
        )
    if end_time is not None and end_time <= 0:
        raise invalid_argument(
            message=f"end_time must be > 0, got {end_time}",
            hint="Use a positive --end-time value.",
        )
    if start_time is not None and end_time is not None and end_time <= start_time:
        raise invalid_argument(
            message=(
                f"end_time must be greater than start_time (start={start_time}, end={end_time})"
            ),
            hint="Use a time range where --end-time is greater than --start-time.",
        )
    if pitch is not None and (pitch < 0 or pitch > 127):
        raise invalid_argument(
            message=f"pitch must be between 0 and 127, got {pitch}",
            hint="Use a valid MIDI pitch value.",
        )
    return {
        "start_time": start_time,
        "end_time": end_time,
        "pitch": pitch,
    }


def _format_note_bound(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def _note_field_hint(name: str) -> str:
    return _NOTE_FIELD_HINTS.get(name, f"Use a valid value for '{name}'.")


def _validate_note_field_bounds(*, index: int, spec: NoteFieldSpec, value: float) -> None:
    name = spec.name
    hint = _note_field_hint(name)
    if spec.minimum is not None and spec.maximum is not None:
        if value < spec.minimum or value > spec.maximum:
            raise invalid_argument(
                message=(
                    f"notes[{index}].{name} must be between "
                    f"{_format_note_bound(spec.minimum)} and {_format_note_bound(spec.maximum)}"
                ),
                hint=hint,
            )
        return
    if spec.minimum is not None:
        if spec.exclusive_minimum:
            if value <= spec.minimum:
                raise invalid_argument(
                    message=f"notes[{index}].{name} must be > {_format_note_bound(spec.minimum)}",
                    hint=hint,
                )
        elif value < spec.minimum:
            raise invalid_argument(
                message=f"notes[{index}].{name} must be >= {_format_note_bound(spec.minimum)}",
                hint=hint,
            )


def _parsed_note_field(*, index: int, spec: NoteFieldSpec, item: dict[str, Any]) -> Any:
    name = spec.name
    value = item[name]
    if spec.kind == "bool":
        if not isinstance(value, bool):
            raise invalid_argument(
                message=f"notes[{index}].{name} must be boolean",
                hint=_note_field_hint(name),
            )
        return value
    if spec.kind == "int":
        if not isinstance(value, int):
            raise invalid_argument(
                message=f"notes[].{name} must be an integer",
                hint="Use numeric values for pitch and velocity.",
            )
        _validate_note_field_bounds(index=index, spec=spec, value=value)
        return value
    if not isinstance(value, (int, float)):
        raise invalid_argument(
            message=f"notes[].{name} must be a number",
            hint="Use numeric values for note timing fields.",
        )
    parsed = float(value)
    _validate_note_field_bounds(index=index, spec=spec, value=parsed)
    return parsed


def _validate_full_note_keys(*, index: int, item: dict[str, Any]) -> None:
    keys = set(item.keys())
    if not _OPTIONAL_NOTE_KEYS:
        if keys != NOTE_KEYS:
            raise invalid_argument(
                message=f"notes[{index}] must include exactly {sorted(NOTE_KEYS)}",
                hint="Provide all required note fields and no extra keys.",
            )
        return
    missing = NOTE_KEYS - keys
    unknown = keys - _ALL_NOTE_KEYS
    if missing or unknown:
        raise invalid_argument(
            message=(
                f"notes[{index}] must include {sorted(NOTE_KEYS)} "
                f"and may only add optional fields from {sorted(_OPTIONAL_NOTE_KEYS)}"
            ),
            hint="Provide all required note fields; only supported optional fields are allowed.",
        )


def parse_notes_json(notes_json: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(notes_json)
    except json.JSONDecodeError as exc:
        raise invalid_argument(
            message=f"notes_json must be valid JSON: {exc.msg}",
            hint="Pass a JSON array like '[{\"pitch\":60,...}]'.",
        ) from exc

    if not isinstance(payload, list):
        raise invalid_argument(
            message="notes_json must decode to an array",
            hint="Pass a JSON array of note objects.",
        )

    sanitized: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise invalid_argument(
                message=f"notes[{index}] must be an object",
                hint="Each note must include pitch/start_time/duration/velocity/mute.",
            )

        _validate_full_note_keys(index=index, item=item)

        parsed_note: dict[str, Any] = {}
        for spec in NOTE_FIELD_SPECS:
            if spec.name not in item:
                continue
            parsed_note[spec.name] = _parsed_note_field(index=index, spec=spec, item=item)
        sanitized.append(parsed_note)

    return sanitized


def _validate_partial_note_keys(*, index: int, item: dict[str, Any]) -> None:
    keys = set(item.keys())
    if "note_id" not in keys:
        raise invalid_argument(
            message=f"notes[{index}] must include note_id",
            hint="Provide note_id from 'clip notes get' for each note to update.",
        )
    editable_keys = keys - {"note_id"}
    unknown = editable_keys - _ALL_NOTE_KEYS
    if unknown:
        raise invalid_argument(
            message=f"notes[{index}] has unsupported fields: {sorted(unknown)}",
            hint=f"Use only note_id and fields from {sorted(_ALL_NOTE_KEYS)}.",
        )
    if not editable_keys:
        raise invalid_argument(
            message=f"notes[{index}] must include at least one editable field besides note_id",
            hint=f"Provide one or more fields from {sorted(_ALL_NOTE_KEYS)}.",
        )


def _parsed_note_id(*, index: int, item: dict[str, Any]) -> int:
    value = item["note_id"]
    if not isinstance(value, int) or isinstance(value, bool):
        raise invalid_argument(
            message=f"notes[{index}].note_id must be an integer",
            hint="Use an integer note_id from 'clip notes get'.",
        )
    if value < 0:
        raise invalid_argument(
            message=f"notes[{index}].note_id must be >= 0",
            hint="Use a non-negative note_id.",
        )
    return value


def parse_partial_notes_json(notes_json: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(notes_json)
    except json.JSONDecodeError as exc:
        raise invalid_argument(
            message=f"notes_json must be valid JSON: {exc.msg}",
            hint='Pass a JSON array like \'[{"note_id":3,"velocity":90}]\'.',
        ) from exc

    if not isinstance(payload, list):
        raise invalid_argument(
            message="notes_json must decode to an array",
            hint="Pass a JSON array of note update objects.",
        )

    sanitized: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise invalid_argument(
                message=f"notes[{index}] must be an object",
                hint="Each note update must include note_id and at least one editable field.",
            )

        _validate_partial_note_keys(index=index, item=item)

        parsed_note: dict[str, Any] = {"note_id": _parsed_note_id(index=index, item=item)}
        for spec in NOTE_FIELD_SPECS:
            if spec.name in item:
                parsed_note[spec.name] = _parsed_note_field(index=index, spec=spec, item=item)
        sanitized.append(parsed_note)

    return sanitized


def parse_notes_input(
    notes_json: str | None,
    notes_file: str | None,
    *,
    parser: Callable[[str], list[dict[str, Any]]] = parse_notes_json,
) -> list[dict[str, Any]]:
    if notes_json is not None and notes_file is not None:
        raise invalid_argument(
            message="--notes-json and --notes-file are mutually exclusive",
            hint="Pass exactly one of --notes-json or --notes-file.",
        )
    if notes_json is None and notes_file is None:
        raise invalid_argument(
            message="Exactly one of --notes-json or --notes-file must be provided",
            hint="Pass note data via --notes-json or --notes-file.",
        )

    if notes_json is not None:
        return parser(notes_json)

    assert notes_file is not None
    path = Path(notes_file)
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise invalid_argument(
            message=f"notes_file could not be read: {path}",
            hint="Pass a readable UTF-8 JSON file path for --notes-file.",
        ) from exc
    return parser(payload)


def parse_pattern_notes(
    pattern: str,
    *,
    pattern_length: float,
    velocity: int,
    gate: float = 1.0,
) -> list[dict[str, Any]]:
    try:
        node = parse_pattern(pattern)
    except PatternSyntaxError as exc:
        raise invalid_argument(
            message=f"pattern is invalid at column {exc.column}: {exc}",
            hint="See docs/pattern-notation.md for the mini-notation grammar.",
        ) from exc
    try:
        return compile_pattern(
            node,
            pattern_length=pattern_length,
            default_velocity=velocity,
            gate=gate,
        )
    except ValueError as exc:
        raise invalid_argument(
            message=str(exc),
            hint="Use --pattern-length > 0 and --gate in (0.0, 1.0].",
        ) from exc


def require_mutually_exclusive_note_sources(
    *,
    notes_json: str | None,
    notes_file: str | None,
    pattern: str | None,
) -> None:
    provided = [
        name
        for name, value in (
            ("--notes-json", notes_json),
            ("--notes-file", notes_file),
            ("--pattern", pattern),
        )
        if value is not None
    ]
    if len(provided) > 1:
        raise invalid_argument(
            message=f"{' and '.join(provided)} are mutually exclusive",
            hint="Pass exactly one of --notes-json, --notes-file, or --pattern.",
        )
