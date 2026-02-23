from __future__ import annotations

import pytest

from ableton_cli.errors import AppError


def test_run_scene_command_validates_scene_before_client_lookup(monkeypatch) -> None:
    from ableton_cli.commands import scenes

    get_client_calls = {"count": 0}

    def _get_client(_ctx):  # noqa: ANN202
        get_client_calls["count"] += 1
        return object()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del command, args, human_formatter
        action()

    monkeypatch.setattr(scenes, "get_client", _get_client)
    monkeypatch.setattr(scenes, "execute_command", _execute_command)

    with pytest.raises(AppError) as exc:
        scenes.run_scene_command(
            ctx=object(),
            command_name="scenes test",
            scene=-1,
            fn=lambda _client, _scene: {"ok": True},
        )

    assert exc.value.message == "scene must be >= 0, got -1"
    assert get_client_calls["count"] == 0


def test_run_scene_value_command_applies_custom_validator(monkeypatch) -> None:
    from ableton_cli.commands import scenes

    captured: dict[str, object] = {}
    client = object()

    def _get_client(_ctx):  # noqa: ANN202
        return client

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del human_formatter
        captured["command"] = command
        captured["args"] = args
        captured["result"] = action()

    def _validator(scene_index: int, value: str) -> tuple[int, str]:
        return scene_index + 1, value.strip().upper()

    monkeypatch.setattr(scenes, "get_client", _get_client)
    monkeypatch.setattr(scenes, "execute_command", _execute_command)

    scenes.run_scene_value_command(
        ctx=object(),
        command_name="scenes test set",
        scene=2,
        value="  build ",
        value_name="name",
        fn=lambda resolved_client, valid_scene, valid_name: {
            "same_client": resolved_client is client,
            "scene": valid_scene,
            "name": valid_name,
        },
        validators=[_validator],
    )

    assert captured["command"] == "scenes test set"
    assert captured["args"] == {"scene": 2, "name": "  build "}
    assert captured["result"] == {"same_client": True, "scene": 3, "name": "BUILD"}


def test_run_scene_move_command_validates_indices_before_client_lookup(monkeypatch) -> None:
    from ableton_cli.commands import scenes

    get_client_calls = {"count": 0}

    def _get_client(_ctx):  # noqa: ANN202
        get_client_calls["count"] += 1
        return object()

    def _execute_command(_ctx, *, command, args, action, human_formatter=None):  # noqa: ANN202
        del command, args, human_formatter
        action()

    monkeypatch.setattr(scenes, "get_client", _get_client)
    monkeypatch.setattr(scenes, "execute_command", _execute_command)

    with pytest.raises(AppError) as exc:
        scenes.run_scene_move_command(
            ctx=object(),
            command_name="scenes move test",
            from_scene=-1,
            to_scene=1,
            fn=lambda _client, _from_scene, _to_scene: {"ok": True},
        )

    assert exc.value.message == "from must be >= 0, got -1"
    assert get_client_calls["count"] == 0
