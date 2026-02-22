from __future__ import annotations

from time import perf_counter
from typing import Any

from .base import _invalid_argument

_ALLOWED_ITEM_TYPES = frozenset({"all", "folder", "device", "loadable"})


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
