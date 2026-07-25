"""Declarative table of the per-facet track commands.

``track volume|panning|mute|solo|arm|name`` differ only in their name, the
client method they call, and the type of the value they carry. That table
lives here, in the core layer, so both the command surface
(``commands/_track_facets.py``, which generates the Typer commands) and
the contract registry (``command_specs``, which needs the command names)
read the same source instead of re-deriving them — command_specs must not
import the commands package, so the data cannot live there.

Value validation stays in the command layer: it needs the CLI error types.
"""

from __future__ import annotations

from dataclasses import dataclass

TRACK_INFO_COMMAND = "track info"
TRACK_INFO_CLIENT_METHOD = "get_track_info"


@dataclass(frozen=True, slots=True)
class TrackFacetSpec:
    """One ``track <facet>`` sub-app: an optional get, an optional set."""

    name: str
    help: str
    client_get: str | None
    client_set: str | None
    value_kind: str = "bool"
    value_help: str = ""
    value_metavar: str = "VALUE"
    value_arg_name: str = "value"

    @property
    def get_command_name(self) -> str | None:
        return None if self.client_get is None else f"track {self.name} get"

    @property
    def set_command_name(self) -> str | None:
        return None if self.client_set is None else f"track {self.name} set"


TRACK_FACET_SPECS: tuple[TrackFacetSpec, ...] = (
    TrackFacetSpec(
        name="volume",
        help="Track volume commands",
        client_get="track_volume_get",
        client_set="track_volume_set",
        value_kind="float",
        value_help="Volume value in [0.0, 1.0]",
    ),
    TrackFacetSpec(
        name="name",
        help="Track naming commands",
        client_get=None,
        client_set="set_track_name",
        value_kind="str",
        value_help="New track name",
        value_metavar="NAME",
        value_arg_name="name",
    ),
    TrackFacetSpec(
        name="mute",
        help="Track mute commands",
        client_get="track_mute_get",
        client_set="track_mute_set",
        value_help="Mute value: true|false",
    ),
    TrackFacetSpec(
        name="solo",
        help="Track solo commands",
        client_get="track_solo_get",
        client_set="track_solo_set",
        value_help="Solo value: true|false",
    ),
    TrackFacetSpec(
        name="arm",
        help="Track arm commands",
        client_get="track_arm_get",
        client_set="track_arm_set",
        value_help="Arm value: true|false",
    ),
    TrackFacetSpec(
        name="panning",
        help="Track panning commands",
        client_get="track_panning_get",
        client_set="track_panning_set",
        value_kind="float",
        value_help="Panning value in [-1.0, 1.0]",
    ),
)


def track_facet_command_names() -> set[str]:
    """Every public command name generated from the facet table."""
    names = {TRACK_INFO_COMMAND}
    for facet in TRACK_FACET_SPECS:
        names.update(
            name for name in (facet.get_command_name, facet.set_command_name) if name is not None
        )
    return names
