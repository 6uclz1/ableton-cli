from __future__ import annotations

import math
import shutil
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import AppError, ErrorCode, ExitCode


@dataclass(frozen=True, slots=True)
class AudioData:
    path: Path
    sample_rate: int
    channels: int
    samples: tuple[tuple[float, ...], ...]

    @property
    def duration_sec(self) -> float:
        if not self.samples:
            return 0.0
        return len(self.samples[0]) / self.sample_rate


def audio_error(message: str, hint: str) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
    )


def require_existing_audio_path(path: str | Path) -> Path:
    audio_path = Path(path).expanduser()
    if not audio_path.exists():
        raise audio_error(
            message=f"audio file not found: {audio_path}",
            hint="Pass an existing WAV/AIFF/FLAC path.",
        )
    if not audio_path.is_file():
        raise audio_error(
            message=f"audio path is not a file: {audio_path}",
            hint="Pass a render file path.",
        )
    return audio_path


def require_ffmpeg_engine(engine: str) -> str:
    parsed = engine.strip().lower()
    if parsed != "ffmpeg":
        raise audio_error(
            message=f"unsupported loudness engine: {engine}",
            hint="Use --engine ffmpeg.",
        )
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise AppError(
            error_code=ErrorCode.CONFIG_INVALID,
            message="ffmpeg engine is not available",
            hint="Install ffmpeg and ffprobe, or run on a host that provides them.",
            exit_code=ExitCode.CONFIG_INVALID,
        )
    return parsed


def read_wav(path: str | Path) -> AudioData:
    audio_path = require_existing_audio_path(path)
    try:
        with wave.open(str(audio_path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            raw = wav.readframes(frame_count)
    except wave.Error as exc:
        raise audio_error(
            message=f"unsupported audio format for builtin analysis: {audio_path}",
            hint="Use PCM WAV for deterministic offline analysis.",
        ) from exc

    if channels <= 0:
        raise audio_error(message="audio file has no channels", hint="Use a valid PCM WAV file.")
    if sample_width not in {1, 2, 3, 4}:
        raise audio_error(
            message=f"unsupported sample width: {sample_width}",
            hint="Use 8/16/24/32-bit PCM WAV.",
        )

    samples = tuple([] for _ in range(channels))
    stride = channels * sample_width
    for offset in range(0, len(raw), stride):
        frame = raw[offset : offset + stride]
        if len(frame) != stride:
            continue
        for channel in range(channels):
            start = channel * sample_width
            value = _decode_pcm(frame[start : start + sample_width], sample_width)
            samples[channel].append(value)

    return AudioData(
        path=audio_path,
        sample_rate=sample_rate,
        channels=channels,
        samples=tuple(tuple(channel_samples) for channel_samples in samples),
    )


def _decode_pcm(raw: bytes, sample_width: int) -> float:
    if sample_width == 1:
        return (raw[0] - 128) / 128.0
    if sample_width == 2:
        return struct.unpack("<h", raw)[0] / 32768.0
    if sample_width == 3:
        value = int.from_bytes(raw, byteorder="little", signed=False)
        if value & 0x800000:
            value -= 0x1000000
        return value / 8388608.0
    return struct.unpack("<i", raw)[0] / 2147483648.0


def write_report(path: str | Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    import json

    report_path = Path(path).expanduser()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rms_dbfs(values: list[float] | tuple[float, ...]) -> float:
    if not values:
        return float("-inf")
    mean_square = sum(value * value for value in values) / len(values)
    if mean_square <= 0:
        return float("-inf")
    return 20.0 * math.log10(math.sqrt(mean_square))


def amplitude_dbfs(value: float) -> float:
    if value <= 0:
        return float("-inf")
    return 20.0 * math.log10(value)


def interleaved_mono(data: AudioData, *, limit: int | None = None) -> tuple[float, ...]:
    if not data.samples:
        return ()
    frame_count = len(data.samples[0]) if limit is None else min(len(data.samples[0]), limit)
    mono: list[float] = []
    for index in range(frame_count):
        mono.append(sum(channel[index] for channel in data.samples) / data.channels)
    return tuple(mono)
