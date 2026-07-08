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
