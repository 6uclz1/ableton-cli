from __future__ import annotations


def test_tracks_run_client_command_spec_passes_method_kwargs(monkeypatch) -> None:
    from ableton_cli.commands import tracks

    captured: dict[str, object] = {}

    class _Client:
        def create_audio_track(self, index: int):  # noqa: ANN201
            return {"index": index, "kind": "audio"}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(tracks, "get_client", _get_client)
    monkeypatch.setattr(tracks, "execute_command", _execute_command)

    tracks.run_client_command_spec(
        ctx=object(),
        spec=tracks.TracksCommandSpec(
            command_name="tracks create audio",
            client_method="create_audio_track",
        ),
        args={"index": -1},
        method_kwargs={"index": 3},
    )

    assert captured["command"] == "tracks create audio"
    assert captured["args"] == {"index": -1}
    assert captured["result"] == {"index": 3, "kind": "audio"}
