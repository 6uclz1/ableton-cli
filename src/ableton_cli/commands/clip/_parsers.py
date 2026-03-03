from __future__ import annotations

from collections.abc import Callable

from .._validation import (
    invalid_argument,
    require_non_empty_string,
    require_non_negative,
    resolve_uri_or_path_target,
)


def parse_duplicate_destinations(
    *,
    src_clip: int,
    dst_clip: int | None,
    to: str | None,
) -> tuple[int | None, list[int] | None]:
    if dst_clip is None and to is None:
        raise invalid_argument(
            message="Either dst_clip or --to must be provided",
            hint="Provide one destination clip slot or --to 2,4,5.",
        )
    if dst_clip is not None and to is not None:
        raise invalid_argument(
            message="dst_clip and --to are mutually exclusive",
            hint="Use either a single dst_clip argument or --to for multiple destinations.",
        )
    if dst_clip is not None:
        normalized_dst_clip = require_non_negative(
            "dst_clip",
            dst_clip,
            hint="Use a valid destination clip slot index.",
        )
        if normalized_dst_clip == src_clip:
            raise invalid_argument(
                message=f"Destination clip index must differ from src_clip ({src_clip})",
                hint="Use a destination index that is not the source clip.",
            )
        return normalized_dst_clip, None

    assert to is not None
    parsed = require_non_empty_string(
        "to",
        to,
        hint="Use comma-separated clip slots like 2,4,5.",
    )
    destinations = _parse_destination_csv(
        src_clip=src_clip,
        raw_values=parsed.split(","),
        source_label="--to",
        empty_hint="Use comma-separated indexes like --to 2,4,5.",
    )
    return None, destinations


def parse_place_pattern_destinations(
    *,
    src_clip: int,
    scenes: str,
    load_scenes: Callable[[], dict[str, object]],
) -> list[int]:
    selectors = _parse_scene_selectors(scenes)
    destinations: list[int] = []
    seen: set[int] = set()
    scenes_payload: dict[str, object] | None = None

    for selector in selectors:
        indexes, scenes_payload = _resolve_scene_selector(
            selector=selector,
            load_scenes=load_scenes,
            scenes_payload=scenes_payload,
        )
        for value in indexes:
            _append_destination_index(
                src_clip=src_clip,
                value=value,
                seen=seen,
                destinations=destinations,
                source_label="--scenes",
            )

    if not destinations:
        raise invalid_argument(
            message="--scenes must include at least one destination",
            hint="Use scene selectors like 2,4 or Intro,Drop.",
        )
    return destinations


def parse_clip_name_assignments(mapping: str) -> list[tuple[int, str]]:
    parsed = require_non_empty_string(
        "map",
        mapping,
        hint="Use clip:name pairs like 1:Main,2:Var.",
    )
    tokens = [token.strip() for token in parsed.split(",")]
    if any(not token for token in tokens):
        raise invalid_argument(
            message="--map contains an empty assignment",
            hint="Use clip:name pairs like 1:Main,2:Var.",
        )

    assignments: list[tuple[int, str]] = []
    seen: set[int] = set()
    for token in tokens:
        assignments.append(_parse_clip_name_assignment(token, seen))

    if not assignments:
        raise invalid_argument(
            message="--map must include at least one clip:name pair",
            hint="Use clip:name pairs like 1:Main,2:Var.",
        )
    return assignments


def parse_cut_to_drum_rack_source(
    *,
    source_track: int | None,
    source_clip: int | None,
    source: str | None,
) -> tuple[int | None, int | None, str | None, str | None]:
    has_session_source = source_track is not None or source_clip is not None
    has_browser_source = source is not None

    if has_session_source and has_browser_source:
        raise invalid_argument(
            message="--source-track/--source-clip and --source are mutually exclusive",
            hint="Use either session clip source or browser source.",
        )

    if has_browser_source:
        assert source is not None
        parsed_source = require_non_empty_string(
            "source",
            source,
            hint="Pass a browser URI/path like sounds/Loop.wav or clip:loop.",
        )
        source_uri, source_path = resolve_uri_or_path_target(
            target=parsed_source,
            name="source",
            hint="Use a browser URI/path like sounds/Loop.wav or clip:loop.",
        )
        return None, None, source_uri, source_path

    if not has_session_source:
        raise invalid_argument(
            message="Either --source-track/--source-clip or --source must be provided",
            hint="Use session clip source or browser source.",
        )
    if source_track is None or source_clip is None:
        raise invalid_argument(
            message="--source-track and --source-clip must be provided together",
            hint="Provide both --source-track and --source-clip for session clip source.",
        )

    valid_source_track = require_non_negative(
        "source_track",
        source_track,
        hint="Use a valid source track index from 'ableton-cli tracks list'.",
    )
    valid_source_clip = require_non_negative(
        "source_clip",
        source_clip,
        hint="Use a valid source clip slot index.",
    )
    return valid_source_track, valid_source_clip, None, None


def parse_cut_to_drum_rack_slice_spec(
    *,
    grid: str | None,
    slice_count: int | None,
) -> tuple[str | None, int | None]:
    if grid is None and slice_count is None:
        raise invalid_argument(
            message="Either --grid or --slice-count must be provided",
            hint="Choose one slicing mode with --grid or --slice-count.",
        )
    if grid is not None and slice_count is not None:
        raise invalid_argument(
            message="--grid and --slice-count are mutually exclusive",
            hint="Use either --grid or --slice-count.",
        )
    if grid is not None:
        valid_grid = require_non_empty_string(
            "grid",
            grid,
            hint="Use a grid like 1/16 or 0.25.",
        )
        return valid_grid, None

    assert slice_count is not None
    if slice_count <= 0:
        raise invalid_argument(
            message=f"slice_count must be > 0, got {slice_count}",
            hint="Use a positive --slice-count.",
        )
    return None, slice_count


def parse_arrangement_scene_durations(scenes: str) -> list[dict[str, float]]:
    parsed = require_non_empty_string(
        "scenes",
        scenes,
        hint="Use scene:duration pairs like 0:24,1:48.",
    )
    tokens = [token.strip() for token in parsed.split(",")]
    if any(not token for token in tokens):
        raise invalid_argument(
            message="--scenes contains an empty entry",
            hint="Use scene:duration pairs like 0:24,1:48.",
        )

    parsed_entries: list[dict[str, float]] = []
    for token in tokens:
        if ":" not in token:
            raise invalid_argument(
                message=f"Invalid scene:duration pair in --scenes: {token!r}",
                hint="Use scene:duration pairs like 0:24,1:48.",
            )
        scene_raw, duration_raw = token.split(":", 1)
        scene_text = scene_raw.strip()
        duration_text = duration_raw.strip()
        if not scene_text or not duration_text:
            raise invalid_argument(
                message=f"Invalid scene:duration pair in --scenes: {token!r}",
                hint="Use scene:duration pairs like 0:24,1:48.",
            )
        try:
            scene_index = int(scene_text)
        except ValueError as exc:
            raise invalid_argument(
                message=f"scene index must be an integer, got {scene_text!r}",
                hint="Use scene indexes like 0:24,1:48.",
            ) from exc
        if scene_index < 0:
            raise invalid_argument(
                message=f"scene index must be >= 0, got {scene_index}",
                hint="Use non-negative scene indexes in --scenes.",
            )
        try:
            duration_beats = float(duration_text)
        except ValueError as exc:
            raise invalid_argument(
                message=f"duration must be numeric, got {duration_text!r}",
                hint="Use beat durations like 0:24,1:48.",
            ) from exc
        if duration_beats <= 0:
            raise invalid_argument(
                message=f"duration must be > 0, got {duration_beats}",
                hint="Use positive beat durations in --scenes.",
            )
        parsed_entries.append({"scene": scene_index, "duration_beats": duration_beats})

    return parsed_entries


def _parse_destination_csv(
    *,
    src_clip: int,
    raw_values: list[str],
    source_label: str,
    empty_hint: str,
) -> list[int]:
    destinations: list[int] = []
    seen: set[int] = set()
    for raw_value in raw_values:
        token = raw_value.strip()
        if not token:
            continue
        try:
            value = int(token)
        except ValueError as exc:
            raise invalid_argument(
                message=f"Invalid destination clip index in {source_label}: {token!r}",
                hint="Use comma-separated non-negative integers like 2,4,5.",
            ) from exc
        _append_destination_index(
            src_clip=src_clip,
            value=value,
            seen=seen,
            destinations=destinations,
            source_label=source_label,
        )
    if not destinations:
        raise invalid_argument(
            message=f"{source_label} must include at least one destination clip index",
            hint=empty_hint,
        )
    return destinations


def _append_destination_index(
    *,
    src_clip: int,
    value: int,
    seen: set[int],
    destinations: list[int],
    source_label: str,
) -> None:
    if value < 0:
        raise invalid_argument(
            message=f"Destination clip index must be >= 0, got {value}",
            hint="Use non-negative destination clip indexes.",
        )
    if value == src_clip:
        raise invalid_argument(
            message=f"Destination clip index must differ from src_clip ({src_clip})",
            hint="Use destination indexes that are not the source clip.",
        )
    if value in seen:
        raise invalid_argument(
            message=f"Duplicate destination clip index in {source_label}: {value}",
            hint="Remove duplicated destination indexes.",
        )
    seen.add(value)
    destinations.append(value)


def _parse_scene_selectors(scenes: str) -> list[str]:
    parsed = require_non_empty_string(
        "scenes",
        scenes,
        hint="Use scene selectors like 2,4,6 or 2-6 or Intro,Drop.",
    )
    selectors = [token.strip() for token in parsed.split(",")]
    if any(not selector for selector in selectors):
        raise invalid_argument(
            message="--scenes contains an empty selector",
            hint="Use comma-separated selectors like 2,4 or Intro,Drop.",
        )
    return selectors


def _resolve_scene_selector(
    *,
    selector: str,
    load_scenes: Callable[[], dict[str, object]],
    scenes_payload: dict[str, object] | None,
) -> tuple[list[int], dict[str, object] | None]:
    parsed_range = _parse_scene_token_as_range(selector)
    if parsed_range is not None:
        start, end = parsed_range
        return list(range(start, end + 1)), scenes_payload

    if selector.isdigit():
        return [int(selector)], scenes_payload

    resolved_payload = scenes_payload if scenes_payload is not None else load_scenes()
    scene_index = _extract_scene_index_by_name(scenes_payload=resolved_payload, name=selector)
    return [scene_index], resolved_payload


def _parse_scene_token_as_range(token: str) -> tuple[int, int] | None:
    parts = token.split("-", 1)
    if len(parts) != 2:
        return None
    start_text = parts[0].strip()
    end_text = parts[1].strip()
    if not start_text or not end_text:
        return None
    if not start_text.isdigit() or not end_text.isdigit():
        return None
    start = int(start_text)
    end = int(end_text)
    if end < start:
        raise invalid_argument(
            message=f"Scene range must be ascending, got {token!r}",
            hint="Use scene ranges like 2-6.",
        )
    return start, end


def _extract_scene_index_by_name(
    *,
    scenes_payload: dict[str, object],
    name: str,
) -> int:
    raw_scenes = scenes_payload.get("scenes")
    if not isinstance(raw_scenes, list):
        raise invalid_argument(
            message="scenes list response is invalid",
            hint="Retry after confirming Ableton scenes are available.",
        )

    normalized_name = name.casefold()
    matches = [
        scene_index
        for raw_scene in raw_scenes
        if (scene_index := _scene_index_for_name(raw_scene, normalized_name)) is not None
    ]

    if not matches:
        raise invalid_argument(
            message=f"Unknown scene name in --scenes: {name!r}",
            hint="Use scene indexes/ranges or existing scene names from 'ableton-cli scenes list'.",
        )
    if len(matches) > 1:
        raise invalid_argument(
            message=f"Scene name is ambiguous in --scenes: {name!r}",
            hint="Use numeric scene indexes for duplicated scene names.",
        )
    return matches[0]


def _scene_index_for_name(raw_scene: object, normalized_name: str) -> int | None:
    if not isinstance(raw_scene, dict):
        return None

    raw_index = raw_scene.get("index")
    if not isinstance(raw_index, int) or raw_index < 0:
        return None

    raw_scene_name = raw_scene.get("name")
    if not isinstance(raw_scene_name, str):
        return None

    if raw_scene_name.strip().casefold() != normalized_name:
        return None

    return raw_index


def _parse_clip_name_assignment(token: str, seen: set[int]) -> tuple[int, str]:
    if ":" not in token:
        raise invalid_argument(
            message=f"Invalid clip:name pair in --map: {token!r}",
            hint="Use clip:name pairs like 1:Main,2:Var.",
        )

    clip_token, name_token = token.split(":", 1)
    clip = _parse_clip_assignment_index(clip_token)
    if clip in seen:
        raise invalid_argument(
            message=f"Duplicate clip index in --map: {clip}",
            hint="Assign each clip index once in --map.",
        )

    seen.add(clip)
    name = require_non_empty_string(
        "name",
        name_token,
        hint="Use non-empty names in --map, e.g. 1:Main.",
    )
    return clip, name


def _parse_clip_assignment_index(clip_token: str) -> int:
    clip_raw = clip_token.strip()
    try:
        clip = int(clip_raw)
    except ValueError as exc:
        raise invalid_argument(
            message=f"Invalid clip index in --map: {clip_raw!r}",
            hint="Use non-negative clip indexes like 1:Main.",
        ) from exc
    return require_non_negative("clip", clip, hint="Use non-negative clip indexes in --map.")
