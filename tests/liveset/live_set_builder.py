"""Synthetic Live Set builder for offline ``.als`` tests.

Live's bundled templates and user sets cannot be committed, so tests build the
smallest XML that mirrors the structure observed in Live 12 saved sets: the
element paths the ``liveset`` package reads, the global pointee-ID families
(``AutomationTarget``, ``*ModulationTarget``, ``Pointee``, ``ControllerTargets.N``)
and the default arrangement-envelope event at ``Time="-63072000"``.
"""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path
from typing import Any

DEFAULT_EVENT_TIME = "-63072000"


@dataclass
class SampleSpec:
    relative_path: str
    path: str = ""
    relative_path_type: int = 3


@dataclass
class DeviceSpec:
    tag: str
    user_name: str = ""
    plugin: tuple[str, str] | None = None  # (info tag, name)


@dataclass
class TrackSpec:
    tag: str = "MidiTrack"
    id: int = 10
    name: str = "Track"
    color: int = 0
    group_id: int = -1
    devices: list[DeviceSpec] = field(default_factory=list)
    session_clips: int = 0
    arrangement_clips: int = 0
    samples: list[SampleSpec] = field(default_factory=list)


@dataclass
class SetSpec:
    major_version: str = "5"
    minor_version: str = "12.0_12402"
    creator: str = "Ableton Live 12.4.6"
    tempo: float = 120.0
    tempo_envelope: list[tuple[str, str]] | None = None  # (time, value) events
    time_signature: int = 201
    scale_root: int = 0
    scale_name: int = 0
    in_key: bool = True
    tracks: list[TrackSpec] = field(default_factory=lambda: [TrackSpec()])
    scenes: list[str] = field(default_factory=lambda: [""])
    locators: list[tuple[float, str]] = field(default_factory=list)
    next_pointee_id: int | None = None  # None: one above the highest allocated ID


def _value(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    return ET.SubElement(parent, tag, Value=str(value))


class _Ids:
    def __init__(self) -> None:
        self._next = count(100)
        self.allocated: list[int] = []

    def target(self, parent: ET.Element, tag: str = "AutomationTarget") -> ET.Element:
        element = ET.SubElement(parent, tag, Id=str(next(self._next)))
        self.allocated.append(int(element.get("Id")))
        return element


def _parameter(parent: ET.Element, tag: str, manual: Any, ids: _Ids) -> str:
    element = ET.SubElement(parent, tag)
    _value(element, "Manual", manual)
    return ids.target(element).get("Id")


def _clip(parent: ET.Element, tag: str, index: int) -> None:
    ET.SubElement(parent, tag, Id=str(index), Time=str(index * 4))


def _build_sequencer(track: ET.Element, spec: TrackSpec, ids: _Ids) -> None:
    sequencer = ET.SubElement(track.find("DeviceChain"), "MainSequencer")
    slots = ET.SubElement(sequencer, "ClipSlotList")
    clip_tag = "MidiClip" if spec.tag == "MidiTrack" else "AudioClip"
    for index in range(max(spec.session_clips, 1)):
        slot = ET.SubElement(ET.SubElement(slots, "ClipSlot", Id=str(index)), "ClipSlot")
        value = ET.SubElement(slot, "Value")
        if index < spec.session_clips:
            _clip(value, clip_tag, index)
    lane = "ClipTimeable" if spec.tag == "MidiTrack" else "Sample"
    events = ET.SubElement(
        ET.SubElement(ET.SubElement(sequencer, lane), "ArrangerAutomation"), "Events"
    )
    for index in range(spec.arrangement_clips):
        _clip(events, clip_tag, index)
    if spec.tag == "MidiTrack":
        ids.target(sequencer, "ControllerTargets.0")
        ids.target(sequencer, "ControllerTargets.1")
    for sample in spec.samples:
        file_ref = ET.SubElement(ET.SubElement(sequencer, "SampleRef"), "FileRef")
        _value(file_ref, "RelativePathType", sample.relative_path_type)
        _value(file_ref, "RelativePath", sample.relative_path)
        _value(file_ref, "Path", sample.path)


def _build_devices(chain: ET.Element, devices: list[DeviceSpec], ids: _Ids) -> None:
    container = ET.SubElement(ET.SubElement(chain, "DeviceChain"), "Devices")
    for device in devices:
        element = ET.SubElement(container, device.tag, Id="0")
        _value(element, "UserName", device.user_name)
        ids.target(element, "Pointee")
        _parameter(element, "On", "true", ids)
        ids.target(element.find("On"), "ModulationTarget")
        if device.plugin is not None:
            info_tag, name = device.plugin
            info = ET.SubElement(ET.SubElement(element, "PluginDesc"), info_tag, Id="0")
            _value(info, "PlugName" if info_tag == "VstPluginInfo" else "Name", name)


def _build_track(tracks: ET.Element, spec: TrackSpec, ids: _Ids) -> None:
    track = ET.SubElement(tracks, spec.tag, Id=str(spec.id))
    name = ET.SubElement(track, "Name")
    _value(name, "EffectiveName", spec.name)
    _value(name, "UserName", spec.name)
    _value(track, "Color", spec.color)
    _value(track, "TrackGroupId", spec.group_id)
    chain = ET.SubElement(track, "DeviceChain")
    mixer = ET.SubElement(chain, "Mixer")
    _parameter(mixer, "Volume", "1", ids)
    ids.target(mixer.find("Volume"), "VolumeModulationTarget")
    if spec.tag in {"MidiTrack", "AudioTrack"}:
        _build_sequencer(track, spec, ids)
    _build_devices(chain, spec.devices, ids)


def _build_main_track(live_set: ET.Element, spec: SetSpec, ids: _Ids) -> None:
    main = ET.SubElement(live_set, "MainTrack")
    envelopes = ET.SubElement(ET.SubElement(main, "AutomationEnvelopes"), "Envelopes")
    mixer = ET.SubElement(ET.SubElement(main, "DeviceChain"), "Mixer")
    tempo_id = _parameter(mixer, "Tempo", spec.tempo, ids)
    _parameter(mixer, "TimeSignature", spec.time_signature, ids)
    if spec.tempo_envelope is not None:
        envelope = ET.SubElement(envelopes, "AutomationEnvelope", Id="0")
        _value(ET.SubElement(envelope, "EnvelopeTarget"), "PointeeId", tempo_id)
        events = ET.SubElement(ET.SubElement(envelope, "Automation"), "Events")
        for index, (time, value) in enumerate(spec.tempo_envelope):
            ET.SubElement(events, "FloatEvent", Id=str(index), Time=time, Value=value)


def build_live_set_xml(spec: SetSpec) -> ET.Element:
    ids = _Ids()
    root = ET.Element(
        "Ableton",
        MajorVersion=spec.major_version,
        MinorVersion=spec.minor_version,
        SchemaChangeCount="5",
        Creator=spec.creator,
        Revision="0",
    )
    live_set = ET.SubElement(root, "LiveSet")
    next_pointee = _value(live_set, "NextPointeeId", 0)
    tracks = ET.SubElement(live_set, "Tracks")
    for track in spec.tracks:
        _build_track(tracks, track, ids)
    _build_main_track(live_set, spec, ids)
    scenes = ET.SubElement(live_set, "Scenes")
    for index, scene_name in enumerate(spec.scenes):
        _value(ET.SubElement(scenes, "Scene", Id=str(index)), "Name", scene_name)
    scale = ET.SubElement(live_set, "ScaleInformation")
    _value(scale, "Root", spec.scale_root)
    _value(scale, "Name", spec.scale_name)
    _value(live_set, "InKey", str(spec.in_key).lower())
    locators = ET.SubElement(ET.SubElement(live_set, "Locators"), "Locators")
    for index, (time, locator_name) in enumerate(spec.locators):
        locator = ET.SubElement(locators, "Locator", Id=str(index))
        _value(locator, "Time", time)
        _value(locator, "Name", locator_name)
    next_value = spec.next_pointee_id
    if next_value is None:
        next_value = max(ids.allocated) + 1
    next_pointee.set("Value", str(next_value))
    return root


def write_live_set(path: Path, root: ET.Element) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as handle:
        handle.write(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    return path
