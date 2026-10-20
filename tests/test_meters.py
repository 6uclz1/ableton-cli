from __future__ import annotations

import json
from typing import Any

import pytest

from ableton_cli.errors import AppError
from ableton_cli.meters import sample_meter


def _reader(readings: list[dict[str, Any]]):
    queue = list(readings)
    return lambda: queue.pop(0)


def _reading(left: float, right: float, level: float, *, playing: bool = True) -> dict[str, Any]:
    return {"track": 2, "left": left, "right": right, "level": level, "is_playing": playing}


def test_single_sample_reports_peak_and_mean_equal() -> None:
    result = sample_meter(_reader([_reading(0.5, 0.25, 0.5)]), samples=1, interval_ms=0, sleep=None)

    assert result == {
        "track": 2,
        "samples": 1,
        "interval_ms": 0,
        "is_playing": True,
        "left": {"peak": 0.5, "mean": 0.5},
        "right": {"peak": 0.25, "mean": 0.25},
        "level": {"peak": 0.5, "mean": 0.5},
    }


def test_samples_aggregate_peak_and_mean_and_sleep_between_reads() -> None:
    sleeps: list[float] = []
    readings = [_reading(0.2, 0.1, 0.2), _reading(0.8, 0.4, 0.8), _reading(0.5, 0.1, 0.5)]

    result = sample_meter(_reader(readings), samples=3, interval_ms=100, sleep=sleeps.append)

    assert sleeps == [0.1, 0.1]
    assert result["left"] == {"peak": 0.8, "mean": pytest.approx(0.5)}
    assert result["right"] == {"peak": 0.4, "mean": pytest.approx(0.2)}


def test_reports_stopped_transport_from_the_last_reading() -> None:
    readings = [_reading(0.0, 0.0, 0.0), _reading(0.0, 0.0, 0.0, playing=False)]

    result = sample_meter(_reader(readings), samples=2, interval_ms=0, sleep=lambda _: None)

    assert result["is_playing"] is False


@pytest.mark.parametrize(("samples", "interval_ms"), [(0, 50), (1001, 50), (2, -1), (2, 10001)])
def test_rejects_out_of_range_sampling(samples: int, interval_ms: int) -> None:
    with pytest.raises(AppError) as raised:
        sample_meter(_reader([]), samples=samples, interval_ms=interval_ms, sleep=None)

    assert raised.value.error_code.value == "INVALID_ARGUMENT"


class _MeterClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def _reading(self, name: str, *args: Any, **ids: Any) -> dict[str, Any]:
        self.calls.append((name, args))
        return {**ids, "left": 0.5, "right": 0.25, "level": 0.5, "is_playing": True}

    def track_meter_get(self, track_ref: dict[str, Any]) -> dict[str, Any]:
        return self._reading("track_meter_get", track_ref, track=track_ref["index"])

    def return_track_meter_get(self, return_track: int) -> dict[str, Any]:
        return self._reading("return_track_meter_get", return_track, return_track=return_track)

    def master_meter_get(self) -> dict[str, Any]:
        return self._reading("master_meter_get")


@pytest.fixture
def meter_client(monkeypatch) -> _MeterClient:  # noqa: ANN001
    from ableton_cli.commands import master, return_track, track

    client = _MeterClient()
    for module in (master, return_track, track):
        monkeypatch.setattr(module, "get_client", lambda ctx: client)
    return client


@pytest.mark.parametrize(
    ("args", "call", "identity"),
    [
        (["track", "meter", "get", "--track-index", "3"], "track_meter_get", {"track": 3}),
        (["return-track", "meter", "get", "1"], "return_track_meter_get", {"return_track": 1}),
        (["master", "meter", "get"], "master_meter_get", {}),
    ],
)
def test_meter_commands_sample_and_aggregate(
    runner, cli_app, meter_client, args, call, identity
) -> None:
    result = runner.invoke(
        cli_app, ["--output", "json", *args, "--samples", "3", "--interval-ms", "0"]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert [name for name, _ in meter_client.calls] == [call] * 3
    assert payload["result"] == {
        **identity,
        "samples": 3,
        "interval_ms": 0,
        "is_playing": True,
        "left": {"peak": 0.5, "mean": 0.5},
        "right": {"peak": 0.25, "mean": 0.25},
        "level": {"peak": 0.5, "mean": 0.5},
    }


def test_meter_command_rejects_zero_samples(runner, cli_app, meter_client) -> None:
    result = runner.invoke(
        cli_app, ["--output", "json", "master", "meter", "get", "--samples", "0"]
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert meter_client.calls == []


def test_meter_commands_are_read_only(runner, cli_app, meter_client) -> None:
    result = runner.invoke(
        cli_app, ["--output", "json", "--read-only", "master", "meter", "get", "--interval-ms", "0"]
    )

    assert result.exit_code == 0, result.stdout
