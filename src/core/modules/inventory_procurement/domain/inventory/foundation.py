from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from src.core.platform.common.ids import generate_id


class StorageLocationType(str, Enum):
    ZONE = "ZONE"
    BIN = "BIN"
    SHELF = "SHELF"
    STAGING = "STAGING"
    RECEIVING = "RECEIVING"
    ISSUE_POINT = "ISSUE_POINT"


class CycleCountStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class StorageLocation:
    id: str
    organization_id: str
    storeroom_id: str
    location_code: str
    name: str
    parent_location_id: str | None = None
    location_type: StorageLocationType = StorageLocationType.BIN
    is_active: bool = True
    is_quarantine: bool = False
    allows_issue: bool = True
    allows_putaway: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        storeroom_id: str,
        location_code: str,
        name: str,
        parent_location_id: str | None = None,
        location_type: StorageLocationType = StorageLocationType.BIN,
        is_active: bool = True,
        is_quarantine: bool = False,
        allows_issue: bool = True,
        allows_putaway: bool = True,
        notes: str = "",
    ) -> "StorageLocation":
        now = datetime.now(timezone.utc)
        return StorageLocation(
            id=generate_id(),
            organization_id=organization_id,
            storeroom_id=storeroom_id,
            location_code=location_code,
            name=name,
            parent_location_id=parent_location_id,
            location_type=location_type,
            is_active=is_active,
            is_quarantine=is_quarantine,
            allows_issue=allows_issue,
            allows_putaway=allows_putaway,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class ReorderPolicy:
    id: str
    organization_id: str
    stock_item_id: str
    storeroom_id: str
    location_id: str | None = None
    policy_name: str = ""
    is_active: bool = True
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    economic_order_qty: float = 0.0
    lead_time_days: int | None = None
    review_period_days: int | None = None
    preferred_supplier_party_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        stock_item_id: str,
        storeroom_id: str,
        location_id: str | None = None,
        policy_name: str = "",
        is_active: bool = True,
        min_qty: float = 0.0,
        max_qty: float = 0.0,
        reorder_point: float = 0.0,
        reorder_qty: float = 0.0,
        economic_order_qty: float = 0.0,
        lead_time_days: int | None = None,
        review_period_days: int | None = None,
        preferred_supplier_party_id: str | None = None,
    ) -> "ReorderPolicy":
        now = datetime.now(timezone.utc)
        return ReorderPolicy(
            id=generate_id(),
            organization_id=organization_id,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            location_id=location_id,
            policy_name=policy_name,
            is_active=is_active,
            min_qty=min_qty,
            max_qty=max_qty,
            reorder_point=reorder_point,
            reorder_qty=reorder_qty,
            economic_order_qty=economic_order_qty,
            lead_time_days=lead_time_days,
            review_period_days=review_period_days,
            preferred_supplier_party_id=preferred_supplier_party_id,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class CycleCount:
    id: str
    organization_id: str
    cycle_count_number: str
    stock_item_id: str
    storeroom_id: str
    location_id: str | None = None
    scheduled_count_date: date | None = None
    status: CycleCountStatus = CycleCountStatus.PLANNED
    expected_qty: float = 0.0
    counted_qty: float | None = None
    variance_qty: float = 0.0
    counted_by_user_id: str | None = None
    counted_by_username: str = ""
    created_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        cycle_count_number: str,
        stock_item_id: str,
        storeroom_id: str,
        location_id: str | None = None,
        scheduled_count_date: date | None = None,
        status: CycleCountStatus = CycleCountStatus.PLANNED,
        expected_qty: float = 0.0,
        counted_qty: float | None = None,
        variance_qty: float = 0.0,
        counted_by_user_id: str | None = None,
        counted_by_username: str = "",
        completed_at: datetime | None = None,
        notes: str = "",
    ) -> "CycleCount":
        now = datetime.now(timezone.utc)
        return CycleCount(
            id=generate_id(),
            organization_id=organization_id,
            cycle_count_number=cycle_count_number,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            location_id=location_id,
            scheduled_count_date=scheduled_count_date,
            status=status,
            expected_qty=expected_qty,
            counted_qty=counted_qty,
            variance_qty=variance_qty,
            counted_by_user_id=counted_by_user_id,
            counted_by_username=counted_by_username,
            created_at=now,
            completed_at=completed_at,
            notes=notes,
            version=1,
        )


__all__ = [
    "CycleCount",
    "CycleCountStatus",
    "ReorderPolicy",
    "StorageLocation",
    "StorageLocationType",
]
