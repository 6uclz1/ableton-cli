from __future__ import annotations

import json
from pathlib import Path

import pytest

from remote_script.AbletonCliRemote.effect_specs import (
    SUPPORTED_EFFECT_TYPES,
    resolve_standard_effect_key_indexes,
    standard_effect_keys,
)
from remote_script.AbletonCliRemote.synth_specs import (
    SUPPORTED_SYNTH_TYPES,
    resolve_standard_synth_key_indexes,
)

# Parameter names captured from Ableton Live 12 factory devices. The supported
# Live version is 12+, so every standard key must resolve against these names.
_LIVE_12_NAMES = json.loads(
    (Path(__file__).parent / "fixtures" / "live_12_device_parameter_names.json").read_text(
        encoding="utf-8"
    )
)


def test_fixture_covers_every_supported_device_type() -> None:
    assert set(_LIVE_12_NAMES["synths"]) == set(SUPPORTED_SYNTH_TYPES)
    assert set(_LIVE_12_NAMES["effects"]) == set(SUPPORTED_EFFECT_TYPES)


@pytest.mark.parametrize("synth_type", SUPPORTED_SYNTH_TYPES)
def test_every_standard_synth_key_resolves_on_live_12(synth_type: str) -> None:
    _, missing = resolve_standard_synth_key_indexes(
        _LIVE_12_NAMES["synths"][synth_type], synth_type
    )

    assert missing == []


@pytest.mark.parametrize("effect_type", SUPPORTED_EFFECT_TYPES)
def test_every_standard_effect_key_resolves_on_live_12(effect_type: str) -> None:
    _, missing = resolve_standard_effect_key_indexes(
        _LIVE_12_NAMES["effects"][effect_type], effect_type
    )

    assert missing == []


@pytest.mark.parametrize(
    ("synth_type", "key", "live_name"),
    [
        ("wavetable", "filter_cutoff", "Flt 1 Freq"),
        ("wavetable", "filter_resonance", "Flt 1 Res"),
        ("drift", "filter_resonance", "LP Res"),
    ],
)
def test_standard_synth_key_targets_the_live_12_parameter(
    synth_type: str, key: str, live_name: str
) -> None:
    names = _LIVE_12_NAMES["synths"][synth_type]

    indexes, _ = resolve_standard_synth_key_indexes(names, synth_type)

    assert names[indexes[key]] == live_name


@pytest.mark.parametrize(
    ("effect_type", "key", "live_name"),
    [
        ("utility", "gain", "Output"),
        ("reverb", "input_filter_freq", "Input Freq"),
        ("reverb", "input_filter_width", "Input Width"),
    ],
)
def test_standard_effect_key_targets_the_live_12_parameter(
    effect_type: str, key: str, live_name: str
) -> None:
    names = _LIVE_12_NAMES["effects"][effect_type]

    indexes, _ = resolve_standard_effect_key_indexes(names, effect_type)

    assert names[indexes[key]] == live_name


def test_reverb_keys_describe_the_live_12_input_filter() -> None:
    # Live 12 Reverb has one band-pass input filter (frequency and width),
    # not separate low-cut and high-cut frequencies.
    assert standard_effect_keys("reverb") == [
        "decay_time",
        "pre_delay",
        "size",
        "input_filter_freq",
        "input_filter_width",
    ]
