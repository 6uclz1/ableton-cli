from __future__ import annotations

from typing import Any


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
