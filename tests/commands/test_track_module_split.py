from __future__ import annotations

import typer

from ableton_cli.command_specs import public_command_names
from ableton_cli.commands._track_facets import get_spec, register_track_facets, set_spec
from ableton_cli.track_facets import TRACK_FACET_SPECS, track_facet_command_names


def _facet_names() -> set[str]:
    return {facet.name for facet in TRACK_FACET_SPECS}


def test_facet_table_covers_the_documented_track_surface() -> None:
    assert _facet_names() == {"volume", "panning", "mute", "solo", "arm", "name"}


def test_generated_command_names_are_in_the_public_surface() -> None:
    generated = track_facet_command_names()
    assert "track info" in generated
    assert "track volume get" in generated
    assert "track name set" in generated
    assert "track name get" not in generated  # naming is set-only
    assert generated <= public_command_names()


def test_register_track_facets_builds_one_sub_app_per_facet() -> None:
    calls: list[tuple[str, object]] = []
    track_app = typer.Typer()

    facet_apps = register_track_facets(
        track_app,
        run_track_command_spec=lambda ctx, **kwargs: calls.append(("get", kwargs)),
        run_track_value_command_spec=lambda ctx, **kwargs: calls.append(("set", kwargs)),
    )

    assert set(facet_apps) == _facet_names()
    assert [info.name for info in track_app.registered_commands] == ["info"]
    for facet in TRACK_FACET_SPECS:
        registered = {info.name for info in facet_apps[facet.name].registered_commands}
        expected = {"set"} | ({"get"} if facet.client_get is not None else set())
        assert registered == expected, facet.name


def test_generated_specs_carry_the_client_method_from_the_table() -> None:
    by_name = {facet.name: facet for facet in TRACK_FACET_SPECS}

    volume_get = get_spec(by_name["volume"])
    assert volume_get is not None
    assert volume_get.client_method == "track_volume_get"

    name_set = set_spec(by_name["name"])
    assert name_set is not None
    assert name_set.client_method == "set_track_name"
    assert name_set.value_name == "name"
    assert name_set.validators is not None

    assert get_spec(by_name["name"]) is None
