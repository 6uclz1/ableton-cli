from __future__ import annotations

import pytest

from remote_script.AbletonCliRemote.live_backend_parts import browser_path_lookup
from remote_script.AbletonCliRemote.live_backend_parts.browser_catalog import (
    LiveBackendBrowserCatalogMixin,
)
from remote_script.AbletonCliRemote.live_backend_parts.browser_path_lookup import (
    LiveBackendBrowserPathLookupMixin,
)


class _Node:
    def __init__(self, name: str, uri: str, children: list[_Node] | None = None) -> None:
        self.name = name
        self.uri = uri
        self._children = children or []


class _Wrapper:
    """Like Live's BrowserItem: a fresh, short-lived proxy on every children access."""

    def __init__(self, node: _Node) -> None:
        self._node = node
        self.name = node.name
        self.uri = node.uri
        self.is_loadable = not node._children
        self.is_device = False

    @property
    def children(self) -> list[_Wrapper]:
        return [_Wrapper(child) for child in self._node._children]


class _Browser:
    def __init__(self) -> None:
        self.sounds = _Wrapper(
            _Node(
                "Sounds",
                "query:Sounds",
                [
                    _Node("Pad", "query:Sounds#Pad", [_Node("Saw Pad.adv", "query:Sounds#Pad:1")]),
                    _Node("Bass", "query:Sounds#Bass", [_Node("808.adg", "query:Sounds#Bass:2")]),
                ],
            )
        )


class _Lookup(LiveBackendBrowserCatalogMixin, LiveBackendBrowserPathLookupMixin):
    def __init__(self) -> None:
        self._fake_browser = _Browser()

    def _browser(self) -> _Browser:
        return self._fake_browser


@pytest.fixture
def reused_proxy_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    # Freed proxies hand their address to the next proxy, so id() repeats.
    monkeypatch.setattr(browser_path_lookup, "id", lambda _obj: 4242, raising=False)


@pytest.mark.usefixtures("reused_proxy_addresses")
@pytest.mark.parametrize(
    ("uri", "path"),
    [
        ("query:Sounds#Pad:1", "sounds/Pad/Saw Pad.adv"),
        ("query:Sounds#Bass:2", "sounds/Bass/808.adg"),
    ],
)
def test_uri_lookup_finds_items_when_proxy_addresses_are_reused(uri: str, path: str) -> None:
    lookup = _Lookup()

    item = lookup._find_browser_item_by_uri(uri)

    assert item is not None
    assert item.uri == uri
    assert lookup._item_path_by_uri(uri) == path
