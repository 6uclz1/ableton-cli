from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from .command_backend_contract import (
    MAX_BPM,
    MAX_PANNING,
    MAX_VOLUME,
    MIN_BPM,
    MIN_PANNING,
    MIN_VOLUME,
    NOTE_PITCH_MAX,
    NOTE_PITCH_MIN,
    NOTE_VELOCITY_MAX,
    CommandError,
)
from .effect_specs import SUPPORTED_EFFECT_TYPES
from .note_fields import NOTE_FIELD_SPECS, NoteFieldSpec
from .synth_specs import SUPPORTED_SYNTH_TYPES

_NOTE_REQUIRED_KEYS = frozenset(spec.name for spec in NOTE_FIELD_SPECS if spec.required)
_NOTE_OPTIONAL_KEYS = frozenset(spec.name for spec in NOTE_FIELD_SPECS if not spec.required)
_NOTE_ALL_KEYS = _NOTE_REQUIRED_KEYS | _NOTE_OPTIONAL_KEYS
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


def _invalid_argument(message: str, hint: str) -> CommandError:
    return CommandError(code="INVALID_ARGUMENT", message=message, hint=hint)


def _as_int(name: str, value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise _invalid_argument(
            message=f"{name} must be an integer",
            hint=f"Pass a valid integer for '{name}'.",
        ) from exc


def _as_float(name: str, value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise _invalid_argument(
            message=f"{name} must be a number",
            hint=f"Pass a valid numeric value for '{name}'.",
        ) from exc


def _as_str(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise _invalid_argument(
            message=f"{name} must be a string",
            hint=f"Pass a valid string for '{name}'.",
        )
    return value


def _non_empty_string(name: str, value: Any) -> str:
    parsed = _as_str(name, value).strip()
    if not parsed:
        raise _invalid_argument(
            message=f"{name} must not be empty",
            hint=f"Pass a non-empty value for '{name}'.",
        )
    return parsed


def _uri_or_path_target(name: str, value: Any) -> str:
    parsed = _non_empty_string(name, value)
    if "/" in parsed or ":" in parsed:
        return parsed
    raise _invalid_argument(
        message=f"{name} must include '/' (path) or ':' (uri)",
        hint="Use a browser path like grooves/My Groove.agr or URI like groove:example.",
    )


def _is_absolute_filesystem_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _absolute_path_or_none(name: str, value: Any) -> str | None:
    if value is None:
        return None
    parsed = _non_empty_string(name, value)
    if not _is_absolute_filesystem_path(parsed):
        raise _invalid_argument(
            message=f"{name} must be an absolute path",
            hint=f"Pass an absolute filesystem path for '{name}'.",
        )
    return parsed


def _track_index(name: str, value: Any) -> int:
    parsed = _as_int(name, value)
    if parsed < 0:
        raise _invalid_argument(
            message=f"{name} must be >= 0",
            hint="Use a valid index from listing commands.",
        )
    return parsed


def _optional_track_index(name: str, value: Any) -> int | None:
    if value is None:
        return None
    return _track_index(name, value)


def _insert_index(name: str, value: Any) -> int:
    parsed = _as_int(name, value)
    if parsed < -1:
        raise _invalid_argument(
            message=f"{name} must be >= -1",
            hint="Use -1 for append or a non-negative insertion index.",
        )
    return parsed


def _bounded_float(
    *,
    name: str,
    value: Any,
    minimum: float,
    maximum: float,
    hint: str,
) -> float:
    parsed = _as_float(name, value)
    if parsed < minimum or parsed > maximum:
        raise _invalid_argument(
            message=f"{name} must be between {minimum} and {maximum}",
            hint=hint,
        )
    return parsed


def _tempo(value: Any) -> float:
    return _bounded_float(
        name="bpm",
        value=value,
        minimum=MIN_BPM,
        maximum=MAX_BPM,
        hint="Use a tempo value like 120.",
    )


def _volume(value: Any) -> float:
    return _bounded_float(
        name="value",
        value=value,
        minimum=MIN_VOLUME,
        maximum=MAX_VOLUME,
        hint="Use a normalized volume value in [0.0, 1.0].",
    )


def _panning(value: Any) -> float:
    return _bounded_float(
        name="value",
        value=value,
        minimum=MIN_PANNING,
        maximum=MAX_PANNING,
        hint="Use a normalized panning value in [-1.0, 1.0].",
    )


def _clip_length(value: Any) -> float:
    length = _as_float("length", value)
    if length <= 0:
        raise _invalid_argument(
            message="length must be > 0",
            hint="Use a positive clip length in beats.",
        )
    return length


def _positive_int(name: str, value: Any) -> int:
    parsed = _as_int(name, value)
    if parsed <= 0:
        raise _invalid_argument(
            message=f"{name} must be > 0",
            hint=f"Pass a positive integer for '{name}'.",
        )
    return parsed


def _non_negative_int(name: str, value: Any) -> int:
    parsed = _as_int(name, value)
    if parsed < 0:
        raise _invalid_argument(
            message=f"{name} must be >= 0",
            hint=f"Pass a non-negative integer for '{name}'.",
        )
    return parsed


def _as_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise _invalid_argument(
            message=f"{name} must be a boolean",
            hint=f"Pass true or false for '{name}'.",
        )
    return value


def _optional_float(name: str, value: Any) -> float | None:
    if value is None:
        return None
    return _as_float(name, value)


def _optional_int(name: str, value: Any) -> int | None:
    if value is None:
        return None
    return _as_int(name, value)


def _clip_notes_filter(args: dict[str, Any]) -> tuple[float | None, float | None, int | None]:
    start_time = _optional_float("start_time", args.get("start_time"))
    end_time = _optional_float("end_time", args.get("end_time"))
    pitch = _optional_int("pitch", args.get("pitch"))
    _validate_clip_time_range(start_time=start_time, end_time=end_time)
    _validate_optional_pitch(pitch)
    return start_time, end_time, pitch


def _non_negative_float(name: str, value: Any) -> float:
    parsed = _as_float(name, value)
    if parsed < 0:
        raise _invalid_argument(
            message=f"{name} must be >= 0",
            hint=f"Pass a non-negative value for '{name}'.",
        )
    return parsed


def _unit_interval(name: str, value: Any) -> float:
    return _bounded_float(
        name=name,
        value=value,
        minimum=0.0,
        maximum=1.0,
        hint=f"Use a value in [0.0, 1.0] for '{name}'.",
    )


def _humanize_velocity_amount(value: Any) -> int:
    return _bounded_int(
        name="velocity",
        value=value,
        minimum=0,
        maximum=NOTE_VELOCITY_MAX,
        hint="Use a velocity amount between 0 and 127.",
    )


def _clip_quantize_grid(value: Any) -> float:
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise _invalid_argument(
                message="grid must not be empty",
                hint="Use a value like '1/16' or 0.25 beats.",
            )
        if "/" in raw:
            numerator_raw, separator, denominator_raw = raw.partition("/")
            if not separator:
                raise _invalid_argument(
                    message="grid must use a valid fraction format",
                    hint="Use a value like '1/16'.",
                )
            try:
                numerator = int(numerator_raw.strip())
                denominator = int(denominator_raw.strip())
            except ValueError as exc:
                raise _invalid_argument(
                    message="grid fraction must contain integers",
                    hint="Use a value like '1/16'.",
                ) from exc
            if numerator <= 0 or denominator <= 0:
                raise _invalid_argument(
                    message="grid fraction values must be > 0",
                    hint="Use a value like '1/16'.",
                )
            grid = (4.0 * float(numerator)) / float(denominator)
        else:
            grid = _as_float("grid", raw)
    else:
        grid = _as_float("grid", value)

    if grid <= 0:
        raise _invalid_argument(
            message="grid must be > 0",
            hint="Use a positive grid in beats.",
        )
    return float(grid)


def _validate_clip_time_range(*, start_time: float | None, end_time: float | None) -> None:
    if start_time is not None and start_time < 0:
        raise _invalid_argument(
            message=f"start_time must be >= 0, got {start_time}",
            hint="Use a non-negative start_time.",
        )
    if end_time is not None and end_time <= 0:
        raise _invalid_argument(
            message=f"end_time must be > 0, got {end_time}",
            hint="Use a positive end_time.",
        )
    if start_time is not None and end_time is not None and end_time <= start_time:
        raise _invalid_argument(
            message=(
                f"end_time must be greater than start_time (start={start_time}, end={end_time})"
            ),
            hint="Use a valid [start_time, end_time) range.",
        )


def _validate_optional_pitch(pitch: int | None) -> None:
    if pitch is None:
        return
    if pitch < NOTE_PITCH_MIN or pitch > NOTE_PITCH_MAX:
        raise _invalid_argument(
            message=f"pitch must be between {NOTE_PITCH_MIN} and {NOTE_PITCH_MAX}",
            hint="Use a valid MIDI pitch.",
        )


def _synth_type(value: Any) -> str:
    parsed = _non_empty_string("synth_type", value).lower()
    if parsed not in SUPPORTED_SYNTH_TYPES:
        raise _invalid_argument(
            message=f"synth_type must be one of {', '.join(SUPPORTED_SYNTH_TYPES)}",
            hint="Use a supported synth type.",
        )
    return parsed


def _effect_type(value: Any) -> str:
    parsed = _non_empty_string("effect_type", value).lower()
    if parsed not in SUPPORTED_EFFECT_TYPES:
        raise _invalid_argument(
            message=f"effect_type must be one of {', '.join(SUPPORTED_EFFECT_TYPES)}",
            hint="Use a supported effect type.",
        )
    return parsed


def _notes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise _invalid_argument(
            message="notes must be an array",
            hint="Pass notes as a JSON array of note objects.",
        )
    return [_parse_note(index=index, note=note) for index, note in enumerate(value)]


def _note_field_hint(name: str) -> str:
    return _NOTE_FIELD_HINTS.get(name, f"Pass a valid value for '{name}'.")


def _format_note_bound(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def _validate_note_field_bounds(*, spec: NoteFieldSpec, value: float) -> None:
    name = spec.name
    hint = _note_field_hint(name)
    if spec.minimum is not None and spec.maximum is not None:
        if value < spec.minimum or value > spec.maximum:
            raise _invalid_argument(
                message=(
                    f"{name} must be between "
                    f"{_format_note_bound(spec.minimum)} and {_format_note_bound(spec.maximum)}"
                ),
                hint=hint,
            )
        return
    if spec.minimum is not None:
        if spec.exclusive_minimum:
            if value <= spec.minimum:
                raise _invalid_argument(
                    message=f"{name} must be > {_format_note_bound(spec.minimum)}",
                    hint=hint,
                )
        elif value < spec.minimum:
            raise _invalid_argument(
                message=f"{name} must be >= {_format_note_bound(spec.minimum)}",
                hint=hint,
            )


def _parsed_note_field(*, spec: NoteFieldSpec, mapping: dict[str, Any]) -> Any:
    name = spec.name
    if spec.kind == "bool":
        value = mapping[name]
        if not isinstance(value, bool):
            raise _invalid_argument(
                message=f"{name} must be a boolean",
                hint=_note_field_hint(name),
            )
        return value
    if spec.kind == "int":
        value = _as_int(name, mapping[name])
    else:
        value = _as_float(name, mapping[name])
    _validate_note_field_bounds(spec=spec, value=value)
    return value


def _parse_note(*, index: int, note: Any) -> dict[str, Any]:
    mapping = _require_note_mapping(index=index, note=note)
    _validate_note_keys(index=index, note=mapping)
    parsed: dict[str, Any] = {}
    for spec in NOTE_FIELD_SPECS:
        if spec.name not in mapping:
            continue
        parsed[spec.name] = _parsed_note_field(spec=spec, mapping=mapping)
    return parsed


def _require_note_mapping(*, index: int, note: Any) -> dict[str, Any]:
    if not isinstance(note, dict):
        raise _invalid_argument(
            message=f"notes[{index}] must be an object",
            hint="Each note must include pitch/start_time/duration/velocity/mute.",
        )
    return note


def _validate_note_keys(*, index: int, note: dict[str, Any]) -> None:
    keys = set(note.keys())
    if not _NOTE_OPTIONAL_KEYS:
        if keys != _NOTE_REQUIRED_KEYS:
            raise _invalid_argument(
                message=f"notes[{index}] must include exactly {sorted(_NOTE_REQUIRED_KEYS)}",
                hint="Provide all required note fields and no extra keys.",
            )
        return
    missing = _NOTE_REQUIRED_KEYS - keys
    unknown = keys - _NOTE_ALL_KEYS
    if missing or unknown:
        raise _invalid_argument(
            message=(
                f"notes[{index}] must include {sorted(_NOTE_REQUIRED_KEYS)} "
                f"and may only add optional fields from {sorted(_NOTE_OPTIONAL_KEYS)}"
            ),
            hint="Provide all required note fields; only supported optional fields are allowed.",
        )


def _validate_partial_note_keys(*, index: int, note: dict[str, Any]) -> None:
    keys = set(note.keys())
    if "note_id" not in keys:
        raise _invalid_argument(
            message=f"notes[{index}] must include note_id",
            hint="Provide note_id from 'clip notes get' for each note to update.",
        )
    editable_keys = keys - {"note_id"}
    unknown = editable_keys - _NOTE_ALL_KEYS
    if unknown:
        raise _invalid_argument(
            message=f"notes[{index}] has unsupported fields: {sorted(unknown)}",
            hint=f"Use only note_id and fields from {sorted(_NOTE_ALL_KEYS)}.",
        )
    if not editable_keys:
        raise _invalid_argument(
            message=f"notes[{index}] must include at least one editable field besides note_id",
            hint=f"Provide one or more fields from {sorted(_NOTE_ALL_KEYS)}.",
        )


def _parse_partial_note(*, index: int, note: Any) -> dict[str, Any]:
    mapping = _require_note_mapping(index=index, note=note)
    _validate_partial_note_keys(index=index, note=mapping)
    note_id = _non_negative_int("note_id", mapping["note_id"])
    parsed: dict[str, Any] = {"note_id": note_id}
    for spec in NOTE_FIELD_SPECS:
        if spec.name in mapping:
            parsed[spec.name] = _parsed_note_field(spec=spec, mapping=mapping)
    return parsed


def _partial_notes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise _invalid_argument(
            message="notes must be an array",
            hint="Pass notes as a JSON array of {note_id, ...} objects.",
        )
    return [_parse_partial_note(index=index, note=note) for index, note in enumerate(value)]


def _bounded_int(
    *,
    name: str,
    value: Any,
    minimum: int,
    maximum: int,
    hint: str,
) -> int:
    parsed = _as_int(name, value)
    if parsed < minimum or parsed > maximum:
        raise _invalid_argument(
            message=f"{name} must be between {minimum} and {maximum}",
            hint=hint,
        )
    return parsed


def _parse_exclusive_string_args(
    args: dict[str, Any],
    *,
    first_key: str,
    second_key: str,
    required_hint: str,
) -> tuple[str | None, str | None]:
    first_raw = args.get(first_key)
    second_raw = args.get(second_key)
    if first_raw is None and second_raw is None:
        raise _invalid_argument(
            message=f"Exactly one of {first_key} or {second_key} must be provided",
            hint=required_hint,
        )
    if first_raw is not None and second_raw is not None:
        raise _invalid_argument(
            message=f"{first_key} and {second_key} are mutually exclusive",
            hint=f"Provide only one of {first_key} or {second_key}.",
        )
    first = _non_empty_string(first_key, first_raw) if first_raw is not None else None
    second = _non_empty_string(second_key, second_raw) if second_raw is not None else None
    return first, second


def _ref_object(name: str, value: Any, *, allowed_modes: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _invalid_argument(
            message=f"{name} must be an object",
            hint=f"Pass a JSON object for '{name}'.",
        )
    mode = _non_empty_string(f"{name}.mode", value.get("mode"))
    if mode not in allowed_modes:
        raise _invalid_argument(
            message=f"{name}.mode must be one of {', '.join(sorted(allowed_modes))}",
            hint=f"Use a supported selector mode for '{name}'.",
        )

    def require_keys(expected_keys: set[str]) -> None:
        actual_keys = set(value)
        if actual_keys == expected_keys:
            return
        raise _invalid_argument(
            message=f"{name} must include exactly {sorted(expected_keys)} for mode {mode!r}",
            hint=f"Provide only the fields required by the '{mode}' selector mode.",
        )

    if mode == "index":
        require_keys({"mode", "index"})
        return {"mode": mode, "index": _track_index(f"{name}.index", value.get("index"))}
    if mode == "name":
        require_keys({"mode", "name"})
        return {"mode": mode, "name": _non_empty_string(f"{name}.name", value.get("name"))}
    if mode == "selected":
        require_keys({"mode"})
        return {"mode": mode}
    if mode == "query":
        require_keys({"mode", "query"})
        return {"mode": mode, "query": _non_empty_string(f"{name}.query", value.get("query"))}
    if mode == "stable_ref":
        require_keys({"mode", "stable_ref"})
        return {
            "mode": mode,
            "stable_ref": _non_empty_string(f"{name}.stable_ref", value.get("stable_ref")),
        }
    if mode == "key":
        require_keys({"mode", "key"})
        return {"mode": mode, "key": _non_empty_string(f"{name}.key", value.get("key"))}
    raise AssertionError(f"unsupported mode: {mode}")


def _track_ref(value: Any) -> dict[str, Any]:
    return _ref_object(
        "track_ref",
        value,
        allowed_modes={"index", "name", "selected", "query", "stable_ref"},
    )


def _device_ref(value: Any) -> dict[str, Any]:
    return _ref_object(
        "device_ref",
        value,
        allowed_modes={"index", "name", "selected", "query", "stable_ref"},
    )


def _parameter_ref(value: Any) -> dict[str, Any]:
    return _ref_object(
        "parameter_ref",
        value,
        allowed_modes={"index", "name", "query", "stable_ref", "key"},
    )


def _device_parameter_args(
    args: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], float]:
    track = _track_ref(args.get("track_ref"))
    device = _device_ref(args.get("device_ref"))
    parameter = _parameter_ref(args.get("parameter_ref"))
    value = _as_float("value", args.get("value"))
    return track, device, parameter, value


def _envelope_points(value: Any) -> list[dict[str, float]]:
    if not isinstance(value, list) or not value:
        raise _invalid_argument(
            message="points must be a non-empty array",
            hint="Pass points as a JSON array of {time, value} objects.",
        )
    parsed: list[dict[str, float]] = []
    previous_time: float | None = None
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item.keys()) != {"time", "value"}:
            raise _invalid_argument(
                message=f"points[{index}] must be an object with exactly 'time' and 'value'",
                hint='Each point must be {"time": <float >= 0>, "value": <float>}.',
            )
        time = _as_float(f"points[{index}].time", item.get("time"))
        if time < 0:
            raise _invalid_argument(
                message=f"points[{index}].time must be >= 0",
                hint="Use non-negative, strictly increasing time values.",
            )
        if previous_time is not None and time <= previous_time:
            raise _invalid_argument(
                message=f"points[{index}].time must be strictly increasing",
                hint="Sort points by time and remove duplicate time values.",
            )
        point_value = _as_float(f"points[{index}].value", item.get("value"))
        parsed.append({"time": time, "value": point_value})
        previous_time = time
    return parsed


def _envelope_mode(value: Any) -> str:
    if value is None:
        return "replace"
    mode = _non_empty_string("mode", value)
    if mode != "replace":
        raise _invalid_argument(
            message=f"mode must be 'replace', got {mode!r}",
            hint="Only mode=replace is currently supported.",
        )
    return mode


def _clip_envelope_set_args(
    args: dict[str, Any],
) -> tuple[int, int, dict[str, Any], dict[str, Any], list[dict[str, float]], str]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    device = _device_ref(args.get("device_ref"))
    parameter = _parameter_ref(args.get("parameter_ref"))
    points = _envelope_points(args.get("points"))
    mode = _envelope_mode(args.get("mode"))
    return track, clip, device, parameter, points, mode


def _clip_envelope_clear_args(
    args: dict[str, Any],
) -> tuple[int, int, dict[str, Any] | None, dict[str, Any] | None, bool]:
    track = _track_index("track", args.get("track"))
    clip = _track_index("clip", args.get("clip"))
    clear_all = _as_bool("clear_all", args.get("clear_all", False))
    if clear_all:
        if args.get("device_ref") is not None or args.get("parameter_ref") is not None:
            raise _invalid_argument(
                message="device_ref/parameter_ref must not be set when clear_all is true",
                hint="Pass either clear_all=true or device_ref+parameter_ref, not both.",
            )
        return track, clip, None, None, True
    device = _device_ref(args.get("device_ref"))
    parameter = _parameter_ref(args.get("parameter_ref"))
    return track, clip, device, parameter, False


def _device_ref_args(args: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    track_ref = _track_ref(args.get("track_ref"))
    device_ref = _device_ref(args.get("device_ref"))
    return track_ref, device_ref


def _device_macro_set_args(
    args: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], int, float]:
    track_ref = _track_ref(args.get("track_ref"))
    device_ref = _device_ref(args.get("device_ref"))
    macro_index = _track_index("macro_index", args.get("macro_index"))
    value = _as_float("value", args.get("value"))
    return track_ref, device_ref, macro_index, value
