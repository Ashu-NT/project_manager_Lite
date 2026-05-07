from __future__ import annotations

from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockBalance,
    StockReservation,
    StockReservationStatus,
    StockTransaction,
    StockTransactionType,
    Storeroom,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.inventory import (
    StockBalanceORM,
    StockReservationORM,
    StockTransactionORM,
    StoreroomORM,
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
        requires_reservation_for_issue=storeroom.requires_reservation_for_issue,
        requires_supplier_reference_for_receipt=storeroom.requires_supplier_reference_for_receipt,
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
        requires_reservation_for_issue=obj.requires_reservation_for_issue,
        requires_supplier_reference_for_receipt=obj.requires_supplier_reference_for_receipt,
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


def stock_reservation_to_orm(reservation: StockReservation) -> StockReservationORM:
    return StockReservationORM(
        id=reservation.id,
        organization_id=reservation.organization_id,
        reservation_number=reservation.reservation_number,
        stock_item_id=reservation.stock_item_id,
        storeroom_id=reservation.storeroom_id,
        reserved_qty=reservation.reserved_qty,
        issued_qty=reservation.issued_qty,
        remaining_qty=reservation.remaining_qty,
        uom=reservation.uom,
        status=reservation.status,
        need_by_date=reservation.need_by_date,
        source_reference_type=reservation.source_reference_type or None,
        source_reference_id=reservation.source_reference_id or None,
        requested_by_user_id=reservation.requested_by_user_id,
        requested_by_username=reservation.requested_by_username or None,
        created_at=reservation.created_at,
        released_at=reservation.released_at,
        cancelled_at=reservation.cancelled_at,
        notes=reservation.notes or None,
        version=getattr(reservation, "version", 1),
    )


def stock_reservation_from_orm(obj: StockReservationORM) -> StockReservation:
    return StockReservation(
        id=obj.id,
        organization_id=obj.organization_id,
        reservation_number=obj.reservation_number,
        stock_item_id=obj.stock_item_id,
        storeroom_id=obj.storeroom_id,
        reserved_qty=float(obj.reserved_qty or 0.0),
        issued_qty=float(obj.issued_qty or 0.0),
        remaining_qty=float(obj.remaining_qty or 0.0),
        uom=obj.uom,
        status=StockReservationStatus(obj.status),
        need_by_date=obj.need_by_date,
        source_reference_type=obj.source_reference_type or "",
        source_reference_id=obj.source_reference_id or "",
        requested_by_user_id=obj.requested_by_user_id,
        requested_by_username=obj.requested_by_username or "",
        created_at=obj.created_at,
        released_at=obj.released_at,
        cancelled_at=obj.cancelled_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "stock_balance_from_orm",
    "stock_balance_to_orm",
    "stock_reservation_from_orm",
    "stock_reservation_to_orm",
    "stock_transaction_from_orm",
    "stock_transaction_to_orm",
    "storeroom_from_orm",
    "storeroom_to_orm",
]
