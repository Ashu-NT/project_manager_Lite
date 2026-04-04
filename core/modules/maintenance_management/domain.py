from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from core.modules.maintenance_management.reliability_domain import (
    MaintenanceDowntimeEvent,
    MaintenanceFailureCode,
    MaintenanceFailureCodeType,
)
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


class MaintenanceWorkOrderTaskStepStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class MaintenanceMaterialProcurementStatus(str, Enum):
    PLANNED = "PLANNED"
    AVAILABLE_FROM_STOCK = "AVAILABLE_FROM_STOCK"
    SHORTAGE_IDENTIFIED = "SHORTAGE_IDENTIFIED"
    REQUISITIONED = "REQUISITIONED"
    PARTIALLY_ISSUED = "PARTIALLY_ISSUED"
    FULLY_ISSUED = "FULLY_ISSUED"
    NON_STOCK = "NON_STOCK"


class MaintenanceSensorQualityState(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    ESTIMATED = "ESTIMATED"
    ERROR = "ERROR"


class MaintenanceSensorExceptionType(str, Enum):
    MISSING_FEED = "MISSING_FEED"
    STALE_READING = "STALE_READING"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    INVALID_THRESHOLD_MAPPING = "INVALID_THRESHOLD_MAPPING"
    EXTERNAL_SYNC_FAILURE = "EXTERNAL_SYNC_FAILURE"


class MaintenanceSensorExceptionStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class MaintenanceTemplateStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class MaintenancePlanStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    RETIRED = "RETIRED"


class MaintenancePlanType(str, Enum):
    PREVENTIVE = "PREVENTIVE"
    INSPECTION = "INSPECTION"
    LUBRICATION = "LUBRICATION"
    CALIBRATION = "CALIBRATION"
    CONDITION_BASED = "CONDITION_BASED"


class MaintenanceCalendarFrequencyUnit(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    CUSTOM_DAYS = "CUSTOM_DAYS"


class MaintenanceSensorDirection(str, Enum):
    GREATER_OR_EQUAL = "GREATER_OR_EQUAL"
    LESS_OR_EQUAL = "LESS_OR_EQUAL"
    EQUAL = "EQUAL"


class MaintenancePlanTaskTriggerScope(str, Enum):
    INHERIT_PLAN = "INHERIT_PLAN"
    TASK_OVERRIDE = "TASK_OVERRIDE"


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


@dataclass
class MaintenanceWorkOrderTaskStep:
    id: str
    organization_id: str
    work_order_task_id: str
    source_step_template_id: str | None = None
    step_number: int = 1
    instruction: str = ""
    expected_result: str = ""
    hint_level: str = ""
    hint_text: str = ""
    status: MaintenanceWorkOrderTaskStepStatus = MaintenanceWorkOrderTaskStepStatus.NOT_STARTED
    requires_confirmation: bool = False
    requires_measurement: bool = False
    requires_photo: bool = False
    measurement_value: str = ""
    measurement_unit: str = ""
    completed_by_user_id: str | None = None
    completed_at: datetime | None = None
    confirmed_by_user_id: str | None = None
    confirmed_at: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        work_order_task_id: str,
        source_step_template_id: str | None = None,
        step_number: int = 1,
        instruction: str,
        expected_result: str = "",
        hint_level: str = "",
        hint_text: str = "",
        requires_confirmation: bool = False,
        requires_measurement: bool = False,
        requires_photo: bool = False,
        measurement_value: str = "",
        measurement_unit: str = "",
        notes: str = "",
    ) -> "MaintenanceWorkOrderTaskStep":
        now = datetime.now(timezone.utc)
        return MaintenanceWorkOrderTaskStep(
            id=generate_id(),
            organization_id=organization_id,
            work_order_task_id=work_order_task_id,
            source_step_template_id=source_step_template_id,
            step_number=step_number,
            instruction=instruction,
            expected_result=expected_result,
            hint_level=hint_level,
            hint_text=hint_text,
            status=MaintenanceWorkOrderTaskStepStatus.NOT_STARTED,
            requires_confirmation=requires_confirmation,
            requires_measurement=requires_measurement,
            requires_photo=requires_photo,
            measurement_value=measurement_value,
            measurement_unit=measurement_unit,
            completed_by_user_id=None,
            completed_at=None,
            confirmed_by_user_id=None,
            confirmed_at=None,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceWorkOrderMaterialRequirement:
    id: str
    organization_id: str
    work_order_id: str
    stock_item_id: str | None = None
    description: str = ""
    required_qty: Decimal = Decimal("0")
    issued_qty: Decimal = Decimal("0")
    required_uom: str = ""
    is_stock_item: bool = True
    preferred_storeroom_id: str | None = None
    procurement_status: MaintenanceMaterialProcurementStatus = MaintenanceMaterialProcurementStatus.PLANNED
    last_availability_status: str = ""
    last_missing_qty: Decimal | None = None
    linked_requisition_id: str | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        work_order_id: str,
        stock_item_id: str | None = None,
        description: str = "",
        required_qty: Decimal,
        issued_qty: Decimal = Decimal("0"),
        required_uom: str = "",
        is_stock_item: bool = True,
        preferred_storeroom_id: str | None = None,
        procurement_status: MaintenanceMaterialProcurementStatus | None = None,
        last_availability_status: str = "",
        last_missing_qty: Decimal | None = None,
        linked_requisition_id: str | None = None,
        notes: str = "",
    ) -> "MaintenanceWorkOrderMaterialRequirement":
        now = datetime.now(timezone.utc)
        resolved_status = procurement_status or (
            MaintenanceMaterialProcurementStatus.PLANNED
            if is_stock_item
            else MaintenanceMaterialProcurementStatus.NON_STOCK
        )
        return MaintenanceWorkOrderMaterialRequirement(
            id=generate_id(),
            organization_id=organization_id,
            work_order_id=work_order_id,
            stock_item_id=stock_item_id,
            description=description,
            required_qty=required_qty,
            issued_qty=issued_qty,
            required_uom=required_uom,
            is_stock_item=is_stock_item,
            preferred_storeroom_id=preferred_storeroom_id,
            procurement_status=resolved_status,
            last_availability_status=last_availability_status,
            last_missing_qty=last_missing_qty,
            linked_requisition_id=linked_requisition_id,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceSensor:
    id: str
    organization_id: str
    site_id: str
    sensor_code: str
    sensor_name: str
    sensor_tag: str = ""
    sensor_type: str = ""
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    source_type: str = ""
    source_name: str = ""
    source_key: str = ""
    unit: str = ""
    current_value: Decimal | None = None
    last_read_at: datetime | None = None
    last_quality_state: MaintenanceSensorQualityState = MaintenanceSensorQualityState.VALID
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        sensor_code: str,
        sensor_name: str,
        sensor_tag: str = "",
        sensor_type: str = "",
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        source_type: str = "",
        source_name: str = "",
        source_key: str = "",
        unit: str = "",
        current_value: Decimal | None = None,
        last_read_at: datetime | None = None,
        last_quality_state: MaintenanceSensorQualityState = MaintenanceSensorQualityState.VALID,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceSensor":
        now = datetime.now(timezone.utc)
        return MaintenanceSensor(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            sensor_code=sensor_code,
            sensor_name=sensor_name,
            sensor_tag=sensor_tag,
            sensor_type=sensor_type,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            source_type=source_type,
            source_name=source_name,
            source_key=source_key,
            unit=unit,
            current_value=current_value,
            last_read_at=last_read_at,
            last_quality_state=last_quality_state,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceSensorReading:
    id: str
    organization_id: str
    sensor_id: str
    reading_value: Decimal
    reading_unit: str
    reading_timestamp: datetime
    quality_state: MaintenanceSensorQualityState = MaintenanceSensorQualityState.VALID
    source_name: str = ""
    source_batch_id: str = ""
    received_at: datetime | None = None
    raw_payload_ref: str = ""
    created_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        sensor_id: str,
        reading_value: Decimal,
        reading_unit: str,
        reading_timestamp: datetime,
        quality_state: MaintenanceSensorQualityState = MaintenanceSensorQualityState.VALID,
        source_name: str = "",
        source_batch_id: str = "",
        received_at: datetime | None = None,
        raw_payload_ref: str = "",
    ) -> "MaintenanceSensorReading":
        now = datetime.now(timezone.utc)
        return MaintenanceSensorReading(
            id=generate_id(),
            organization_id=organization_id,
            sensor_id=sensor_id,
            reading_value=reading_value,
            reading_unit=reading_unit,
            reading_timestamp=reading_timestamp,
            quality_state=quality_state,
            source_name=source_name,
            source_batch_id=source_batch_id,
            received_at=received_at or now,
            raw_payload_ref=raw_payload_ref,
            created_at=now,
            version=1,
        )


@dataclass
class MaintenanceIntegrationSource:
    id: str
    organization_id: str
    integration_code: str
    name: str
    integration_type: str
    endpoint_or_path: str = ""
    authentication_mode: str = ""
    schedule_expression: str = ""
    last_successful_sync_at: datetime | None = None
    last_failed_sync_at: datetime | None = None
    last_error_message: str = ""
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        integration_code: str,
        name: str,
        integration_type: str,
        endpoint_or_path: str = "",
        authentication_mode: str = "",
        schedule_expression: str = "",
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceIntegrationSource":
        now = datetime.now(timezone.utc)
        return MaintenanceIntegrationSource(
            id=generate_id(),
            organization_id=organization_id,
            integration_code=integration_code,
            name=name,
            integration_type=integration_type,
            endpoint_or_path=endpoint_or_path,
            authentication_mode=authentication_mode,
            schedule_expression=schedule_expression,
            last_successful_sync_at=None,
            last_failed_sync_at=None,
            last_error_message="",
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceSensorSourceMapping:
    id: str
    organization_id: str
    integration_source_id: str
    sensor_id: str
    external_equipment_key: str = ""
    external_measurement_key: str = ""
    transform_rule: str = ""
    unit_conversion_rule: str = ""
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        integration_source_id: str,
        sensor_id: str,
        external_equipment_key: str = "",
        external_measurement_key: str = "",
        transform_rule: str = "",
        unit_conversion_rule: str = "",
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceSensorSourceMapping":
        now = datetime.now(timezone.utc)
        return MaintenanceSensorSourceMapping(
            id=generate_id(),
            organization_id=organization_id,
            integration_source_id=integration_source_id,
            sensor_id=sensor_id,
            external_equipment_key=external_equipment_key,
            external_measurement_key=external_measurement_key,
            transform_rule=transform_rule,
            unit_conversion_rule=unit_conversion_rule,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceSensorException:
    id: str
    organization_id: str
    sensor_id: str | None = None
    integration_source_id: str | None = None
    source_mapping_id: str | None = None
    exception_type: MaintenanceSensorExceptionType = MaintenanceSensorExceptionType.STALE_READING
    status: MaintenanceSensorExceptionStatus = MaintenanceSensorExceptionStatus.OPEN
    message: str = ""
    source_batch_id: str = ""
    raw_payload_ref: str = ""
    detected_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by_user_id: str | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: str | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        sensor_id: str | None = None,
        integration_source_id: str | None = None,
        source_mapping_id: str | None = None,
        exception_type: MaintenanceSensorExceptionType,
        message: str,
        source_batch_id: str = "",
        raw_payload_ref: str = "",
        detected_at: datetime | None = None,
        notes: str = "",
    ) -> "MaintenanceSensorException":
        now = datetime.now(timezone.utc)
        return MaintenanceSensorException(
            id=generate_id(),
            organization_id=organization_id,
            sensor_id=sensor_id,
            integration_source_id=integration_source_id,
            source_mapping_id=source_mapping_id,
            exception_type=exception_type,
            status=MaintenanceSensorExceptionStatus.OPEN,
            message=message,
            source_batch_id=source_batch_id,
            raw_payload_ref=raw_payload_ref,
            detected_at=detected_at or now,
            acknowledged_at=None,
            acknowledged_by_user_id=None,
            resolved_at=None,
            resolved_by_user_id=None,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceTaskTemplate:
    id: str
    organization_id: str
    task_template_code: str
    name: str
    description: str = ""
    maintenance_type: str = ""
    revision_no: int = 1
    template_status: MaintenanceTemplateStatus = MaintenanceTemplateStatus.DRAFT
    estimated_minutes: int | None = None
    required_skill: str = ""
    requires_shutdown: bool = False
    requires_permit: bool = False
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        task_template_code: str,
        name: str,
        description: str = "",
        maintenance_type: str = "",
        revision_no: int = 1,
        template_status: MaintenanceTemplateStatus = MaintenanceTemplateStatus.DRAFT,
        estimated_minutes: int | None = None,
        required_skill: str = "",
        requires_shutdown: bool = False,
        requires_permit: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceTaskTemplate":
        now = datetime.now(timezone.utc)
        return MaintenanceTaskTemplate(
            id=generate_id(),
            organization_id=organization_id,
            task_template_code=task_template_code,
            name=name,
            description=description,
            maintenance_type=maintenance_type,
            revision_no=revision_no,
            template_status=template_status,
            estimated_minutes=estimated_minutes,
            required_skill=required_skill,
            requires_shutdown=requires_shutdown,
            requires_permit=requires_permit,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenanceTaskStepTemplate:
    id: str
    organization_id: str
    task_template_id: str
    step_number: int
    instruction: str
    expected_result: str = ""
    hint_level: str = ""
    hint_text: str = ""
    requires_confirmation: bool = False
    requires_measurement: bool = False
    requires_photo: bool = False
    measurement_unit: str = ""
    sort_order: int = 0
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        task_template_id: str,
        step_number: int,
        instruction: str,
        expected_result: str = "",
        hint_level: str = "",
        hint_text: str = "",
        requires_confirmation: bool = False,
        requires_measurement: bool = False,
        requires_photo: bool = False,
        measurement_unit: str = "",
        sort_order: int = 0,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenanceTaskStepTemplate":
        now = datetime.now(timezone.utc)
        return MaintenanceTaskStepTemplate(
            id=generate_id(),
            organization_id=organization_id,
            task_template_id=task_template_id,
            step_number=step_number,
            instruction=instruction,
            expected_result=expected_result,
            hint_level=hint_level,
            hint_text=hint_text,
            requires_confirmation=requires_confirmation,
            requires_measurement=requires_measurement,
            requires_photo=requires_photo,
            measurement_unit=measurement_unit,
            sort_order=sort_order,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenancePreventivePlan:
    id: str
    organization_id: str
    site_id: str
    plan_code: str
    name: str
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    description: str = ""
    status: MaintenancePlanStatus = MaintenancePlanStatus.DRAFT
    plan_type: MaintenancePlanType = MaintenancePlanType.PREVENTIVE
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    trigger_mode: MaintenanceTriggerMode = MaintenanceTriggerMode.CALENDAR
    calendar_frequency_unit: MaintenanceCalendarFrequencyUnit | None = None
    calendar_frequency_value: int | None = None
    sensor_id: str | None = None
    sensor_threshold: Decimal | None = None
    sensor_direction: MaintenanceSensorDirection | None = None
    sensor_reset_rule: str = ""
    last_generated_at: datetime | None = None
    last_completed_at: datetime | None = None
    next_due_at: datetime | None = None
    next_due_counter: Decimal | None = None
    requires_shutdown: bool = False
    approval_required: bool = False
    auto_generate_work_order: bool = False
    is_active: bool = True
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        plan_code: str,
        name: str,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        description: str = "",
        status: MaintenancePlanStatus = MaintenancePlanStatus.DRAFT,
        plan_type: MaintenancePlanType = MaintenancePlanType.PREVENTIVE,
        priority: MaintenancePriority = MaintenancePriority.MEDIUM,
        trigger_mode: MaintenanceTriggerMode = MaintenanceTriggerMode.CALENDAR,
        calendar_frequency_unit: MaintenanceCalendarFrequencyUnit | None = None,
        calendar_frequency_value: int | None = None,
        sensor_id: str | None = None,
        sensor_threshold: Decimal | None = None,
        sensor_direction: MaintenanceSensorDirection | None = None,
        sensor_reset_rule: str = "",
        last_generated_at: datetime | None = None,
        last_completed_at: datetime | None = None,
        next_due_at: datetime | None = None,
        next_due_counter: Decimal | None = None,
        requires_shutdown: bool = False,
        approval_required: bool = False,
        auto_generate_work_order: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> "MaintenancePreventivePlan":
        now = datetime.now(timezone.utc)
        return MaintenancePreventivePlan(
            id=generate_id(),
            organization_id=organization_id,
            site_id=site_id,
            plan_code=plan_code,
            name=name,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            description=description,
            status=status,
            plan_type=plan_type,
            priority=priority,
            trigger_mode=trigger_mode,
            calendar_frequency_unit=calendar_frequency_unit,
            calendar_frequency_value=calendar_frequency_value,
            sensor_id=sensor_id,
            sensor_threshold=sensor_threshold,
            sensor_direction=sensor_direction,
            sensor_reset_rule=sensor_reset_rule,
            last_generated_at=last_generated_at,
            last_completed_at=last_completed_at,
            next_due_at=next_due_at,
            next_due_counter=next_due_counter,
            requires_shutdown=requires_shutdown,
            approval_required=approval_required,
            auto_generate_work_order=auto_generate_work_order,
            is_active=is_active,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class MaintenancePreventivePlanTask:
    id: str
    organization_id: str
    plan_id: str
    task_template_id: str
    trigger_scope: MaintenancePlanTaskTriggerScope = MaintenancePlanTaskTriggerScope.INHERIT_PLAN
    trigger_mode_override: MaintenanceTriggerMode | None = None
    calendar_frequency_unit_override: MaintenanceCalendarFrequencyUnit | None = None
    calendar_frequency_value_override: int | None = None
    sensor_id_override: str | None = None
    sensor_threshold_override: Decimal | None = None
    sensor_direction_override: MaintenanceSensorDirection | None = None
    sequence_no: int = 1
    is_mandatory: bool = True
    default_assigned_employee_id: str | None = None
    default_assigned_team_id: str | None = None
    estimated_minutes_override: int | None = None
    last_generated_at: datetime | None = None
    next_due_at: datetime | None = None
    next_due_counter: Decimal | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        plan_id: str,
        task_template_id: str,
        trigger_scope: MaintenancePlanTaskTriggerScope = MaintenancePlanTaskTriggerScope.INHERIT_PLAN,
        trigger_mode_override: MaintenanceTriggerMode | None = None,
        calendar_frequency_unit_override: MaintenanceCalendarFrequencyUnit | None = None,
        calendar_frequency_value_override: int | None = None,
        sensor_id_override: str | None = None,
        sensor_threshold_override: Decimal | None = None,
        sensor_direction_override: MaintenanceSensorDirection | None = None,
        sequence_no: int = 1,
        is_mandatory: bool = True,
        default_assigned_employee_id: str | None = None,
        default_assigned_team_id: str | None = None,
        estimated_minutes_override: int | None = None,
        last_generated_at: datetime | None = None,
        next_due_at: datetime | None = None,
        next_due_counter: Decimal | None = None,
        notes: str = "",
    ) -> "MaintenancePreventivePlanTask":
        now = datetime.now(timezone.utc)
        return MaintenancePreventivePlanTask(
            id=generate_id(),
            organization_id=organization_id,
            plan_id=plan_id,
            task_template_id=task_template_id,
            trigger_scope=trigger_scope,
            trigger_mode_override=trigger_mode_override,
            calendar_frequency_unit_override=calendar_frequency_unit_override,
            calendar_frequency_value_override=calendar_frequency_value_override,
            sensor_id_override=sensor_id_override,
            sensor_threshold_override=sensor_threshold_override,
            sensor_direction_override=sensor_direction_override,
            sequence_no=sequence_no,
            is_mandatory=is_mandatory,
            default_assigned_employee_id=default_assigned_employee_id,
            default_assigned_team_id=default_assigned_team_id,
            estimated_minutes_override=estimated_minutes_override,
            last_generated_at=last_generated_at,
            next_due_at=next_due_at,
            next_due_counter=next_due_counter,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


__all__ = [
    "MaintenanceAsset",
    "MaintenanceAssetComponent",
    "MaintenanceCriticality",
    "MaintenanceDowntimeEvent",
    "MaintenanceFailureCode",
    "MaintenanceFailureCodeType",
    "MaintenanceIntegrationSource",
    "MaintenanceLifecycleStatus",
    "MaintenanceLocation",
    "MaintenanceMaterialProcurementStatus",
    "MaintenancePriority",
    "MaintenancePreventivePlan",
    "MaintenancePreventivePlanTask",
    "MaintenancePlanStatus",
    "MaintenancePlanTaskTriggerScope",
    "MaintenancePlanType",
    "MaintenanceCalendarFrequencyUnit",
    "MaintenanceSensorException",
    "MaintenanceSensorDirection",
    "MaintenanceSensorExceptionStatus",
    "MaintenanceSensorExceptionType",
    "MaintenanceSensor",
    "MaintenanceSensorQualityState",
    "MaintenanceSensorReading",
    "MaintenanceSensorSourceMapping",
    "MaintenanceSystem",
    "MaintenanceTaskStepTemplate",
    "MaintenanceTaskTemplate",
    "MaintenanceTemplateStatus",
    "MaintenanceTriggerMode",
    "MaintenanceWorkOrder",
    "MaintenanceWorkOrderMaterialRequirement",
    "MaintenanceWorkOrderTask",
    "MaintenanceWorkOrderTaskStep",
    "MaintenanceWorkOrderTaskStepStatus",
    "MaintenanceWorkOrderTaskStatus",
    "MaintenanceWorkOrderStatus",
    "MaintenanceWorkOrderType",
    "MaintenanceTaskCompletionRule",
    "MaintenanceWorkRequest",
    "MaintenanceWorkRequestSourceType",
    "MaintenanceWorkRequestStatus",
]
