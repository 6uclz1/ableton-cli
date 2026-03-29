from __future__ import annotations

import json


def test_session_diff_reports_added_removed_and_changed(runner, cli_app, tmp_path) -> None:
    from_path = tmp_path / "from.json"
    to_path = tmp_path / "to.json"
    from_path.write_text(
        json.dumps(
            {
                "song_info": {"tempo": 120.0, "is_playing": False},
                "tracks_list": {"tracks": [{"index": 0, "name": "Kick"}]},
            }
        ),
        encoding="utf-8",
    )
    to_path.write_text(
        json.dumps(
            {
                "song_info": {"tempo": 128.0, "is_playing": False},
                "tracks_list": {
                    "tracks": [{"index": 0, "name": "Kick"}, {"index": 1, "name": "Bass"}]
                },
                "scenes_list": {"scenes": [{"index": 0, "name": "Intro"}]},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "session",
            "diff",
            "--from",
            str(from_path),
            "--to",
            str(to_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["changed"]["song_info"]["tempo"]["from"] == 120.0
    assert payload["result"]["changed"]["song_info"]["tempo"]["to"] == 128.0
    assert payload["result"]["added"]["scenes_list"]["scenes"][0]["name"] == "Intro"
    assert payload["result"]["changed"]["tracks_list"]["tracks"]["to"][1]["name"] == "Bass"


def test_session_diff_output_is_stable(runner, cli_app, tmp_path) -> None:
    from_path = tmp_path / "from.json"
    to_path = tmp_path / "to.json"
    from_path.write_text(json.dumps({"song_info": {"tempo": 120.0}}), encoding="utf-8")
    to_path.write_text(json.dumps({"song_info": {"tempo": 121.0}}), encoding="utf-8")

    first = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "session",
            "diff",
            "--from",
            str(from_path),
            "--to",
            str(to_path),
        ],
    )
    second = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "session",
            "diff",
            "--from",
            str(from_path),
            "--to",
            str(to_path),
        ],
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert json.loads(first.stdout)["result"] == json.loads(second.stdout)["result"]


def test_compact_reduces_large_json_arrays(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import tracks

    class _ClientStub:
        def tracks_list(self):  # noqa: ANN201
            return {
                "tracks": [
                    {
                        "index": index,
                        "stable_ref": f"track:{index}",
                        "name": f"Track {index}",
                        "mute": False,
                        "solo": False,
                        "arm": False,
                        "volume": 0.75,
                    }
                    for index in range(40)
                ]
            }

    monkeypatch.setattr(tracks, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "--compact", "tracks", "list"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    compacted_tracks = payload["result"]["tracks"]
    assert isinstance(compacted_tracks, dict)
    assert "_compact_ref" in compacted_tracks
    assert "_compact_summary" in compacted_tracks
    ref = compacted_tracks["_compact_ref"]
    assert payload["compact_refs"][ref]["count"] == 40


def test_compact_keeps_small_arrays_unmodified(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import tracks

    class _ClientStub:
        def tracks_list(self):  # noqa: ANN201
            return {
                "tracks": [
                    {
                        "index": 0,
                        "stable_ref": "track:0",
                        "name": "Only",
                        "mute": False,
                        "solo": False,
                        "arm": False,
                        "volume": 0.75,
                    }
                ]
            }

    monkeypatch.setattr(tracks, "get_client", lambda _ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "--compact", "tracks", "list"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert isinstance(payload["result"]["tracks"], list)
    assert "compact_refs" not in payload
