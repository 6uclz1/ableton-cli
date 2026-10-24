from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .effect_specs import (
    SUPPORTED_EFFECT_TYPES,
    canonicalize_effect_type,
    detect_effect_type,
    resolve_standard_effect_key_indexes,
    standard_effect_keys,
)
from .synth_specs import (
    SUPPORTED_SYNTH_TYPES,
    canonicalize_synth_type,
    detect_synth_type,
    resolve_standard_synth_key_indexes,
    standard_synth_keys,
)


@dataclass(frozen=True, slots=True)
class DeviceFamily:
    """Native devices (synths, effects) that share one command shape and key catalog."""

    name: str
    supported_types: tuple[str, ...]
    canonicalize: Callable[[str], str]
    detect: Callable[[Any], str | None]
    standard_keys: Callable[[str], list[str]]
    resolve_key_indexes: Callable[[list[str], str], tuple[dict[str, int], list[str]]]
    unsupported_device_hint: str

    @property
    def type_arg(self) -> str:
        return f"{self.name}_type"


SYNTH_FAMILY = DeviceFamily(
    name="synth",
    supported_types=SUPPORTED_SYNTH_TYPES,
    canonicalize=canonicalize_synth_type,
    detect=detect_synth_type,
    standard_keys=standard_synth_keys,
    resolve_key_indexes=resolve_standard_synth_key_indexes,
    unsupported_device_hint="Choose a Wavetable, Drift, or Meld device.",
)

EFFECT_FAMILY = DeviceFamily(
    name="effect",
    supported_types=SUPPORTED_EFFECT_TYPES,
    canonicalize=canonicalize_effect_type,
    detect=detect_effect_type,
    standard_keys=standard_effect_keys,
    resolve_key_indexes=resolve_standard_effect_key_indexes,
    unsupported_device_hint="Choose one of the supported audio effects.",
)

DEVICE_FAMILIES: tuple[DeviceFamily, ...] = (SYNTH_FAMILY, EFFECT_FAMILY)
