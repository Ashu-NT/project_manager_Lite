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
    MaintenancePriority,
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderType,
    MaintenanceWorkRequestSourceType,
    MaintenanceWorkRequestStatus,
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


class MaintenanceWorkRequestORM(Base):
    __tablename__ = "maintenance_work_requests"
    __table_args__ = (
        UniqueConstraint("organization_id", "work_request_code", name="ux_maintenance_work_requests_org_code"),
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
    work_request_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[MaintenanceWorkRequestSourceType] = mapped_column(
        SAEnum(MaintenanceWorkRequestSourceType),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    component_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_asset_components.id", ondelete="SET NULL"),
        nullable=True,
    )
    system_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_systems.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    priority: Mapped[MaintenancePriority] = mapped_column(
        SAEnum(MaintenancePriority),
        nullable=False,
        default=MaintenancePriority.MEDIUM,
        server_default=MaintenancePriority.MEDIUM.value,
    )
    status: Mapped[MaintenanceWorkRequestStatus] = mapped_column(
        SAEnum(MaintenanceWorkRequestStatus),
        nullable=False,
        default=MaintenanceWorkRequestStatus.NEW,
        server_default=MaintenanceWorkRequestStatus.NEW.value,
    )
    requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    requested_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_name_snapshot: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    triaged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    triaged_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    failure_symptom_code: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    safety_risk_level: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    production_impact_level: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceWorkOrderORM(Base):
    __tablename__ = "maintenance_work_orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "work_order_code", name="ux_maintenance_work_orders_org_code"),
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
    work_order_code: Mapped[str] = mapped_column(String(64), nullable=False)
    work_order_type: Mapped[MaintenanceWorkOrderType] = mapped_column(
        SAEnum(MaintenanceWorkOrderType),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    asset_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    component_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_asset_components.id", ondelete="SET NULL"),
        nullable=True,
    )
    system_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_systems.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    priority: Mapped[MaintenancePriority] = mapped_column(
        SAEnum(MaintenancePriority),
        nullable=False,
        default=MaintenancePriority.MEDIUM,
        server_default=MaintenancePriority.MEDIUM.value,
    )
    status: Mapped[MaintenanceWorkOrderStatus] = mapped_column(
        SAEnum(MaintenanceWorkOrderStatus),
        nullable=False,
        default=MaintenanceWorkOrderStatus.DRAFT,
        server_default=MaintenanceWorkOrderStatus.DRAFT.value,
    )
    requested_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    planner_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    supervisor_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_team_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    assigned_employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    planned_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    planned_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    requires_shutdown: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    permit_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    failure_code: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    root_cause_code: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    downtime_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parts_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    labor_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    vendor_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_preventive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceWorkOrderTaskORM(Base):
    __tablename__ = "maintenance_work_order_tasks"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "work_order_id",
            "sequence_no",
            name="ux_maintenance_work_order_tasks_work_order_sequence",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    work_order_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_work_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_template_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    assigned_employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_team_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    required_skill: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    status: Mapped[MaintenanceWorkOrderTaskStatus] = mapped_column(
        SAEnum(MaintenanceWorkOrderTaskStatus),
        nullable=False,
        default=MaintenanceWorkOrderTaskStatus.NOT_STARTED,
        server_default=MaintenanceWorkOrderTaskStatus.NOT_STARTED.value,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    completion_rule: Mapped[MaintenanceTaskCompletionRule] = mapped_column(
        SAEnum(MaintenanceTaskCompletionRule),
        nullable=False,
        default=MaintenanceTaskCompletionRule.NO_STEPS_REQUIRED,
        server_default=MaintenanceTaskCompletionRule.NO_STEPS_REQUIRED.value,
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
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
Index("idx_maintenance_work_requests_org", MaintenanceWorkRequestORM.organization_id)
Index("idx_maintenance_work_requests_site", MaintenanceWorkRequestORM.site_id)
Index("idx_maintenance_work_requests_asset", MaintenanceWorkRequestORM.asset_id)
Index("idx_maintenance_work_requests_component", MaintenanceWorkRequestORM.component_id)
Index("idx_maintenance_work_requests_system", MaintenanceWorkRequestORM.system_id)
Index("idx_maintenance_work_requests_location", MaintenanceWorkRequestORM.location_id)
Index("idx_maintenance_work_requests_status", MaintenanceWorkRequestORM.status)
Index("idx_maintenance_work_requests_priority", MaintenanceWorkRequestORM.priority)
Index("idx_maintenance_work_requests_requested_by", MaintenanceWorkRequestORM.requested_by_user_id)
Index("idx_maintenance_work_requests_triaged_by", MaintenanceWorkRequestORM.triaged_by_user_id)
Index("idx_maintenance_work_orders_org", MaintenanceWorkOrderORM.organization_id)
Index("idx_maintenance_work_orders_site", MaintenanceWorkOrderORM.site_id)
Index("idx_maintenance_work_orders_asset", MaintenanceWorkOrderORM.asset_id)
Index("idx_maintenance_work_orders_component", MaintenanceWorkOrderORM.component_id)
Index("idx_maintenance_work_orders_system", MaintenanceWorkOrderORM.system_id)
Index("idx_maintenance_work_orders_location", MaintenanceWorkOrderORM.location_id)
Index("idx_maintenance_work_orders_status", MaintenanceWorkOrderORM.status)
Index("idx_maintenance_work_orders_priority", MaintenanceWorkOrderORM.priority)
Index("idx_maintenance_work_orders_assigned_team", MaintenanceWorkOrderORM.assigned_team_id)
Index("idx_maintenance_work_orders_assigned_employee", MaintenanceWorkOrderORM.assigned_employee_id)
Index("idx_maintenance_work_orders_planner", MaintenanceWorkOrderORM.planner_user_id)
Index("idx_maintenance_work_orders_supervisor", MaintenanceWorkOrderORM.supervisor_user_id)
Index("idx_maintenance_work_orders_type", MaintenanceWorkOrderORM.work_order_type)
Index("idx_maintenance_work_orders_preventive", MaintenanceWorkOrderORM.is_preventive)
Index("idx_maintenance_work_orders_emergency", MaintenanceWorkOrderORM.is_emergency)
Index("idx_maintenance_work_order_tasks_org", MaintenanceWorkOrderTaskORM.organization_id)
Index("idx_maintenance_work_order_tasks_work_order", MaintenanceWorkOrderTaskORM.work_order_id)
Index("idx_maintenance_work_order_tasks_status", MaintenanceWorkOrderTaskORM.status)
Index("idx_maintenance_work_order_tasks_assigned_employee", MaintenanceWorkOrderTaskORM.assigned_employee_id)
Index("idx_maintenance_work_order_tasks_assigned_team", MaintenanceWorkOrderTaskORM.assigned_team_id)


__all__ = [
    "MaintenanceAssetORM",
    "MaintenanceAssetComponentORM",
    "MaintenanceLocationORM",
    "MaintenanceSystemORM",
    "MaintenanceWorkOrderORM",
    "MaintenanceWorkOrderTaskORM",
    "MaintenanceWorkRequestORM",
]
