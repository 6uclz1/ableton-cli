from __future__ import annotations

import importlib


def test_track_domain_modules_exist() -> None:
    module_names = (
        "ableton_cli.commands._track_info_commands",
        "ableton_cli.commands._track_volume_commands",
        "ableton_cli.commands._track_name_commands",
        "ableton_cli.commands._track_mute_commands",
        "ableton_cli.commands._track_solo_commands",
        "ableton_cli.commands._track_arm_commands",
        "ableton_cli.commands._track_panning_commands",
    )

    for module_name in module_names:
        module = importlib.import_module(module_name)
        assert hasattr(module, "register_commands")
