from __future__ import annotations


def test_run_track_command_dispatches_track_ref_to_client(monkeypatch) -> None:
    from ableton_cli.commands import track

    captured: dict[str, object] = {}
    track_ref = {"mode": "selected"}

    class _Client:
        def track_mute_get(self, resolved_track_ref):  # noqa: ANN001, ANN201
            return {"track_ref": resolved_track_ref, "mute": True}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(track, "get_client", _get_client)
    monkeypatch.setattr(track, "execute_command", _execute_command)

    track.run_track_command(
        ctx=object(),
        command_name="track test",
        track_ref=track_ref,
        fn=lambda resolved_client, resolved_track_ref: {
            "same_client": isinstance(resolved_client, _Client),
            "track_ref": resolved_track_ref,
        },
    )

    assert captured["command"] == "track test"
    assert captured["args"] == {"track_ref": track_ref}
    assert captured["result"] == {"same_client": True, "track_ref": track_ref}


def test_run_track_value_command_applies_value_validators(monkeypatch) -> None:
    from ableton_cli.commands import track

    captured: dict[str, object] = {}
    track_ref = {"mode": "name", "name": "Bass"}

    class _Client:
        def set_track_name(self, resolved_track_ref, name: str):  # noqa: ANN001, ANN201
            return {"track_ref": resolved_track_ref, "name": name}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(track, "get_client", _get_client)
    monkeypatch.setattr(track, "execute_command", _execute_command)

    track.run_track_value_command(
        ctx=object(),
        command_name="track name set",
        track_ref=track_ref,
        value="  Bass  ",
        fn=lambda resolved_client, resolved_track_ref, valid_value: {
            "same_client": isinstance(resolved_client, _Client),
            "track_ref": resolved_track_ref,
            "value": valid_value,
        },
        value_name="name",
        validators=[str.strip],
    )

    assert captured["command"] == "track name set"
    assert captured["args"] == {"track_ref": track_ref, "name": "  Bass  "}
    assert captured["result"] == {
        "same_client": True,
        "track_ref": track_ref,
        "value": "Bass",
    }


def test_run_track_command_spec_dispatches_client_method(monkeypatch) -> None:
    from ableton_cli.commands import track

    captured: dict[str, object] = {}
    track_ref = {"mode": "stable_ref", "stable_ref": "track:7"}

    class _Client:
        def track_mute_get(self, resolved_track_ref):  # noqa: ANN001, ANN201
            return {"track_ref": resolved_track_ref, "mute": True}

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
        track_ref=track_ref,
    )

    assert captured["command"] == "track mute get"
    assert captured["args"] == {"track_ref": track_ref}
    assert captured["result"] == {"track_ref": track_ref, "mute": True}


def test_run_track_value_command_spec_uses_value_name_and_validators(monkeypatch) -> None:
    from ableton_cli.commands import track

    captured: dict[str, object] = {}
    track_ref = {"mode": "index", "index": 0}

    class _Client:
        def set_track_name(self, resolved_track_ref, name: str):  # noqa: ANN001, ANN201
            return {"track_ref": resolved_track_ref, "name": name}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(track, "get_client", _get_client)
    monkeypatch.setattr(track, "execute_command", _execute_command)

    track.run_track_value_command_spec(
        ctx=object(),
        spec=track.TrackValueCommandSpec[str](
            command_name="track name set",
            client_method="set_track_name",
            value_name="name",
            validators=(str.strip,),
        ),
        track_ref=track_ref,
        value="  Bass  ",
    )

    assert captured["command"] == "track name set"
    assert captured["args"] == {"track_ref": track_ref, "name": "  Bass  "}
    assert captured["result"] == {"track_ref": track_ref, "name": "Bass"}
