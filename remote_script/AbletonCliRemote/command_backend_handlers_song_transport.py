from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .command_backend_contract import CommandBackend
from .command_backend_validators import (
    _as_bool,
    _insert_index,
    _non_empty_string,
    _non_negative_float,
    _panning,
    _tempo,
    _track_index,
    _volume,
)

Handler = Callable[[CommandBackend, dict[str, Any]], dict[str, Any]]


def _handle_song_info(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.song_info()


def _handle_song_new(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.song_new()


def _handle_song_save(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    path = _non_empty_string("path", args.get("path"))
    return backend.song_save(path)


def _handle_song_export_audio(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    path = _non_empty_string("path", args.get("path"))
    return backend.song_export_audio(path)


def _handle_get_session_info(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.get_session_info()


def _handle_session_snapshot(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.session_snapshot()


def _handle_get_track_info(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.get_track_info(track)


def _handle_tracks_list(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.tracks_list()


def _handle_create_midi_track(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    index = _insert_index("index", args.get("index", -1))
    return backend.create_midi_track(index)


def _handle_create_audio_track(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    index = _insert_index("index", args.get("index", -1))
    return backend.create_audio_track(index)


def _handle_set_track_name(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    name = _non_empty_string("name", args.get("name"))
    return backend.set_track_name(track, name)


def _handle_transport_play(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_play()


def _handle_transport_stop(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_stop()


def _handle_transport_toggle(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_toggle()


def _handle_start_playback(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.start_playback()


def _handle_stop_playback(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.stop_playback()


def _handle_transport_tempo_get(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_tempo_get()


def _handle_transport_tempo_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.transport_tempo_set(_tempo(args.get("bpm")))


def _handle_transport_position_get(
    backend: CommandBackend,
    _args: dict[str, Any],
) -> dict[str, Any]:
    return backend.transport_position_get()


def _handle_transport_position_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    return backend.transport_position_set(_non_negative_float("beats", args.get("beats")))


def _handle_transport_rewind(
    backend: CommandBackend,
    _args: dict[str, Any],
) -> dict[str, Any]:
    return backend.transport_rewind()


def _handle_set_tempo(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.set_tempo(_tempo(args.get("tempo")))


def _handle_track_volume_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_volume_get(track)


def _handle_track_volume_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_volume_set(track, _volume(args.get("value")))


def _handle_track_mute_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_mute_get(track)


def _handle_track_mute_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    value = _as_bool("value", args.get("value"))
    return backend.track_mute_set(track, value)


def _handle_track_solo_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_solo_get(track)


def _handle_track_solo_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    value = _as_bool("value", args.get("value"))
    return backend.track_solo_set(track, value)


def _handle_track_arm_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_arm_get(track)


def _handle_track_arm_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    value = _as_bool("value", args.get("value"))
    return backend.track_arm_set(track, value)


def _handle_track_panning_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_panning_get(track)


def _handle_track_panning_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_panning_set(track, _panning(args.get("value")))


def _handle_track_send_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    send = _track_index("send", args.get("send"))
    return backend.track_send_get(track, send)


def _handle_track_send_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    send = _track_index("send", args.get("send"))
    return backend.track_send_set(track, send, _volume(args.get("value")))


def _handle_return_tracks_list(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.return_tracks_list()


def _handle_return_track_volume_get(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    return_track = _track_index("return_track", args.get("return_track"))
    return backend.return_track_volume_get(return_track)


def _handle_return_track_volume_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    return_track = _track_index("return_track", args.get("return_track"))
    return backend.return_track_volume_set(return_track, _volume(args.get("value")))


def _handle_return_track_mute_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return_track = _track_index("return_track", args.get("return_track"))
    return backend.return_track_mute_get(return_track)


def _handle_return_track_mute_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return_track = _track_index("return_track", args.get("return_track"))
    value = _as_bool("value", args.get("value"))
    return backend.return_track_mute_set(return_track, value)


def _handle_return_track_solo_get(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return_track = _track_index("return_track", args.get("return_track"))
    return backend.return_track_solo_get(return_track)


def _handle_return_track_solo_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return_track = _track_index("return_track", args.get("return_track"))
    value = _as_bool("value", args.get("value"))
    return backend.return_track_solo_set(return_track, value)


def _handle_master_info(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.master_info()


def _handle_master_volume_get(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.master_volume_get()


def _handle_master_panning_get(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.master_panning_get()


def _handle_master_devices_list(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.master_devices_list()


def _handle_mixer_crossfader_get(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.mixer_crossfader_get()


def _handle_mixer_crossfader_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.mixer_crossfader_set(_panning(args.get("value")))


def _handle_mixer_cue_volume_get(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.mixer_cue_volume_get()


def _handle_mixer_cue_volume_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    return backend.mixer_cue_volume_set(_volume(args.get("value")))


def _handle_mixer_cue_routing_get(backend: CommandBackend, _args: dict[str, Any]) -> dict[str, Any]:
    return backend.mixer_cue_routing_get()


def _handle_mixer_cue_routing_set(backend: CommandBackend, args: dict[str, Any]) -> dict[str, Any]:
    routing = _non_empty_string("routing", args.get("routing"))
    return backend.mixer_cue_routing_set(routing)


def _handle_track_routing_input_get(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_routing_input_get(track)


def _handle_track_routing_input_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    routing_type = _non_empty_string("routing_type", args.get("routing_type"))
    routing_channel = _non_empty_string("routing_channel", args.get("routing_channel"))
    return backend.track_routing_input_set(track, routing_type, routing_channel)


def _handle_track_routing_output_get(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    return backend.track_routing_output_get(track)


def _handle_track_routing_output_set(
    backend: CommandBackend,
    args: dict[str, Any],
) -> dict[str, Any]:
    track = _track_index("track", args.get("track"))
    routing_type = _non_empty_string("routing_type", args.get("routing_type"))
    routing_channel = _non_empty_string("routing_channel", args.get("routing_channel"))
    return backend.track_routing_output_set(track, routing_type, routing_channel)


SONG_TRANSPORT_HANDLERS: dict[str, Handler] = {
    "song_info": _handle_song_info,
    "song_new": _handle_song_new,
    "song_save": _handle_song_save,
    "song_export_audio": _handle_song_export_audio,
    "get_session_info": _handle_get_session_info,
    "session_snapshot": _handle_session_snapshot,
    "get_track_info": _handle_get_track_info,
    "tracks_list": _handle_tracks_list,
    "create_midi_track": _handle_create_midi_track,
    "create_audio_track": _handle_create_audio_track,
    "set_track_name": _handle_set_track_name,
    "transport_play": _handle_transport_play,
    "transport_stop": _handle_transport_stop,
    "transport_toggle": _handle_transport_toggle,
    "start_playback": _handle_start_playback,
    "stop_playback": _handle_stop_playback,
    "transport_tempo_get": _handle_transport_tempo_get,
    "transport_tempo_set": _handle_transport_tempo_set,
    "transport_position_get": _handle_transport_position_get,
    "transport_position_set": _handle_transport_position_set,
    "transport_rewind": _handle_transport_rewind,
    "set_tempo": _handle_set_tempo,
    "track_volume_get": _handle_track_volume_get,
    "track_volume_set": _handle_track_volume_set,
    "track_mute_get": _handle_track_mute_get,
    "track_mute_set": _handle_track_mute_set,
    "track_solo_get": _handle_track_solo_get,
    "track_solo_set": _handle_track_solo_set,
    "track_arm_get": _handle_track_arm_get,
    "track_arm_set": _handle_track_arm_set,
    "track_panning_get": _handle_track_panning_get,
    "track_panning_set": _handle_track_panning_set,
    "track_send_get": _handle_track_send_get,
    "track_send_set": _handle_track_send_set,
    "return_tracks_list": _handle_return_tracks_list,
    "return_track_volume_get": _handle_return_track_volume_get,
    "return_track_volume_set": _handle_return_track_volume_set,
    "return_track_mute_get": _handle_return_track_mute_get,
    "return_track_mute_set": _handle_return_track_mute_set,
    "return_track_solo_get": _handle_return_track_solo_get,
    "return_track_solo_set": _handle_return_track_solo_set,
    "master_info": _handle_master_info,
    "master_volume_get": _handle_master_volume_get,
    "master_panning_get": _handle_master_panning_get,
    "master_devices_list": _handle_master_devices_list,
    "mixer_crossfader_get": _handle_mixer_crossfader_get,
    "mixer_crossfader_set": _handle_mixer_crossfader_set,
    "mixer_cue_volume_get": _handle_mixer_cue_volume_get,
    "mixer_cue_volume_set": _handle_mixer_cue_volume_set,
    "mixer_cue_routing_get": _handle_mixer_cue_routing_get,
    "mixer_cue_routing_set": _handle_mixer_cue_routing_set,
    "track_routing_input_get": _handle_track_routing_input_get,
    "track_routing_input_set": _handle_track_routing_input_set,
    "track_routing_output_get": _handle_track_routing_output_get,
    "track_routing_output_set": _handle_track_routing_output_set,
}
