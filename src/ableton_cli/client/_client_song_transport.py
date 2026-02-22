from __future__ import annotations


class _AbletonClientSongTransportMixin:
    def ping(self) -> dict[str, object]:
        return self._call("ping")

    def song_info(self) -> dict[str, object]:
        return self._call("song_info")

    def song_new(self) -> dict[str, object]:
        return self._call("song_new")

    def song_save(self, path: str) -> dict[str, object]:
        return self._call("song_save", {"path": path})

    def song_export_audio(self, path: str) -> dict[str, object]:
        return self._call("song_export_audio", {"path": path})

    def get_session_info(self) -> dict[str, object]:
        return self._call("get_session_info")

    def session_snapshot(self) -> dict[str, object]:
        return self._call("session_snapshot")

    def transport_play(self) -> dict[str, object]:
        return self._call("transport_play")

    def transport_stop(self) -> dict[str, object]:
        return self._call("transport_stop")

    def transport_toggle(self) -> dict[str, object]:
        return self._call("transport_toggle")

    def transport_tempo_get(self) -> dict[str, object]:
        return self._call("transport_tempo_get")

    def transport_tempo_set(self, bpm: float) -> dict[str, object]:
        return self._call("transport_tempo_set", {"bpm": bpm})

    def start_playback(self) -> dict[str, object]:
        return self._call("start_playback")

    def stop_playback(self) -> dict[str, object]:
        return self._call("stop_playback")

    def set_tempo(self, tempo: float) -> dict[str, object]:
        return self._call("set_tempo", {"tempo": tempo})
