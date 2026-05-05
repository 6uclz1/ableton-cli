from __future__ import annotations

import json


class _ClipPropsClient:
    def __init__(self) -> None:
        self.warping = False
        self.warp_mode = None
        self.warp_markers: list[dict[str, float]] = []

    def clip_props_get(self, track: int, clip: int):  # noqa: ANN201
        return {"track": track, "clip": clip, "loop_start": 0.0, "loop_end": 16.0, "length": 64.0}

    def clip_loop_set(self, track: int, clip: int, start: float, end: float, enabled: bool):  # noqa: ANN201
        return {
            "track": track,
            "clip": clip,
            "loop_start": start,
            "loop_end": end,
            "looping": enabled,
        }

    def clip_marker_set(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        start_marker: float,
        end_marker: float,
    ):
        return {
            "track": track,
            "clip": clip,
            "start_marker": start_marker,
            "end_marker": end_marker,
        }

    def clip_warp_set(self, track: int, clip: int, enabled: bool, mode: str | None):  # noqa: ANN201
        self.warping = enabled
        if mode is not None:
            self.warp_mode = mode
        return {"track": track, "clip": clip, "warping": enabled, "warp_mode": self.warp_mode}

    def clip_warp_get(self, track: int, clip: int):  # noqa: ANN201
        return {
            "track": track,
            "clip": clip,
            "warping": self.warping,
            "warp_mode": self.warp_mode,
            "available_warp_modes": [0, 1, 2, 3, 4, 6],
        }

    def clip_warp_marker_list(self, track: int, clip: int):  # noqa: ANN201
        return {"track": track, "clip": clip, "warp_markers": list(self.warp_markers)}

    def clip_warp_marker_add(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        beat_time: float,
        sample_time: float | None = None,
    ):
        self.warp_markers.append({"beat_time": beat_time})
        return {"track": track, "clip": clip, "sample_time": sample_time, "beat_time": beat_time}

    def clip_warp_marker_move(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        beat_time: float,
        distance: float,
    ):
        return {"track": track, "clip": clip, "beat_time": beat_time, "distance": distance}

    def clip_warp_marker_remove(self, track: int, clip: int, beat_time: float):  # noqa: ANN201
        return {"track": track, "clip": clip, "beat_time": beat_time, "removed": True}

    def clip_gain_set(self, track: int, clip: int, db: float):  # noqa: ANN201
        return {"track": track, "clip": clip, "gain_db": db}

    def clip_transpose_set(self, track: int, clip: int, semitones: int):  # noqa: ANN201
        return {"track": track, "clip": clip, "pitch_coarse": semitones}

    def arrangement_clip_props_get(self, track: int, index: int):  # noqa: ANN201
        return {"track": track, "index": index, "loop_start": 0.0, "loop_end": 16.0}

    def arrangement_clip_gain_set(self, track: int, index: int, db: float):  # noqa: ANN201
        return {"track": track, "index": index, "gain_db": db}

    def arrangement_clip_transpose_set(self, track: int, index: int, semitones: int):  # noqa: ANN201
        return {"track": track, "index": index, "pitch_coarse": semitones}


def test_session_clip_props_commands_output_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClipPropsClient())

    props = runner.invoke(cli_app, ["--output", "json", "clip", "props", "get", "0", "1"])
    loop = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "loop",
            "set",
            "0",
            "1",
            "--start",
            "0",
            "--end",
            "16",
            "--enabled",
            "true",
        ],
    )
    warp = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "warp",
            "set",
            "0",
            "1",
            "--enabled",
            "true",
            "--mode",
            "complex-pro",
        ],
    )
    gain = runner.invoke(
        cli_app, ["--output", "json", "clip", "gain", "set", "0", "1", "--db", "-3"]
    )

    assert props.exit_code == 0, props.stdout
    assert loop.exit_code == 0, loop.stdout
    assert warp.exit_code == 0, warp.stdout
    assert gain.exit_code == 0, gain.stdout
    assert json.loads(gain.stdout)["result"]["gain_db"] == -3.0


def test_clip_warp_marker_add_allows_omitted_sample_time(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClipPropsClient())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "warp-marker",
            "add",
            "0",
            "1",
            "--beat-time",
            "32",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)["result"]
    assert payload["beat_time"] == 32.0
    assert payload["sample_time"] is None


def test_clip_warp_marker_move_and_remove_output_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClipPropsClient())

    move = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "warp-marker",
            "move",
            "0",
            "1",
            "--beat-time",
            "32",
            "--distance",
            "-0.5",
        ],
    )
    remove = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "warp-marker",
            "remove",
            "0",
            "1",
            "--beat-time",
            "32",
        ],
    )

    assert move.exit_code == 0, move.stdout
    assert remove.exit_code == 0, remove.stdout
    assert json.loads(move.stdout)["result"]["distance"] == -0.5
    assert json.loads(remove.stdout)["result"]["removed"] is True


def test_clip_warp_conform_selects_profile_mode_and_verifies(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClipPropsClient())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "warp",
            "conform",
            "0",
            "1",
            "--source-bpm",
            "174",
            "--target-bpm",
            "168",
            "--profile",
            "full-mix",
            "--verify",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)["result"]
    assert payload["selected_warp_mode"] == "complex-pro"
    assert payload["verified"] is True
    assert payload["markers"]["count"] == 2
    assert payload["markers"]["beat_times"] == [0.0, 64.0]
    assert payload["warnings"] == ["moderate_stretch_risk"]


def test_clip_warp_conform_requires_force_for_extreme_stretch(
    runner,
    cli_app,
    monkeypatch,
) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClipPropsClient())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "warp",
            "conform",
            "0",
            "1",
            "--source-bpm",
            "174",
            "--target-bpm",
            "128",
            "--profile",
            "full-mix",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_arrangement_clip_props_commands_output_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClipPropsClient())

    props = runner.invoke(
        cli_app,
        ["--output", "json", "arrangement", "clip", "props", "get", "0", "0"],
    )
    gain = runner.invoke(
        cli_app,
        ["--output", "json", "arrangement", "clip", "gain", "set", "0", "0", "--db", "-6"],
    )
    transpose = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "arrangement",
            "clip",
            "transpose",
            "set",
            "0",
            "0",
            "--semitones",
            "-1",
        ],
    )

    assert props.exit_code == 0, props.stdout
    assert gain.exit_code == 0, gain.stdout
    assert transpose.exit_code == 0, transpose.stdout
    assert json.loads(transpose.stdout)["result"]["pitch_coarse"] == -1
