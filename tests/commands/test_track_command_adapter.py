from __future__ import annotations

import pytest

from ableton_cli.errors import AppError


def test_run_track_command_validates_track_before_client_lookup(monkeypatch) -> None:
    from ableton_cli.commands import track

    get_client_calls = {"count": 0}

    def _get_client(_ctx):  # noqa: ANN202
        get_client_calls["count"] += 1
        return object()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del command, args, human_formatter
        action()

    monkeypatch.setattr(track, "get_client", _get_client)
    monkeypatch.setattr(track, "execute_command", _execute_command)

    with pytest.raises(AppError) as exc:
        track.run_track_command(
            ctx=object(),
            command_name="track test",
            track=-1,
            fn=lambda _client, _track: {"ok": True},
        )

    assert exc.value.message == "track must be >= 0, got -1"
    assert get_client_calls["count"] == 0


def test_run_track_value_command_applies_custom_validators(monkeypatch) -> None:
    from ableton_cli.commands import track

    captured: dict[str, object] = {}
    client = object()

    def _get_client(_ctx):  # noqa: ANN202
        return client

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    def _validator(track_index: int, value: float) -> tuple[int, float]:
        return track_index + 1, value + 0.25

    monkeypatch.setattr(track, "get_client", _get_client)
    monkeypatch.setattr(track, "execute_command", _execute_command)

    track.run_track_value_command(
        ctx=object(),
        command_name="track test set",
        track=1,
        value=0.5,
        fn=lambda resolved_client, valid_track, valid_value: {
            "same_client": resolved_client is client,
            "track": valid_track,
            "value": valid_value,
        },
        validators=[_validator],
    )

    assert captured["command"] == "track test set"
    assert captured["args"] == {"track": 1, "value": 0.5}
    assert captured["result"] == {"same_client": True, "track": 2, "value": 0.75}


def test_run_track_value_command_defaults_to_track_validation(monkeypatch) -> None:
    from ableton_cli.commands import track

    get_client_calls = {"count": 0}

    def _get_client(_ctx):  # noqa: ANN202
        get_client_calls["count"] += 1
        return object()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del command, args, human_formatter
        action()

    monkeypatch.setattr(track, "get_client", _get_client)
    monkeypatch.setattr(track, "execute_command", _execute_command)

    with pytest.raises(AppError) as exc:
        track.run_track_value_command(
            ctx=object(),
            command_name="track test set",
            track=-1,
            value=True,
            fn=lambda _client, _track, _value: {"ok": True},
        )

    assert exc.value.message == "track must be >= 0, got -1"
    assert get_client_calls["count"] == 0
