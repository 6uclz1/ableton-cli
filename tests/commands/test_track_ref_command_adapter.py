from __future__ import annotations


def test_run_track_command_spec_passes_track_ref(monkeypatch) -> None:
    from ableton_cli.commands import track

    captured: dict[str, object] = {}

    class _Client:
        def track_mute_get(self, track_ref):  # noqa: ANN001, ANN201
            return {"track_ref": track_ref, "mute": True}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(track, "get_client", _get_client)
    monkeypatch.setattr(track, "execute_command", _execute_command)

    track.run_track_command_spec(
        ctx=object(),
        spec=track.TrackCommandSpec(
            command_name="track mute get",
            client_method="track_mute_get",
        ),
        track_ref={"mode": "selected"},
    )

    assert captured["command"] == "track mute get"
    assert captured["args"] == {"track_ref": {"mode": "selected"}}
    assert captured["result"] == {"track_ref": {"mode": "selected"}, "mute": True}
