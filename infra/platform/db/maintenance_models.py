from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.modules.maintenance_management.domain import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
)
from infra.platform.db.base import Base


class MaintenanceLocationORM(Base):
    __tablename__ = "maintenance_locations"
    __table_args__ = (
        UniqueConstraint("organization_id", "location_code", name="ux_maintenance_locations_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sites.id"),
        nullable=False,
    )
    location_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_location_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    criticality: Mapped[MaintenanceCriticality] = mapped_column(
        SAEnum(MaintenanceCriticality),
        nullable=False,
        default=MaintenanceCriticality.MEDIUM,
        server_default=MaintenanceCriticality.MEDIUM.value,
    )
    status: Mapped[MaintenanceLifecycleStatus] = mapped_column(
        SAEnum(MaintenanceLifecycleStatus),
        nullable=False,
        default=MaintenanceLifecycleStatus.ACTIVE,
        server_default=MaintenanceLifecycleStatus.ACTIVE.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceSystemORM(Base):
    __tablename__ = "maintenance_systems"
    __table_args__ = (
        UniqueConstraint("organization_id", "system_code", name="ux_maintenance_systems_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sites.id"),
        nullable=False,
    )
    system_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    location_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_system_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_systems.id", ondelete="SET NULL"),
        nullable=True,
    )
    system_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    criticality: Mapped[MaintenanceCriticality] = mapped_column(
        SAEnum(MaintenanceCriticality),
        nullable=False,
        default=MaintenanceCriticality.MEDIUM,
        server_default=MaintenanceCriticality.MEDIUM.value,
    )
    status: Mapped[MaintenanceLifecycleStatus] = mapped_column(
        SAEnum(MaintenanceLifecycleStatus),
        nullable=False,
        default=MaintenanceLifecycleStatus.ACTIVE,
        server_default=MaintenanceLifecycleStatus.ACTIVE.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceAssetORM(Base):
    __tablename__ = "maintenance_assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "asset_code", name="ux_maintenance_assets_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sites.id"),
        nullable=False,
    )
    location_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_locations.id"),
        nullable=False,
    )
    asset_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    system_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_systems.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_asset_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    asset_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[MaintenanceLifecycleStatus] = mapped_column(
        SAEnum(MaintenanceLifecycleStatus),
        nullable=False,
        default=MaintenanceLifecycleStatus.ACTIVE,
        server_default=MaintenanceLifecycleStatus.ACTIVE.value,
    )
    criticality: Mapped[MaintenanceCriticality] = mapped_column(
        SAEnum(MaintenanceCriticality),
        nullable=False,
        default=MaintenanceCriticality.MEDIUM,
        server_default=MaintenanceCriticality.MEDIUM.value,
    )
    manufacturer_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    supplier_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    install_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    commission_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warranty_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warranty_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_life_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    replacement_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    maintenance_strategy: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    service_level: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    requires_shutdown_for_major_work: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceAssetComponentORM(Base):
    __tablename__ = "maintenance_asset_components"
    __table_args__ = (
        UniqueConstraint("organization_id", "component_code", name="ux_maintenance_components_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_component_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_asset_components.id", ondelete="SET NULL"),
        nullable=True,
    )
    component_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[MaintenanceLifecycleStatus] = mapped_column(
        SAEnum(MaintenanceLifecycleStatus),
        nullable=False,
        default=MaintenanceLifecycleStatus.ACTIVE,
        server_default=MaintenanceLifecycleStatus.ACTIVE.value,
    )
    manufacturer_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    supplier_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    manufacturer_part_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    supplier_part_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    model_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    install_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warranty_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_life_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expected_life_cycles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_critical_component: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_maintenance_locations_org", MaintenanceLocationORM.organization_id)
Index("idx_maintenance_locations_site", MaintenanceLocationORM.site_id)
Index("idx_maintenance_locations_parent", MaintenanceLocationORM.parent_location_id)
Index("idx_maintenance_locations_active", MaintenanceLocationORM.is_active)
Index("idx_maintenance_systems_org", MaintenanceSystemORM.organization_id)
Index("idx_maintenance_systems_site", MaintenanceSystemORM.site_id)
Index("idx_maintenance_systems_location", MaintenanceSystemORM.location_id)
Index("idx_maintenance_systems_parent", MaintenanceSystemORM.parent_system_id)
Index("idx_maintenance_systems_active", MaintenanceSystemORM.is_active)
Index("idx_maintenance_assets_org", MaintenanceAssetORM.organization_id)
Index("idx_maintenance_assets_site", MaintenanceAssetORM.site_id)
Index("idx_maintenance_assets_location", MaintenanceAssetORM.location_id)
Index("idx_maintenance_assets_system", MaintenanceAssetORM.system_id)
Index("idx_maintenance_assets_parent", MaintenanceAssetORM.parent_asset_id)
Index("idx_maintenance_assets_manufacturer", MaintenanceAssetORM.manufacturer_party_id)
Index("idx_maintenance_assets_supplier", MaintenanceAssetORM.supplier_party_id)
Index("idx_maintenance_assets_active", MaintenanceAssetORM.is_active)
Index("idx_maintenance_components_org", MaintenanceAssetComponentORM.organization_id)
Index("idx_maintenance_components_asset", MaintenanceAssetComponentORM.asset_id)
Index("idx_maintenance_components_parent", MaintenanceAssetComponentORM.parent_component_id)
Index("idx_maintenance_components_manufacturer", MaintenanceAssetComponentORM.manufacturer_party_id)
Index("idx_maintenance_components_supplier", MaintenanceAssetComponentORM.supplier_party_id)
Index("idx_maintenance_components_active", MaintenanceAssetComponentORM.is_active)


__all__ = [
    "MaintenanceAssetORM",
    "MaintenanceAssetComponentORM",
    "MaintenanceLocationORM",
    "MaintenanceSystemORM",
]
