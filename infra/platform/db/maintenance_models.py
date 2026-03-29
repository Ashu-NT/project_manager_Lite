from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
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


Index("idx_maintenance_locations_org", MaintenanceLocationORM.organization_id)
Index("idx_maintenance_locations_site", MaintenanceLocationORM.site_id)
Index("idx_maintenance_locations_parent", MaintenanceLocationORM.parent_location_id)
Index("idx_maintenance_locations_active", MaintenanceLocationORM.is_active)
Index("idx_maintenance_systems_org", MaintenanceSystemORM.organization_id)
Index("idx_maintenance_systems_site", MaintenanceSystemORM.site_id)
Index("idx_maintenance_systems_location", MaintenanceSystemORM.location_id)
Index("idx_maintenance_systems_parent", MaintenanceSystemORM.parent_system_id)
Index("idx_maintenance_systems_active", MaintenanceSystemORM.is_active)


__all__ = [
    "MaintenanceLocationORM",
    "MaintenanceSystemORM",
]
