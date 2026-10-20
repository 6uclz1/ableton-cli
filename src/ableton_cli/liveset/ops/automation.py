"""Write one arrangement automation lane, replacing any lane for the same parameter.

An arrangement envelope lives in its track's ``AutomationEnvelopes/Envelopes``
and points at the parameter's ``AutomationTarget`` through ``PointeeId``, so no
new global ID is allocated. Its first event sits at ``DEFAULT_EVENT_TIME`` and
carries the value Live uses before the first breakpoint; it overrides the
parameter's ``Manual`` value.

Values are Live's internal parameter values, not the Remote Script's normalized
ones: mixer volume and sends are linear gain (1.0 = 0 dB), frequencies are in Hz.
They are validated against the parameter's ``MidiControllerRange`` (tempo against
Live's fixed 20-999 BPM).
Only continuous parameters are written. In Live-saved sets they are the ones
with a ``*ModulationTarget``; choice parameters (EQ Eight ``Mode``, Compressor
``Model``) have none and on/off parameters carry ``MidiCCOnOffThresholds``.
Both need event types other than ``FloatEvent`` and are rejected.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Literal

from ...errors import AppError, ErrorCode, ExitCode
from ..document import LiveSetDocument
from ..model import parse_number, require, require_value, track_name

DEFAULT_EVENT_TIME = "-63072000"
TEMPO_RANGE = (20.0, 999.0)
REGULAR_TRACK_TAGS = frozenset({"MidiTrack", "AudioTrack", "GroupTrack"})
_MIXER_TARGETS = {"mixer.volume": "Volume", "mixer.pan": "Pan", "mixer.tempo": "Tempo"}
_TARGET_HINT = (
    "Use mixer.volume, mixer.pan, mixer.tempo (main track), send.<index> "
    "or device.<index>.<ParameterTag>."
)


@dataclass(frozen=True, slots=True)
class AutomationScope:
    kind: Literal["track", "return", "main"]
    index: int | None = None
    name: str | None = None


def _invalid(message: str, hint: str, **details: Any) -> AppError:
    return AppError(
        error_code=ErrorCode.INVALID_ARGUMENT,
        message=message,
        hint=hint,
        exit_code=ExitCode.INVALID_ARGUMENT,
        details=details or None,
    )


def _pick(
    document: LiveSetDocument, tracks: list[ET.Element], scope: AutomationScope, label: str
) -> tuple[int, ET.Element]:
    if scope.name is not None:
        named = [track for track in tracks if track_name(document, track) == scope.name]
        if len(named) != 1:
            raise _invalid(
                f"no track named {scope.name!r}"
                if not named
                else f"track name {scope.name!r} is ambiguous",
                "Use a unique name from 'set inspect', or --track-index.",
            )
        return tracks.index(named[0]), named[0]
    assert scope.index is not None
    if not 0 <= scope.index < len(tracks):
        raise _invalid(
            f"{label} index out of range: {scope.index}",
            f"Use a {label} index from 'set inspect' (0..{len(tracks) - 1}).",
        )
    return scope.index, tracks[scope.index]


def _owner(document: LiveSetDocument, scope: AutomationScope) -> tuple[ET.Element, dict[str, Any]]:
    live_set = document.live_set
    if scope.kind == "main":
        return require(document, live_set, "MainTrack", where=""), {
            "kind": "main",
            "index": None,
            "name": None,
        }
    tracks = list(require(document, live_set, "Tracks", where=""))
    if scope.kind == "return":
        candidates, label = (
            [track for track in tracks if track.tag == "ReturnTrack"],
            "return track",
        )
    else:
        candidates, label = [track for track in tracks if track.tag in REGULAR_TRACK_TAGS], "track"
    index, track = _pick(document, candidates, scope, label)
    return track, {"kind": scope.kind, "index": index, "name": track_name(document, track)}


def _is_on_off(parameter: ET.Element) -> bool:
    manual = parameter.find("Manual")
    return parameter.find("MidiCCOnOffThresholds") is not None or (
        manual is not None and manual.get("Value") in {"true", "false"}
    )


def _is_modulatable(parameter: ET.Element) -> bool:
    return any(child.tag.endswith("ModulationTarget") for child in parameter)


def _is_float_parameter(parameter: ET.Element) -> bool:
    return (
        parameter.find("Manual") is not None
        and parameter.find("AutomationTarget") is not None
        and parameter.find("MidiControllerRange") is not None
        and _is_modulatable(parameter)
        and not _is_on_off(parameter)
    )


def _device_parameter_error(device: ET.Element, tag: str) -> AppError:
    parameter = device.find(tag)
    available = [child.tag for child in device if _is_float_parameter(child)]
    hint = "Pick a continuous parameter tag listed in details.available_parameters."
    if parameter is None or parameter.find("AutomationTarget") is None:
        return _invalid(
            f"no automatable parameter {tag!r} on {device.tag}",
            hint,
            available_parameters=available,
        )
    if _is_on_off(parameter):
        return _invalid(f"{tag} is an on/off parameter, which is not supported", hint)
    if parameter.find("MidiControllerRange") is None:
        return _invalid(f"{tag} has no value range in the set", hint)
    return _invalid(f"{tag} is a choice parameter, which is not supported", hint)


def _device_parameter(owner: ET.Element, target: str) -> ET.Element:
    parts = target.split(".", 2)
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2]:
        raise _invalid(f"unknown target {target!r}", _TARGET_HINT)
    devices = owner.findall("DeviceChain/DeviceChain/Devices/*")
    index = int(parts[1])
    if index >= len(devices):
        raise _invalid(
            f"device index out of range: {index}",
            "Use a top-level device index from 'set inspect'.",
        )
    parameter = devices[index].find(parts[2])
    if parameter is None or not _is_float_parameter(parameter):
        raise _device_parameter_error(devices[index], parts[2])
    return parameter


def _send_parameter(owner: ET.Element, target: str) -> ET.Element:
    raw = target.removeprefix("send.")
    if not raw.isdigit():
        raise _invalid(f"unknown target {target!r}", _TARGET_HINT)
    holders = owner.findall("DeviceChain/Mixer/Sends/TrackSendHolder")
    if int(raw) >= len(holders):
        raise _invalid(
            f"send index out of range: {raw}",
            f"Use a return track index from 'set inspect' (0..{len(holders) - 1}).",
        )
    return holders[int(raw)].find("Send")  # type: ignore[return-value]


def _parameter(
    document: LiveSetDocument, owner: ET.Element, scope: AutomationScope, target: str
) -> ET.Element:
    if target in _MIXER_TARGETS:
        if target == "mixer.tempo" and scope.kind != "main":
            raise _invalid("mixer.tempo is available only on the main track", "Pass --main.")
        return require(
            document, owner, f"DeviceChain/Mixer/{_MIXER_TARGETS[target]}", where=owner.tag
        )
    if target.startswith("send."):
        return _send_parameter(owner, target)
    if target.startswith("device."):
        return _device_parameter(owner, target)
    raise _invalid(f"unknown target {target!r}", _TARGET_HINT)


def _value_range(document: LiveSetDocument, parameter: ET.Element) -> tuple[float, float]:
    if parameter.tag == "Tempo":
        return TEMPO_RANGE
    bounds = [
        require_value(document, parameter, f"MidiControllerRange/{bound}", where=parameter.tag)
        for bound in ("Min", "Max")
    ]
    low, high = (
        parse_number(document, raw, element=f"{parameter.tag}/MidiControllerRange", kind=float)
        for raw in bounds
    )
    return low, high


def _validate_points(points: list[dict[str, float]], low: float, high: float) -> None:
    previous: float | None = None
    for index, point in enumerate(points):
        time, value = point["time"], point["value"]
        if time < 0:
            raise _invalid(f"points[{index}] time must be >= 0", "Use beat times from 0.")
        if previous is not None and time <= previous:
            raise _invalid(
                f"point times must be strictly increasing (points[{index}])",
                "Sort the points by time and drop duplicates.",
            )
        if not low <= value <= high:
            raise _invalid(
                f"points[{index}] value {value} out of range [{low}, {high}]",
                "Use Live's internal parameter value within the parameter's range.",
            )
        previous = time


def _format(number: float) -> str:
    return str(int(number)) if float(number).is_integer() else repr(float(number))


def _replace_lane(envelopes: ET.Element, target_id: str) -> int:
    replaced = 0
    for envelope in list(envelopes):
        pointee = envelope.find("EnvelopeTarget/PointeeId")
        if pointee is None or pointee.get("Value") != target_id:
            continue
        events = envelope.findall("Automation/Events/*")
        replaced = sum(float(event.get("Time", "0")) >= 0 for event in events)
        envelopes.remove(envelope)
    return replaced


def _append_lane(envelopes: ET.Element, target_id: str, points: list[dict[str, float]]) -> None:
    next_id = max((int(envelope.get("Id", "0")) for envelope in envelopes), default=-1) + 1
    envelope = ET.SubElement(envelopes, "AutomationEnvelope", Id=str(next_id))
    ET.SubElement(ET.SubElement(envelope, "EnvelopeTarget"), "PointeeId", Value=target_id)
    events = ET.SubElement(ET.SubElement(envelope, "Automation"), "Events")
    timeline = [(DEFAULT_EVENT_TIME, points[0]["value"])] + [
        (_format(point["time"]), point["value"]) for point in points
    ]
    for event_id, (time, value) in enumerate(timeline):
        ET.SubElement(events, "FloatEvent", Id=str(event_id), Time=time, Value=_format(value))


def write_automation(
    document: LiveSetDocument,
    scope: AutomationScope,
    target: str,
    points: list[dict[str, float]],
) -> dict[str, Any]:
    owner, scope_payload = _owner(document, scope)
    parameter = _parameter(document, owner, scope, target)
    _validate_points(points, *_value_range(document, parameter))
    envelopes = require(document, owner, "AutomationEnvelopes/Envelopes", where=owner.tag)
    target_id = require(document, parameter, "AutomationTarget", where=parameter.tag).get("Id", "")
    replaced = _replace_lane(envelopes, target_id)
    _append_lane(envelopes, target_id, points)
    return {
        "scope": scope_payload,
        "target": target,
        "parameter": parameter.tag,
        "point_count": len(points),
        "replaced_point_count": replaced,
    }
