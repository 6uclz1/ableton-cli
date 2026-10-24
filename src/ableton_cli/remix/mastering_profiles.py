from __future__ import annotations

from copy import deepcopy
from typing import Any

from .manifest import default_mastering_targets, remix_error

MASTERING_PROFILES: dict[str, dict[str, Any]] = {
    "anime-club-demo": {
        **default_mastering_targets(),
        "profile": "anime-club-demo",
        "integrated_lufs": -14.0,
        "true_peak_dbtp_max": -1.0,
        "crest_db_min": 6.0,
        "spectrum_profile": "anime-club-balanced",
        "notes": "Working preset for anime club remix demos; not a platform specification.",
    },
    "anime-vocal-forward": {
        **default_mastering_targets(),
        "profile": "anime-vocal-forward",
        "integrated_lufs": -15.0,
        "true_peak_dbtp_max": -1.0,
        "crest_db_min": 7.0,
        "spectrum_profile": "anime-vocal-forward",
        "notes": "Keeps vocal presence as a mix decision before master EQ compensation.",
    },
    "club-preview": {
        **default_mastering_targets(),
        "profile": "club-preview",
        "integrated_lufs": -12.0,
        "true_peak_dbtp_max": -1.0,
        "crest_db_min": 5.5,
        "spectrum_profile": "club-preview",
        "notes": (
            "Preview loudness target for club checks; avoid destructive loudness maximization."
        ),
    },
    "broadcast-r128": {
        **default_mastering_targets(),
        "profile": "broadcast-r128",
        "integrated_lufs": -23.0,
        "true_peak_dbtp_max": -1.0,
        "crest_db_min": None,
        "spectrum_profile": "broadcast-r128",
        "notes": "EBU R128 broadcast-oriented profile with programme loudness target -23.0 LUFS.",
    },
}


def list_profiles() -> dict[str, Any]:
    return {
        "profiles": [
            {"name": name, **profile} for name, profile in sorted(MASTERING_PROFILES.items())
        ]
    }


def profile_targets(profile: str) -> dict[str, Any]:
    try:
        return deepcopy(MASTERING_PROFILES[profile])
    except KeyError as exc:
        raise remix_error(
            message=f"unknown mastering profile: {profile}",
            hint=f"Use one of: {', '.join(sorted(MASTERING_PROFILES))}.",
        ) from exc
