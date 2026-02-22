from __future__ import annotations

from typing import Any

from .command_backend_contract import (
    MAX_BPM,
    MAX_PANNING,
    MAX_VOLUME,
    MIN_BPM,
    MIN_PANNING,
    MIN_VOLUME,
    NOTE_KEYS,
    NOTE_PITCH_MAX,
    NOTE_PITCH_MIN,
    NOTE_VELOCITY_MAX,
    NOTE_VELOCITY_MIN,
    CommandError,
)
from .effect_specs import SUPPORTED_EFFECT_TYPES
from .synth_specs import SUPPORTED_SYNTH_TYPES


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


def _parse_note(*, index: int, note: Any) -> dict[str, Any]:
    mapping = _require_note_mapping(index=index, note=note)
    _validate_note_keys(index=index, note=mapping)

    pitch = _bounded_int(
        name="pitch",
        value=mapping["pitch"],
        minimum=NOTE_PITCH_MIN,
        maximum=NOTE_PITCH_MAX,
        hint="Use a valid MIDI pitch.",
    )
    velocity = _bounded_int(
        name="velocity",
        value=mapping["velocity"],
        minimum=NOTE_VELOCITY_MIN,
        maximum=NOTE_VELOCITY_MAX,
        hint="Use a valid MIDI velocity.",
    )

    start_time = _as_float("start_time", mapping["start_time"])
    if start_time < 0:
        raise _invalid_argument(
            message="start_time must be >= 0",
            hint="Use a non-negative note start time.",
        )

    duration = _as_float("duration", mapping["duration"])
    if duration <= 0:
        raise _invalid_argument(
            message="duration must be > 0",
            hint="Use a positive note duration.",
        )

    mute = mapping["mute"]
    if not isinstance(mute, bool):
        raise _invalid_argument(
            message="mute must be a boolean",
            hint="Set mute to true or false.",
        )

    return {
        "pitch": pitch,
        "start_time": start_time,
        "duration": duration,
        "velocity": velocity,
        "mute": mute,
    }


def _require_note_mapping(*, index: int, note: Any) -> dict[str, Any]:
    if not isinstance(note, dict):
        raise _invalid_argument(
            message=f"notes[{index}] must be an object",
            hint="Each note must include pitch/start_time/duration/velocity/mute.",
        )
    return note


def _validate_note_keys(*, index: int, note: dict[str, Any]) -> None:
    keys = set(note.keys())
    if keys != NOTE_KEYS:
        raise _invalid_argument(
            message=f"notes[{index}] must include exactly {sorted(NOTE_KEYS)}",
            hint="Provide all required note fields and no extra keys.",
        )


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


def _device_parameter_args(args: dict[str, Any]) -> tuple[int, int, int, float]:
    track = _track_index("track", args.get("track"))
    device = _track_index("device", args.get("device"))
    parameter = _track_index("parameter", args.get("parameter"))
    value = _as_float("value", args.get("value"))
    return track, device, parameter, value
