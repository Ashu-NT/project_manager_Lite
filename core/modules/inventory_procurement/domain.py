from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from core.modules.project_management.domain.identifiers import generate_id


class StockTransactionType(str, Enum):
    OPENING_BALANCE = "OPENING_BALANCE"
    ADJUSTMENT_INCREASE = "ADJUSTMENT_INCREASE"
    ADJUSTMENT_DECREASE = "ADJUSTMENT_DECREASE"


@dataclass
class StockItem:
    id: str
    organization_id: str
    item_code: str
    name: str
    description: str = ""
    item_type: str = ""
    status: str = "DRAFT"
    stock_uom: str = ""
    order_uom: str = ""
    issue_uom: str = ""
    category_code: str = ""
    commodity_code: str = ""
    is_stocked: bool = True
    is_purchase_allowed: bool = True
    is_active: bool = False
    default_reorder_policy: str = ""
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    lead_time_days: int | None = None
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    shelf_life_days: int | None = None
    preferred_party_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        item_code: str,
        name: str,
        description: str = "",
        item_type: str = "",
        status: str = "DRAFT",
        stock_uom: str,
        order_uom: str = "",
        issue_uom: str = "",
        category_code: str = "",
        commodity_code: str = "",
        is_stocked: bool = True,
        is_purchase_allowed: bool = True,
        is_active: bool = False,
        default_reorder_policy: str = "",
        min_qty: float = 0.0,
        max_qty: float = 0.0,
        reorder_point: float = 0.0,
        reorder_qty: float = 0.0,
        lead_time_days: int | None = None,
        is_lot_tracked: bool = False,
        is_serial_tracked: bool = False,
        shelf_life_days: int | None = None,
        preferred_party_id: str | None = None,
        notes: str = "",
    ) -> "StockItem":
        now = datetime.now(timezone.utc)
        return StockItem(
            id=generate_id(),
            organization_id=organization_id,
            item_code=item_code,
            name=name,
            description=description,
            item_type=item_type,
            status=status,
            stock_uom=stock_uom,
            order_uom=order_uom,
            issue_uom=issue_uom,
            category_code=category_code,
            commodity_code=commodity_code,
            is_stocked=is_stocked,
            is_purchase_allowed=is_purchase_allowed,
            is_active=is_active,
            default_reorder_policy=default_reorder_policy,
            min_qty=min_qty,
            max_qty=max_qty,
            reorder_point=reorder_point,
            reorder_qty=reorder_qty,
            lead_time_days=lead_time_days,
            is_lot_tracked=is_lot_tracked,
            is_serial_tracked=is_serial_tracked,
            shelf_life_days=shelf_life_days,
            preferred_party_id=preferred_party_id,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


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


__all__ = [
    "StockBalance",
    "StockItem",
    "StockTransaction",
    "StockTransactionType",
    "Storeroom",
]
