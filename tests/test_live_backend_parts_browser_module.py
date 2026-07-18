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
    assert (
        browser.LiveBackendBrowserLoadMixin.__module__
        == "remote_script.AbletonCliRemote.live_backend_parts.browser_load"
    )


def test_browser_load_mixin_exposes_load_instrument_or_effect() -> None:
    assert hasattr(browser.LiveBackendBrowserLoadMixin, "load_instrument_or_effect")


def test_browser_read_mixin_exposes_tree_and_category_reads() -> None:
    assert hasattr(browser.LiveBackendBrowserReadMixin, "get_browser_tree")
    assert hasattr(browser.LiveBackendBrowserReadMixin, "get_browser_items_at_path")
    assert hasattr(browser.LiveBackendBrowserReadMixin, "get_browser_item")
    assert hasattr(browser.LiveBackendBrowserReadMixin, "get_browser_categories")
    assert not hasattr(browser.LiveBackendBrowserReadMixin, "load_instrument_or_effect")
