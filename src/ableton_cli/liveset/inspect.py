from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any

from .document import LiveSetDocument
from .model import (
    envelope_events_by_target,
    parse_number,
    require,
    require_value,
    schema_unsupported,
)

TRACK_TYPES = {"MidiTrack": "midi", "AudioTrack": "audio", "GroupTrack": "group"}
RETURN_TRACK_TAG = "ReturnTrack"
MIXER = "MainTrack/DeviceChain/Mixer"

#: Time signatures are stored as ``(numerator - 1) + 99 * log2(denominator)``.
_TIME_SIGNATURE_BASE = 99


def _parameter(
    document: LiveSetDocument, path: str, envelopes: dict[str, list[ET.Element]]
) -> tuple[str, bool]:
    """Return a parameter's effective value and whether it is automated.

    An arrangement envelope's default event (negative time) overrides ``Manual``:
    Live plays the envelope value, so reporting ``Manual`` alone would be wrong.
    """
    parameter = require(document, document.live_set, path, where="")
    manual = require_value(document, parameter, "Manual", where=path)
    target = require(document, parameter, "AutomationTarget", where=path).get("Id", "")
    events = envelopes.get(target, [])
    defaults = [event for event in events if float(event.get("Time", "0")) < 0]
    value = defaults[0].get("Value", manual) if defaults else manual
    return value, len(events) > len(defaults)


def _song(document: LiveSetDocument) -> dict[str, Any]:
    envelopes = envelope_events_by_target(document.root)
    tempo, tempo_automated = _parameter(document, f"{MIXER}/Tempo", envelopes)
    signature, _ = _parameter(document, f"{MIXER}/TimeSignature", envelopes)
    encoded = parse_number(document, signature, element=f"{MIXER}/TimeSignature", kind=int)
    live_set = document.live_set
    return {
        "tempo": parse_number(document, tempo, element=f"{MIXER}/Tempo", kind=float),
        "tempo_automated": tempo_automated,
        "time_signature": {
            "numerator": encoded % _TIME_SIGNATURE_BASE + 1,
            "denominator": 2 ** (encoded // _TIME_SIGNATURE_BASE),
        },
        "scale": {
            "root_note": int(require_value(document, live_set, "ScaleInformation/Root", where="")),
            "name_index": int(require_value(document, live_set, "ScaleInformation/Name", where="")),
            "in_key": require_value(document, live_set, "InKey", where="") == "true",
        },
    }


def _plugin_name(info: ET.Element) -> str | None:
    for tag in ("PlugName", "Name"):
        element = info.find(tag)
        if element is not None and element.get("Value"):
            return element.get("Value")
    return None


def _device(device: ET.Element) -> dict[str, Any]:
    user_name = device.find("UserName")
    name = user_name.get("Value") if user_name is not None else None
    if not name:
        info = device.find("PluginDesc/*")
        name = _plugin_name(info) if info is not None else None
    return {"class": device.tag, "name": name}


def _track_base(document: LiveSetDocument, track: ET.Element) -> dict[str, Any]:
    where = track.tag
    devices = track.findall("DeviceChain/DeviceChain/Devices/*")
    return {
        "id": parse_number(document, track.get("Id", ""), element=f"{where}@Id", kind=int),
        # Live displays UserName when set, else the auto-generated EffectiveName.
        "name": require_value(document, track, "Name/UserName", where=where)
        or require_value(document, track, "Name/EffectiveName", where=where),
        "color": int(require_value(document, track, "Color", where=where)),
        "devices": [_device(device) for device in devices],
    }


def _track(document: LiveSetDocument, index: int, track: ET.Element) -> dict[str, Any]:
    base = _track_base(document, track)
    group_id = int(require_value(document, track, "TrackGroupId", where=track.tag))
    sequencer = "DeviceChain/MainSequencer"
    arrangement = track.findall(f"{sequencer}/ClipTimeable/ArrangerAutomation/Events/*")
    arrangement += track.findall(f"{sequencer}/Sample/ArrangerAutomation/Events/*")
    return {
        "index": index,
        "id": base["id"],
        "type": TRACK_TYPES[track.tag],
        "name": base["name"],
        "color": base["color"],
        "group_id": None if group_id < 0 else group_id,
        "devices": base["devices"],
        "session_clip_count": len(
            track.findall(f"{sequencer}/ClipSlotList/ClipSlot/ClipSlot/Value/*")
        ),
        "arrangement_clip_count": len(arrangement),
    }


def _tracks(document: LiveSetDocument) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    elements = list(require(document, document.live_set, "Tracks", where=""))
    for track in elements:
        if track.tag != RETURN_TRACK_TAG and track.tag not in TRACK_TYPES:
            raise schema_unsupported(document, track.tag, f"unknown track type {track.tag}")
    regular = [track for track in elements if track.tag in TRACK_TYPES]
    returns = [track for track in elements if track.tag == RETURN_TRACK_TAG]
    return (
        [_track(document, index, track) for index, track in enumerate(regular)],
        [{"index": index, **_track_base(document, track)} for index, track in enumerate(returns)],
    )


def _locators(document: LiveSetDocument) -> list[dict[str, Any]]:
    locators = []
    for locator in document.live_set.findall("Locators/Locators/Locator"):
        time = require_value(document, locator, "Time", where="Locator")
        locators.append(
            {
                "id": int(locator.get("Id", "0")),
                "time": parse_number(document, time, element="Locator/Time", kind=float),
                "name": require_value(document, locator, "Name", where="Locator"),
            }
        )
    return locators


def _plugins(document: LiveSetDocument) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for info in document.root.findall(".//PluginDesc/*"):
        name = _plugin_name(info)
        if name is None:
            raise schema_unsupported(document, f"PluginDesc/{info.tag}", "plug-in without a name")
        counts[(info.tag, name)] += 1
    return [
        {"format": plugin_format, "name": name, "count": count}
        for (plugin_format, name), count in sorted(counts.items())
    ]


def inspect_live_set(document: LiveSetDocument) -> dict[str, Any]:
    tracks, returns = _tracks(document)
    scenes = require(document, document.live_set, "Scenes", where="")
    return {
        "path": str(document.path),
        "version": document.version.to_payload(),
        "song": _song(document),
        "tracks": tracks,
        "return_tracks": returns,
        "scenes": [
            {"index": index, "name": require_value(document, scene, "Name", where="Scene")}
            for index, scene in enumerate(scenes)
        ],
        "locators": _locators(document),
        "plugins": _plugins(document),
    }
