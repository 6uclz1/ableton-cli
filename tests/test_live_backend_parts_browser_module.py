from __future__ import annotations

from remote_script.AbletonCliRemote.live_backend_parts import browser


def test_browser_mixin_definitions_live_in_split_modules() -> None:
    assert (
        browser.LiveBackendBrowserCatalogMixin.__module__
        == "remote_script.AbletonCliRemote.live_backend_parts.browser_catalog"
    )
    assert (
        browser.LiveBackendBrowserPathLookupMixin.__module__
        == "remote_script.AbletonCliRemote.live_backend_parts.browser_path_lookup"
    )
    assert (
        browser.LiveBackendBrowserSearchIndexMixin.__module__
        == "remote_script.AbletonCliRemote.live_backend_parts.browser_search_index"
    )
    assert (
        browser.LiveBackendBrowserReadMixin.__module__
        == "remote_script.AbletonCliRemote.live_backend_parts.browser_read"
    )
    assert (
        browser.LiveBackendBrowserSearchMixin.__module__
        == "remote_script.AbletonCliRemote.live_backend_parts.browser_search"
    )
