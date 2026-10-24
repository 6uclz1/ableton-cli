"""Fixtures for offline ``.als`` tests; the builder lives in ``live_set_builder``."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from live_set_builder import SetSpec, build_live_set_xml, write_live_set

LiveSetFactory = Callable[..., Path]


@pytest.fixture
def live_set_factory(tmp_path: Path) -> Iterator[LiveSetFactory]:
    """Write a synthetic set; ``mutate`` may edit the XML before it is written."""

    def _factory(
        spec: SetSpec | None = None,
        *,
        name: str = "Test.als",
        mutate: Callable[[ET.Element], None] | None = None,
    ) -> Path:
        root = build_live_set_xml(spec or SetSpec())
        if mutate is not None:
            mutate(root)
        return write_live_set(tmp_path / name, root)

    yield _factory
