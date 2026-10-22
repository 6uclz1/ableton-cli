from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .ffmpeg import Runner, ffmpeg_output_error, run_ffmpeg
from .io import read_wav, require_ffmpeg_engine, rms_dbfs, write_report

BANDS: tuple[tuple[str, float, float], ...] = (
    ("sub_20_60_hz", 20.0, 60.0),
    ("bass_60_120_hz", 60.0, 120.0),
    ("low_mid_120_400_hz", 120.0, 400.0),
    ("mid_400_2000_hz", 400.0, 2000.0),
    ("presence_2000_6000_hz", 2000.0, 6000.0),
    ("brilliance_6000_10000_hz", 6000.0, 10000.0),
    ("air_10000_18000_hz", 10000.0, 18000.0),
)

# Bands are cut brick-wall in the FFT domain: biquad slopes sag inside one-octave bands.
# 8192 points at 48 kHz gives 5.9 Hz bins, fine enough for the 20-60 Hz band.
_FFT_WINDOW = 8192
_RMS_PATTERN = re.compile(r"RMS level dB:\s*(-?\d+(?:\.\d+)?|-inf)")
_HINT = "Check that ffmpeg provides the highpass, lowpass, and astats filters."

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
    data = read_wav(path)
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
    run: Runner | None = None,
) -> dict[str, float]:
    """Return each band's RMS level (dBFS) of the mono downmix over the whole file."""
    downmix = "+".join(f"{1 / channels:g}*c{index}" for index in range(channels))
    levels: dict[str, float] = {}
    for name, low, high in BANDS:
        in_band = f"between(b*sr/(2*(nb-1)),{low:g},{high:g})"
        band_filter = (
            f"afftfilt=real='re*{in_band}':imag='im*{in_band}':win_size={_FFT_WINDOW}:overlap=0.75"
        )
        graph = (
            f"pan=mono|c0={downmix},{band_filter},"
            "astats=measure_perchannel=none:measure_overall=RMS_level"
        )
        command = [
            "ffmpeg",
            "-nostdin",
            "-nostats",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            graph,
            "-f",
            "null",
            "-",
        ]
        match = _RMS_PATTERN.search(run_ffmpeg(command, run=run, hint=_HINT))
        if match is None:
            raise ffmpeg_output_error(
                message=f"ffmpeg astats output has no RMS level for {name}",
                hint=_HINT,
                band=name,
            )
        levels[name] = float(match.group(1))
    return levels


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
