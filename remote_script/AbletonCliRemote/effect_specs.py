from __future__ import annotations

from typing import Any

SUPPORTED_EFFECT_TYPES: tuple[str, ...] = (
    "eq8",
    "limiter",
    "compressor",
    "auto_filter",
    "reverb",
    "utility",
)

_STANDARD_EFFECT_PARAMETER_NAMES: dict[str, dict[str, tuple[str, ...]]] = {
    "eq8": {
        "band1_freq": ("1 Frequency A", "Band 1 Frequency"),
        "band1_gain": ("1 Gain A", "Band 1 Gain"),
        "band1_q": ("1 Q A", "1 Resonance A", "Band 1 Q"),
        "low_cut_freq": ("LowCut Frequency", "Low Cut Frequency", "1 Frequency A"),
        "high_cut_freq": ("HighCut Frequency", "High Cut Frequency", "8 Frequency A"),
    },
    "limiter": {
        "gain": ("Gain", "Input Gain"),
        "ceiling": ("Ceiling",),
        "release": ("Release",),
        "lookahead": ("Lookahead", "Look Ahead"),
        "soft_clip": ("Soft Clip", "Softclip", "Maximize On"),
    },
    "compressor": {
        "threshold": ("Threshold",),
        "ratio": ("Ratio",),
        "attack": ("Attack",),
        "release": ("Release",),
        "makeup": ("Makeup", "Make-up"),
    },
    "auto_filter": {
        "frequency": ("Frequency",),
        "resonance": ("Resonance", "Reson"),
        "env_amount": ("Env Amount", "Envelope Amount"),
        "lfo_amount": ("LFO Amount",),
        "lfo_rate": ("LFO Rate",),
    },
    "reverb": {
        "decay_time": ("Decay Time",),
        "pre_delay": ("PreDelay", "Pre Delay", "Predelay"),
        "size": ("Size", "Room Size"),
        "low_cut": ("LowCut", "Low Cut", "In Filter Freq"),
        "high_cut": ("HighCut", "High Cut", "HiFilter Freq"),
    },
    "utility": {
        "gain": ("Gain",),
        "width": ("Width", "Stereo Width"),
        "balance": ("Balance",),
        "bass_mono": ("Bass Mono",),
        "bass_mono_frequency": ("Bass Mono Frequency", "Bass Freq"),
    },
}

_DETECTION_LABELS: dict[str, tuple[str, ...]] = {
    "eq8": ("eq eight", "eq8"),
    "limiter": ("limiter",),
    "compressor": ("compressor",),
    "auto_filter": ("auto filter", "autofilter"),
    "reverb": ("reverb",),
    "utility": ("utility",),
}


def _normalize_label(value: str) -> str:
    return " ".join(value.strip().lower().split())


def canonicalize_effect_type(value: str) -> str:
    normalized = _normalize_label(value).replace("-", "_")
    if normalized not in _STANDARD_EFFECT_PARAMETER_NAMES:
        raise ValueError(f"unsupported effect_type: {value!r}")
    return normalized


def detect_effect_type(device: Any) -> str | None:
    labels = (
        str(getattr(device, "name", "")),
        str(getattr(device, "class_name", "")),
        str(getattr(device, "class_display_name", "")),
    )
    normalized_labels = [_normalize_label(label) for label in labels if str(label).strip()]
    for effect_type in SUPPORTED_EFFECT_TYPES:
        signatures = _DETECTION_LABELS[effect_type]
        if any(signature in label for label in normalized_labels for signature in signatures):
            return effect_type
    return None


def standard_parameter_alias_map(effect_type: str) -> dict[str, tuple[str, ...]]:
    parsed_type = canonicalize_effect_type(effect_type)
    return dict(_STANDARD_EFFECT_PARAMETER_NAMES[parsed_type])


def standard_effect_keys(effect_type: str) -> list[str]:
    return list(standard_parameter_alias_map(effect_type).keys())


def resolve_standard_effect_key_indexes(
    parameter_names: list[str], effect_type: str
) -> tuple[dict[str, int], list[str]]:
    expected_map = standard_parameter_alias_map(effect_type)
    normalized_to_index: dict[str, int] = {}
    for index, name in enumerate(parameter_names):
        normalized_name = _normalize_label(str(name))
        if normalized_name and normalized_name not in normalized_to_index:
            normalized_to_index[normalized_name] = index

    key_indexes: dict[str, int] = {}
    missing_keys: list[str] = []
    for key, aliases in expected_map.items():
        resolved_index: int | None = None
        for alias in aliases:
            candidate = normalized_to_index.get(_normalize_label(alias))
            if candidate is not None:
                resolved_index = candidate
                break
        if resolved_index is None:
            missing_keys.append(key)
            continue
        key_indexes[key] = resolved_index
    return key_indexes, missing_keys
