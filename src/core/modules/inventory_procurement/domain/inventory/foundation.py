from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.modules.inventory_procurement.domain._validation import (
    normalize_enum,
    normalize_inventory_code,
    normalize_inventory_name,
    normalize_nonnegative_days,
    normalize_nonnegative_quantity,
    normalize_optional_date,
    normalize_optional_datetime,
    normalize_optional_identifier,
    normalize_optional_nonnegative_quantity,
    normalize_optional_text,
    normalize_positive_int,
    normalize_required_text,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass


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


@validated_dataclass
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

    @field_validator("id", "organization_id", "storeroom_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Storage location ID is required.",
                "INVENTORY_LOCATION_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "INVENTORY_LOCATION_ORGANIZATION_REQUIRED",
            ),
            "storeroom_id": (
                "Storeroom ID is required.",
                "INVENTORY_STOREROOM_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("location_code", mode="before")
    @classmethod
    def _validate_location_code(cls, value: object) -> str:
        return normalize_inventory_code(value, label="Location code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_inventory_name(value, label="Location name")

    @field_validator("parent_location_id", mode="before")
    @classmethod
    def _normalize_parent_location_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("location_type", mode="before")
    @classmethod
    def _validate_location_type(cls, value: object) -> StorageLocationType:
        return normalize_enum(
            value,
            enum_type=StorageLocationType,
            default=StorageLocationType.BIN,
            message="Storage location type is invalid.",
            code="INVENTORY_LOCATION_TYPE_INVALID",
        )

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Storage location {info.field_name.replace('_', ' ')} is invalid.",
            code=f"INVENTORY_LOCATION_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Storage location version must be positive.",
            code="INVENTORY_LOCATION_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "StorageLocation":
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="INVENTORY_LOCATION_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        storeroom_id: str,
        location_code: str,
        name: str,
        parent_location_id: str | None = None,
        location_type: StorageLocationType | str = StorageLocationType.BIN,
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


@validated_dataclass
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

    @field_validator("id", "organization_id", "stock_item_id", "storeroom_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Reorder policy ID is required.",
                "INVENTORY_REORDER_POLICY_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "INVENTORY_REORDER_POLICY_ORGANIZATION_REQUIRED",
            ),
            "stock_item_id": (
                "Stock item ID is required.",
                "INVENTORY_ITEM_REQUIRED",
            ),
            "storeroom_id": (
                "Storeroom ID is required.",
                "INVENTORY_STOREROOM_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("location_id", "preferred_supplier_party_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("policy_name", mode="before")
    @classmethod
    def _normalize_policy_name(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "min_qty",
        "max_qty",
        "reorder_point",
        "reorder_qty",
        "economic_order_qty",
        mode="before",
    )
    @classmethod
    def _validate_quantities(cls, value: object, info) -> float:
        labels = {
            "min_qty": "Minimum quantity",
            "max_qty": "Maximum quantity",
            "reorder_point": "Reorder point",
            "reorder_qty": "Reorder quantity",
            "economic_order_qty": "Economic order quantity",
        }
        return normalize_nonnegative_quantity(value, label=labels[info.field_name])

    @field_validator("lead_time_days", "review_period_days", mode="before")
    @classmethod
    def _validate_days(cls, value: object, info) -> int | None:
        labels = {
            "lead_time_days": "Lead time",
            "review_period_days": "Review period",
        }
        return normalize_nonnegative_days(value, label=labels[info.field_name])

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Reorder policy {info.field_name.replace('_', ' ')} is invalid.",
            code=f"INVENTORY_REORDER_POLICY_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Reorder policy version must be positive.",
            code="INVENTORY_REORDER_POLICY_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "ReorderPolicy":
        if self.max_qty and self.max_qty < self.min_qty:
            raise ValidationError(
                "Maximum quantity cannot be less than minimum quantity.",
                code="INVENTORY_REORDER_POLICY_MAX_INVALID",
            )
        if self.max_qty and self.reorder_point > self.max_qty:
            raise ValidationError(
                "Reorder point cannot exceed maximum quantity.",
                code="INVENTORY_REORDER_POLICY_POINT_INVALID",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="INVENTORY_REORDER_POLICY_UPDATED_RANGE_INVALID",
            )
        return self

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
        lead_time_days: int | str | None = None,
        review_period_days: int | str | None = None,
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


@validated_dataclass
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

    @field_validator("id", "organization_id", "stock_item_id", "storeroom_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Cycle count ID is required.",
                "INVENTORY_CYCLE_COUNT_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "INVENTORY_CYCLE_COUNT_ORGANIZATION_REQUIRED",
            ),
            "stock_item_id": (
                "Stock item ID is required.",
                "INVENTORY_ITEM_REQUIRED",
            ),
            "storeroom_id": (
                "Storeroom ID is required.",
                "INVENTORY_STOREROOM_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("cycle_count_number", mode="before")
    @classmethod
    def _validate_cycle_count_number(cls, value: object) -> str:
        return normalize_inventory_code(value, label="Cycle count number")

    @field_validator("location_id", "counted_by_user_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("scheduled_count_date", mode="before")
    @classmethod
    def _validate_scheduled_count_date(cls, value: object) -> date | None:
        return normalize_optional_date(value, label="Scheduled count date")

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> CycleCountStatus:
        return normalize_enum(
            value,
            enum_type=CycleCountStatus,
            default=CycleCountStatus.PLANNED,
            message="Cycle count status is invalid.",
            code="INVENTORY_CYCLE_COUNT_STATUS_INVALID",
        )

    @field_validator("expected_qty", mode="before")
    @classmethod
    def _validate_expected_qty(cls, value: object) -> float:
        return normalize_nonnegative_quantity(value, label="Expected quantity")

    @field_validator("counted_qty", mode="before")
    @classmethod
    def _validate_counted_qty(cls, value: object) -> float | None:
        return normalize_optional_nonnegative_quantity(value, label="Counted quantity")

    @field_validator("variance_qty", mode="before")
    @classmethod
    def _validate_variance_qty(cls, value: object) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Variance quantity is invalid.",
                code="INVENTORY_QUANTITY_INVALID",
            ) from exc

    @field_validator("counted_by_username", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("created_at", "completed_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Cycle count {info.field_name.replace('_', ' ')} is invalid.",
            code=f"INVENTORY_CYCLE_COUNT_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Cycle count version must be positive.",
            code="INVENTORY_CYCLE_COUNT_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "CycleCount":
        if self.counted_qty is not None:
            object.__setattr__(
                self,
                "variance_qty",
                round(float(self.counted_qty) - float(self.expected_qty or 0.0), 6),
            )
        if (
            self.completed_at is not None
            and self.created_at is not None
            and self.completed_at < self.created_at
        ):
            raise ValidationError(
                "Completed timestamp cannot be earlier than created timestamp.",
                code="INVENTORY_CYCLE_COUNT_COMPLETED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        cycle_count_number: str,
        stock_item_id: str,
        storeroom_id: str,
        location_id: str | None = None,
        scheduled_count_date: date | str | None = None,
        status: CycleCountStatus | str = CycleCountStatus.PLANNED,
        expected_qty: float = 0.0,
        counted_qty: float | None = None,
        variance_qty: float = 0.0,
        counted_by_user_id: str | None = None,
        counted_by_username: str = "",
        completed_at: datetime | str | None = None,
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
