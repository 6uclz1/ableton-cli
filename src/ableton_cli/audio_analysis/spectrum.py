from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .ffmpeg import Runner, ffmpeg_output_error, run_ffmpeg
from .io import (
    audio_error,
    read_audio,
    require_existing_audio_path,
    require_ffmpeg_engine,
    rms_dbfs,
    wav_channels,
    write_report,
)

Band = tuple[str, float, float]

BANDS: tuple[Band, ...] = (
    ("sub_20_60_hz", 20.0, 60.0),
    ("bass_60_120_hz", 60.0, 120.0),
    ("low_mid_120_400_hz", 120.0, 400.0),
    ("mid_400_2000_hz", 400.0, 2000.0),
    ("presence_2000_6000_hz", 2000.0, 6000.0),
    ("brilliance_6000_10000_hz", 6000.0, 10000.0),
    ("air_10000_18000_hz", 10000.0, 18000.0),
)

_THIRD_OCTAVE_NOMINAL_HZ = (
    "25", "31.5", "40", "50", "63", "80", "100", "125", "160", "200",
    "250", "315", "400", "500", "630", "800", "1000", "1250", "1600", "2000",
    "2500", "3150", "4000", "5000", "6300", "8000", "10000", "12500", "16000",
)  # fmt: skip


def _third_octave_bands() -> tuple[Band, ...]:
    # Base-2 ISO centers 1000 * 2^(k/3) named by their nominal frequency; adjacent bands
    # share an exact edge.
    first = _THIRD_OCTAVE_NOMINAL_HZ.index("1000")
    edges = [
        1000.0 * 2 ** ((index - first - 0.5) / 3)
        for index in range(len(_THIRD_OCTAVE_NOMINAL_HZ) + 1)
    ]
    return tuple(
        (f"{nominal}_hz", edges[index], edges[index + 1])
        for index, nominal in enumerate(_THIRD_OCTAVE_NOMINAL_HZ)
    )


THIRD_OCTAVE_BANDS: tuple[Band, ...] = _third_octave_bands()
RESOLUTIONS: dict[str, tuple[Band, ...]] = {"bands": BANDS, "third-octave": THIRD_OCTAVE_BANDS}

# Bands are cut brick-wall in the FFT domain: biquad slopes sag inside one-octave bands.
# 16384 points at 48 kHz gives 2.9 Hz bins, enough for the 22-28 Hz third-octave band.
_FFT_WINDOW = 16384
_HINT = "Check that ffmpeg provides the asplit, afftfilt, astats, and amix filters."

# Each band's expected share of the file's full-band (20 Hz-18 kHz) level, in dB. The
# anime-club-balanced shape integrates a spectrum whose energy per octave falls 1.5 dB per
# octave around 1 kHz (the -4.5 dB/octave slope of a per-Hz analyzer); the other profiles
# keep their character as offsets from it. Relative values judge tonal balance, not loudness.
PROFILE_BASELINES: dict[str, dict[str, float]] = {
    "anime-club": {
        "sub_20_60_hz": -2.6,
        "bass_60_120_hz": -6.6,
        "low_mid_120_400_hz": -6.2,
        "mid_400_2000_hz": -8.9,
        "presence_2000_6000_hz": -13.6,
        "brilliance_6000_10000_hz": -19.2,
        "air_10000_18000_hz": -20.3,
    },
    "anime-club-balanced": {
        "sub_20_60_hz": -3.6,
        "bass_60_120_hz": -7.6,
        "low_mid_120_400_hz": -7.2,
        "mid_400_2000_hz": -8.9,
        "presence_2000_6000_hz": -13.6,
        "brilliance_6000_10000_hz": -18.7,
        "air_10000_18000_hz": -19.3,
    },
    "anime-vocal-forward": {
        "sub_20_60_hz": -4.6,
        "bass_60_120_hz": -8.6,
        "low_mid_120_400_hz": -7.2,
        "mid_400_2000_hz": -7.9,
        "presence_2000_6000_hz": -12.1,
        "brilliance_6000_10000_hz": -17.4,
        "air_10000_18000_hz": -18.3,
    },
    "club-preview": {
        "sub_20_60_hz": -1.6,
        "bass_60_120_hz": -6.1,
        "low_mid_120_400_hz": -7.2,
        "mid_400_2000_hz": -9.9,
        "presence_2000_6000_hz": -14.6,
        "brilliance_6000_10000_hz": -19.7,
        "air_10000_18000_hz": -20.3,
    },
    "broadcast-r128": {
        "sub_20_60_hz": -3.8,
        "bass_60_120_hz": -8.8,
        "low_mid_120_400_hz": -5.4,
        "mid_400_2000_hz": -8.1,
        "presence_2000_6000_hz": -13.8,
        "brilliance_6000_10000_hz": -19.4,
        "air_10000_18000_hz": -20.5,
    },
}


def analyze_spectrum(
    path: str | Path,
    *,
    profile: str = "anime-club",
    report_out: str | Path | None = None,
) -> dict[str, Any]:
    require_ffmpeg_engine("ffmpeg")
    data = read_audio(path)
    bands = {
        name: round(level, 3)
        for name, level in measure_band_levels(data.path, channels=data.channels).items()
    }
    stereo = _stereo_metrics(data)
    result = {
        "path": str(Path(path).expanduser()),
        "profile": profile,
        "bands": bands,
        "stereo": stereo,
        "warnings": _profile_warnings(profile, bands, stereo),
    }
    write_report(report_out, result)
    return result


def measure_band_levels(
    path: str | Path,
    *,
    channels: int,
    bands: tuple[Band, ...] = BANDS,
    run: Runner | None = None,
) -> dict[str, float]:
    """Return each band's RMS level (dBFS) of the mono downmix over the whole file."""
    command = [
        "ffmpeg",
        "-nostdin",
        "-nostats",
        "-hide_banner",
        "-i",
        str(path),
        "-filter_complex",
        _band_filter_graph(channels, bands),
        "-map",
        "[out]",
        "-f",
        "null",
        "-",
    ]
    return _parse_band_levels(run_ffmpeg(command, run=run, hint=_HINT), bands)


def _band_filter_graph(channels: int, bands: tuple[Band, ...]) -> str:
    """One pass: split the downmix into a branch per band, each read by ``astats@b<index>``."""
    downmix = "+".join(f"{1 / channels:g}*c{index}" for index in range(channels))
    branches = "".join(f"[s{index}]" for index in range(len(bands)))
    graph = [f"[0:a]pan=mono|c0={downmix},asplit={len(bands)}{branches}"]
    for index, (_name, low, high) in enumerate(bands):
        in_band = f"between(b*sr/(2*(nb-1)),{low:g},{high:g})"
        graph.append(
            f"[s{index}]afftfilt=real='re*{in_band}':imag='im*{in_band}'"
            f":win_size={_FFT_WINDOW}:overlap=0.75,"
            f"astats@b{index}=measure_perchannel=none:measure_overall=RMS_level[o{index}]"
        )
    outputs = "".join(f"[o{index}]" for index in range(len(bands)))
    graph.append(f"{outputs}amix=inputs={len(bands)}[out]")
    return ";".join(graph)


def _parse_band_levels(log: str, bands: tuple[Band, ...]) -> dict[str, float]:
    # ffmpeg prints each named astats instance at uninit, in no guaranteed order.
    levels: dict[str, float] = {}
    for index, (name, _low, _high) in enumerate(bands):
        match = re.search(
            rf"\[astats@b{index} @ [^\]]*\] RMS level dB:\s*(-?\d+(?:\.\d+)?|-inf)", log
        )
        if match is None:
            raise ffmpeg_output_error(
                message=f"ffmpeg astats output has no RMS level for {name}",
                hint=_HINT,
                band=name,
            )
        levels[name] = float(match.group(1))
    return levels


def spectrum_shares(
    stems: list[tuple[str, str | Path]],
    *,
    resolution: str = "bands",
    focus: str | None = None,
    report_out: str | Path | None = None,
) -> dict[str, Any]:
    """Split each band's energy between stems, e.g. solo captures of a mix's tracks."""
    bands = _validate_shares_request(stems, resolution=resolution, focus=focus)
    require_ffmpeg_engine("ffmpeg")
    measured = [
        (
            label,
            Path(path).expanduser(),
            measure_band_levels(path, channels=wav_channels(path), bands=bands),
        )
        for label, path in stems
    ]
    result = _shares_result(measured, bands, resolution=resolution)
    if focus is not None:
        result["focus"] = {"label": focus, "margin_db": _focus_margins(measured, focus, bands)}
    write_report(report_out, result)
    return result


def _shares_result(
    measured: list[tuple[str, Path, dict[str, float]]],
    bands: tuple[Band, ...],
    *,
    resolution: str,
) -> dict[str, Any]:
    powers = {
        name: {label: 10 ** (levels[name] / 10.0) for label, _path, levels in measured}
        for name, _low, _high in bands
    }
    return {
        "resolution": resolution,
        "bands": [
            {"name": name, "low_hz": round(low, 1), "high_hz": round(high, 1)}
            for name, low, high in bands
        ],
        "stems": [
            {
                "label": label,
                "path": str(path),
                "levels": {name: round(level, 3) for name, level in levels.items()},
            }
            for label, path, levels in measured
        ],
        "band_totals_dbfs": {name: _power_dbfs(sum(p.values())) for name, p in powers.items()},
        "shares_pct": {name: _shares_pct(by_label) for name, by_label in powers.items()},
        "dominant": {name: _dominant(by_label) for name, by_label in powers.items()},
    }


def _power_dbfs(power: float) -> float:
    return round(10.0 * math.log10(power), 3) if power > 0 else float("-inf")


def _shares_pct(by_label: dict[str, float]) -> dict[str, float]:
    total = sum(by_label.values())
    return {
        label: round(100.0 * power / total, 1) if total > 0 else 0.0
        for label, power in by_label.items()
    }


def _dominant(by_label: dict[str, float]) -> str | None:
    """The stem with the most energy in the band, or None when the band is silent."""
    if sum(by_label.values()) <= 0:
        return None
    return max(by_label, key=by_label.__getitem__)


def _validate_shares_request(
    stems: list[tuple[str, str | Path]], *, resolution: str, focus: str | None
) -> tuple[Band, ...]:
    if resolution not in RESOLUTIONS:
        raise audio_error(
            message=f"unsupported spectrum resolution: {resolution}",
            hint=f"Use one of: {', '.join(RESOLUTIONS)}.",
        )
    if not stems:
        raise audio_error(
            message="spectrum shares needs at least one stem",
            hint="Pass --stem LABEL=PATH once per stem.",
        )
    labels = [label for label, _path in stems]
    for label in labels:
        if labels.count(label) > 1:
            raise audio_error(
                message=f"duplicate stem label: {label}",
                hint="Give every --stem a unique LABEL.",
            )
    for _label, path in stems:
        require_existing_audio_path(path)
    if focus is not None and focus not in labels:
        raise audio_error(
            message=f"focus label is not a stem: {focus}",
            hint=f"Use one of: {', '.join(labels)}.",
        )
    return RESOLUTIONS[resolution]


def _focus_margins(
    measured: list[tuple[str, Path, dict[str, float]]], focus: str, bands: tuple[Band, ...]
) -> dict[str, float | None]:
    """Focus stem level minus the loudest other stem; None when either side is silent."""
    margins: dict[str, float | None] = {}
    for name, _low, _high in bands:
        focus_level = next(levels[name] for label, _path, levels in measured if label == focus)
        others = [levels[name] for label, _path, levels in measured if label != focus]
        loudest_other = max(others, default=float("-inf"))
        if math.isinf(focus_level) or math.isinf(loudest_other):
            margins[name] = None
        else:
            margins[name] = round(focus_level - loudest_other, 3)
    return margins


def _stereo_metrics(data: Any) -> dict[str, Any]:
    if data.channels < 2:
        return {
            "correlation_avg": 1.0,
            "side_energy_ratio": 0.0,
            "mono_low_end_risk": False,
        }
    left = data.samples[0]
    right = data.samples[1]
    count = min(len(left), len(right))
    if count == 0:
        return {
            "correlation_avg": 0.0,
            "side_energy_ratio": 0.0,
            "mono_low_end_risk": False,
        }
    numerator = sum(left[index] * right[index] for index in range(count))
    left_power = sum(left[index] * left[index] for index in range(count))
    right_power = sum(right[index] * right[index] for index in range(count))
    denominator = math.sqrt(left_power * right_power)
    correlation = numerator / denominator if denominator > 0 else 0.0
    mid = [(left[index] + right[index]) * 0.5 for index in range(count)]
    side = [(left[index] - right[index]) * 0.5 for index in range(count)]
    mid_rms = rms_dbfs(mid)
    side_rms = rms_dbfs(side)
    ratio = 0.0 if mid_rms == float("-inf") else 10 ** ((side_rms - mid_rms) / 20.0)
    return {
        "correlation_avg": round(correlation, 3),
        "side_energy_ratio": round(ratio, 3),
        "mono_low_end_risk": correlation < 0.1 and ratio > 0.7,
    }


def _profile_warnings(
    profile: str,
    bands: dict[str, float],
    stereo: dict[str, Any],
) -> list[dict[str, str]]:
    baseline = PROFILE_BASELINES.get(profile, PROFILE_BASELINES["anime-club"])
    warnings: list[dict[str, str]] = []
    total_power = sum(10 ** (value / 10.0) for value in bands.values())
    if total_power <= 0:
        warnings.append({"code": "silent", "message": "No signal in any band; balance not judged"})
    else:
        full_band_db = 10.0 * math.log10(total_power)
        for key, value in bands.items():
            delta = (value - full_band_db) - baseline[key]
            if delta > 6.0:
                warnings.append({"code": f"{key}_hot", "message": f"{key} is high for {profile}"})
            elif delta < -8.0:
                warnings.append({"code": f"{key}_low", "message": f"{key} is low for {profile}"})
    if stereo["mono_low_end_risk"]:
        warnings.append(
            {
                "code": "mono_low_end_risk",
                "message": "Stereo correlation suggests mono compatibility risk",
            }
        )
    return warnings
