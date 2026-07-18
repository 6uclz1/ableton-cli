from __future__ import annotations

from typing import Any

from .base import _invalid_argument


class LiveBackendBrowserReadMixin:
    """Browser catalog reading: category trees, folder listings, and
    single-item lookups by URI/path. Loading an item into a track lives in
    ``LiveBackendBrowserLoadMixin`` (``browser_load.py``); this mixin never
    mutates the Live Set.
    """

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
