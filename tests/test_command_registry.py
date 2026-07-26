from __future__ import annotations


def test_transport_command_specs_validate_against_current_surfaces() -> None:
    from ableton_cli.actions import stable_action_capability_map, stable_action_command_map
    from ableton_cli.capabilities import required_remote_commands
    from ableton_cli.command_specs import TRANSPORT_COMMAND_SPECS, public_command_names
    from ableton_cli.commands import transport
    from ableton_cli.contracts.registry import get_registered_contracts

    contracts = get_registered_contracts()
    action_commands = stable_action_command_map()
    action_capabilities = stable_action_capability_map()
    required = required_remote_commands()
    public_commands = public_command_names()
    module_specs = {
        item.command_name: item.client_method
        for item in (
            transport.TRANSPORT_PLAY_SPEC,
            transport.TRANSPORT_STOP_SPEC,
            transport.TRANSPORT_TOGGLE_SPEC,
            transport.TRANSPORT_TEMPO_GET_SPEC,
            transport.TRANSPORT_TEMPO_SET_SPEC,
            transport.TRANSPORT_POSITION_GET_SPEC,
            transport.TRANSPORT_POSITION_SET_SPEC,
            transport.TRANSPORT_REWIND_SPEC,
        )
    }

    for spec in TRANSPORT_COMMAND_SPECS:
        assert spec.command_name in public_commands
        assert module_specs[spec.command_name] == spec.client_method
        assert spec.remote_command in required
        assert spec.command_name in contracts
        if spec.action_name is None:
            continue
        assert action_commands[spec.action_name] == spec.action_command
        assert action_capabilities[spec.action_name] == spec.capability


def test_required_remote_commands_are_derived_from_command_specs() -> None:
    from ableton_cli.capabilities import required_remote_commands
    from ableton_cli.command_specs import remote_command_names

    assert required_remote_commands() == remote_command_names()


def test_remote_handler_registry_matches_command_specs() -> None:
    from ableton_cli.command_specs import remote_command_names
    from remote_script.AbletonCliRemote.command_backend_registry import _HANDLERS

    assert set(_HANDLERS) == remote_command_names()


def test_public_contract_registry_covers_all_public_commands() -> None:
    from ableton_cli.command_specs import public_command_names
    from ableton_cli.contracts.registry import get_registered_contracts

    assert set(get_registered_contracts()) == public_command_names()


def test_public_contract_registry_includes_errors_and_side_effect_metadata() -> None:
    from ableton_cli.contracts.registry import get_registered_contracts

    contracts = get_registered_contracts()

    assert contracts
    for contract in contracts.values():
        assert "args" in contract
        assert "result" in contract
        assert "errors" in contract
        assert "side_effect" in contract


def test_read_only_remote_commands_are_derived_from_contract_metadata() -> None:
    from ableton_cli.capabilities import read_only_remote_commands
    from ableton_cli.contracts.registry import read_only_remote_command_names

    assert read_only_remote_commands() == read_only_remote_command_names()


def test_every_public_command_declares_a_side_effect() -> None:
    from ableton_cli.command_specs import _SIDE_EFFECTS, public_command_names

    assert set(_SIDE_EFFECTS) == public_command_names()


def test_side_effect_table_has_no_entries_for_removed_commands() -> None:
    from ableton_cli.command_specs import _SIDE_EFFECTS, public_command_names

    assert sorted(set(_SIDE_EFFECTS) - public_command_names()) == []


def test_undeclared_command_has_no_default_side_effect() -> None:
    import pytest

    from ableton_cli.command_specs import _side_effect_spec

    with pytest.raises(KeyError, match="no declared side effect"):
        _side_effect_spec("totally not a command")


def test_destructive_commands_always_require_confirmation() -> None:
    from ableton_cli.command_specs import _SIDE_EFFECTS

    destructive = [spec for spec in _SIDE_EFFECTS.values() if spec.kind == "destructive"]

    assert destructive
    assert all(spec.requires_confirmation for spec in destructive)


def test_read_commands_are_always_idempotent() -> None:
    from ableton_cli.command_specs import _SIDE_EFFECTS

    reads = [spec for spec in _SIDE_EFFECTS.values() if spec.kind == "read"]

    assert reads
    assert all(spec.idempotent for spec in reads)


def test_only_read_commands_are_reachable_under_read_only() -> None:
    from ableton_cli.command_specs import command_specs, read_only_remote_command_names

    read_only = read_only_remote_command_names()
    writable_remote_commands = {
        spec.remote_command
        for spec in command_specs()
        if spec.remote_command is not None and spec.side_effect.kind != "read"
    }

    assert read_only.isdisjoint(writable_remote_commands)


def test_generated_command_families_are_declared_individually() -> None:
    from ableton_cli.command_specs import (
        _SIDE_EFFECTS,
        _STANDARD_EFFECT_TYPES,
        _STANDARD_SYNTH_TYPES,
    )

    for synth_type in _STANDARD_SYNTH_TYPES:
        for suffix in ("keys", "set", "observe"):
            assert f"synth {synth_type} {suffix}" in _SIDE_EFFECTS
    for effect_type in _STANDARD_EFFECT_TYPES:
        for suffix in ("keys", "set", "observe"):
            assert f"effect {effect_type} {suffix}" in _SIDE_EFFECTS
    for effect_type in ("eq8", "limiter", "compressor", "utility"):
        for suffix in ("keys", "set", "observe"):
            assert f"master effect {effect_type} {suffix}" in _SIDE_EFFECTS


def test_remote_command_spec_map_covers_every_dispatchable_remote_command() -> None:
    from ableton_cli.command_specs import (
        _REMOTE_COMMAND_ALIASES,
        remote_command_names,
        remote_command_spec_map,
    )

    assert set(remote_command_spec_map()) == remote_command_names() - _REMOTE_COMMAND_ALIASES


def test_remote_command_spec_map_merges_collisions_on_the_safe_side() -> None:
    from ableton_cli.command_specs import command_spec_map, remote_command_spec_map

    cli_specs = command_spec_map()
    # `browser load` (write) and `clip notes import-browser` (destructive) both
    # dispatch load_instrument_or_effect.
    assert cli_specs["browser load"].side_effect.kind == "write"
    assert cli_specs["clip notes import-browser"].side_effect.kind == "destructive"

    merged = remote_command_spec_map()["load_instrument_or_effect"].side_effect
    assert merged.kind == "destructive"
    assert merged.idempotent is False
    assert merged.requires_confirmation is True


def test_remote_command_spec_map_marks_note_writes_non_idempotent() -> None:
    from ableton_cli.command_specs import remote_command_spec_map

    specs = remote_command_spec_map()

    assert specs["add_notes_to_clip"].side_effect.idempotent is False
    assert specs["tracks_list"].side_effect.idempotent is True
