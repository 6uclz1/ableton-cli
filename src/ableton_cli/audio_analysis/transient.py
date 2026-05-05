from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import AudioData, audio_error, read_wav

ANALYSIS_VERSION = "builtin_energy_flux_v1"
_BPM_MIN = 20.0
_BPM_MAX = 999.0


@dataclass(frozen=True, slots=True)
class TransientAnalysisConfig:
    window_ms: float = 20.0
    hop_ms: float = 5.0
    smooth_hops: int = 3
    local_window_ms: float = 120.0
    threshold_scale: float = 1.5
    min_distance_beats: float = 0.10
    boundary_merge_beats: float = 0.03
    round_beats: int = 6


DEFAULT_TRANSIENT_ANALYSIS_CONFIG = TransientAnalysisConfig()


@dataclass(frozen=True, slots=True)
class _Candidate:
    beat: float
    strength: float


def analyze_transients(
    path: str | Path,
    *,
    bpm: float,
    max_slices: int,
    config: TransientAnalysisConfig = DEFAULT_TRANSIENT_ANALYSIS_CONFIG,
) -> dict[str, Any]:
    valid_bpm = _validate_bpm(bpm)
    valid_max_slices = _validate_max_slices(max_slices)
    audio_path = _require_pcm_wav_path(path)
    data = read_wav(audio_path)
    duration_beats = data.duration_sec * valid_bpm / 60.0

    envelope = _channel_summed_rms_envelope(data, config=config)
    smoothed = _smooth(envelope, config.smooth_hops)
    flux = _positive_flux(smoothed)
    candidates = _detect_candidates(data, flux, bpm=valid_bpm, config=config)
    filtered = _filter_candidates(
        candidates,
        duration_beats=duration_beats,
        max_slices=valid_max_slices,
        config=config,
    )

    onset_points = [round(candidate.beat, config.round_beats) for candidate in filtered]
    slice_points = _slice_points(
        onset_points=onset_points,
        duration_beats=duration_beats,
        config=config,
    )
    slice_ranges = [
        {
            "index": index,
            "slice_start": start,
            "slice_end": end,
            "duration_beats": round(end - start, config.round_beats),
        }
        for index, (start, end) in enumerate(zip(slice_points, slice_points[1:], strict=False))
    ]
    warnings = [] if onset_points else ["LOW_CONFIDENCE"]

    return {
        "path": str(audio_path),
        "bpm": float(valid_bpm),
        "sample_rate": data.sample_rate,
        "channels": data.channels,
        "duration_sec": round(data.duration_sec, 6),
        "duration_beats": round(duration_beats, config.round_beats),
        "analysis_version": ANALYSIS_VERSION,
        "onset_points_beats": onset_points,
        "slice_points_beats": slice_points,
        "slice_ranges": slice_ranges,
        "confidence": _confidence(filtered, flux, warnings),
        "warnings": warnings,
    }


def _validate_bpm(bpm: float) -> float:
    if bpm < _BPM_MIN or bpm > _BPM_MAX:
        raise audio_error(
            message=f"bpm must be between {_BPM_MIN} and {_BPM_MAX}, got {bpm}",
            hint="Use a realistic tempo between 20.0 and 999.0 BPM.",
        )
    return float(bpm)


def _validate_max_slices(max_slices: int) -> int:
    if max_slices <= 0:
        raise audio_error(
            message=f"max_slices must be > 0, got {max_slices}",
            hint="Use a positive --max-slices value.",
        )
    return max_slices


def _require_pcm_wav_path(path: str | Path) -> Path:
    audio_path = Path(path).expanduser()
    if not audio_path.exists():
        raise audio_error(
            message=f"audio file not found: {audio_path}",
            hint="Pass an existing PCM WAV file.",
        )
    if not audio_path.is_file():
        raise audio_error(
            message=f"audio path is not a file: {audio_path}",
            hint="Pass an existing PCM WAV file.",
        )
    audio_path = audio_path.resolve(strict=True)
    if audio_path.suffix.lower() != ".wav":
        raise audio_error(
            message=f"transient analysis requires a PCM WAV file, got {audio_path}",
            hint="Use a .wav file encoded as PCM.",
        )
    return audio_path


def _channel_summed_rms_envelope(
    data: AudioData,
    *,
    config: TransientAnalysisConfig,
) -> list[float]:
    frame_count = len(data.samples[0]) if data.samples else 0
    if frame_count == 0:
        return []
    window = max(1, int(round(data.sample_rate * config.window_ms / 1000.0)))
    hop = max(1, int(round(data.sample_rate * config.hop_ms / 1000.0)))
    half_window = window // 2
    envelope: list[float] = []
    for center in range(0, frame_count, hop):
        start = max(0, center - half_window)
        end = min(frame_count, start + window)
        energy = 0.0
        count = max(1, end - start)
        for index in range(start, end):
            energy += sum(channel[index] * channel[index] for channel in data.samples)
        envelope.append(math.sqrt(energy / float(count * data.channels)))
    return envelope


def _smooth(values: list[float], width: int) -> list[float]:
    if width <= 1 or not values:
        return values
    smoothed: list[float] = []
    radius = width // 2
    for index in range(len(values)):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        smoothed.append(sum(values[start:end]) / float(end - start))
    return smoothed


def _positive_flux(envelope: list[float]) -> list[float]:
    if not envelope:
        return []
    flux = [0.0]
    for previous, current in zip(envelope, envelope[1:], strict=False):
        flux.append(max(0.0, current - previous))
    return flux


def _detect_candidates(
    data: AudioData,
    flux: list[float],
    *,
    bpm: float,
    config: TransientAnalysisConfig,
) -> list[_Candidate]:
    if len(flux) < 3:
        return []
    hop = max(1, int(round(data.sample_rate * config.hop_ms / 1000.0)))
    local_radius = max(1, int(round(config.local_window_ms / config.hop_ms / 2.0)))
    candidates: list[_Candidate] = []
    for index in range(1, len(flux) - 1):
        strength = flux[index]
        if strength <= 0.0 or strength < flux[index - 1] or strength < flux[index + 1]:
            continue
        start = max(0, index - local_radius)
        end = min(len(flux), index + local_radius + 1)
        local = flux[start:end]
        local_mean = sum(local) / float(len(local))
        local_peak = max(local)
        threshold = local_mean + ((local_peak - local_mean) / max(config.threshold_scale, 1.0))
        if strength < threshold:
            continue
        sample_index = _refine_peak_sample(data, index * hop, hop * 4)
        beat = sample_index / data.sample_rate * bpm / 60.0
        candidates.append(_Candidate(beat=beat, strength=strength))
    return candidates


def _refine_peak_sample(data: AudioData, estimate: int, radius: int) -> int:
    frame_count = len(data.samples[0]) if data.samples else 0
    if frame_count == 0:
        return 0
    start = max(0, estimate - radius)
    end = min(frame_count, estimate + radius + 1)
    return max(
        range(start, end),
        key=lambda index: sum(channel[index] * channel[index] for channel in data.samples),
    )


def _filter_candidates(
    candidates: list[_Candidate],
    *,
    duration_beats: float,
    max_slices: int,
    config: TransientAnalysisConfig,
) -> list[_Candidate]:
    in_bounds = [
        candidate
        for candidate in sorted(candidates, key=lambda item: item.beat)
        if (
            config.boundary_merge_beats
            <= candidate.beat
            <= duration_beats - config.boundary_merge_beats
        )
    ]
    merged: list[_Candidate] = []
    for candidate in in_bounds:
        if merged and candidate.beat - merged[-1].beat < config.min_distance_beats:
            if candidate.strength > merged[-1].strength:
                merged[-1] = candidate
            continue
        merged.append(candidate)

    max_onsets = max(0, max_slices - 1)
    if len(merged) > max_onsets:
        strongest = sorted(merged, key=lambda item: item.strength, reverse=True)[:max_onsets]
        merged = sorted(strongest, key=lambda item: item.beat)
    return merged


def _slice_points(
    *,
    onset_points: list[float],
    duration_beats: float,
    config: TransientAnalysisConfig,
) -> list[float]:
    rounded_end = round(max(duration_beats, 0.0), config.round_beats)
    points = [0.0]
    for onset in onset_points:
        if onset <= config.boundary_merge_beats:
            continue
        if onset >= rounded_end - config.boundary_merge_beats:
            continue
        points.append(round(onset, config.round_beats))
    points.append(rounded_end)
    return points


def _confidence(candidates: list[_Candidate], flux: list[float], warnings: list[str]) -> float:
    if warnings or not candidates or not flux:
        return 0.0
    peak = max(flux, default=0.0)
    if peak <= 0.0:
        return 0.0
    mean_strength = sum(candidate.strength for candidate in candidates) / len(candidates)
    density_bonus = min(0.25, len(candidates) * 0.02)
    return round(max(0.0, min(1.0, (mean_strength / peak) * 0.75 + density_bonus)), 3)
