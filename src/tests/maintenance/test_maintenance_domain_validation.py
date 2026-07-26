from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.core.modules.maintenance.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
    MaintenanceLocation,
    MaintenanceSystem,
)
from src.core.platform.common.exceptions import ValidationError


def test_maintenance_location_and_system_dtos_normalize_fields() -> None:
    location = MaintenanceLocation.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        location_code="  area-1  ",
        name="  Area 1  ",
        description="  Main production area  ",
        parent_location_id="  parent-1  ",
        location_type="  process  ",
        criticality="high",
        is_active=False,
        notes="  Monitored daily  ",
    )

    assert location.organization_id == "org-1"
    assert location.site_id == "site-1"
    assert location.location_code == "AREA-1"
    assert location.name == "Area 1"
    assert location.description == "Main production area"
    assert location.parent_location_id == "parent-1"
    assert location.location_type == "process"
    assert location.criticality is MaintenanceCriticality.HIGH
    assert location.status is MaintenanceLifecycleStatus.INACTIVE
    assert location.notes == "Monitored daily"

    location.version = "2"
    assert location.version == 2

    system = MaintenanceSystem.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        system_code="  cw-001  ",
        name="  Cooling Water  ",
        location_id="  location-1  ",
        parent_system_id="  parent-system  ",
        system_type="  utility  ",
        status="active",
        notes="  Core loop  ",
    )

    assert system.system_code == "CW-001"
    assert system.name == "Cooling Water"
    assert system.location_id == "location-1"
    assert system.parent_system_id == "parent-system"
    assert system.system_type == "utility"
    assert system.status is MaintenanceLifecycleStatus.ACTIVE
    assert system.notes == "Core loop"


def test_maintenance_asset_dto_normalizes_fields_and_validates_ranges() -> None:
    asset = MaintenanceAsset.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        location_id="  loc-1  ",
        asset_code="  pump-001  ",
        name="  Boiler Feed Pump  ",
        system_id="  sys-1  ",
        description="  Primary duty pump  ",
        parent_asset_id="  asset-parent  ",
        asset_type="  pump  ",
        asset_category="  rotating  ",
        criticality="critical",
        manufacturer_party_id="  party-mfg  ",
        supplier_party_id="  party-sup  ",
        model_number="  mdl-22  ",
        serial_number="  sn-900  ",
        barcode="  bc-500  ",
        install_date="2025-01-10",
        commission_date="2025-01-15",
        warranty_start=date(2025, 1, 15),
        warranty_end="2027-01-15",
        expected_life_years="12",
        replacement_cost="12500.50",
        maintenance_strategy="  cbm  ",
        service_level="  critical  ",
        requires_shutdown_for_major_work=True,
        notes="  Inspect monthly  ",
    )

    assert asset.organization_id == "org-1"
    assert asset.asset_code == "PUMP-001"
    assert asset.name == "Boiler Feed Pump"
    assert asset.system_id == "sys-1"
    assert asset.description == "Primary duty pump"
    assert asset.parent_asset_id == "asset-parent"
    assert asset.asset_type == "pump"
    assert asset.asset_category == "ROTATING"
    assert asset.criticality is MaintenanceCriticality.CRITICAL
    assert asset.manufacturer_party_id == "party-mfg"
    assert asset.supplier_party_id == "party-sup"
    assert asset.model_number == "mdl-22"
    assert asset.serial_number == "sn-900"
    assert asset.barcode == "bc-500"
    assert asset.install_date == date(2025, 1, 10)
    assert asset.commission_date == date(2025, 1, 15)
    assert asset.warranty_end == date(2027, 1, 15)
    assert asset.expected_life_years == 12
    assert asset.replacement_cost == Decimal("12500.50")
    assert asset.maintenance_strategy == "cbm"
    assert asset.service_level == "critical"
    assert asset.notes == "Inspect monthly"

    asset.updated_at = datetime(2026, 7, 26, 8, 30, 0)
    asset.version = "2"

    assert asset.updated_at == datetime(2026, 7, 26, 8, 30, 0, tzinfo=timezone.utc)
    assert asset.version == 2

    with pytest.raises(ValidationError) as exc_date_sequence:
        MaintenanceAsset.create(
            organization_id="org-1",
            site_id="site-1",
            location_id="loc-1",
            asset_code="PUMP-002",
            name="Bad Commission Window",
            install_date="2025-02-10",
            commission_date="2025-02-01",
        )
    assert exc_date_sequence.value.code == "MAINTENANCE_ASSET_DATE_SEQUENCE_INVALID"

    with pytest.raises(ValidationError) as exc_warranty_range:
        MaintenanceAsset.create(
            organization_id="org-1",
            site_id="site-1",
            location_id="loc-1",
            asset_code="PUMP-003",
            name="Bad Warranty Window",
            warranty_start="2025-04-10",
            warranty_end="2025-04-01",
        )
    assert exc_warranty_range.value.code == "MAINTENANCE_ASSET_WARRANTY_RANGE_INVALID"


def test_maintenance_component_dto_normalizes_fields_and_validates_ranges() -> None:
    component = MaintenanceAssetComponent.create(
        organization_id="  org-1  ",
        asset_id="  asset-1  ",
        component_code="  seal-001  ",
        name="  Seal Cartridge  ",
        description="  Dual mechanical seal  ",
        parent_component_id="  parent-1  ",
        component_type="  seal  ",
        supplier_party_id="  supplier-1  ",
        manufacturer_part_number="  mpn-1  ",
        supplier_part_number="  spn-1  ",
        model_number="  mdl-1  ",
        serial_number="  sn-1  ",
        install_date="2025-03-01",
        warranty_end="2026-03-01",
        expected_life_hours="12000",
        expected_life_cycles="5000",
        is_critical_component=True,
        notes="  Spare kept onsite  ",
    )

    assert component.organization_id == "org-1"
    assert component.asset_id == "asset-1"
    assert component.component_code == "SEAL-001"
    assert component.name == "Seal Cartridge"
    assert component.description == "Dual mechanical seal"
    assert component.parent_component_id == "parent-1"
    assert component.component_type == "SEAL"
    assert component.supplier_party_id == "supplier-1"
    assert component.manufacturer_part_number == "mpn-1"
    assert component.supplier_part_number == "spn-1"
    assert component.expected_life_hours == 12000
    assert component.expected_life_cycles == 5000
    assert component.is_critical_component is True
    assert component.notes == "Spare kept onsite"

    component.status = "inactive"
    component.version = "2"

    assert component.status is MaintenanceLifecycleStatus.INACTIVE
    assert component.version == 2

    with pytest.raises(ValidationError) as exc_warranty:
        MaintenanceAssetComponent.create(
            organization_id="org-1",
            asset_id="asset-1",
            component_code="SEAL-002",
            name="Bad Seal",
            install_date="2025-03-10",
            warranty_end="2025-03-01",
        )
    assert exc_warranty.value.code == "MAINTENANCE_COMPONENT_WARRANTY_RANGE_INVALID"

    with pytest.raises(ValidationError) as exc_version:
        component.version = 0
    assert exc_version.value.code == "MAINTENANCE_COMPONENT_VERSION_INVALID"
