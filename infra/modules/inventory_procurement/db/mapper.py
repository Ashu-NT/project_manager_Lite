from __future__ import annotations

from core.modules.inventory_procurement.domain import (
    PurchaseRequisition,
    PurchaseRequisitionLine,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
    StockBalance,
    StockItem,
    StockTransaction,
    StockTransactionType,
    Storeroom,
)
from infra.platform.db.models import (
    PurchaseRequisitionLineORM,
    PurchaseRequisitionORM,
    StockBalanceORM,
    StockItemORM,
    StockTransactionORM,
    StoreroomORM,
)


def stock_item_to_orm(item: StockItem) -> StockItemORM:
    return StockItemORM(
        id=item.id,
        organization_id=item.organization_id,
        item_code=item.item_code,
        name=item.name,
        description=item.description or None,
        item_type=item.item_type or None,
        status=item.status,
        stock_uom=item.stock_uom,
        order_uom=item.order_uom,
        issue_uom=item.issue_uom,
        category_code=item.category_code or None,
        commodity_code=item.commodity_code or None,
        is_stocked=item.is_stocked,
        is_purchase_allowed=item.is_purchase_allowed,
        is_active=item.is_active,
        default_reorder_policy=item.default_reorder_policy or None,
        min_qty=item.min_qty,
        max_qty=item.max_qty,
        reorder_point=item.reorder_point,
        reorder_qty=item.reorder_qty,
        lead_time_days=item.lead_time_days,
        is_lot_tracked=item.is_lot_tracked,
        is_serial_tracked=item.is_serial_tracked,
        shelf_life_days=item.shelf_life_days,
        preferred_party_id=item.preferred_party_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        notes=item.notes or None,
        version=getattr(item, "version", 1),
    )


def stock_item_from_orm(obj: StockItemORM) -> StockItem:
    return StockItem(
        id=obj.id,
        organization_id=obj.organization_id,
        item_code=obj.item_code,
        name=obj.name,
        description=obj.description or "",
        item_type=obj.item_type or "",
        status=obj.status,
        stock_uom=obj.stock_uom,
        order_uom=obj.order_uom,
        issue_uom=obj.issue_uom,
        category_code=obj.category_code or "",
        commodity_code=obj.commodity_code or "",
        is_stocked=obj.is_stocked,
        is_purchase_allowed=obj.is_purchase_allowed,
        is_active=obj.is_active,
        default_reorder_policy=obj.default_reorder_policy or "",
        min_qty=float(obj.min_qty or 0.0),
        max_qty=float(obj.max_qty or 0.0),
        reorder_point=float(obj.reorder_point or 0.0),
        reorder_qty=float(obj.reorder_qty or 0.0),
        lead_time_days=obj.lead_time_days,
        is_lot_tracked=obj.is_lot_tracked,
        is_serial_tracked=obj.is_serial_tracked,
        shelf_life_days=obj.shelf_life_days,
        preferred_party_id=obj.preferred_party_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


def storeroom_to_orm(storeroom: Storeroom) -> StoreroomORM:
    return StoreroomORM(
        id=storeroom.id,
        organization_id=storeroom.organization_id,
        storeroom_code=storeroom.storeroom_code,
        name=storeroom.name,
        description=storeroom.description or None,
        site_id=storeroom.site_id,
        status=storeroom.status,
        storeroom_type=storeroom.storeroom_type or None,
        is_active=storeroom.is_active,
        is_internal_supplier=storeroom.is_internal_supplier,
        allows_issue=storeroom.allows_issue,
        allows_transfer=storeroom.allows_transfer,
        allows_receiving=storeroom.allows_receiving,
        default_currency_code=storeroom.default_currency_code or None,
        manager_party_id=storeroom.manager_party_id,
        created_at=storeroom.created_at,
        updated_at=storeroom.updated_at,
        notes=storeroom.notes or None,
        version=getattr(storeroom, "version", 1),
    )


def storeroom_from_orm(obj: StoreroomORM) -> Storeroom:
    return Storeroom(
        id=obj.id,
        organization_id=obj.organization_id,
        storeroom_code=obj.storeroom_code,
        name=obj.name,
        description=obj.description or "",
        site_id=obj.site_id,
        status=obj.status,
        storeroom_type=obj.storeroom_type or "",
        is_active=obj.is_active,
        is_internal_supplier=obj.is_internal_supplier,
        allows_issue=obj.allows_issue,
        allows_transfer=obj.allows_transfer,
        allows_receiving=obj.allows_receiving,
        default_currency_code=obj.default_currency_code or "",
        manager_party_id=obj.manager_party_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


def stock_balance_to_orm(balance: StockBalance) -> StockBalanceORM:
    return StockBalanceORM(
        id=balance.id,
        organization_id=balance.organization_id,
        stock_item_id=balance.stock_item_id,
        storeroom_id=balance.storeroom_id,
        uom=balance.uom,
        on_hand_qty=balance.on_hand_qty,
        reserved_qty=balance.reserved_qty,
        available_qty=balance.available_qty,
        on_order_qty=balance.on_order_qty,
        committed_qty=balance.committed_qty,
        average_cost=balance.average_cost,
        last_receipt_at=balance.last_receipt_at,
        last_issue_at=balance.last_issue_at,
        reorder_required=balance.reorder_required,
        updated_at=balance.updated_at,
        version=getattr(balance, "version", 1),
    )


def stock_balance_from_orm(obj: StockBalanceORM) -> StockBalance:
    return StockBalance(
        id=obj.id,
        organization_id=obj.organization_id,
        stock_item_id=obj.stock_item_id,
        storeroom_id=obj.storeroom_id,
        uom=obj.uom,
        on_hand_qty=float(obj.on_hand_qty or 0.0),
        reserved_qty=float(obj.reserved_qty or 0.0),
        available_qty=float(obj.available_qty or 0.0),
        on_order_qty=float(obj.on_order_qty or 0.0),
        committed_qty=float(obj.committed_qty or 0.0),
        average_cost=float(obj.average_cost or 0.0),
        last_receipt_at=obj.last_receipt_at,
        last_issue_at=obj.last_issue_at,
        reorder_required=obj.reorder_required,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
    )


def stock_transaction_to_orm(transaction: StockTransaction) -> StockTransactionORM:
    return StockTransactionORM(
        id=transaction.id,
        organization_id=transaction.organization_id,
        transaction_number=transaction.transaction_number,
        stock_item_id=transaction.stock_item_id,
        storeroom_id=transaction.storeroom_id,
        transaction_type=transaction.transaction_type,
        quantity=transaction.quantity,
        uom=transaction.uom,
        unit_cost=transaction.unit_cost,
        transaction_at=transaction.transaction_at,
        reference_type=transaction.reference_type or None,
        reference_id=transaction.reference_id or None,
        performed_by_user_id=transaction.performed_by_user_id,
        performed_by_username=transaction.performed_by_username or None,
        resulting_on_hand_qty=transaction.resulting_on_hand_qty,
        resulting_available_qty=transaction.resulting_available_qty,
        notes=transaction.notes or None,
    )


def stock_transaction_from_orm(obj: StockTransactionORM) -> StockTransaction:
    return StockTransaction(
        id=obj.id,
        organization_id=obj.organization_id,
        transaction_number=obj.transaction_number,
        stock_item_id=obj.stock_item_id,
        storeroom_id=obj.storeroom_id,
        transaction_type=StockTransactionType(obj.transaction_type),
        quantity=float(obj.quantity or 0.0),
        uom=obj.uom,
        unit_cost=float(obj.unit_cost or 0.0),
        transaction_at=obj.transaction_at,
        reference_type=obj.reference_type or "",
        reference_id=obj.reference_id or "",
        performed_by_user_id=obj.performed_by_user_id,
        performed_by_username=obj.performed_by_username or "",
        resulting_on_hand_qty=float(obj.resulting_on_hand_qty or 0.0),
        resulting_available_qty=float(obj.resulting_available_qty or 0.0),
        notes=obj.notes or "",
    )


def purchase_requisition_to_orm(requisition: PurchaseRequisition) -> PurchaseRequisitionORM:
    return PurchaseRequisitionORM(
        id=requisition.id,
        organization_id=requisition.organization_id,
        requisition_number=requisition.requisition_number,
        requesting_site_id=requisition.requesting_site_id,
        requesting_storeroom_id=requisition.requesting_storeroom_id,
        requester_user_id=requisition.requester_user_id,
        requester_username=requisition.requester_username or None,
        status=requisition.status,
        purpose=requisition.purpose or None,
        needed_by_date=requisition.needed_by_date,
        priority=requisition.priority or None,
        approval_request_id=requisition.approval_request_id,
        source_reference_type=requisition.source_reference_type or None,
        source_reference_id=requisition.source_reference_id or None,
        submitted_at=requisition.submitted_at,
        approved_at=requisition.approved_at,
        cancelled_at=requisition.cancelled_at,
        notes=requisition.notes or None,
        created_at=requisition.created_at,
        updated_at=requisition.updated_at,
        version=getattr(requisition, "version", 1),
    )


def purchase_requisition_from_orm(obj: PurchaseRequisitionORM) -> PurchaseRequisition:
    return PurchaseRequisition(
        id=obj.id,
        organization_id=obj.organization_id,
        requisition_number=obj.requisition_number,
        requesting_site_id=obj.requesting_site_id,
        requesting_storeroom_id=obj.requesting_storeroom_id,
        requester_user_id=obj.requester_user_id,
        requester_username=obj.requester_username or "",
        status=PurchaseRequisitionStatus(obj.status),
        purpose=obj.purpose or "",
        needed_by_date=obj.needed_by_date,
        priority=obj.priority or "",
        approval_request_id=obj.approval_request_id,
        source_reference_type=obj.source_reference_type or "",
        source_reference_id=obj.source_reference_id or "",
        submitted_at=obj.submitted_at,
        approved_at=obj.approved_at,
        cancelled_at=obj.cancelled_at,
        notes=obj.notes or "",
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
    )


def purchase_requisition_line_to_orm(line: PurchaseRequisitionLine) -> PurchaseRequisitionLineORM:
    return PurchaseRequisitionLineORM(
        id=line.id,
        purchase_requisition_id=line.purchase_requisition_id,
        line_number=line.line_number,
        stock_item_id=line.stock_item_id,
        description=line.description or None,
        quantity_requested=line.quantity_requested,
        uom=line.uom,
        needed_by_date=line.needed_by_date,
        estimated_unit_cost=line.estimated_unit_cost,
        suggested_supplier_party_id=line.suggested_supplier_party_id,
        status=line.status,
        notes=line.notes or None,
    )


def purchase_requisition_line_from_orm(obj: PurchaseRequisitionLineORM) -> PurchaseRequisitionLine:
    return PurchaseRequisitionLine(
        id=obj.id,
        purchase_requisition_id=obj.purchase_requisition_id,
        line_number=obj.line_number,
        stock_item_id=obj.stock_item_id,
        description=obj.description or "",
        quantity_requested=float(obj.quantity_requested or 0.0),
        uom=obj.uom,
        needed_by_date=obj.needed_by_date,
        estimated_unit_cost=float(obj.estimated_unit_cost or 0.0),
        suggested_supplier_party_id=obj.suggested_supplier_party_id,
        status=PurchaseRequisitionLineStatus(obj.status),
        notes=obj.notes or "",
    )


__all__ = [
    "purchase_requisition_from_orm",
    "purchase_requisition_line_from_orm",
    "purchase_requisition_line_to_orm",
    "purchase_requisition_to_orm",
    "stock_balance_from_orm",
    "stock_balance_to_orm",
    "stock_item_from_orm",
    "stock_item_to_orm",
    "stock_transaction_from_orm",
    "stock_transaction_to_orm",
    "storeroom_from_orm",
    "storeroom_to_orm",
]
