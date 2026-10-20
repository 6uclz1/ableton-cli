from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from live_set_builder import DEFAULT_EVENT_TIME, DeviceSpec, SetSpec, TrackSpec

from ableton_cli.errors import AppError, ErrorCode
from ableton_cli.liveset.document import load_live_set
from ableton_cli.liveset.inspect import inspect_live_set


def _inspect(live_set_factory, spec: SetSpec | None = None, **kwargs) -> dict:
    return inspect_live_set(load_live_set(live_set_factory(spec, **kwargs)))


def test_inspect_reports_path_and_version(live_set_factory) -> None:
    summary = _inspect(live_set_factory)

    assert summary["path"].endswith("Test.als")
    assert summary["version"] == {
        "major": "5",
        "minor": "12.0_12402",
        "creator": "Ableton Live 12.4.6",
    }


def test_inspect_reads_manual_tempo_without_envelope(live_set_factory) -> None:
    song = _inspect(live_set_factory, SetSpec(tempo=96.5))["song"]

    assert song["tempo"] == 96.5
    assert song["tempo_automated"] is False


def test_inspect_tempo_follows_default_envelope_event_over_manual(live_set_factory) -> None:
    # Live plays the envelope's default event, not Tempo/Manual, when both exist.
    spec = SetSpec(tempo=128, tempo_envelope=[(DEFAULT_EVENT_TIME, "74")])

    song = _inspect(live_set_factory, spec)["song"]

    assert song["tempo"] == 74.0
    assert song["tempo_automated"] is False


def test_inspect_flags_tempo_automation(live_set_factory) -> None:
    spec = SetSpec(tempo_envelope=[(DEFAULT_EVENT_TIME, "120"), ("16", "140")])

    song = _inspect(live_set_factory, spec)["song"]

    assert song["tempo"] == 120.0
    assert song["tempo_automated"] is True


@pytest.mark.parametrize(
    ("encoded", "numerator", "denominator"),
    [(201, 4, 4), (200, 3, 4), (402, 7, 16), (104, 6, 2), (0, 1, 1)],
)
def test_inspect_decodes_time_signature(
    live_set_factory, encoded: int, numerator: int, denominator: int
) -> None:
    song = _inspect(live_set_factory, SetSpec(time_signature=encoded))["song"]

    assert song["time_signature"] == {"numerator": numerator, "denominator": denominator}


def test_inspect_reads_scale(live_set_factory) -> None:
    song = _inspect(live_set_factory, SetSpec(scale_root=9, scale_name=1, in_key=False))["song"]

    assert song["scale"] == {"root_note": 9, "name_index": 1, "in_key": False}


def test_inspect_lists_tracks_with_type_group_devices_and_clips(live_set_factory) -> None:
    spec = SetSpec(
        tracks=[
            TrackSpec(tag="GroupTrack", id=4, name="Rhythm", color=3),
            TrackSpec(
                tag="MidiTrack",
                id=10,
                name="Drums",
                color=5,
                group_id=4,
                devices=[DeviceSpec(tag="DrumGroupDevice", user_name="Kit")],
                session_clips=2,
                arrangement_clips=3,
            ),
            TrackSpec(
                tag="AudioTrack",
                id=11,
                name="Vox",
                devices=[DeviceSpec(tag="PluginDevice", plugin=("Vst3PluginInfo", "Serum 2"))],
                arrangement_clips=1,
            ),
        ]
    )

    tracks = _inspect(live_set_factory, spec)["tracks"]

    assert tracks == [
        {
            "index": 0,
            "id": 4,
            "type": "group",
            "name": "Rhythm",
            "color": 3,
            "group_id": None,
            "devices": [],
            "session_clip_count": 0,
            "arrangement_clip_count": 0,
        },
        {
            "index": 1,
            "id": 10,
            "type": "midi",
            "name": "Drums",
            "color": 5,
            "group_id": 4,
            "devices": [{"class": "DrumGroupDevice", "name": "Kit"}],
            "session_clip_count": 2,
            "arrangement_clip_count": 3,
        },
        {
            "index": 2,
            "id": 11,
            "type": "audio",
            "name": "Vox",
            "color": 0,
            "group_id": None,
            "devices": [{"class": "PluginDevice", "name": "Serum 2"}],
            "session_clip_count": 0,
            "arrangement_clip_count": 1,
        },
    ]


def test_inspect_device_without_user_or_plugin_name_has_null_name(live_set_factory) -> None:
    spec = SetSpec(tracks=[TrackSpec(devices=[DeviceSpec(tag="Eq8")])])

    devices = _inspect(live_set_factory, spec)["tracks"][0]["devices"]

    assert devices == [{"class": "Eq8", "name": None}]


def test_inspect_separates_return_tracks(live_set_factory) -> None:
    spec = SetSpec(
        tracks=[
            TrackSpec(id=1, name="Lead"),
            TrackSpec(tag="ReturnTrack", id=2, name="A-Reverb", devices=[DeviceSpec(tag="Reverb")]),
        ]
    )

    summary = _inspect(live_set_factory, spec)

    assert [track["name"] for track in summary["tracks"]] == ["Lead"]
    assert summary["return_tracks"] == [
        {
            "index": 0,
            "id": 2,
            "name": "A-Reverb",
            "color": 0,
            "devices": [{"class": "Reverb", "name": None}],
        }
    ]


def test_inspect_lists_scenes_and_locators(live_set_factory) -> None:
    spec = SetSpec(scenes=["Intro", ""], locators=[(0.0, "Intro"), (32.5, "Drop")])

    summary = _inspect(live_set_factory, spec)

    assert summary["scenes"] == [{"index": 0, "name": "Intro"}, {"index": 1, "name": ""}]
    assert summary["locators"] == [
        {"id": 0, "time": 0.0, "name": "Intro"},
        {"id": 1, "time": 32.5, "name": "Drop"},
    ]


def test_inspect_inventories_plugins_once_per_format_and_name(live_set_factory) -> None:
    serum = DeviceSpec(tag="PluginDevice", plugin=("Vst3PluginInfo", "Serum 2"))
    spec = SetSpec(
        tracks=[
            TrackSpec(id=1, devices=[serum]),
            TrackSpec(
                id=2,
                devices=[serum, DeviceSpec(tag="PluginDevice", plugin=("VstPluginInfo", "Old"))],
            ),
        ]
    )

    plugins = _inspect(live_set_factory, spec)["plugins"]

    assert plugins == [
        {"format": "Vst3PluginInfo", "name": "Serum 2", "count": 2},
        {"format": "VstPluginInfo", "name": "Old", "count": 1},
    ]


def test_inspect_rejects_unknown_track_type(live_set_factory) -> None:
    def _rename(root: ET.Element) -> None:
        root.find("LiveSet/Tracks")[0].tag = "HologramTrack"

    with pytest.raises(AppError) as exc:
        _inspect(live_set_factory, mutate=_rename)

    assert exc.value.error_code == ErrorCode.SET_SCHEMA_UNSUPPORTED
    assert exc.value.details["element"] == "HologramTrack"


def test_inspect_rejects_missing_required_element(live_set_factory) -> None:
    def _drop_tempo(root: ET.Element) -> None:
        mixer = root.find("LiveSet/MainTrack/DeviceChain/Mixer")
        mixer.remove(mixer.find("Tempo"))

    with pytest.raises(AppError) as exc:
        _inspect(live_set_factory, mutate=_drop_tempo)

    assert exc.value.error_code == ErrorCode.SET_SCHEMA_UNSUPPORTED
    assert exc.value.details["element"] == "MainTrack/DeviceChain/Mixer/Tempo"


def test_inspect_track_name_prefers_user_name_like_live(live_set_factory) -> None:
    # Live shows UserName when set; EffectiveName is the auto name it falls back to.
    def _rename(root: ET.Element) -> None:
        tracks = root.find("LiveSet/Tracks")
        tracks[0].find("Name/UserName").set("Value", "Renamed")
        tracks[1].find("Name/UserName").set("Value", "")

    spec = SetSpec(tracks=[TrackSpec(id=1, name="Auto A"), TrackSpec(id=2, name="Auto B")])

    tracks = _inspect(live_set_factory, spec, mutate=_rename)["tracks"]

    assert [track["name"] for track in tracks] == ["Renamed", "Auto B"]
