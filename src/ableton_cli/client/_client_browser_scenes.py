from __future__ import annotations

from typing import Any


class _AbletonClientBrowserScenesMixin:
    def _build_arrangement_clip_note_args(
        self,
        *,
        track: int,
        index: int,
        notes: list[dict[str, Any]] | None,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "index": index}
        self._add_if_not_none(args, "notes", notes)
        self._add_if_not_none(args, "start_time", start_time)
        self._add_if_not_none(args, "end_time", end_time)
        self._add_if_not_none(args, "pitch", pitch)
        return args

    def load_instrument_or_effect(
        self,
        track: int,
        uri: str | None = None,
        path: str | None = None,
        target_track_mode: str = "auto",
        clip_slot: int | None = None,
        preserve_track_name: bool = False,
        notes_mode: str | None = None,
        import_length: bool | None = None,
        import_groove: bool | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "track": track,
            "target_track_mode": target_track_mode,
            "preserve_track_name": preserve_track_name,
        }
        self._add_if_not_none(args, "uri", uri)
        self._add_if_not_none(args, "path", path)
        self._add_if_not_none(args, "clip_slot", clip_slot)
        self._add_if_not_none(args, "notes_mode", notes_mode)
        self._add_if_not_none(args, "import_length", import_length)
        self._add_if_not_none(args, "import_groove", import_groove)
        return self._call("load_instrument_or_effect", args)

    def get_browser_tree(self, category_type: str = "all") -> dict[str, Any]:
        return self._call("get_browser_tree", {"category_type": category_type})

    def get_browser_items_at_path(self, path: str) -> dict[str, Any]:
        return self._call("get_browser_items_at_path", {"path": path})

    def get_browser_item(self, uri: str | None, path: str | None) -> dict[str, Any]:
        args: dict[str, Any] = {}
        self._add_if_not_none(args, "uri", uri)
        self._add_if_not_none(args, "path", path)
        return self._call("get_browser_item", args)

    def get_browser_categories(self, category_type: str = "all") -> dict[str, Any]:
        return self._call("get_browser_categories", {"category_type": category_type})

    def get_browser_items(
        self,
        path: str,
        item_type: str = "all",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self._call(
            "get_browser_items",
            {"path": path, "item_type": item_type, "limit": limit, "offset": offset},
        )

    def search_browser_items(
        self,
        query: str,
        path: str | None = None,
        item_type: str = "loadable",
        limit: int = 50,
        offset: int = 0,
        exact: bool = False,
        case_sensitive: bool = False,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "query": query,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "exact": exact,
            "case_sensitive": case_sensitive,
        }
        self._add_if_not_none(args, "path", path)
        return self._call("search_browser_items", args)

    def load_drum_kit(
        self,
        track: int,
        rack_uri: str,
        kit_uri: str | None,
        kit_path: str | None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "rack_uri": rack_uri}
        self._add_if_not_none(args, "kit_uri", kit_uri)
        self._add_if_not_none(args, "kit_path", kit_path)
        return self._call("load_drum_kit", args)

    def scenes_list(self) -> dict[str, Any]:
        return self._call("scenes_list")

    def create_scene(self, index: int) -> dict[str, Any]:
        return self._call("create_scene", {"index": index})

    def set_scene_name(self, scene: int, name: str) -> dict[str, Any]:
        return self._call("set_scene_name", {"scene": scene, "name": name})

    def fire_scene(self, scene: int) -> dict[str, Any]:
        return self._call("fire_scene", {"scene": scene})

    def scenes_move(self, from_index: int, to_index: int) -> dict[str, Any]:
        return self._call("scenes_move", {"from": from_index, "to": to_index})

    def stop_all_clips(self) -> dict[str, Any]:
        return self._call("stop_all_clips")

    def arrangement_record_start(self) -> dict[str, Any]:
        return self._call("arrangement_record_start")

    def arrangement_record_stop(self) -> dict[str, Any]:
        return self._call("arrangement_record_stop")

    def arrangement_clip_create(
        self,
        track: int,
        start_time: float,
        length: float,
        audio_path: str | None,
        notes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "track": track,
            "start_time": start_time,
            "length": length,
        }
        self._add_if_not_none(args, "audio_path", audio_path)
        self._add_if_not_none(args, "notes", notes)
        return self._call("arrangement_clip_create", args)

    def arrangement_clip_list(self, track: int | None) -> dict[str, Any]:
        args: dict[str, Any] = {}
        self._add_if_not_none(args, "track", track)
        return self._call("arrangement_clip_list", args)

    def arrangement_clip_notes_add(
        self,
        track: int,
        index: int,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        args = self._build_arrangement_clip_note_args(
            track=track,
            index=index,
            notes=notes,
            start_time=None,
            end_time=None,
            pitch=None,
        )
        return self._call("arrangement_clip_notes_add", args)

    def arrangement_clip_notes_get(
        self,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args = self._build_arrangement_clip_note_args(
            track=track,
            index=index,
            notes=None,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return self._call("arrangement_clip_notes_get", args)

    def arrangement_clip_notes_clear(
        self,
        track: int,
        index: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args = self._build_arrangement_clip_note_args(
            track=track,
            index=index,
            notes=None,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return self._call("arrangement_clip_notes_clear", args)

    def arrangement_clip_notes_replace(
        self,
        track: int,
        index: int,
        notes: list[dict[str, Any]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ) -> dict[str, Any]:
        args = self._build_arrangement_clip_note_args(
            track=track,
            index=index,
            notes=notes,
            start_time=start_time,
            end_time=end_time,
            pitch=pitch,
        )
        return self._call("arrangement_clip_notes_replace", args)

    def arrangement_clip_notes_import_browser(
        self,
        track: int,
        index: int,
        target_uri: str | None,
        target_path: str | None,
        mode: str,
        import_length: bool,
        import_groove: bool,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {
            "track": track,
            "index": index,
            "mode": mode,
            "import_length": import_length,
            "import_groove": import_groove,
        }
        self._add_if_not_none(args, "target_uri", target_uri)
        self._add_if_not_none(args, "target_path", target_path)
        return self._call("arrangement_clip_notes_import_browser", args)

    def arrangement_clip_delete(
        self,
        track: int,
        index: int | None,
        start: float | None,
        end: float | None,
        delete_all: bool,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "all": delete_all}
        self._add_if_not_none(args, "index", index)
        self._add_if_not_none(args, "start", start)
        self._add_if_not_none(args, "end", end)
        return self._call("arrangement_clip_delete", args)

    def arrangement_clip_props_get(self, track: int, index: int) -> dict[str, Any]:
        return self._call("arrangement_clip_props_get", {"track": track, "index": index})

    def arrangement_clip_loop_set(
        self,
        track: int,
        index: int,
        start: float,
        end: float,
        enabled: bool,
    ) -> dict[str, Any]:
        return self._call(
            "arrangement_clip_loop_set",
            {"track": track, "index": index, "start": start, "end": end, "enabled": enabled},
        )

    def arrangement_clip_marker_set(
        self,
        track: int,
        index: int,
        start_marker: float,
        end_marker: float,
    ) -> dict[str, Any]:
        return self._call(
            "arrangement_clip_marker_set",
            {
                "track": track,
                "index": index,
                "start_marker": start_marker,
                "end_marker": end_marker,
            },
        )

    def arrangement_clip_warp_get(self, track: int, index: int) -> dict[str, Any]:
        return self._call("arrangement_clip_warp_get", {"track": track, "index": index})

    def arrangement_clip_warp_set(
        self,
        track: int,
        index: int,
        enabled: bool,
        mode: str | None,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"track": track, "index": index, "enabled": enabled}
        self._add_if_not_none(args, "mode", mode)
        return self._call("arrangement_clip_warp_set", args)

    def arrangement_clip_gain_set(self, track: int, index: int, db: float) -> dict[str, Any]:
        return self._call(
            "arrangement_clip_gain_set",
            {"track": track, "index": index, "db": db},
        )

    def arrangement_clip_transpose_set(
        self,
        track: int,
        index: int,
        semitones: int,
    ) -> dict[str, Any]:
        return self._call(
            "arrangement_clip_transpose_set",
            {"track": track, "index": index, "semitones": semitones},
        )

    def arrangement_clip_file_replace(
        self,
        track: int,
        index: int,
        audio_path: str,
    ) -> dict[str, Any]:
        return self._call(
            "arrangement_clip_file_replace",
            {"track": track, "index": index, "audio_path": audio_path},
        )

    def arrangement_from_session(self, scenes: list[dict[str, float]]) -> dict[str, Any]:
        return self._call("arrangement_from_session", {"scenes": scenes})

    def tracks_delete(self, track: int) -> dict[str, Any]:
        return self._call("tracks_delete", {"track": track})
