from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .io import amplitude_dbfs, interleaved_mono, read_wav, rms_dbfs, write_report

BANDS: tuple[tuple[str, float, float], ...] = (
    ("sub_20_60_hz", 20.0, 60.0),
    ("bass_60_120_hz", 60.0, 120.0),
    ("low_mid_120_400_hz", 120.0, 400.0),
    ("mid_400_2000_hz", 400.0, 2000.0),
    ("presence_2000_6000_hz", 2000.0, 6000.0),
    ("air_10000_18000_hz", 10000.0, 18000.0),
)

PROFILE_BASELINES: dict[str, dict[str, float]] = {
    "anime-club": {
        "sub_20_60_hz": -26.0,
        "bass_60_120_hz": -18.0,
        "low_mid_120_400_hz": -20.0,
        "mid_400_2000_hz": -19.0,
        "presence_2000_6000_hz": -18.0,
        "air_10000_18000_hz": -24.0,
    },
    "anime-club-balanced": {
        "sub_20_60_hz": -27.0,
        "bass_60_120_hz": -19.0,
        "low_mid_120_400_hz": -21.0,
        "mid_400_2000_hz": -19.0,
        "presence_2000_6000_hz": -18.0,
        "air_10000_18000_hz": -23.0,
    },
    "anime-vocal-forward": {
        "sub_20_60_hz": -28.0,
        "bass_60_120_hz": -20.0,
        "low_mid_120_400_hz": -21.0,
        "mid_400_2000_hz": -18.0,
        "presence_2000_6000_hz": -16.5,
        "air_10000_18000_hz": -22.0,
    },
    "club-preview": {
        "sub_20_60_hz": -25.0,
        "bass_60_120_hz": -17.5,
        "low_mid_120_400_hz": -21.0,
        "mid_400_2000_hz": -20.0,
        "presence_2000_6000_hz": -19.0,
        "air_10000_18000_hz": -24.0,
    },
    "broadcast-r128": {
        "sub_20_60_hz": -31.0,
        "bass_60_120_hz": -24.0,
        "low_mid_120_400_hz": -23.0,
        "mid_400_2000_hz": -22.0,
        "presence_2000_6000_hz": -22.0,
        "air_10000_18000_hz": -28.0,
    },
}


def analyze_spectrum(
    path: str | Path,
    *,
    profile: str = "anime-club",
    report_out: str | Path | None = None,
) -> dict[str, Any]:
    data = read_wav(path)
    mono = interleaved_mono(data, limit=min(data.sample_rate * 4, 131072))
    bands = {
        band_name: round(_band_level(mono, data.sample_rate, low, high), 3)
        for band_name, low, high in BANDS
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


def _band_level(samples: tuple[float, ...], sample_rate: int, low: float, high: float) -> float:
    if not samples:
        return float("-inf")
    centers = _band_centers(low, high)
    powers = [_goertzel_power(samples, sample_rate, freq) for freq in centers]
    mean_power = sum(powers) / len(powers)
    return amplitude_dbfs(math.sqrt(max(mean_power, 0.0)) * 2.0)


def _band_centers(low: float, high: float) -> tuple[float, ...]:
    ratio = (high / low) ** 0.25
    return tuple(low * (ratio**index) for index in range(1, 4))


def _goertzel_power(samples: tuple[float, ...], sample_rate: int, freq: float) -> float:
    normalized = freq / sample_rate
    coeff = 2.0 * math.cos(2.0 * math.pi * normalized)
    prev = 0.0
    prev2 = 0.0
    for sample in samples:
        value = sample + coeff * prev - prev2
        prev2 = prev
        prev = value
    power = prev2 * prev2 + prev * prev - coeff * prev * prev2
    return power / (len(samples) * len(samples))


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
    for key, value in bands.items():
        delta = value - baseline.get(key, value)
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
