from __future__ import annotations

from typing import Any

from .live_backend_parts import (
    LiveBackendBaseMixin,
    LiveBackendBrowserCatalogMixin,
    LiveBackendBrowserLoadMixin,
    LiveBackendBrowserPathLookupMixin,
    LiveBackendBrowserReadMixin,
    LiveBackendBrowserSearchIndexMixin,
    LiveBackendBrowserSearchMixin,
    LiveBackendClipEnvelopesMixin,
    LiveBackendClipNotesMixin,
    LiveBackendDeviceRacksMixin,
    LiveBackendDeviceSharedMixin,
    LiveBackendEffectDevicesMixin,
    LiveBackendScenesArrangementMixin,
    LiveBackendSongSessionMixin,
    LiveBackendSynthDevicesMixin,
    LiveBackendTracksClipsMixin,
    LiveBackendTracksCutToDrumRackMixin,
    LiveBackendTransportMixerMixin,
)


class LiveBackend(
    LiveBackendEffectDevicesMixin,
    LiveBackendSynthDevicesMixin,
    LiveBackendDeviceRacksMixin,
    LiveBackendDeviceSharedMixin,
    LiveBackendBrowserSearchMixin,
    LiveBackendBrowserReadMixin,
    LiveBackendBrowserLoadMixin,
    LiveBackendBrowserSearchIndexMixin,
    LiveBackendBrowserPathLookupMixin,
    LiveBackendBrowserCatalogMixin,
    LiveBackendTracksCutToDrumRackMixin,
    LiveBackendClipEnvelopesMixin,
    LiveBackendClipNotesMixin,
    LiveBackendTracksClipsMixin,
    LiveBackendScenesArrangementMixin,
    LiveBackendTransportMixerMixin,
    LiveBackendSongSessionMixin,
    LiveBackendBaseMixin,
):
    def __init__(self, control_surface: Any) -> None:
        self._control_surface = control_surface
        self._browser_search_index_cache: dict[str, list[dict[str, Any]]] = {}
