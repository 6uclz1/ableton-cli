from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from live_set_builder import DeviceSpec, SetSpec, TrackSpec

from ableton_cli.liveset.document import load_live_set
from ableton_cli.liveset.ids import global_id_elements, pointee_references
from ableton_cli.liveset.integrity import check_integrity


def _first(root: ET.Element, tag: str) -> ET.Element:
    return next(root.iter(tag))


def _add_reference(root: ET.Element, value: str) -> None:
    target = ET.SubElement(root.find("LiveSet"), "AutomationEnvelope")
    ET.SubElement(ET.SubElement(target, "EnvelopeTarget"), "PointeeId", Value=value)


@pytest.mark.parametrize(
    "tag",
    [
        "AutomationTarget",
        "ModulationTarget",
        "VolumeModulationTarget",
        "Pointee",
        "ControllerTargets.0",
        "ControllerTargets.12",
    ],
)
def test_global_id_elements_cover_every_pointee_family(tag: str) -> None:
    root = ET.Element("Ableton")
    ET.SubElement(root, tag, Id="5")
    ET.SubElement(root, "FloatEvent", Id="5")
    ET.SubElement(root, "KeyTrack", Id="5")

    assert [element.tag for element in global_id_elements(root)] == [tag]


def test_pointee_references_reads_pointee_id_values() -> None:
    root = ET.Element("Ableton")
    ET.SubElement(root, "PointeeId", Value="7")
    ET.SubElement(root, "PointeeId", Value="9")

    assert list(pointee_references(root)) == ["7", "9"]


def test_clean_set_has_no_findings(live_set_factory) -> None:
    spec = SetSpec(
        tempo_envelope=[("-63072000", "120")],
        tracks=[TrackSpec(id=1), TrackSpec(tag="AudioTrack", id=2)],
    )

    assert check_integrity(load_live_set(live_set_factory(spec))) == []


def test_duplicate_ids_across_families_are_reported(live_set_factory) -> None:
    def _collide(root: ET.Element) -> None:
        controller = _first(root, "ControllerTargets.0")
        _first(root, "AutomationTarget").set("Id", controller.get("Id"))

    findings = check_integrity(load_live_set(live_set_factory(mutate=_collide)))

    assert [finding.code for finding in findings] == ["pointee_id_duplicate"]
    assert findings[0].severity == "error"
    assert findings[0].details["count"] == 1


def test_non_integer_id_is_reported(live_set_factory) -> None:
    spec = SetSpec(tracks=[TrackSpec(devices=[DeviceSpec(tag="Eq8")])])

    findings = check_integrity(
        load_live_set(
            live_set_factory(spec, mutate=lambda root: _first(root, "Pointee").set("Id", "x"))
        )
    )

    assert [finding.code for finding in findings] == ["pointee_id_invalid"]
    assert findings[0].details["ids"] == ["x"]


def test_dangling_reference_is_reported(live_set_factory) -> None:
    findings = check_integrity(
        load_live_set(live_set_factory(mutate=lambda root: _add_reference(root, "99999")))
    )

    assert [finding.code for finding in findings] == ["pointee_ref_dangling"]
    assert findings[0].details == {"count": 1, "ids": ["99999"]}


def test_next_pointee_id_must_exceed_every_id(live_set_factory) -> None:
    findings = check_integrity(load_live_set(live_set_factory(SetSpec(next_pointee_id=101))))

    assert [finding.code for finding in findings] == ["next_pointee_id_too_low"]
    assert findings[0].details["next_pointee_id"] == 101
    assert findings[0].details["max_id"] > 101


def test_missing_next_pointee_id_is_reported(live_set_factory) -> None:
    def _drop(root: ET.Element) -> None:
        live_set = root.find("LiveSet")
        live_set.remove(live_set.find("NextPointeeId"))

    findings = check_integrity(load_live_set(live_set_factory(mutate=_drop)))

    assert [finding.code for finding in findings] == ["next_pointee_id_missing"]


def test_findings_are_aggregated_and_capped(live_set_factory) -> None:
    def _many_dangling(root: ET.Element) -> None:
        for value in range(50000, 50030):
            _add_reference(root, str(value))

    findings = check_integrity(load_live_set(live_set_factory(mutate=_many_dangling)))

    assert len(findings) == 1
    assert findings[0].details["count"] == 30
    assert findings[0].details["ids"] == [str(value) for value in range(50000, 50020)]
