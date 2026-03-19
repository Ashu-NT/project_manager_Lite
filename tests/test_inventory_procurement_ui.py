from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from core.platform.party.domain import PartyType
from tests.ui_runtime_helpers import login_as, make_settings_store, register_and_login
from ui.modules.inventory_procurement.items_tab import InventoryItemsTab
from ui.modules.inventory_procurement.purchase_orders_tab import PurchaseOrdersTab
from ui.modules.inventory_procurement.receiving_tab import ReceivingTab
from ui.modules.inventory_procurement.requisitions_tab import RequisitionsTab
from ui.modules.inventory_procurement.stock_tab import StockTab
from ui.platform.shell.main_window import MainWindow
from ui.platform.shared.styles.theme import base_stylesheet


def _child_labels(item) -> list[str]:
    return [item.child(i).text(0) for i in range(item.childCount())]


def _enable_inventory_module(services) -> None:
    services["module_catalog_service"].set_module_state(
        "inventory_procurement",
        licensed=True,
        enabled=True,
    )


def _create_procurement_context(services):
    suffix = uuid4().hex[:6].upper()
    site = services["site_service"].create_site(
        site_code=f"INV-{suffix}",
        name=f"Inventory Site {suffix}",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"MOTOR-{suffix}",
        name=f"Motor {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"MAIN-{suffix}",
        name=f"Main Stores {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code=f"SUP-{suffix}",
        party_name=f"Supplier {suffix}",
        party_type=PartyType.SUPPLIER,
    )
    return site, storeroom, item, supplier


def _create_purchase_flow(services, *, with_receipt: bool = False):
    auth = services["auth_service"]
    manager_name = f"inventory-ui-manager-{uuid4().hex[:6]}"
    approver_name = f"inventory-ui-approver-{uuid4().hex[:6]}"
    auth.register_user(manager_name, "StrongPass123", role_names=["inventory_manager"])
    auth.register_user(approver_name, "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _create_procurement_context(services)
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    login_as(services, manager_name, "StrongPass123")
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Restock motors",
    )
    requisition_line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=120.0,
    )
    requisition = procurement.submit_requisition(requisition.id)

    login_as(services, approver_name, "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved requisition")

    login_as(services, manager_name, "StrongPass123")
    purchase_order = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        source_requisition_id=requisition.id,
    )
    purchase_order_line = purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=5,
        unit_price=115.0,
        source_requisition_line_id=requisition_line.id,
    )
    purchase_order = purchasing.submit_purchase_order(purchase_order.id)

    login_as(services, approver_name, "StrongPass123")
    approvals.approve_and_apply(purchase_order.approval_request_id, note="Approved purchase order")

    receipt = None
    if with_receipt:
        login_as(services, manager_name, "StrongPass123")
        receipt = purchasing.post_receipt(
            purchase_order.id,
            receipt_lines=[
                {
                    "purchase_order_line_id": purchase_order_line.id,
                    "quantity_accepted": 3,
                    "quantity_rejected": 1,
                    "unit_cost": 115.0,
                }
            ],
            supplier_delivery_reference="DEL-UI-01",
        )
    else:
        login_as(services, manager_name, "StrongPass123")
    return site, storeroom, item, supplier, requisition, purchase_order, purchase_order_line, receipt


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

    assert tab.work_tabs.count() == 2
    assert tab.work_tabs.tabText(0) == "Stock Positions"
    assert tab.work_tabs.tabText(1) == "Transaction History"
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


def test_requisitions_tab_shows_demand_lines_and_shared_context(qapp, services):
    _enable_inventory_module(services)
    site, storeroom, item, supplier = _create_procurement_context(services)
    register_and_login(services, username_prefix="inventory-ui-req", role_names=("inventory_manager",))
    requisition = services["inventory_procurement_service"].create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Restock inspection spares",
    )
    services["inventory_procurement_service"].add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=4,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=85.0,
    )

    tab = RequisitionsTab(
        procurement_service=services["inventory_procurement_service"],
        item_service=services["inventory_item_service"],
        inventory_service=services["inventory_service"],
        reference_service=services["inventory_reference_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 1
    assert tab.count_badge.text() == "1 requisitions"

    tab.table.selectRow(0)
    qapp.processEvents()

    assert tab.detail_name.text() == requisition.requisition_number
    assert tab.detail_site.text() == f"{site.site_code} - {site.name}"
    assert tab.detail_storeroom.text() == f"{storeroom.storeroom_code} - {storeroom.name}"
    assert tab.lines_table.rowCount() == 1
    assert item.item_code in tab.lines_table.item(0, 1).text()


def test_purchase_orders_tab_shows_line_and_source_requisition(qapp, services):
    _enable_inventory_module(services)
    (
        _site,
        storeroom,
        item,
        supplier,
        requisition,
        purchase_order,
        _purchase_order_line,
        _receipt,
    ) = _create_purchase_flow(services)

    tab = PurchaseOrdersTab(
        purchasing_service=services["inventory_purchasing_service"],
        procurement_service=services["inventory_procurement_service"],
        item_service=services["inventory_item_service"],
        inventory_service=services["inventory_service"],
        reference_service=services["inventory_reference_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 1
    assert tab.count_badge.text() == "1 purchase orders"

    tab.table.selectRow(0)
    qapp.processEvents()

    assert tab.detail_name.text() == purchase_order.po_number
    assert tab.detail_supplier.text() == f"{supplier.party_code} - {supplier.party_name}"
    assert tab.detail_source.text() == requisition.requisition_number
    assert tab.lines_table.rowCount() == 1
    assert storeroom.storeroom_code in tab.lines_table.item(0, 2).text()
    assert item.item_code in tab.lines_table.item(0, 1).text()


def test_receiving_tab_shows_outstanding_lines_and_receipt_history(qapp, services):
    _enable_inventory_module(services)
    (
        site,
        _storeroom,
        item,
        _supplier,
        _requisition,
        purchase_order,
        _purchase_order_line,
        receipt,
    ) = _create_purchase_flow(services, with_receipt=True)

    tab = ReceivingTab(
        purchasing_service=services["inventory_purchasing_service"],
        item_service=services["inventory_item_service"],
        inventory_service=services["inventory_service"],
        reference_service=services["inventory_reference_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )

    assert tab.work_tabs.count() == 2
    assert tab.work_tabs.tabText(0) == "Outstanding Lines"
    assert tab.work_tabs.tabText(1) == "Receipt History"
    assert tab.table.rowCount() == 1

    tab.table.selectRow(0)
    qapp.processEvents()

    assert tab.detail_name.text() == purchase_order.po_number
    assert tab.detail_site.text() == f"{site.site_code} - {site.name}"
    assert tab.lines_table.rowCount() == 1
    assert tab.receipts_table.rowCount() == 1
    assert item.item_code in tab.lines_table.item(0, 1).text()
    assert tab.receipts_table.item(0, 0).text() == receipt.receipt_number


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
    assert "Requisitions" in labels
    assert "Purchase Orders" in labels
    assert "Receiving" in labels

    inventory_section = window.shell_navigation.tree.topLevelItem(2)
    assert inventory_section.text(0) == "Inventory & Procurement"
    assert _child_labels(inventory_section) == ["Master Data", "Operations", "Procurement"]
    assert _child_labels(inventory_section.child(0)) == ["Items", "Storerooms"]
    assert _child_labels(inventory_section.child(1)) == ["Stock"]
    assert _child_labels(inventory_section.child(2)) == ["Requisitions", "Purchase Orders", "Receiving"]


def test_inventory_ui_uses_qdialog_acceptance_constant_in_new_dialog_paths():
    root = Path(__file__).resolve().parents[1]
    inventory_ui = root / "ui" / "modules" / "inventory_procurement"
    texts = [
        (inventory_ui / "items_tab.py").read_text(encoding="utf-8", errors="ignore"),
        (inventory_ui / "purchase_orders_tab.py").read_text(encoding="utf-8", errors="ignore"),
        (inventory_ui / "receiving_tab.py").read_text(encoding="utf-8", errors="ignore"),
        (inventory_ui / "requisitions_tab.py").read_text(encoding="utf-8", errors="ignore"),
        (inventory_ui / "storerooms_tab.py").read_text(encoding="utf-8", errors="ignore"),
        (inventory_ui / "stock_tab.py").read_text(encoding="utf-8", errors="ignore"),
    ]

    assert all("dialog.Accepted" not in text for text in texts)
    assert all("QDialog.Accepted" in text for text in texts)


def test_base_stylesheet_explicitly_styles_qplaintextedit_note_surfaces():
    css = base_stylesheet()

    assert "QPlainTextEdit" in css
    assert "QPlainTextEdit:focus" in css
