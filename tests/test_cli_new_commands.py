from __future__ import annotations

import json
from pathlib import Path

from ableton_cli.errors import AppError, ExitCode


class _ClientStub:
    def song_new(self):  # noqa: ANN201
        return {"created": True}

    def song_save(self, path: str):  # noqa: ANN201
        return {"saved": True, "path": path}

    def song_export_audio(self, path: str):  # noqa: ANN201
        return {"exported": True, "path": path}

    def get_session_info(self):  # noqa: ANN201
        return {"tempo": 123.0}

    def session_snapshot(self):  # noqa: ANN201
        return {
            "song_info": {"tempo": 123.0, "is_playing": False},
            "session_info": {"track_count": 2},
            "tracks_list": {"tracks": [{"index": 0, "name": "Track 1"}]},
            "scenes_list": {"scenes": [{"index": 0, "name": "Intro"}]},
        }

    def stop_all_clips(self):  # noqa: ANN201
        return {"stopped": True}

    def set_device_parameter(  # noqa: ANN201
        self, track: int, device: int, parameter: int, value: float
    ):
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "value": value,
        }

    def create_midi_track(self, index: int):  # noqa: ANN201
        return {"index": index, "name": "MIDI", "kind": "midi"}

    def create_audio_track(self, index: int):  # noqa: ANN201
        return {"index": index, "name": "Audio", "kind": "audio"}

    def add_notes_to_clip(self, track: int, clip: int, notes: list[dict[str, object]]):  # noqa: ANN201
        return {"track": track, "clip": clip, "note_count": len(notes)}

    def get_clip_notes(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "notes": [],
            "note_count": 0,
        }

    def clear_clip_notes(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": 1,
        }

    def replace_clip_notes(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        notes: list[dict[str, object]],
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "cleared_count": 2,
            "added_count": len(notes),
        }

    def clip_duplicate(self, track: int, src_clip: int, dst_clip: int):  # noqa: ANN201
        return {"track": track, "src_clip": src_clip, "dst_clip": dst_clip, "duplicated": True}

    def clip_notes_quantize(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        grid: str,
        strength: float,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "grid": grid,
            "strength": strength,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "changed_count": 2,
        }

    def clip_notes_humanize(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        timing: float,
        velocity: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "timing": timing,
            "velocity": velocity,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "changed_count": 2,
        }

    def clip_notes_velocity_scale(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        scale: float,
        offset: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "scale": scale,
            "offset": offset,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "changed_count": 2,
        }

    def clip_notes_transpose(  # noqa: ANN201
        self,
        track: int,
        clip: int,
        semitones: int,
        start_time: float | None,
        end_time: float | None,
        pitch: int | None,
    ):
        return {
            "track": track,
            "clip": clip,
            "semitones": semitones,
            "start_time": start_time,
            "end_time": end_time,
            "pitch": pitch,
            "changed_count": 2,
        }

    def clip_active_get(self, track: int, clip: int):  # noqa: ANN201
        return {"track": track, "clip": clip, "active": True}

    def clip_active_set(self, track: int, clip: int, value: bool):  # noqa: ANN201
        return {"track": track, "clip": clip, "active": value}

    def search_browser_items(  # noqa: ANN201
        self,
        query: str,
        path: str | None,
        item_type: str,
        limit: int,
        offset: int,
        exact: bool,
        case_sensitive: bool,
    ):
        return {
            "query": query,
            "path": path,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "exact": exact,
            "case_sensitive": case_sensitive,
            "duration_ms": 1.23,
            "items": [],
        }

    def get_browser_items(  # noqa: ANN201
        self,
        path: str,
        item_type: str,
        limit: int,
        offset: int,
    ):
        return {
            "path": path,
            "item_type": item_type,
            "limit": limit,
            "offset": offset,
            "returned": 0,
            "total_matches": 0,
            "has_more": False,
            "duration_ms": 0.1,
            "items": [],
        }

    def get_browser_item(self, uri: str | None, path: str | None):  # noqa: ANN201
        return {"uri": uri, "path": path, "found": True}

    def load_instrument_or_effect(  # noqa: ANN201
        self,
        track: int,
        uri: str | None,
        path: str | None,
        target_track_mode: str = "auto",
        clip_slot: int | None = None,
        preserve_track_name: bool = False,
    ):
        return {
            "track": track,
            "uri": uri,
            "path": path,
            "target_track_mode": target_track_mode,
            "clip_slot": clip_slot,
            "preserve_track_name": preserve_track_name,
            "loaded": True,
        }

    def load_drum_kit(  # noqa: ANN201
        self,
        track: int,
        rack_uri: str,
        kit_uri: str | None,
        kit_path: str | None,
    ):
        return {
            "track": track,
            "rack_uri": rack_uri,
            "kit_uri": kit_uri,
            "kit_path": kit_path,
            "loaded": True,
        }

    def track_mute_get(self, track: int):  # noqa: ANN201
        return {"track": track, "mute": False}

    def track_mute_set(self, track: int, value: bool):  # noqa: ANN201
        return {"track": track, "mute": value}

    def track_solo_get(self, track: int):  # noqa: ANN201
        return {"track": track, "solo": False}

    def track_solo_set(self, track: int, value: bool):  # noqa: ANN201
        return {"track": track, "solo": value}

    def track_arm_get(self, track: int):  # noqa: ANN201
        return {"track": track, "arm": False}

    def track_arm_set(self, track: int, value: bool):  # noqa: ANN201
        return {"track": track, "arm": value}

    def track_panning_get(self, track: int):  # noqa: ANN201
        return {"track": track, "panning": 0.0}

    def track_panning_set(self, track: int, value: float):  # noqa: ANN201
        return {"track": track, "panning": value}

    def scenes_list(self):  # noqa: ANN201
        return {"scenes": [{"index": 0, "name": "Intro"}]}

    def create_scene(self, index: int):  # noqa: ANN201
        return {"index": index, "name": "Scene"}

    def set_scene_name(self, scene: int, name: str):  # noqa: ANN201
        return {"scene": scene, "name": name}

    def fire_scene(self, scene: int):  # noqa: ANN201
        return {"scene": scene, "fired": True}

    def scenes_move(self, from_index: int, to_index: int):  # noqa: ANN201
        return {"from": from_index, "to": to_index, "moved": True}

    def tracks_delete(self, track: int):  # noqa: ANN201
        return {"track": track, "deleted": True}

    def arrangement_record_start(self):  # noqa: ANN201
        return {"recording": True}

    def arrangement_record_stop(self):  # noqa: ANN201
        return {"recording": False}

    def execute_batch(self, steps: list[dict[str, object]]):  # noqa: ANN201
        return {
            "step_count": len(steps),
            "results": [{"index": idx, "result": {"ok": True}} for idx, _ in enumerate(steps)],
        }

    def find_synth_devices(  # noqa: ANN201
        self,
        track: int | None,
        synth_type: str | None,
    ):
        return {
            "track": track,
            "synth_type": synth_type,
            "count": 1,
            "devices": [{"track": 0, "device": 1, "detected_type": "wavetable"}],
        }

    def list_synth_parameters(self, track: int, device: int):  # noqa: ANN201
        return {
            "track": track,
            "device": device,
            "detected_type": "wavetable",
            "parameter_count": 1,
            "parameters": [
                {
                    "index": 0,
                    "name": "Filter Freq",
                    "value": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "is_enabled": True,
                    "is_quantized": False,
                }
            ],
        }

    def set_synth_parameter_safe(  # noqa: ANN201
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ):
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "before": 0.3,
            "after": value,
        }

    def observe_synth_parameters(self, track: int, device: int):  # noqa: ANN201
        return {
            "track": track,
            "device": device,
            "detected_type": "wavetable",
            "parameter_count": 1,
            "parameters": [{"index": 0, "name": "Filter Freq", "value": 0.5}],
        }

    def list_standard_synth_keys(self, synth_type: str):  # noqa: ANN201
        return {
            "synth_type": synth_type,
            "key_count": 9,
            "keys": [
                "filter_cutoff",
                "filter_resonance",
                "amp_attack",
                "amp_decay",
                "amp_sustain",
                "amp_release",
                "osc1_position",
                "osc2_position",
                "unison_amount",
            ],
        }

    def set_standard_synth_parameter_safe(  # noqa: ANN201
        self,
        synth_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ):
        return {
            "synth_type": synth_type,
            "track": track,
            "device": device,
            "key": key,
            "before": 0.4,
            "after": value,
        }

    def observe_standard_synth_state(  # noqa: ANN201
        self,
        synth_type: str,
        track: int,
        device: int,
    ):
        return {
            "synth_type": synth_type,
            "track": track,
            "device": device,
            "state": {"filter_cutoff": 0.5},
        }

    def find_effect_devices(  # noqa: ANN201
        self,
        track: int | None,
        effect_type: str | None,
    ):
        return {
            "track": track,
            "effect_type": effect_type,
            "count": 1,
            "devices": [{"track": 0, "device": 2, "detected_type": "eq8"}],
        }

    def list_effect_parameters(self, track: int, device: int):  # noqa: ANN201
        return {
            "track": track,
            "device": device,
            "detected_type": "eq8",
            "parameter_count": 1,
            "parameters": [
                {
                    "index": 0,
                    "name": "1 Frequency A",
                    "value": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "is_enabled": True,
                    "is_quantized": False,
                }
            ],
        }

    def set_effect_parameter_safe(  # noqa: ANN201
        self,
        track: int,
        device: int,
        parameter: int,
        value: float,
    ):
        return {
            "track": track,
            "device": device,
            "parameter": parameter,
            "before": 0.2,
            "after": value,
        }

    def observe_effect_parameters(self, track: int, device: int):  # noqa: ANN201
        return {
            "track": track,
            "device": device,
            "detected_type": "eq8",
            "parameter_count": 1,
            "parameters": [{"index": 0, "name": "1 Frequency A", "value": 0.5}],
        }

    def list_standard_effect_keys(self, effect_type: str):  # noqa: ANN201
        return {
            "effect_type": effect_type,
            "key_count": 5,
            "keys": [
                "band1_freq",
                "band1_gain",
                "band1_q",
                "low_cut_freq",
                "high_cut_freq",
            ],
        }

    def set_standard_effect_parameter_safe(  # noqa: ANN201
        self,
        effect_type: str,
        track: int,
        device: int,
        key: str,
        value: float,
    ):
        return {
            "effect_type": effect_type,
            "track": track,
            "device": device,
            "key": key,
            "before": 0.1,
            "after": value,
        }

    def observe_standard_effect_state(  # noqa: ANN201
        self,
        effect_type: str,
        track: int,
        device: int,
    ):
        return {
            "effect_type": effect_type,
            "track": track,
            "device": device,
            "state": {"band1_freq": 0.5},
        }


class _WaitReadyClientAlwaysReady:
    def ping(self):  # noqa: ANN201
        return {"protocol_version": 2, "remote_script_version": "0.2.0"}


class _WaitReadyClientEventuallyReady:
    def __init__(self) -> None:
        self._attempt = 0

    def ping(self):  # noqa: ANN201
        self._attempt += 1
        if self._attempt < 3:
            raise AppError(
                error_code="ABLETON_NOT_REACHABLE",
                message="offline",
                hint="start ableton",
                exit_code=ExitCode.ABLETON_NOT_CONNECTED,
            )
        return {"protocol_version": 2, "remote_script_version": "0.2.0"}


class _WaitReadyClientNeverReady:
    def ping(self):  # noqa: ANN201
        raise AppError(
            error_code="ABLETON_NOT_REACHABLE",
            message="offline",
            hint="start ableton",
            exit_code=ExitCode.ABLETON_NOT_CONNECTED,
        )


def test_session_info_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    monkeypatch.setattr(session, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "session", "info"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["tempo"] == 123.0


def test_session_stop_all_clips_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    monkeypatch.setattr(session, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "session", "stop-all-clips"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["stopped"] is True


def test_session_snapshot_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import session

    monkeypatch.setattr(session, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(cli_app, ["--output", "json", "session", "snapshot"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["song_info"]["tempo"] == 123.0
    assert payload["result"]["scenes_list"]["scenes"][0]["name"] == "Intro"


def test_device_parameter_set_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import device

    monkeypatch.setattr(device, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "device", "parameter", "set", "1", "2", "3", "0.75"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 1, "device": 2, "parameter": 3, "value": 0.75}


def test_tracks_create_commands_accept_index_option(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import tracks

    monkeypatch.setattr(tracks, "get_client", lambda ctx: _ClientStub())

    midi = runner.invoke(
        cli_app,
        ["--output", "json", "tracks", "create", "midi", "--index", "-1"],
    )
    audio = runner.invoke(
        cli_app,
        ["--output", "json", "tracks", "create", "audio", "--index", "2"],
    )

    assert midi.exit_code == 0
    assert audio.exit_code == 0
    midi_payload = json.loads(midi.stdout)
    audio_payload = json.loads(audio.stdout)
    assert midi_payload["result"]["index"] == -1
    assert midi_payload["result"]["kind"] == "midi"
    assert audio_payload["result"]["index"] == 2
    assert audio_payload["result"]["kind"] == "audio"


def test_song_new_save_export_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import song

    monkeypatch.setattr(song, "get_client", lambda ctx: _ClientStub())

    created = runner.invoke(cli_app, ["--output", "json", "song", "new"])
    saved = runner.invoke(
        cli_app,
        ["--output", "json", "song", "save", "--path", "/tmp/demo.als"],
    )
    exported = runner.invoke(
        cli_app,
        ["--output", "json", "song", "export", "audio", "--path", "/tmp/demo.wav"],
    )

    assert created.exit_code == 0
    assert saved.exit_code == 0
    assert exported.exit_code == 0

    created_payload = json.loads(created.stdout)
    saved_payload = json.loads(saved.stdout)
    exported_payload = json.loads(exported.stdout)
    assert created_payload["result"]["created"] is True
    assert saved_payload["result"]["saved"] is True
    assert saved_payload["result"]["path"] == "/tmp/demo.als"
    assert exported_payload["result"]["exported"] is True
    assert exported_payload["result"]["path"] == "/tmp/demo.wav"


def test_clip_notes_add_parses_json_and_calls_client(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    notes_json = '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'

    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "notes", "add", "0", "1", "--notes-json", notes_json],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 0, "clip": 1, "note_count": 1}


def test_clip_notes_add_accepts_notes_file(runner, cli_app, monkeypatch, tmp_path: Path) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    notes_path = tmp_path / "notes.json"
    notes_path.write_text(
        '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]',
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "add",
            "0",
            "1",
            "--notes-file",
            str(notes_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 0, "clip": 1, "note_count": 1}


def test_clip_notes_get_clear_replace_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    notes_json = '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]'

    result_get = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "get",
            "0",
            "1",
            "--start-time",
            "0.0",
            "--end-time",
            "1.0",
            "--pitch",
            "60",
        ],
    )
    result_clear = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "notes", "clear", "0", "1", "--pitch", "60"],
    )
    result_replace = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "replace",
            "0",
            "1",
            "--notes-json",
            notes_json,
            "--start-time",
            "0.0",
            "--end-time",
            "4.0",
        ],
    )

    assert result_get.exit_code == 0
    assert result_clear.exit_code == 0
    assert result_replace.exit_code == 0

    payload_get = json.loads(result_get.stdout)
    payload_clear = json.loads(result_clear.stdout)
    payload_replace = json.loads(result_replace.stdout)

    assert payload_get["ok"] is True
    assert payload_get["result"]["pitch"] == 60
    assert payload_clear["ok"] is True
    assert payload_clear["result"]["cleared_count"] == 1
    assert payload_replace["ok"] is True
    assert payload_replace["result"]["added_count"] == 1


def test_clip_notes_replace_accepts_notes_file(
    runner, cli_app, monkeypatch, tmp_path: Path
) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    notes_path = tmp_path / "replace-notes.json"
    notes_path.write_text(
        '[{"pitch":65,"start_time":0.25,"duration":0.5,"velocity":96,"mute":false}]',
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "replace",
            "0",
            "1",
            "--notes-file",
            str(notes_path),
            "--start-time",
            "0.0",
            "--end-time",
            "4.0",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["added_count"] == 1


def test_clip_note_transform_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    quantize = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "quantize",
            "0",
            "1",
            "--grid",
            "1/16",
            "--strength",
            "0.8",
            "--start-time",
            "0.0",
            "--end-time",
            "4.0",
            "--pitch",
            "60",
        ],
    )
    humanize = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "humanize",
            "0",
            "1",
            "--timing",
            "0.1",
            "--velocity",
            "5",
        ],
    )
    velocity_scale = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "velocity-scale",
            "0",
            "1",
            "--scale",
            "1.2",
            "--offset",
            "-3",
        ],
    )
    transpose = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "transpose",
            "0",
            "1",
            "--semitones",
            "7",
        ],
    )

    assert quantize.exit_code == 0
    assert humanize.exit_code == 0
    assert velocity_scale.exit_code == 0
    assert transpose.exit_code == 0

    quantize_payload = json.loads(quantize.stdout)
    humanize_payload = json.loads(humanize.stdout)
    velocity_scale_payload = json.loads(velocity_scale.stdout)
    transpose_payload = json.loads(transpose.stdout)

    assert quantize_payload["result"]["changed_count"] == 2
    assert quantize_payload["result"]["grid"] == "1/16"
    assert humanize_payload["result"]["timing"] == 0.1
    assert humanize_payload["result"]["velocity"] == 5
    assert velocity_scale_payload["result"]["scale"] == 1.2
    assert velocity_scale_payload["result"]["offset"] == -3
    assert transpose_payload["result"]["semitones"] == 7


def test_browser_item_supports_uri_and_path_target(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    by_uri = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "item", "query:Synths#Operator"],
    )
    by_path = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "item", "instruments/Operator"],
    )

    assert by_uri.exit_code == 0
    assert by_path.exit_code == 0

    uri_payload = json.loads(by_uri.stdout)
    path_payload = json.loads(by_path.stdout)
    assert uri_payload["result"]["uri"] == "query:Synths#Operator"
    assert uri_payload["result"]["path"] is None
    assert path_payload["result"]["path"] == "instruments/Operator"
    assert path_payload["result"]["uri"] is None


def test_browser_items_includes_pagination_fields(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "items",
            "drums",
            "--item-type",
            "loadable",
            "--limit",
            "100",
            "--offset",
            "0",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["limit"] == 100
    assert payload["result"]["offset"] == 0
    assert payload["result"]["has_more"] is False


def test_browser_search_includes_duration_ms(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "search", "drift", "--item-type", "loadable"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["duration_ms"] == 1.23


def test_browser_load_supports_uri_and_path_target(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    by_uri = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "load", "0", "query:Synths#Operator"],
    )
    by_path = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "load", "0", "instruments/Operator"],
    )

    assert by_uri.exit_code == 0
    assert by_path.exit_code == 0

    uri_payload = json.loads(by_uri.stdout)
    path_payload = json.loads(by_path.stdout)
    assert uri_payload["result"]["uri"] == "query:Synths#Operator"
    assert uri_payload["result"]["path"] is None
    assert path_payload["result"]["path"] == "instruments/Operator"
    assert path_payload["result"]["uri"] is None


def test_browser_load_supports_target_track_mode_clip_slot_and_preserve_track_name(
    runner,
    cli_app,
    monkeypatch,
) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "1",
            "sounds/Bass Loop.alc",
            "--target-track-mode",
            "existing",
            "--clip-slot",
            "3",
            "--preserve-track-name",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["track"] == 1
    assert payload["result"]["target_track_mode"] == "existing"
    assert payload["result"]["clip_slot"] == 3
    assert payload["result"]["preserve_track_name"] is True


def test_browser_load_drum_kit_supports_kit_uri_or_path(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import browser

    monkeypatch.setattr(browser, "get_client", lambda ctx: _ClientStub())

    by_uri = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load-drum-kit",
            "0",
            "rack:drums",
            "--kit-uri",
            "kit:acoustic",
        ],
    )
    by_path = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load-drum-kit",
            "0",
            "rack:drums",
            "--kit-path",
            "drums/Kits/Acoustic Kit",
        ],
    )

    assert by_uri.exit_code == 0
    assert by_path.exit_code == 0
    uri_payload = json.loads(by_uri.stdout)
    path_payload = json.loads(by_path.stdout)
    assert uri_payload["result"]["kit_uri"] == "kit:acoustic"
    assert uri_payload["result"]["kit_path"] is None
    assert path_payload["result"]["kit_path"] == "drums/Kits/Acoustic Kit"
    assert path_payload["result"]["kit_uri"] is None


def test_track_mixer_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import track

    monkeypatch.setattr(track, "get_client", lambda ctx: _ClientStub())

    mute = runner.invoke(cli_app, ["--output", "json", "track", "mute", "set", "0", "true"])
    solo = runner.invoke(cli_app, ["--output", "json", "track", "solo", "get", "0"])
    arm = runner.invoke(cli_app, ["--output", "json", "track", "arm", "set", "0", "false"])
    panning = runner.invoke(
        cli_app,
        ["--output", "json", "track", "panning", "set", "0", "--", "-0.3"],
    )

    assert mute.exit_code == 0
    assert solo.exit_code == 0
    assert arm.exit_code == 0
    assert panning.exit_code == 0

    mute_payload = json.loads(mute.stdout)
    solo_payload = json.loads(solo.stdout)
    arm_payload = json.loads(arm.stdout)
    panning_payload = json.loads(panning.stdout)
    assert mute_payload["result"]["mute"] is True
    assert solo_payload["result"]["solo"] is False
    assert arm_payload["result"]["arm"] is False
    assert panning_payload["result"]["panning"] == -0.3


def test_scenes_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import scenes

    monkeypatch.setattr(scenes, "get_client", lambda ctx: _ClientStub())

    listed = runner.invoke(cli_app, ["--output", "json", "scenes", "list"])
    created = runner.invoke(cli_app, ["--output", "json", "scenes", "create", "--index", "1"])
    renamed = runner.invoke(
        cli_app,
        ["--output", "json", "scenes", "name", "set", "1", "Build"],
    )
    fired = runner.invoke(cli_app, ["--output", "json", "scenes", "fire", "1"])

    assert listed.exit_code == 0
    assert created.exit_code == 0
    assert renamed.exit_code == 0
    assert fired.exit_code == 0

    listed_payload = json.loads(listed.stdout)
    created_payload = json.loads(created.stdout)
    renamed_payload = json.loads(renamed.stdout)
    fired_payload = json.loads(fired.stdout)
    assert listed_payload["result"]["scenes"][0]["name"] == "Intro"
    assert created_payload["result"]["index"] == 1
    assert renamed_payload["result"]["name"] == "Build"
    assert fired_payload["result"]["fired"] is True


def test_clip_duplicate_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    duplicated = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "duplicate", "0", "1", "2"],
    )
    assert duplicated.exit_code == 0
    payload = json.loads(duplicated.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 0, "src_clip": 1, "dst_clip": 2, "duplicated": True}


def test_clip_active_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip

    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())

    active_get = runner.invoke(cli_app, ["--output", "json", "clip", "active", "get", "0", "1"])
    active_set = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "active", "set", "0", "1", "false"],
    )

    assert active_get.exit_code == 0
    assert active_set.exit_code == 0
    payload_get = json.loads(active_get.stdout)
    payload_set = json.loads(active_set.stdout)
    assert payload_get["result"] == {"track": 0, "clip": 1, "active": True}
    assert payload_set["result"] == {"track": 0, "clip": 1, "active": False}


def test_scenes_move_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import scenes

    monkeypatch.setattr(scenes, "get_client", lambda ctx: _ClientStub())

    moved = runner.invoke(
        cli_app,
        ["--output", "json", "scenes", "move", "3", "1"],
    )
    assert moved.exit_code == 0
    payload = json.loads(moved.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"from": 3, "to": 1, "moved": True}


def test_tracks_delete_command_outputs_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import tracks

    monkeypatch.setattr(tracks, "get_client", lambda ctx: _ClientStub())

    deleted = runner.invoke(cli_app, ["--output", "json", "tracks", "delete", "1"])
    assert deleted.exit_code == 0
    payload = json.loads(deleted.stdout)
    assert payload["ok"] is True
    assert payload["result"] == {"track": 1, "deleted": True}


def test_arrangement_record_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import arrangement

    monkeypatch.setattr(arrangement, "get_client", lambda ctx: _ClientStub())

    started = runner.invoke(cli_app, ["--output", "json", "arrangement", "record", "start"])
    stopped = runner.invoke(cli_app, ["--output", "json", "arrangement", "record", "stop"])

    assert started.exit_code == 0
    assert stopped.exit_code == 0
    started_payload = json.loads(started.stdout)
    stopped_payload = json.loads(stopped.stdout)
    assert started_payload["result"]["recording"] is True
    assert stopped_payload["result"]["recording"] is False


def test_new_commands_validate_arguments_with_exit_code_2(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import clip, scenes, song, tracks

    monkeypatch.setattr(song, "get_client", lambda ctx: _ClientStub())
    monkeypatch.setattr(clip, "get_client", lambda ctx: _ClientStub())
    monkeypatch.setattr(scenes, "get_client", lambda ctx: _ClientStub())
    monkeypatch.setattr(tracks, "get_client", lambda ctx: _ClientStub())

    song_save = runner.invoke(cli_app, ["--output", "json", "song", "save", "--path", "   "])
    song_export = runner.invoke(
        cli_app,
        ["--output", "json", "song", "export", "audio", "--path", " "],
    )
    clip_duplicate = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "duplicate", "0", "1", "--", "-1"],
    )
    scenes_move = runner.invoke(cli_app, ["--output", "json", "scenes", "move", "--", "-1", "0"])
    tracks_delete = runner.invoke(cli_app, ["--output", "json", "tracks", "delete", "--", "-1"])

    assert song_save.exit_code == 2
    assert song_export.exit_code == 2
    assert clip_duplicate.exit_code == 2
    assert scenes_move.exit_code == 2
    assert tracks_delete.exit_code == 2

    assert json.loads(song_save.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(song_export.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(clip_duplicate.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(scenes_move.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(tracks_delete.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_batch_run_outputs_json_envelope(runner, cli_app, monkeypatch, tmp_path: Path) -> None:
    from ableton_cli.commands import batch

    monkeypatch.setattr(batch, "get_client", lambda ctx: _ClientStub())

    steps_path = tmp_path / "steps.json"
    steps_path.write_text(
        json.dumps(
            {
                "steps": [
                    {"name": "transport_tempo_set", "args": {"bpm": 128}},
                    {"name": "tracks_list", "args": {}},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli_app,
        ["--output", "json", "batch", "run", "--steps-file", str(steps_path)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["step_count"] == 2


def test_batch_run_accepts_steps_json(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    monkeypatch.setattr(batch, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--steps-json",
            json.dumps({"steps": [{"name": "tracks_list", "args": {}}]}),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["step_count"] == 1


def test_batch_run_accepts_steps_stdin(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import batch

    monkeypatch.setattr(batch, "get_client", lambda ctx: _ClientStub())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "batch", "run", "--steps-stdin"],
        input=json.dumps({"steps": [{"name": "tracks_list", "args": {}}]}),
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["step_count"] == 1


def test_wait_ready_succeeds_when_ping_is_ready(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    monkeypatch.setattr(setup, "get_client", lambda ctx: _WaitReadyClientAlwaysReady())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "wait-ready", "--max-wait-ms", "100", "--interval-ms", "1"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["ready"] is True


def test_wait_ready_retries_until_ready(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    client = _WaitReadyClientEventuallyReady()
    monkeypatch.setattr(setup, "get_client", lambda ctx: client)

    result = runner.invoke(
        cli_app,
        ["--output", "json", "wait-ready", "--max-wait-ms", "100", "--interval-ms", "1"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["attempts"] == 3


def test_wait_ready_times_out_when_ping_never_recovers(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import setup

    monkeypatch.setattr(setup, "get_client", lambda ctx: _WaitReadyClientNeverReady())

    result = runner.invoke(
        cli_app,
        ["--output", "json", "wait-ready", "--max-wait-ms", "1", "--interval-ms", "1"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "TIMEOUT"


def test_synth_foundation_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import synth

    monkeypatch.setattr(synth, "get_client", lambda ctx: _ClientStub())

    found = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "find", "--track", "0", "--type", "wavetable"],
    )
    listed = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "parameters", "list", "0", "1"],
    )
    set_result = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "parameter", "set", "0", "1", "0", "0.77"],
    )
    observed = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "observe", "0", "1"],
    )

    assert found.exit_code == 0
    assert listed.exit_code == 0
    assert set_result.exit_code == 0
    assert observed.exit_code == 0

    found_payload = json.loads(found.stdout)
    listed_payload = json.loads(listed.stdout)
    set_payload = json.loads(set_result.stdout)
    observed_payload = json.loads(observed.stdout)
    assert found_payload["result"]["synth_type"] == "wavetable"
    assert listed_payload["result"]["parameters"][0]["name"] == "Filter Freq"
    assert set_payload["result"]["after"] == 0.77
    assert observed_payload["result"]["detected_type"] == "wavetable"


def test_synth_standard_wrapper_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import synth

    monkeypatch.setattr(synth, "get_client", lambda ctx: _ClientStub())

    keys = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "wavetable", "keys"],
    )
    set_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "synth",
            "wavetable",
            "set",
            "0",
            "1",
            "filter_cutoff",
            "0.62",
        ],
    )
    observed = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "wavetable", "observe", "0", "1"],
    )

    assert keys.exit_code == 0
    assert set_result.exit_code == 0
    assert observed.exit_code == 0

    keys_payload = json.loads(keys.stdout)
    set_payload = json.loads(set_result.stdout)
    observed_payload = json.loads(observed.stdout)
    assert keys_payload["result"]["key_count"] == 9
    assert set_payload["result"]["key"] == "filter_cutoff"
    assert set_payload["result"]["after"] == 0.62
    assert observed_payload["result"]["state"]["filter_cutoff"] == 0.5


def test_effect_foundation_commands_output_json_envelope(runner, cli_app, monkeypatch) -> None:
    from ableton_cli.commands import effect

    monkeypatch.setattr(effect, "get_client", lambda ctx: _ClientStub())

    found = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "find", "--track", "0", "--type", "eq8"],
    )
    listed = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "parameters", "list", "0", "2"],
    )
    set_result = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "parameter", "set", "0", "2", "0", "0.77"],
    )
    observed = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "observe", "0", "2"],
    )

    assert found.exit_code == 0
    assert listed.exit_code == 0
    assert set_result.exit_code == 0
    assert observed.exit_code == 0

    found_payload = json.loads(found.stdout)
    listed_payload = json.loads(listed.stdout)
    set_payload = json.loads(set_result.stdout)
    observed_payload = json.loads(observed.stdout)
    assert found_payload["result"]["effect_type"] == "eq8"
    assert listed_payload["result"]["parameters"][0]["name"] == "1 Frequency A"
    assert set_payload["result"]["after"] == 0.77
    assert observed_payload["result"]["detected_type"] == "eq8"


def test_effect_standard_wrapper_commands_output_json_envelope(
    runner, cli_app, monkeypatch
) -> None:
    from ableton_cli.commands import effect

    monkeypatch.setattr(effect, "get_client", lambda ctx: _ClientStub())

    keys = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "eq8", "keys"],
    )
    set_result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "effect",
            "eq8",
            "set",
            "0",
            "2",
            "band1_freq",
            "0.62",
        ],
    )
    observed = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "eq8", "observe", "0", "2"],
    )

    assert keys.exit_code == 0
    assert set_result.exit_code == 0
    assert observed.exit_code == 0

    keys_payload = json.loads(keys.stdout)
    set_payload = json.loads(set_result.stdout)
    observed_payload = json.loads(observed.stdout)
    assert keys_payload["result"]["key_count"] == 5
    assert set_payload["result"]["key"] == "band1_freq"
    assert set_payload["result"]["after"] == 0.62
    assert observed_payload["result"]["state"]["band1_freq"] == 0.5
