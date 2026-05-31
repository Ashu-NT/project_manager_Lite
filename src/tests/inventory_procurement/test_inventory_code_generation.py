"""Inventory catalog/storeroom code-generation wiring."""

from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.modules.inventory_procurement.presenters.catalog_workspace_presenter import (
    InventoryCatalogWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.inventory_workspace_presenter import (
    InventoryInventoryWorkspacePresenter,
)


class _FakeCatalogApi:
    def __init__(self, categories=(), items=()):
        self._categories = list(categories)
        self._items = list(items)

    def list_categories(self, active_only=None):
        return [SimpleNamespace(category_code=code) for code in self._categories]

    def list_items(self, active_only=None):
        return [SimpleNamespace(item_code=code) for code in self._items]


class _FakeInventoryApi:
    def __init__(self, storerooms=()):
        self._storerooms = list(storerooms)

    def list_storerooms(self, active_only=None):
        return [SimpleNamespace(storeroom_code=code) for code in self._storerooms]


def test_category_suggest_uses_name_and_increments():
    presenter = InventoryCatalogWorkspacePresenter(
        desktop_api=_FakeCatalogApi(categories=["CAT-SPAR-0001"])
    )
    assert presenter.suggest_category_code({"name": "Spare Parts"}) == "CAT-SPAR-0002"


def test_item_suggest_uses_name():
    presenter = InventoryCatalogWorkspacePresenter(desktop_api=_FakeCatalogApi())
    assert presenter.suggest_item_code({"name": "Pump"}) == "ITM-PUMP-0001"


def test_item_suggest_year_fallback_without_name():
    presenter = InventoryCatalogWorkspacePresenter(desktop_api=_FakeCatalogApi())
    code = presenter.suggest_item_code({})
    assert code.startswith("ITM-") and code.endswith("-0001")


def test_storeroom_suggest_uses_name():
    presenter = InventoryInventoryWorkspacePresenter(desktop_api=_FakeInventoryApi())
    assert presenter.suggest_storeroom_code({"name": "Main Storeroom"}) == "STR-MAIN-0001"
