from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceTaskStepTemplateCreateCommand,
    MaintenanceTaskStepTemplateUpdateCommand,
)

from .validation import (
    optional_bool,
    optional_int,
    optional_optional_bool,
    optional_text,
    require_int,
    require_text,
)


def create_task_step(desktop_api, payload: dict) -> None:
    desktop_api.create_task_step_template(
        MaintenanceTaskStepTemplateCreateCommand(
            task_template_id=require_text(
                payload,
                "taskTemplateId",
                "Choose a task template before saving a step.",
            ),
            step_number=require_int(
                payload,
                "stepNumber",
                "Step number is required.",
            ),
            sort_order=optional_int(payload, "sortOrder"),
            instruction=require_text(
                payload,
                "instruction",
                "Instruction is required.",
            ),
            expected_result=optional_text(payload, "expectedResult") or "",
            hint_level=optional_text(payload, "hintLevel") or "",
            hint_text=optional_text(payload, "hintText") or "",
            requires_confirmation=optional_bool(payload, "requiresConfirmation", False),
            requires_measurement=optional_bool(payload, "requiresMeasurement", False),
            requires_photo=optional_bool(payload, "requiresPhoto", False),
            measurement_unit=optional_text(payload, "measurementUnit") or "",
            is_active=optional_bool(payload, "isActive", True),
            notes=optional_text(payload, "notes") or "",
        )
    )


def update_task_step(desktop_api, payload: dict) -> None:
    desktop_api.update_task_step_template(
        MaintenanceTaskStepTemplateUpdateCommand(
            task_step_template_id=require_text(
                payload,
                "taskStepTemplateId",
                "Task step template ID is required.",
            ),
            step_number=optional_int(payload, "stepNumber"),
            sort_order=optional_int(payload, "sortOrder"),
            instruction=optional_text(payload, "instruction"),
            expected_result=optional_text(payload, "expectedResult"),
            hint_level=optional_text(payload, "hintLevel"),
            hint_text=optional_text(payload, "hintText"),
            requires_confirmation=optional_optional_bool(payload, "requiresConfirmation"),
            requires_measurement=optional_optional_bool(payload, "requiresMeasurement"),
            requires_photo=optional_optional_bool(payload, "requiresPhoto"),
            measurement_unit=optional_text(payload, "measurementUnit"),
            is_active=optional_optional_bool(payload, "isActive"),
            notes=optional_text(payload, "notes"),
            expected_version=require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
    )


def toggle_task_step_active(
    desktop_api,
    *,
    task_step_template_id: str,
    is_active: bool,
    expected_version: int,
) -> None:
    desktop_api.update_task_step_template(
        MaintenanceTaskStepTemplateUpdateCommand(
            task_step_template_id=task_step_template_id,
            is_active=is_active,
            expected_version=expected_version,
        )
    )
