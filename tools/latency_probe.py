from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class _SongStub:
    def __init__(self) -> None:
        self.tempo = 120.0
        self.is_playing = False
        self.current_song_time = 0.0
        self.signature_numerator = 4
        self.signature_denominator = 4
        self.tracks: list[object] = []
        self.return_tracks: list[object] = []
        self.scenes: list[object] = []
        self.master_track = type(
            "MasterTrackStub",
            (),
            {
                "name": "Master",
                "mixer_device": type(
                    "MixerStub",
                    (),
                    {
                        "volume": type("VolumeStub", (), {"value": 0.75})(),
                        "panning": type("PanningStub", (), {"value": 0.0})(),
                    },
                )(),
            },
        )()


class _CInstanceStub:
    def __init__(self) -> None:
        self._song = _SongStub()
        self._app = type("ApplicationStub", (), {"browser": type("BrowserStub", (), {})()})()

    def song(self) -> _SongStub:
        return self._song

    def application(self) -> object:
        return self._app


def _percentile(samples: list[float], percentile: float) -> float:
    if not samples:
        raise ValueError("samples must not be empty")
    ordered = sorted(samples)
    rank = max(0, math.ceil((percentile / 100.0) * len(ordered)) - 1)
    return ordered[rank]


def _summarize(samples: list[float]) -> dict[str, float]:
    return {
        "count": float(len(samples)),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
        "mean_ms": round(statistics.fmean(samples), 3),
        "p50_ms": round(_percentile(samples, 50.0), 3),
        "p95_ms": round(_percentile(samples, 95.0), 3),
    }


def _validate_cli_json_output(stdout: str, *, expected_id: str | None = None) -> None:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
        raise RuntimeError(f"CLI returned malformed JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):  # pragma: no cover - defensive branch
        raise RuntimeError("CLI returned non-object JSON payload")
    if payload.get("ok") is not True:
        raise RuntimeError(f"CLI call failed: {payload.get('error')}")
    if expected_id is not None and payload.get("id") != expected_id:
        raise RuntimeError(
            f"stream response id mismatch: expected={expected_id} got={payload.get('id')}"
        )


def _benchmark_single_shot(cli_prefix: list[str], iterations: int, warmup: int) -> list[float]:
    samples: list[float] = []
    command = [*cli_prefix, "--output", "json", "song", "info"]

    for index in range(iterations + warmup):
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if completed.returncode != 0:
            raise RuntimeError(
                "single-shot command failed "
                f"(exit={completed.returncode} stderr={completed.stderr.strip()!r})"
            )
        _validate_cli_json_output(completed.stdout)
        if index >= warmup:
            samples.append(elapsed_ms)

    return samples


def _benchmark_stream(cli_prefix: list[str], iterations: int, warmup: int) -> list[float]:
    samples: list[float] = []
    command = [*cli_prefix, "batch", "stream"]
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    if process.stdin is None or process.stdout is None:
        process.kill()
        raise RuntimeError("failed to open stream pipes")

    try:
        for index in range(iterations + warmup):
            request_id = str(index)
            payload = {
                "id": request_id,
                "steps": [{"name": "song_info", "args": {}}],
            }
            started = time.perf_counter()
            process.stdin.write(json.dumps(payload) + "\n")
            process.stdin.flush()
            response_line = process.stdout.readline()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if not response_line:
                stderr = ""
                if process.stderr is not None:
                    stderr = process.stderr.read().strip()
                raise RuntimeError(f"stream command terminated unexpectedly (stderr={stderr!r})")
            _validate_cli_json_output(response_line, expected_id=request_id)
            if index >= warmup:
                samples.append(elapsed_ms)
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)

    if process.returncode not in {0, None}:
        stderr = ""
        if process.stderr is not None:
            stderr = process.stderr.read().strip()
        raise RuntimeError(f"stream command failed (exit={process.returncode} stderr={stderr!r})")

    return samples


def _build_parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    default_cli = str(repo_root / ".venv" / "bin" / "ableton-cli")

    parser = argparse.ArgumentParser(
        description="Compare single-shot CLI latency against batch stream latency.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=30,
        help="Number of requests per mode.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Number of warmup requests per mode (excluded from stats).",
    )
    parser.add_argument(
        "--target-ms",
        type=float,
        default=150.0,
        help="Target p95 latency threshold for single-shot mode.",
    )
    parser.add_argument(
        "--cli",
        nargs="+",
        default=[default_cli],
        help="CLI command prefix, e.g. '.venv/bin/ableton-cli' or 'uv run ableton-cli'.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print report as JSON only.",
    )
    return parser


def main() -> int:
    from remote_script.AbletonCliRemote.control_surface import (
        AbletonCliRemoteSurface,
    )

    parser = _build_parser()
    args = parser.parse_args()

    if args.iterations <= 0:
        raise SystemExit("--iterations must be > 0")
    if args.warmup < 0:
        raise SystemExit("--warmup must be >= 0")

    surface = AbletonCliRemoteSurface(None)
    c_instance = _CInstanceStub()
    surface.song = c_instance.song  # type: ignore[attr-defined]
    surface.application = c_instance.application  # type: ignore[attr-defined]
    time.sleep(0.02)

    try:
        single_samples = _benchmark_single_shot(args.cli, args.iterations, args.warmup)
        stream_samples = _benchmark_stream(args.cli, args.iterations, args.warmup)
    finally:
        surface.disconnect()

    single_summary = _summarize(single_samples)
    stream_summary = _summarize(stream_samples)
    p95_improvement_ms = round(single_summary["p95_ms"] - stream_summary["p95_ms"], 3)
    p95_improvement_ratio = round(single_summary["p95_ms"] / stream_summary["p95_ms"], 3)

    report = {
        "iterations": args.iterations,
        "warmup": args.warmup,
        "cli_prefix": args.cli,
        "single_shot": single_summary,
        "batch_stream": stream_summary,
        "delta": {
            "p95_improvement_ms": p95_improvement_ms,
            "p95_improvement_ratio": p95_improvement_ratio,
        },
        "target": {
            "single_shot_p95_target_ms": args.target_ms,
            "single_shot_p95_met": single_summary["p95_ms"] < args.target_ms,
        },
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0

    print(f"CLI prefix: {' '.join(args.cli)}")
    print(f"Iterations: {args.iterations}")
    print(f"Single-shot p50/p95 (ms): {single_summary['p50_ms']} / {single_summary['p95_ms']}")
    print(f"Batch stream p50/p95 (ms): {stream_summary['p50_ms']} / {stream_summary['p95_ms']}")
    print(f"P95 improvement (single - stream): {p95_improvement_ms}ms ({p95_improvement_ratio}x)")
    print(
        "Single-shot target met: "
        f"{single_summary['p95_ms']} < {args.target_ms} => "
        f"{report['target']['single_shot_p95_met']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
