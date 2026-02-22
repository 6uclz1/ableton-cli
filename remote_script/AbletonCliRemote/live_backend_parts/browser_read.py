from __future__ import annotations

from time import monotonic, sleep
from typing import Any

from ..command_backend import CommandError
from .base import _invalid_argument, _not_supported_by_live_api

_ALLOWED_TARGET_TRACK_MODES = frozenset({"auto", "existing", "new"})
_BROWSER_IMPORT_SETTLE_TIMEOUT_SECONDS = 1.0
_BROWSER_IMPORT_SETTLE_POLL_INTERVAL_SECONDS = 0.01


class LiveBackendBrowserReadMixin:
    def _resolve_load_target_track(self, *, track: int, target_track_mode: str) -> tuple[Any, int]:
        if target_track_mode not in _ALLOWED_TARGET_TRACK_MODES:
            raise _invalid_argument(
                message=(
                    f"target_track_mode must be one of auto/existing/new, got {target_track_mode}"
                ),
                hint="Use a supported target_track_mode.",
            )

        if target_track_mode != "new":
            return self._track_at(track), track

        song = self._song()
        tracks = list(getattr(song, "tracks", []))
        if track > len(tracks):
            raise _invalid_argument(
                message=f"track out of range: {track}",
                hint="Use a non-negative insertion index up to the current track count.",
            )
        create_midi_track = getattr(song, "create_midi_track", None)
        if not callable(create_midi_track):
            raise _not_supported_by_live_api(
                message="Track creation API is not available in Live API",
                hint="Use target_track_mode auto or existing instead.",
            )
        create_midi_track(track)
        return self._track_at(track), track

    def _select_track_for_load(self, *, song: Any, target_track: Any) -> None:
        view = getattr(song, "view", None)
        if view is None or not hasattr(view, "selected_track"):
            raise _not_supported_by_live_api(
                message="Song view selected_track API is not available in Live API",
                hint="Use a Live version exposing song.view.selected_track.",
            )
        view.selected_track = target_track

    def _select_clip_slot_for_load(
        self,
        *,
        song: Any,
        target_track: Any,
        clip_slot: int | None,
    ) -> int | None:
        if clip_slot is None:
            return None

        slots = list(getattr(target_track, "clip_slots", []))
        if clip_slot < 0 or clip_slot >= len(slots):
            raise _invalid_argument(
                message=f"clip_slot out of range: {clip_slot}",
                hint="Use a valid clip slot index for the target track.",
            )

        view = getattr(song, "view", None)
        if view is None:
            raise _not_supported_by_live_api(
                message="Song view is not available in Live API",
                hint="Use --clip-slot only on versions exposing song.view.",
            )

        selected = False
        scenes = list(getattr(song, "scenes", []))
        if clip_slot < len(scenes) and hasattr(view, "selected_scene"):
            view.selected_scene = scenes[clip_slot]
            selected = True
        if hasattr(view, "highlighted_clip_slot"):
            view.highlighted_clip_slot = slots[clip_slot]
            selected = True
        if not selected:
            raise _not_supported_by_live_api(
                message="Clip slot selection API is not available in Live API",
                hint="Use a Live version exposing selected_scene or highlighted_clip_slot.",
            )
        return clip_slot

    @staticmethod
    def _is_midi_clip_browser_item(item: Any) -> bool:
        name = str(getattr(item, "name", "")).strip().lower()
        return bool(name.endswith(".alc"))

    @staticmethod
    def _created_tracks_since(
        *,
        after: list[Any],
        base_track_count: int,
    ) -> list[tuple[int, Any]]:
        start = min(max(int(base_track_count), 0), len(after))
        return [(index, track) for index, track in enumerate(after[start:], start=start)]

    @staticmethod
    def _first_track_clip(track: Any) -> tuple[int, Any] | None:
        for slot_index, slot in enumerate(list(getattr(track, "clip_slots", []))):
            if not bool(getattr(slot, "has_clip", False)):
                continue
            clip_obj = getattr(slot, "clip", None)
            if clip_obj is not None:
                return slot_index, clip_obj
        return None

    def _created_track_details(
        self,
        *,
        after: list[Any],
        base_track_count: int,
    ) -> list[dict[str, Any]]:
        details: list[dict[str, Any]] = []
        for index, track in self._created_tracks_since(
            after=after,
            base_track_count=base_track_count,
        ):
            clip_entry = self._first_track_clip(track)
            details.append(
                {
                    "index": index,
                    "track": track,
                    "name": str(getattr(track, "name", "")),
                    "has_clip": clip_entry is not None,
                    "clip_slot": clip_entry[0] if clip_entry is not None else None,
                    "clip": clip_entry[1] if clip_entry is not None else None,
                }
            )
        return details

    @staticmethod
    def _created_track_error_details(*, created_tracks: list[dict[str, Any]]) -> dict[str, Any]:
        clip_tracks = [track for track in created_tracks if bool(track.get("has_clip"))]
        return {
            "created_track_count": len(created_tracks),
            "clip_track_count": len(clip_tracks),
            "created_tracks": [
                {
                    "index": int(track["index"]),
                    "name": str(track["name"]),
                    "has_clip": bool(track["has_clip"]),
                    "clip_slot": track["clip_slot"],
                }
                for track in created_tracks
            ],
        }

    def _raise_ambiguous_created_track_error(
        self,
        *,
        message: str,
        hint: str,
        created_tracks: list[dict[str, Any]],
    ) -> None:
        raise CommandError(
            code="INVALID_ARGUMENT",
            message=message,
            hint=hint,
            details=self._created_track_error_details(created_tracks=created_tracks),
        )

    def _cleanup_created_tracks_except(
        self,
        *,
        song: Any,
        base_track_count: int,
        keep_track_indices: set[int],
    ) -> dict[int, int]:
        tracks_after_load = list(getattr(song, "tracks", []))
        created_tracks = self._created_tracks_since(
            after=tracks_after_load,
            base_track_count=base_track_count,
        )
        deleted_before_kept = {index: 0 for index in keep_track_indices}
        for track_index, _created_track in reversed(created_tracks):
            if track_index in keep_track_indices:
                continue
            self._delete_track(song, track_index)
            for kept_track_index in keep_track_indices:
                if track_index < kept_track_index:
                    deleted_before_kept[kept_track_index] += 1
        return {
            kept_track_index: kept_track_index - deleted_before_kept[kept_track_index]
            for kept_track_index in keep_track_indices
        }

    def _cleanup_created_tracks(self, *, song: Any, base_track_count: int) -> None:
        self._cleanup_created_tracks_except(
            song=song,
            base_track_count=base_track_count,
            keep_track_indices=set(),
        )

    def _wait_for_created_clip_track(
        self,
        *,
        song: Any,
        base_track_count: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        deadline = monotonic() + _BROWSER_IMPORT_SETTLE_TIMEOUT_SECONDS
        latest_created_tracks: list[dict[str, Any]] = []
        while True:
            latest_created_tracks = self._created_track_details(
                after=list(getattr(song, "tracks", [])),
                base_track_count=base_track_count,
            )
            clip_tracks = [track for track in latest_created_tracks if bool(track["has_clip"])]
            if len(clip_tracks) == 1:
                return latest_created_tracks, clip_tracks[0]
            if monotonic() >= deadline:
                return latest_created_tracks, None
            sleep(_BROWSER_IMPORT_SETTLE_POLL_INTERVAL_SECONDS)

    @staticmethod
    def _scene_index(song: Any, scene_obj: Any) -> int | None:
        for index, scene in enumerate(list(getattr(song, "scenes", []))):
            if scene is scene_obj:
                return index
        return None

    def _selected_scene_index(self, *, song: Any) -> int | None:
        view = getattr(song, "view", None)
        if view is None or not hasattr(view, "selected_scene"):
            return None
        selected_scene = getattr(view, "selected_scene", None)
        if selected_scene is None:
            return None
        return self._scene_index(song, selected_scene)

    def _resolve_rehome_clip_slot(
        self,
        *,
        song: Any,
        target_track: Any,
        clip_slot: int | None,
    ) -> int:
        if clip_slot is not None:
            return clip_slot

        selected_scene_index = self._selected_scene_index(song=song)
        if selected_scene_index is None:
            raise _invalid_argument(
                message="clip_slot is required when selected scene is unavailable",
                hint=(
                    "Pass --clip-slot when using target_track_mode=existing for MIDI clip targets."
                ),
            )

        target_slots = list(getattr(target_track, "clip_slots", []))
        if selected_scene_index < 0 or selected_scene_index >= len(target_slots):
            raise _invalid_argument(
                message=(
                    f"selected scene index out of range for target track: {selected_scene_index}"
                ),
                hint="Use --clip-slot to choose a valid destination clip slot.",
            )
        return selected_scene_index

    @staticmethod
    def _clip_note_tuples(
        notes: list[dict[str, Any]],
    ) -> tuple[tuple[int, float, float, int, bool], ...]:
        return tuple(
            (
                int(note["pitch"]),
                float(note["start_time"]),
                float(note["duration"]),
                int(note["velocity"]),
                bool(note["mute"]),
            )
            for note in notes
        )

    def _import_clip_notes(
        self,
        *,
        source_clip: Any,
        target_clip: Any,
        notes_mode: str,
    ) -> int:
        source_notes = list(self._clip_notes_extended(source_clip))
        if notes_mode == "replace":
            existing_notes = list(self._clip_notes_extended(target_clip))
            note_ids_to_remove = [int(note["note_id"]) for note in existing_notes]
            remove_notes_by_id = getattr(target_clip, "remove_notes_by_id", None)
            if note_ids_to_remove and callable(remove_notes_by_id):
                remove_notes_by_id(note_ids_to_remove)
        elif notes_mode != "append":
            raise _invalid_argument(
                message=f"notes_mode must be one of replace/append, got {notes_mode}",
                hint="Use notes_mode replace or append.",
            )

        set_notes = getattr(target_clip, "set_notes", None)
        if not callable(set_notes):
            raise _not_supported_by_live_api(
                message="Clip note write API is not available in Live API",
                hint="Use a Live version exposing clip.set_notes for MIDI clips.",
            )
        note_payload = self._clip_note_tuples(source_notes)
        if note_payload:
            set_notes(note_payload)
        return len(note_payload)

    @staticmethod
    def _import_clip_length(*, source_clip: Any, target_clip: Any) -> bool:
        if not hasattr(source_clip, "length") or not hasattr(target_clip, "length"):
            return False
        source_length = getattr(source_clip, "length", None)
        if not isinstance(source_length, (int, float)):
            return False
        normalized_length = float(source_length)
        if normalized_length <= 0:
            return False
        try:
            target_clip.length = normalized_length
        except Exception:
            return False
        return True

    @staticmethod
    def _import_clip_groove(*, source_clip: Any, target_clip: Any) -> bool:
        imported = False
        for attribute in ("groove", "groove_assignment"):
            if not hasattr(source_clip, attribute) or not hasattr(target_clip, attribute):
                continue
            try:
                setattr(target_clip, attribute, getattr(source_clip, attribute))
            except Exception:
                continue
            imported = True
            break

        for attribute in ("groove_amount", "groove_amount_value"):
            if not hasattr(source_clip, attribute) or not hasattr(target_clip, attribute):
                continue
            source_value = getattr(source_clip, attribute)
            if isinstance(source_value, (int, float)):
                try:
                    setattr(target_clip, attribute, float(source_value))
                except Exception:
                    continue
                imported = True
            break

        for attribute in (
            "_ableton_cli_groove_uri",
            "_ableton_cli_groove_path",
            "_ableton_cli_groove_name",
        ):
            if not hasattr(source_clip, attribute):
                continue
            try:
                setattr(target_clip, attribute, getattr(source_clip, attribute))
            except Exception:
                continue
            imported = True
        return imported

    @staticmethod
    def _copy_clip_name(*, source_clip: Any, target_clip: Any) -> None:
        if not hasattr(target_clip, "name"):
            return
        try:
            target_clip.name = str(getattr(source_clip, "name", ""))
        except Exception:
            return

    @staticmethod
    def _delete_track(song: Any, track_index: int) -> None:
        delete_track = getattr(song, "delete_track", None)
        if not callable(delete_track):
            raise _not_supported_by_live_api(
                message="Track delete API is not available in Live API",
                hint="Use a Live version exposing song.delete_track.",
            )
        delete_track(track_index)

    def _target_clip_for_import(
        self,
        *,
        target_track: Any,
        clip_slot: int,
        source_clip: Any,
        require_existing_clip: bool,
    ) -> Any:
        target_slots = list(getattr(target_track, "clip_slots", []))
        if clip_slot < 0 or clip_slot >= len(target_slots):
            raise _invalid_argument(
                message=f"clip_slot out of range after load: {clip_slot}",
                hint="Use a valid clip slot index for the target track.",
            )
        target_slot = target_slots[clip_slot]
        if not bool(getattr(target_slot, "has_clip", False)):
            if require_existing_clip:
                raise _invalid_argument(
                    message="No clip in slot",
                    hint="Create a clip before importing browser MIDI notes.",
                )
            create_clip = getattr(target_slot, "create_clip", None)
            if not callable(create_clip):
                raise _not_supported_by_live_api(
                    message="Clip creation API is not available in Live API",
                    hint="Use a Live version exposing clip_slot.create_clip.",
                )
            source_length = max(float(getattr(source_clip, "length", 1.0)), 0.000001)
            create_clip(source_length)
        target_clip = getattr(target_slot, "clip", None)
        if target_clip is None:
            raise _invalid_argument(
                message="Target clip slot did not contain a clip after creation",
                hint="Retry with an existing or creatable MIDI clip slot.",
            )
        return target_clip

    def _load_midi_clip_to_temporary_track(self, *, song: Any, item: Any) -> tuple[int, Any]:
        base_track_count = len(list(getattr(song, "tracks", [])))
        create_midi_track = getattr(song, "create_midi_track", None)
        if not callable(create_midi_track):
            raise _not_supported_by_live_api(
                message="Track creation API is not available in Live API",
                hint="Use a Live version exposing song.create_midi_track.",
            )
        temporary_track_index = base_track_count
        create_midi_track(-1)
        temporary_track = self._track_at(temporary_track_index)

        view = getattr(song, "view", None)
        previous_selected_track = (
            getattr(view, "selected_track", None)
            if view is not None and hasattr(view, "selected_track")
            else None
        )
        self._select_track_for_load(song=song, target_track=temporary_track)
        try:
            try:
                self._browser().load_item(item)
            except Exception:
                self._cleanup_created_tracks(song=song, base_track_count=base_track_count)
                raise
        finally:
            if previous_selected_track is not None and view is not None:
                view.selected_track = previous_selected_track

        created_tracks, source_track = self._wait_for_created_clip_track(
            song=song,
            base_track_count=base_track_count,
        )
        if source_track is None:
            self._cleanup_created_tracks(song=song, base_track_count=base_track_count)
            self._raise_ambiguous_created_track_error(
                message="MIDI clip import did not create a deterministic source track",
                hint="Retry with a loadable .alc target from browser items/search.",
                created_tracks=created_tracks,
            )

        source_track_index = int(source_track["index"])
        reindexed_tracks = self._cleanup_created_tracks_except(
            song=song,
            base_track_count=base_track_count,
            keep_track_indices={source_track_index},
        )
        source_track_index = reindexed_tracks.get(source_track_index)
        current_tracks = list(getattr(song, "tracks", []))
        if source_track_index is None or source_track_index >= len(current_tracks):
            raise _invalid_argument(
                message="Imported source track was removed before note import",
                hint="Retry with a deterministic loadable MIDI clip target.",
            )

        source_clip = source_track["clip"]
        return source_track_index, source_clip

    def _rehome_loaded_midi_clip_if_needed(
        self,
        *,
        song: Any,
        item: Any,
        target_track: Any,
        target_track_mode: str,
        clip_slot: int | None,
        base_track_count: int,
    ) -> tuple[int, int] | None:
        if target_track_mode != "existing":
            return None
        if not self._is_midi_clip_browser_item(item):
            return None

        created_tracks = self._created_track_details(
            after=list(getattr(song, "tracks", [])),
            base_track_count=base_track_count,
        )
        if not created_tracks:
            return None

        clip_tracks = [track for track in created_tracks if bool(track["has_clip"])]
        if len(clip_tracks) != 1:
            self._cleanup_created_tracks(song=song, base_track_count=base_track_count)
            self._raise_ambiguous_created_track_error(
                message="Clip load created an ambiguous source track set",
                hint="Retry with a deterministic MIDI clip target track and slot.",
                created_tracks=created_tracks,
            )

        source_clip = clip_tracks[0]["clip"]
        if source_clip is None:
            self._cleanup_created_tracks(song=song, base_track_count=base_track_count)
            raise _invalid_argument(
                message="Loaded clip source track did not contain a clip",
                hint="Retry with a loadable MIDI clip target.",
            )

        try:
            destination_clip_slot = self._resolve_rehome_clip_slot(
                song=song,
                target_track=target_track,
                clip_slot=clip_slot,
            )
            target_clip = self._target_clip_for_import(
                target_track=target_track,
                clip_slot=destination_clip_slot,
                source_clip=source_clip,
                require_existing_clip=False,
            )
            imported_note_count = self._import_clip_notes(
                source_clip=source_clip,
                target_clip=target_clip,
                notes_mode="replace",
            )
            self._copy_clip_name(source_clip=source_clip, target_clip=target_clip)
            return imported_note_count, destination_clip_slot
        finally:
            self._cleanup_created_tracks(song=song, base_track_count=base_track_count)

    def load_instrument_or_effect(
        self,
        track: int,
        uri: str | None,
        path: str | None,
        target_track_mode: str = "auto",
        clip_slot: int | None = None,
        preserve_track_name: bool = False,
        notes_mode: str | None = None,
        import_length: bool = False,
        import_groove: bool = False,
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

        resolved_notes_mode = notes_mode.lower() if isinstance(notes_mode, str) else None
        if resolved_notes_mode is not None and resolved_notes_mode not in {"replace", "append"}:
            raise _invalid_argument(
                message=f"notes_mode must be one of replace/append, got {notes_mode}",
                hint="Use notes_mode replace or append.",
            )
        if resolved_notes_mode is None and (import_length or import_groove):
            raise _invalid_argument(
                message="import_length/import_groove require notes_mode",
                hint="Use notes_mode replace or append when importing clip length/groove.",
            )

        song = self._song()
        base_track_count = len(list(getattr(song, "tracks", [])))
        track_count_before = base_track_count
        target, resolved_track = self._resolve_load_target_track(
            track=track,
            target_track_mode=target_track_mode,
        )
        track_name_before = str(getattr(target, "name", "")) if preserve_track_name else None
        self._select_track_for_load(song=song, target_track=target)
        resolved_clip_slot = self._select_clip_slot_for_load(
            song=song,
            target_track=target,
            clip_slot=clip_slot,
        )
        imported_note_count: int | None = None
        length_imported: bool | None = None
        groove_imported: bool | None = None
        if resolved_notes_mode is None:
            self._browser().load_item(item)
            rehomed = self._rehome_loaded_midi_clip_if_needed(
                song=song,
                item=item,
                target_track=target,
                target_track_mode=target_track_mode,
                clip_slot=resolved_clip_slot,
                base_track_count=base_track_count,
            )
            if rehomed is not None:
                imported_note_count, resolved_clip_slot = rehomed
        else:
            if target_track_mode != "existing":
                raise _invalid_argument(
                    message="notes_mode requires target_track_mode=existing",
                    hint="Use --target-track-mode existing when importing notes.",
                )
            if resolved_clip_slot is None:
                raise _invalid_argument(
                    message="notes_mode requires clip_slot",
                    hint="Use --clip-slot to select the destination clip.",
                )
            if not self._is_midi_clip_browser_item(item):
                raise _invalid_argument(
                    message="notes_mode is supported only for MIDI clip (.alc) browser items",
                    hint="Choose a .alc target from browser search/items.",
                )
            source_track_index, source_clip = self._load_midi_clip_to_temporary_track(
                song=song,
                item=item,
            )
            try:
                target_clip = self._target_clip_for_import(
                    target_track=target,
                    clip_slot=resolved_clip_slot,
                    source_clip=source_clip,
                    require_existing_clip=True,
                )
                imported_note_count = self._import_clip_notes(
                    source_clip=source_clip,
                    target_clip=target_clip,
                    notes_mode=resolved_notes_mode,
                )
                self._copy_clip_name(source_clip=source_clip, target_clip=target_clip)
                length_imported = (
                    self._import_clip_length(source_clip=source_clip, target_clip=target_clip)
                    if import_length
                    else False
                )
                groove_imported = (
                    self._import_clip_groove(source_clip=source_clip, target_clip=target_clip)
                    if import_groove
                    else False
                )
            finally:
                self._delete_track(song, source_track_index)

        if track_name_before is not None and hasattr(target, "name"):
            target.name = track_name_before
        track_count_after = len(list(getattr(song, "tracks", [])))

        return {
            "track": resolved_track,
            "loaded": True,
            "item_name": str(getattr(item, "name", "")),
            "uri": uri,
            "path": serialized["path"],
            "clip_slot": resolved_clip_slot,
            "target_track_mode": target_track_mode,
            "preserve_track_name": preserve_track_name,
            "notes_mode": resolved_notes_mode,
            "import_length": import_length,
            "import_groove": import_groove,
            "notes_imported": imported_note_count,
            "length_imported": length_imported,
            "groove_imported": groove_imported,
            "track_name": str(getattr(target, "name", "")),
            "track_count": track_count_after,
            "track_count_delta": track_count_after - track_count_before,
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
