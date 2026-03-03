from __future__ import annotations


def test_song_run_client_command_spec_dispatches_method(monkeypatch) -> None:
    from ableton_cli.commands import song

    captured: dict[str, object] = {}

    class _Client:
        def song_new(self):  # noqa: ANN201
            return {"created": True}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(song, "get_client", _get_client)
    monkeypatch.setattr(song, "execute_command", _execute_command)

    song.run_client_command_spec(
        ctx=object(),
        spec=song.SongCommandSpec(
            command_name="song new",
            client_method="song_new",
        ),
        args={},
    )

    assert captured["command"] == "song new"
    assert captured["args"] == {}
    assert captured["result"] == {"created": True}
