from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import field_validator, model_validator

from src.core.modules.maintenance.domain._validation import (
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_material_procurement_status,
    normalize_optional_datetime,
    normalize_optional_decimal,
    normalize_optional_identifier,
    normalize_optional_non_negative_int,
    normalize_optional_text,
    normalize_optional_upper_text,
    normalize_positive_int,
    normalize_positive_decimal,
    normalize_priority,
    normalize_required_text,
    normalize_task_completion_rule,
    normalize_work_order_status,
    normalize_work_order_task_status,
    normalize_work_order_task_step_status,
    normalize_work_order_type,
)
from src.core.modules.maintenance.domain.enums import (
    MaintenanceMaterialProcurementStatus,
    MaintenancePriority,
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrderStatus,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderTaskStepStatus,
    MaintenanceWorkOrderType,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass
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

    @field_validator("id", "organization_id", "site_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": ("Maintenance work order ID is required.", "MAINTENANCE_WORK_ORDER_ID_REQUIRED"),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_WORK_ORDER_ORGANIZATION_REQUIRED",
            ),
            "site_id": ("Site ID is required.", "MAINTENANCE_WORK_ORDER_SITE_REQUIRED"),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("work_order_code", mode="before")
    @classmethod
    def _validate_work_order_code(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Work order code")

    @field_validator("work_order_type", mode="before")
    @classmethod
    def _validate_work_order_type(cls, value: object) -> MaintenanceWorkOrderType:
        return normalize_work_order_type(value)

    @field_validator("source_type", mode="before")
    @classmethod
    def _validate_source_type(cls, value: object) -> str:
        return normalize_maintenance_code(value, label="Source type")

    @field_validator(
        "source_id",
        "asset_id",
        "component_id",
        "system_id",
        "location_id",
        "requested_by_user_id",
        "planner_user_id",
        "supervisor_user_id",
        "assigned_team_id",
        "assigned_employee_id",
        "vendor_party_id",
        "closed_by_user_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator(
        "title",
        "description",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _validate_priority(cls, value: object) -> MaintenancePriority:
        return normalize_priority(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> MaintenanceWorkOrderStatus:
        return normalize_work_order_status(value)

    @field_validator("failure_code", "root_cause_code", mode="before")
    @classmethod
    def _normalize_failure_fields(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("downtime_minutes", mode="before")
    @classmethod
    def _validate_downtime_minutes(cls, value: object) -> int | None:
        return normalize_optional_non_negative_int(value, label="Downtime minutes")

    @field_validator("parts_cost", "labor_cost", mode="before")
    @classmethod
    def _validate_costs(cls, value: object, info) -> Decimal | None:
        labels = {
            "parts_cost": "Parts cost",
            "labor_cost": "Labor cost",
        }
        return normalize_optional_decimal(value, label=labels[info.field_name])

    @field_validator(
        "planned_start",
        "planned_end",
        "actual_start",
        "actual_end",
        "closed_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance work order {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_WORK_ORDER_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance work order version must be positive.",
            code="MAINTENANCE_WORK_ORDER_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceWorkOrder":
        if (
            self.planned_start is not None
            and self.planned_end is not None
            and self.planned_end < self.planned_start
        ):
            raise ValidationError(
                "Planned end cannot be earlier than planned start.",
                code="MAINTENANCE_WORK_ORDER_PLANNED_RANGE_INVALID",
            )
        if (
            self.actual_start is not None
            and self.actual_end is not None
            and self.actual_end < self.actual_start
        ):
            raise ValidationError(
                "Actual end cannot be earlier than actual start.",
                code="MAINTENANCE_WORK_ORDER_ACTUAL_RANGE_INVALID",
            )
        if (
            self.actual_end is not None
            and self.closed_at is not None
            and self.closed_at < self.actual_end
        ):
            raise ValidationError(
                "Closed timestamp cannot be earlier than actual completion.",
                code="MAINTENANCE_WORK_ORDER_CLOSED_RANGE_INVALID",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_WORK_ORDER_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        site_id: str,
        work_order_code: str,
        work_order_type: MaintenanceWorkOrderType | str | None,
        source_type: str,
        source_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        title: str = "",
        description: str = "",
        priority: MaintenancePriority | str | None = None,
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


@validated_dataclass
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

    @field_validator("id", "organization_id", "work_order_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance work order task ID is required.",
                "MAINTENANCE_WORK_ORDER_TASK_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_WORK_ORDER_TASK_ORGANIZATION_REQUIRED",
            ),
            "work_order_id": (
                "Work order ID is required.",
                "MAINTENANCE_WORK_ORDER_TASK_WORK_ORDER_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator(
        "task_template_id",
        "assigned_employee_id",
        "assigned_team_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("task_name", mode="before")
    @classmethod
    def _validate_task_name(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Task name")

    @field_validator("description", "required_skill", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("estimated_minutes", "actual_minutes", mode="before")
    @classmethod
    def _validate_minutes(cls, value: object, info) -> int | None:
        labels = {
            "estimated_minutes": "Estimated minutes",
            "actual_minutes": "Actual minutes",
        }
        return normalize_optional_non_negative_int(value, label=labels[info.field_name])

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> MaintenanceWorkOrderTaskStatus:
        return normalize_work_order_task_status(value)

    @field_validator("sequence_no", mode="before")
    @classmethod
    def _validate_sequence_no(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Sequence number must be greater than zero.",
            code="MAINTENANCE_WORK_ORDER_TASK_SEQUENCE_INVALID",
        )

    @field_validator("completion_rule", mode="before")
    @classmethod
    def _validate_completion_rule(cls, value: object) -> MaintenanceTaskCompletionRule:
        return normalize_task_completion_rule(value)

    @field_validator("started_at", "completed_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance work order task {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_WORK_ORDER_TASK_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance work order task version must be positive.",
            code="MAINTENANCE_WORK_ORDER_TASK_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceWorkOrderTask":
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValidationError(
                "Task completion timestamp cannot be earlier than the start timestamp.",
                code="MAINTENANCE_WORK_ORDER_TASK_RANGE_INVALID",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_WORK_ORDER_TASK_UPDATED_RANGE_INVALID",
            )
        return self

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
        estimated_minutes: int | str | None = None,
        actual_minutes: int | str | None = None,
        required_skill: str = "",
        sequence_no: int | str = 1,
        is_mandatory: bool = True,
        completion_rule: MaintenanceTaskCompletionRule | str | None = None,
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


@validated_dataclass
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

    @field_validator("id", "organization_id", "work_order_task_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance work order task step ID is required.",
                "MAINTENANCE_WORK_ORDER_TASK_STEP_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_WORK_ORDER_TASK_STEP_ORGANIZATION_REQUIRED",
            ),
            "work_order_task_id": (
                "Work order task ID is required.",
                "MAINTENANCE_WORK_ORDER_TASK_STEP_TASK_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator(
        "source_step_template_id",
        "completed_by_user_id",
        "confirmed_by_user_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("step_number", mode="before")
    @classmethod
    def _validate_step_number(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Step number must be greater than zero.",
            code="MAINTENANCE_WORK_ORDER_TASK_STEP_NUMBER_INVALID",
        )

    @field_validator("instruction", mode="before")
    @classmethod
    def _validate_instruction(cls, value: object) -> str:
        return normalize_maintenance_name(value, label="Instruction")

    @field_validator(
        "expected_result",
        "hint_text",
        "measurement_value",
        "measurement_unit",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("hint_level", mode="before")
    @classmethod
    def _normalize_hint_level(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> MaintenanceWorkOrderTaskStepStatus:
        return normalize_work_order_task_step_status(value)

    @field_validator("completed_at", "confirmed_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance work order task step {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_WORK_ORDER_TASK_STEP_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance work order task step version must be positive.",
            code="MAINTENANCE_WORK_ORDER_TASK_STEP_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceWorkOrderTaskStep":
        if (
            self.completed_at is not None
            and self.confirmed_at is not None
            and self.confirmed_at < self.completed_at
        ):
            raise ValidationError(
                "Confirmation timestamp cannot be earlier than completion timestamp.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEP_CONFIRMATION_RANGE_INVALID",
            )
        if (
            self.requires_measurement
            and self.status == MaintenanceWorkOrderTaskStepStatus.DONE
            and not self.measurement_value
        ):
            raise ValidationError(
                "Measurement value is required before completing this step.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEP_MEASUREMENT_REQUIRED",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEP_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        work_order_task_id: str,
        source_step_template_id: str | None = None,
        step_number: int | str = 1,
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


@validated_dataclass
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
    procurement_status: MaintenanceMaterialProcurementStatus | None = None
    last_availability_status: str = ""
    last_missing_qty: Decimal | None = None
    linked_requisition_id: str | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", "work_order_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Maintenance material requirement ID is required.",
                "MAINTENANCE_MATERIAL_REQUIREMENT_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "MAINTENANCE_MATERIAL_REQUIREMENT_ORGANIZATION_REQUIRED",
            ),
            "work_order_id": (
                "Work order ID is required.",
                "MAINTENANCE_MATERIAL_REQUIREMENT_WORK_ORDER_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator(
        "stock_item_id",
        "preferred_storeroom_id",
        "linked_requisition_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("required_qty", mode="before")
    @classmethod
    def _validate_required_qty(cls, value: object) -> Decimal:
        return normalize_positive_decimal(value, label="Required quantity")

    @field_validator("issued_qty", mode="before")
    @classmethod
    def _validate_issued_qty(cls, value: object) -> Decimal:
        return normalize_optional_decimal(value, label="Issued quantity") or Decimal("0")

    @field_validator("required_uom", "last_availability_status", mode="before")
    @classmethod
    def _normalize_upper_text_fields(cls, value: object) -> str:
        return normalize_optional_upper_text(value)

    @field_validator("last_missing_qty", mode="before")
    @classmethod
    def _validate_last_missing_qty(cls, value: object) -> Decimal | None:
        return normalize_optional_decimal(value, label="Missing quantity")

    @field_validator("procurement_status", mode="before")
    @classmethod
    def _validate_procurement_status(
        cls,
        value: object,
    ) -> MaintenanceMaterialProcurementStatus | None:
        if value in (None, ""):
            return None
        return normalize_material_procurement_status(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Maintenance material requirement {info.field_name.replace('_', ' ')} is invalid.",
            code=f"MAINTENANCE_MATERIAL_REQUIREMENT_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Maintenance material requirement version must be positive.",
            code="MAINTENANCE_MATERIAL_REQUIREMENT_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "MaintenanceWorkOrderMaterialRequirement":
        object.__setattr__(
            self,
            "procurement_status",
            normalize_material_procurement_status(
                self.procurement_status,
                is_stock_item=self.is_stock_item,
            ),
        )
        if self.is_stock_item and not self.stock_item_id:
            raise ValidationError(
                "Stock item is required for stock-based maintenance material demand.",
                code="MAINTENANCE_MATERIAL_STOCK_ITEM_REQUIRED",
            )
        if self.is_stock_item and not self.preferred_storeroom_id:
            raise ValidationError(
                "Preferred storeroom is required for stock-based maintenance material demand.",
                code="MAINTENANCE_MATERIAL_STOREROOM_REQUIRED",
            )
        if not self.is_stock_item and not self.description:
            raise ValidationError(
                "Description is required for maintenance material demand.",
                code="MAINTENANCE_MATERIAL_DESCRIPTION_REQUIRED",
            )
        if not self.is_stock_item and not self.required_uom:
            raise ValidationError(
                "Required UOM is required for maintenance material demand.",
                code="MAINTENANCE_MATERIAL_REQUIRED_UOM_REQUIRED",
            )
        if self.issued_qty > self.required_qty:
            raise ValidationError(
                "Issued quantity cannot exceed required quantity.",
                code="MAINTENANCE_MATERIAL_ISSUED_QTY_EXCEEDS_REQUIRED",
            )
        if (
            self.updated_at is not None
            and self.created_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="MAINTENANCE_MATERIAL_REQUIREMENT_UPDATED_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        work_order_id: str,
        stock_item_id: str | None = None,
        description: str = "",
        required_qty: Decimal | int | float | str,
        issued_qty: Decimal | int | float | str = Decimal("0"),
        required_uom: str = "",
        is_stock_item: bool = True,
        preferred_storeroom_id: str | None = None,
        procurement_status: MaintenanceMaterialProcurementStatus | str | None = None,
        last_availability_status: str = "",
        last_missing_qty: Decimal | int | float | str | None = None,
        linked_requisition_id: str | None = None,
        notes: str = "",
    ) -> "MaintenanceWorkOrderMaterialRequirement":
        now = datetime.now(timezone.utc)
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
            procurement_status=procurement_status,
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
