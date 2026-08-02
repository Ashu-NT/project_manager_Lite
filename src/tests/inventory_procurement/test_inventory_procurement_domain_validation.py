from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.modules.inventory_procurement.domain import (
    CycleCount,
    CycleCountStatus,
    InventoryItemCategory,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
    ReceiptHeader,
    ReceiptLine,
    ReceiptStatus,
    ReorderPolicy,
    StockBalance,
    StockItem,
    StockReservation,
    StockReservationStatus,
    StockTransaction,
    StockTransactionType,
    StorageLocation,
    StorageLocationType,
    Storeroom,
)
from src.core.platform.common.exceptions import ValidationError


def test_inventory_catalog_dtos_normalize_fields() -> None:
    category = InventoryItemCategory.create(
        organization_id="  org-1  ",
        category_code="  equip-01  ",
        name="  Generator Sets  ",
        description="  Prime power assets  ",
        category_type=" equipment ",
        is_equipment=False,
        supports_project_usage=True,
        supports_maintenance_usage=True,
    )

    assert category.organization_id == "org-1"
    assert category.category_code == "EQUIP-01"
    assert category.name == "Generator Sets"
    assert category.description == "Prime power assets"
    assert category.category_type == "EQUIPMENT"
    assert category.is_equipment is True

    item = StockItem.create(
        organization_id="  org-1  ",
        item_code="  valve-01  ",
        name="  Control Valve  ",
        description="  Stainless trim  ",
        item_type=" spare ",
        status=" active ",
        stock_uom=" ea ",
        order_uom=" box ",
        issue_uom=" box ",
        order_uom_ratio="12",
        issue_uom_ratio=12.0,
        category_code="  spare-mech  ",
        commodity_code="  mech  ",
        is_stocked=True,
        is_purchase_allowed=True,
        default_reorder_policy="  minmax  ",
        min_qty="2",
        max_qty="12",
        reorder_point="4",
        reorder_qty="6",
        lead_time_days="5",
        shelf_life_days="30",
        preferred_party_id="  supplier-1  ",
        notes="  cool storage  ",
    )

    assert item.organization_id == "org-1"
    assert item.item_code == "VALVE-01"
    assert item.name == "Control Valve"
    assert item.description == "Stainless trim"
    assert item.item_type == "SPARE"
    assert item.status == "ACTIVE"
    assert item.stock_uom == "EA"
    assert item.order_uom == "BOX"
    assert item.issue_uom == "BOX"
    assert item.order_uom_ratio == 12.0
    assert item.issue_uom_ratio == 12.0
    assert item.category_code == "SPARE-MECH"
    assert item.commodity_code == "MECH"
    assert item.default_reorder_policy == "MINMAX"
    assert item.lead_time_days == 5
    assert item.shelf_life_days == 30
    assert item.preferred_party_id == "supplier-1"
    assert item.notes == "cool storage"
    assert item.is_active is True

    storeroom = Storeroom.create(
        organization_id="  org-1  ",
        storeroom_code="  main-01  ",
        name="  Main Warehouse  ",
        site_id="  site-1  ",
        description="  Central issue point  ",
        status=" active ",
        storeroom_type=" main ",
        default_currency_code=" usd ",
        manager_party_id="  manager-1  ",
        notes="  climate controlled  ",
    )

    assert storeroom.organization_id == "org-1"
    assert storeroom.storeroom_code == "MAIN-01"
    assert storeroom.name == "Main Warehouse"
    assert storeroom.description == "Central issue point"
    assert storeroom.status == "ACTIVE"
    assert storeroom.storeroom_type == "MAIN"
    assert storeroom.default_currency_code == "USD"
    assert storeroom.manager_party_id == "manager-1"
    assert storeroom.notes == "climate controlled"
    assert storeroom.is_active is True


def test_inventory_foundation_dtos_normalize_fields_and_validate_ranges() -> None:
    location = StorageLocation.create(
        organization_id="  org-1  ",
        storeroom_id="  store-1  ",
        location_code="  bin-a1  ",
        name="  Bin A1  ",
        parent_location_id="  zone-1  ",
        location_type=" shelf ",
        notes="  Upper rack  ",
    )

    assert location.organization_id == "org-1"
    assert location.storeroom_id == "store-1"
    assert location.location_code == "BIN-A1"
    assert location.name == "Bin A1"
    assert location.parent_location_id == "zone-1"
    assert location.location_type is StorageLocationType.SHELF
    assert location.notes == "Upper rack"

    policy = ReorderPolicy.create(
        organization_id="  org-1  ",
        stock_item_id="  item-1  ",
        storeroom_id="  store-1  ",
        location_id="  loc-1  ",
        policy_name="  Main shelf policy  ",
        min_qty="2",
        max_qty="10",
        reorder_point="4",
        reorder_qty="6",
        economic_order_qty="8",
        lead_time_days="7",
        review_period_days="14",
        preferred_supplier_party_id="  supplier-1  ",
    )

    assert policy.organization_id == "org-1"
    assert policy.stock_item_id == "item-1"
    assert policy.storeroom_id == "store-1"
    assert policy.location_id == "loc-1"
    assert policy.policy_name == "Main shelf policy"
    assert policy.min_qty == 2.0
    assert policy.max_qty == 10.0
    assert policy.reorder_point == 4.0
    assert policy.reorder_qty == 6.0
    assert policy.economic_order_qty == 8.0
    assert policy.lead_time_days == 7
    assert policy.review_period_days == 14
    assert policy.preferred_supplier_party_id == "supplier-1"

    cycle_count = CycleCount(
        id="cycle-1",
        organization_id="  org-1  ",
        cycle_count_number="  cc-001  ",
        stock_item_id="  item-1  ",
        storeroom_id="  store-1  ",
        location_id="  loc-1  ",
        scheduled_count_date="2026-07-01",
        status=" completed ",
        expected_qty="10",
        counted_qty="12.5",
        variance_qty="-99",
        counted_by_user_id="  user-1  ",
        counted_by_username="  Alex Counter  ",
        created_at=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        notes="  counted and verified  ",
    )

    assert cycle_count.organization_id == "org-1"
    assert cycle_count.cycle_count_number == "CC-001"
    assert cycle_count.location_id == "loc-1"
    assert cycle_count.scheduled_count_date == date(2026, 7, 1)
    assert cycle_count.status is CycleCountStatus.COMPLETED
    assert cycle_count.expected_qty == 10.0
    assert cycle_count.counted_qty == 12.5
    assert cycle_count.variance_qty == 2.5
    assert cycle_count.counted_by_user_id == "user-1"
    assert cycle_count.counted_by_username == "Alex Counter"
    assert cycle_count.notes == "counted and verified"


def test_inventory_catalog_and_foundation_dtos_raise_expected_validation_codes() -> None:
    with pytest.raises(ValidationError) as exc_uom:
        StockItem.create(
            organization_id="org-1",
            item_code="VALVE-ALT",
            name="Alternate Valve",
            stock_uom="EA",
            order_uom="BOX",
        )
    assert exc_uom.value.code == "INVENTORY_UOM_FACTOR_REQUIRED"

    with pytest.raises(ValidationError) as exc_policy:
        ReorderPolicy.create(
            organization_id="org-1",
            stock_item_id="item-1",
            storeroom_id="store-1",
            min_qty=6,
            max_qty=3,
        )
    assert exc_policy.value.code == "INVENTORY_REORDER_POLICY_MAX_INVALID"

    created_at = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError) as exc_cycle:
        CycleCount(
            id="cycle-1",
            organization_id="org-1",
            cycle_count_number="CC-002",
            stock_item_id="item-1",
            storeroom_id="store-1",
            status="COMPLETED",
            expected_qty=10,
            counted_qty=8,
            created_at=created_at,
            completed_at=created_at - timedelta(minutes=30),
        )
    assert exc_cycle.value.code == "INVENTORY_CYCLE_COUNT_COMPLETED_RANGE_INVALID"


def test_inventory_stock_operation_dtos_normalize_fields_and_validate_ranges() -> None:
    updated_at = datetime(2026, 7, 21, 15, 0, tzinfo=timezone.utc)
    balance = StockBalance(
        id="  bal-1  ",
        organization_id="  org-1  ",
        stock_item_id="  item-1  ",
        storeroom_id="  store-1  ",
        uom=" ea ",
        on_hand_qty="10",
        reserved_qty="2.5",
        available_qty="7.5",
        on_order_qty="4",
        committed_qty="1.5",
        average_cost="12.34",
        last_receipt_at=datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc),
        last_issue_at=datetime(2026, 7, 21, 10, 30, tzinfo=timezone.utc),
        updated_at=updated_at,
        version="2",
    )

    assert balance.id == "bal-1"
    assert balance.organization_id == "org-1"
    assert balance.stock_item_id == "item-1"
    assert balance.storeroom_id == "store-1"
    assert balance.uom == "EA"
    assert balance.on_hand_qty == 10.0
    assert balance.reserved_qty == 2.5
    assert balance.available_qty == 7.5
    assert balance.on_order_qty == 4.0
    assert balance.committed_qty == 1.5
    assert balance.average_cost == 12.34
    assert balance.version == 2

    reservation = StockReservation(
        id="  res-1  ",
        organization_id="  org-1  ",
        reservation_number="  inv-res-001  ",
        stock_item_id="  item-1  ",
        storeroom_id="  store-1  ",
        reserved_qty="5",
        issued_qty="2",
        remaining_qty="999",
        uom=" ea ",
        status=" partially_issued ",
        need_by_date="2026-07-30",
        source_reference_type=" work_order ",
        source_reference_id="  wo-1  ",
        source_module="  maintenance_management  ",
        source_entity_type="  work_order  ",
        source_code_snapshot="  wo-001  ",
        source_title_snapshot="  Pump Overhaul  ",
        source_status_snapshot="  approved  ",
        requested_by_user_id="  user-1  ",
        requested_by_username="  Alex Planner  ",
        created_at=datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc),
        notes="  reserve for shutdown  ",
        version="2",
    )

    assert reservation.id == "res-1"
    assert reservation.organization_id == "org-1"
    assert reservation.reservation_number == "INV-RES-001"
    assert reservation.uom == "EA"
    assert reservation.status is StockReservationStatus.PARTIALLY_ISSUED
    assert reservation.need_by_date == date(2026, 7, 30)
    assert reservation.source_reference_type == "work_order"
    assert reservation.source_reference_id == "wo-1"
    assert reservation.source_module == "maintenance_management"
    assert reservation.source_entity_type == "work_order"
    assert reservation.source_code_snapshot == "wo-001"
    assert reservation.source_title_snapshot == "Pump Overhaul"
    assert reservation.source_status_snapshot == "approved"
    assert reservation.requested_by_user_id == "user-1"
    assert reservation.requested_by_username == "Alex Planner"
    assert reservation.notes == "reserve for shutdown"
    assert reservation.remaining_qty == 3.0
    assert reservation.version == 2

    transaction = StockTransaction(
        id="  txn-1  ",
        organization_id="  org-1  ",
        transaction_number="  inv-txn-001  ",
        stock_item_id="  item-1  ",
        storeroom_id="  store-1  ",
        transaction_type=" transfer_out ",
        quantity="3.5",
        uom=" ea ",
        unit_cost="7.25",
        transaction_at=datetime(2026, 7, 21, 16, 30),
        reference_type="  task_issue  ",
        reference_id="  TASK-1  ",
        performed_by_user_id="  user-2  ",
        performed_by_username="  Alex Mover  ",
        resulting_on_hand_qty="9",
        resulting_available_qty="8",
        notes="  moved to field crew  ",
        lot_number="  lot-1  ",
        serial_number="  sn-9  ",
    )

    assert transaction.id == "txn-1"
    assert transaction.organization_id == "org-1"
    assert transaction.transaction_number == "INV-TXN-001"
    assert transaction.transaction_type is StockTransactionType.TRANSFER_OUT
    assert transaction.quantity == 3.5
    assert transaction.uom == "EA"
    assert transaction.unit_cost == 7.25
    assert transaction.transaction_at == datetime(2026, 7, 21, 16, 30, tzinfo=timezone.utc)
    assert transaction.reference_type == "task_issue"
    assert transaction.reference_id == "TASK-1"
    assert transaction.performed_by_user_id == "user-2"
    assert transaction.performed_by_username == "Alex Mover"
    assert transaction.resulting_on_hand_qty == 9.0
    assert transaction.resulting_available_qty == 8.0
    assert transaction.notes == "moved to field crew"
    assert transaction.lot_number == "lot-1"
    assert transaction.serial_number == "sn-9"


def test_inventory_stock_operation_dtos_raise_expected_validation_codes() -> None:
    with pytest.raises(ValidationError) as exc_balance:
        StockBalance(
            id="bal-1",
            organization_id="org-1",
            stock_item_id="item-1",
            storeroom_id="store-1",
            uom="EA",
            on_hand_qty=10,
            reserved_qty=3,
            available_qty=8,
            updated_at=datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc),
        )
    assert exc_balance.value.code == "INVENTORY_STOCK_BALANCE_AVAILABLE_INVALID"

    with pytest.raises(ValidationError) as exc_source:
        StockReservation.create(
            organization_id="org-1",
            reservation_number="INV-RES-002",
            stock_item_id="item-1",
            storeroom_id="store-1",
            reserved_qty=2,
            uom="EA",
            source_reference_type="",
            source_reference_id="",
        )
    assert exc_source.value.code == "INVENTORY_RESERVATION_SOURCE_REQUIRED"

    with pytest.raises(ValidationError) as exc_qty:
        StockReservation(
            id="res-2",
            organization_id="org-1",
            reservation_number="INV-RES-003",
            stock_item_id="item-1",
            storeroom_id="store-1",
            reserved_qty=5,
            issued_qty=0,
            remaining_qty=5,
            uom="EA",
            status=StockReservationStatus.PARTIALLY_ISSUED,
            source_reference_type="work_order",
            source_reference_id="wo-2",
            created_at=datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc),
        )
    assert exc_qty.value.code == "INVENTORY_RESERVATION_QTY_INVALID"

    with pytest.raises(ValidationError) as exc_closed:
        StockReservation(
            id="res-3",
            organization_id="org-1",
            reservation_number="INV-RES-004",
            stock_item_id="item-1",
            storeroom_id="store-1",
            reserved_qty=5,
            issued_qty=5,
            remaining_qty=0,
            uom="EA",
            status=StockReservationStatus.RELEASED,
            source_reference_type="work_order",
            source_reference_id="wo-3",
            created_at=datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc),
            released_at=datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc),
            cancelled_at=datetime(2026, 7, 21, 11, 0, tzinfo=timezone.utc),
    )
    assert exc_closed.value.code == "INVENTORY_RESERVATION_CLOSED_STATE_INVALID"

    with pytest.raises(ValidationError) as exc_transaction_type:
        StockTransaction(
            id="txn-2",
            organization_id="org-1",
            transaction_number="INV-TXN-002",
            stock_item_id="item-1",
            storeroom_id="store-1",
            transaction_type="unsupported",
            quantity=1,
            uom="EA",
            transaction_at=datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc),
            resulting_on_hand_qty=1,
            resulting_available_qty=1,
        )
    assert exc_transaction_type.value.code == "INVENTORY_STOCK_TRANSACTION_TYPE_INVALID"

    with pytest.raises(ValidationError) as exc_transaction_time:
        StockTransaction(
            id="txn-3",
            organization_id="org-1",
            transaction_number="INV-TXN-003",
            stock_item_id="item-1",
            storeroom_id="store-1",
            transaction_type=StockTransactionType.ISSUE,
            quantity=1,
            uom="EA",
            transaction_at=None,
            resulting_on_hand_qty=1,
            resulting_available_qty=1,
        )
    assert exc_transaction_time.value.code == "INVENTORY_STOCK_TRANSACTION_AT_REQUIRED"

    with pytest.raises(ValidationError) as exc_transaction_available:
        StockTransaction(
            id="txn-4",
            organization_id="org-1",
            transaction_number="INV-TXN-004",
            stock_item_id="item-1",
            storeroom_id="store-1",
            transaction_type=StockTransactionType.RETURN,
            quantity=1,
            uom="EA",
            transaction_at=datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc),
            resulting_on_hand_qty=2,
            resulting_available_qty=3,
        )
    assert exc_transaction_available.value.code == "INVENTORY_STOCK_TRANSACTION_AVAILABLE_INVALID"


def test_inventory_procurement_dtos_normalize_fields_and_validate_ranges() -> None:
    requisition = PurchaseRequisition(
        id="  req-1  ",
        organization_id="  org-1  ",
        requisition_number="  req-001  ",
        requesting_site_id="  site-1  ",
        requesting_storeroom_id="  store-1  ",
        requester_user_id="  user-1  ",
        requester_username="  Buyer One  ",
        status=" approved ",
        purpose="  Restock rotating spares  ",
        needed_by_date="2026-08-15",
        priority=" high ",
        approval_request_id="  appr-1  ",
        source_reference_type=" task ",
        source_reference_id="  task-1  ",
        source_module="  project_management  ",
        source_entity_type="  task  ",
        source_code_snapshot="  tsk-001  ",
        source_title_snapshot="  Replace pump seals  ",
        source_status_snapshot="  approved  ",
        submitted_at=datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc),
        approved_at=datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc),
        notes="  expedite  ",
        created_at=datetime(2026, 7, 19, 8, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc),
        version="2",
    )

    assert requisition.id == "req-1"
    assert requisition.requisition_number == "REQ-001"
    assert requisition.requesting_site_id == "site-1"
    assert requisition.requesting_storeroom_id == "store-1"
    assert requisition.requester_user_id == "user-1"
    assert requisition.requester_username == "Buyer One"
    assert requisition.status is PurchaseRequisitionStatus.APPROVED
    assert requisition.purpose == "Restock rotating spares"
    assert requisition.needed_by_date == date(2026, 8, 15)
    assert requisition.priority == "HIGH"
    assert requisition.approval_request_id == "appr-1"
    assert requisition.source_reference_type == "task"
    assert requisition.source_reference_id == "task-1"
    assert requisition.source_module == "project_management"
    assert requisition.source_entity_type == "task"
    assert requisition.source_code_snapshot == "tsk-001"
    assert requisition.source_title_snapshot == "Replace pump seals"
    assert requisition.source_status_snapshot == "approved"
    assert requisition.notes == "expedite"
    assert requisition.version == 2

    requisition_line = PurchaseRequisitionLine(
        id="  req-line-1  ",
        purchase_requisition_id="  req-1  ",
        line_number="1",
        stock_item_id="  item-1  ",
        description="  Pump seal kit  ",
        quantity_requested="5",
        uom=" ea ",
        needed_by_date="2026-08-15",
        estimated_unit_cost="12.5",
        quantity_sourced="2",
        suggested_supplier_party_id="  supplier-1  ",
        status=" partially_sourced ",
        notes="  primary supplier  ",
    )

    assert requisition_line.id == "req-line-1"
    assert requisition_line.purchase_requisition_id == "req-1"
    assert requisition_line.line_number == 1
    assert requisition_line.stock_item_id == "item-1"
    assert requisition_line.description == "Pump seal kit"
    assert requisition_line.quantity_requested == 5.0
    assert requisition_line.uom == "EA"
    assert requisition_line.needed_by_date == date(2026, 8, 15)
    assert requisition_line.estimated_unit_cost == 12.5
    assert requisition_line.quantity_sourced == 2.0
    assert requisition_line.suggested_supplier_party_id == "supplier-1"
    assert requisition_line.status is PurchaseRequisitionLineStatus.PARTIALLY_SOURCED
    assert requisition_line.notes == "primary supplier"

    purchase_order = PurchaseOrder(
        id="  po-1  ",
        organization_id="  org-1  ",
        po_number="  po-001  ",
        site_id="  site-1  ",
        supplier_party_id="  supplier-1  ",
        status=" sent ",
        order_date="2026-07-22",
        expected_delivery_date="2026-07-24",
        currency_code=" eur ",
        approval_request_id="  appr-po-1  ",
        source_requisition_id="  req-1  ",
        supplier_reference="  sup-ref-01  ",
        submitted_at=datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc),
        approved_at=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
        sent_at=datetime(2026, 7, 22, 10, 0, tzinfo=timezone.utc),
        notes="  release to vendor  ",
        created_at=datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 22, 10, 0, tzinfo=timezone.utc),
        version="3",
    )

    assert purchase_order.id == "po-1"
    assert purchase_order.po_number == "PO-001"
    assert purchase_order.site_id == "site-1"
    assert purchase_order.supplier_party_id == "supplier-1"
    assert purchase_order.status is PurchaseOrderStatus.SENT
    assert purchase_order.order_date == date(2026, 7, 22)
    assert purchase_order.expected_delivery_date == date(2026, 7, 24)
    assert purchase_order.currency_code == "EUR"
    assert purchase_order.approval_request_id == "appr-po-1"
    assert purchase_order.source_requisition_id == "req-1"
    assert purchase_order.supplier_reference == "sup-ref-01"
    assert purchase_order.notes == "release to vendor"
    assert purchase_order.version == 3

    purchase_order_line = PurchaseOrderLine(
        id="  po-line-1  ",
        purchase_order_id="  po-1  ",
        line_number="1",
        stock_item_id="  item-1  ",
        destination_storeroom_id="  store-1  ",
        description="  Pump seal kit  ",
        quantity_ordered="5",
        quantity_received="4",
        quantity_rejected="1",
        uom=" ea ",
        unit_price="11.25",
        expected_delivery_date="2026-07-24",
        source_requisition_line_id="  req-line-1  ",
        status=" fully_received ",
        notes="  final receipt  ",
    )

    assert purchase_order_line.id == "po-line-1"
    assert purchase_order_line.purchase_order_id == "po-1"
    assert purchase_order_line.line_number == 1
    assert purchase_order_line.stock_item_id == "item-1"
    assert purchase_order_line.destination_storeroom_id == "store-1"
    assert purchase_order_line.description == "Pump seal kit"
    assert purchase_order_line.quantity_ordered == 5.0
    assert purchase_order_line.quantity_received == 4.0
    assert purchase_order_line.quantity_rejected == 1.0
    assert purchase_order_line.uom == "EA"
    assert purchase_order_line.unit_price == 11.25
    assert purchase_order_line.expected_delivery_date == date(2026, 7, 24)
    assert purchase_order_line.source_requisition_line_id == "req-line-1"
    assert purchase_order_line.status is PurchaseOrderLineStatus.FULLY_RECEIVED
    assert purchase_order_line.notes == "final receipt"

    receipt = ReceiptHeader(
        id="  rcv-1  ",
        organization_id="  org-1  ",
        receipt_number="  rcv-001  ",
        purchase_order_id="  po-1  ",
        received_site_id="  site-1  ",
        supplier_party_id="  supplier-1  ",
        status=" posted ",
        receipt_date="2026-07-24T10:30:00+00:00",
        supplier_delivery_reference="  del-001  ",
        received_by_user_id="  user-2  ",
        received_by_username="  Store Receiver  ",
        notes="  received complete shipment  ",
        created_at=datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc),
    )

    assert receipt.id == "rcv-1"
    assert receipt.organization_id == "org-1"
    assert receipt.receipt_number == "RCV-001"
    assert receipt.purchase_order_id == "po-1"
    assert receipt.received_site_id == "site-1"
    assert receipt.supplier_party_id == "supplier-1"
    assert receipt.status is ReceiptStatus.POSTED
    assert receipt.receipt_date == datetime(2026, 7, 24, 10, 30, tzinfo=timezone.utc)
    assert receipt.supplier_delivery_reference == "del-001"
    assert receipt.received_by_user_id == "user-2"
    assert receipt.received_by_username == "Store Receiver"
    assert receipt.notes == "received complete shipment"

    receipt_line = ReceiptLine(
        id="  rcv-line-1  ",
        receipt_header_id="  rcv-1  ",
        purchase_order_line_id="  po-line-1  ",
        line_number="1",
        stock_item_id="  item-1  ",
        storeroom_id="  store-1  ",
        quantity_accepted="4",
        quantity_rejected="1",
        uom=" ea ",
        unit_cost="11.0",
        lot_number="  lot-001  ",
        serial_number="  ser-001  ",
        expiry_date="2026-08-31",
        notes="  QA checked  ",
    )

    assert receipt_line.id == "rcv-line-1"
    assert receipt_line.receipt_header_id == "rcv-1"
    assert receipt_line.purchase_order_line_id == "po-line-1"
    assert receipt_line.line_number == 1
    assert receipt_line.stock_item_id == "item-1"
    assert receipt_line.storeroom_id == "store-1"
    assert receipt_line.quantity_accepted == 4.0
    assert receipt_line.quantity_rejected == 1.0
    assert receipt_line.uom == "EA"
    assert receipt_line.unit_cost == 11.0
    assert receipt_line.lot_number == "lot-001"
    assert receipt_line.serial_number == "ser-001"
    assert receipt_line.expiry_date == date(2026, 8, 31)
    assert receipt_line.notes == "QA checked"


def test_inventory_procurement_dtos_raise_expected_validation_codes() -> None:
    with pytest.raises(ValidationError) as exc_source:
        PurchaseRequisition(
            id="req-2",
            organization_id="org-1",
            requisition_number="REQ-002",
            requesting_site_id="site-1",
            requesting_storeroom_id="store-1",
            source_reference_type="task",
            source_reference_id="",
        )
    assert exc_source.value.code == "INVENTORY_REQUISITION_SOURCE_REQUIRED"

    with pytest.raises(ValidationError) as exc_priority:
        PurchaseRequisition(
            id="req-3",
            organization_id="org-1",
            requisition_number="REQ-003",
            requesting_site_id="site-1",
            requesting_storeroom_id="store-1",
            priority="rush-now",
        )
    assert exc_priority.value.code == "INVENTORY_PROCUREMENT_PRIORITY_INVALID"

    with pytest.raises(ValidationError) as exc_requisition_line:
        PurchaseRequisitionLine(
            id="req-line-2",
            purchase_requisition_id="req-1",
            line_number=1,
            stock_item_id="item-1",
            quantity_requested=5,
            quantity_sourced=6,
            uom="EA",
        )
    assert exc_requisition_line.value.code == "INVENTORY_REQUISITION_LINE_QTY_INVALID"

    with pytest.raises(ValidationError) as exc_purchase_order:
        PurchaseOrder(
            id="po-2",
            organization_id="org-1",
            po_number="PO-002",
            site_id="site-1",
            supplier_party_id="supplier-1",
            order_date=date(2026, 7, 25),
            expected_delivery_date=date(2026, 7, 24),
            currency_code="EUR",
        )
    assert exc_purchase_order.value.code == "INVENTORY_PURCHASE_ORDER_DELIVERY_RANGE_INVALID"

    with pytest.raises(ValidationError) as exc_purchase_order_line:
        PurchaseOrderLine(
            id="po-line-2",
            purchase_order_id="po-1",
            line_number=1,
            stock_item_id="item-1",
            destination_storeroom_id="store-1",
            quantity_ordered=5,
            quantity_received=4,
            quantity_rejected=2,
            uom="EA",
        )
    assert exc_purchase_order_line.value.code == "INVENTORY_PURCHASE_ORDER_LINE_QTY_INVALID"

    with pytest.raises(ValidationError) as exc_receipt_status:
        ReceiptHeader(
            id="rcv-2",
            organization_id="org-1",
            receipt_number="RCV-002",
            purchase_order_id="po-1",
            received_site_id="site-1",
            supplier_party_id="supplier-1",
            status="draft",
        )
    assert exc_receipt_status.value.code == "INVENTORY_RECEIPT_STATUS_INVALID"

    with pytest.raises(ValidationError) as exc_receipt_line:
        ReceiptLine(
            id="rcv-line-2",
            receipt_header_id="rcv-1",
            purchase_order_line_id="po-line-1",
            line_number=1,
            stock_item_id="item-1",
            storeroom_id="store-1",
            quantity_accepted=0,
            quantity_rejected=0,
            uom="EA",
        )
    assert exc_receipt_line.value.code == "INVENTORY_RECEIPT_QUANTITY_REQUIRED"
