from __future__ import annotations

from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.modules.inventory_procurement.domain._validation import (
    ITEM_STATUS_VALUES,
    normalize_inventory_code,
    normalize_inventory_name,
    normalize_item_category_type,
    normalize_nonnegative_days,
    normalize_nonnegative_quantity,
    normalize_optional_datetime,
    normalize_optional_identifier,
    normalize_optional_nonnegative_quantity,
    normalize_optional_text,
    normalize_optional_upper_text,
    normalize_positive_int,
    normalize_required_text,
    normalize_status,
    normalize_uom,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass
class InventoryItemCategory:
    id: str
    organization_id: str
    category_code: str
    name: str
    description: str = ""
    category_type: str = "MATERIAL"
    is_equipment: bool = False
    supports_project_usage: bool = False
    supports_maintenance_usage: bool = False
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Inventory item category ID is required.",
                "INVENTORY_CATEGORY_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "INVENTORY_CATEGORY_ORGANIZATION_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("category_code", mode="before")
    @classmethod
    def _validate_category_code(cls, value: object) -> str:
        return normalize_inventory_code(value, label="Category code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_inventory_name(value, label="Category name")

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("category_type", mode="before")
    @classmethod
    def _validate_category_type(cls, value: object) -> str:
        return normalize_item_category_type(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Inventory item category {info.field_name.replace('_', ' ')} is invalid.",
            code=f"INVENTORY_CATEGORY_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Inventory item category version must be positive.",
            code="INVENTORY_CATEGORY_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "InventoryItemCategory":
        if self.category_type == "EQUIPMENT" and not self.is_equipment:
            object.__setattr__(self, "is_equipment", True)
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="INVENTORY_CATEGORY_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        category_code: str,
        name: str,
        description: str = "",
        category_type: str = "MATERIAL",
        is_equipment: bool = False,
        supports_project_usage: bool = False,
        supports_maintenance_usage: bool = False,
        is_active: bool = True,
    ) -> "InventoryItemCategory":
        now = datetime.now(timezone.utc)
        return InventoryItemCategory(
            id=generate_id(),
            organization_id=organization_id,
            category_code=category_code,
            name=name,
            description=description,
            category_type=category_type,
            is_equipment=is_equipment,
            supports_project_usage=supports_project_usage,
            supports_maintenance_usage=supports_maintenance_usage,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            version=1,
        )


@validated_dataclass
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
    order_uom_ratio: float | None = None
    issue_uom_ratio: float | None = None
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

    @field_validator("id", "organization_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": ("Inventory item ID is required.", "INVENTORY_ITEM_ID_REQUIRED"),
            "organization_id": (
                "Organization ID is required.",
                "INVENTORY_ITEM_ORGANIZATION_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("item_code", mode="before")
    @classmethod
    def _validate_item_code(cls, value: object) -> str:
        return normalize_inventory_code(value, label="Item code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_inventory_name(value, label="Item name")

    @field_validator(
        "description",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "item_type",
        "category_code",
        "commodity_code",
        "default_reorder_policy",
        mode="before",
    )
    @classmethod
    def _normalize_upper_text_fields(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> str:
        return normalize_status(
            value,
            default_status="DRAFT",
            allowed_statuses=ITEM_STATUS_VALUES,
            label="Inventory item status",
        )

    @field_validator("stock_uom", mode="before")
    @classmethod
    def _validate_stock_uom(cls, value: object) -> str:
        return normalize_uom(value, label="Stock UOM")

    @field_validator("order_uom", "issue_uom", mode="before")
    @classmethod
    def _normalize_optional_uoms(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("order_uom_ratio", "issue_uom_ratio", mode="before")
    @classmethod
    def _validate_optional_ratios(cls, value: object, info) -> float | None:
        labels = {
            "order_uom_ratio": "Order UOM factor",
            "issue_uom_ratio": "Issue UOM factor",
        }
        return normalize_optional_nonnegative_quantity(value, label=labels[info.field_name])

    @field_validator(
        "min_qty",
        "max_qty",
        "reorder_point",
        "reorder_qty",
        mode="before",
    )
    @classmethod
    def _validate_quantities(cls, value: object, info) -> float:
        labels = {
            "min_qty": "Minimum quantity",
            "max_qty": "Maximum quantity",
            "reorder_point": "Reorder point",
            "reorder_qty": "Reorder quantity",
        }
        return normalize_nonnegative_quantity(value, label=labels[info.field_name])

    @field_validator("lead_time_days", "shelf_life_days", mode="before")
    @classmethod
    def _validate_days(cls, value: object, info) -> int | None:
        labels = {
            "lead_time_days": "Lead time days",
            "shelf_life_days": "Shelf life days",
        }
        return normalize_nonnegative_days(value, label=labels[info.field_name])

    @field_validator("preferred_party_id", mode="before")
    @classmethod
    def _normalize_optional_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Inventory item {info.field_name.replace('_', ' ')} is invalid.",
            code=f"INVENTORY_ITEM_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Inventory item version must be positive.",
            code="INVENTORY_ITEM_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "StockItem":
        order_uom = self.order_uom or self.stock_uom
        issue_uom = self.issue_uom or self.stock_uom
        object.__setattr__(self, "order_uom", order_uom)
        object.__setattr__(self, "issue_uom", issue_uom)

        if order_uom == self.stock_uom:
            object.__setattr__(self, "order_uom_ratio", 1.0)
        elif self.order_uom_ratio in (None, 0):
            raise ValidationError(
                "Order UOM factor is required when order UOM differs from stock UOM.",
                code="INVENTORY_UOM_FACTOR_REQUIRED",
            )

        if issue_uom == self.stock_uom:
            object.__setattr__(self, "issue_uom_ratio", 1.0)
        elif self.issue_uom_ratio in (None, 0):
            raise ValidationError(
                "Issue UOM factor is required when issue UOM differs from stock UOM.",
                code="INVENTORY_UOM_FACTOR_REQUIRED",
            )

        if (
            self.order_uom == self.issue_uom
            and self.order_uom_ratio is not None
            and self.issue_uom_ratio is not None
            and abs(float(self.order_uom_ratio) - float(self.issue_uom_ratio)) > 1e-9
        ):
            raise ValidationError(
                "Order and issue UOM factors must match when they use the same UOM code.",
                code="INVENTORY_UOM_FACTOR_CONFLICT",
            )

        if self.max_qty and self.max_qty < self.min_qty:
            raise ValidationError(
                "Maximum quantity cannot be less than minimum quantity.",
                code="INVENTORY_REORDER_RANGE_INVALID",
            )
        if self.max_qty and self.reorder_point > self.max_qty:
            raise ValidationError(
                "Reorder point cannot exceed maximum quantity.",
                code="INVENTORY_REORDER_POINT_INVALID",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="INVENTORY_ITEM_UPDATED_RANGE_INVALID",
            )
        object.__setattr__(self, "is_active", self.status == "ACTIVE")
        return self

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
        order_uom: str | None = "",
        issue_uom: str | None = "",
        order_uom_ratio: float | int | None = None,
        issue_uom_ratio: float | int | None = None,
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
        lead_time_days: int | str | None = None,
        is_lot_tracked: bool = False,
        is_serial_tracked: bool = False,
        shelf_life_days: int | str | None = None,
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
            order_uom=order_uom or "",
            issue_uom=issue_uom or "",
            order_uom_ratio=order_uom_ratio,
            issue_uom_ratio=issue_uom_ratio,
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
