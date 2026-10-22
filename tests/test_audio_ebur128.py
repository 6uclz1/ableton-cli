from __future__ import annotations

import math
import struct
import subprocess
import wave
from pathlib import Path

import pytest

from ableton_cli.errors import AppError

EBUR128_LOG = """\
[Parsed_ebur128_0 @ 0x1] t: 0.0999792  TARGET:-23 LUFS    M:-120.7 S:-120.7     I: -70.0 LUFS
[Parsed_ebur128_0 @ 0x1] t: 3.499979   TARGET:-23 LUFS    M:  -9.4 S: -12.5     I: -14.2 LUFS
[Parsed_ebur128_0 @ 0x1] t: 4.999979   TARGET:-23 LUFS    M: -11.0 S: -10.8     I: -14.0 LUFS
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         -14.0 LUFS
    Threshold: -24.0 LUFS

  Loudness range:
    LRA:         5.1 LU
    Threshold: -34.0 LUFS
    LRA low:   -18.0 LUFS
    LRA high:  -13.0 LUFS

  True peak:
    Peak:       -0.7 dBFS
"""


def _completed(returncode: int, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


def test_parse_ebur128_log_reads_summary_and_frame_maxima() -> None:
    from ableton_cli.audio_analysis.ebur128 import parse_ebur128_log

    measurement = parse_ebur128_log(EBUR128_LOG)

    assert measurement.integrated_lufs == -14.0
    assert measurement.lra_lu == 5.1
    assert measurement.true_peak_dbtp == -0.7
    assert measurement.momentary_lufs_max == -9.4
    assert measurement.short_term_lufs_max == -10.8


def test_parse_ebur128_log_reads_silent_true_peak_as_negative_infinity() -> None:
    from ableton_cli.audio_analysis.ebur128 import parse_ebur128_log

    measurement = parse_ebur128_log(
        EBUR128_LOG.replace("Peak:       -0.7 dBFS", "Peak:       -inf dBFS")
    )

    assert measurement.true_peak_dbtp == float("-inf")


def test_parse_ebur128_log_fails_without_summary() -> None:
    from ableton_cli.audio_analysis.ebur128 import parse_ebur128_log

    with pytest.raises(AppError) as exc_info:
        parse_ebur128_log("[Parsed_ebur128_0 @ 0x1] t: 0.1 M: -20.0 S: -20.0\n")

    assert exc_info.value.error_code == "INTERNAL_ERROR"
    assert "Integrated loudness" in exc_info.value.message


def test_measure_ebur128_runs_ffmpeg_with_true_peak_enabled(tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.ebur128 import measure_ebur128

    calls: list[list[str]] = []

    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return _completed(0, EBUR128_LOG)

    audio_path = tmp_path / "mix.wav"
    measurement = measure_ebur128(audio_path, run=run)

    assert measurement.integrated_lufs == -14.0
    [command] = calls
    assert command[0] == "ffmpeg"
    assert str(audio_path) in command
    assert "ebur128=peak=true:framelog=info" in command


def test_measure_ebur128_fails_when_ffmpeg_exits_nonzero(tmp_path: Path) -> None:
    from ableton_cli.audio_analysis.ebur128 import measure_ebur128

    with pytest.raises(AppError) as exc_info:
        measure_ebur128(tmp_path / "mix.wav", run=lambda _command: _completed(1, "boom\n"))

    assert exc_info.value.error_code == "INTERNAL_ERROR"
    assert exc_info.value.details["returncode"] == 1
    assert exc_info.value.details["stderr_tail"] == ["boom"]


def _write_stereo(path: Path, frames: list[float], *, sample_rate: int = 48000) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        payload = bytearray()
        for value in frames:
            sample = int(value * 32767)
            payload.extend(struct.pack("<hh", sample, sample))
        wav.writeframes(bytes(payload))


def _sine(*, freq: float, amp: float, seconds: float, phase: float = 0.0) -> list[float]:
    sample_rate = 48000
    return [
        amp * math.sin(2 * math.pi * freq * index / sample_rate + phase)
        for index in range(int(sample_rate * seconds))
    ]


def test_analyze_loudness_reports_inter_sample_true_peak(tmp_path: Path, real_ffmpeg) -> None:
    from ableton_cli.audio_analysis import analyze_loudness

    # A quarter-sample-rate sine sampled 45 degrees off its crest never hits its peak on
    # a sample: sample peak sits 3 dB under the true (inter-sample) peak.
    audio_path = tmp_path / "isp.wav"
    _write_stereo(audio_path, _sine(freq=12000.0, amp=0.5, seconds=2.0, phase=math.pi / 4))

    result = analyze_loudness(audio_path)

    assert math.isclose(result["sample_peak_dbfs"], -9.03, abs_tol=0.1)
    # ffmpeg's 4x oversampling reads near-fs/4 content slightly hot (-5.4 for -6.02 dBTP).
    assert result["true_peak_dbtp"] > result["sample_peak_dbfs"] + 2.5
    assert math.isclose(result["true_peak_dbtp"], -6.02, abs_tol=0.75)


def test_analyze_loudness_gates_silence_out_of_integrated_loudness(
    tmp_path: Path, real_ffmpeg
) -> None:
    from ableton_cli.audio_analysis import analyze_loudness

    tone = _sine(freq=997.0, amp=0.5, seconds=4.0)
    tone_only = tmp_path / "tone.wav"
    tone_then_silence = tmp_path / "tone_silence.wav"
    _write_stereo(tone_only, tone)
    _write_stereo(tone_then_silence, tone + [0.0] * len(tone))

    tone_result = analyze_loudness(tone_only)
    gated_result = analyze_loudness(tone_then_silence)

    # 997 Hz at -6 dBFS peak on both channels reads -6 LUFS (BS.1770 calibration).
    assert math.isclose(tone_result["integrated_lufs"], -6.0, abs_tol=0.3)
    assert math.isclose(
        gated_result["integrated_lufs"], tone_result["integrated_lufs"], abs_tol=0.3
    )
    assert gated_result["rms_dbfs"] < tone_result["rms_dbfs"] - 2.5
