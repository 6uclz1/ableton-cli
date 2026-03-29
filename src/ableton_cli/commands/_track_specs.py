from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic

from ._track_shared import TValue, ValueValidator


@dataclass(frozen=True)
class TrackCommandSpec:
    command_name: str
    client_method: str


@dataclass(frozen=True)
class TrackValueCommandSpec(Generic[TValue]):
    command_name: str
    client_method: str
    value_name: str = "value"
    validators: Sequence[ValueValidator[TValue]] | None = None
