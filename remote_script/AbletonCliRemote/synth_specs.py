from __future__ import annotations

from typing import Any

SUPPORTED_SYNTH_TYPES: tuple[str, ...] = ("wavetable", "drift", "meld")

_STANDARD_SYNTH_PARAMETER_NAMES: dict[str, dict[str, str]] = {
    "wavetable": {
        "filter_cutoff": "Filter 1 Freq",
        "filter_resonance": "Filter 1 Res",
        "amp_attack": "Amp Attack",
        "amp_decay": "Amp Decay",
        "amp_sustain": "Amp Sustain",
        "amp_release": "Amp Release",
        "osc1_position": "Osc 1 Pos",
        "osc2_position": "Osc 2 Pos",
        "unison_amount": "Unison Amount",
    },
    "drift": {
        "filter_cutoff": "LP Freq",
        "filter_resonance": "LP Reso",
        "amp_attack": "Env 1 Attack",
        "amp_decay": "Env 1 Decay",
        "amp_sustain": "Env 1 Sustain",
        "amp_release": "Env 1 Release",
        "osc1_shape": "Osc 1 Shape",
        "osc2_shape": "Osc 2 Wave",
        "drift_amount": "Drift",
    },
    "meld": {
        "filter_cutoff": "A Filter Freq",
        "filter_resonance": "A Filter Q",
        "amp_attack": "A Amp Attack",
        "amp_decay": "A Amp Decay",
        "amp_sustain": "A Amp Sustain",
        "amp_release": "A Amp Release",
        "oscillator_balance": "B Volume",
        "timbre_amount": "A Osc Tone",
        "spread_amount": "Voice Spread",
    },
}


def _normalize_label(value: str) -> str:
    return " ".join(value.strip().lower().split())


def canonicalize_synth_type(value: str) -> str:
    normalized = _normalize_label(value)
    if normalized not in _STANDARD_SYNTH_PARAMETER_NAMES:
        raise ValueError(f"unsupported synth_type: {value!r}")
    return normalized


def detect_synth_type(device: Any) -> str | None:
    labels = (
        str(getattr(device, "name", "")),
        str(getattr(device, "class_name", "")),
        str(getattr(device, "class_display_name", "")),
    )
    normalized_labels = [_normalize_label(label) for label in labels if str(label).strip()]
    for synth_type in SUPPORTED_SYNTH_TYPES:
        if any(synth_type in label for label in normalized_labels):
            return synth_type
    return None


def standard_parameter_name_map(synth_type: str) -> dict[str, str]:
    parsed_type = canonicalize_synth_type(synth_type)
    return dict(_STANDARD_SYNTH_PARAMETER_NAMES[parsed_type])


def standard_synth_keys(synth_type: str) -> list[str]:
    return list(standard_parameter_name_map(synth_type).keys())


def resolve_standard_synth_key_indexes(
    parameter_names: list[str], synth_type: str
) -> tuple[dict[str, int], list[str]]:
    expected_map = standard_parameter_name_map(synth_type)
    normalized_to_index: dict[str, int] = {}
    for index, name in enumerate(parameter_names):
        normalized_name = _normalize_label(str(name))
        if normalized_name and normalized_name not in normalized_to_index:
            normalized_to_index[normalized_name] = index

    key_indexes: dict[str, int] = {}
    missing_keys: list[str] = []
    for key, expected_name in expected_map.items():
        resolved_index = normalized_to_index.get(_normalize_label(expected_name))
        if resolved_index is None:
            missing_keys.append(key)
            continue
        key_indexes[key] = resolved_index
    return key_indexes, missing_keys
