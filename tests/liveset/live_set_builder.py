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
class ParameterSpec:
    tag: str
    manual: str
    value_range: tuple[str, str] | None = None  # MidiControllerRange (min, max)
    modulatable: bool = True  # continuous parameters carry a ModulationTarget


@dataclass
class DeviceSpec:
    tag: str
    user_name: str = ""
    plugin: tuple[str, str] | None = None  # (info tag, name)
    parameters: list[ParameterSpec] = field(default_factory=list)


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
    main_devices: list[DeviceSpec] = field(default_factory=list)


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


VOLUME_RANGE = ("0.0003162277571", "1.99526238")
PAN_RANGE = ("-1", "1")
SEND_RANGE = ("0.0003162277571", "1")
TEMPO_MIDI_RANGE = ("60", "200")


def _parameter(
    parent: ET.Element,
    tag: str,
    manual: Any,
    ids: _Ids,
    value_range: tuple[str, str] | None = None,
    *,
    modulatable: bool = False,
) -> str:
    element = ET.SubElement(parent, tag)
    _value(element, "Manual", manual)
    if value_range is not None:
        controller_range = ET.SubElement(element, "MidiControllerRange")
        _value(controller_range, "Min", value_range[0])
        _value(controller_range, "Max", value_range[1])
    target_id = ids.target(element).get("Id")
    if modulatable:
        ids.target(element, "ModulationTarget")
    return target_id


def _mixer(chain: ET.Element, ids: _Ids, send_count: int) -> ET.Element:
    mixer = ET.SubElement(chain, "Mixer")
    sends = ET.SubElement(mixer, "Sends")
    for index in range(send_count):
        holder = ET.SubElement(sends, "TrackSendHolder", Id=str(index))
        _parameter(holder, "Send", SEND_RANGE[0], ids, SEND_RANGE, modulatable=True)
    _parameter(mixer, "Pan", "0", ids, PAN_RANGE, modulatable=True)
    _parameter(mixer, "Volume", "1", ids, VOLUME_RANGE)
    ids.target(mixer.find("Volume"), "VolumeModulationTarget")
    return mixer


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
        for parameter in device.parameters:
            _parameter(
                element,
                parameter.tag,
                parameter.manual,
                ids,
                parameter.value_range,
                modulatable=parameter.modulatable,
            )
        if device.plugin is not None:
            info_tag, name = device.plugin
            info = ET.SubElement(ET.SubElement(element, "PluginDesc"), info_tag, Id="0")
            _value(info, "PlugName" if info_tag == "VstPluginInfo" else "Name", name)


def _build_track(tracks: ET.Element, spec: TrackSpec, ids: _Ids, send_count: int) -> None:
    track = ET.SubElement(tracks, spec.tag, Id=str(spec.id))
    name = ET.SubElement(track, "Name")
    _value(name, "EffectiveName", spec.name)
    _value(name, "UserName", spec.name)
    _value(track, "Color", spec.color)
    ET.SubElement(ET.SubElement(track, "AutomationEnvelopes"), "Envelopes")
    _value(track, "TrackGroupId", spec.group_id)
    chain = ET.SubElement(track, "DeviceChain")
    _mixer(chain, ids, send_count)
    if spec.tag in {"MidiTrack", "AudioTrack"}:
        _build_sequencer(track, spec, ids)
    _build_devices(chain, spec.devices, ids)


def _build_main_track(live_set: ET.Element, spec: SetSpec, ids: _Ids) -> None:
    main = ET.SubElement(live_set, "MainTrack")
    envelopes = ET.SubElement(ET.SubElement(main, "AutomationEnvelopes"), "Envelopes")
    chain = ET.SubElement(main, "DeviceChain")
    mixer = _mixer(chain, ids, 0)
    tempo_id = _parameter(mixer, "Tempo", spec.tempo, ids, TEMPO_MIDI_RANGE)
    _parameter(mixer, "TimeSignature", spec.time_signature, ids)
    if spec.tempo_envelope is not None:
        envelope = ET.SubElement(envelopes, "AutomationEnvelope", Id="0")
        _value(ET.SubElement(envelope, "EnvelopeTarget"), "PointeeId", tempo_id)
        events = ET.SubElement(ET.SubElement(envelope, "Automation"), "Events")
        for index, (time, value) in enumerate(spec.tempo_envelope):
            ET.SubElement(events, "FloatEvent", Id=str(index), Time=time, Value=value)
    _build_devices(chain, spec.main_devices, ids)


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
    send_count = sum(1 for track in spec.tracks if track.tag == "ReturnTrack")
    for track in spec.tracks:
        _build_track(tracks, track, ids, send_count)
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


def read_live_set_xml(path: Path) -> ET.Element:
    with gzip.open(path, "rb") as handle:
        return ET.fromstring(handle.read())


def write_live_set(path: Path, root: ET.Element) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as handle:
        handle.write(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    return path
