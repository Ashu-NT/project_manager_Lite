from __future__ import annotations

from src.core.modules.maintenance.api.desktop._support import (
    clean_id,
    clean_text,
    code_name_label,
    date_text,
    enum_value,
    float_value,
    format_active_label,
    format_enum_label,
    int_value,
)
from src.core.modules.maintenance.api.desktop.assets.models import (
    MaintenanceAssetDesktopDto,
    MaintenanceComponentDesktopDto,
    MaintenanceLocationDesktopDto,
    MaintenanceSystemDesktopDto,
)


def serialize_location(
    row,
    *,
    site_lookup: dict[str, str],
    location_lookup: dict[str, str],
) -> MaintenanceLocationDesktopDto:
    criticality = enum_value(getattr(row, "criticality", ""))
    status = enum_value(getattr(row, "status", ""))
    parent_location_id = clean_id(getattr(row, "parent_location_id", None))
    return MaintenanceLocationDesktopDto(
        id=row.id,
        site_id=row.site_id,
        site_label=site_lookup.get(row.site_id, "-"),
        location_code=clean_text(getattr(row, "location_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        parent_location_id=parent_location_id,
        parent_location_label=location_lookup.get(parent_location_id or "", "-"),
        location_type=clean_text(getattr(row, "location_type", "")),
        criticality=criticality,
        criticality_label=format_enum_label(criticality),
        status=status,
        status_label=format_enum_label(status),
        is_active=bool(getattr(row, "is_active", True)),
        active_label=format_active_label(getattr(row, "is_active", True)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 0) or 0),
    )


def serialize_system(
    row,
    *,
    site_lookup: dict[str, str],
    location_lookup: dict[str, str],
    system_lookup: dict[str, str],
) -> MaintenanceSystemDesktopDto:
    criticality = enum_value(getattr(row, "criticality", ""))
    status = enum_value(getattr(row, "status", ""))
    location_id = clean_id(getattr(row, "location_id", None))
    parent_system_id = clean_id(getattr(row, "parent_system_id", None))
    return MaintenanceSystemDesktopDto(
        id=row.id,
        site_id=row.site_id,
        site_label=site_lookup.get(row.site_id, "-"),
        location_id=location_id,
        location_label=location_lookup.get(location_id or "", "-"),
        system_code=clean_text(getattr(row, "system_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        parent_system_id=parent_system_id,
        parent_system_label=system_lookup.get(parent_system_id or "", "-"),
        system_type=clean_text(getattr(row, "system_type", "")),
        criticality=criticality,
        criticality_label=format_enum_label(criticality),
        status=status,
        status_label=format_enum_label(status),
        is_active=bool(getattr(row, "is_active", True)),
        active_label=format_active_label(getattr(row, "is_active", True)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 0) or 0),
    )


def serialize_asset(
    row,
    *,
    site_lookup: dict[str, str],
    location_lookup: dict[str, str],
    system_lookup: dict[str, str],
    asset_lookup: dict[str, str],
    party_lookup: dict[str, str],
) -> MaintenanceAssetDesktopDto:
    criticality = enum_value(getattr(row, "criticality", ""))
    status = enum_value(getattr(row, "status", ""))
    system_id = clean_id(getattr(row, "system_id", None))
    parent_asset_id = clean_id(getattr(row, "parent_asset_id", None))
    manufacturer_party_id = clean_id(getattr(row, "manufacturer_party_id", None))
    supplier_party_id = clean_id(getattr(row, "supplier_party_id", None))
    return MaintenanceAssetDesktopDto(
        id=row.id,
        site_id=row.site_id,
        site_label=site_lookup.get(row.site_id, "-"),
        location_id=row.location_id,
        location_label=location_lookup.get(row.location_id, "-"),
        system_id=system_id,
        system_label=system_lookup.get(system_id or "", "-"),
        parent_asset_id=parent_asset_id,
        parent_asset_label=asset_lookup.get(parent_asset_id or "", "-"),
        asset_code=clean_text(getattr(row, "asset_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        asset_type=clean_text(getattr(row, "asset_type", "")),
        asset_category=clean_text(getattr(row, "asset_category", "")),
        criticality=criticality,
        criticality_label=format_enum_label(criticality),
        status=status,
        status_label=format_enum_label(status),
        manufacturer_party_id=manufacturer_party_id,
        manufacturer_party_label=party_lookup.get(manufacturer_party_id or "", "-"),
        supplier_party_id=supplier_party_id,
        supplier_party_label=party_lookup.get(supplier_party_id or "", "-"),
        model_number=clean_text(getattr(row, "model_number", "")),
        serial_number=clean_text(getattr(row, "serial_number", "")),
        barcode=clean_text(getattr(row, "barcode", "")),
        install_date=date_text(getattr(row, "install_date", None)),
        commission_date=date_text(getattr(row, "commission_date", None)),
        warranty_start=date_text(getattr(row, "warranty_start", None)),
        warranty_end=date_text(getattr(row, "warranty_end", None)),
        expected_life_years=int_value(getattr(row, "expected_life_years", None)),
        replacement_cost=float_value(getattr(row, "replacement_cost", None)),
        maintenance_strategy=clean_text(getattr(row, "maintenance_strategy", "")),
        service_level=clean_text(getattr(row, "service_level", "")),
        requires_shutdown_for_major_work=bool(getattr(row, "requires_shutdown_for_major_work", False)),
        is_active=bool(getattr(row, "is_active", True)),
        active_label=format_active_label(getattr(row, "is_active", True)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 0) or 0),
    )


def serialize_component(
    row,
    *,
    asset_lookup: dict[str, str],
    component_lookup: dict[str, str],
    party_lookup: dict[str, str],
) -> MaintenanceComponentDesktopDto:
    status = enum_value(getattr(row, "status", ""))
    parent_component_id = clean_id(getattr(row, "parent_component_id", None))
    manufacturer_party_id = clean_id(getattr(row, "manufacturer_party_id", None))
    supplier_party_id = clean_id(getattr(row, "supplier_party_id", None))
    return MaintenanceComponentDesktopDto(
        id=row.id,
        asset_id=row.asset_id,
        asset_label=asset_lookup.get(row.asset_id, "-"),
        component_code=clean_text(getattr(row, "component_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        parent_component_id=parent_component_id,
        parent_component_label=component_lookup.get(parent_component_id or "", "-"),
        component_type=clean_text(getattr(row, "component_type", "")),
        status=status,
        status_label=format_enum_label(status),
        manufacturer_party_id=manufacturer_party_id,
        manufacturer_party_label=party_lookup.get(manufacturer_party_id or "", "-"),
        supplier_party_id=supplier_party_id,
        supplier_party_label=party_lookup.get(supplier_party_id or "", "-"),
        manufacturer_part_number=clean_text(getattr(row, "manufacturer_part_number", "")),
        supplier_part_number=clean_text(getattr(row, "supplier_part_number", "")),
        model_number=clean_text(getattr(row, "model_number", "")),
        serial_number=clean_text(getattr(row, "serial_number", "")),
        install_date=date_text(getattr(row, "install_date", None)),
        warranty_end=date_text(getattr(row, "warranty_end", None)),
        expected_life_hours=int_value(getattr(row, "expected_life_hours", None)),
        expected_life_cycles=int_value(getattr(row, "expected_life_cycles", None)),
        is_critical_component=bool(getattr(row, "is_critical_component", False)),
        is_active=bool(getattr(row, "is_active", True)),
        active_label=format_active_label(getattr(row, "is_active", True)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 0) or 0),
    )


def location_label(row) -> str:
    return code_name_label(getattr(row, "location_code", ""), getattr(row, "name", ""))


def system_label(row) -> str:
    return code_name_label(getattr(row, "system_code", ""), getattr(row, "name", ""))


def asset_label(row) -> str:
    return code_name_label(getattr(row, "asset_code", ""), getattr(row, "name", ""))


def component_label(row) -> str:
    return code_name_label(getattr(row, "component_code", ""), getattr(row, "name", ""))


def build_lookup(rows, *, label_getter) -> dict[str, str]:
    return {
        row.id: label_getter(row)
        for row in rows
        if getattr(row, "id", None)
    }


__all__ = [
    "asset_label",
    "build_lookup",
    "component_label",
    "location_label",
    "serialize_asset",
    "serialize_component",
    "serialize_location",
    "serialize_system",
    "system_label",
]
