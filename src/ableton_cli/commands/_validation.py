from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..errors import AppError, ExitCode

NOTE_KEYS = {"pitch", "start_time", "duration", "velocity", "mute"}


def invalid_argument(message: str, hint: str) -> AppError:
    return AppError(
        error_code="INVALID_ARGUMENT",
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
    )


def require_non_negative(name: str, value: int, *, hint: str) -> int:
    if value < 0:
        raise invalid_argument(message=f"{name} must be >= 0, got {value}", hint=hint)
    return value


def require_minus_one_or_non_negative(name: str, value: int, *, hint: str) -> int:
    if value < -1:
        raise invalid_argument(message=f"{name} must be >= -1, got {value}", hint=hint)
    return value


def require_positive_float(name: str, value: float, *, hint: str) -> float:
    if value <= 0:
        raise invalid_argument(message=f"{name} must be > 0, got {value}", hint=hint)
    return value


def require_non_empty_string(name: str, value: str, *, hint: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise invalid_argument(message=f"{name} must not be empty", hint=hint)
    return stripped


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
                "end_time must be greater than start_time "
                f"(start={start_time}, end={end_time})"
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


def _note_field_int(note: dict[str, Any], name: str) -> int:
    value = note[name]
    if not isinstance(value, int):
        raise invalid_argument(
            message=f"notes[].{name} must be an integer",
            hint="Use numeric values for pitch and velocity.",
        )
    return value


def _note_field_float(note: dict[str, Any], name: str) -> float:
    value = note[name]
    if not isinstance(value, (int, float)):
        raise invalid_argument(
            message=f"notes[].{name} must be a number",
            hint="Use numeric values for note timing fields.",
        )
    return float(value)


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

        keys = set(item.keys())
        if keys != NOTE_KEYS:
            raise invalid_argument(
                message=f"notes[{index}] must include exactly {sorted(NOTE_KEYS)}",
                hint="Provide all required note fields and no extra keys.",
            )

        pitch = _note_field_int(item, "pitch")
        if pitch < 0 or pitch > 127:
            raise invalid_argument(
                message=f"notes[{index}].pitch must be between 0 and 127",
                hint="Use a valid MIDI pitch.",
            )

        start_time = _note_field_float(item, "start_time")
        if start_time < 0:
            raise invalid_argument(
                message=f"notes[{index}].start_time must be >= 0",
                hint="Use a non-negative note start time.",
            )

        duration = _note_field_float(item, "duration")
        if duration <= 0:
            raise invalid_argument(
                message=f"notes[{index}].duration must be > 0",
                hint="Use a positive note duration.",
            )

        velocity = _note_field_int(item, "velocity")
        if velocity < 1 or velocity > 127:
            raise invalid_argument(
                message=f"notes[{index}].velocity must be between 1 and 127",
                hint="Use a valid MIDI velocity.",
            )

        mute = item["mute"]
        if not isinstance(mute, bool):
            raise invalid_argument(
                message=f"notes[{index}].mute must be boolean",
                hint="Set mute to true or false.",
            )

        sanitized.append(
            {
                "pitch": pitch,
                "start_time": start_time,
                "duration": duration,
                "velocity": velocity,
                "mute": mute,
            }
        )

    return sanitized


def parse_notes_input(notes_json: str | None, notes_file: str | None) -> list[dict[str, Any]]:
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
        return parse_notes_json(notes_json)

    assert notes_file is not None
    path = Path(notes_file)
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise invalid_argument(
            message=f"notes_file could not be read: {path}",
            hint="Pass a readable UTF-8 JSON file path for --notes-file.",
        ) from exc
    return parse_notes_json(payload)
