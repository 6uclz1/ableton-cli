"""Remix pattern generation.

Turns manifest state (target key, sections) plus explicit arguments into
real notes-json via the pure :mod:`~ableton_cli.pattern_library` and
:mod:`~ableton_cli.harmony` layers, records the result in the manifest's
``generated_assets`` list, and builds the batch steps needed to write the
pattern into a clip.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from ..harmony import Chord, HarmonyError, parse_key, parse_progression, progression_notes
from ..pattern_library import (
    BEATS_PER_BAR,
    PatternLibraryError,
    bass_pattern_notes,
    bass_patterns,
    drum_pattern_notes,
    drum_styles,
)
from .manifest import load_manifest, remix_error, resolve_manifest_path, save_manifest

MAX_BARS = 256
DEFAULT_BARS = 4
DEFAULT_BASS_OCTAVE_PITCH = 36  # C1 in Live's octave naming.
DEFAULT_CHORD_BASE_PITCH = 60  # C3 in Live's octave naming.


def _validated_bars(bars: int) -> int:
    if not (1 <= bars <= MAX_BARS):
        raise remix_error(
            message=f"bars must be between 1 and {MAX_BARS}, got {bars}",
            hint=f"Use --bars in [1, {MAX_BARS}].",
        )
    return bars


def _section_bars(manifest: dict[str, Any], section: str) -> int:
    for entry in manifest.get("sections", []):
        if entry.get("name") == section:
            return int(entry["end_bar"]) - int(entry["start_bar"]) + 1
    known = sorted(str(entry.get("name")) for entry in manifest.get("sections", []))
    raise remix_error(
        message=f"unknown section: {section!r}",
        hint=f"Run 'ableton-cli remix plan' first, or use one of: {', '.join(known) or '(none)'}.",
    )


def resolve_bars(manifest: dict[str, Any], *, section: str | None, bars: int | None) -> int:
    if section is not None:
        if bars is not None:
            raise remix_error(
                message="pass either --section or --bars, not both",
                hint="Section length already determines the bar count.",
            )
        return _validated_bars(_section_bars(manifest, section))
    return _validated_bars(DEFAULT_BARS if bars is None else bars)


def resolve_key(manifest: dict[str, Any], key: str | None):  # noqa: ANN201 - harmony.Key
    text = key if key is not None else manifest.get("target_key")
    if not text:
        raise remix_error(
            message="no key available",
            hint="Pass --key 'F minor' or run 'ableton-cli remix set-target --key'.",
        )
    try:
        return parse_key(str(text))
    except HarmonyError as exc:
        raise remix_error(
            message=str(exc), hint="Use a key like 'F minor' or 'Bb dorian'."
        ) from exc


def _rng(seed: int | None) -> random.Random | None:
    return None if seed is None else random.Random(seed)


def _record_asset(manifest_path: Path, manifest: dict[str, Any], asset: dict[str, Any]) -> None:
    assets = list(manifest.get("generated_assets", []))
    assets = [item for item in assets if not _same_slot(item, asset)]
    assets.append(asset)
    manifest["generated_assets"] = assets
    save_manifest(manifest_path, manifest)


def _same_slot(existing: dict[str, Any], asset: dict[str, Any]) -> bool:
    return existing.get("kind") == asset.get("kind") and existing.get("section") == asset.get(
        "section"
    )


def latest_asset(
    manifest: dict[str, Any], kind: str, *, section: str | None
) -> dict[str, Any] | None:
    for item in reversed(list(manifest.get("generated_assets", []))):
        if item.get("kind") != kind:
            continue
        if section is not None and item.get("section") not in (section, None):
            continue
        return item
    return None


def apply_steps(
    *,
    track: int,
    clip: int,
    length_beats: float,
    notes: list[dict[str, Any]],
    label: str,
) -> list[dict[str, Any]]:
    """Batch steps that create the target clip and write ``notes`` into it."""
    return [
        {
            "name": "create_clip",
            "args": {"track": track, "clip": clip, "length": length_beats},
            "label": f"{label}: create clip",
        },
        {
            "name": "replace_clip_notes",
            "args": {"track": track, "clip": clip, "notes": notes},
            "label": f"{label}: write notes",
        },
    ]


def generate_drums(
    project: str | Path,
    *,
    style: str,
    section: str | None = None,
    bars: int | None = None,
    humanize: float = 0.0,
    seed: int | None = None,
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    bar_count = resolve_bars(manifest, section=section, bars=bars)
    try:
        notes = drum_pattern_notes(style, bars=bar_count, humanize=humanize, rng=_rng(seed))
    except PatternLibraryError as exc:
        raise remix_error(
            message=str(exc), hint=f"Use --style with one of: {', '.join(drum_styles())}."
        ) from exc

    asset = {
        "kind": "drums",
        "style": style,
        "section": section,
        "bars": bar_count,
        "length_beats": bar_count * BEATS_PER_BAR,
        "seed": seed,
        "note_count": len(notes),
    }
    _record_asset(manifest_path, manifest, asset)
    return {"project": str(manifest_path), **asset, "pattern": {"notes": notes}}


def _bass_root_pitches(
    manifest: dict[str, Any],
    *,
    key: str | None,
    bars: int,
    section: str | None,
    follow_chords: bool,
) -> tuple[list[int], str, str]:
    """Roots per bar, where they came from, and the key label to record.

    A generated chord progression already carries the harmony, so the key
    is only resolved (and only required) when there is nothing to follow.
    """
    if follow_chords:
        chords_asset = latest_asset(manifest, "chords", section=section) or {}
        roots = list(chords_asset.get("bar_root_pitch_classes") or [])
        if roots:
            pitches = [_bass_pitch(roots[bar % len(roots)]) for bar in range(bars)]
            return pitches, "chords", str(chords_asset.get("key", ""))
    resolved_key = resolve_key(manifest, key)
    label = f"{resolved_key.root} {resolved_key.scale}"
    return [_bass_pitch(resolved_key.root_pitch_class)] * bars, "key", label


def _bass_pitch(pitch_class: int) -> int:
    return DEFAULT_BASS_OCTAVE_PITCH + (pitch_class % 12)


def generate_bass(
    project: str | Path,
    *,
    pattern: str,
    key: str | None = None,
    section: str | None = None,
    bars: int | None = None,
    follow_chords: bool = True,
    humanize: float = 0.0,
    seed: int | None = None,
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    bar_count = resolve_bars(manifest, section=section, bars=bars)
    root_pitches, root_source, key_label = _bass_root_pitches(
        manifest, key=key, bars=bar_count, section=section, follow_chords=follow_chords
    )
    try:
        notes = bass_pattern_notes(
            pattern,
            root_pitches=root_pitches,
            bars=bar_count,
            humanize=humanize,
            rng=_rng(seed),
        )
    except PatternLibraryError as exc:
        raise remix_error(
            message=str(exc), hint=f"Use --pattern with one of: {', '.join(bass_patterns())}."
        ) from exc

    asset = {
        "kind": "bass",
        "pattern_name": pattern,
        "section": section,
        "key": key_label,
        "root_source": root_source,
        "bars": bar_count,
        "length_beats": bar_count * BEATS_PER_BAR,
        "seed": seed,
        "note_count": len(notes),
    }
    _record_asset(manifest_path, manifest, asset)
    return {"project": str(manifest_path), **asset, "pattern": {"notes": notes}}


def _parsed_progression(progression: str, key) -> list[Chord]:  # noqa: ANN001 - harmony.Key
    try:
        return parse_progression(progression, key=key)
    except HarmonyError as exc:
        raise remix_error(
            message=str(exc),
            hint="Use roman numerals like 'i-VI-III-VII' with --key, or symbols like 'Cmaj7 A7'.",
        ) from exc


def generate_chords(
    project: str | Path,
    *,
    progression: str,
    key: str | None = None,
    section: str | None = None,
    bars_per_chord: float = 1.0,
    voicing: str = "close",
    base_pitch: int = DEFAULT_CHORD_BASE_PITCH,
    voice_leading: bool = True,
) -> dict[str, Any]:
    manifest_path = resolve_manifest_path(project)
    manifest = load_manifest(manifest_path)
    resolved_key = resolve_key(manifest, key)
    if bars_per_chord <= 0:
        raise remix_error(
            message=f"bars_per_chord must be > 0, got {bars_per_chord}",
            hint="Use --bars-per-chord > 0.",
        )
    chords = _parsed_progression(progression, resolved_key)
    try:
        notes = progression_notes(
            chords,
            beats_per_chord=bars_per_chord * BEATS_PER_BAR,
            base_pitch=base_pitch,
            voicing=voicing,
            voice_leading=voice_leading,
        )
    except HarmonyError as exc:
        raise remix_error(
            message=str(exc), hint="Try a different --voicing or a lower --base-pitch."
        ) from exc

    bar_count = _validated_bars(max(1, round(len(chords) * bars_per_chord)))
    asset = {
        "kind": "chords",
        "section": section,
        "progression": progression,
        "chords": [chord.to_dict() for chord in chords],
        "bar_root_pitch_classes": _bar_roots(chords, bars_per_chord=bars_per_chord, bars=bar_count),
        "key": f"{resolved_key.root} {resolved_key.scale}",
        "voicing": voicing,
        "bars": bar_count,
        "length_beats": bar_count * BEATS_PER_BAR,
        "note_count": len(notes),
    }
    _record_asset(manifest_path, manifest, asset)
    return {"project": str(manifest_path), **asset, "pattern": {"notes": notes}}


def _bar_roots(chords: list[Chord], *, bars_per_chord: float, bars: int) -> list[int]:
    roots: list[int] = []
    for bar in range(bars):
        index = min(int(bar / bars_per_chord), len(chords) - 1)
        roots.append(chords[index].bass if chords[index].bass is not None else chords[index].root)
    return roots
