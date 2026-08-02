from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import field_validator, model_validator

from src.core.modules.maintenance.domain._validation import (
    normalize_criticality,
    normalize_lifecycle_status,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_date,
    normalize_optional_datetime,
    normalize_optional_decimal,
    normalize_optional_identifier,
    normalize_optional_non_negative_int,
    normalize_optional_text,
    normalize_optional_upper_text,
    normalize_positive_int,
    normalize_required_text,
)
from src.core.modules.maintenance.domain.enums import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass
class MaintenanceAsset:
    id: str
    organization_id: str
    site_id: str
    location_id: str
    asset_code: str
    name: str
    system_id: str | None = None
    description: str = ""
    parent_asset_id: str | None = None
    asset_type: str = ""
    asset_category: str = ""
    status: MaintenanceLifecycleStatus | None = None
    criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM
    manufacturer_party_id: str | None = None
    supplier_party_id: str | None = None
    model_number: str = ""
    serial_number: str = ""
    barcode: str = ""
    install_date: date | None = None
    commission_date: date | None = None
    warranty_start: date | None = None
    warranty_end: date | None = None
    expected_life_years: int | None = None
    replacement_cost: Decimal | None = None
    maintenance_strategy: str = ""
    service_level: str = ""
    requires_shutdown_for_major_work: bool = False
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @field_validator(
        "id",
        "organization_id",
        "site_id",
        "location_id",
        mode="before",
    )
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": ("Maintenance asset ID is required.", "MAINTENANCE_ASSET_ID_REQUIRED"),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_ASSET_ORGANIZATION_REQUIRED",
            ),
            "site_id": ("Site ID is required.", "MAINTENANCE_ASSET_SITE_REQUIRED"),
            "location_id": (
                "Location ID is required.",
                "MAINTENANCE_ASSET_LOCATION_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("asset_code", mode="before")
    @classmethod
    def _validate_asset_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Asset code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Asset name")

    @field_validator(
        "system_id",
        "parent_asset_id",
        "manufacturer_party_id",
        "supplier_party_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator(
        "description",
        "asset_type",
        "model_number",
        "serial_number",
        "barcode",
        "maintenance_strategy",
        "service_level",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("asset_category", mode="before")
    @classmethod
    def _normalize_asset_category(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status_input(
        cls,
        value: object,
    ) -> MaintenanceLifecycleStatus | None:
        if value in (None, ""):
            return None
        return normalize_lifecycle_status(value)

    @field_validator("criticality", mode="before")
    @classmethod
    def _validate_criticality(cls, value: object) -> MaintenanceCriticality:
        return normalize_criticality(value)

    @field_validator(
        "install_date",
        "commission_date",
        "warranty_start",
        "warranty_end",
        mode="before",
    )
    @classmethod
    def _validate_dates(cls, value: object, info) -> date | None:
        labels = {
            "install_date": "Install date",
            "commission_date": "Commission date",
            "warranty_start": "Warranty start",
            "warranty_end": "Warranty end",
        }
        return normalize_optional_date(value, label=labels[info.field_name])

    @field_validator("expected_life_years", mode="before")
    @classmethod
    def _validate_expected_life_years(cls, value: object) -> int | None:
        return normalize_optional_non_negative_int(value, label="Expected life years")

    @field_validator("replacement_cost", mode="before")
    @classmethod
    def _validate_replacement_cost(cls, value: object) -> Decimal | None:
        return normalize_optional_decimal(value, label="Replacement cost")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance asset {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_ASSET_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance asset version must be positive.",
            code="MAINTENANCE_ASSET_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceAsset":
        object.__setattr__(
            self,
            "status",
            normalize_lifecycle_status(self.status, is_active=self.is_active),
        )
        if (
            self.install_date is not None
            and self.commission_date is not None
            and self.commission_date < self.install_date
        ):
            raise ValidationError(
                "Commission date cannot be earlier than install date.",
                code="MAINTENANCE_ASSET_DATE_SEQUENCE_INVALID",
            )
        if (
            self.warranty_start is not None
            and self.warranty_end is not None
            and self.warranty_end < self.warranty_start
        ):
            raise ValidationError(
                "Warranty end cannot be earlier than warranty start.",
                code="MAINTENANCE_ASSET_WARRANTY_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        location_id: str,
        asset_code: str,
        name: str,
        system_id: str | None = None,
        description: str = "",
        parent_asset_id: str | None = None,
        asset_type: str = "",
        asset_category: str = "",
        status: MaintenanceLifecycleStatus | str | None = None,
        criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM,
        manufacturer_party_id: str | None = None,
        supplier_party_id: str | None = None,
        model_number: str = "",
        serial_number: str = "",
        barcode: str = "",
        install_date: date | None = None,
        commission_date: date | None = None,
        warranty_start: date | None = None,
        warranty_end: date | None = None,
        expected_life_years: int | None = None,
        replacement_cost: Decimal | None = None,
        maintenance_strategy: str = "",
        service_level: str = "",
        requires_shutdown_for_major_work: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceAsset":
        now = datetime.now(timezone.utc)
        return MaintenanceAsset(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            location_id=location_id,
            asset_code=asset_code,
            name=name,
            system_id=system_id,
            description=description,
            parent_asset_id=parent_asset_id,
            asset_type=asset_type,
            asset_category=asset_category,
            status=status,
            criticality=criticality,
            manufacturer_party_id=manufacturer_party_id,
            supplier_party_id=supplier_party_id,
            model_number=model_number,
            serial_number=serial_number,
            barcode=barcode,
            install_date=install_date,
            commission_date=commission_date,
            warranty_start=warranty_start,
            warranty_end=warranty_end,
            expected_life_years=expected_life_years,
            replacement_cost=replacement_cost,
            maintenance_strategy=maintenance_strategy,
            service_level=service_level,
            requires_shutdown_for_major_work=requires_shutdown_for_major_work,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


@validated_dataclass
class MaintenanceAssetComponent:
    id: str
    organization_id: str
    asset_id: str
    component_code: str
    name: str
    description: str = ""
    parent_component_id: str | None = None
    component_type: str = ""
    status: MaintenanceLifecycleStatus | None = None
    manufacturer_party_id: str | None = None
    supplier_party_id: str | None = None
    manufacturer_part_number: str = ""
    supplier_part_number: str = ""
    model_number: str = ""
    serial_number: str = ""
    install_date: date | None = None
    warranty_end: date | None = None
    expected_life_hours: int | None = None
    expected_life_cycles: int | None = None
    is_critical_component: bool = False
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @field_validator("id", "organization_id", "asset_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance asset component ID is required.",
                "MAINTENANCE_COMPONENT_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_COMPONENT_ORGANIZATION_REQUIRED",
            ),
            "asset_id": (
                "Asset ID is required.",
                "MAINTENANCE_COMPONENT_ASSET_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("component_code", mode="before")
    @classmethod
    def _validate_component_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Component code")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Component name")

    @field_validator(
        "parent_component_id",
        "manufacturer_party_id",
        "supplier_party_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator(
        "description",
        "manufacturer_part_number",
        "supplier_part_number",
        "model_number",
        "serial_number",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("component_type", mode="before")
    @classmethod
    def _normalize_component_type(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status_input(
        cls,
        value: object,
    ) -> MaintenanceLifecycleStatus | None:
        if value in (None, ""):
            return None
        return normalize_lifecycle_status(value)

    @field_validator("install_date", "warranty_end", mode="before")
    @classmethod
    def _validate_dates(cls, value: object, info) -> date | None:
        labels = {
            "install_date": "Install date",
            "warranty_end": "Warranty end",
        }
        return normalize_optional_date(value, label=labels[info.field_name])

    @field_validator("expected_life_hours", mode="before")
    @classmethod
    def _validate_expected_life_hours(cls, value: object) -> int | None:
        return normalize_optional_non_negative_int(value, label="Expected life hours")

    @field_validator("expected_life_cycles", mode="before")
    @classmethod
    def _validate_expected_life_cycles(cls, value: object) -> int | None:
        return normalize_optional_non_negative_int(value, label="Expected life cycles")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance asset component {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_COMPONENT_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance asset component version must be positive.",
            code="MAINTENANCE_COMPONENT_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceAssetComponent":
        object.__setattr__(
            self,
            "status",
            normalize_lifecycle_status(self.status, is_active=self.is_active),
        )
        if (
            self.install_date is not None
            and self.warranty_end is not None
            and self.warranty_end < self.install_date
        ):
            raise ValidationError(
                "Warranty end cannot be earlier than install date.",
                code="MAINTENANCE_COMPONENT_WARRANTY_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        asset_id: str,
        component_code: str,
        name: str,
        description: str = "",
        parent_component_id: str | None = None,
        component_type: str = "",
        status: MaintenanceLifecycleStatus | str | None = None,
        manufacturer_party_id: str | None = None,
        supplier_party_id: str | None = None,
        manufacturer_part_number: str = "",
        supplier_part_number: str = "",
        model_number: str = "",
        serial_number: str = "",
        install_date: date | None = None,
        warranty_end: date | None = None,
        expected_life_hours: int | None = None,
        expected_life_cycles: int | None = None,
        is_critical_component: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceAssetComponent":
        now = datetime.now(timezone.utc)
        return MaintenanceAssetComponent(
            id=generate_id(),
            organization_id=organization_id,
            asset_id=asset_id,
            component_code=component_code,
            name=name,
            description=description,
            parent_component_id=parent_component_id,
            component_type=component_type,
            status=status,
            manufacturer_party_id=manufacturer_party_id,
            supplier_party_id=supplier_party_id,
            manufacturer_part_number=manufacturer_part_number,
            supplier_part_number=supplier_part_number,
            model_number=model_number,
            serial_number=serial_number,
            install_date=install_date,
            warranty_end=warranty_end,
            expected_life_hours=expected_life_hours,
            expected_life_cycles=expected_life_cycles,
            is_critical_component=is_critical_component,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


__all__ = [
    "MaintenanceAsset",
    "MaintenanceAssetComponent",
]
