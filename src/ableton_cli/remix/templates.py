from __future__ import annotations

from typing import Any

from .manifest import remix_error

TEMPLATES: dict[str, list[tuple[str, int]]] = {
    "anime-club": [
        ("intro", 8),
        ("verse_chop", 16),
        ("build", 16),
        ("chorus_drop", 32),
        ("breakdown", 16),
        ("final_drop", 32),
        ("outro", 8),
    ],
    "anime-dnb": [
        ("intro", 16),
        ("pre_drop_vocal", 8),
        ("drop", 32),
        ("bridge", 16),
        ("second_drop", 32),
    ],
    "anime-future-bass": [
        ("intro_pad", 8),
        ("vocal_verse", 16),
        ("build", 8),
        ("supersaw_drop", 32),
    ],
}


def template_sections(style: str, bars: str | None = None) -> list[dict[str, Any]]:
    if bars is not None:
        return _parse_bars(bars)
    key = style.strip()
    if key not in TEMPLATES:
        raise remix_error(
            message=f"unknown remix template: {style}",
            hint=f"Use one of: {', '.join(sorted(TEMPLATES))}.",
        )
    start_bar = 1
    sections: list[dict[str, Any]] = []
    for name, length in TEMPLATES[key]:
        end_bar = start_bar + length - 1
        sections.append({"name": name, "start_bar": start_bar, "end_bar": end_bar})
        start_bar = end_bar + 1
    return sections


def _parse_bars(bars: str) -> list[dict[str, Any]]:
    start_bar = 1
    sections: list[dict[str, Any]] = []
    for raw in bars.split(","):
        name, _, length_raw = raw.partition(":")
        if not name.strip() or not length_raw.strip():
            raise remix_error(
                message=f"invalid bars spec: {raw!r}",
                hint="Use bars like intro:8,build:16,drop:32.",
            )
        try:
            length = int(length_raw)
        except ValueError as exc:
            raise remix_error(
                message=f"bar length must be an integer: {raw!r}",
                hint="Use bars like intro:8.",
            ) from exc
        if length <= 0:
            raise remix_error(
                message=f"bar length must be > 0: {raw!r}", hint="Use positive bar counts."
            )
        end_bar = start_bar + length - 1
        sections.append({"name": name.strip(), "start_bar": start_bar, "end_bar": end_bar})
        start_bar = end_bar + 1
    if not sections:
        raise remix_error(message="bars must not be empty", hint="Use bars like intro:8,drop:32.")
    return sections
