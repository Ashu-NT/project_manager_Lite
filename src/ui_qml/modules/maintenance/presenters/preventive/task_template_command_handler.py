from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceTaskTemplateCreateCommand,
    MaintenanceTaskTemplateUpdateCommand,
)

from .validation import (
    optional_bool,
    optional_int,
    optional_optional_bool,
    optional_text,
    require_int,
    require_text,
)


def create_task_template(desktop_api, payload: dict) -> None:
    desktop_api.create_task_template(
        MaintenanceTaskTemplateCreateCommand(
            task_template_code=require_text(
                payload,
                "taskTemplateCode",
                "Task template code is required.",
            ),
            name=require_text(payload, "name", "Task template name is required."),
            description=optional_text(payload, "description") or "",
            maintenance_type=optional_text(payload, "maintenanceType") or "PREVENTIVE",
            revision_no=require_int(
                payload,
                "revisionNo",
                "Revision number is required.",
            ),
            template_status=optional_text(payload, "templateStatus") or "DRAFT",
            estimated_minutes=optional_int(payload, "estimatedMinutes"),
            required_skill=optional_text(payload, "requiredSkill") or "",
            requires_shutdown=optional_bool(payload, "requiresShutdown", False),
            requires_permit=optional_bool(payload, "requiresPermit", False),
            is_active=optional_bool(payload, "isActive", True),
            notes=optional_text(payload, "notes") or "",
        )
    )


def update_task_template(desktop_api, payload: dict) -> None:
    desktop_api.update_task_template(
        MaintenanceTaskTemplateUpdateCommand(
            task_template_id=require_text(
                payload,
                "taskTemplateId",
                "Task template ID is required.",
            ),
            task_template_code=optional_text(payload, "taskTemplateCode"),
            name=optional_text(payload, "name"),
            description=optional_text(payload, "description"),
            maintenance_type=optional_text(payload, "maintenanceType"),
            revision_no=optional_int(payload, "revisionNo"),
            template_status=optional_text(payload, "templateStatus"),
            estimated_minutes=optional_int(payload, "estimatedMinutes"),
            required_skill=optional_text(payload, "requiredSkill"),
            requires_shutdown=optional_optional_bool(payload, "requiresShutdown"),
            requires_permit=optional_optional_bool(payload, "requiresPermit"),
            is_active=optional_optional_bool(payload, "isActive"),
            notes=optional_text(payload, "notes"),
            expected_version=require_int(
                payload,
                "expectedVersion",
                "Expected version is required before saving.",
            ),
        )
    )


def toggle_task_template_active(
    desktop_api,
    *,
    task_template_id: str,
    is_active: bool,
    expected_version: int,
) -> None:
    desktop_api.update_task_template(
        MaintenanceTaskTemplateUpdateCommand(
            task_template_id=task_template_id,
            is_active=is_active,
            expected_version=expected_version,
        )
    )
