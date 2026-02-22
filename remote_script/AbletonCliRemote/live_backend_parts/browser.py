from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter
from typing import Any
from urllib.parse import unquote

from .base import _invalid_argument, _not_supported_by_live_api

_ALLOWED_ITEM_TYPES = frozenset({"all", "folder", "device", "loadable"})
_ALLOWED_TARGET_TRACK_MODES = frozenset({"auto", "existing", "new"})


class LiveBackendBrowserCatalogMixin:
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


class LiveBackendBrowserPathLookupMixin:
    def _split_browser_path(self, path: str) -> list[str]:
        parts = [part for part in path.split("/") if part]
        if not parts:
            raise _invalid_argument(
                message="path must not be empty",
                hint="Use a path like 'drums/Kits'.",
            )
        return parts

    def _resolve_browser_root(self, root_name: str, categories: dict[str, Any]) -> Any:
        root = categories.get(root_name.lower())
        if root is not None:
            return root
        available = ", ".join(sorted(categories.keys()))
        raise _invalid_argument(
            message=f"Unknown or unavailable category: {root_name}",
            hint=f"Available categories: {available}",
        )

    def _find_named_child(self, parent: Any, expected_name: str) -> Any:
        for child in list(getattr(parent, "children", []) or []):
            if str(getattr(child, "name", "")).lower() == expected_name.lower():
                return child
        raise _invalid_argument(
            message=f"Path part '{expected_name}' not found",
            hint="Use browser tree/items commands to inspect available paths.",
        )

    def _resolve_browser_path(self, path: str) -> Any:
        parts = self._split_browser_path(path)
        categories = self._browser_category_map()
        current = self._resolve_browser_root(parts[0], categories)
        for part in parts[1:]:
            current = self._find_named_child(current, part)
        return current

    def _iterate_items_with_path(self) -> Iterable[tuple[Any, str]]:
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
                yield item, path
                children = list(getattr(item, "children", []) or [])
                for child in children:
                    child_name = str(getattr(child, "name", "")).strip()
                    child_path = f"{path}/{child_name}" if child_name else path
                    stack.append((child, child_path))

    def _find_browser_item_by_uri(self, uri: str) -> Any | None:
        for item, _path in self._iterate_items_with_path():
            if self._uri_matches(getattr(item, "uri", None), uri):
                return item
        return None

    def _item_path_by_uri(self, uri: str) -> str | None:
        for item, path in self._iterate_items_with_path():
            if self._uri_matches(getattr(item, "uri", None), uri):
                return path
        return None


class LiveBackendBrowserSearchIndexMixin:
    _browser_search_index_cache: dict[str, list[dict[str, Any]]]

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
        before: list[Any],
        after: list[Any],
    ) -> list[tuple[int, Any]]:
        before_ids = {id(track) for track in before}
        return [(index, track) for index, track in enumerate(after) if id(track) not in before_ids]

    @staticmethod
    def _first_track_clip(track: Any) -> tuple[int, Any] | None:
        for slot_index, slot in enumerate(list(getattr(track, "clip_slots", []))):
            if not bool(getattr(slot, "has_clip", False)):
                continue
            clip_obj = getattr(slot, "clip", None)
            if clip_obj is not None:
                return slot_index, clip_obj
        return None

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
        tracks_before_load = list(getattr(song, "tracks", []))
        view = getattr(song, "view", None)
        had_selected_scene = bool(view is not None and hasattr(view, "selected_scene"))
        previous_selected_scene = (
            getattr(view, "selected_scene", None) if had_selected_scene else None
        )
        if had_selected_scene:
            view.selected_scene = None
        try:
            self._browser().load_item(item)
        finally:
            if had_selected_scene:
                view.selected_scene = previous_selected_scene

        tracks_after_load = list(getattr(song, "tracks", []))
        created_tracks = self._created_tracks_since(
            before=tracks_before_load,
            after=tracks_after_load,
        )
        if len(created_tracks) != 1:
            raise _invalid_argument(
                message="MIDI clip import did not create a deterministic source track",
                hint="Retry with a loadable .alc target from browser items/search.",
            )
        source_track_index, source_track = created_tracks[0]
        source_clip_entry = self._first_track_clip(source_track)
        if source_clip_entry is None:
            raise _invalid_argument(
                message="Imported source track did not contain a clip",
                hint="Retry with a loadable MIDI clip target.",
            )
        _source_slot_index, source_clip = source_clip_entry
        return source_track_index, source_clip

    def _rehome_loaded_midi_clip_if_needed(
        self,
        *,
        song: Any,
        item: Any,
        target_track: Any,
        target_track_mode: str,
        clip_slot: int | None,
        tracks_before_load: list[Any],
    ) -> int | None:
        if target_track_mode != "existing":
            return None
        if clip_slot is None:
            return None
        if not self._is_midi_clip_browser_item(item):
            return None

        tracks_after_load = list(getattr(song, "tracks", []))
        created_tracks = self._created_tracks_since(
            before=tracks_before_load,
            after=tracks_after_load,
        )
        if not created_tracks:
            return None
        if len(created_tracks) != 1:
            raise _invalid_argument(
                message="Clip load created an unexpected number of tracks",
                hint="Retry with a deterministic MIDI clip target track and slot.",
            )

        source_track_index, source_track = created_tracks[0]
        source_clip_entry = self._first_track_clip(source_track)
        if source_clip_entry is None:
            raise _invalid_argument(
                message="Loaded clip track did not contain a clip",
                hint="Retry with a loadable MIDI clip target.",
            )
        _source_slot_index, source_clip = source_clip_entry

        target_clip = self._target_clip_for_import(
            target_track=target_track,
            clip_slot=clip_slot,
            source_clip=source_clip,
            require_existing_clip=False,
        )
        imported_note_count = self._import_clip_notes(
            source_clip=source_clip,
            target_clip=target_clip,
            notes_mode="replace",
        )
        if hasattr(target_clip, "name"):
            target_clip.name = str(getattr(source_clip, "name", ""))

        self._delete_track(song, source_track_index)
        return imported_note_count

    def load_instrument_or_effect(
        self,
        track: int,
        uri: str | None,
        path: str | None,
        target_track_mode: str = "auto",
        clip_slot: int | None = None,
        preserve_track_name: bool = False,
        notes_mode: str | None = None,
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

        song = self._song()
        tracks_before_load = list(getattr(song, "tracks", []))
        track_count_before = len(list(getattr(song, "tracks", [])))
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
            imported_note_count = self._rehome_loaded_midi_clip_if_needed(
                song=song,
                item=item,
                target_track=target,
                target_track_mode=target_track_mode,
                clip_slot=resolved_clip_slot,
                tracks_before_load=tracks_before_load,
            )
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
                if hasattr(target_clip, "name"):
                    target_clip.name = str(getattr(source_clip, "name", ""))
            finally:
                self._delete_track(song, source_track_index)
            length_imported = False
            groove_imported = False

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


class LiveBackendBrowserSearchMixin:
    def _validate_paging(self, *, limit: int, offset: int) -> None:
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

    def _validate_item_type(self, item_type: str) -> None:
        if item_type not in _ALLOWED_ITEM_TYPES:
            raise _invalid_argument(
                message=f"item_type must be one of all/folder/device/loadable, got {item_type}",
                hint="Use a supported item type.",
            )

    def _filter_browser_items_by_type(
        self,
        items: list[dict[str, Any]],
        item_type: str,
    ) -> list[dict[str, Any]]:
        if item_type == "all":
            return list(items)
        return [item for item in items if self._item_matches_type(item, item_type)]

    def get_browser_items(
        self,
        path: str,
        item_type: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        self._validate_item_type(item_type)
        self._validate_paging(limit=limit, offset=offset)

        started_at = perf_counter()
        result = self.get_browser_items_at_path(path)
        filtered = self._filter_browser_items_by_type(list(result["items"]), item_type)

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

    def _ranked_search_matches(
        self,
        *,
        candidates: list[dict[str, Any]],
        query: str,
        item_type: str,
        exact: bool,
        case_sensitive: bool,
    ) -> list[tuple[int, dict[str, Any]]]:
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
        return matches

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

        self._validate_item_type(item_type)
        self._validate_paging(limit=limit, offset=offset)

        started_at = perf_counter()
        candidates = self._browser_search_candidates(path)
        matches = self._ranked_search_matches(
            candidates=candidates,
            query=query,
            item_type=item_type,
            exact=exact,
            case_sensitive=case_sensitive,
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
        resolved_kit_uri: str
        resolved_kit_path: str | None
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
