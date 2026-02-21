from __future__ import annotations

from time import perf_counter
from typing import Any
from urllib.parse import unquote

from .command_backend import (
    MAX_BPM,
    MAX_PANNING,
    MAX_VOLUME,
    MIN_BPM,
    MIN_PANNING,
    MIN_VOLUME,
    PROTOCOL_VERSION,
    REMOTE_SCRIPT_VERSION,
    CommandError,
)
from .effect_specs import (
    SUPPORTED_EFFECT_TYPES,
    canonicalize_effect_type,
    detect_effect_type,
    resolve_standard_effect_key_indexes,
    standard_effect_keys,
)
from .synth_specs import (
    SUPPORTED_SYNTH_TYPES,
    canonicalize_synth_type,
    detect_synth_type,
    resolve_standard_synth_key_indexes,
    standard_synth_keys,
)


def _invalid_argument(message: str, hint: str) -> CommandError:
    return CommandError(code="INVALID_ARGUMENT", message=message, hint=hint)


def _not_supported_by_live_api(message: str, hint: str) -> CommandError:
    return CommandError(
        code="INVALID_ARGUMENT",
        message=message,
        hint=hint,
        details={"reason": "not_supported_by_live_api"},
    )


class LiveBackend:
    def __init__(self, control_surface: Any) -> None:
        self._control_surface = control_surface
        self._browser_search_index_cache: dict[str, list[dict[str, Any]]] = {}

    def _song(self) -> Any:
        return self._control_surface.song()

    def _application(self) -> Any:
        app = self._control_surface.application()
        if app is None:
            raise _invalid_argument(
                message="Live application is not available",
                hint="Make sure Ableton Live is running and fully loaded.",
            )
        return app

    def _track_at(self, index: int) -> Any:
        tracks = list(self._song().tracks)
        if index < 0 or index >= len(tracks):
            raise _invalid_argument(
                message=f"track out of range: {index}",
                hint="Use a valid track index from tracks list.",
            )
        return tracks[index]

    def _clip_slot_at(self, track: int, clip: int) -> Any:
        target = self._track_at(track)
        slots = list(target.clip_slots)
        if clip < 0 or clip >= len(slots):
            raise _invalid_argument(
                message=f"clip out of range: {clip}",
                hint="Use a valid clip slot index for the target track.",
            )
        return slots[clip]

    def _scene_at(self, index: int) -> Any:
        scenes = list(getattr(self._song(), "scenes", []))
        if index < 0 or index >= len(scenes):
            raise _invalid_argument(
                message=f"scene out of range: {index}",
                hint="Use a valid scene index from scenes list.",
            )
        return scenes[index]

    def _device_at(self, track: int, device: int) -> Any:
        target = self._track_at(track)
        devices = list(target.devices)
        if device < 0 or device >= len(devices):
            raise _invalid_argument(
                message=f"device out of range: {device}",
                hint="Use a valid device index from track info.",
            )
        return devices[device]

    def _parameter_at(self, track: int, device: int, parameter: int) -> Any:
        target_device = self._device_at(track, device)
        parameters = list(getattr(target_device, "parameters", []))
        if parameter < 0 or parameter >= len(parameters):
            raise _invalid_argument(
                message=f"parameter out of range: {parameter}",
                hint="Use a valid parameter index from track info.",
            )
        return parameters[parameter]

    def _safe_float(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def _serialize_parameter(self, parameter: Any, index: int) -> dict[str, Any]:
        minimum = self._safe_float(getattr(parameter, "min", None))
        maximum = self._safe_float(getattr(parameter, "max", None))
        return {
            "index": index,
            "name": str(getattr(parameter, "name", f"Parameter {index}")),
            "value": float(getattr(parameter, "value", 0.0)),
            "min": minimum,
            "max": maximum,
            "is_enabled": bool(getattr(parameter, "is_enabled", True)),
            "is_quantized": bool(getattr(parameter, "is_quantized", False)),
        }

    def _synth_type_for_device(self, device: Any) -> str | None:
        return detect_synth_type(device)

    def _effect_type_for_device(self, device: Any) -> str | None:
        return detect_effect_type(device)

    def _require_supported_synth_device(self, track: int, device: int) -> tuple[Any, str]:
        target_device = self._device_at(track, device)
        detected_type = self._synth_type_for_device(target_device)
        if detected_type is None:
            raise _invalid_argument(
                message=(
                    "Device is not a supported synth "
                    f"(supported: {', '.join(SUPPORTED_SYNTH_TYPES)})"
                ),
                hint="Choose a Wavetable, Drift, or Meld device.",
            )
        return target_device, detected_type

    def _synth_device_payload(
        self,
        *,
        track: int,
        device_index: int,
        device: Any,
        detected_type: str,
    ) -> dict[str, Any]:
        return {
            "track": track,
            "device": device_index,
            "track_name": str(getattr(self._track_at(track), "name", "")),
            "device_name": str(getattr(device, "name", "")),
            "class_name": str(getattr(device, "class_name", "")),
            "detected_type": detected_type,
        }

    def _effect_device_payload(
        self,
        *,
        track: int,
        device_index: int,
        device: Any,
        detected_type: str,
    ) -> dict[str, Any]:
        return {
            "track": track,
            "device": device_index,
            "track_name": str(getattr(self._track_at(track), "name", "")),
            "device_name": str(getattr(device, "name", "")),
            "class_name": str(getattr(device, "class_name", "")),
            "detected_type": detected_type,
        }

    def _require_supported_effect_device(self, track: int, device: int) -> tuple[Any, str]:
        target_device = self._device_at(track, device)
        detected_type = self._effect_type_for_device(target_device)
        if detected_type is None:
            raise _invalid_argument(
                message=(
                    "Device is not a supported effect "
                    f"(supported: {', '.join(SUPPORTED_EFFECT_TYPES)})"
                ),
                hint="Choose one of the supported audio effects.",
            )
        return target_device, detected_type

    def _list_synth_parameters_payload(self, track: int, device: int) -> dict[str, Any]:
        target_device, detected_type = self._require_supported_synth_device(track, device)
        serialized_parameters = [
            self._serialize_parameter(parameter, index)
            for index, parameter in enumerate(list(getattr(target_device, "parameters", [])))
        ]
        return {
            "track": track,
            "device": device,
            "device_name": str(getattr(target_device, "name", "")),
            "class_name": str(getattr(target_device, "class_name", "")),
            "detected_type": detected_type,
            "parameter_count": len(serialized_parameters),
            "parameters": serialized_parameters,
        }

    def _resolved_standard_synth_key_indexes(
        self,
        *,
        synth_type: str,
        track: int,
        device: int,
    ) -> tuple[dict[str, int], str]:
        parsed_type = canonicalize_synth_type(synth_type)
        target_device, detected_type = self._require_supported_synth_device(track, device)
        if detected_type != parsed_type:
            raise _invalid_argument(
                message=(
                    f"Device synth type mismatch: requested={parsed_type}, "
                    f"detected={detected_type}"
                ),
                hint="Select a device that matches the requested synth type.",
            )

        parameter_names = [
            str(getattr(parameter, "name", ""))
            for parameter in list(getattr(target_device, "parameters", []))
        ]
        key_indexes, missing_keys = resolve_standard_synth_key_indexes(
            parameter_names,
            parsed_type,
        )
        if missing_keys:
            raise _invalid_argument(
                message=(
                    f"Missing required standard synth keys for {parsed_type}: "
                    f"{', '.join(missing_keys)}"
                ),
                hint="Use the exact English standard synth parameter names.",
            )
        return key_indexes, parsed_type

    def _list_effect_parameters_payload(self, track: int, device: int) -> dict[str, Any]:
        target_device, detected_type = self._require_supported_effect_device(track, device)
        serialized_parameters = [
            self._serialize_parameter(parameter, index)
            for index, parameter in enumerate(list(getattr(target_device, "parameters", [])))
        ]
        return {
            "track": track,
            "device": device,
            "device_name": str(getattr(target_device, "name", "")),
            "class_name": str(getattr(target_device, "class_name", "")),
            "detected_type": detected_type,
            "parameter_count": len(serialized_parameters),
            "parameters": serialized_parameters,
        }

    def _resolved_standard_effect_key_indexes(
        self,
        *,
        effect_type: str,
        track: int,
        device: int,
    ) -> tuple[dict[str, int], str]:
        parsed_type = canonicalize_effect_type(effect_type)
        target_device, detected_type = self._require_supported_effect_device(track, device)
        if detected_type != parsed_type:
            raise _invalid_argument(
                message=(
                    f"Device effect type mismatch: requested={parsed_type}, "
                    f"detected={detected_type}"
                ),
                hint="Select a device that matches the requested effect type.",
            )

        parameter_names = [
            str(getattr(parameter, "name", ""))
            for parameter in list(getattr(target_device, "parameters", []))
        ]
        key_indexes, missing_keys = resolve_standard_effect_key_indexes(
            parameter_names,
            parsed_type,
        )
        if missing_keys:
            raise _invalid_argument(
                message=(
                    f"Missing required standard effect keys for {parsed_type}: "
                    f"{', '.join(missing_keys)}"
                ),
                hint="Use the exact English standard effect parameter names.",
            )
        return key_indexes, parsed_type

    def _browser(self) -> Any:
        app = self._application()
        browser = getattr(app, "browser", None)
        if browser is None:
            raise _invalid_argument(
                message="Browser is not available in the Live application",
                hint="Open Ableton Live browser and retry.",
            )
        return browser

    def _coerce_uri(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text

    def _normalize_uri(self, value: str) -> str:
        return unquote(value.strip())

    def _uri_matches(self, candidate: Any, expected: str) -> bool:
        candidate_uri = self._coerce_uri(candidate)
        if candidate_uri is None:
            return False
        if candidate_uri == expected:
            return True
        return self._normalize_uri(candidate_uri) == self._normalize_uri(expected)

    def _preferred_categories_for_uri(
        self, uri: str, available_categories: list[str]
    ) -> list[str]:
        mapping = {
            "query:Synths": "instruments",
            "query:Drums": "drums",
            "query:AudioFx": "audio_effects",
            "query:MidiFx": "midi_effects",
            "query:Sounds": "sounds",
        }
        prefix = self._normalize_uri(uri).split("#", 1)[0]
        preferred = mapping.get(prefix)
        if preferred is None:
            return []
        if preferred not in available_categories:
            return []
        return [preferred]

    def _find_path_in_serialized_tree_by_uri(
        self, tree: dict[str, Any], uri: str
    ) -> str | None:
        stack = [tree]
        while stack:
            node = stack.pop()
            if self._uri_matches(node.get("uri"), uri):
                path = node.get("path")
                if isinstance(path, str) and path:
                    return path
            children = node.get("children")
            if isinstance(children, list):
                stack.extend(children)
        return None

    def _find_browser_path_by_uri_fallback(self, uri: str) -> str | None:
        categories = self._browser_category_map()
        available = sorted(categories.keys())
        preferred = self._preferred_categories_for_uri(uri, available)
        ordered_categories = preferred + [name for name in available if name not in preferred]

        for category_name in ordered_categories:
            category = categories.get(category_name)
            if category is None:
                continue
            tree = self._serialize_browser_tree(category, category_name)
            path = self._find_path_in_serialized_tree_by_uri(tree, uri)
            if path is not None:
                return path
        return None

    def _flatten_serialized_tree(self, root: dict[str, Any]) -> list[dict[str, Any]]:
        stack = [root]
        items: list[dict[str, Any]] = []
        while stack:
            node = stack.pop()
            children = node.get("children")
            if isinstance(children, list):
                stack.extend(children)
            items.append(
                {
                    "name": node.get("name"),
                    "path": node.get("path"),
                    "is_folder": bool(node.get("is_folder")),
                    "is_device": bool(node.get("is_device")),
                    "is_loadable": bool(node.get("is_loadable")),
                    "uri": node.get("uri"),
                }
            )
        return items

    def _item_matches_type(self, item: dict[str, Any], item_type: str) -> bool:
        if item_type == "all":
            return True
        if item_type == "folder":
            return bool(item.get("is_folder"))
        if item_type == "device":
            return bool(item.get("is_device"))
        if item_type == "loadable":
            return bool(item.get("is_loadable"))
        return False

    def _normalized_text(self, value: Any, *, case_sensitive: bool) -> str:
        text = str(value or "")
        return text if case_sensitive else text.lower()

    def _match_rank(
        self,
        item: dict[str, Any],
        query: str,
        *,
        exact: bool,
        case_sensitive: bool,
    ) -> int | None:
        name = self._normalized_text(item.get("name"), case_sensitive=case_sensitive)
        path = self._normalized_text(item.get("path"), case_sensitive=case_sensitive)
        uri = self._normalized_text(item.get("uri"), case_sensitive=case_sensitive)
        target = self._normalized_text(query, case_sensitive=case_sensitive)

        if exact:
            if name == target:
                return 0
            if path == target:
                return 3
            if uri == target:
                return 4
            return None

        if name == target:
            return 0
        if name.startswith(target):
            return 1
        if target in name:
            return 2
        if target in path:
            return 3
        if target in uri:
            return 4
        return None

    def _search_cache_key(self, path: str | None) -> str:
        return "__all__" if path is None else f"path:{path}"

    def _browser_search_candidates(self, path: str | None) -> list[dict[str, Any]]:
        key = self._search_cache_key(path)
        cached = self._browser_search_index_cache.get(key)
        if cached is not None:
            return cached

        if path is None:
            categories = self._browser_category_map()
            roots = [
                self._serialize_browser_tree(categories[name], name)
                for name in sorted(categories.keys())
            ]
        else:
            root = self._resolve_browser_path(path)
            roots = [self._serialize_browser_tree(root, path)]

        indexed: list[dict[str, Any]] = []
        for root in roots:
            indexed.extend(self._flatten_serialized_tree(root))

        self._browser_search_index_cache[key] = indexed
        return indexed

    def _clip_note_matches_filter(
        self,
        note: dict[str, Any],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> bool:
        note_start = float(note["start_time"])
        note_pitch = int(note["pitch"])
        if start_time is not None and note_start < start_time:
            return False
        if end_time is not None and note_start >= end_time:
            return False
        if pitch is not None and note_pitch != pitch:
            return False
        return True

    def _normalize_clip_note(self, note: Any) -> dict[str, Any]:
        return {
            "note_id": int(note.note_id),
            "pitch": int(note.pitch),
            "start_time": float(note.start_time),
            "duration": float(note.duration),
            "velocity": int(note.velocity),
            "mute": bool(note.mute),
        }

    def _clip_notes_extended(self, clip_obj: Any) -> list[dict[str, Any]]:
        time_span = max(float(getattr(clip_obj, "length", 0.0)), 0.0) + 1.0
        notes_raw = tuple(
            clip_obj.get_notes_extended(
                from_pitch=0,
                pitch_span=128,
                from_time=0.0,
                time_span=time_span,
            )
        )
        return [self._normalize_clip_note(note) for note in notes_raw]

    def _filtered_clip_notes(
        self,
        clip_obj: Any,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> list[dict[str, Any]]:
        return [
            note
            for note in self._clip_notes_extended(clip_obj)
            if self._clip_note_matches_filter(note, start_time, end_time, pitch)
        ]

    def _known_browser_categories(self) -> dict[str, Any]:
        browser = self._browser()
        categories: dict[str, Any] = {}
        for name in ("instruments", "sounds", "drums", "audio_effects", "midi_effects"):
            item = getattr(browser, name, None)
            if item is not None:
                categories[name] = item
        return categories

    def _browser_category_map(self) -> dict[str, Any]:
        browser = self._browser()
        categories = self._known_browser_categories()
        for attr in dir(browser):
            if attr.startswith("_") or attr in categories:
                continue
            item = getattr(browser, attr, None)
            if item is None:
                continue
            if hasattr(item, "name") or hasattr(item, "children"):
                categories[attr.lower()] = item
        return categories

    def _serialize_browser_item(self, item: Any, *, path: str | None = None) -> dict[str, Any]:
        children = list(getattr(item, "children", []) or [])
        return {
            "name": str(getattr(item, "name", "Unknown")),
            "path": path,
            "is_folder": bool(children),
            "is_device": bool(getattr(item, "is_device", False)),
            "is_loadable": bool(getattr(item, "is_loadable", False)),
            "uri": self._coerce_uri(getattr(item, "uri", None)),
        }

    def _serialize_browser_tree(self, item: Any, path: str) -> dict[str, Any]:
        payload = self._serialize_browser_item(item, path=path)
        children = []
        for child in list(getattr(item, "children", []) or []):
            child_path = f"{path}/{getattr(child, 'name', '')}".rstrip("/")
            children.append(self._serialize_browser_tree(child, child_path))
        payload["children"] = children
        return payload

    def _resolve_browser_path(self, path: str) -> Any:
        parts = [part for part in path.split("/") if part]
        if not parts:
            raise _invalid_argument(
                message="path must not be empty",
                hint="Use a path like 'drums/Kits'.",
            )
        categories = self._browser_category_map()
        root_key = parts[0].lower()
        root = categories.get(root_key)
        if root is None:
            available = ", ".join(sorted(categories.keys()))
            raise _invalid_argument(
                message=f"Unknown or unavailable category: {parts[0]}",
                hint=f"Available categories: {available}",
            )

        current = root
        for part in parts[1:]:
            children = list(getattr(current, "children", []) or [])
            next_item = None
            for child in children:
                if str(getattr(child, "name", "")).lower() == part.lower():
                    next_item = child
                    break
            if next_item is None:
                raise _invalid_argument(
                    message=f"Path part '{part}' not found",
                    hint="Use browser tree/items commands to inspect available paths.",
                )
            current = next_item
        return current

    def _find_browser_item_by_uri(self, uri: str) -> Any | None:
        categories = self._browser_category_map()
        stack = list(categories.values())
        seen: set[int] = set()
        while stack:
            item = stack.pop()
            ident = id(item)
            if ident in seen:
                continue
            seen.add(ident)
            if self._uri_matches(getattr(item, "uri", None), uri):
                return item
            stack.extend(list(getattr(item, "children", []) or []))
        fallback_path = self._find_browser_path_by_uri_fallback(uri)
        if fallback_path is None:
            return None
        try:
            return self._resolve_browser_path(fallback_path)
        except CommandError:
            return None

    def _item_path_by_uri(self, uri: str) -> str | None:
        categories = self._browser_category_map()
        for category_name, category in categories.items():
            stack: list[tuple[Any, str]] = [(category, category_name)]
            seen: set[int] = set()
            while stack:
                item, path = stack.pop()
                ident = id(item)
                if ident in seen:
                    continue
                seen.add(ident)
                if self._uri_matches(getattr(item, "uri", None), uri):
                    return path
                children = list(getattr(item, "children", []) or [])
                for child in children:
                    child_name = str(getattr(child, "name", "")).strip()
                    child_path = f"{path}/{child_name}" if child_name else path
                    stack.append((child, child_path))
        return self._find_browser_path_by_uri_fallback(uri)

    def ping_info(self) -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "remote_script_version": REMOTE_SCRIPT_VERSION,
        }

    def song_info(self) -> dict[str, Any]:
        song = self._song()
        return {
            "tempo": float(song.tempo),
            "is_playing": bool(song.is_playing),
            "current_time": float(song.current_song_time),
            "beat_position": float(song.current_song_time),
            "signature": {
                "numerator": int(song.signature_numerator),
                "denominator": int(song.signature_denominator),
            },
        }

    def song_new(self) -> dict[str, Any]:
        app = self._application()
        create_set = getattr(app, "new_live_set", None)
        if not callable(create_set):
            raise _not_supported_by_live_api(
                message="Song creation API is not available in Live API",
                hint="Create a new empty Set manually in Ableton Live.",
            )
        create_set()
        return {"created": True}

    def song_save(self, path: str) -> dict[str, Any]:
        app = self._application()
        save_set = getattr(app, "save_live_set", None)
        if not callable(save_set):
            raise _not_supported_by_live_api(
                message="Song save API is not available in Live API",
                hint="Save the Set manually from Ableton Live.",
            )
        save_set(path)
        return {"saved": True, "path": path}

    def song_export_audio(self, path: str) -> dict[str, Any]:
        app = self._application()
        export_audio = getattr(app, "export_audio", None)
        if not callable(export_audio):
            raise _not_supported_by_live_api(
                message="Song audio export API is not available in Live API",
                hint="Export audio manually from Ableton Live.",
            )
        export_audio(path)
        return {"exported": True, "path": path}

    def get_session_info(self) -> dict[str, Any]:
        song = self._song()
        master = song.master_track
        return {
            "tempo": float(song.tempo),
            "signature_numerator": int(song.signature_numerator),
            "signature_denominator": int(song.signature_denominator),
            "track_count": len(song.tracks),
            "return_track_count": len(getattr(song, "return_tracks", [])),
            "master_track": {
                "name": str(getattr(master, "name", "Master")),
                "volume": float(master.mixer_device.volume.value),
                "panning": float(master.mixer_device.panning.value),
            },
        }

    def session_snapshot(self) -> dict[str, Any]:
        return {
            "song_info": self.song_info(),
            "session_info": self.get_session_info(),
            "tracks_list": self.tracks_list(),
            "scenes_list": self.scenes_list(),
        }

    def get_track_info(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        clip_slots = []
        for slot_index, slot in enumerate(list(target.clip_slots)):
            clip_info = None
            if slot.has_clip:
                clip = slot.clip
                clip_info = {
                    "name": str(getattr(clip, "name", "")),
                    "length": float(getattr(clip, "length", 0.0)),
                    "is_playing": bool(getattr(clip, "is_playing", False)),
                    "is_recording": bool(getattr(clip, "is_recording", False)),
                }
            clip_slots.append(
                {
                    "index": slot_index,
                    "has_clip": bool(slot.has_clip),
                    "clip": clip_info,
                }
            )

        devices = []
        for device_index, device in enumerate(list(target.devices)):
            params = []
            for param_index, param in enumerate(list(getattr(device, "parameters", []))):
                params.append(
                    {
                        "index": param_index,
                        "name": str(getattr(param, "name", f"Parameter {param_index}")),
                        "value": float(getattr(param, "value", 0.0)),
                    }
                )
            devices.append(
                {
                    "index": device_index,
                    "name": str(getattr(device, "name", "")),
                    "class_name": str(getattr(device, "class_name", "")),
                    "type": self._get_device_type(device),
                    "parameters": params,
                }
            )

        return {
            "index": track,
            "name": str(target.name),
            "is_audio_track": bool(getattr(target, "has_audio_input", False)),
            "is_midi_track": bool(getattr(target, "has_midi_input", False)),
            "mute": bool(target.mute),
            "solo": bool(target.solo),
            "arm": bool(getattr(target, "arm", False)),
            "volume": float(target.mixer_device.volume.value),
            "panning": float(target.mixer_device.panning.value),
            "clip_slots": clip_slots,
            "devices": devices,
        }

    def tracks_list(self) -> dict[str, Any]:
        tracks = []
        for index, track in enumerate(self._song().tracks):
            tracks.append(
                {
                    "index": index,
                    "name": str(track.name),
                    "mute": bool(track.mute),
                    "solo": bool(track.solo),
                    "arm": bool(getattr(track, "arm", False)),
                    "volume": float(track.mixer_device.volume.value),
                }
            )
        return {"tracks": tracks}

    def create_midi_track(self, index: int) -> dict[str, Any]:
        song = self._song()
        if index != -1 and index > len(song.tracks):
            raise _invalid_argument(
                message=f"index out of range: {index}",
                hint="Use -1 for append or a valid insertion index.",
            )
        song.create_midi_track(index)
        target_index = len(song.tracks) - 1 if index == -1 else index
        track = song.tracks[target_index]
        return {"index": target_index, "name": str(track.name), "kind": "midi"}

    def create_audio_track(self, index: int) -> dict[str, Any]:
        song = self._song()
        if index != -1 and index > len(song.tracks):
            raise _invalid_argument(
                message=f"index out of range: {index}",
                hint="Use -1 for append or a valid insertion index.",
            )
        song.create_audio_track(index)
        target_index = len(song.tracks) - 1 if index == -1 else index
        track = song.tracks[target_index]
        return {"index": target_index, "name": str(track.name), "kind": "audio"}

    def set_track_name(self, track: int, name: str) -> dict[str, Any]:
        target = self._track_at(track)
        target.name = name
        return {"track": track, "name": str(target.name)}

    def transport_play(self) -> dict[str, Any]:
        return self.start_playback()

    def transport_stop(self) -> dict[str, Any]:
        return self.stop_playback()

    def transport_toggle(self) -> dict[str, Any]:
        song = self._song()
        if song.is_playing:
            song.stop_playing()
        else:
            song.start_playing()
        return {"is_playing": bool(song.is_playing)}

    def start_playback(self) -> dict[str, Any]:
        song = self._song()
        song.start_playing()
        return {"is_playing": bool(song.is_playing)}

    def stop_playback(self) -> dict[str, Any]:
        song = self._song()
        song.stop_playing()
        return {"is_playing": bool(song.is_playing)}

    def transport_tempo_get(self) -> dict[str, Any]:
        return {"tempo": float(self._song().tempo)}

    def transport_tempo_set(self, bpm: float) -> dict[str, Any]:
        if bpm < MIN_BPM or bpm > MAX_BPM:
            raise _invalid_argument(
                message=f"bpm must be between {MIN_BPM} and {MAX_BPM}",
                hint="Use a tempo value like 120.",
            )
        song = self._song()
        song.tempo = float(bpm)
        return {"tempo": float(song.tempo)}

    def set_tempo(self, tempo: float) -> dict[str, Any]:
        return self.transport_tempo_set(tempo)

    def track_volume_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        return {"track": track, "volume": float(target.mixer_device.volume.value)}

    def track_volume_set(self, track: int, value: float) -> dict[str, Any]:
        if value < MIN_VOLUME or value > MAX_VOLUME:
            raise _invalid_argument(
                message=f"value must be between {MIN_VOLUME} and {MAX_VOLUME}",
                hint="Use a normalized volume value in [0.0, 1.0].",
            )
        target = self._track_at(track)
        target.mixer_device.volume.value = float(value)
        return {"track": track, "volume": float(target.mixer_device.volume.value)}

    def track_mute_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        return {"track": track, "mute": bool(target.mute)}

    def track_mute_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._track_at(track)
        target.mute = bool(value)
        return {"track": track, "mute": bool(target.mute)}

    def track_solo_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        return {"track": track, "solo": bool(target.solo)}

    def track_solo_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._track_at(track)
        target.solo = bool(value)
        return {"track": track, "solo": bool(target.solo)}

    def track_arm_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        if not hasattr(target, "arm"):
            raise _invalid_argument(
                message="Track does not support arm",
                hint="Use a MIDI or audio track with arm support.",
            )
        return {"track": track, "arm": bool(target.arm)}

    def track_arm_set(self, track: int, value: bool) -> dict[str, Any]:
        target = self._track_at(track)
        if not hasattr(target, "arm"):
            raise _invalid_argument(
                message="Track does not support arm",
                hint="Use a MIDI or audio track with arm support.",
            )
        target.arm = bool(value)
        return {"track": track, "arm": bool(target.arm)}

    def track_panning_get(self, track: int) -> dict[str, Any]:
        target = self._track_at(track)
        return {"track": track, "panning": float(target.mixer_device.panning.value)}

    def track_panning_set(self, track: int, value: float) -> dict[str, Any]:
        if value < MIN_PANNING or value > MAX_PANNING:
            raise _invalid_argument(
                message=f"value must be between {MIN_PANNING} and {MAX_PANNING}",
                hint="Use a normalized panning value in [-1.0, 1.0].",
            )
        target = self._track_at(track)
        target.mixer_device.panning.value = float(value)
        return {"track": track, "panning": float(target.mixer_device.panning.value)}

    def create_clip(self, track: int, clip: int, length: float) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if slot.has_clip:
            raise _invalid_argument(
                message="Clip slot already has a clip",
                hint="Use an empty clip slot.",
            )
        slot.create_clip(float(length))
        if not slot.has_clip:
            raise CommandError(
                code="INTERNAL_ERROR",
                message="Clip creation did not produce a clip",
                hint="Retry and check Ableton logs.",
            )
        clip_obj = slot.clip
        return {
            "track": track,
            "clip": clip,
            "name": str(getattr(clip_obj, "name", "")),
            "length": float(getattr(clip_obj, "length", length)),
        }

    def add_notes_to_clip(
        self, track: int, clip: int, notes: list[dict[str, Any]]
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before adding notes.",
            )
        clip_obj = slot.clip
        live_notes = []
        for note in notes:
            live_notes.append(
                (
                    int(note["pitch"]),
                    float(note["start_time"]),
                    float(note["duration"]),
                    int(note["velocity"]),
                    bool(note["mute"]),
                )
            )
        clip_obj.set_notes(tuple(live_notes))
        return {"track": track, "clip": clip, "note_count": len(live_notes)}

    def get_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before reading notes.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        filtered = self._filtered_clip_notes(clip_obj, start_time, end_time, pitch)
        payload_notes = [
            {
                "pitch": int(note["pitch"]),
                "start_time": float(note["start_time"]),
                "duration": float(note["duration"]),
                "velocity": int(note["velocity"]),
                "mute": bool(note["mute"]),
            }
            for note in filtered
        ]
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "notes": payload_notes,
            "note_count": len(payload_notes),
        }

    def clear_clip_notes(
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before clearing notes.",
            )
        clip_obj = slot.clip
        assert clip_obj is not None
        filtered = self._filtered_clip_notes(clip_obj, start_time, end_time, pitch)
        to_remove = [int(note["note_id"]) for note in filtered]
        if to_remove:
            clip_obj.remove_notes_by_id(to_remove)
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": len(to_remove),
        }

    def replace_clip_notes(
        self,
        track: int,
        clip: int,
        notes: list[dict[str, Any]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        cleared = self.clear_clip_notes(track, clip, start_time, end_time, pitch)
        added = self.add_notes_to_clip(track, clip, notes)
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": int(cleared["cleared_count"]),
            "added_count": int(added["note_count"]),
        }

    def set_clip_name(self, track: int, clip: int, name: str) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before renaming.",
            )
        clip_obj = slot.clip
        clip_obj.name = name
        return {"track": track, "clip": clip, "name": str(clip_obj.name)}

    def fire_clip(self, track: int, clip: int) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before firing.",
            )
        slot.fire()
        return {"track": track, "clip": clip, "fired": True}

    def stop_clip(self, track: int, clip: int) -> dict[str, Any]:
        slot = self._clip_slot_at(track, clip)
        if not slot.has_clip:
            raise _invalid_argument(
                message="No clip in slot",
                hint="Create a clip in the target slot before stopping.",
            )
        slot.stop()
        return {"track": track, "clip": clip, "stopped": True}

    def clip_duplicate(self, track: int, src_clip: int, dst_clip: int) -> dict[str, Any]:
        source_slot = self._clip_slot_at(track, src_clip)
        if not source_slot.has_clip:
            raise _invalid_argument(
                message="Source clip does not exist",
                hint="Create a clip in the source slot before duplicating.",
            )

        destination_slot = self._clip_slot_at(track, dst_clip)
        if destination_slot.has_clip:
            raise _invalid_argument(
                message="Destination clip slot already has a clip",
                hint="Use an empty destination clip slot.",
            )

        source_clip = source_slot.clip
        assert source_clip is not None
        source_length = float(getattr(source_clip, "length", 0.0))
        if source_length <= 0:
            raise _invalid_argument(
                message="Source clip length must be > 0",
                hint="Duplicate only clips with positive length.",
            )

        destination_slot.create_clip(source_length)
        if not destination_slot.has_clip:
            raise CommandError(
                code="INTERNAL_ERROR",
                message="Clip duplication did not create destination clip",
                hint="Retry and check Ableton logs.",
            )
        destination_clip = destination_slot.clip
        assert destination_clip is not None

        source_notes = self._clip_notes_extended(source_clip)
        live_notes = [
            (
                int(note["pitch"]),
                float(note["start_time"]),
                float(note["duration"]),
                int(note["velocity"]),
                bool(note["mute"]),
            )
            for note in source_notes
        ]
        if live_notes:
            destination_clip.set_notes(tuple(live_notes))
        destination_clip.name = str(getattr(source_clip, "name", ""))

        return {
            "track": track,
            "src_clip": src_clip,
            "dst_clip": dst_clip,
            "duplicated": True,
            "note_count": len(live_notes),
        }

    def load_instrument_or_effect(
        self, track: int, uri: str | None, path: str | None
    ) -> dict[str, Any]:
        if uri is None and path is None:
            raise _invalid_argument(
                message="Exactly one of uri or path must be provided",
                hint="Provide --uri or --path.",
            )
        if uri is not None and path is not None:
            raise _invalid_argument(
                message="uri and path are mutually exclusive",
                hint="Provide only one of uri or path.",
            )

        target = self._track_at(track)
        if uri is not None:
            item = self._find_browser_item_by_uri(uri)
            if item is None:
                raise _invalid_argument(
                    message=f"Browser item with URI '{uri}' not found",
                    hint="Inspect browser tree/items and choose a valid URI.",
                )
            resolved_path = self._item_path_by_uri(uri)
            serialized = self._serialize_browser_item(item, path=resolved_path)
        else:
            assert path is not None
            item = self._resolve_browser_path(path)
            serialized = self._serialize_browser_item(item, path=path)
            if not serialized["is_loadable"]:
                raise _invalid_argument(
                    message=f"Browser item at path '{path}' is not loadable",
                    hint="Use browser search/items to select a loadable item.",
                )
            uri = serialized["uri"]

        song = self._song()
        if hasattr(song, "view") and hasattr(song.view, "selected_track"):
            song.view.selected_track = target
        self._browser().load_item(item)

        return {
            "track": track,
            "loaded": True,
            "item_name": str(getattr(item, "name", "")),
            "uri": uri,
            "path": serialized["path"],
        }

    def get_browser_tree(self, category_type: str) -> dict[str, Any]:
        categories = self._browser_category_map()
        available = sorted(categories.keys())
        if category_type == "all":
            selected = available
        else:
            if category_type not in categories:
                raise _invalid_argument(
                    message=f"Unknown or unavailable category: {category_type}",
                    hint=f"Available categories: {', '.join(available)}",
                )
            selected = [category_type]

        tree = []
        for name in selected:
            root = categories[name]
            tree.append(self._serialize_browser_tree(root, name))
        return {
            "type": category_type,
            "categories": tree,
            "total_folders": len(tree),
            "available_categories": available,
        }

    def get_browser_items_at_path(self, path: str) -> dict[str, Any]:
        node = self._resolve_browser_path(path)
        children = []
        for child in list(getattr(node, "children", []) or []):
            child_name = str(getattr(child, "name", ""))
            child_path = f"{path.rstrip('/')}/{child_name}"
            children.append(self._serialize_browser_item(child, path=child_path))
        return {
            "path": path,
            "name": str(getattr(node, "name", "Unknown")),
            "uri": self._coerce_uri(getattr(node, "uri", None)),
            "is_folder": bool(getattr(node, "children", [])),
            "is_device": bool(getattr(node, "is_device", False)),
            "is_loadable": bool(getattr(node, "is_loadable", False)),
            "items": children,
        }

    def get_browser_item(self, uri: str | None, path: str | None) -> dict[str, Any]:
        if uri is not None:
            item = self._find_browser_item_by_uri(uri)
            if item is None:
                return {"uri": uri, "path": None, "found": False}
            found_path = self._item_path_by_uri(uri)
            return {
                "uri": uri,
                "path": found_path,
                "found": True,
                "item": self._serialize_browser_item(item, path=found_path),
            }

        if path is not None:
            item = self._resolve_browser_path(path)
            return {
                "uri": self._coerce_uri(getattr(item, "uri", None)),
                "path": path,
                "found": True,
                "item": self._serialize_browser_item(item, path=path),
            }

        raise _invalid_argument(
            message="Exactly one of uri or path must be provided",
            hint="Provide uri or path.",
        )

    def get_browser_categories(self, category_type: str) -> dict[str, Any]:
        categories = self._browser_category_map()
        available = sorted(categories.keys())
        if category_type == "all":
            selected = available
        else:
            if category_type not in categories:
                raise _invalid_argument(
                    message=f"Unknown or unavailable category: {category_type}",
                    hint=f"Available categories: {', '.join(available)}",
                )
            selected = [category_type]

        payload = []
        for name in selected:
            payload.append(self._serialize_browser_item(categories[name], path=name))
        return {
            "type": category_type,
            "categories": payload,
            "available_categories": available,
        }

    def get_browser_items(
        self, path: str, item_type: str, limit: int, offset: int
    ) -> dict[str, Any]:
        if limit <= 0:
            raise _invalid_argument(
                message="limit must be > 0",
                hint="Use a positive integer limit.",
            )
        if offset < 0:
            raise _invalid_argument(
                message="offset must be >= 0",
                hint="Use a non-negative integer offset.",
            )

        started_at = perf_counter()
        result = self.get_browser_items_at_path(path)
        if item_type == "all":
            filtered = list(result["items"])
        else:
            filtered = []
            for item in result["items"]:
                if item_type == "folder" and item["is_folder"]:
                    filtered.append(item)
                elif item_type == "device" and item["is_device"]:
                    filtered.append(item)
                elif item_type == "loadable" and item["is_loadable"]:
                    filtered.append(item)

        total_matches = len(filtered)
        paged = filtered[offset : offset + limit]
        returned = len(paged)
        return {
            **result,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "returned": returned,
            "total_matches": total_matches,
            "has_more": (offset + returned) < total_matches,
            "duration_ms": (perf_counter() - started_at) * 1000.0,
            "items": paged,
        }

    def search_browser_items(
        self,
        query: str,
        path: str | None,
        item_type: str,
        limit: int,
        offset: int,
        exact: bool,
        case_sensitive: bool,
    ) -> dict[str, Any]:
        if not query.strip():
            raise _invalid_argument(
                message="query must not be empty",
                hint="Pass a non-empty search query.",
            )
        if path is not None and not path.strip():
            raise _invalid_argument(
                message="path must not be empty",
                hint="Pass a non-empty browser path.",
            )
        if item_type not in {"all", "folder", "device", "loadable"}:
            raise _invalid_argument(
                message=f"item_type must be one of all/folder/device/loadable, got {item_type}",
                hint="Use a supported item type.",
            )
        if limit <= 0:
            raise _invalid_argument(
                message="limit must be > 0",
                hint="Use a positive integer limit.",
            )
        if offset < 0:
            raise _invalid_argument(
                message="offset must be >= 0",
                hint="Use a non-negative integer offset.",
            )
        started_at = perf_counter()
        candidates = self._browser_search_candidates(path)

        matches: list[tuple[int, dict[str, Any]]] = []
        for item in candidates:
            if not self._item_matches_type(item, item_type):
                continue
            rank = self._match_rank(
                item,
                query,
                exact=exact,
                case_sensitive=case_sensitive,
            )
            if rank is None:
                continue
            matches.append((rank, item))

        matches.sort(
            key=lambda value: (
                value[0],
                str(value[1].get("path") or ""),
                str(value[1].get("name") or ""),
                str(value[1].get("uri") or ""),
            )
        )

        total_matches = len(matches)
        paged = matches[offset : offset + limit]
        items = [item for _rank, item in paged]
        returned = len(items)

        return {
            "query": query,
            "path": path,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "returned": returned,
            "total_matches": total_matches,
            "has_more": (offset + returned) < total_matches,
            "duration_ms": (perf_counter() - started_at) * 1000.0,
            "items": items,
        }

    def load_drum_kit(
        self,
        track: int,
        rack_uri: str,
        kit_uri: str | None,
        kit_path: str | None,
    ) -> dict[str, Any]:
        if kit_uri is None and kit_path is None:
            raise _invalid_argument(
                message="Exactly one of kit_uri or kit_path must be provided",
                hint="Provide a specific kit URI or path.",
            )
        if kit_uri is not None and kit_path is not None:
            raise _invalid_argument(
                message="kit_uri and kit_path are mutually exclusive",
                hint="Provide only one kit selector.",
            )

        self.load_instrument_or_effect(track, uri=rack_uri, path=None)

        selected_item: dict[str, Any]
        if kit_uri is not None:
            item = self._find_browser_item_by_uri(kit_uri)
            if item is None:
                raise _invalid_argument(
                    message=f"Browser item with URI '{kit_uri}' not found",
                    hint="Inspect browser tree/items and choose a valid kit URI.",
                )
            resolved_path = self._item_path_by_uri(kit_uri)
            selected_item = self._serialize_browser_item(item, path=resolved_path)
            if not selected_item["is_loadable"]:
                raise _invalid_argument(
                    message=f"Browser item with URI '{kit_uri}' is not loadable",
                    hint="Select a loadable drum kit URI.",
                )
            self.load_instrument_or_effect(track, uri=kit_uri, path=None)
            resolved_kit_uri = kit_uri
            resolved_kit_path = selected_item["path"]
        else:
            assert kit_path is not None
            item = self._resolve_browser_path(kit_path)
            selected_item = self._serialize_browser_item(item, path=kit_path)
            if not selected_item["is_loadable"] or not selected_item["uri"]:
                raise _invalid_argument(
                    message=f"Browser item at path '{kit_path}' is not loadable",
                    hint="Select a loadable drum kit path.",
                )
            resolved_kit_uri = str(selected_item["uri"])
            resolved_kit_path = kit_path
            self.load_instrument_or_effect(track, uri=resolved_kit_uri, path=None)

        return {
            "track": track,
            "loaded": True,
            "rack_uri": rack_uri,
            "kit_uri": str(resolved_kit_uri),
            "kit_path": resolved_kit_path,
            "kit_name": str(selected_item["name"]),
        }

    def scenes_list(self) -> dict[str, Any]:
        scenes = []
        for index, scene in enumerate(list(getattr(self._song(), "scenes", []))):
            scenes.append({"index": index, "name": str(getattr(scene, "name", ""))})
        return {"scenes": scenes}

    def create_scene(self, index: int) -> dict[str, Any]:
        song = self._song()
        scenes = list(getattr(song, "scenes", []))
        if index != -1 and index > len(scenes):
            raise _invalid_argument(
                message=f"index out of range: {index}",
                hint="Use -1 for append or a valid insertion index.",
            )

        target_index = len(scenes) if index == -1 else index
        song.create_scene(target_index)
        created = self._scene_at(target_index)
        return {"index": target_index, "name": str(getattr(created, "name", ""))}

    def set_scene_name(self, scene: int, name: str) -> dict[str, Any]:
        target = self._scene_at(scene)
        target.name = name
        return {"scene": scene, "name": str(target.name)}

    def fire_scene(self, scene: int) -> dict[str, Any]:
        target = self._scene_at(scene)
        target.fire()
        return {"scene": scene, "fired": True}

    def scenes_move(self, from_index: int, to_index: int) -> dict[str, Any]:
        self._scene_at(from_index)
        self._scene_at(to_index)
        move_scene = getattr(self._song(), "move_scene", None)
        if not callable(move_scene):
            raise _not_supported_by_live_api(
                message="Scene move API is not available in Live API",
                hint="Move scenes manually in Ableton Live.",
            )
        move_scene(from_index, to_index)
        return {"from": from_index, "to": to_index, "moved": True}

    def stop_all_clips(self) -> dict[str, Any]:
        song = self._song()
        if not hasattr(song, "stop_all_clips"):
            raise _invalid_argument(
                message="Song does not support stop_all_clips",
                hint="Use a compatible Ableton Live version.",
            )
        song.stop_all_clips()
        return {"stopped": True}

    def arrangement_record_start(self) -> dict[str, Any]:
        song = self._song()
        if hasattr(song, "record_mode"):
            song.record_mode = True
            return {"recording": bool(song.record_mode)}
        start_recording = getattr(song, "start_arrangement_recording", None)
        if callable(start_recording):
            start_recording()
            return {"recording": True}
        raise _not_supported_by_live_api(
            message="Arrangement record start API is not available in Live API",
            hint="Start arrangement recording manually in Ableton Live.",
        )

    def arrangement_record_stop(self) -> dict[str, Any]:
        song = self._song()
        if hasattr(song, "record_mode"):
            song.record_mode = False
            return {"recording": bool(song.record_mode)}
        stop_recording = getattr(song, "stop_arrangement_recording", None)
        if callable(stop_recording):
            stop_recording()
            return {"recording": False}
        raise _not_supported_by_live_api(
            message="Arrangement record stop API is not available in Live API",
            hint="Stop arrangement recording manually in Ableton Live.",
        )

    def tracks_delete(self, track: int) -> dict[str, Any]:
        self._track_at(track)
        delete_track = getattr(self._song(), "delete_track", None)
        if not callable(delete_track):
            raise _not_supported_by_live_api(
                message="Track delete API is not available in Live API",
                hint="Delete tracks manually in Ableton Live.",
            )
        delete_track(track)
        return {"track": track, "deleted": True, "track_count": len(list(self._song().tracks))}

    def set_device_parameter(
        self, track: int, device: int, parameter: int, value: float
    ) -> dict[str, Any]:
        target_param = self._parameter_at(track, device, parameter)
        target_param.value = float(value)
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "value": float(target_param.value),
        }

    def find_synth_devices(
        self,
        track: int | None,
        synth_type: str | None,
    ) -> dict[str, Any]:
        parsed_type: str | None = None
        if synth_type is not None:
            try:
                parsed_type = canonicalize_synth_type(synth_type)
            except ValueError as exc:
                raise _invalid_argument(
                    message=f"Unsupported synth_type: {synth_type}",
                    hint=f"Use one of: {', '.join(SUPPORTED_SYNTH_TYPES)}.",
                ) from exc

        if track is None:
            track_indexes = range(len(list(self._song().tracks)))
        else:
            self._track_at(track)
            track_indexes = (track,)

        devices: list[dict[str, Any]] = []
        for track_index in track_indexes:
            target_track = self._track_at(track_index)
            for device_index, target_device in enumerate(list(target_track.devices)):
                detected_type = self._synth_type_for_device(target_device)
                if detected_type is None:
                    continue
                if parsed_type is not None and detected_type != parsed_type:
                    continue
                devices.append(
                    self._synth_device_payload(
                        track=track_index,
                        device_index=device_index,
                        device=target_device,
                        detected_type=detected_type,
                    )
                )

        return {
            "track": track,
            "synth_type": parsed_type,
            "count": len(devices),
            "devices": devices,
        }

    def list_synth_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._list_synth_parameters_payload(track, device)

    def set_synth_parameter_safe(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        target_device, detected_type = self._require_supported_synth_device(track, device)
        del target_device
        target_parameter = self._parameter_at(track, device, parameter)
        serialized_parameter = self._serialize_parameter(target_parameter, parameter)

        if not serialized_parameter["is_enabled"]:
            raise _invalid_argument(
                message=f"Parameter is disabled at index {parameter}",
                hint="Choose an enabled parameter from synth parameters list.",
            )

        minimum = serialized_parameter["min"]
        maximum = serialized_parameter["max"]
        if minimum is None or maximum is None:
            raise _invalid_argument(
                message=f"Parameter bounds are unavailable at index {parameter}",
                hint="Choose a parameter with numeric min/max bounds.",
            )
        if value < minimum or value > maximum:
            raise _invalid_argument(
                message=f"value must be between {minimum} and {maximum}",
                hint="Use a value within the reported parameter range.",
            )

        before = float(getattr(target_parameter, "value", 0.0))
        target_parameter.value = float(value)
        after = float(getattr(target_parameter, "value", 0.0))
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "detected_type": detected_type,
            "before": before,
            "after": after,
            "min": minimum,
            "max": maximum,
            "is_enabled": serialized_parameter["is_enabled"],
            "is_quantized": serialized_parameter["is_quantized"],
        }

    def observe_synth_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._list_synth_parameters_payload(track, device)

    def list_standard_synth_keys(self, synth_type: str) -> dict[str, Any]:
        try:
            parsed_type = canonicalize_synth_type(synth_type)
        except ValueError as exc:
            raise _invalid_argument(
                message=f"Unsupported synth_type: {synth_type}",
                hint=f"Use one of: {', '.join(SUPPORTED_SYNTH_TYPES)}.",
            ) from exc
        keys = standard_synth_keys(parsed_type)
        return {
            "synth_type": parsed_type,
            "key_count": len(keys),
            "keys": keys,
        }

    def set_standard_synth_parameter_safe(
        self,
        synth_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._resolved_standard_synth_key_indexes(
            synth_type=synth_type,
            track=track,
            device=device,
        )
        if key not in key_indexes:
            raise _invalid_argument(
                message=f"Unsupported key for {parsed_type}: {key}",
                hint=f"Use one of: {', '.join(standard_synth_keys(parsed_type))}.",
            )

        parameter_index = key_indexes[key]
        result = self.set_synth_parameter_safe(
            track=track,
            device=device,
            parameter=parameter_index,
            value=value,
        )
        return {
            **result,
            "synth_type": parsed_type,
            "key": key,
            "resolved_parameter": parameter_index,
        }

    def observe_standard_synth_state(
        self,
        synth_type: str,
        track: int,
        device: int,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._resolved_standard_synth_key_indexes(
            synth_type=synth_type,
            track=track,
            device=device,
        )
        observed = self.observe_synth_parameters(track, device)
        parameters = observed["parameters"]
        state = {
            key: float(parameters[index]["value"])
            for key, index in key_indexes.items()
        }
        return {
            "synth_type": parsed_type,
            "track": track,
            "device": device,
            "key_count": len(state),
            "keys": standard_synth_keys(parsed_type),
            "state": state,
        }

    def find_effect_devices(
        self,
        track: int | None,
        effect_type: str | None,
    ) -> dict[str, Any]:
        parsed_type: str | None = None
        if effect_type is not None:
            try:
                parsed_type = canonicalize_effect_type(effect_type)
            except ValueError as exc:
                raise _invalid_argument(
                    message=f"Unsupported effect_type: {effect_type}",
                    hint=f"Use one of: {', '.join(SUPPORTED_EFFECT_TYPES)}.",
                ) from exc

        if track is None:
            track_indexes = range(len(list(self._song().tracks)))
        else:
            self._track_at(track)
            track_indexes = (track,)

        devices: list[dict[str, Any]] = []
        for track_index in track_indexes:
            target_track = self._track_at(track_index)
            for device_index, target_device in enumerate(list(target_track.devices)):
                detected_type = self._effect_type_for_device(target_device)
                if detected_type is None:
                    continue
                if parsed_type is not None and detected_type != parsed_type:
                    continue
                devices.append(
                    self._effect_device_payload(
                        track=track_index,
                        device_index=device_index,
                        device=target_device,
                        detected_type=detected_type,
                    )
                )

        return {
            "track": track,
            "effect_type": parsed_type,
            "count": len(devices),
            "devices": devices,
        }

    def list_effect_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._list_effect_parameters_payload(track, device)

    def set_effect_parameter_safe(
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ) -> dict[str, Any]:
        target_device, detected_type = self._require_supported_effect_device(track, device)
        del target_device
        target_parameter = self._parameter_at(track, device, parameter)
        serialized_parameter = self._serialize_parameter(target_parameter, parameter)

        if not serialized_parameter["is_enabled"]:
            raise _invalid_argument(
                message=f"Parameter is disabled at index {parameter}",
                hint="Choose an enabled parameter from effect parameters list.",
            )

        minimum = serialized_parameter["min"]
        maximum = serialized_parameter["max"]
        if minimum is None or maximum is None:
            raise _invalid_argument(
                message=f"Parameter bounds are unavailable at index {parameter}",
                hint="Choose a parameter with numeric min/max bounds.",
            )
        if value < minimum or value > maximum:
            raise _invalid_argument(
                message=f"value must be between {minimum} and {maximum}",
                hint="Use a value within the reported parameter range.",
            )

        before = float(getattr(target_parameter, "value", 0.0))
        target_parameter.value = float(value)
        after = float(getattr(target_parameter, "value", 0.0))
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "detected_type": detected_type,
            "before": before,
            "after": after,
            "min": minimum,
            "max": maximum,
            "is_enabled": serialized_parameter["is_enabled"],
            "is_quantized": serialized_parameter["is_quantized"],
        }

    def observe_effect_parameters(self, track: int, device: int) -> dict[str, Any]:
        return self._list_effect_parameters_payload(track, device)

    def list_standard_effect_keys(self, effect_type: str) -> dict[str, Any]:
        try:
            parsed_type = canonicalize_effect_type(effect_type)
        except ValueError as exc:
            raise _invalid_argument(
                message=f"Unsupported effect_type: {effect_type}",
                hint=f"Use one of: {', '.join(SUPPORTED_EFFECT_TYPES)}.",
            ) from exc
        keys = standard_effect_keys(parsed_type)
        return {
            "effect_type": parsed_type,
            "key_count": len(keys),
            "keys": keys,
        }

    def set_standard_effect_parameter_safe(
        self,
        effect_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._resolved_standard_effect_key_indexes(
            effect_type=effect_type,
            track=track,
            device=device,
        )
        if key not in key_indexes:
            raise _invalid_argument(
                message=f"Unsupported key for {parsed_type}: {key}",
                hint=f"Use one of: {', '.join(standard_effect_keys(parsed_type))}.",
            )

        parameter_index = key_indexes[key]
        result = self.set_effect_parameter_safe(
            track=track,
            device=device,
            parameter=parameter_index,
            value=value,
        )
        return {
            **result,
            "effect_type": parsed_type,
            "key": key,
            "resolved_parameter": parameter_index,
        }

    def observe_standard_effect_state(
        self,
        effect_type: str,
        track: int,
        device: int,
    ) -> dict[str, Any]:
        key_indexes, parsed_type = self._resolved_standard_effect_key_indexes(
            effect_type=effect_type,
            track=track,
            device=device,
        )
        observed = self.observe_effect_parameters(track, device)
        parameters = observed["parameters"]
        state = {
            key: float(parameters[index]["value"])
            for key, index in key_indexes.items()
        }
        return {
            "effect_type": parsed_type,
            "track": track,
            "device": device,
            "key_count": len(state),
            "keys": standard_effect_keys(parsed_type),
            "state": state,
        }

    def _get_device_type(self, device: Any) -> str:
        try:
            if bool(getattr(device, "can_have_drum_pads", False)):
                return "drum_machine"
            if bool(getattr(device, "can_have_chains", False)):
                return "rack"
            class_display_name = str(getattr(device, "class_display_name", "")).lower()
            class_name = str(getattr(device, "class_name", "")).lower()
            if "instrument" in class_display_name:
                return "instrument"
            if "audio_effect" in class_name:
                return "audio_effect"
            if "midi_effect" in class_name:
                return "midi_effect"
            return "unknown"
        except Exception:  # noqa: BLE001
            return "unknown"
