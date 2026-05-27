from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.maintenance.api.desktop._support import (
    clean_id,
    clean_text,
    code_name_label,
    enum_value,
    party_contact_label,
)


@dataclass(frozen=True)
class MaintenanceSiteOptionDescriptor:
    value: str
    label: str
    name: str
    city: str
    country: str
    is_active: bool


@dataclass(frozen=True)
class MaintenanceBusinessPartyOptionDescriptor:
    value: str
    label: str
    party_type: str
    contact: str
    city: str
    country: str
    is_active: bool


@dataclass(frozen=True)
class MaintenanceLocationOptionDescriptor:
    value: str
    label: str
    site_id: str
    parent_location_id: str | None
    is_active: bool


@dataclass(frozen=True)
class MaintenanceSystemOptionDescriptor:
    value: str
    label: str
    site_id: str
    location_id: str | None
    parent_system_id: str | None
    is_active: bool


@dataclass(frozen=True)
class MaintenanceAssetOptionDescriptor:
    value: str
    label: str
    site_id: str
    location_id: str
    system_id: str | None
    parent_asset_id: str | None
    is_active: bool


@dataclass(frozen=True)
class MaintenanceComponentOptionDescriptor:
    value: str
    label: str
    asset_id: str
    parent_component_id: str | None
    is_active: bool


@dataclass(frozen=True)
class MaintenanceEmployeeOptionDescriptor:
    value: str
    label: str
    employee_code: str
    full_name: str
    site_id: str | None
    department_id: str | None
    title: str
    is_active: bool


def serialize_site_option(row) -> MaintenanceSiteOptionDescriptor:
    return MaintenanceSiteOptionDescriptor(
        value=row.id,
        label=code_name_label(getattr(row, "site_code", ""), getattr(row, "name", "")),
        name=clean_text(getattr(row, "name", "")),
        city=clean_text(getattr(row, "city", "")),
        country=clean_text(getattr(row, "country", "")),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_business_party_option(row) -> MaintenanceBusinessPartyOptionDescriptor:
    return MaintenanceBusinessPartyOptionDescriptor(
        value=row.id,
        label=code_name_label(getattr(row, "party_code", ""), getattr(row, "party_name", "")),
        party_type=enum_value(getattr(row, "party_type", "")),
        contact=party_contact_label(row),
        city=clean_text(getattr(row, "city", "")),
        country=clean_text(getattr(row, "country", "")),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_location_option(row) -> MaintenanceLocationOptionDescriptor:
    return MaintenanceLocationOptionDescriptor(
        value=row.id,
        label=code_name_label(getattr(row, "location_code", ""), getattr(row, "name", "")),
        site_id=row.site_id,
        parent_location_id=clean_id(getattr(row, "parent_location_id", None)),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_system_option(row) -> MaintenanceSystemOptionDescriptor:
    return MaintenanceSystemOptionDescriptor(
        value=row.id,
        label=code_name_label(getattr(row, "system_code", ""), getattr(row, "name", "")),
        site_id=row.site_id,
        location_id=clean_id(getattr(row, "location_id", None)),
        parent_system_id=clean_id(getattr(row, "parent_system_id", None)),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_asset_option(row) -> MaintenanceAssetOptionDescriptor:
    return MaintenanceAssetOptionDescriptor(
        value=row.id,
        label=code_name_label(getattr(row, "asset_code", ""), getattr(row, "name", "")),
        site_id=row.site_id,
        location_id=row.location_id,
        system_id=clean_id(getattr(row, "system_id", None)),
        parent_asset_id=clean_id(getattr(row, "parent_asset_id", None)),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_component_option(row) -> MaintenanceComponentOptionDescriptor:
    return MaintenanceComponentOptionDescriptor(
        value=row.id,
        label=code_name_label(getattr(row, "component_code", ""), getattr(row, "name", "")),
        asset_id=row.asset_id,
        parent_component_id=clean_id(getattr(row, "parent_component_id", None)),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_employee_option(row) -> MaintenanceEmployeeOptionDescriptor:
    return MaintenanceEmployeeOptionDescriptor(
        value=row.id,
        label=code_name_label(getattr(row, "employee_code", ""), getattr(row, "full_name", "")),
        employee_code=clean_text(getattr(row, "employee_code", "")),
        full_name=clean_text(getattr(row, "full_name", "")),
        site_id=clean_id(getattr(row, "site_id", None)),
        department_id=clean_id(getattr(row, "department_id", None)),
        title=clean_text(getattr(row, "title", "")),
        is_active=bool(getattr(row, "is_active", True)),
    )


__all__ = [
    "MaintenanceAssetOptionDescriptor",
    "MaintenanceBusinessPartyOptionDescriptor",
    "MaintenanceComponentOptionDescriptor",
    "MaintenanceEmployeeOptionDescriptor",
    "MaintenanceLocationOptionDescriptor",
    "MaintenanceSiteOptionDescriptor",
    "MaintenanceSystemOptionDescriptor",
    "serialize_asset_option",
    "serialize_business_party_option",
    "serialize_component_option",
    "serialize_employee_option",
    "serialize_location_option",
    "serialize_site_option",
    "serialize_system_option",
]
