from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from src.core.platform.common.ids import generate_id


class StockTransactionType(str, Enum):
    OPENING_BALANCE = "OPENING_BALANCE"
    ADJUSTMENT_INCREASE = "ADJUSTMENT_INCREASE"
    ADJUSTMENT_DECREASE = "ADJUSTMENT_DECREASE"
    ISSUE = "ISSUE"
    RETURN = "RETURN"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    RESERVATION_HOLD = "RESERVATION_HOLD"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"


class StockReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PARTIALLY_ISSUED = "PARTIALLY_ISSUED"
    FULLY_ISSUED = "FULLY_ISSUED"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"


@dataclass
class Storeroom:
    id: str
    organization_id: str
    storeroom_code: str
    name: str
    description: str = ""
    site_id: str = ""
    status: str = "DRAFT"
    storeroom_type: str = ""
    is_active: bool = False
    is_internal_supplier: bool = False
    allows_issue: bool = True
    allows_transfer: bool = True
    allows_receiving: bool = True
    requires_reservation_for_issue: bool = False
    requires_supplier_reference_for_receipt: bool = False
    default_currency_code: str = ""
    manager_party_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        storeroom_code: str,
        name: str,
        site_id: str,
        description: str = "",
        status: str = "DRAFT",
        storeroom_type: str = "",
        is_active: bool = False,
        is_internal_supplier: bool = False,
        allows_issue: bool = True,
        allows_transfer: bool = True,
        allows_receiving: bool = True,
        requires_reservation_for_issue: bool = False,
        requires_supplier_reference_for_receipt: bool = False,
        default_currency_code: str = "",
        manager_party_id: str | None = None,
        notes: str = "",
    ) -> "Storeroom":
        now = datetime.now(timezone.utc)
        return Storeroom(
            id=generate_id(),
            organization_id=organization_id,
            storeroom_code=storeroom_code,
            name=name,
            description=description,
            site_id=site_id,
            status=status,
            storeroom_type=storeroom_type,
            is_active=is_active,
            is_internal_supplier=is_internal_supplier,
            allows_issue=allows_issue,
            allows_transfer=allows_transfer,
            allows_receiving=allows_receiving,
            requires_reservation_for_issue=requires_reservation_for_issue,
            requires_supplier_reference_for_receipt=requires_supplier_reference_for_receipt,
            default_currency_code=default_currency_code,
            manager_party_id=manager_party_id,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


@dataclass
class StockBalance:
    id: str
    organization_id: str
    stock_item_id: str
    storeroom_id: str
    uom: str
    on_hand_qty: float = 0.0
    reserved_qty: float = 0.0
    available_qty: float = 0.0
    on_order_qty: float = 0.0
    committed_qty: float = 0.0
    average_cost: float = 0.0
    last_receipt_at: datetime | None = None
    last_issue_at: datetime | None = None
    reorder_required: bool = False
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        stock_item_id: str,
        storeroom_id: str,
        uom: str,
    ) -> "StockBalance":
        now = datetime.now(timezone.utc)
        return StockBalance(
            id=generate_id(),
            organization_id=organization_id,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            uom=uom,
            updated_at=now,
            version=1,
        )


@dataclass
class StockTransaction:
    id: str
    organization_id: str
    transaction_number: str
    stock_item_id: str
    storeroom_id: str
    transaction_type: StockTransactionType
    quantity: float
    uom: str
    unit_cost: float = 0.0
    transaction_at: datetime | None = None
    reference_type: str = ""
    reference_id: str = ""
    performed_by_user_id: str | None = None
    performed_by_username: str = ""
    resulting_on_hand_qty: float = 0.0
    resulting_available_qty: float = 0.0
    notes: str = ""

    @staticmethod
    def create(
        *,
        organization_id: str,
        transaction_number: str,
        stock_item_id: str,
        storeroom_id: str,
        transaction_type: StockTransactionType,
        quantity: float,
        uom: str,
        unit_cost: float = 0.0,
        transaction_at: datetime | None = None,
        reference_type: str = "",
        reference_id: str = "",
        performed_by_user_id: str | None = None,
        performed_by_username: str = "",
        resulting_on_hand_qty: float = 0.0,
        resulting_available_qty: float = 0.0,
        notes: str = "",
    ) -> "StockTransaction":
        return StockTransaction(
            id=generate_id(),
            organization_id=organization_id,
            transaction_number=transaction_number,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            transaction_type=transaction_type,
            quantity=quantity,
            uom=uom,
            unit_cost=unit_cost,
            transaction_at=transaction_at or datetime.now(timezone.utc),
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by_user_id=performed_by_user_id,
            performed_by_username=performed_by_username,
            resulting_on_hand_qty=resulting_on_hand_qty,
            resulting_available_qty=resulting_available_qty,
            notes=notes,
        )


@dataclass
class StockReservation:
    id: str
    organization_id: str
    reservation_number: str
    stock_item_id: str
    storeroom_id: str
    reserved_qty: float
    issued_qty: float = 0.0
    remaining_qty: float = 0.0
    uom: str = ""
    status: StockReservationStatus = StockReservationStatus.ACTIVE
    need_by_date: date | None = None
    source_reference_type: str = ""
    source_reference_id: str = ""
    requested_by_user_id: str | None = None
    requested_by_username: str = ""
    created_at: datetime | None = None
    released_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        reservation_number: str,
        stock_item_id: str,
        storeroom_id: str,
        reserved_qty: float,
        uom: str,
        issued_qty: float = 0.0,
        remaining_qty: float | None = None,
        status: StockReservationStatus = StockReservationStatus.ACTIVE,
        need_by_date: date | None = None,
        source_reference_type: str = "",
        source_reference_id: str = "",
        requested_by_user_id: str | None = None,
        requested_by_username: str = "",
        released_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        notes: str = "",
    ) -> "StockReservation":
        now = datetime.now(timezone.utc)
        effective_remaining = (
            float(remaining_qty)
            if remaining_qty is not None
            else max(0.0, float(reserved_qty or 0.0) - float(issued_qty or 0.0))
        )
        return StockReservation(
            id=generate_id(),
            organization_id=organization_id,
            reservation_number=reservation_number,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            reserved_qty=reserved_qty,
            issued_qty=issued_qty,
            remaining_qty=effective_remaining,
            uom=uom,
            status=status,
            need_by_date=need_by_date,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            requested_by_user_id=requested_by_user_id,
            requested_by_username=requested_by_username,
            created_at=now,
            released_at=released_at,
            cancelled_at=cancelled_at,
            notes=notes,
            version=1,
        )
