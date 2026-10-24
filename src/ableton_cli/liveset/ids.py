"""The global pointee-ID space of a Live Set.

``Id`` on these elements is unique across the whole document, stays below
``LiveSet/NextPointeeId`` and is what ``PointeeId`` values refer to. Every other
``Id`` attribute (events, key tracks, clip slots, ...) is a local list index.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator

GLOBAL_ID_TAG = re.compile(
    r"^(?:AutomationTarget|\w*ModulationTarget|Pointee|ControllerTargets\.\d+)$"
)


def global_id_elements(root: ET.Element) -> Iterator[ET.Element]:
    return (element for element in root.iter() if GLOBAL_ID_TAG.match(element.tag))


def pointee_references(root: ET.Element) -> Iterator[str]:
    return (element.get("Value", "") for element in root.iter("PointeeId"))
