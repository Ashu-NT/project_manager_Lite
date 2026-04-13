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
    MaintenanceCalendarFrequencyUnit,
    MaintenanceCriticality,
    MaintenanceFailureCodeType,
    MaintenanceGenerationLeadUnit,
    MaintenanceLifecycleStatus,
    MaintenanceMaterialProcurementStatus,
    MaintenancePlanStatus,
    MaintenancePlanTaskTriggerScope,
    MaintenancePlanType,
    MaintenancePriority,
    MaintenanceSchedulePolicy,
    MaintenanceSensorDirection,
    MaintenanceSensorExceptionStatus,
    MaintenanceSensorExceptionType,
    MaintenanceSensorQualityState,
    MaintenanceTemplateStatus,
    MaintenanceTriggerMode,
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderTaskStepStatus,
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


class MaintenanceSensorORM(Base):
    __tablename__ = "maintenance_sensors"
    __table_args__ = (
        UniqueConstraint("organization_id", "sensor_code", name="ux_maintenance_sensors_org_code"),
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
    sensor_code: Mapped[str] = mapped_column(String(64), nullable=False)
    sensor_name: Mapped[str] = mapped_column(String(256), nullable=False)
    sensor_tag: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sensor_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
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
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    current_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    last_read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_quality_state: Mapped[MaintenanceSensorQualityState] = mapped_column(
        SAEnum(MaintenanceSensorQualityState),
        nullable=False,
        default=MaintenanceSensorQualityState.VALID,
        server_default=MaintenanceSensorQualityState.VALID.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceSensorReadingORM(Base):
    __tablename__ = "maintenance_sensor_readings"
    __table_args__ = (
        Index("ix_maintenance_sensor_readings_sensor_timestamp", "sensor_id", "reading_timestamp"),
        Index("ix_maintenance_sensor_readings_org_batch", "organization_id", "source_batch_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sensor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_sensors.id", ondelete="CASCADE"),
        nullable=False,
    )
    reading_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reading_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    reading_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    quality_state: Mapped[MaintenanceSensorQualityState] = mapped_column(
        SAEnum(MaintenanceSensorQualityState),
        nullable=False,
        default=MaintenanceSensorQualityState.VALID,
        server_default=MaintenanceSensorQualityState.VALID.value,
    )
    source_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_batch_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    raw_payload_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceIntegrationSourceORM(Base):
    __tablename__ = "maintenance_integration_sources"
    __table_args__ = (
        UniqueConstraint("organization_id", "integration_code", name="ux_maintenance_integration_sources_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    integration_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint_or_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    authentication_mode: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    schedule_expression: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_successful_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_failed_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceSensorSourceMappingORM(Base):
    __tablename__ = "maintenance_sensor_source_mappings"
    __table_args__ = (
        UniqueConstraint(
            "integration_source_id",
            "sensor_id",
            "external_equipment_key",
            "external_measurement_key",
            name="ux_maintenance_sensor_source_mappings_unique",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    integration_source_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_integration_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    sensor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_sensors.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_equipment_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    external_measurement_key: Mapped[str] = mapped_column(String(128), nullable=False)
    transform_rule: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_conversion_rule: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceSensorExceptionORM(Base):
    __tablename__ = "maintenance_sensor_exceptions"
    __table_args__ = (
        Index("ix_maintenance_sensor_exceptions_status", "status"),
        Index("ix_maintenance_sensor_exceptions_sensor", "sensor_id"),
        Index("ix_maintenance_sensor_exceptions_integration_source", "integration_source_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sensor_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_sensors.id", ondelete="SET NULL"),
        nullable=True,
    )
    integration_source_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_integration_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_mapping_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_sensor_source_mappings.id", ondelete="SET NULL"),
        nullable=True,
    )
    exception_type: Mapped[MaintenanceSensorExceptionType] = mapped_column(
        SAEnum(MaintenanceSensorExceptionType),
        nullable=False,
    )
    status: Mapped[MaintenanceSensorExceptionStatus] = mapped_column(
        SAEnum(MaintenanceSensorExceptionStatus),
        nullable=False,
        default=MaintenanceSensorExceptionStatus.OPEN,
        server_default=MaintenanceSensorExceptionStatus.OPEN.value,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_batch_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    raw_payload_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceFailureCodeORM(Base):
    __tablename__ = "maintenance_failure_codes"
    __table_args__ = (
        UniqueConstraint("organization_id", "failure_code", name="ux_maintenance_failure_codes_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    failure_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code_type: Mapped[MaintenanceFailureCodeType] = mapped_column(
        SAEnum(MaintenanceFailureCodeType),
        nullable=False,
        default=MaintenanceFailureCodeType.SYMPTOM,
        server_default=MaintenanceFailureCodeType.SYMPTOM.value,
    )
    parent_code_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_failure_codes.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceDowntimeEventORM(Base):
    __tablename__ = "maintenance_downtime_events"
    __table_args__ = (
        Index("ix_maintenance_downtime_events_work_order", "work_order_id"),
        Index("ix_maintenance_downtime_events_asset", "asset_id"),
        Index("ix_maintenance_downtime_events_system", "system_id"),
        Index("ix_maintenance_downtime_events_start", "started_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    system_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_systems.id", ondelete="SET NULL"),
        nullable=True,
    )
    work_order_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_work_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    downtime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    impact_notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
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
    source_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_plan_task_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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


class MaintenanceWorkOrderTaskStepORM(Base):
    __tablename__ = "maintenance_work_order_task_steps"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "work_order_task_id",
            "step_number",
            name="ux_maintenance_work_order_task_steps_task_step_number",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    work_order_task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_work_order_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_step_template_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    expected_result: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    hint_level: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    hint_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    status: Mapped[MaintenanceWorkOrderTaskStepStatus] = mapped_column(
        SAEnum(MaintenanceWorkOrderTaskStepStatus),
        nullable=False,
        default=MaintenanceWorkOrderTaskStepStatus.NOT_STARTED,
        server_default=MaintenanceWorkOrderTaskStepStatus.NOT_STARTED.value,
    )
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    requires_measurement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    requires_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    measurement_value: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    measurement_unit: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    completed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceWorkOrderMaterialRequirementORM(Base):
    __tablename__ = "maintenance_work_order_material_requirements"

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
    stock_item_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("inventory_stock_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    required_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0, server_default="0")
    issued_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0, server_default="0")
    required_uom: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    is_stock_item: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    preferred_storeroom_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("inventory_storerooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    procurement_status: Mapped[MaintenanceMaterialProcurementStatus] = mapped_column(
        SAEnum(MaintenanceMaterialProcurementStatus),
        nullable=False,
        default=MaintenanceMaterialProcurementStatus.PLANNED,
        server_default=MaintenanceMaterialProcurementStatus.PLANNED.value,
    )
    last_availability_status: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    last_missing_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    linked_requisition_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("inventory_purchase_requisitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceTaskTemplateORM(Base):
    __tablename__ = "maintenance_task_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "task_template_code", name="ux_maintenance_task_templates_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_template_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    maintenance_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    template_status: Mapped[MaintenanceTemplateStatus] = mapped_column(
        SAEnum(MaintenanceTemplateStatus),
        nullable=False,
        default=MaintenanceTemplateStatus.DRAFT,
        server_default=MaintenanceTemplateStatus.DRAFT.value,
    )
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    required_skill: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    requires_shutdown: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    requires_permit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenanceTaskStepTemplateORM(Base):
    __tablename__ = "maintenance_task_step_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "task_template_id",
            "step_number",
            name="ux_maintenance_task_step_templates_task_step_number",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_template_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_task_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    expected_result: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    hint_level: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    hint_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    requires_measurement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    requires_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    measurement_unit: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenancePreventivePlanORM(Base):
    __tablename__ = "maintenance_preventive_plans"
    __table_args__ = (
        UniqueConstraint("organization_id", "plan_code", name="ux_maintenance_preventive_plans_org_code"),
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
    plan_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
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
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    status: Mapped[MaintenancePlanStatus] = mapped_column(
        SAEnum(MaintenancePlanStatus),
        nullable=False,
        default=MaintenancePlanStatus.DRAFT,
        server_default=MaintenancePlanStatus.DRAFT.value,
    )
    plan_type: Mapped[MaintenancePlanType] = mapped_column(
        SAEnum(MaintenancePlanType),
        nullable=False,
        default=MaintenancePlanType.PREVENTIVE,
        server_default=MaintenancePlanType.PREVENTIVE.value,
    )
    priority: Mapped[MaintenancePriority] = mapped_column(
        SAEnum(MaintenancePriority),
        nullable=False,
        default=MaintenancePriority.MEDIUM,
        server_default=MaintenancePriority.MEDIUM.value,
    )
    trigger_mode: Mapped[MaintenanceTriggerMode] = mapped_column(
        SAEnum(MaintenanceTriggerMode),
        nullable=False,
        default=MaintenanceTriggerMode.CALENDAR,
        server_default=MaintenanceTriggerMode.CALENDAR.value,
    )
    schedule_policy: Mapped[MaintenanceSchedulePolicy] = mapped_column(
        SAEnum(MaintenanceSchedulePolicy),
        nullable=False,
        default=MaintenanceSchedulePolicy.FIXED,
        server_default=MaintenanceSchedulePolicy.FIXED.value,
    )
    calendar_frequency_unit: Mapped[Optional[MaintenanceCalendarFrequencyUnit]] = mapped_column(SAEnum(MaintenanceCalendarFrequencyUnit), nullable=True)
    calendar_frequency_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    generation_horizon_count: Mapped[int] = mapped_column(Integer, nullable=False, default=13, server_default="13")
    generation_lead_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    generation_lead_unit: Mapped[MaintenanceGenerationLeadUnit] = mapped_column(SAEnum(MaintenanceGenerationLeadUnit), nullable=False, default=MaintenanceGenerationLeadUnit.DAYS, server_default=MaintenanceGenerationLeadUnit.DAYS.value)
    sensor_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_sensors.id", ondelete="SET NULL"),
        nullable=True,
    )
    sensor_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    sensor_direction: Mapped[Optional[MaintenanceSensorDirection]] = mapped_column(SAEnum(MaintenanceSensorDirection), nullable=True)
    sensor_reset_rule: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    last_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_due_counter: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    requires_shutdown: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    auto_generate_work_order: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class MaintenancePreventivePlanTaskORM(Base):
    __tablename__ = "maintenance_preventive_plan_tasks"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "plan_id",
            "sequence_no",
            name="ux_maintenance_preventive_plan_tasks_plan_sequence",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_preventive_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_template_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("maintenance_task_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger_scope: Mapped[MaintenancePlanTaskTriggerScope] = mapped_column(
        SAEnum(MaintenancePlanTaskTriggerScope),
        nullable=False,
        default=MaintenancePlanTaskTriggerScope.INHERIT_PLAN,
        server_default=MaintenancePlanTaskTriggerScope.INHERIT_PLAN.value,
    )
    trigger_mode_override: Mapped[Optional[MaintenanceTriggerMode]] = mapped_column(
        SAEnum(MaintenanceTriggerMode),
        nullable=True,
    )
    calendar_frequency_unit_override: Mapped[Optional[MaintenanceCalendarFrequencyUnit]] = mapped_column(
        SAEnum(MaintenanceCalendarFrequencyUnit),
        nullable=True,
    )
    calendar_frequency_value_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sensor_id_override: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("maintenance_sensors.id", ondelete="SET NULL"),
        nullable=True,
    )
    sensor_threshold_override: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    sensor_direction_override: Mapped[Optional[MaintenanceSensorDirection]] = mapped_column(
        SAEnum(MaintenanceSensorDirection),
        nullable=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    default_assigned_employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    default_assigned_team_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    estimated_minutes_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_due_counter: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
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
Index("idx_maintenance_work_order_task_steps_org", MaintenanceWorkOrderTaskStepORM.organization_id)
Index("idx_maintenance_work_order_task_steps_task", MaintenanceWorkOrderTaskStepORM.work_order_task_id)
Index("idx_maintenance_work_order_task_steps_status", MaintenanceWorkOrderTaskStepORM.status)
Index("idx_maintenance_work_order_task_steps_completed_by", MaintenanceWorkOrderTaskStepORM.completed_by_user_id)
Index("idx_maintenance_work_order_task_steps_confirmed_by", MaintenanceWorkOrderTaskStepORM.confirmed_by_user_id)
Index("idx_maintenance_material_requirements_org", MaintenanceWorkOrderMaterialRequirementORM.organization_id)
Index("idx_maintenance_material_requirements_work_order", MaintenanceWorkOrderMaterialRequirementORM.work_order_id)
Index("idx_maintenance_material_requirements_stock_item", MaintenanceWorkOrderMaterialRequirementORM.stock_item_id)
Index(
    "idx_maintenance_material_requirements_storeroom",
    MaintenanceWorkOrderMaterialRequirementORM.preferred_storeroom_id,
)
Index(
    "idx_maintenance_material_requirements_status",
    MaintenanceWorkOrderMaterialRequirementORM.procurement_status,
)
Index(
    "idx_maintenance_material_requirements_requisition",
    MaintenanceWorkOrderMaterialRequirementORM.linked_requisition_id,
)
Index("idx_maintenance_task_templates_org", MaintenanceTaskTemplateORM.organization_id)
Index("idx_maintenance_task_templates_status", MaintenanceTaskTemplateORM.template_status)
Index("idx_maintenance_task_templates_active", MaintenanceTaskTemplateORM.is_active)
Index("idx_maintenance_task_templates_type", MaintenanceTaskTemplateORM.maintenance_type)
Index("idx_maintenance_task_step_templates_org", MaintenanceTaskStepTemplateORM.organization_id)
Index("idx_maintenance_task_step_templates_task", MaintenanceTaskStepTemplateORM.task_template_id)
Index("idx_maintenance_task_step_templates_active", MaintenanceTaskStepTemplateORM.is_active)
Index("idx_maintenance_task_step_templates_sort", MaintenanceTaskStepTemplateORM.sort_order)
Index("idx_maintenance_preventive_plans_org", MaintenancePreventivePlanORM.organization_id)
Index("idx_maintenance_preventive_plans_site", MaintenancePreventivePlanORM.site_id)
Index("idx_maintenance_preventive_plans_asset", MaintenancePreventivePlanORM.asset_id)
Index("idx_maintenance_preventive_plans_component", MaintenancePreventivePlanORM.component_id)
Index("idx_maintenance_preventive_plans_system", MaintenancePreventivePlanORM.system_id)
Index("idx_maintenance_preventive_plans_status", MaintenancePreventivePlanORM.status)
Index("idx_maintenance_preventive_plans_type", MaintenancePreventivePlanORM.plan_type)
Index("idx_maintenance_preventive_plans_trigger", MaintenancePreventivePlanORM.trigger_mode)
Index("idx_maintenance_preventive_plans_sensor", MaintenancePreventivePlanORM.sensor_id)
Index("idx_maintenance_plan_tasks_org", MaintenancePreventivePlanTaskORM.organization_id)
Index("idx_maintenance_plan_tasks_plan", MaintenancePreventivePlanTaskORM.plan_id)
Index("idx_maintenance_plan_tasks_template", MaintenancePreventivePlanTaskORM.task_template_id)
Index("idx_maintenance_plan_tasks_sensor", MaintenancePreventivePlanTaskORM.sensor_id_override)
Index("idx_maintenance_plan_tasks_assigned_employee", MaintenancePreventivePlanTaskORM.default_assigned_employee_id)
Index("idx_maintenance_plan_tasks_next_due_at", MaintenancePreventivePlanTaskORM.next_due_at)


__all__ = [
    "MaintenanceAssetORM",
    "MaintenanceAssetComponentORM",
    "MaintenanceLocationORM",
    "MaintenancePreventivePlanORM",
    "MaintenancePreventivePlanTaskORM",
    "MaintenanceSystemORM",
    "MaintenanceTaskStepTemplateORM",
    "MaintenanceTaskTemplateORM",
    "MaintenanceWorkOrderORM",
    "MaintenanceWorkOrderMaterialRequirementORM",
    "MaintenanceWorkOrderTaskORM",
    "MaintenanceWorkOrderTaskStepORM",
    "MaintenanceWorkRequestORM",
]
