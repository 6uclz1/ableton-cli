from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import amplitude_dbfs, read_wav, require_ffmpeg_engine, rms_dbfs, write_report


def analyze_loudness(
    path: str | Path,
    *,
    engine: str = "ffmpeg",
    report_out: str | Path | None = None,
) -> dict[str, Any]:
    parsed_engine = require_ffmpeg_engine(engine)
    data = read_wav(path)
    all_samples = [sample for channel in data.samples for sample in channel]
    peak = max((abs(sample) for sample in all_samples), default=0.0)
    sample_peak_dbfs = amplitude_dbfs(peak)
    rms = rms_dbfs(all_samples)
    crest = sample_peak_dbfs - rms if rms != float("-inf") else 0.0
    clipping = sum(1 for sample in all_samples if abs(sample) >= 0.999969)
    dc_offset = _dc_offset(data.samples)
    momentary_max = _windowed_loudness_max(data.samples, data.sample_rate, seconds=0.4)
    short_term_max = _windowed_loudness_max(data.samples, data.sample_rate, seconds=3.0)

    result = {
        "path": str(Path(path).expanduser()),
        "engine": parsed_engine,
        "duration_sec": round(data.duration_sec, 6),
        "sample_rate": data.sample_rate,
        "channels": data.channels,
        "integrated_lufs": round(rms - 0.691, 3),
        "short_term_lufs_max": round(short_term_max - 0.691, 3),
        "momentary_lufs_max": round(momentary_max - 0.691, 3),
        "lra_lu": round(max(0.0, short_term_max - rms), 3),
        "true_peak_dbtp": round(sample_peak_dbfs, 3),
        "sample_peak_dbfs": round(sample_peak_dbfs, 3),
        "rms_dbfs": round(rms, 3),
        "crest_db": round(crest, 3),
        "clipping_sample_count": clipping,
        "dc_offset": dc_offset,
    }
    write_report(report_out, result)
    return result


def _dc_offset(samples: tuple[tuple[float, ...], ...]) -> dict[str, float]:
    labels = ["left", "right"]
    offsets: dict[str, float] = {}
    for index, channel in enumerate(samples):
        label = labels[index] if index < len(labels) else f"channel_{index + 1}"
        offsets[label] = round(sum(channel) / len(channel), 8) if channel else 0.0
    return offsets


def _windowed_loudness_max(
    samples: tuple[tuple[float, ...], ...],
    sample_rate: int,
    *,
    seconds: float,
) -> float:
    if not samples or not samples[0]:
        return float("-inf")
    window = max(1, int(sample_rate * seconds))
    frame_count = len(samples[0])
    if frame_count <= window:
        return rms_dbfs([sample for channel in samples for sample in channel])
    step = max(1, window // 2)
    values: list[float] = []
    for start in range(0, frame_count - window + 1, step):
        window_samples = [
            sample for channel in samples for sample in channel[start : start + window]
        ]
        values.append(rms_dbfs(window_samples))
    return max(values, default=float("-inf"))
