from __future__ import annotations

import json


def test_tempo_set_rejects_out_of_range_value(runner, cli_app) -> None:
    result = runner.invoke(cli_app, ["--output", "json", "transport", "tempo", "set", "10"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_track_volume_set_rejects_out_of_range_value(runner, cli_app) -> None:
    result = runner.invoke(cli_app, ["--output", "json", "track", "volume", "set", "0", "1.2"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_tracks_create_audio_rejects_index_below_minus_one(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "tracks", "create", "audio", "--index", "-2"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_create_rejects_non_positive_length(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "create", "0", "0", "--length", "0"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_add_rejects_invalid_json(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "add",
            "0",
            "0",
            "--notes-json",
            "not-json",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_add_rejects_notes_json_and_notes_file_together(
    runner, cli_app, tmp_path
) -> None:
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
            "0",
            "--notes-json",
            '[{"pitch":60,"start_time":0.0,"duration":0.5,"velocity":100,"mute":false}]',
            "--notes-file",
            str(notes_path),
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_replace_requires_notes_input(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "notes", "replace", "0", "0"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_add_rejects_invalid_notes_file_json(runner, cli_app, tmp_path) -> None:
    notes_path = tmp_path / "broken-notes.json"
    notes_path.write_text("not-json", encoding="utf-8")

    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "add",
            "0",
            "0",
            "--notes-file",
            str(notes_path),
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_quantize_rejects_invalid_strength(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "quantize",
            "0",
            "0",
            "--grid",
            "1/16",
            "--strength",
            "1.5",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_humanize_rejects_invalid_velocity(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "humanize",
            "0",
            "0",
            "--timing",
            "0.1",
            "--velocity",
            "128",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_velocity_scale_rejects_negative_scale(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "velocity-scale",
            "0",
            "0",
            "--scale",
            "-0.5",
            "--offset",
            "0",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_groove_set_rejects_invalid_target(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "groove", "set", "0", "0", "hiphop"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_groove_amount_set_rejects_out_of_range_value(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "groove", "amount", "set", "0", "0", "1.5"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_item_requires_target(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "item"],
    )

    assert result.exit_code == 2


def test_browser_item_rejects_non_uri_non_path_target(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "item", "drift"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_items_rejects_invalid_limit(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "items", "drums", "--limit", "0"],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_items_rejects_negative_offset(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "items", "drums", "--offset", "-1"],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_search_rejects_empty_query(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "search", "  "],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_search_rejects_invalid_limit(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "search", "drift", "--limit", "0"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_search_rejects_negative_offset(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "search", "drift", "--offset", "-1"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_search_rejects_invalid_item_type(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "search", "drift", "--item-type", "unknown"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_load_requires_target(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "load", "0"],
    )

    assert result.exit_code == 2


def test_browser_load_rejects_non_uri_non_path_target(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "load", "0", "drift"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_load_rejects_invalid_target_track_mode(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "0",
            "instruments/Operator",
            "--target-track-mode",
            "legacy",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_load_rejects_negative_clip_slot(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "0",
            "instruments/Operator",
            "--clip-slot",
            "-1",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_load_rejects_invalid_notes_mode(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "0",
            "sounds/Bass Loop.alc",
            "--target-track-mode",
            "existing",
            "--clip-slot",
            "1",
            "--notes-mode",
            "merge",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_load_rejects_import_flags_without_notes_mode(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "browser",
            "load",
            "0",
            "sounds/Bass Loop.alc",
            "--target-track-mode",
            "existing",
            "--clip-slot",
            "1",
            "--import-length",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_browser_load_drum_kit_requires_exactly_one_kit_selector(runner, cli_app) -> None:
    none_selected = runner.invoke(
        cli_app,
        ["--output", "json", "browser", "load-drum-kit", "0", "rack:drums"],
    )
    both_selected = runner.invoke(
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
            "--kit-path",
            "drums/Kits/Acoustic Kit",
        ],
    )

    assert none_selected.exit_code == 2
    assert both_selected.exit_code == 2
    assert json.loads(none_selected.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(both_selected.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_duplicate_rejects_invalid_to_list(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "duplicate", "0", "1", "--to", "1,2"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_duplicate_many_rejects_empty_to_list(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "duplicate-many", "0", "1", "--to", ""],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_place_pattern_rejects_descending_range(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "place-pattern", "0", "--clip", "1", "--scenes", "5-2"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_name_set_many_rejects_invalid_map_entry(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "name", "set-many", "0", "--map", "1Main,2:Var"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_import_browser_rejects_invalid_mode(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "import-browser",
            "0",
            "1",
            "sounds/Bass Loop.alc",
            "--mode",
            "merge",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_filters_reject_invalid_range(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "clip",
            "notes",
            "get",
            "0",
            "0",
            "--start-time",
            "2.0",
            "--end-time",
            "2.0",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_clip_notes_filters_reject_invalid_pitch(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "clip", "notes", "clear", "0", "0", "--pitch", "200"],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_track_panning_set_rejects_out_of_range_value(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "track", "panning", "set", "0", "1.1"],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_scenes_create_rejects_index_below_minus_one(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "scenes", "create", "--index", "-2"],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_scene_command_is_removed(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "scene", "list"],
    )

    assert result.exit_code == 2


def test_tracks_create_midi_rejects_legacy_positional_minus_one(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "tracks", "create", "midi", "-1"],
    )
    assert result.exit_code == 2


def test_scenes_create_rejects_legacy_positional_minus_one(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "scenes", "create", "-1"],
    )
    assert result.exit_code == 2


def test_batch_run_requires_exactly_one_input_source(runner, cli_app, tmp_path) -> None:
    steps_path = tmp_path / "steps.json"
    steps_path.write_text('{"steps":[{"name":"tracks_list","args":{}}]}', encoding="utf-8")

    none_selected = runner.invoke(
        cli_app,
        ["--output", "json", "batch", "run"],
    )
    both_selected = runner.invoke(
        cli_app,
        [
            "--output",
            "json",
            "batch",
            "run",
            "--steps-file",
            str(steps_path),
            "--steps-json",
            '{"steps":[{"name":"tracks_list","args":{}}]}',
        ],
    )

    assert none_selected.exit_code == 2
    assert both_selected.exit_code == 2
    assert json.loads(none_selected.stdout)["error"]["code"] == "INVALID_ARGUMENT"
    assert json.loads(both_selected.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_synth_find_rejects_negative_track(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "find", "--track", "-1"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_synth_find_rejects_unknown_type(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "find", "--type", "operator"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_synth_parameter_set_rejects_negative_parameter_index(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "parameter", "set", "0", "1", "--", "-1", "0.5"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_synth_standard_set_rejects_empty_key(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "synth", "wavetable", "set", "0", "1", "   ", "0.5"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_effect_find_rejects_unknown_type(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "find", "--type", "phaser"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_effect_standard_set_rejects_empty_key(runner, cli_app) -> None:
    result = runner.invoke(
        cli_app,
        ["--output", "json", "effect", "eq8", "set", "0", "2", "   ", "0.5"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
