from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.maintenance.domain import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
)


@dataclass(frozen=True)
class MaintenanceLifecycleStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceCriticalityDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceLocationDesktopDto:
    id: str
    site_id: str
    site_label: str
    location_code: str
    name: str
    description: str
    parent_location_id: str | None
    parent_location_label: str
    location_type: str
    criticality: str
    criticality_label: str
    status: str
    status_label: str
    is_active: bool
    active_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class MaintenanceSystemDesktopDto:
    id: str
    site_id: str
    site_label: str
    location_id: str | None
    location_label: str
    system_code: str
    name: str
    description: str
    parent_system_id: str | None
    parent_system_label: str
    system_type: str
    criticality: str
    criticality_label: str
    status: str
    status_label: str
    is_active: bool
    active_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class MaintenanceAssetDesktopDto:
    id: str
    site_id: str
    site_label: str
    location_id: str
    location_label: str
    system_id: str | None
    system_label: str
    parent_asset_id: str | None
    parent_asset_label: str
    asset_code: str
    name: str
    description: str
    asset_type: str
    asset_category: str
    criticality: str
    criticality_label: str
    status: str
    status_label: str
    manufacturer_party_id: str | None
    manufacturer_party_label: str
    supplier_party_id: str | None
    supplier_party_label: str
    model_number: str
    serial_number: str
    barcode: str
    install_date: str
    commission_date: str
    warranty_start: str
    warranty_end: str
    expected_life_years: int | None
    replacement_cost: float | None
    maintenance_strategy: str
    service_level: str
    requires_shutdown_for_major_work: bool
    is_active: bool
    active_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class MaintenanceComponentDesktopDto:
    id: str
    asset_id: str
    asset_label: str
    component_code: str
    name: str
    description: str
    parent_component_id: str | None
    parent_component_label: str
    component_type: str
    status: str
    status_label: str
    manufacturer_party_id: str | None
    manufacturer_party_label: str
    supplier_party_id: str | None
    supplier_party_label: str
    manufacturer_part_number: str
    supplier_part_number: str
    model_number: str
    serial_number: str
    install_date: str
    warranty_end: str
    expected_life_hours: int | None
    expected_life_cycles: int | None
    is_critical_component: bool
    is_active: bool
    active_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class MaintenanceLocationCreateCommand:
    site_id: str
    location_code: str = ""
    name: str = ""
    description: str = ""
    parent_location_id: str | None = None
    location_type: str = ""
    criticality: str = MaintenanceCriticality.MEDIUM.value
    status: str = MaintenanceLifecycleStatus.ACTIVE.value
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class MaintenanceLocationUpdateCommand:
    location_id: str
    site_id: str | None = None
    location_code: str | None = None
    name: str | None = None
    description: str | None = None
    parent_location_id: str | None = None
    location_type: str | None = None
    criticality: str | None = None
    status: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class MaintenanceSystemCreateCommand:
    site_id: str
    system_code: str = ""
    name: str = ""
    location_id: str | None = None
    description: str = ""
    parent_system_id: str | None = None
    system_type: str = ""
    criticality: str = MaintenanceCriticality.MEDIUM.value
    status: str = MaintenanceLifecycleStatus.ACTIVE.value
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class MaintenanceSystemUpdateCommand:
    system_id: str
    site_id: str | None = None
    system_code: str | None = None
    name: str | None = None
    location_id: str | None = None
    description: str | None = None
    parent_system_id: str | None = None
    system_type: str | None = None
    criticality: str | None = None
    status: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class MaintenanceAssetCreateCommand:
    site_id: str
    location_id: str
    asset_code: str = ""
    name: str = ""
    system_id: str | None = None
    description: str = ""
    parent_asset_id: str | None = None
    asset_type: str = ""
    asset_category: str = ""
    criticality: str = MaintenanceCriticality.MEDIUM.value
    status: str = MaintenanceLifecycleStatus.ACTIVE.value
    manufacturer_party_id: str | None = None
    supplier_party_id: str | None = None
    model_number: str = ""
    serial_number: str = ""
    barcode: str = ""
    install_date: str = ""
    commission_date: str = ""
    warranty_start: str = ""
    warranty_end: str = ""
    expected_life_years: int | None = None
    replacement_cost: float | None = None
    maintenance_strategy: str = ""
    service_level: str = ""
    requires_shutdown_for_major_work: bool = False
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class MaintenanceAssetUpdateCommand:
    asset_id: str
    site_id: str | None = None
    location_id: str | None = None
    asset_code: str | None = None
    name: str | None = None
    system_id: str | None = None
    description: str | None = None
    parent_asset_id: str | None = None
    asset_type: str | None = None
    asset_category: str | None = None
    criticality: str | None = None
    status: str | None = None
    manufacturer_party_id: str | None = None
    supplier_party_id: str | None = None
    model_number: str | None = None
    serial_number: str | None = None
    barcode: str | None = None
    install_date: str | None = None
    commission_date: str | None = None
    warranty_start: str | None = None
    warranty_end: str | None = None
    expected_life_years: int | None = None
    replacement_cost: float | None = None
    maintenance_strategy: str | None = None
    service_level: str | None = None
    requires_shutdown_for_major_work: bool | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class MaintenanceComponentCreateCommand:
    asset_id: str
    component_code: str = ""
    name: str = ""
    description: str = ""
    parent_component_id: str | None = None
    component_type: str = ""
    status: str = MaintenanceLifecycleStatus.ACTIVE.value
    manufacturer_party_id: str | None = None
    supplier_party_id: str | None = None
    manufacturer_part_number: str = ""
    supplier_part_number: str = ""
    model_number: str = ""
    serial_number: str = ""
    install_date: str = ""
    warranty_end: str = ""
    expected_life_hours: int | None = None
    expected_life_cycles: int | None = None
    is_critical_component: bool = False
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class MaintenanceComponentUpdateCommand:
    component_id: str
    asset_id: str | None = None
    component_code: str | None = None
    name: str | None = None
    description: str | None = None
    parent_component_id: str | None = None
    component_type: str | None = None
    status: str | None = None
    manufacturer_party_id: str | None = None
    supplier_party_id: str | None = None
    manufacturer_part_number: str | None = None
    supplier_part_number: str | None = None
    model_number: str | None = None
    serial_number: str | None = None
    install_date: str | None = None
    warranty_end: str | None = None
    expected_life_hours: int | None = None
    expected_life_cycles: int | None = None
    is_critical_component: bool | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None


__all__ = [
    "MaintenanceAssetCreateCommand",
    "MaintenanceAssetDesktopDto",
    "MaintenanceAssetUpdateCommand",
    "MaintenanceComponentCreateCommand",
    "MaintenanceComponentDesktopDto",
    "MaintenanceComponentUpdateCommand",
    "MaintenanceCriticalityDescriptor",
    "MaintenanceLifecycleStatusDescriptor",
    "MaintenanceLocationCreateCommand",
    "MaintenanceLocationDesktopDto",
    "MaintenanceLocationUpdateCommand",
    "MaintenanceSystemCreateCommand",
    "MaintenanceSystemDesktopDto",
    "MaintenanceSystemUpdateCommand",
]
