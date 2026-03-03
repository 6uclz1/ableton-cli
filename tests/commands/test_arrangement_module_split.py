from __future__ import annotations

import importlib


def test_arrangement_domain_modules_exist() -> None:
    module_names = (
        "ableton_cli.commands._arrangement_record_commands",
        "ableton_cli.commands._arrangement_clip_commands",
        "ableton_cli.commands._arrangement_notes_commands",
        "ableton_cli.commands._arrangement_session_commands",
    )

    for module_name in module_names:
        module = importlib.import_module(module_name)
        assert hasattr(module, "register_commands")


def test_arrangement_clip_and_session_modules_expose_specs() -> None:
    clip_module = importlib.import_module("ableton_cli.commands._arrangement_clip_commands")
    session_module = importlib.import_module("ableton_cli.commands._arrangement_session_commands")

    assert hasattr(clip_module, "CLIP_CREATE_SPEC")
    assert hasattr(clip_module, "CLIP_LIST_SPEC")
    assert hasattr(clip_module, "CLIP_DELETE_SPEC")
    assert hasattr(session_module, "FROM_SESSION_SPEC")
