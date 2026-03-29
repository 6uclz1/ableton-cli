from __future__ import annotations


def test_run_track_device_command_dispatches_ref_payloads(monkeypatch) -> None:
    from ableton_cli.commands import effect

    captured: dict[str, object] = {}
    track_ref = {"mode": "selected"}
    device_ref = {"mode": "query", "query": "eq"}

    class _Client:
        def list_effect_parameters(self, track_ref, device_ref):  # noqa: ANN001, ANN201
            return {"track_ref": track_ref, "device_ref": device_ref, "parameters": []}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(effect, "get_client", _get_client)
    monkeypatch.setattr(effect, "execute_command", _execute_command)

    effect.run_track_device_command(
        ctx=object(),
        command_name="effect test",
        track_ref=track_ref,
        device_ref=device_ref,
        fn=lambda resolved_client, resolved_track_ref, resolved_device_ref: {
            "same_client": isinstance(resolved_client, _Client),
            "track_ref": resolved_track_ref,
            "device_ref": resolved_device_ref,
        },
    )

    assert captured["command"] == "effect test"
    assert captured["args"] == {"track_ref": track_ref, "device_ref": device_ref}
    assert captured["result"] == {
        "same_client": True,
        "track_ref": track_ref,
        "device_ref": device_ref,
    }


def test_run_track_device_command_spec_dispatches_client_method(monkeypatch) -> None:
    from ableton_cli.commands import effect

    captured: dict[str, object] = {}
    track_ref = {"mode": "index", "index": 3}
    device_ref = {"mode": "stable_ref", "stable_ref": "device:2"}

    class _Client:
        def list_effect_parameters(self, track_ref, device_ref):  # noqa: ANN001, ANN201
            return {"track_ref": track_ref, "device_ref": device_ref, "parameters": []}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(effect, "get_client", _get_client)
    monkeypatch.setattr(effect, "execute_command", _execute_command)

    effect.run_track_device_command_spec(
        ctx=object(),
        spec=effect.TrackDeviceCommandSpec(
            command_name="effect parameters list",
            client_method="list_effect_parameters",
        ),
        track_ref=track_ref,
        device_ref=device_ref,
    )

    assert captured["command"] == "effect parameters list"
    assert captured["args"] == {"track_ref": track_ref, "device_ref": device_ref}
    assert captured["result"] == {
        "track_ref": track_ref,
        "device_ref": device_ref,
        "parameters": [],
    }


def test_run_client_command_spec_dispatches_method(monkeypatch) -> None:
    from ableton_cli.commands import effect

    captured: dict[str, object] = {}

    class _Client:
        def find_effect_devices(  # noqa: ANN201
            self,
            track: int | None,
            effect_type: str | None,
        ):
            return {"track": track, "effect_type": effect_type}

    def _get_client(_ctx):  # noqa: ANN202
        return _Client()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    monkeypatch.setattr(effect, "get_client", _get_client)
    monkeypatch.setattr(effect, "execute_command", _execute_command)

    effect.run_client_command_spec(
        ctx=object(),
        spec=effect.EffectCommandSpec(
            command_name="effect find",
            client_method="find_effect_devices",
        ),
        args={"track": 0, "effect_type": "eq8"},
        method_kwargs={"track": 0, "effect_type": "eq8"},
    )

    assert captured["command"] == "effect find"
    assert captured["args"] == {"track": 0, "effect_type": "eq8"}
    assert captured["result"] == {"track": 0, "effect_type": "eq8"}
