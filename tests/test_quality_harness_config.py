from __future__ import annotations

from pathlib import Path

from ableton_cli.quality_harness.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
QUALITY_HARNESS_CONFIG = REPO_ROOT / ".quality-harness.yml"


def test_commands_layer_includes_app_factory() -> None:
    config = load_config(QUALITY_HARNESS_CONFIG)

    commands_layer = next(rule for rule in config.layers.order if rule.name == "commands")
    assert "src/ableton_cli/app_factory.py" in commands_layer.include


def test_function_args_threshold_allows_cli_entry_points() -> None:
    config = load_config(QUALITY_HARNESS_CONFIG)

    function_args_threshold = config.thresholds.function["args"]
    assert function_args_threshold.warn == 8
    assert function_args_threshold.fail == 20


def test_class_args_threshold_allows_remote_contract_surfaces() -> None:
    config = load_config(QUALITY_HARNESS_CONFIG)

    class_args_threshold = config.thresholds.class_["args"]
    assert class_args_threshold.warn == 8
    assert class_args_threshold.fail == 14
