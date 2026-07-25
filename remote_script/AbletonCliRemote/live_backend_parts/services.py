"""The eight backend domain services and the bundle that holds them.

Each service groups the mixins for one cohesive domain and is constructed
over the shared :class:`LiveBackendContext`. The per-file mixins remain the
unit of code organisation; the service is the unit of composition, and the
only thing a service can reach through the context.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import LiveBackendContext
from .browser_catalog import LiveBackendBrowserCatalogMixin
from .browser_load import LiveBackendBrowserLoadMixin
from .browser_path_lookup import LiveBackendBrowserPathLookupMixin
from .browser_read import LiveBackendBrowserReadMixin
from .browser_search import LiveBackendBrowserSearchMixin
from .browser_search_index import LiveBackendBrowserSearchIndexMixin
from .clip_envelopes import LiveBackendClipEnvelopesMixin
from .clip_notes import LiveBackendClipNotesMixin
from .devices import (
    LiveBackendDeviceSharedMixin,
    LiveBackendEffectDevicesMixin,
    LiveBackendSynthDevicesMixin,
)
from .devices_racks import LiveBackendDeviceRacksMixin
from .scenes_arrangement import LiveBackendScenesArrangementMixin
from .service import LiveBackendService
from .song_transport import LiveBackendSongSessionMixin, LiveBackendTransportMixerMixin
from .tracks_clips import LiveBackendTracksClipsMixin
from .tracks_clips_cut_to_drum_rack import LiveBackendTracksCutToDrumRackMixin


class SongTransportService(
    LiveBackendService,
    LiveBackendSongSessionMixin,
    LiveBackendTransportMixerMixin,
):
    """Song/session state, transport, mixer, tracks, returns and master."""


class TracksClipsService(
    LiveBackendService,
    LiveBackendTracksClipsMixin,
    LiveBackendTracksCutToDrumRackMixin,
):
    """Session clips, clip properties, warping and audio-to-drum-rack."""


class ClipNotesService(LiveBackendService, LiveBackendClipNotesMixin):
    """Reading and writing MIDI notes in session clips."""


class ClipEnvelopesService(LiveBackendService, LiveBackendClipEnvelopesMixin):
    """Clip automation envelopes."""


class ScenesArrangementService(LiveBackendService, LiveBackendScenesArrangementMixin):
    """Scenes plus everything on the arrangement timeline."""


class DevicesService(
    LiveBackendService,
    LiveBackendDeviceSharedMixin,
    LiveBackendSynthDevicesMixin,
    LiveBackendEffectDevicesMixin,
):
    """Device listing/parameters and the standard synth/effect surfaces."""


class DeviceRacksService(LiveBackendService, LiveBackendDeviceRacksMixin):
    """Rack chains and macros."""


class BrowserService(
    LiveBackendService,
    LiveBackendBrowserCatalogMixin,
    LiveBackendBrowserPathLookupMixin,
    LiveBackendBrowserSearchIndexMixin,
    LiveBackendBrowserReadMixin,
    LiveBackendBrowserSearchMixin,
    LiveBackendBrowserLoadMixin,
):
    """Live browser reads, search and loading."""


@dataclass(frozen=True, slots=True)
class BackendServices:
    """Every service, reachable by the name used in cross-service calls."""

    song_transport: SongTransportService
    tracks_clips: TracksClipsService
    clip_notes: ClipNotesService
    clip_envelopes: ClipEnvelopesService
    scenes_arrangement: ScenesArrangementService
    devices: DevicesService
    device_racks: DeviceRacksService
    browser: BrowserService

    def all(self) -> tuple[LiveBackendService, ...]:
        return (
            self.song_transport,
            self.tracks_clips,
            self.clip_notes,
            self.clip_envelopes,
            self.scenes_arrangement,
            self.devices,
            self.device_racks,
            self.browser,
        )


def build_services(context: LiveBackendContext) -> BackendServices:
    services = BackendServices(
        song_transport=SongTransportService(context),
        tracks_clips=TracksClipsService(context),
        clip_notes=ClipNotesService(context),
        clip_envelopes=ClipEnvelopesService(context),
        scenes_arrangement=ScenesArrangementService(context),
        devices=DevicesService(context),
        device_racks=DeviceRacksService(context),
        browser=BrowserService(context),
    )
    context.bind_services(services)
    return services
