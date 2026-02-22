from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    BaselineConfig,
    Config,
    DependenciesConfig,
    DuplicationConfig,
    LayerRule,
    LayersConfig,
    Severity,
    Threshold,
    ThresholdGroups,
)

TOP_LEVEL_KEYS = {
    "version",
    "phase",
    "include",
    "exclude",
    "duplication",
    "thresholds",
    "parse_errors",
    "baseline",
    "dependencies",
    "layers",
}

THRESHOLD_KEYS: dict[str, set[str]] = {
    "file": {"complexity", "imports", "estimated_tokens"},
    "function": {"complexity", "nesting", "args", "estimated_tokens"},
    "class": {
        "complexity",
        "nesting",
        "args",
        "imports",
        "estimated_tokens",
        "god_class_risk",
    },
    "duplicates": {"occurrences"},
}


class ConfigError(ValueError):
    pass


def load_config(path: Path) -> Config:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - surfaced by CLI tests
        raise ConfigError(f"failed to read config file: {path}") from exc

    try:
        raw_data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"failed to parse yaml: {exc}") from exc

    data = _expect_mapping(raw_data, context="root")
    _require_exact_keys(data, required=TOP_LEVEL_KEYS, context="root")

    version = _expect_int(data["version"], context="version", min_value=1)
    if version != 1:
        raise ConfigError("version must be 1")

    phase = _expect_int(data["phase"], context="phase", min_value=1)
    if phase != 2:
        raise ConfigError("phase must be 2 for this harness")

    include = _expect_string_list(data["include"], context="include", allow_empty=False)
    exclude = _expect_string_list(data["exclude"], context="exclude", allow_empty=True)

    duplication = _parse_duplication(data["duplication"])
    thresholds = _parse_thresholds(data["thresholds"])
    parse_errors_mode = _parse_parse_errors_mode(data["parse_errors"])
    baseline = _parse_baseline(data["baseline"])
    dependencies = _parse_dependencies(data["dependencies"])
    layers = _parse_layers(data["layers"])

    return Config(
        version=version,
        phase=phase,
        include=include,
        exclude=exclude,
        duplication=duplication,
        thresholds=thresholds,
        parse_errors_mode=parse_errors_mode,
        baseline=baseline,
        dependencies=dependencies,
        layers=layers,
    )


def config_to_dict(config: Config) -> dict[str, Any]:
    return {
        "version": config.version,
        "phase": config.phase,
        "include": list(config.include),
        "exclude": list(config.exclude),
        "duplication": {
            "min_lines": config.duplication.min_lines,
            "min_tokens": config.duplication.min_tokens,
        },
        "thresholds": {
            "file": _threshold_map_to_dict(config.thresholds.file),
            "function": _threshold_map_to_dict(config.thresholds.function),
            "class": _threshold_map_to_dict(config.thresholds.class_),
            "duplicates": _threshold_map_to_dict(config.thresholds.duplicates),
        },
        "parse_errors": {"mode": config.parse_errors_mode},
        "baseline": {
            "warning_delta": _single_threshold_to_dict(config.baseline.warning_delta),
            "failure_delta": _single_threshold_to_dict(config.baseline.failure_delta),
            "new_failures": _single_threshold_to_dict(config.baseline.new_failures),
        },
        "dependencies": {
            "cycle_count": _single_threshold_to_dict(config.dependencies.cycle_count),
        },
        "layers": {
            "violation_count": _single_threshold_to_dict(config.layers.violation_count),
            "order": [
                {
                    "name": rule.name,
                    "include": list(rule.include),
                }
                for rule in config.layers.order
            ],
        },
    }


def _single_threshold_to_dict(threshold: Threshold) -> dict[str, float]:
    return {"warn": threshold.warn, "fail": threshold.fail}


def _threshold_map_to_dict(thresholds: dict[str, Threshold]) -> dict[str, dict[str, float]]:
    return {
        metric: _single_threshold_to_dict(threshold)
        for metric, threshold in sorted(thresholds.items())
    }


def _parse_duplication(raw_value: Any) -> DuplicationConfig:
    data = _expect_mapping(raw_value, context="duplication")
    _require_exact_keys(data, required={"min_lines", "min_tokens"}, context="duplication")

    min_lines = _expect_int(data["min_lines"], context="duplication.min_lines", min_value=1)
    min_tokens = _expect_int(data["min_tokens"], context="duplication.min_tokens", min_value=1)
    return DuplicationConfig(min_lines=min_lines, min_tokens=min_tokens)


def _parse_thresholds(raw_value: Any) -> ThresholdGroups:
    data = _expect_mapping(raw_value, context="thresholds")
    _require_exact_keys(data, required=set(THRESHOLD_KEYS), context="thresholds")

    parsed: dict[str, dict[str, Threshold]] = {}
    for scope, metrics in THRESHOLD_KEYS.items():
        section = _expect_mapping(data[scope], context=f"thresholds.{scope}")
        _require_exact_keys(section, required=metrics, context=f"thresholds.{scope}")

        parsed_metrics: dict[str, Threshold] = {}
        for metric_name in metrics:
            parsed_metrics[metric_name] = _parse_threshold(
                raw_value=section[metric_name],
                context=f"thresholds.{scope}.{metric_name}",
            )
        parsed[scope] = parsed_metrics

    return ThresholdGroups(
        file=parsed["file"],
        function=parsed["function"],
        class_=parsed["class"],
        duplicates=parsed["duplicates"],
    )


def _parse_parse_errors_mode(raw_value: Any) -> Severity:
    data = _expect_mapping(raw_value, context="parse_errors")
    _require_exact_keys(data, required={"mode"}, context="parse_errors")

    mode = data["mode"]
    if mode not in {"warn", "fail"}:
        raise ConfigError("parse_errors.mode must be 'warn' or 'fail'")
    return mode


def _parse_baseline(raw_value: Any) -> BaselineConfig:
    data = _expect_mapping(raw_value, context="baseline")
    _require_exact_keys(
        data,
        required={"warning_delta", "failure_delta", "new_failures"},
        context="baseline",
    )

    return BaselineConfig(
        warning_delta=_parse_threshold(
            raw_value=data["warning_delta"], context="baseline.warning_delta"
        ),
        failure_delta=_parse_threshold(
            raw_value=data["failure_delta"], context="baseline.failure_delta"
        ),
        new_failures=_parse_threshold(
            raw_value=data["new_failures"], context="baseline.new_failures"
        ),
    )


def _parse_dependencies(raw_value: Any) -> DependenciesConfig:
    data = _expect_mapping(raw_value, context="dependencies")
    _require_exact_keys(data, required={"cycle_count"}, context="dependencies")

    return DependenciesConfig(
        cycle_count=_parse_threshold(
            raw_value=data["cycle_count"],
            context="dependencies.cycle_count",
        )
    )


def _parse_layers(raw_value: Any) -> LayersConfig:
    data = _expect_mapping(raw_value, context="layers")
    _require_exact_keys(data, required={"violation_count", "order"}, context="layers")

    order_raw = data["order"]
    if not isinstance(order_raw, list) or not order_raw:
        raise ConfigError("layers.order must be a non-empty list")

    order: list[LayerRule] = []
    known_names: set[str] = set()
    for index, item in enumerate(order_raw):
        entry = _expect_mapping(item, context=f"layers.order[{index}]")
        _require_exact_keys(entry, required={"name", "include"}, context=f"layers.order[{index}]")

        name = entry["name"]
        if not isinstance(name, str) or not name:
            raise ConfigError(f"layers.order[{index}].name must be a non-empty string")
        if name in known_names:
            raise ConfigError(f"layers.order[{index}].name must be unique: {name}")
        known_names.add(name)

        include = _expect_string_list(
            entry["include"],
            context=f"layers.order[{index}].include",
            allow_empty=False,
        )
        order.append(LayerRule(name=name, include=include))

    return LayersConfig(
        violation_count=_parse_threshold(
            raw_value=data["violation_count"],
            context="layers.violation_count",
        ),
        order=order,
    )


def _parse_threshold(*, raw_value: Any, context: str) -> Threshold:
    data = _expect_mapping(raw_value, context=context)
    _require_exact_keys(data, required={"warn", "fail"}, context=context)

    warn = _expect_number(data["warn"], context=f"{context}.warn", min_value=0.0)
    fail = _expect_number(data["fail"], context=f"{context}.fail", min_value=0.0)
    if warn >= fail:
        raise ConfigError(f"warn must be lower than fail: {context}")
    return Threshold(warn=warn, fail=fail)


def _expect_mapping(raw_value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(raw_value, dict):
        raise ConfigError(f"{context} must be a mapping")
    normalized: dict[str, Any] = {}
    for key, value in raw_value.items():
        if not isinstance(key, str):
            raise ConfigError(f"{context} contains non-string key")
        normalized[key] = value
    return normalized


def _expect_string_list(raw_value: Any, *, context: str, allow_empty: bool) -> list[str]:
    if not isinstance(raw_value, list):
        raise ConfigError(f"{context} must be a list")
    if not allow_empty and not raw_value:
        raise ConfigError(f"{context} must not be empty")
    values: list[str] = []
    for index, item in enumerate(raw_value):
        if not isinstance(item, str) or not item:
            raise ConfigError(f"{context}[{index}] must be a non-empty string")
        values.append(item)
    return values


def _expect_int(raw_value: Any, *, context: str, min_value: int) -> int:
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ConfigError(f"{context} must be an integer")
    if raw_value < min_value:
        raise ConfigError(f"{context} must be >= {min_value}")
    return raw_value


def _expect_number(raw_value: Any, *, context: str, min_value: float) -> float:
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        raise ConfigError(f"{context} must be a number")
    value = float(raw_value)
    if value < min_value:
        raise ConfigError(f"{context} must be >= {min_value}")
    return value


def _require_exact_keys(
    data: dict[str, Any],
    *,
    required: set[str],
    context: str,
) -> None:
    missing = sorted(required - set(data))
    unknown = sorted(set(data) - required)
    if missing:
        raise ConfigError(f"missing required key(s) in {context}: {', '.join(missing)}")
    if unknown:
        raise ConfigError(f"unknown key(s) in {context}: {', '.join(unknown)}")
