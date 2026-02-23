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
