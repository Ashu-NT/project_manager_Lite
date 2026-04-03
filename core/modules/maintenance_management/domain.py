from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from core.platform.common.ids import generate_id


class MaintenanceLifecycleStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RETIRED = "RETIRED"


class MaintenanceCriticality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaintenancePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class MaintenanceTriggerMode(str, Enum):
    CALENDAR = "CALENDAR"
    SENSOR = "SENSOR"
    HYBRID = "HYBRID"


class MaintenanceWorkRequestSourceType(str, Enum):
    MANUAL = "MANUAL"
    PREVENTIVE_PLAN = "PREVENTIVE_PLAN"
    SENSOR_TRIGGER = "SENSOR_TRIGGER"
    INSPECTION = "INSPECTION"
    INTEGRATION = "INTEGRATION"


class MaintenanceWorkRequestStatus(str, Enum):
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"
    DEFERRED = "DEFERRED"


class MaintenanceWorkOrderType(str, Enum):
    CORRECTIVE = "CORRECTIVE"
    PREVENTIVE = "PREVENTIVE"
    INSPECTION = "INSPECTION"
    CALIBRATION = "CALIBRATION"
    EMERGENCY = "EMERGENCY"
    CONDITION_BASED = "CONDITION_BASED"


class MaintenanceWorkOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    WAITING_PARTS = "WAITING_PARTS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_SHUTDOWN = "WAITING_SHUTDOWN"
    SCHEDULED = "SCHEDULED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class MaintenanceWorkOrderTaskStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class MaintenanceTaskCompletionRule(str, Enum):
    NO_STEPS_REQUIRED = "NO_STEPS_REQUIRED"
    ALL_STEPS_REQUIRED = "ALL_STEPS_REQUIRED"


@dataclass
class MaintenanceLocation:
    id: str
    organization_id: str
    site_id: str
    location_code: str
    name: str
    description: str = ""
    parent_location_id: str | None = None
    location_type: str = ""
    criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM
    status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE
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
        location_code: str,
        name: str,
        description: str = "",
        parent_location_id: str | None = None,
        location_type: str = "",
        criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM,
        status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceLocation":
        now = datetime.now(timezone.utc)
        return MaintenanceLocation(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            location_code=location_code,
            name=name,
            description=description,
            parent_location_id=parent_location_id,
            location_type=location_type,
            criticality=criticality,
            status=status,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


@dataclass
class MaintenanceSystem:
    id: str
    organization_id: str
    site_id: str
    system_code: str
    name: str
    location_id: str | None = None
    description: str = ""
    parent_system_id: str | None = None
    system_type: str = ""
    criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM
    status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE
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
        system_code: str,
        name: str,
        location_id: str | None = None,
        description: str = "",
        parent_system_id: str | None = None,
        system_type: str = "",
        criticality: MaintenanceCriticality = MaintenanceCriticality.MEDIUM,
        status: MaintenanceLifecycleStatus = MaintenanceLifecycleStatus.ACTIVE,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceSystem":
        now = datetime.now(timezone.utc)
        return MaintenanceSystem(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            system_code=system_code,
            name=name,
            location_id=location_id,
            description=description,
            parent_system_id=parent_system_id,
            system_type=system_type,
            criticality=criticality,
            status=status,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )


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


@dataclass
class MaintenanceWorkRequest:
    id: str
    organization_id: str
    site_id: str
    work_request_code: str
    source_type: MaintenanceWorkRequestSourceType
    request_type: str
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    location_id: str | None = None
    title: str = ""
    description: str = ""
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    status: MaintenanceWorkRequestStatus = MaintenanceWorkRequestStatus.NEW
    requested_at: datetime | None = None
    requested_by_user_id: str | None = None
    requested_by_name_snapshot: str = ""
    triaged_at: datetime | None = None
    triaged_by_user_id: str | None = None
    failure_symptom_code: str = ""
    safety_risk_level: str = ""
    production_impact_level: str = ""
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        work_request_code: str,
        source_type: MaintenanceWorkRequestSourceType,
        request_type: str,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str = "",
        description: str = "",
        priority: MaintenancePriority = MaintenancePriority.MEDIUM,
        requested_by_user_id: str | None = None,
        requested_by_name_snapshot: str = "",
        failure_symptom_code: str = "",
        safety_risk_level: str = "",
        production_impact_level: str = "",
        notes: str = "",
    ) -> "MaintenanceWorkRequest":
        now = datetime.now(timezone.utc)
        return MaintenanceWorkRequest(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            work_request_code=work_request_code,
            source_type=source_type,
            request_type=request_type,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
            title=title,
            description=description,
            priority=priority,
            status=MaintenanceWorkRequestStatus.NEW,
            requested_at=now,
            requested_by_user_id=requested_by_user_id,
            requested_by_name_snapshot=requested_by_name_snapshot,
            failure_symptom_code=failure_symptom_code,
            safety_risk_level=safety_risk_level,
            production_impact_level=production_impact_level,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceWorkOrder:
    id: str
    organization_id: str
    site_id: str
    work_order_code: str
    work_order_type: MaintenanceWorkOrderType
    source_type: str
    source_id: str | None = None
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    location_id: str | None = None
    title: str = ""
    description: str = ""
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    status: MaintenanceWorkOrderStatus = MaintenanceWorkOrderStatus.DRAFT
    requested_by_user_id: str | None = None
    planner_user_id: str | None = None
    supervisor_user_id: str | None = None
    assigned_team_id: str | None = None
    assigned_employee_id: str | None = None
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    requires_shutdown: bool = False
    permit_required: bool = False
    approval_required: bool = False
    failure_code: str = ""
    root_cause_code: str = ""
    downtime_minutes: int | None = None
    parts_cost: Decimal | None = None
    labor_cost: Decimal | None = None
    vendor_party_id: str | None = None
    is_preventive: bool = False
    is_emergency: bool = False
    closed_at: datetime | None = None
    closed_by_user_id: str | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        work_order_code: str,
        work_order_type: MaintenanceWorkOrderType,
        source_type: str,
        source_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str = "",
        description: str = "",
        priority: MaintenancePriority = MaintenancePriority.MEDIUM,
        requested_by_user_id: str | None = None,
        planner_user_id: str | None = None,
        supervisor_user_id: str | None = None,
        assigned_team_id: str | None = None,
        assigned_employee_id: str | None = None,
        planned_start: datetime | None = None,
        planned_end: datetime | None = None,
        requires_shutdown: bool = False,
        permit_required: bool = False,
        approval_required: bool = False,
        vendor_party_id: str | None = None,
        is_preventive: bool = False,
        is_emergency: bool = False,
        notes: str = "",
    ) -> "MaintenanceWorkOrder":
        now = datetime.now(timezone.utc)
        return MaintenanceWorkOrder(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            work_order_code=work_order_code,
            work_order_type=work_order_type,
            source_type=source_type,
            source_id=source_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            location_id=location_id,
            title=title,
            description=description,
            priority=priority,
            status=MaintenanceWorkOrderStatus.DRAFT,
            requested_by_user_id=requested_by_user_id,
            planner_user_id=planner_user_id,
            supervisor_user_id=supervisor_user_id,
            assigned_team_id=assigned_team_id,
            assigned_employee_id=assigned_employee_id,
            planned_start=planned_start,
            planned_end=planned_end,
            requires_shutdown=requires_shutdown,
            permit_required=permit_required,
            approval_required=approval_required,
            vendor_party_id=vendor_party_id,
            is_preventive=is_preventive,
            is_emergency=is_emergency,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceWorkOrderTask:
    id: str
    organization_id: str
    work_order_id: str
    task_template_id: str | None = None
    task_name: str = ""
    description: str = ""
    assigned_employee_id: str | None = None
    assigned_team_id: str | None = None
    estimated_minutes: int | None = None
    actual_minutes: int | None = None
    required_skill: str = ""
    status: MaintenanceWorkOrderTaskStatus = MaintenanceWorkOrderTaskStatus.NOT_STARTED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    sequence_no: int = 1
    is_mandatory: bool = True
    completion_rule: MaintenanceTaskCompletionRule = MaintenanceTaskCompletionRule.NO_STEPS_REQUIRED
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        work_order_id: str,
        task_template_id: str | None = None,
        task_name: str,
        description: str = "",
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
        estimated_minutes: int | None = None,
        actual_minutes: int | None = None,
        required_skill: str = "",
        sequence_no: int = 1,
        is_mandatory: bool = True,
        completion_rule: MaintenanceTaskCompletionRule = MaintenanceTaskCompletionRule.NO_STEPS_REQUIRED,
        notes: str = "",
    ) -> "MaintenanceWorkOrderTask":
        now = datetime.now(timezone.utc)
        return MaintenanceWorkOrderTask(
            id=generate_id(),
            organization_id=organization_id,
            work_order_id=work_order_id,
            task_template_id=task_template_id,
            task_name=task_name,
            description=description,
            assigned_employee_id=assigned_employee_id,
            assigned_team_id=assigned_team_id,
            estimated_minutes=estimated_minutes,
            actual_minutes=actual_minutes,
            required_skill=required_skill,
            status=MaintenanceWorkOrderTaskStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
            sequence_no=sequence_no,
            is_mandatory=is_mandatory,
            completion_rule=completion_rule,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


__all__ = [
    "MaintenanceAsset",
    "MaintenanceAssetComponent",
    "MaintenanceCriticality",
    "MaintenanceLifecycleStatus",
    "MaintenanceLocation",
    "MaintenancePriority",
    "MaintenanceSystem",
    "MaintenanceTriggerMode",
    "MaintenanceWorkOrder",
    "MaintenanceWorkOrderTask",
    "MaintenanceWorkOrderTaskStatus",
    "MaintenanceWorkOrderStatus",
    "MaintenanceWorkOrderType",
    "MaintenanceTaskCompletionRule",
    "MaintenanceWorkRequest",
    "MaintenanceWorkRequestSourceType",
    "MaintenanceWorkRequestStatus",
]
