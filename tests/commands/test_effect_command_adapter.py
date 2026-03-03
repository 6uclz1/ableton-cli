from __future__ import annotations

import pytest

from ableton_cli.errors import AppError


def test_run_track_device_command_validates_indices_before_client_lookup(monkeypatch) -> None:
    from ableton_cli.commands import effect

    get_client_calls = {"count": 0}

    def _get_client(_ctx):  # noqa: ANN202
        get_client_calls["count"] += 1
        return object()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del command, args, human_formatter
        action()

    monkeypatch.setattr(effect, "get_client", _get_client)
    monkeypatch.setattr(effect, "execute_command", _execute_command)

    with pytest.raises(AppError) as exc:
        effect.run_track_device_command(
            ctx=object(),
            command_name="effect test",
            track=1,
            device=-1,
            fn=lambda _client, _track, _device: {"ok": True},
        )

    assert exc.value.message == "device must be >= 0, got -1"
    assert get_client_calls["count"] == 0


def test_run_track_device_command_applies_custom_validator(monkeypatch) -> None:
    from ableton_cli.commands import effect

    captured: dict[str, object] = {}
    client = object()

    def _get_client(_ctx):  # noqa: ANN202
        return client

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    def _validator(track_index: int, device_index: int) -> tuple[int, int]:
        return track_index + 2, device_index + 2

    monkeypatch.setattr(effect, "get_client", _get_client)
    monkeypatch.setattr(effect, "execute_command", _execute_command)

    effect.run_track_device_command(
        ctx=object(),
        command_name="effect test",
        track=0,
        device=1,
        fn=lambda resolved_client, valid_track, valid_device: {
            "same_client": resolved_client is client,
            "track": valid_track,
            "device": valid_device,
        },
        validators=[_validator],
    )

    assert captured["command"] == "effect test"
    assert captured["args"] == {"track": 0, "device": 1}
    assert captured["result"] == {"same_client": True, "track": 2, "device": 3}


def test_run_track_device_command_spec_dispatches_client_method(monkeypatch) -> None:
    from ableton_cli.commands import effect

    captured: dict[str, object] = {}

    class _Client:
        def list_effect_parameters(self, track: int, device: int):  # noqa: ANN201
            return {"track": track, "device": device, "parameters": []}

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
        track=3,
        device=2,
    )

    assert captured["command"] == "effect parameters list"
    assert captured["args"] == {"track": 3, "device": 2}
    assert captured["result"] == {"track": 3, "device": 2, "parameters": []}


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
