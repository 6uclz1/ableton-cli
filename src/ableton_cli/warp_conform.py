from __future__ import annotations

from typing import Any

from .errors import AppError, ErrorCode, ExitCode

WARP_MODE_VALUES: dict[str, int] = {
    "beats": 0,
    "tones": 1,
    "texture": 2,
    "re-pitch": 3,
    "complex": 4,
    "rex": 5,
    "complex-pro": 6,
}

WARP_PROFILES: dict[str, tuple[str, ...]] = {
    "full-mix": ("complex-pro", "complex"),
    "vocal": ("complex-pro", "tones"),
    "drums": ("beats", "re-pitch"),
    "bass": ("tones", "complex"),
    "pad": ("texture", "complex"),
    "fx": ("texture", "re-pitch"),
    "pitch-locked-draft": ("complex", "beats"),
    "artifact-min": ("re-pitch", "complex"),
}


def _invalid_argument(message: str, hint: str, **details: Any) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
        details=details,
    )


def _positive_bpm(name: str, value: float) -> float:
    bpm = float(value)
    if bpm <= 0:
        raise _invalid_argument(
            message=f"{name} must be greater than 0",
            hint=f"Pass a positive --{name.replace('_', '-')} value.",
            value=bpm,
        )
    return bpm


def stretch_warnings(
    source_bpm: float, target_bpm: float, *, force_large_stretch: bool
) -> list[str]:
    ratio = target_bpm / source_bpm
    if 0.97 <= ratio <= 1.03:
        return []
    if 0.80 <= ratio < 0.90 or 1.11 < ratio <= 1.25:
        return ["large_stretch_risk"]
    if ratio < 0.80 or ratio > 1.25:
        if not force_large_stretch:
            raise _invalid_argument(
                message="BPM stretch ratio is too large",
                hint=(
                    "Pass --force-large-stretch if this destructive-sounding stretch "
                    "is intentional."
                ),
                ratio=ratio,
                source_bpm=source_bpm,
                target_bpm=target_bpm,
            )
        return ["extreme_stretch_risk"]
    return ["moderate_stretch_risk"]


def select_warp_mode(profile: str, available_warp_modes: list[int]) -> tuple[str, str | None]:
    preferred = WARP_PROFILES.get(profile)
    if preferred is None:
        raise _invalid_argument(
            message=f"unsupported warp profile: {profile}",
            hint=f"Use one of: {', '.join(sorted(WARP_PROFILES))}.",
            profile=profile,
        )
    available = {int(value) for value in available_warp_modes}
    for mode in preferred:
        if WARP_MODE_VALUES[mode] in available:
            return mode, None
    raise _invalid_argument(
        message=f"no warp mode is available for profile: {profile}",
        hint="Inspect clip warp get and choose a profile supported by available_warp_modes.",
        profile=profile,
        preferred_modes=list(preferred),
        available_warp_modes=available_warp_modes,
    )


def _warp_mode_matches(actual: Any, expected_mode: str) -> bool:
    expected_value = WARP_MODE_VALUES[expected_mode]
    if actual == expected_mode or actual == expected_value:
        return True
    try:
        return int(actual) == expected_value
    except (TypeError, ValueError):
        return False


def _verify_warp_readback(readback: dict[str, Any], selected_mode: str) -> None:
    if readback.get("warping") is not True:
        raise _invalid_argument(
            message="warp conform verification failed: warping is not enabled",
            hint="Retry after Live has processed the clip warp state.",
            readback=readback,
        )
    if not _warp_mode_matches(readback.get("warp_mode"), selected_mode):
        raise _invalid_argument(
            message="warp conform verification failed: warp_mode did not match selected mode",
            hint="Retry after Live has processed the clip warp mode.",
            selected_mode=selected_mode,
            readback=readback,
        )


def conform_session_clip_warp(
    client: Any,
    *,
    track: int,
    clip: int,
    source_bpm: float,
    target_bpm: float,
    profile: str,
    markers: str,
    verify: bool,
    force_large_stretch: bool,
) -> dict[str, Any]:
    valid_source_bpm = _positive_bpm("source_bpm", source_bpm)
    valid_target_bpm = _positive_bpm("target_bpm", target_bpm)
    if markers not in {"none", "two-point"}:
        raise _invalid_argument(
            message=f"unsupported marker strategy: {markers}",
            hint="Use --markers none or --markers two-point.",
            markers=markers,
        )

    initial = client.clip_warp_get(track, clip)
    available_warp_modes = [int(value) for value in initial.get("available_warp_modes", [])]
    selected_mode, fallback_reason = select_warp_mode(profile, available_warp_modes)
    warnings = stretch_warnings(
        valid_source_bpm,
        valid_target_bpm,
        force_large_stretch=force_large_stretch,
    )

    client.clip_warp_set(track, clip, True, None)
    mode_readback = client.clip_warp_set(track, clip, True, selected_mode)

    marker_count = 0
    marker_beats: list[float] = []
    if markers == "two-point":
        props = client.clip_props_get(track, clip)
        clip_length = float(props.get("length", 0.0))
        planned_marker_beats = [0.0]
        if clip_length > 0:
            planned_marker_beats.append(clip_length)
        else:
            warnings.append("clip_length_unavailable_for_second_marker")
        for beat_time in planned_marker_beats:
            if beat_time < 0:
                continue
            client.clip_warp_marker_add(track, clip, beat_time=beat_time, sample_time=None)
            marker_beats.append(beat_time)
            marker_count += 1

    verified = False
    marker_readback: dict[str, Any] | None = None
    if verify:
        readback = client.clip_warp_get(track, clip)
        _verify_warp_readback(readback, selected_mode)
        if markers != "none":
            marker_readback = client.clip_warp_marker_list(track, clip)
        verified = True
    else:
        readback = mode_readback

    return {
        "track": track,
        "clip": clip,
        "source_bpm": valid_source_bpm,
        "target_bpm": valid_target_bpm,
        "ratio": valid_target_bpm / valid_source_bpm,
        "profile": profile,
        "selected_warp_mode": selected_mode,
        "fallback_reason": fallback_reason,
        "available_warp_modes": available_warp_modes,
        "markers": {"strategy": markers, "count": marker_count, "beat_times": marker_beats},
        "verified": verified,
        "warnings": warnings,
        "readback": readback,
        "marker_readback": marker_readback,
    }
