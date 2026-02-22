from __future__ import annotations

from ._client_browser_scenes import _AbletonClientBrowserScenesMixin
from ._client_core import _AbletonClientCore
from ._client_devices import _AbletonClientDevicesMixin
from ._client_song_transport import _AbletonClientSongTransportMixin
from ._client_tracks_clips import _AbletonClientTracksClipsMixin


class AbletonClient(
    _AbletonClientDevicesMixin,
    _AbletonClientBrowserScenesMixin,
    _AbletonClientTracksClipsMixin,
    _AbletonClientSongTransportMixin,
    _AbletonClientCore,
):
    pass
