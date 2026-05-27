from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from src.core.modules.maintenance.domain.enums import (
    MaintenanceMaterialProcurementStatus,
    MaintenancePriority,
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderTaskStepStatus,
    MaintenanceWorkOrderType,
)
from src.core.platform.common.ids import generate_id


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


__all__ = [
    "MaintenanceWorkOrder",
    "MaintenanceWorkOrderMaterialRequirement",
    "MaintenanceWorkOrderTask",
    "MaintenanceWorkOrderTaskStep",
]
