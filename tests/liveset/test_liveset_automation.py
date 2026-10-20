from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from live_set_builder import (
    DEFAULT_EVENT_TIME,
    DeviceSpec,
    ParameterSpec,
    SetSpec,
    TrackSpec,
)

from ableton_cli.errors import AppError
from ableton_cli.liveset.document import load_live_set
from ableton_cli.liveset.integrity import check_integrity
from ableton_cli.liveset.ops.automation import AutomationScope, write_automation

POINTS = [{"time": 0.0, "value": 0.5}, {"time": 16.0, "value": 1.0}]


def _spec() -> SetSpec:
    return SetSpec(
        tracks=[
            TrackSpec(
                name="Keys",
                devices=[
                    DeviceSpec(
                        tag="AutoFilter2",
                        parameters=[
                            ParameterSpec("Cutoff", "100", ("20", "135")),
                            ParameterSpec("Resonance", "0.25", ("0", "1.25")),
                            ParameterSpec("FilterType", "0", ("0", "5"), modulatable=False),
                            ParameterSpec("Unranged", "0.5", modulatable=False),
                        ],
                    )
                ],
            ),
            TrackSpec(tag="ReturnTrack", id=20, name="A-Reverb"),
            TrackSpec(tag="ReturnTrack", id=21, name="B-Delay"),
        ]
    )


def _track(document, tag: str = "MidiTrack", position: int = 0) -> ET.Element:
    return [track for track in document.live_set.find("Tracks") if track.tag == tag][position]


def _envelopes(owner: ET.Element) -> list[ET.Element]:
    return list(owner.find("AutomationEnvelopes/Envelopes"))


def _target_id(owner: ET.Element, path: str) -> str:
    return owner.find(f"{path}/AutomationTarget").get("Id")


def _events(envelope: ET.Element) -> list[tuple[str, str, str]]:
    return [
        (event.tag, event.get("Time"), event.get("Value"))
        for event in envelope.find("Automation/Events")
    ]


def test_writes_track_volume_envelope_with_default_event(live_set_factory) -> None:
    document = load_live_set(live_set_factory(_spec()))

    summary = write_automation(document, AutomationScope("track", index=0), "mixer.volume", POINTS)

    track = _track(document)
    [envelope] = _envelopes(track)
    assert envelope.get("Id") == "0"
    assert envelope.find("EnvelopeTarget/PointeeId").get("Value") == _target_id(
        track, "DeviceChain/Mixer/Volume"
    )
    assert _events(envelope) == [
        ("FloatEvent", DEFAULT_EVENT_TIME, "0.5"),
        ("FloatEvent", "0", "0.5"),
        ("FloatEvent", "16", "1"),
    ]
    assert [event.get("Id") for event in envelope.find("Automation/Events")] == ["0", "1", "2"]
    assert summary["scope"] == {"kind": "track", "index": 0, "name": "Keys"}
    assert summary["target"] == "mixer.volume"
    assert summary["parameter"] == "Volume"
    assert summary["point_count"] == 2
    assert summary["replaced_point_count"] == 0
    assert check_integrity(document) == []


def test_replaces_existing_lane_and_keeps_other_envelopes(live_set_factory) -> None:
    document = load_live_set(live_set_factory(_spec()))
    scope = AutomationScope("track", index=0)
    write_automation(document, scope, "mixer.pan", [{"time": 0.0, "value": -1.0}])
    write_automation(document, scope, "mixer.volume", POINTS)

    summary = write_automation(document, scope, "mixer.pan", [{"time": 4.0, "value": 0.25}])

    envelopes = _envelopes(_track(document))
    assert [envelope.get("Id") for envelope in envelopes] == ["1", "2"]
    assert _events(envelopes[1]) == [
        ("FloatEvent", DEFAULT_EVENT_TIME, "0.25"),
        ("FloatEvent", "4", "0.25"),
    ]
    assert summary["replaced_point_count"] == 1


@pytest.mark.parametrize(
    ("scope", "target", "value", "path", "owner"),
    [
        (
            AutomationScope("track", name="Keys"),
            "send.1",
            0.75,
            "DeviceChain/Mixer/Sends/TrackSendHolder[2]/Send",
            "track",
        ),
        (
            AutomationScope("track", index=0),
            "device.0.Cutoff",
            64.5,
            "DeviceChain/DeviceChain/Devices/AutoFilter2/Cutoff",
            "track",
        ),
        (
            AutomationScope("return", index=1),
            "mixer.volume",
            0.75,
            "DeviceChain/Mixer/Volume",
            "return",
        ),
        (AutomationScope("main"), "mixer.tempo", 120.0, "DeviceChain/Mixer/Tempo", "main"),
    ],
)
def test_resolves_each_target_family(live_set_factory, scope, target, value, path, owner) -> None:
    document = load_live_set(live_set_factory(_spec()))
    points = [{"time": 0.0, "value": value}]

    write_automation(document, scope, target, points)

    element = {
        "track": lambda: _track(document),
        "return": lambda: _track(document, "ReturnTrack", 1),
        "main": lambda: document.live_set.find("MainTrack"),
    }[owner]()
    [envelope] = _envelopes(element)
    assert envelope.find("EnvelopeTarget/PointeeId").get("Value") == _target_id(element, path)


@pytest.mark.parametrize(
    ("scope", "target", "points", "message"),
    [
        (AutomationScope("track", index=5), "mixer.volume", POINTS, "track index out of range"),
        (AutomationScope("track", name="Nope"), "mixer.volume", POINTS, "no track named"),
        (
            AutomationScope("return", index=2),
            "mixer.volume",
            POINTS,
            "return track index out of range",
        ),
        (AutomationScope("track", index=0), "mixer.tempo", POINTS, "only on the main track"),
        (AutomationScope("track", index=0), "send.2", POINTS, "send index out of range"),
        (AutomationScope("track", index=0), "mixer.width", POINTS, "unknown target"),
        (AutomationScope("track", index=0), "device.3.Cutoff", POINTS, "device index out of range"),
        (AutomationScope("track", index=0), "device.0.Missing", POINTS, "no automatable parameter"),
        (AutomationScope("track", index=0), "device.0.On", POINTS, "on/off"),
        (AutomationScope("track", index=0), "device.0.FilterType", POINTS, "choice parameter"),
        (AutomationScope("track", index=0), "device.0.Unranged", POINTS, "no value range"),
        (
            AutomationScope("track", index=0),
            "mixer.volume",
            [{"time": 0.0, "value": 3.0}],
            "out of range",
        ),
        (AutomationScope("main"), "mixer.tempo", [{"time": 0.0, "value": 1000.0}], "out of range"),
        (
            AutomationScope("track", index=0),
            "mixer.volume",
            [{"time": -1.0, "value": 0.5}],
            "time must be >= 0",
        ),
        (
            AutomationScope("track", index=0),
            "mixer.volume",
            [{"time": 4.0, "value": 0.5}, {"time": 4.0, "value": 0.6}],
            "strictly increasing",
        ),
    ],
)
def test_rejects_invalid_requests(live_set_factory, scope, target, points, message) -> None:
    document = load_live_set(live_set_factory(_spec()))

    with pytest.raises(AppError) as raised:
        write_automation(document, scope, target, points)

    assert raised.value.error_code.value == "INVALID_ARGUMENT"
    assert message in raised.value.message
    assert raised.value.hint
    assert _envelopes(_track(document)) == []


def test_unknown_device_parameter_lists_available_tags(live_set_factory) -> None:
    document = load_live_set(live_set_factory(_spec()))

    with pytest.raises(AppError) as raised:
        write_automation(document, AutomationScope("track", index=0), "device.0.Missing", POINTS)

    assert raised.value.details["available_parameters"] == ["Cutoff", "Resonance"]


def test_missing_envelope_container_is_schema_error(live_set_factory) -> None:
    def _strip(root: ET.Element) -> None:
        track = root.find("LiveSet/Tracks/MidiTrack")
        track.remove(track.find("AutomationEnvelopes"))

    document = load_live_set(live_set_factory(_spec(), mutate=_strip))

    with pytest.raises(AppError) as raised:
        write_automation(document, AutomationScope("track", index=0), "mixer.volume", POINTS)

    assert raised.value.error_code.value == "SET_SCHEMA_UNSUPPORTED"
