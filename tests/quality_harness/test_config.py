from __future__ import annotations

from pathlib import Path

import pytest

from ableton_cli.quality_harness.config import ConfigError, load_config

from .helpers import write_config


def test_load_config_success(tmp_path: Path) -> None:
    config_path = write_config(tmp_path / ".quality-harness.yml", include=["src/**/*.py"])

    config = load_config(config_path)

    assert config.version == 1
    assert config.phase == 2
    assert config.include == ["src/**/*.py"]
    assert config.parse_errors_mode == "warn"
    assert config.thresholds.function["complexity"].warn == 10
    assert config.thresholds.function["complexity"].fail == 15
    assert config.baseline.warning_delta.warn == 5
    assert config.dependencies.cycle_count.fail == 3
    assert config.layers.order[0].name == "app"


def test_load_config_requires_all_top_level_keys(tmp_path: Path) -> None:
    config_path = tmp_path / ".quality-harness.yml"
    config_path.write_text("version: 1\nphase: 2\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="missing required key"):
        load_config(config_path)


def test_load_config_rejects_warn_ge_fail(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / ".quality-harness.yml",
        include=["src/**/*.py"],
        function_complexity_warn=15,
        function_complexity_fail=15,
    )

    with pytest.raises(ConfigError, match="warn must be lower than fail"):
        load_config(config_path)


def test_load_config_rejects_non_phase2(tmp_path: Path) -> None:
    config_path = write_config(tmp_path / ".quality-harness.yml", include=["src/**/*.py"])
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("phase: 2", "phase: 1"),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="phase must be 2"):
        load_config(config_path)
