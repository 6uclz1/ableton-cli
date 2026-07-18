from __future__ import annotations

from typing import Any

from .base import _invalid_argument, _not_supported_by_live_api


class LiveBackendClipEnvelopesMixin:
    """Session clip automation envelope write commands.

    The remote surface stays primitive: it receives a breakpoint list and
    calls ``clip.create_automation_envelope``/``envelope.insert_step``. Curve
    mathematics (ramps, easing, LFOs) live in the CLI layer
    (``ableton_cli.envelope_shapes``), which is testable without Live.
    """

    def _clip_for_envelope(self, track: int, clip: int) -> Any:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before writing an envelope.",
            )
        return slot.clip

    def _validate_envelope_point_range(
        self,
        points: list[dict[str, float]],
        parameter: Any,
    ) -> None:
        minimum = getattr(parameter, "min", None)
        maximum = getattr(parameter, "max", None)
        if minimum is None or maximum is None:
            return
        offending = [
            index
            for index, point in enumerate(points)
            if point["value"] < minimum or point["value"] > maximum
        ]
        if offending:
            raise _invalid_argument(
                message=(
                    f"points value out of parameter range [{minimum}, {maximum}] "
                    f"at indices: {offending}"
                ),
                hint="Keep point values within the parameter's min/max before writing.",
                details={"offending_indices": offending},
            )

    def clip_envelope_set(
        self,
        track: int,
        clip: int,
        device: int,
        parameter: int,
        points: list[dict[str, float]],
        mode: str,
    ) -> dict[str, Any]:
        clip_obj = self._clip_for_envelope(track, clip)
        target_param = self._parameter_at(track, device, parameter)
        self._validate_envelope_point_range(points, target_param)

        create_automation_envelope = getattr(clip_obj, "create_automation_envelope", None)
        if not callable(create_automation_envelope):
            raise _not_supported_by_live_api(
                message="Clip automation envelope API is not available in Live API",
                hint="Use a Live version exposing clip.create_automation_envelope (Live 12+).",
            )

        if mode == "replace":
            clear_envelope = getattr(clip_obj, "clear_envelope", None)
            if callable(clear_envelope):
                clear_envelope(target_param)

        envelope = create_automation_envelope(target_param)
        if envelope is None:
            raise _not_supported_by_live_api(
                message="Live did not return an automation envelope for this parameter",
                hint="Confirm the parameter is automatable and the clip is a session clip.",
            )

        insert_step = envelope.insert_step
        for index, point in enumerate(points):
            start = point["time"]
            end = points[index + 1]["time"] if index + 1 < len(points) else start
            length = max(end - start, 0.0)
            insert_step(start, length, point["value"])

        return {
            "track": track,
            "clip": clip,
            "device": device,
            "parameter": parameter,
            "mode": mode,
            "point_count": len(points),
        }

    def clip_envelope_clear(
        self,
        track: int,
        clip: int,
        device: int | None,
        parameter: int | None,
        clear_all: bool,
    ) -> dict[str, Any]:
        clip_obj = self._clip_for_envelope(track, clip)

        if clear_all:
            clear_all_envelopes = getattr(clip_obj, "clear_all_envelopes", None)
            if not callable(clear_all_envelopes):
                raise _not_supported_by_live_api(
                    message="Clip clear_all_envelopes API is not available in Live API",
                    hint="Use a Live version exposing clip.clear_all_envelopes (Live 12+).",
                )
            clear_all_envelopes()
            return {"track": track, "clip": clip, "cleared_all": True}

        assert device is not None and parameter is not None
        target_param = self._parameter_at(track, device, parameter)
        clear_envelope = getattr(clip_obj, "clear_envelope", None)
        if not callable(clear_envelope):
            raise _not_supported_by_live_api(
                message="Clip clear_envelope API is not available in Live API",
                hint="Use a Live version exposing clip.clear_envelope (Live 12+).",
            )
        clear_envelope(target_param)
        return {
            "track": track,
            "clip": clip,
            "device": device,
            "parameter": parameter,
            "cleared_all": False,
        }
