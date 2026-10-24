from __future__ import annotations

from live_set_builder import SetSpec, TrackSpec

from ableton_cli.liveset.diff import diff_live_sets
from ableton_cli.liveset.document import load_live_set


def _diff(live_set_factory, before: SetSpec, after: SetSpec) -> dict:
    return diff_live_sets(
        load_live_set(live_set_factory(before, name="before.als")),
        load_live_set(live_set_factory(after, name="after.als")),
    )


def test_identical_sets_have_empty_diff(live_set_factory) -> None:
    result = _diff(live_set_factory, SetSpec(), SetSpec())

    assert result["from_path"].endswith("before.als")
    assert result["to_path"].endswith("after.als")
    assert (result["added"], result["removed"], result["changed"]) == ({}, {}, {})


def test_diff_reports_song_changes(live_set_factory) -> None:
    result = _diff(live_set_factory, SetSpec(tempo=120), SetSpec(tempo=128, time_signature=200))

    assert result["changed"]["song"]["tempo"] == {"from": 120.0, "to": 128.0}
    assert result["changed"]["song"]["time_signature"]["numerator"] == {"from": 4, "to": 3}


def test_diff_matches_tracks_by_id(live_set_factory) -> None:
    before = SetSpec(tracks=[TrackSpec(id=1, name="Lead"), TrackSpec(id=2, name="Pad")])
    after = SetSpec(tracks=[TrackSpec(id=3, name="Bass"), TrackSpec(id=1, name="Lead 2")])

    result = _diff(live_set_factory, before, after)

    assert result["changed"]["tracks"]["1"]["name"] == {"from": "Lead", "to": "Lead 2"}
    assert result["changed"]["tracks"]["1"]["index"] == {"from": 0, "to": 1}
    assert result["added"]["tracks"]["3"]["name"] == "Bass"
    assert result["removed"]["tracks"]["2"]["name"] == "Pad"


def test_diff_reports_locator_changes(live_set_factory) -> None:
    before = SetSpec(locators=[(0.0, "Intro")])
    after = SetSpec(locators=[(0.0, "Intro"), (64.0, "Drop")])

    result = _diff(live_set_factory, before, after)

    assert result["added"]["locators"] == {"1": {"id": 1, "time": 64.0, "name": "Drop"}}
    assert "path" not in result["changed"]
