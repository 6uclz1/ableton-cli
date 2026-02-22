from __future__ import annotations

from typing import Any


class _AbletonClientBrowserScenesMixin:
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

    def tracks_delete(self, track: int) -> dict[str, Any]:
        return self._call("tracks_delete", {"track": track})
