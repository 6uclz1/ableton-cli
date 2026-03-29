from __future__ import annotations


def test_transport_command_specs_validate_against_current_surfaces() -> None:
    from ableton_cli.command_specs import validate_transport_command_specs

    validate_transport_command_specs()


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
