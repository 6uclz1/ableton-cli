from __future__ import annotations

import pytest

from ableton_cli.errors import AppError


def _capture_execute_command(captured: dict[str, object]):  # noqa: ANN202
    def _execute_command(_ctx, *, command, args, action, resolved_args=None):  # noqa: ANN202
        captured["command"] = command
        captured["args"] = args
        captured["resolved_args"] = resolved_args() if resolved_args is not None else None
        captured["result"] = action()

    return _execute_command


def test_run_track_device_command_validates_refs_before_client_lookup(monkeypatch) -> None:
    from ableton_cli.commands import _device_family
    from ableton_cli.refs import build_track_ref

    get_client_calls = {"count": 0}

    def _get_client(_ctx):  # noqa: ANN202
        get_client_calls["count"] += 1
        return object()

    def _execute_command(_ctx, *, command, args, action, resolved_args=None):  # noqa: ANN202
        del command, args, resolved_args
        action()

    monkeypatch.setattr(_device_family, "get_client", _get_client)
    monkeypatch.setattr(_device_family, "execute_command", _execute_command)

    with pytest.raises(AppError) as exc:
        _device_family.run_track_device_command(
            ctx=object(),
            command_name="synth test",
            track_ref=lambda: build_track_ref(
                track_index=-1,
                track_name=None,
                selected_track=False,
                track_query=None,
                track_ref=None,
            ),
            device_ref=lambda: {"mode": "index", "index": 2},
            fn=lambda _client, _track, _device: {"ok": True},
        )

    assert exc.value.message == "track_index must be >= 0, got -1"
    assert get_client_calls["count"] == 0


def test_run_track_device_command_dispatches_resolved_refs(monkeypatch) -> None:
    from ableton_cli.commands import _device_family

    captured: dict[str, object] = {}
    track_ref = {"mode": "selected"}
    device_ref = {"mode": "query", "query": "eq"}
    client = object()

    monkeypatch.setattr(_device_family, "get_client", lambda _ctx: client)
    monkeypatch.setattr(_device_family, "execute_command", _capture_execute_command(captured))

    _device_family.run_track_device_command(
        ctx=object(),
        command_name="effect test",
        track_ref=lambda: track_ref,
        device_ref=lambda: device_ref,
        fn=lambda resolved_client, resolved_track_ref, resolved_device_ref: {
            "same_client": resolved_client is client,
            "track_ref": resolved_track_ref,
            "device_ref": resolved_device_ref,
        },
    )

    assert captured["command"] == "effect test"
    assert captured["args"] == {"track_ref": None, "device_ref": None}
    assert captured["resolved_args"] == {"track_ref": track_ref, "device_ref": device_ref}
    assert captured["result"] == {
        "same_client": True,
        "track_ref": track_ref,
        "device_ref": device_ref,
    }
