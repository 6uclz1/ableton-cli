from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from ableton_cli.client.ableton_client import AbletonClient
from ableton_cli.config import Settings
from ableton_cli.errors import AppError, ExitCode


def _settings() -> Settings:
    return Settings(
        host="127.0.0.1",
        port=8765,
        timeout_ms=15000,
        log_level="INFO",
        log_file=None,
        protocol_version=2,
        config_path="/tmp/ableton-cli-test.toml",
    )


def _ok_response(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "request_id": request["request_id"],
        "protocol_version": request["protocol_version"],
        "result": result,
        "error": None,
    }


def _capture_requests(
    monkeypatch: pytest.MonkeyPatch,
    client: AbletonClient,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        return _ok_response(request, {"ok": True})

    monkeypatch.setattr(client.transport, "send", _send)
    return requests


def test_client_non_ping_command_sends_single_request_without_preflight(monkeypatch) -> None:
    client = AbletonClient(_settings())
    requests = _capture_requests(monkeypatch, client)

    client.song_info()

    assert [request["name"] for request in requests] == ["song_info"]


def test_client_does_not_retry_read_command_on_timeout(monkeypatch) -> None:
    client = AbletonClient(_settings())
    requests: list[dict[str, Any]] = []
    state = {"song_info_calls": 0}

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        if request["name"] == "song_info":
            state["song_info_calls"] += 1
            raise AppError(
                error_code="TIMEOUT",
                message="Timed out while communicating with 127.0.0.1:8765",
                hint="Increase --timeout-ms or verify Ableton Remote Script responsiveness.",
                exit_code=ExitCode.TIMEOUT,
            )
        return _ok_response(request, {})

    monkeypatch.setattr(client.transport, "send", _send)

    with pytest.raises(AppError) as exc_info:
        client.song_info()

    assert exc_info.value.error_code == "TIMEOUT"
    assert [request["name"] for request in requests] == ["song_info"]


def test_client_does_not_retry_write_command_on_timeout(monkeypatch) -> None:
    client = AbletonClient(_settings())
    requests: list[dict[str, Any]] = []

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        if request["name"] == "track_volume_set":
            raise AppError(
                error_code="TIMEOUT",
                message="Timed out while communicating with 127.0.0.1:8765",
                hint="Increase --timeout-ms or verify Ableton Remote Script responsiveness.",
                exit_code=ExitCode.TIMEOUT,
            )
        return _ok_response(request, {})

    monkeypatch.setattr(client.transport, "send", _send)

    with pytest.raises(AppError) as exc_info:
        client.track_volume_set(0, 0.7)

    assert exc_info.value.error_code == "TIMEOUT"
    assert [request["name"] for request in requests] == ["track_volume_set"]


def test_client_read_only_blocks_write_command_before_transport(monkeypatch) -> None:
    client = AbletonClient(_settings(), read_only=True)
    requests: list[dict[str, Any]] = []

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        return _ok_response(request, {"ok": True})

    monkeypatch.setattr(client.transport, "send", _send)

    with pytest.raises(AppError) as exc_info:
        client.track_volume_set(0, 0.5)

    assert exc_info.value.error_code == "READ_ONLY_VIOLATION"
    assert requests == []


def test_client_read_only_allows_read_command(monkeypatch) -> None:
    client = AbletonClient(_settings(), read_only=True)
    requests: list[dict[str, Any]] = []

    def _send(request: dict[str, Any]):  # noqa: ANN202
        requests.append(request)
        return _ok_response(request, {"tempo": 120.0})

    monkeypatch.setattr(client.transport, "send", _send)

    result = client.song_info()

    assert result["tempo"] == 120.0
    assert [request["name"] for request in requests] == ["song_info"]


def test_client_sends_request_timeout_meta(monkeypatch) -> None:
    client = AbletonClient(_settings())
    requests = _capture_requests(monkeypatch, client)

    client.song_info()

    assert requests[0]["meta"]["request_timeout_ms"] == 15000


@pytest.mark.parametrize(
    ("runner", "expected_command", "expected_args"),
    [
        (
            lambda client: client.mixer_crossfader_set(value=0.2),
            "mixer_crossfader_set",
            {"value": 0.2},
        ),
        (
            lambda client: client.track_routing_input_set(
                track_ref={"mode": "index", "index": 0},
                routing_type="Ext. In",
                routing_channel="1/2",
            ),
            "track_routing_input_set",
            {
                "track_ref": {"mode": "index", "index": 0},
                "routing_type": "Ext. In",
                "routing_channel": "1/2",
            },
        ),
        (
            lambda client: client.track_routing_output_get(track_ref={"mode": "index", "index": 1}),
            "track_routing_output_get",
            {"track_ref": {"mode": "index", "index": 1}},
        ),
        (
            lambda client: client.master_info(),
            "master_info",
            {},
        ),
        (
            lambda client: client.master_devices_list(),
            "master_devices_list",
            {},
        ),
        (
            lambda client: client.return_tracks_list(),
            "return_tracks_list",
            {},
        ),
        (
            lambda client: client.return_track_volume_set(return_track=1, value=0.4),
            "return_track_volume_set",
            {"return_track": 1, "value": 0.4},
        ),
        (
            lambda client: client.return_track_solo_get(return_track=2),
            "return_track_solo_get",
            {"return_track": 2},
        ),
        (
            lambda client: client.track_send_get(track_ref={"mode": "index", "index": 1}, send=2),
            "track_send_get",
            {"track_ref": {"mode": "index", "index": 1}, "send": 2},
        ),
        (
            lambda client: client.track_send_set(
                track_ref={"mode": "index", "index": 3},
                send=4,
                value=0.75,
            ),
            "track_send_set",
            {"track_ref": {"mode": "index", "index": 3}, "send": 4, "value": 0.75},
        ),
        (
            lambda client: client.get_clip_notes(
                track=1,
                clip=2,
                start_time=None,
                end_time=4.0,
                pitch=None,
            ),
            "get_clip_notes",
            {"track": 1, "clip": 2, "end_time": 4.0},
        ),
        (
            lambda client: client.replace_clip_notes(
                track=3,
                clip=4,
                notes=[
                    {
                        "pitch": 60,
                        "start_time": 0.0,
                        "duration": 0.5,
                        "velocity": 100,
                        "mute": False,
                    }
                ],
                start_time=0.0,
                end_time=None,
                pitch=60,
            ),
            "replace_clip_notes",
            {
                "track": 3,
                "clip": 4,
                "notes": [
                    {
                        "pitch": 60,
                        "start_time": 0.0,
                        "duration": 0.5,
                        "velocity": 100,
                        "mute": False,
                    }
                ],
                "start_time": 0.0,
                "pitch": 60,
            },
        ),
        (
            lambda client: client.search_browser_items(
                query="drift",
                path=None,
                item_type="loadable",
                limit=10,
                offset=2,
                exact=True,
                case_sensitive=False,
            ),
            "search_browser_items",
            {
                "query": "drift",
                "item_type": "loadable",
                "limit": 10,
                "offset": 2,
                "exact": True,
                "case_sensitive": False,
            },
        ),
        (
            lambda client: client.search_browser_items(
                query="kit",
                path="drums/Kits",
                item_type="folder",
                limit=20,
                offset=0,
                exact=False,
                case_sensitive=True,
            ),
            "search_browser_items",
            {
                "query": "kit",
                "path": "drums/Kits",
                "item_type": "folder",
                "limit": 20,
                "offset": 0,
                "exact": False,
                "case_sensitive": True,
            },
        ),
        (
            lambda client: client.load_instrument_or_effect(
                track=2,
                uri=None,
                path="sounds/Bass Loop.alc",
                target_track_mode="existing",
                clip_slot=4,
                preserve_track_name=True,
            ),
            "load_instrument_or_effect",
            {
                "track": 2,
                "path": "sounds/Bass Loop.alc",
                "target_track_mode": "existing",
                "clip_slot": 4,
                "preserve_track_name": True,
            },
        ),
        (
            lambda client: client.load_instrument_or_effect(
                track=1,
                uri=None,
                path="sounds/Bass Loop.alc",
                target_track_mode="existing",
                clip_slot=3,
                notes_mode="append",
                import_length=True,
                import_groove=True,
            ),
            "load_instrument_or_effect",
            {
                "track": 1,
                "path": "sounds/Bass Loop.alc",
                "target_track_mode": "existing",
                "clip_slot": 3,
                "preserve_track_name": False,
                "notes_mode": "append",
                "import_length": True,
                "import_groove": True,
            },
        ),
        (
            lambda client: client.clip_notes_quantize(
                track=0,
                clip=1,
                grid="1/16",
                strength=0.75,
                start_time=0.0,
                end_time=4.0,
                pitch=60,
            ),
            "clip_notes_quantize",
            {
                "track": 0,
                "clip": 1,
                "grid": "1/16",
                "strength": 0.75,
                "start_time": 0.0,
                "end_time": 4.0,
                "pitch": 60,
            },
        ),
        (
            lambda client: client.clip_notes_transpose(
                track=0,
                clip=1,
                semitones=-12,
                start_time=None,
                end_time=None,
                pitch=None,
            ),
            "clip_notes_transpose",
            {
                "track": 0,
                "clip": 1,
                "semitones": -12,
            },
        ),
        (
            lambda client: client.clip_groove_set(
                track=0,
                clip=2,
                target="grooves/Hip Hop Boom Bap 16ths 90 bpm.agr",
            ),
            "clip_groove_set",
            {
                "track": 0,
                "clip": 2,
                "target": "grooves/Hip Hop Boom Bap 16ths 90 bpm.agr",
            },
        ),
        (
            lambda client: client.clip_cut_to_drum_rack(
                source_track=0,
                source_clip=1,
                source_uri=None,
                source_path=None,
                target_track=None,
                grid="1/8",
                slice_count=None,
                start_pad=4,
                create_trigger_clip=False,
                trigger_clip_slot=None,
            ),
            "clip_cut_to_drum_rack",
            {
                "source_track": 0,
                "source_clip": 1,
                "grid": "1/8",
                "start_pad": 4,
                "create_trigger_clip": False,
            },
        ),
        (
            lambda client: client.clip_cut_to_drum_rack(
                source_track=None,
                source_clip=None,
                source_uri=None,
                source_path="sounds/Bass Loop.wav",
                target_track=2,
                grid=None,
                slice_count=8,
                start_pad=0,
                create_trigger_clip=True,
                trigger_clip_slot=3,
            ),
            "clip_cut_to_drum_rack",
            {
                "source_path": "sounds/Bass Loop.wav",
                "target_track": 2,
                "slice_count": 8,
                "start_pad": 0,
                "create_trigger_clip": True,
                "trigger_clip_slot": 3,
            },
        ),
        (
            lambda client: client.clip_cut_to_drum_rack(
                source_track=None,
                source_clip=None,
                source_uri=None,
                source_path=None,
                target_track=None,
                grid=None,
                slice_count=None,
                start_pad=0,
                create_trigger_clip=False,
                trigger_clip_slot=None,
                source_file="/tmp/source.wav",
                source_file_duration_beats=8.0,
                slice_ranges=[
                    {"slice_start": 0.0, "slice_end": 1.5},
                    {"slice_start": 1.5, "slice_end": 2.0},
                ],
            ),
            "clip_cut_to_drum_rack",
            {
                "source_file": "/tmp/source.wav",
                "source_file_duration_beats": 8.0,
                "slice_ranges": [
                    {"slice_start": 0.0, "slice_end": 1.5},
                    {"slice_start": 1.5, "slice_end": 2.0},
                ],
                "start_pad": 0,
                "create_trigger_clip": False,
            },
        ),
        (
            lambda client: client.transport_position_get(),
            "transport_position_get",
            {},
        ),
        (
            lambda client: client.transport_position_set(32.0),
            "transport_position_set",
            {"beats": 32.0},
        ),
        (
            lambda client: client.transport_rewind(),
            "transport_rewind",
            {},
        ),
        (
            lambda client: client.arrangement_clip_create(
                track=0,
                start_time=8.0,
                length=4.0,
                audio_path=None,
            ),
            "arrangement_clip_create",
            {
                "track": 0,
                "start_time": 8.0,
                "length": 4.0,
            },
        ),
        (
            lambda client: client.arrangement_clip_create(
                track=1,
                start_time=16.0,
                length=8.0,
                audio_path="/tmp/loop.wav",
            ),
            "arrangement_clip_create",
            {
                "track": 1,
                "start_time": 16.0,
                "length": 8.0,
                "audio_path": "/tmp/loop.wav",
            },
        ),
        (
            lambda client: client.arrangement_clip_create(
                track=0,
                start_time=0.0,
                length=4.0,
                audio_path=None,
                notes=[
                    {
                        "pitch": 60,
                        "start_time": 0.0,
                        "duration": 0.5,
                        "velocity": 100,
                        "mute": False,
                    }
                ],
            ),
            "arrangement_clip_create",
            {
                "track": 0,
                "start_time": 0.0,
                "length": 4.0,
                "notes": [
                    {
                        "pitch": 60,
                        "start_time": 0.0,
                        "duration": 0.5,
                        "velocity": 100,
                        "mute": False,
                    }
                ],
            },
        ),
        (
            lambda client: client.arrangement_clip_list(track=None),
            "arrangement_clip_list",
            {},
        ),
        (
            lambda client: client.arrangement_clip_list(track=1),
            "arrangement_clip_list",
            {"track": 1},
        ),
        (
            lambda client: client.arrangement_clip_notes_add(
                track=0,
                index=1,
                notes=[
                    {
                        "pitch": 62,
                        "start_time": 0.0,
                        "duration": 0.5,
                        "velocity": 100,
                        "mute": False,
                    }
                ],
            ),
            "arrangement_clip_notes_add",
            {
                "track": 0,
                "index": 1,
                "notes": [
                    {
                        "pitch": 62,
                        "start_time": 0.0,
                        "duration": 0.5,
                        "velocity": 100,
                        "mute": False,
                    }
                ],
            },
        ),
        (
            lambda client: client.arrangement_clip_notes_get(
                track=0,
                index=1,
                start_time=0.0,
                end_time=4.0,
                pitch=62,
            ),
            "arrangement_clip_notes_get",
            {
                "track": 0,
                "index": 1,
                "start_time": 0.0,
                "end_time": 4.0,
                "pitch": 62,
            },
        ),
        (
            lambda client: client.arrangement_clip_notes_clear(
                track=0,
                index=1,
                start_time=None,
                end_time=None,
                pitch=None,
            ),
            "arrangement_clip_notes_clear",
            {
                "track": 0,
                "index": 1,
            },
        ),
        (
            lambda client: client.arrangement_clip_notes_replace(
                track=0,
                index=1,
                notes=[
                    {
                        "pitch": 64,
                        "start_time": 1.0,
                        "duration": 0.5,
                        "velocity": 90,
                        "mute": False,
                    }
                ],
                start_time=0.0,
                end_time=8.0,
                pitch=None,
            ),
            "arrangement_clip_notes_replace",
            {
                "track": 0,
                "index": 1,
                "notes": [
                    {
                        "pitch": 64,
                        "start_time": 1.0,
                        "duration": 0.5,
                        "velocity": 90,
                        "mute": False,
                    }
                ],
                "start_time": 0.0,
                "end_time": 8.0,
            },
        ),
        (
            lambda client: client.arrangement_clip_notes_import_browser(
                track=0,
                index=1,
                target_uri=None,
                target_path="sounds/Bass Loop.alc",
                mode="append",
                import_length=True,
                import_groove=False,
            ),
            "arrangement_clip_notes_import_browser",
            {
                "track": 0,
                "index": 1,
                "target_path": "sounds/Bass Loop.alc",
                "mode": "append",
                "import_length": True,
                "import_groove": False,
            },
        ),
        (
            lambda client: client.arrangement_clip_delete(
                track=0,
                index=None,
                start=8.0,
                end=16.0,
                delete_all=False,
            ),
            "arrangement_clip_delete",
            {"track": 0, "start": 8.0, "end": 16.0, "all": False},
        ),
        (
            lambda client: client.arrangement_from_session(
                scenes=[{"scene": 0, "duration_beats": 24.0}, {"scene": 1, "duration_beats": 48.0}]
            ),
            "arrangement_from_session",
            {
                "scenes": [
                    {"scene": 0, "duration_beats": 24.0},
                    {"scene": 1, "duration_beats": 48.0},
                ]
            },
        ),
    ],
)
def test_client_builds_optional_arguments_deterministically(
    monkeypatch: pytest.MonkeyPatch,
    runner: Callable[[AbletonClient], dict[str, Any]],
    expected_command: str,
    expected_args: dict[str, Any],
) -> None:
    client = AbletonClient(_settings())
    requests = _capture_requests(monkeypatch, client)
    runner(client)

    assert [request["name"] for request in requests] == [expected_command]
    assert requests[0]["args"] == expected_args


@pytest.mark.parametrize(
    ("runner", "expected_command", "expected_value"),
    [
        (
            lambda client: client.set_device_parameter(
                track_ref={"mode": "index", "index": 0},
                device_ref={"mode": "index", "index": 1},
                parameter_ref={"mode": "index", "index": 2},
                value=0.3,
            ),
            "set_device_parameter",
            0.3,
        ),
        (
            lambda client: client.set_synth_parameter_safe(
                track_ref={"mode": "index", "index": 0},
                device_ref={"mode": "index", "index": 1},
                parameter_ref={"mode": "index", "index": 2},
                value=0.4,
            ),
            "set_synth_parameter_safe",
            0.4,
        ),
        (
            lambda client: client.set_effect_parameter_safe(
                track_ref={"mode": "index", "index": 0},
                device_ref={"mode": "index", "index": 1},
                parameter_ref={"mode": "index", "index": 2},
                value=0.5,
            ),
            "set_effect_parameter_safe",
            0.5,
        ),
    ],
)
def test_client_parameter_commands_share_payload_shape(
    monkeypatch: pytest.MonkeyPatch,
    runner: Callable[[AbletonClient], dict[str, Any]],
    expected_command: str,
    expected_value: float,
) -> None:
    client = AbletonClient(_settings())
    requests = _capture_requests(monkeypatch, client)
    runner(client)

    assert requests[0]["name"] == expected_command
    assert requests[0]["args"] == {
        "track_ref": {"mode": "index", "index": 0},
        "device_ref": {"mode": "index", "index": 1},
        "parameter_ref": {"mode": "index", "index": 2},
        "value": expected_value,
    }
