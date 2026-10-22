from __future__ import annotations

from pathlib import Path
from typing import Any

from .ebur128 import measure_ebur128
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
    measurement = measure_ebur128(data.path)

    result = {
        "path": str(Path(path).expanduser()),
        "engine": parsed_engine,
        "duration_sec": round(data.duration_sec, 6),
        "sample_rate": data.sample_rate,
        "channels": data.channels,
        "integrated_lufs": measurement.integrated_lufs,
        "short_term_lufs_max": measurement.short_term_lufs_max,
        "momentary_lufs_max": measurement.momentary_lufs_max,
        "lra_lu": measurement.lra_lu,
        "true_peak_dbtp": measurement.true_peak_dbtp,
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
