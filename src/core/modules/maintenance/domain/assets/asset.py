from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from src.core.modules.maintenance.domain.enums import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
)
from src.core.platform.common.ids import generate_id


@dataclass
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
    status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE
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
        status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE,
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


@dataclass
class MaintenanceAssetComponent:
    id: str
    organization_id: str
    asset_id: str
    component_code: str
    name: str
    description: str = ""
    parent_component_id: str | None = None
    component_type: str = ""
    status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE
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
        status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE,
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
