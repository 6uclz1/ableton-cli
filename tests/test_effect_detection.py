from __future__ import annotations

from types import SimpleNamespace

import pytest

from remote_script.AbletonCliRemote.effect_specs import detect_effect_type


def _device(name: str, class_name: str, class_display_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        class_name=class_name,
        class_display_name=class_display_name,
    )


def test_detects_live_compressor_as_compressor() -> None:
    device = _device("Compressor", "Compressor2", "Compressor")

    assert detect_effect_type(device) == "compressor"


@pytest.mark.parametrize(
    "name",
    ["Glue Compressor", "Bus Compressor", "Compressor"],
)
def test_glue_compressor_is_not_a_supported_effect(name: str) -> None:
    # Glue has no Makeup parameter and uses other value scales, so the
    # compressor key catalog does not apply to it, even after a rename.
    device = _device(name, "GlueCompressor", "Glue Compressor")

    assert detect_effect_type(device) is None
