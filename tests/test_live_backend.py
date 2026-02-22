from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from remote_script.AbletonCliRemote.command_backend import CommandError
from remote_script.AbletonCliRemote.live_backend import LiveBackend


@dataclass(slots=True)
class _Value:
    value: float


@dataclass(slots=True)
class _Mixer:
    volume: _Value
    panning: _Value


@dataclass(slots=True)
class _Parameter:
    name: str
    value: float
    min: float = 0.0
    max: float = 1.0
    is_enabled: bool = True
    is_quantized: bool = False


@dataclass(slots=True)
class _Device:
    name: str
    class_name: str
    parameters: list[_Parameter]
    can_have_drum_pads: bool = False
    can_have_chains: bool = False
    class_display_name: str = ""

    def __post_init__(self) -> None:
        if not self.class_display_name:
            self.class_display_name = self.class_name


@dataclass(slots=True)
class _MidiNote:
    note_id: int
    pitch: int
    start_time: float
    duration: float
    velocity: int
    mute: bool


class _Clip:
    def __init__(self, length: float, name: str = "") -> None:
        self.name = name or "Clip"
        self.length = float(length)
        self.is_playing = False
        self.is_recording = False
        self.muted = False
        self._notes: list[_MidiNote] = []
        self._next_note_id = 1

    @property
    def notes(self) -> tuple[tuple[int, float, float, int, bool], ...]:
        return tuple(
            (
                int(note.pitch),
                float(note.start_time),
                float(note.duration),
                int(note.velocity),
                bool(note.mute),
            )
            for note in self._notes
        )

    def set_notes(self, notes: tuple[tuple[int, float, float, int, bool], ...]) -> None:
        for note in notes:
            pitch, start_time, duration, velocity, mute = note
            self._notes.append(
                _MidiNote(
                    note_id=self._next_note_id,
                    pitch=int(pitch),
                    start_time=float(start_time),
                    duration=float(duration),
                    velocity=int(velocity),
                    mute=bool(mute),
                )
            )
            self._next_note_id += 1

    def get_notes_extended(
        self,
        from_pitch: int = 0,
        pitch_span: int = 128,
        from_time: float = 0.0,
        time_span: float | None = None,
    ) -> list[_MidiNote]:
        to_pitch = from_pitch + pitch_span
        to_time = None if time_span is None else from_time + time_span
        payload: list[_MidiNote] = []
        for note in self._notes:
            pitch = int(note.pitch)
            start_time = float(note.start_time)
            if pitch < from_pitch or pitch >= to_pitch:
                continue
            if start_time < from_time:
                continue
            if to_time is not None and start_time >= to_time:
                continue
            payload.append(note)
        return payload

    def remove_notes_by_id(self, note_ids: list[int]) -> None:
        remove_set = {int(value) for value in note_ids}
        self._notes = [note for note in self._notes if int(note.note_id) not in remove_set]


class _ClipSlot:
    def __init__(self) -> None:
        self.clip: _Clip | None = None

    @property
    def has_clip(self) -> bool:
        return self.clip is not None

    def create_clip(self, length: float) -> None:
        if self.has_clip:
            raise RuntimeError("slot occupied")
        self.clip = _Clip(length=length)

    def fire(self) -> None:
        if not self.has_clip:
            raise RuntimeError("missing clip")
        assert self.clip is not None
        self.clip.is_playing = True

    def stop(self) -> None:
        if not self.has_clip:
            return
        assert self.clip is not None
        self.clip.is_playing = False


@dataclass(slots=True)
class _Track:
    name: str
    has_audio_input: bool
    has_midi_input: bool
    mute: bool = False
    solo: bool = False
    arm: bool = False
    mixer_device: _Mixer = field(
        default_factory=lambda: _Mixer(volume=_Value(0.75), panning=_Value(0.0))
    )
    clip_slots: list[_ClipSlot] = field(default_factory=lambda: [_ClipSlot(), _ClipSlot()])
    devices: list[_Device] = field(
        default_factory=lambda: [_Device("Utility", "AudioEffect", [_Parameter("Gain", 0.0)])]
    )


@dataclass(slots=True)
class _BrowserItem:
    name: str
    uri: str
    is_device: bool = False
    is_loadable: bool = False
    children: list[_BrowserItem] = field(default_factory=list)

    @property
    def is_folder(self) -> bool:
        return bool(self.children)


class _UriValue:
    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value


class _Browser:
    def __init__(self, song: _Song) -> None:
        self._song = song
        self.instruments = _BrowserItem(
            name="Instruments",
            uri="cat:instruments",
            children=[
                _BrowserItem(name="Synth", uri="inst:synth", is_device=True, is_loadable=True),
            ],
        )
        self.sounds = _BrowserItem(
            name="Sounds",
            uri="cat:sounds",
            children=[
                _BrowserItem(
                    name="Bass Loop.alc",
                    uri="clip:bass-loop-alc",
                    is_device=False,
                    is_loadable=True,
                )
            ],
        )
        self.drums = _BrowserItem(
            name="Drums",
            uri="cat:drums",
            children=[
                _BrowserItem(
                    name="Rack",
                    uri="rack:drums",
                    is_device=True,
                    is_loadable=True,
                ),
                _BrowserItem(
                    name="Kits",
                    uri="folder:kits",
                    children=[
                        _BrowserItem(
                            name="Acoustic Kit",
                            uri="kit:acoustic",
                            is_device=True,
                            is_loadable=True,
                        )
                    ],
                ),
            ],
        )
        self.audio_effects = _BrowserItem(name="Audio Effects", uri="cat:audio", children=[])
        self.midi_effects = _BrowserItem(name="MIDI Effects", uri="cat:midi", children=[])

    def load_item(self, item: _BrowserItem) -> None:
        uri = str(getattr(item, "uri", ""))
        if uri.startswith("clip:"):
            selected_scene = self._song.view.selected_scene
            if selected_scene is None:
                self._song.tracks.append(
                    _Track(name=str(item.name), has_audio_input=False, has_midi_input=True)
                )
                return

            target_track = self._song.view.selected_track
            scene_index = list(self._song.scenes).index(selected_scene)
            while scene_index >= len(target_track.clip_slots):
                target_track.clip_slots.append(_ClipSlot())
            slot = target_track.clip_slots[scene_index]
            if not slot.has_clip:
                slot.create_clip(length=1.0)
            target_track.name = str(item.name)
            return

        target = self._song.view.selected_track
        target.devices.append(
            _Device(
                name=item.name,
                class_name="LoadedDevice",
                parameters=[_Parameter("Macro 1", 0.5)],
            )
        )


@dataclass(slots=True)
class _SongView:
    selected_track: _Track
    selected_scene: _Scene | None = None
    highlighted_clip_slot: _ClipSlot | None = None


class _Song:
    def __init__(self) -> None:
        self.tempo = 120.0
        self.is_playing = False
        self.current_song_time = 4.0
        self.signature_numerator = 4
        self.signature_denominator = 4
        self.tracks = [
            _Track(name="Track 1", has_audio_input=False, has_midi_input=True),
            _Track(name="Track 2", has_audio_input=True, has_midi_input=False),
        ]
        self.return_tracks: list[_Track] = []
        self.scenes = [_Scene("Scene 1"), _Scene("Scene 2")]
        self.master_track = _Track(
            name="Master",
            has_audio_input=False,
            has_midi_input=False,
            clip_slots=[],
            devices=[],
        )
        self.view = _SongView(selected_track=self.tracks[0], selected_scene=self.scenes[0])
        self.stop_all_clips_calls = 0

    def start_playing(self) -> None:
        self.is_playing = True

    def stop_playing(self) -> None:
        self.is_playing = False

    def stop_all_clips(self) -> None:
        self.stop_all_clips_calls += 1

    def create_midi_track(self, index: int) -> None:
        target = _Track(name="MIDI", has_audio_input=False, has_midi_input=True)
        if index == -1:
            self.tracks.append(target)
            return
        self.tracks.insert(index, target)

    def create_audio_track(self, index: int) -> None:
        target = _Track(name="Audio", has_audio_input=True, has_midi_input=False)
        if index == -1:
            self.tracks.append(target)
            return
        self.tracks.insert(index, target)

    def create_scene(self, index: int) -> None:
        target = _Scene("Scene")
        self.scenes.insert(index, target)

    def delete_track(self, index: int) -> None:
        del self.tracks[index]

    def move_scene(self, from_index: int, to_index: int) -> None:
        scene = self.scenes.pop(from_index)
        self.scenes.insert(to_index, scene)


class _EventuallyConsistentSong(_Song):
    def __init__(self) -> None:
        self._actual_is_playing = False
        self._reported_is_playing = False
        self._stale_reads_remaining = 0
        super().__init__()

    @property
    def is_playing(self) -> bool:
        if self._stale_reads_remaining > 0:
            self._stale_reads_remaining -= 1
            return bool(self._reported_is_playing)
        self._reported_is_playing = bool(self._actual_is_playing)
        return bool(self._actual_is_playing)

    @is_playing.setter
    def is_playing(self, value: bool) -> None:
        state = bool(value)
        self._actual_is_playing = state
        self._reported_is_playing = state
        self._stale_reads_remaining = 0

    def start_playing(self) -> None:
        self._actual_is_playing = True
        self._stale_reads_remaining = 1

    def stop_playing(self) -> None:
        self._actual_is_playing = False
        self._stale_reads_remaining = 1


@dataclass(slots=True)
class _Scene:
    name: str
    fired: bool = False

    def fire(self) -> None:
        self.fired = True


class _Application:
    def __init__(self, song: _Song) -> None:
        self.browser = _Browser(song)


class _SurfaceStub:
    def __init__(self) -> None:
        self._song_obj = _Song()
        self._app = _Application(self._song_obj)

    def song(self) -> _Song:
        return self._song_obj

    def application(self) -> _Application:
        return self._app


class _EventuallyConsistentSurfaceStub(_SurfaceStub):
    def __init__(self) -> None:
        self._song_obj = _EventuallyConsistentSong()
        self._app = _Application(self._song_obj)


def _note() -> dict[str, Any]:
    return {
        "pitch": 60,
        "start_time": 0.0,
        "duration": 0.5,
        "velocity": 100,
        "mute": False,
    }


def _synth_parameters_for(synth_type: str) -> list[_Parameter]:
    if synth_type == "wavetable":
        return [
            _Parameter("Filter 1 Freq", 0.5, min=0.0, max=1.0),
            _Parameter("Filter 1 Res", 0.2, min=0.0, max=1.0),
            _Parameter("Amp Attack", 0.1, min=0.0, max=1.0),
            _Parameter("Amp Decay", 0.2, min=0.0, max=1.0),
            _Parameter("Amp Sustain", 0.8, min=0.0, max=1.0),
            _Parameter("Amp Release", 0.3, min=0.0, max=1.0),
            _Parameter("Osc 1 Pos", 0.4, min=0.0, max=1.0),
            _Parameter("Osc 2 Pos", 0.6, min=0.0, max=1.0),
            _Parameter("Unison Amount", 0.2, min=0.0, max=1.0),
        ]
    if synth_type == "drift":
        return [
            _Parameter("LP Freq", 0.5, min=0.0, max=1.0),
            _Parameter("LP Reso", 0.2, min=0.0, max=1.0),
            _Parameter("Env 1 Attack", 0.1, min=0.0, max=1.0),
            _Parameter("Env 1 Decay", 0.2, min=0.0, max=1.0),
            _Parameter("Env 1 Sustain", 0.8, min=0.0, max=1.0),
            _Parameter("Env 1 Release", 0.3, min=0.0, max=1.0),
            _Parameter("Osc 1 Shape", 3.0, min=0.0, max=7.0, is_quantized=True),
            _Parameter("Osc 2 Wave", 2.0, min=0.0, max=7.0, is_quantized=True),
            _Parameter("Drift", 0.35, min=0.0, max=1.0),
        ]
    if synth_type == "meld":
        return [
            _Parameter("A Filter Freq", 0.5, min=0.0, max=1.0),
            _Parameter("A Filter Q", 0.2, min=0.0, max=1.0),
            _Parameter("A Amp Attack", 0.1, min=0.0, max=1.0),
            _Parameter("A Amp Decay", 0.2, min=0.0, max=1.0),
            _Parameter("A Amp Sustain", 0.8, min=0.0, max=1.0),
            _Parameter("A Amp Release", 0.3, min=0.0, max=1.0),
            _Parameter("B Volume", 0.5, min=0.0, max=1.0),
            _Parameter("A Osc Tone", 0.3, min=0.0, max=1.0),
            _Parameter("Voice Spread", 0.25, min=0.0, max=1.0),
        ]
    raise AssertionError(f"unsupported synth_type for tests: {synth_type}")


def _set_track_device_to_synth(
    surface: _SurfaceStub, *, track: int, device: int, synth_type: str
) -> None:
    target_track = surface.song().tracks[track]
    synth_name = synth_type.capitalize()
    synth_device = _Device(
        name=synth_name,
        class_name=synth_name,
        parameters=_synth_parameters_for(synth_type),
        class_display_name=synth_name,
    )
    target_track.devices[device] = synth_device


def _effect_parameters_for(effect_type: str) -> list[_Parameter]:
    if effect_type == "eq8":
        return [
            _Parameter("1 Frequency A", 0.5, min=0.0, max=1.0),
            _Parameter("1 Gain A", 0.2, min=0.0, max=1.0),
            _Parameter("1 Q A", 0.3, min=0.0, max=1.0),
            _Parameter("LowCut Frequency", 0.15, min=0.0, max=1.0),
            _Parameter("HighCut Frequency", 0.85, min=0.0, max=1.0),
        ]
    if effect_type == "limiter":
        return [
            _Parameter("Gain", 0.5, min=0.0, max=1.0),
            _Parameter("Ceiling", 0.8, min=0.0, max=1.0),
            _Parameter("Release", 0.2, min=0.0, max=1.0),
            _Parameter("Lookahead", 1.0, min=0.0, max=2.0, is_quantized=True),
            _Parameter("Soft Clip", 0.0, min=0.0, max=1.0, is_quantized=True),
        ]
    if effect_type == "compressor":
        return [
            _Parameter("Threshold", 0.45, min=0.0, max=1.0),
            _Parameter("Ratio", 0.35, min=0.0, max=1.0),
            _Parameter("Attack", 0.1, min=0.0, max=1.0),
            _Parameter("Release", 0.2, min=0.0, max=1.0),
            _Parameter("Makeup", 0.3, min=0.0, max=1.0),
        ]
    if effect_type == "auto_filter":
        return [
            _Parameter("Frequency", 0.5, min=0.0, max=1.0),
            _Parameter("Resonance", 0.2, min=0.0, max=1.0),
            _Parameter("Env Amount", 0.3, min=0.0, max=1.0),
            _Parameter("LFO Amount", 0.4, min=0.0, max=1.0),
            _Parameter("LFO Rate", 0.5, min=0.0, max=1.0),
        ]
    if effect_type == "reverb":
        return [
            _Parameter("Decay Time", 0.6, min=0.0, max=1.0),
            _Parameter("PreDelay", 0.1, min=0.0, max=1.0),
            _Parameter("Size", 0.5, min=0.0, max=1.0),
            _Parameter("LowCut", 0.2, min=0.0, max=1.0),
            _Parameter("HighCut", 0.8, min=0.0, max=1.0),
        ]
    if effect_type == "utility":
        return [
            _Parameter("Gain", 0.5, min=0.0, max=1.0),
            _Parameter("Width", 0.7, min=0.0, max=1.0),
            _Parameter("Balance", 0.5, min=0.0, max=1.0),
            _Parameter("Bass Mono", 1.0, min=0.0, max=1.0, is_quantized=True),
            _Parameter("Bass Mono Frequency", 0.35, min=0.0, max=1.0),
        ]
    raise AssertionError(f"unsupported effect_type for tests: {effect_type}")


def _set_track_device_to_effect(
    surface: _SurfaceStub, *, track: int, device: int, effect_type: str
) -> None:
    target_track = surface.song().tracks[track]
    effect_name_map = {
        "eq8": "EQ Eight",
        "limiter": "Limiter",
        "compressor": "Compressor",
        "auto_filter": "Auto Filter",
        "reverb": "Reverb",
        "utility": "Utility",
    }
    effect_name = effect_name_map[effect_type]
    effect_device = _Device(
        name=effect_name,
        class_name=effect_name,
        parameters=_effect_parameters_for(effect_type),
        class_display_name=effect_name,
    )
    target_track.devices[device] = effect_device


def test_live_backend_ping_info_reports_api_support_matrix() -> None:
    backend = LiveBackend(_SurfaceStub())

    result = backend.ping_info()

    assert result["protocol_version"] == 2
    assert "remote_script_version" in result
    assert result["api_support"] == {
        "song_new_supported": False,
        "song_save_supported": False,
        "song_export_audio_supported": False,
        "arrangement_record_start_supported": False,
        "arrangement_record_stop_supported": False,
        "arrangement_record_supported": False,
    }


def test_live_backend_ping_info_reports_api_support_true_when_available() -> None:
    surface = _SurfaceStub()
    app = surface.application()
    song = surface.song()
    app.new_live_set = lambda: None
    app.save_live_set = lambda _path: None
    app.export_audio = lambda _path: None
    song.record_mode = False
    backend = LiveBackend(surface)

    result = backend.ping_info()

    assert result["api_support"] == {
        "song_new_supported": True,
        "song_save_supported": True,
        "song_export_audio_supported": True,
        "arrangement_record_start_supported": True,
        "arrangement_record_stop_supported": True,
        "arrangement_record_supported": True,
    }


def test_live_backend_transport_and_tempo() -> None:
    backend = LiveBackend(_SurfaceStub())

    assert backend.transport_play()["is_playing"] is True
    assert backend.transport_tempo_set(128.0)["tempo"] == 128.0
    assert backend.transport_tempo_get()["tempo"] == 128.0
    assert backend.stop_playback()["is_playing"] is False


def test_live_backend_transport_waits_for_committed_state() -> None:
    backend = LiveBackend(_EventuallyConsistentSurfaceStub())

    assert backend.transport_play()["is_playing"] is True
    assert backend.transport_stop()["is_playing"] is False


def test_live_backend_track_volume_set() -> None:
    backend = LiveBackend(_SurfaceStub())

    assert backend.track_volume_set(0, 0.5) == {"track": 0, "volume": 0.5}
    assert backend.track_volume_get(0) == {"track": 0, "volume": 0.5}


def test_live_backend_session_and_track_info() -> None:
    backend = LiveBackend(_SurfaceStub())

    session = backend.get_session_info()
    assert session["track_count"] == 2

    track_info = backend.get_track_info(0)
    assert track_info["index"] == 0
    assert track_info["name"] == "Track 1"
    assert len(track_info["clip_slots"]) == 2


def test_live_backend_session_snapshot() -> None:
    backend = LiveBackend(_SurfaceStub())

    snapshot = backend.session_snapshot()
    assert snapshot["song_info"]["tempo"] == 120.0
    assert snapshot["session_info"]["track_count"] == 2
    assert snapshot["tracks_list"]["tracks"][0]["index"] == 0
    assert snapshot["scenes_list"]["scenes"][0]["index"] == 0


def test_live_backend_track_creation_and_rename() -> None:
    backend = LiveBackend(_SurfaceStub())

    midi = backend.create_midi_track(-1)
    audio = backend.create_audio_track(1)
    renamed = backend.set_track_name(0, "Lead")

    assert midi["kind"] == "midi"
    assert audio["kind"] == "audio"
    assert renamed == {"track": 0, "name": "Lead"}


def test_live_backend_clip_lifecycle() -> None:
    backend = LiveBackend(_SurfaceStub())

    assert backend.create_clip(0, 0, 4.0)["length"] == 4.0
    assert backend.add_notes_to_clip(0, 0, [_note()]) == {"track": 0, "clip": 0, "note_count": 1}
    assert backend.set_clip_name(0, 0, "Hook") == {"track": 0, "clip": 0, "name": "Hook"}
    assert backend.fire_clip(0, 0) == {"track": 0, "clip": 0, "fired": True}
    assert backend.stop_clip(0, 0) == {"track": 0, "clip": 0, "stopped": True}


def test_live_backend_clip_active_toggle_is_non_destructive() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.create_clip(0, 0, 4.0)
    backend.add_notes_to_clip(0, 0, [_note()])

    assert backend.clip_active_get(0, 0) == {"track": 0, "clip": 0, "active": True}
    assert backend.clip_active_set(0, 0, False) == {"track": 0, "clip": 0, "active": False}
    assert backend.get_clip_notes(0, 0, None, None, None)["note_count"] == 1
    assert backend.clip_active_set(0, 0, True) == {"track": 0, "clip": 0, "active": True}
    assert backend.get_clip_notes(0, 0, None, None, None)["note_count"] == 1


def test_live_backend_browser_and_loading_operations() -> None:
    backend = LiveBackend(_SurfaceStub())

    tree = backend.get_browser_tree("all")
    assert "categories" in tree

    items = backend.get_browser_items_at_path("drums/Kits")
    assert items["path"] == "drums/Kits"
    assert items["items"]

    item = backend.get_browser_item(uri="inst:synth", path=None)
    assert item["found"] is True

    load = backend.load_instrument_or_effect(0, uri="inst:synth", path=None)
    assert load["loaded"] is True

    kit_load = backend.load_drum_kit(
        0,
        "rack:drums",
        kit_uri="kit:acoustic",
        kit_path=None,
    )
    assert kit_load["loaded"] is True


def test_live_backend_browser_items_supports_pagination() -> None:
    backend = LiveBackend(_SurfaceStub())

    result = backend.get_browser_items("drums/Kits", "loadable", limit=1, offset=0)
    assert result["item_type"] == "loadable"
    assert result["limit"] == 1
    assert result["offset"] == 0
    assert result["returned"] == 1
    assert result["total_matches"] >= 1
    assert "duration_ms" in result


def test_live_backend_browser_uri_lookup_accepts_stringable_uri_objects() -> None:
    surface = _SurfaceStub()
    surface.application().browser.instruments.children[0].uri = _UriValue("inst:synth")
    backend = LiveBackend(surface)

    item = backend.get_browser_item(uri="inst:synth", path=None)
    assert item["found"] is True
    load = backend.load_instrument_or_effect(0, uri="inst:synth", path=None)
    assert load["loaded"] is True


def test_live_backend_browser_uri_lookup_normalizes_percent_encoding() -> None:
    surface = _SurfaceStub()
    surface.application().browser.instruments.children[0].uri = "query:Synths#Drift%20Lead"
    backend = LiveBackend(surface)

    item = backend.get_browser_item(uri="query:Synths#Drift Lead", path=None)
    assert item["found"] is True
    load = backend.load_instrument_or_effect(0, uri="query:Synths#Drift Lead", path=None)
    assert load["loaded"] is True


def test_live_backend_browser_unknown_uri_is_deterministic_without_fallback() -> None:
    backend = LiveBackend(_SurfaceStub())
    uri = "query:Synths#Missing-Device"

    item = backend.get_browser_item(uri=uri, path=None)
    assert item == {"uri": uri, "path": None, "found": False}

    with pytest.raises(CommandError) as exc_info:
        backend.load_instrument_or_effect(0, uri=uri, path=None)
    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_live_backend_browser_search_matches_query_and_order() -> None:
    backend = LiveBackend(_SurfaceStub())

    result = backend.search_browser_items(
        query="kit",
        path=None,
        item_type="loadable",
        limit=50,
        offset=0,
        exact=False,
        case_sensitive=False,
    )

    assert result["query"] == "kit"
    assert result["returned"] == len(result["items"])
    assert result["total_matches"] >= result["returned"] >= 1
    names = [item["name"] for item in result["items"]]
    assert "Acoustic Kit" in names


def test_live_backend_browser_search_exact_and_case_sensitive() -> None:
    backend = LiveBackend(_SurfaceStub())

    lower = backend.search_browser_items(
        query="synth",
        path=None,
        item_type="loadable",
        limit=50,
        offset=0,
        exact=True,
        case_sensitive=True,
    )
    exact = backend.search_browser_items(
        query="Synth",
        path=None,
        item_type="loadable",
        limit=50,
        offset=0,
        exact=True,
        case_sensitive=True,
    )

    assert lower["returned"] == 0
    assert exact["returned"] == 1
    assert exact["items"][0]["name"] == "Synth"


def test_live_backend_browser_search_supports_path_filter_item_type_and_paging() -> None:
    backend = LiveBackend(_SurfaceStub())

    folder_only = backend.search_browser_items(
        query="kit",
        path="drums",
        item_type="folder",
        limit=50,
        offset=0,
        exact=False,
        case_sensitive=False,
    )
    loadable = backend.search_browser_items(
        query="kit",
        path="drums",
        item_type="loadable",
        limit=1,
        offset=0,
        exact=False,
        case_sensitive=False,
    )
    page_2 = backend.search_browser_items(
        query="kit",
        path="drums",
        item_type="loadable",
        limit=1,
        offset=1,
        exact=False,
        case_sensitive=False,
    )

    assert folder_only["items"][0]["path"] == "drums/Kits"
    assert folder_only["items"][0]["is_folder"] is True
    assert loadable["returned"] == 1
    assert loadable["has_more"] is False
    assert page_2["returned"] == 0
    assert page_2["has_more"] is False
    assert isinstance(loadable["duration_ms"], float)


def test_live_backend_load_with_path_and_non_loadable_path_rejected() -> None:
    backend = LiveBackend(_SurfaceStub())

    loaded = backend.load_instrument_or_effect(0, uri=None, path="instruments/Synth")
    assert loaded["loaded"] is True

    with pytest.raises(CommandError) as exc_info:
        backend.load_instrument_or_effect(0, uri=None, path="drums/Kits")
    assert "not loadable" in exc_info.value.message


def test_live_backend_load_existing_mode_targets_clip_slot_and_preserves_track_name() -> None:
    surface = _SurfaceStub()
    backend = LiveBackend(surface)

    loaded = backend.load_instrument_or_effect(
        0,
        uri=None,
        path="sounds/Bass Loop.alc",
        target_track_mode="existing",
        clip_slot=1,
        preserve_track_name=True,
    )

    target_track = surface.song().tracks[0]
    assert loaded["loaded"] is True
    assert loaded["track"] == 0
    assert loaded["clip_slot"] == 1
    assert loaded["target_track_mode"] == "existing"
    assert loaded["track_name"] == "Track 1"
    assert loaded["track_count"] == 2
    assert target_track.name == "Track 1"
    assert target_track.clip_slots[1].has_clip is True


def test_live_backend_load_existing_mode_rejects_invalid_clip_slot() -> None:
    backend = LiveBackend(_SurfaceStub())

    with pytest.raises(CommandError) as exc_info:
        backend.load_instrument_or_effect(
            0,
            uri=None,
            path="sounds/Bass Loop.alc",
            target_track_mode="existing",
            clip_slot=99,
            preserve_track_name=False,
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_live_backend_device_parameter_set() -> None:
    backend = LiveBackend(_SurfaceStub())
    result = backend.set_device_parameter(track=0, device=0, parameter=0, value=0.33)
    assert result == {"track": 0, "device": 0, "parameter": 0, "value": 0.33}


def test_live_backend_find_synth_devices_with_filters() -> None:
    surface = _SurfaceStub()
    _set_track_device_to_synth(surface, track=0, device=0, synth_type="wavetable")
    _set_track_device_to_synth(surface, track=1, device=0, synth_type="drift")
    backend = LiveBackend(surface)

    all_result = backend.find_synth_devices(track=None, synth_type=None)
    wavetable_only = backend.find_synth_devices(track=None, synth_type="wavetable")
    track_1_only = backend.find_synth_devices(track=1, synth_type=None)

    assert all_result["count"] == 2
    assert {item["detected_type"] for item in all_result["devices"]} == {"wavetable", "drift"}
    assert wavetable_only["count"] == 1
    assert wavetable_only["devices"][0]["detected_type"] == "wavetable"
    assert track_1_only["count"] == 1
    assert track_1_only["devices"][0]["track"] == 1


def test_live_backend_list_and_observe_synth_parameters_include_safe_metadata() -> None:
    surface = _SurfaceStub()
    _set_track_device_to_synth(surface, track=0, device=0, synth_type="wavetable")
    backend = LiveBackend(surface)

    listed = backend.list_synth_parameters(track=0, device=0)
    observed = backend.observe_synth_parameters(track=0, device=0)

    assert listed["detected_type"] == "wavetable"
    assert listed["parameter_count"] >= 9
    assert listed["parameters"][0]["min"] == 0.0
    assert listed["parameters"][0]["max"] == 1.0
    assert listed["parameters"][0]["is_enabled"] is True
    assert listed["parameters"][0]["is_quantized"] is False
    assert observed["parameter_count"] == listed["parameter_count"]


def test_live_backend_set_synth_parameter_safe_accepts_in_range_only() -> None:
    surface = _SurfaceStub()
    _set_track_device_to_synth(surface, track=0, device=0, synth_type="wavetable")
    backend = LiveBackend(surface)

    ok = backend.set_synth_parameter_safe(track=0, device=0, parameter=0, value=0.7)
    assert ok["before"] == 0.5
    assert ok["after"] == 0.7

    with pytest.raises(CommandError) as exc_info:
        backend.set_synth_parameter_safe(track=0, device=0, parameter=0, value=1.5)
    assert exc_info.value.code == "INVALID_ARGUMENT"


@pytest.mark.parametrize(
    ("synth_type", "key", "value"),
    (
        ("wavetable", "filter_cutoff", 0.65),
        ("drift", "drift_amount", 0.44),
        ("meld", "spread_amount", 0.33),
    ),
)
def test_live_backend_standard_synth_wrappers_keys_set_and_observe(
    synth_type: str,
    key: str,
    value: float,
) -> None:
    surface = _SurfaceStub()
    _set_track_device_to_synth(surface, track=0, device=0, synth_type=synth_type)
    backend = LiveBackend(surface)

    keys = backend.list_standard_synth_keys(synth_type)
    set_result = backend.set_standard_synth_parameter_safe(
        synth_type=synth_type,
        track=0,
        device=0,
        key=key,
        value=value,
    )
    observed = backend.observe_standard_synth_state(
        synth_type=synth_type,
        track=0,
        device=0,
    )

    assert keys["key_count"] == 9
    assert key in keys["keys"]
    assert set_result["key"] == key
    assert set_result["after"] == value
    assert observed["state"][key] == value


def test_live_backend_standard_wrapper_rejects_missing_required_key_mapping() -> None:
    surface = _SurfaceStub()
    _set_track_device_to_synth(surface, track=0, device=0, synth_type="wavetable")
    surface.song().tracks[0].devices[0].parameters = [
        param
        for param in surface.song().tracks[0].devices[0].parameters
        if param.name != "Osc 2 Pos"
    ]
    backend = LiveBackend(surface)

    with pytest.raises(CommandError) as exc_info:
        backend.observe_standard_synth_state(
            synth_type="wavetable",
            track=0,
            device=0,
        )
    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_live_backend_find_effect_devices_with_filters() -> None:
    surface = _SurfaceStub()
    _set_track_device_to_effect(surface, track=0, device=0, effect_type="eq8")
    _set_track_device_to_effect(surface, track=1, device=0, effect_type="limiter")
    backend = LiveBackend(surface)

    all_result = backend.find_effect_devices(track=None, effect_type=None)
    eq8_only = backend.find_effect_devices(track=None, effect_type="eq8")
    track_1_only = backend.find_effect_devices(track=1, effect_type=None)

    assert all_result["count"] == 2
    assert {item["detected_type"] for item in all_result["devices"]} == {"eq8", "limiter"}
    assert eq8_only["count"] == 1
    assert eq8_only["devices"][0]["detected_type"] == "eq8"
    assert track_1_only["count"] == 1
    assert track_1_only["devices"][0]["track"] == 1


def test_live_backend_list_and_observe_effect_parameters_include_safe_metadata() -> None:
    surface = _SurfaceStub()
    _set_track_device_to_effect(surface, track=0, device=0, effect_type="eq8")
    backend = LiveBackend(surface)

    listed = backend.list_effect_parameters(track=0, device=0)
    observed = backend.observe_effect_parameters(track=0, device=0)

    assert listed["detected_type"] == "eq8"
    assert listed["parameter_count"] >= 5
    assert listed["parameters"][0]["min"] == 0.0
    assert listed["parameters"][0]["max"] == 1.0
    assert listed["parameters"][0]["is_enabled"] is True
    assert listed["parameters"][0]["is_quantized"] is False
    assert observed["parameter_count"] == listed["parameter_count"]


def test_live_backend_set_effect_parameter_safe_accepts_in_range_only() -> None:
    surface = _SurfaceStub()
    _set_track_device_to_effect(surface, track=0, device=0, effect_type="eq8")
    backend = LiveBackend(surface)

    ok = backend.set_effect_parameter_safe(track=0, device=0, parameter=0, value=0.7)
    assert ok["before"] == 0.5
    assert ok["after"] == 0.7

    with pytest.raises(CommandError) as exc_info:
        backend.set_effect_parameter_safe(track=0, device=0, parameter=0, value=1.5)
    assert exc_info.value.code == "INVALID_ARGUMENT"


@pytest.mark.parametrize(
    ("effect_type", "key", "value"),
    (
        ("eq8", "band1_freq", 0.65),
        ("limiter", "ceiling", 0.44),
        ("compressor", "ratio", 0.33),
        ("auto_filter", "lfo_rate", 0.31),
        ("reverb", "size", 0.5),
        ("utility", "width", 0.7),
    ),
)
def test_live_backend_standard_effect_wrappers_keys_set_and_observe(
    effect_type: str,
    key: str,
    value: float,
) -> None:
    surface = _SurfaceStub()
    _set_track_device_to_effect(surface, track=0, device=0, effect_type=effect_type)
    backend = LiveBackend(surface)

    keys = backend.list_standard_effect_keys(effect_type)
    set_result = backend.set_standard_effect_parameter_safe(
        effect_type=effect_type,
        track=0,
        device=0,
        key=key,
        value=value,
    )
    observed = backend.observe_standard_effect_state(
        effect_type=effect_type,
        track=0,
        device=0,
    )

    assert keys["key_count"] == 5
    assert key in keys["keys"]
    assert set_result["key"] == key
    assert set_result["after"] == value
    assert observed["state"][key] == value


def test_live_backend_standard_effect_wrapper_rejects_missing_required_key_mapping() -> None:
    surface = _SurfaceStub()
    _set_track_device_to_effect(surface, track=0, device=0, effect_type="eq8")
    surface.song().tracks[0].devices[0].parameters = [
        param for param in surface.song().tracks[0].devices[0].parameters if param.name != "1 Q A"
    ]
    backend = LiveBackend(surface)

    with pytest.raises(CommandError) as exc_info:
        backend.observe_standard_effect_state(
            effect_type="eq8",
            track=0,
            device=0,
        )
    assert exc_info.value.code == "INVALID_ARGUMENT"


def test_live_backend_clip_notes_get_clear_replace_with_filters() -> None:
    backend = LiveBackend(_SurfaceStub())
    note_a = _note()
    note_b = {
        "pitch": 62,
        "start_time": 1.0,
        "duration": 0.5,
        "velocity": 110,
        "mute": False,
    }
    note_c = {
        "pitch": 60,
        "start_time": 2.0,
        "duration": 0.5,
        "velocity": 95,
        "mute": False,
    }
    replacement = {
        "pitch": 65,
        "start_time": 0.25,
        "duration": 0.5,
        "velocity": 96,
        "mute": False,
    }

    backend.create_clip(0, 1, 4.0)
    backend.add_notes_to_clip(0, 1, [note_a, note_b, note_c])

    all_notes = backend.get_clip_notes(0, 1, None, None, None)
    assert all_notes["note_count"] == 3

    pitch_60 = backend.get_clip_notes(0, 1, None, None, 60)
    assert pitch_60["note_count"] == 2

    cleared = backend.clear_clip_notes(0, 1, 1.0, 3.0, 60)
    assert cleared["cleared_count"] == 1
    remaining_pitch_60 = backend.get_clip_notes(0, 1, None, None, 60)
    assert remaining_pitch_60["note_count"] == 1

    replaced = backend.replace_clip_notes(0, 1, [replacement], 0.0, 1.0, 60)
    assert replaced["cleared_count"] == 1
    assert replaced["added_count"] == 1
    after_replace = backend.get_clip_notes(0, 1, None, None, None)
    pitches = sorted(note["pitch"] for note in after_replace["notes"])
    assert pitches == [62, 65]


def test_live_backend_clip_note_transform_commands_with_filters() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.create_clip(0, 0, 4.0)
    backend.add_notes_to_clip(
        0,
        0,
        [
            {
                "pitch": 60,
                "start_time": 0.12,
                "duration": 0.5,
                "velocity": 100,
                "mute": False,
            },
            {
                "pitch": 60,
                "start_time": 0.62,
                "duration": 0.5,
                "velocity": 90,
                "mute": False,
            },
            {
                "pitch": 64,
                "start_time": 1.1,
                "duration": 0.5,
                "velocity": 80,
                "mute": False,
            },
        ],
    )

    quantized = backend.clip_notes_quantize(
        0,
        0,
        grid=0.5,
        strength=1.0,
        start_time=0.0,
        end_time=1.0,
        pitch=60,
    )
    assert quantized["changed_count"] == 2

    humanized = backend.clip_notes_humanize(
        0,
        0,
        timing=0.1,
        velocity=5,
        start_time=0.0,
        end_time=1.0,
        pitch=60,
    )
    assert humanized["changed_count"] == 2

    velocity_scaled = backend.clip_notes_velocity_scale(
        0,
        0,
        scale=1.0,
        offset=10,
        start_time=0.0,
        end_time=1.0,
        pitch=60,
    )
    assert velocity_scaled["changed_count"] == 2

    transposed = backend.clip_notes_transpose(
        0,
        0,
        semitones=2,
        start_time=0.0,
        end_time=1.0,
        pitch=60,
    )
    assert transposed["changed_count"] == 2

    after = backend.get_clip_notes(0, 0, None, None, None)
    notes = sorted(after["notes"], key=lambda note: float(note["start_time"]))
    assert notes[0]["pitch"] == 62
    assert notes[0]["start_time"] == 0.1
    assert notes[0]["velocity"] == 115
    assert notes[1]["pitch"] == 62
    assert notes[1]["start_time"] == 0.4
    assert notes[1]["velocity"] == 95
    assert notes[2]["pitch"] == 64
    assert notes[2]["start_time"] == 1.1
    assert notes[2]["velocity"] == 80


def test_live_backend_load_drum_kit_requires_explicit_selection() -> None:
    backend = LiveBackend(_SurfaceStub())
    by_uri = backend.load_drum_kit(0, "rack:drums", kit_uri="kit:acoustic", kit_path=None)
    by_path = backend.load_drum_kit(
        0,
        "rack:drums",
        kit_uri=None,
        kit_path="drums/Kits/Acoustic Kit",
    )

    assert by_uri["kit_uri"] == "kit:acoustic"
    assert by_uri["kit_path"] == "drums/Kits/Acoustic Kit"
    assert by_path["kit_uri"] == "kit:acoustic"
    assert by_path["kit_path"] == "drums/Kits/Acoustic Kit"

    with pytest.raises(CommandError) as exc_info_none:
        backend.load_drum_kit(0, "rack:drums", kit_uri=None, kit_path=None)
    with pytest.raises(CommandError) as exc_info_both:
        backend.load_drum_kit(
            0,
            "rack:drums",
            kit_uri="kit:acoustic",
            kit_path="drums/Kits/Acoustic Kit",
        )
    assert exc_info_none.value.code == "INVALID_ARGUMENT"
    assert exc_info_both.value.code == "INVALID_ARGUMENT"


def test_live_backend_scene_lifecycle() -> None:
    backend = LiveBackend(_SurfaceStub())

    listed = backend.scenes_list()
    assert listed["scenes"][0]["index"] == 0

    created = backend.create_scene(1)
    assert created["index"] == 1

    renamed = backend.set_scene_name(1, "Build")
    assert renamed == {"scene": 1, "name": "Build"}

    fired = backend.fire_scene(1)
    assert fired == {"scene": 1, "fired": True}


def test_live_backend_clip_duplicate() -> None:
    backend = LiveBackend(_SurfaceStub())
    backend.create_clip(0, 0, 4.0)
    backend.add_notes_to_clip(0, 0, [_note()])

    duplicated = backend.clip_duplicate(track=0, src_clip=0, dst_clip=1)
    assert duplicated == {
        "track": 0,
        "src_clip": 0,
        "dst_clip": 1,
        "duplicated": True,
        "note_count": 1,
    }
    duplicated_notes = backend.get_clip_notes(0, 1, None, None, None)
    assert duplicated_notes["note_count"] == 1

    with pytest.raises(CommandError) as missing_src:
        backend.clip_duplicate(track=1, src_clip=0, dst_clip=1)
    assert missing_src.value.code == "INVALID_ARGUMENT"

    with pytest.raises(CommandError) as occupied_dst:
        backend.clip_duplicate(track=0, src_clip=0, dst_clip=1)
    assert occupied_dst.value.code == "INVALID_ARGUMENT"


def test_live_backend_tracks_delete_and_not_supported_error() -> None:
    backend = LiveBackend(_SurfaceStub())
    deleted = backend.tracks_delete(0)
    assert deleted == {"track": 0, "deleted": True, "track_count": 1}

    with pytest.raises(CommandError) as out_of_range:
        backend.tracks_delete(99)
    assert out_of_range.value.code == "INVALID_ARGUMENT"

    unsupported_surface = _SurfaceStub()
    unsupported_surface.song().delete_track = None
    unsupported_backend = LiveBackend(unsupported_surface)
    with pytest.raises(CommandError) as unsupported_exc:
        unsupported_backend.tracks_delete(0)
    assert unsupported_exc.value.code == "INVALID_ARGUMENT"
    assert unsupported_exc.value.details == {"reason": "not_supported_by_live_api"}


def test_live_backend_scenes_move_and_not_supported_error() -> None:
    backend = LiveBackend(_SurfaceStub())
    moved = backend.scenes_move(from_index=0, to_index=1)
    assert moved == {"from": 0, "to": 1, "moved": True}
    assert backend.scenes_list()["scenes"][1]["name"] == "Scene 1"

    unsupported_surface = _SurfaceStub()
    unsupported_surface.song().move_scene = None
    unsupported_backend = LiveBackend(unsupported_surface)
    with pytest.raises(CommandError) as unsupported_exc:
        unsupported_backend.scenes_move(from_index=0, to_index=1)
    assert unsupported_exc.value.code == "INVALID_ARGUMENT"
    assert unsupported_exc.value.details == {"reason": "not_supported_by_live_api"}


@pytest.mark.parametrize(
    "operation",
    (
        "song_new",
        "song_save",
        "song_export_audio",
        "arrangement_record_start",
        "arrangement_record_stop",
    ),
)
def test_live_backend_high_difficulty_commands_raise_explicit_not_supported(operation: str) -> None:
    backend = LiveBackend(_SurfaceStub())

    with pytest.raises(CommandError) as exc_info:
        if operation == "song_new":
            backend.song_new()
        elif operation == "song_save":
            backend.song_save("/tmp/demo.als")
        elif operation == "song_export_audio":
            backend.song_export_audio("/tmp/demo.wav")
        elif operation == "arrangement_record_start":
            backend.arrangement_record_start()
        else:
            backend.arrangement_record_stop()

    assert exc_info.value.code == "INVALID_ARGUMENT"
    assert exc_info.value.details == {"reason": "not_supported_by_live_api"}


def test_live_backend_stop_all_clips() -> None:
    surface = _SurfaceStub()
    backend = LiveBackend(surface)

    result = backend.stop_all_clips()

    assert result == {"stopped": True}
    assert surface.song().stop_all_clips_calls == 1


def test_live_backend_track_mixer_controls() -> None:
    backend = LiveBackend(_SurfaceStub())

    assert backend.track_mute_set(0, True) == {"track": 0, "mute": True}
    assert backend.track_mute_get(0) == {"track": 0, "mute": True}
    assert backend.track_solo_set(0, True) == {"track": 0, "solo": True}
    assert backend.track_solo_get(0) == {"track": 0, "solo": True}
    assert backend.track_arm_set(0, True) == {"track": 0, "arm": True}
    assert backend.track_arm_get(0) == {"track": 0, "arm": True}
    assert backend.track_panning_set(0, -0.4) == {"track": 0, "panning": -0.4}
    assert backend.track_panning_get(0) == {"track": 0, "panning": -0.4}


def test_live_backend_track_arm_set_rejects_unarmable_track() -> None:
    class _TrackNoArm:
        def __init__(self, original: _Track) -> None:
            self.name = original.name
            self.has_audio_input = original.has_audio_input
            self.has_midi_input = original.has_midi_input
            self.mute = original.mute
            self.solo = original.solo
            self.mixer_device = original.mixer_device
            self.clip_slots = original.clip_slots
            self.devices = original.devices

    surface = _SurfaceStub()
    surface.song().tracks[0] = _TrackNoArm(surface.song().tracks[0])
    backend = LiveBackend(surface)

    with pytest.raises(CommandError) as exc_info:
        backend.track_arm_set(0, True)
    assert exc_info.value.code == "INVALID_ARGUMENT"
