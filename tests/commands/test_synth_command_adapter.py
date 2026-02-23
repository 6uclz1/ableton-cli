from __future__ import annotations

import pytest

from ableton_cli.errors import AppError


def test_run_track_device_command_validates_indices_before_client_lookup(monkeypatch) -> None:
    from ableton_cli.commands import synth

    get_client_calls = {"count": 0}

    def _get_client(_ctx):  # noqa: ANN202
        get_client_calls["count"] += 1
        return object()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del command, args, human_formatter
        action()

    monkeypatch.setattr(synth, "get_client", _get_client)
    monkeypatch.setattr(synth, "execute_command", _execute_command)

    with pytest.raises(AppError) as exc:
        synth.run_track_device_command(
            ctx=object(),
            command_name="synth test",
            track=-1,
            device=2,
            fn=lambda _client, _track, _device: {"ok": True},
        )

    assert exc.value.message == "track must be >= 0, got -1"
    assert get_client_calls["count"] == 0


def test_run_track_device_command_applies_custom_validator(monkeypatch) -> None:
    from ableton_cli.commands import synth

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
        return track_index + 1, device_index + 1

    monkeypatch.setattr(synth, "get_client", _get_client)
    monkeypatch.setattr(synth, "execute_command", _execute_command)

    synth.run_track_device_command(
        ctx=object(),
        command_name="synth test",
        track=2,
        device=3,
        fn=lambda resolved_client, valid_track, valid_device: {
            "same_client": resolved_client is client,
            "track": valid_track,
            "device": valid_device,
        },
        validators=[_validator],
    )

    assert captured["command"] == "synth test"
    assert captured["args"] == {"track": 2, "device": 3}
    assert captured["result"] == {"same_client": True, "track": 3, "device": 4}
