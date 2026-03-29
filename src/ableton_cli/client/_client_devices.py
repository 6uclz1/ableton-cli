from __future__ import annotations

from typing import Any

from ..refs import RefPayload


class _AbletonClientDevicesMixin:
    def set_device_parameter(
        self,
        track_ref: RefPayload,
        device_ref: RefPayload,
        parameter_ref: RefPayload,
        value: float,
    ) -> dict[str, Any]:
        return self._call_parameter_command(
            "set_device_parameter",
            track_ref=track_ref,
            device_ref=device_ref,
            parameter_ref=parameter_ref,
            value=value,
        )

    def find_synth_devices(
        self,
        track: int | None = None,
        synth_type: str | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {}
        self._add_if_not_none(args, "track", track)
        self._add_if_not_none(args, "synth_type", synth_type)
        return self._call("find_synth_devices", args)

    def list_synth_parameters(
        self, track_ref: RefPayload, device_ref: RefPayload
    ) -> dict[str, Any]:
        return self._call(
            "list_synth_parameters", {"track_ref": track_ref, "device_ref": device_ref}
        )

    def set_synth_parameter_safe(
        self,
        track_ref: RefPayload,
        device_ref: RefPayload,
        parameter_ref: RefPayload,
        value: float,
    ) -> dict[str, Any]:
        return self._call_parameter_command(
            "set_synth_parameter_safe",
            track_ref=track_ref,
            device_ref=device_ref,
            parameter_ref=parameter_ref,
            value=value,
        )

    def observe_synth_parameters(
        self, track_ref: RefPayload, device_ref: RefPayload
    ) -> dict[str, Any]:
        return self._call(
            "observe_synth_parameters", {"track_ref": track_ref, "device_ref": device_ref}
        )

    def list_standard_synth_keys(self, synth_type: str) -> dict[str, Any]:
        return self._call("list_standard_synth_keys", {"synth_type": synth_type})

    def set_standard_synth_parameter_safe(
        self,
        synth_type: str,
        track_ref: RefPayload,
        device_ref: RefPayload,
        key: str,
        value: float,
        parameter_ref: RefPayload | None = None,
    ) -> dict[str, Any]:
        return self._call(
            "set_standard_synth_parameter_safe",
            {
                "synth_type": synth_type,
                "track_ref": track_ref,
                "device_ref": device_ref,
                "parameter_ref": (
                    {"mode": "key", "key": key} if parameter_ref is None else parameter_ref
                ),
                "key": key,
                "value": value,
            },
        )

    def observe_standard_synth_state(
        self,
        synth_type: str,
        track_ref: RefPayload,
        device_ref: RefPayload,
    ) -> dict[str, Any]:
        return self._call(
            "observe_standard_synth_state",
            {"synth_type": synth_type, "track_ref": track_ref, "device_ref": device_ref},
        )

    def find_effect_devices(
        self,
        track: int | None = None,
        effect_type: str | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {}
        self._add_if_not_none(args, "track", track)
        self._add_if_not_none(args, "effect_type", effect_type)
        return self._call("find_effect_devices", args)

    def list_effect_parameters(
        self, track_ref: RefPayload, device_ref: RefPayload
    ) -> dict[str, Any]:
        return self._call(
            "list_effect_parameters", {"track_ref": track_ref, "device_ref": device_ref}
        )

    def set_effect_parameter_safe(
        self,
        track_ref: RefPayload,
        device_ref: RefPayload,
        parameter_ref: RefPayload,
        value: float,
    ) -> dict[str, Any]:
        return self._call_parameter_command(
            "set_effect_parameter_safe",
            track_ref=track_ref,
            device_ref=device_ref,
            parameter_ref=parameter_ref,
            value=value,
        )

    def observe_effect_parameters(
        self, track_ref: RefPayload, device_ref: RefPayload
    ) -> dict[str, Any]:
        return self._call(
            "observe_effect_parameters", {"track_ref": track_ref, "device_ref": device_ref}
        )

    def list_standard_effect_keys(self, effect_type: str) -> dict[str, Any]:
        return self._call("list_standard_effect_keys", {"effect_type": effect_type})

    def set_standard_effect_parameter_safe(
        self,
        effect_type: str,
        track_ref: RefPayload,
        device_ref: RefPayload,
        key: str,
        value: float,
        parameter_ref: RefPayload | None = None,
    ) -> dict[str, Any]:
        return self._call(
            "set_standard_effect_parameter_safe",
            {
                "effect_type": effect_type,
                "track_ref": track_ref,
                "device_ref": device_ref,
                "parameter_ref": (
                    {"mode": "key", "key": key} if parameter_ref is None else parameter_ref
                ),
                "key": key,
                "value": value,
            },
        )

    def observe_standard_effect_state(
        self,
        effect_type: str,
        track_ref: RefPayload,
        device_ref: RefPayload,
    ) -> dict[str, Any]:
        return self._call(
            "observe_standard_effect_state",
            {"effect_type": effect_type, "track_ref": track_ref, "device_ref": device_ref},
        )
