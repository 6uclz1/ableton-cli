from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .base import _invalid_argument


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
