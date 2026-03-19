from __future__ import annotations

from core.platform.party.domain import PartyType
from tests.ui_runtime_helpers import make_settings_store, register_and_login
from ui.modules.inventory_procurement.items_tab import InventoryItemsTab
from ui.modules.inventory_procurement.stock_tab import StockTab
from ui.platform.shell.main_window import MainWindow


def _child_labels(item) -> list[str]:
    return [item.child(i).text(0) for i in range(item.childCount())]


def _enable_inventory_module(services) -> None:
    services["module_catalog_service"].set_module_state(
        "inventory_procurement",
        licensed=True,
        enabled=True,
    )


def test_inventory_items_tab_shows_platform_referenced_supplier_context(qapp, services):
    _enable_inventory_module(services)
    supplier = services["party_service"].create_party(
        party_code="SUP-INV-01",
        party_name="North Supply",
        party_type=PartyType.SUPPLIER,
    )
    register_and_login(services, username_prefix="inventory-ui-items", role_names=("inventory_manager",))
    services["inventory_item_service"].create_item(
        item_code="FILTER-01",
        name="Filter Cartridge",
        status="ACTIVE",
        stock_uom="EA",
        preferred_party_id=supplier.id,
    )

    tab = InventoryItemsTab(
        item_service=services["inventory_item_service"],
        reference_service=services["inventory_reference_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 1
    assert tab.count_badge.text() == "1 items"
    assert tab.active_badge.text() == "1 active"
    assert tab.stocked_badge.text() == "1 stocked"
    assert tab.table.item(0, 5).text() == "SUP-INV-01 - North Supply"

    tab.table.selectRow(0)
    qapp.processEvents()

    assert tab.detail_name.text() == "FILTER-01 - Filter Cartridge"
    assert "Preferred party: SUP-INV-01 - North Supply" in tab.detail_status.text()
    assert tab.detail_documents.text() == "No linked documents"


def test_stock_tab_shows_balance_and_transaction_history(qapp, services):
    _enable_inventory_module(services)
    site = services["site_service"].create_site(site_code="HAM", name="Hamburg Warehouse")
    register_and_login(services, username_prefix="inventory-ui-stock", role_names=("inventory_manager",))
    item = services["inventory_item_service"].create_item(
        item_code="BOLT-01",
        name="Hex Bolt",
        status="ACTIVE",
        stock_uom="EA",
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="MAIN",
        name="Main Stores",
        site_id=site.id,
        status="ACTIVE",
    )
    services["inventory_stock_service"].post_opening_balance(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=12.0,
        unit_cost=1.25,
    )
    services["inventory_stock_service"].post_adjustment(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
        quantity=2.0,
        direction="INCREASE",
        unit_cost=1.25,
        reference_id="COUNT-01",
    )

    tab = StockTab(
        stock_service=services["inventory_stock_service"],
        item_service=services["inventory_item_service"],
        inventory_service=services["inventory_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )

    assert tab.balance_table.rowCount() == 1
    assert tab.balance_count_badge.text() == "1 balances"
    assert tab.on_hand_badge.text() == "On hand: 14.000"
    assert tab.available_badge.text() == "Available: 14.000"

    tab.balance_table.selectRow(0)
    qapp.processEvents()

    assert tab.selection_badge.text().startswith("Selection: BOLT-01 - Hex Bolt")
    assert tab.transaction_table.rowCount() == 2
    assert tab.transaction_table.item(0, 1).text() == "Adjustment Increase"
    assert tab.transaction_table.item(1, 1).text() == "Opening Balance"


def test_main_window_exposes_inventory_workspaces_when_module_is_enabled(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    _enable_inventory_module(services)
    register_and_login(services, username_prefix="inventory-shell", role_names=("inventory_manager", "viewer"))
    store = make_settings_store(repo_workspace, prefix="inventory-shell")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]

    assert "Items" in labels
    assert "Storerooms" in labels
    assert "Stock" in labels

    inventory_section = window.shell_navigation.tree.topLevelItem(2)
    assert inventory_section.text(0) == "Inventory & Procurement"
    assert _child_labels(inventory_section) == ["Master Data", "Operations"]
    assert _child_labels(inventory_section.child(0)) == ["Items", "Storerooms"]
    assert _child_labels(inventory_section.child(1)) == ["Stock"]
