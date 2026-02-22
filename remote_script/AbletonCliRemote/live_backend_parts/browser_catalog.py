from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from .base import _invalid_argument


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
        normalized = value.strip()
        for _ in range(4):
            decoded = unquote(normalized)
            if decoded == normalized:
                break
            normalized = decoded
        return normalized

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
