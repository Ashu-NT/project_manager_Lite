from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from core.platform.common.exceptions import ValidationError
from src.core.platform.party.domain import PartyType
from tests.ui_runtime_helpers import login_as


def _create_procurement_context(services):
    suffix = uuid4().hex[:6].upper()
    site = services["site_service"].create_site(
        site_code=f"PO-{suffix}",
        name=f"Procurement Site {suffix}",
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
        storeroom_code=f"PO-MAIN-{suffix}",
        name=f"PO Main {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code=f"SUP-PO-{suffix}",
        party_name=f"Industrial Supplier {suffix}",
        party_type=PartyType.SUPPLIER,
    )
    return site, storeroom, item, supplier


def _create_approved_purchase_order(services):
    auth = services["auth_service"]
    auth.register_user("inventory-buyer", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user("inventory-approver-po", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _create_procurement_context(services)
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    login_as(services, "inventory-buyer", "StrongPass123")

    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Source maintenance motor",
        needed_by_date=date(2026, 4, 10),
    )
    requisition_line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=250.0,
    )
    requisition = procurement.submit_requisition(requisition.id)

    login_as(services, "inventory-approver-po", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved requisition")

    login_as(services, "inventory-buyer", "StrongPass123")
    purchase_order = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        source_requisition_id=requisition.id,
        expected_delivery_date=date(2026, 4, 20),
    )
    purchase_order_line = purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=5,
        unit_price=240.0,
        source_requisition_line_id=requisition_line.id,
    )
    purchase_order = purchasing.submit_purchase_order(purchase_order.id)

    login_as(services, "inventory-approver-po", "StrongPass123")
    approvals.approve_and_apply(purchase_order.approval_request_id, note="Approved PO")

    login_as(services, "inventory-buyer", "StrongPass123")
    return site, storeroom, item, supplier, requisition, requisition_line, purchase_order, purchase_order_line


def test_purchase_order_submit_enriches_approval_payload(services):
    site, storeroom, item, supplier = _create_procurement_context(services)
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    purchase_order = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        source_requisition_id=None,
        expected_delivery_date=date(2026, 4, 20),
    )
    _purchase_order_line = purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=5,
        unit_price=240.0,
    )
    purchase_order = purchasing.submit_purchase_order(purchase_order.id)

    pending = approvals.list_pending()
    assert len(pending) == 1
    request = pending[0]
    assert request.request_type == "purchase_order.submit"
    assert request.payload["purchase_order_id"] == purchase_order.id
    assert request.payload["po_number"] == purchase_order.po_number
    assert request.payload["supplier_name"] == supplier.party_name
    assert request.payload["site_name"] == site.name
    assert request.payload["line_count"] == 1
    assert request.payload["total_amount"] == pytest.approx(1200.0)

    from ui.platform.control.approvals.presentation import approval_display_label, approval_context_label

    display_label = approval_display_label(request)
    context_label = approval_context_label(request)

    assert "Submit purchase order" in display_label
    assert supplier.party_name in display_label
    assert site.name in display_label
    assert "PO" in context_label


def test_purchase_order_approval_updates_requisition_sourcing_and_on_order_balance(services):
    (
        _site,
        storeroom,
        item,
        _supplier,
        requisition,
        _requisition_line,
        purchase_order,
        _purchase_order_line,
    ) = _create_approved_purchase_order(services)

    purchasing = services["inventory_purchasing_service"]
    procurement = services["inventory_procurement_service"]
    stock = services["inventory_stock_service"]

    approved_order = purchasing.get_purchase_order(purchase_order.id)
    order_lines = purchasing.list_purchase_order_lines(purchase_order.id)
    refreshed_requisition = procurement.get_requisition(requisition.id)
    requisition_lines = procurement.list_requisition_lines(requisition.id)
    balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=storeroom.id)

    assert approved_order.status.value == "APPROVED"
    assert [line.status.value for line in order_lines] == ["OPEN"]
    assert refreshed_requisition.status.value == "FULLY_SOURCED"
    assert requisition_lines[0].status.value == "FULLY_SOURCED"
    assert requisition_lines[0].quantity_sourced == pytest.approx(5.0)
    assert balance is not None
    assert balance.on_order_qty == pytest.approx(5.0)
    assert balance.on_hand_qty == pytest.approx(0.0)


def test_receiving_posts_stock_for_accepted_qty_and_reduces_on_order(services):
    (
        _site,
        storeroom,
        item,
        _supplier,
        _requisition,
        _requisition_line,
        purchase_order,
        purchase_order_line,
    ) = _create_approved_purchase_order(services)

    purchasing = services["inventory_purchasing_service"]
    stock = services["inventory_stock_service"]

    first_receipt = purchasing.post_receipt(
        purchase_order.id,
        receipt_lines=[
            {
                "purchase_order_line_id": purchase_order_line.id,
                "quantity_accepted": 3,
                "quantity_rejected": 1,
                "unit_cost": 240.0,
            }
        ],
        supplier_delivery_reference="DEL-1001",
    )

    mid_order = purchasing.get_purchase_order(purchase_order.id)
    mid_line = purchasing.list_purchase_order_lines(purchase_order.id)[0]
    mid_balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=storeroom.id)
    transactions = stock.list_transactions(stock_item_id=item.id, storeroom_id=storeroom.id)

    assert first_receipt.receipt_number.startswith("INV-RCV-")
    assert mid_order.status.value == "PARTIALLY_RECEIVED"
    assert mid_line.status.value == "PARTIALLY_RECEIVED"
    assert mid_line.quantity_received == pytest.approx(3.0)
    assert mid_line.quantity_rejected == pytest.approx(1.0)
    assert mid_balance.on_hand_qty == pytest.approx(3.0)
    assert mid_balance.on_order_qty == pytest.approx(1.0)
    assert len(transactions) == 1
    assert transactions[0].reference_type == "inventory_receipt"

    purchasing.post_receipt(
        purchase_order.id,
        receipt_lines=[
            {
                "purchase_order_line_id": purchase_order_line.id,
                "quantity_accepted": 1,
                "unit_cost": 240.0,
            }
        ],
    )

    final_order = purchasing.get_purchase_order(purchase_order.id)
    final_line = purchasing.list_purchase_order_lines(purchase_order.id)[0]
    final_balance = stock.get_balance_for_stock_position(stock_item_id=item.id, storeroom_id=storeroom.id)

    assert final_order.status.value == "FULLY_RECEIVED"
    assert final_line.status.value == "FULLY_RECEIVED"
    assert final_balance.on_hand_qty == pytest.approx(4.0)
    assert final_balance.on_order_qty == pytest.approx(0.0)


def test_receiving_validates_open_qty_and_po_status(services):
    site, storeroom, item, supplier = _create_procurement_context(services)
    purchasing = services["inventory_purchasing_service"]

    draft_order = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
    )
    draft_line = purchasing.add_purchase_order_line(
        draft_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=2,
    )

    with pytest.raises(ValidationError, match="not open for receiving"):
        purchasing.post_receipt(
            draft_order.id,
            receipt_lines=[{"purchase_order_line_id": draft_line.id, "quantity_accepted": 1}],
        )

    (
        _site,
        _storeroom,
        _item,
        _supplier,
        _requisition,
        _requisition_line,
        approved_order,
        approved_line,
    ) = _create_approved_purchase_order(services)

    with pytest.raises(ValidationError, match="exceeds the remaining open quantity"):
        purchasing.post_receipt(
            approved_order.id,
            receipt_lines=[{"purchase_order_line_id": approved_line.id, "quantity_accepted": 6}],
        )


def test_receiving_enforces_lot_and_shelf_life_controls(services):
    (
        _site,
        _storeroom,
        item,
        _supplier,
        _requisition,
        _requisition_line,
        purchase_order,
        purchase_order_line,
    ) = _create_approved_purchase_order(services)

    services["inventory_item_service"].update_item(
        item.id,
        is_lot_tracked=True,
        shelf_life_days=30,
    )
    purchasing = services["inventory_purchasing_service"]

    with pytest.raises(ValidationError, match="lot number"):
        purchasing.post_receipt(
            purchase_order.id,
            receipt_lines=[
                {
                    "purchase_order_line_id": purchase_order_line.id,
                    "quantity_accepted": 1,
                    "unit_cost": 240.0,
                }
            ],
            supplier_delivery_reference="DEL-TRACK-1",
        )

    with pytest.raises(ValidationError, match="expiry date"):
        purchasing.post_receipt(
            purchase_order.id,
            receipt_lines=[
                {
                    "purchase_order_line_id": purchase_order_line.id,
                    "quantity_accepted": 1,
                    "unit_cost": 240.0,
                    "lot_number": "LOT-001",
                }
            ],
            supplier_delivery_reference="DEL-TRACK-2",
        )


def test_purchase_order_service_can_update_and_cancel_draft_purchase_order(services):
    auth = services["auth_service"]
    auth.register_user("inventory-buyer-edit", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _create_procurement_context(services)
    alternate_site = services["site_service"].create_site(
        site_code="PO-ALT",
        name="Alternate PO Site",
        currency_code="USD",
    )
    alternate_storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PO-ALT-MAIN",
        name="Alternate PO Stores",
        site_id=alternate_site.id,
        status="ACTIVE",
    )
    alternate_supplier = services["party_service"].create_party(
        party_code="SUP-PO-ALT",
        party_name="Secondary Industrial Supplier",
        party_type=PartyType.SUPPLIER,
    )

    login_as(services, "inventory-buyer-edit", "StrongPass123")

    purchasing = services["inventory_purchasing_service"]
    purchase_order = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        supplier_reference="SUP-REF-1",
    )

    updated = purchasing.update_purchase_order(
        purchase_order.id,
        site_id=alternate_site.id,
        supplier_party_id=alternate_supplier.id,
        currency_code="USD",
        expected_delivery_date=date(2026, 5, 12),
        supplier_reference="SUP-REF-2",
        notes="Updated before lines were added",
        expected_version=purchase_order.version,
    )
    purchasing.add_purchase_order_line(
        updated.id,
        stock_item_id=item.id,
        destination_storeroom_id=alternate_storeroom.id,
        quantity_ordered=3,
        unit_price=210.0,
    )
    cancelled = purchasing.cancel_purchase_order(updated.id, expected_version=updated.version)
    lines = purchasing.list_purchase_order_lines(updated.id)

    assert updated.site_id == alternate_site.id
    assert updated.supplier_party_id == alternate_supplier.id
    assert updated.currency_code == "USD"
    assert updated.expected_delivery_date == date(2026, 5, 12)
    assert updated.supplier_reference == "SUP-REF-2"
    assert cancelled.status.value == "CANCELLED"
    assert cancelled.cancelled_at is not None
    assert [line.status.value for line in lines] == ["CANCELLED"]


def test_purchase_order_service_can_send_and_close_when_fully_processed(services):
    (
        _site,
        storeroom,
        item,
        _supplier,
        _requisition,
        _requisition_line,
        purchase_order,
        purchase_order_line,
    ) = _create_approved_purchase_order(services)

    purchasing = services["inventory_purchasing_service"]
    sent = purchasing.send_purchase_order(purchase_order.id, note="Sent to supplier")
    purchasing.post_receipt(
        sent.id,
        receipt_lines=[
            {
                "purchase_order_line_id": purchase_order_line.id,
                "quantity_accepted": 4,
                "quantity_rejected": 1,
                "unit_cost": 240.0,
            }
        ],
    )
    closed = purchasing.close_purchase_order(sent.id, note="Closed after full processing")
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
    )

    assert sent.status.value == "SENT"
    assert sent.sent_at is not None
    assert closed.status.value == "CLOSED"
    assert closed.closed_at is not None
    assert balance is not None
    assert balance.on_order_qty == pytest.approx(0.0)


def test_purchase_order_service_rejects_close_when_open_qty_remains(services):
    (
        _site,
        _storeroom,
        _item,
        _supplier,
        _requisition,
        _requisition_line,
        purchase_order,
        _purchase_order_line,
    ) = _create_approved_purchase_order(services)

    purchasing = services["inventory_purchasing_service"]

    with pytest.raises(ValidationError, match="still has open quantity"):
        purchasing.close_purchase_order(purchase_order.id)


def test_purchase_order_workflow_converts_between_issue_and_order_uoms(services):
    auth = services["auth_service"]
    auth.register_user("inventory-buyer-uom", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user("inventory-approver-uom", "StrongPass123", role_names=["approver"])

    site = services["site_service"].create_site(
        site_code="PO-UOM",
        name="PO UOM Site",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code="MOTOR-UOM-PO",
        name="Motor Alternate UOM",
        status="ACTIVE",
        stock_uom="EA",
        order_uom="BOX",
        order_uom_ratio=10,
        issue_uom="PACK",
        issue_uom_ratio=2,
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PO-UOM-MAIN",
        name="PO UOM Main",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-PO-UOM",
        party_name="Alternate UOM Supplier",
        party_type=PartyType.SUPPLIER,
    )
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    login_as(services, "inventory-buyer-uom", "StrongPass123")
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Order alternate UOM stock",
    )
    requisition_line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        uom="PACK",
        suggested_supplier_party_id=supplier.id,
    )
    requisition = procurement.submit_requisition(requisition.id)

    login_as(services, "inventory-approver-uom", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved alternate UOM requisition")

    login_as(services, "inventory-buyer-uom", "StrongPass123")
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
        quantity_ordered=1,
        uom="BOX",
        unit_price=120.0,
        source_requisition_line_id=requisition_line.id,
    )
    purchase_order = purchasing.submit_purchase_order(purchase_order.id)

    login_as(services, "inventory-approver-uom", "StrongPass123")
    approvals.approve_and_apply(purchase_order.approval_request_id, note="Approved alternate UOM PO")

    login_as(services, "inventory-buyer-uom", "StrongPass123")
    refreshed_requisition_line = procurement.list_requisition_lines(requisition.id)[0]
    balance_after_approval = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
    )

    assert purchase_order_line.uom == "BOX"
    assert refreshed_requisition_line.uom == "PACK"
    assert refreshed_requisition_line.quantity_sourced == pytest.approx(5.0)
    assert balance_after_approval is not None
    assert balance_after_approval.on_order_qty == pytest.approx(10.0)

    purchasing.post_receipt(
        purchase_order.id,
        receipt_lines=[
            {
                "purchase_order_line_id": purchase_order_line.id,
                "quantity_accepted": 1,
                "unit_cost": 120.0,
            }
        ],
    )
    balance_after_receipt = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id,
        storeroom_id=storeroom.id,
    )

    assert balance_after_receipt is not None
    assert balance_after_receipt.on_hand_qty == pytest.approx(10.0)
    assert balance_after_receipt.on_order_qty == pytest.approx(0.0)
