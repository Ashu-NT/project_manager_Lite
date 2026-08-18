from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.modules.project_management.api.desktop import (
    AssignmentValidationDesktopDto,
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
    TaskAssignmentPlannedHoursCommand,
)

from .validation import optional_decimal, require_decimal, require_float, require_text

def create_assignment(desktop_api, payload: dict[str, Any]) -> None:
    command = TaskAssignmentCreateCommand(
        task_id=require_text(
            payload, "taskId", "Select a task before assigning resources."
        ),
        project_resource_id=require_text(
            payload, "projectResourceId", "Select a project resource to assign."
        ),
        allocation_percent=require_float(
            payload, "allocationPercent", "Allocation percent is required."
        ),
        allocated_planned_hours=optional_decimal(payload, "plannedHours") or Decimal("0"),
    )
    desktop_api.create_assignment(command)

def update_assignment_allocation(desktop_api, payload: dict[str, Any]) -> None:
    raw_version = payload.get("version")
    expected_version = (
        int(raw_version)
        if raw_version is not None and str(raw_version).strip() != ""
        else None
    )
    command = TaskAssignmentAllocationCommand(
        assignment_id=require_text(
            payload,
            "assignmentId",
            "Assignment ID is required for allocation updates.",
        ),
        allocation_percent=require_float(
            payload, "allocationPercent", "Allocation percent is required."
        ),
        expected_version=expected_version,
    )
    desktop_api.update_assignment_allocation(command)

def set_assignment_hours(desktop_api, payload: dict[str, Any]) -> None:
    command = TaskAssignmentHoursCommand(
        assignment_id=require_text(
            payload, "assignmentId", "Assignment ID is required for effort updates."
        ),
        hours_logged=require_decimal(
            payload, "hoursLogged", "Hours logged is required."
        ),
    )
    desktop_api.set_assignment_hours(command)

def update_assignment_planned_hours(desktop_api, payload: dict[str, Any]) -> None:
    command = TaskAssignmentPlannedHoursCommand(
        assignment_id=require_text(
            payload,
            "assignmentId",
            "Assignment ID is required for planned-hours updates.",
        ),
        allocated_planned_hours=require_decimal(
            payload, "plannedHours", "Planned work is required."
        ),
        expected_assignment_version=int(
            require_text(payload, "version", "Assignment version is required.")
        ),
        expected_project_resource_version=int(
            require_text(
                payload,
                "projectResourceVersion",
                "Project resource version is required.",
            )
        ),
    )
    desktop_api.update_assignment_planned_hours(command)

def delete_assignment(desktop_api, assignment_id: str) -> None:
    normalized_assignment_id = (assignment_id or "").strip()
    if not normalized_assignment_id:
        raise ValueError("Assignment ID is required to remove an assignment.")
    desktop_api.delete_assignment(normalized_assignment_id)

def accept_assignment(desktop_api, assignment_id: str) -> None:
    normalized_assignment_id = (assignment_id or "").strip()
    if not normalized_assignment_id:
        raise ValueError("Select an assignment before accepting it.")
    desktop_api.accept_assignment(normalized_assignment_id)

def decline_assignment(desktop_api, payload: dict[str, Any]) -> None:
    assignment_id = require_text(
        payload,
        "assignmentId",
        "Select an assignment before declining it.",
    )
    reason = require_text(
        payload,
        "reason",
        "Provide a reason for declining this assignment.",
    )
    desktop_api.decline_assignment(assignment_id, reason)

def preview_assignment(desktop_api, payload: dict[str, Any]) -> dict[str, object]:
    from src.core.modules.project_management.api.desktop.tasks import (
        AssignmentPreviewDesktopDto,
    )

    task_id = str(payload.get("taskId") or "").strip()
    project_resource_id = str(payload.get("projectResourceId") or "").strip()
    if not task_id or not project_resource_id:
        return {
            "ok": True,
            "overallocationPct": 0.0,
            "conflictProjects": [],
            "skillsMatched": True,
            "certsValid": True,
            "hasWarnings": False,
            "warningMessages": [],
            "isBlocked": False,
            "blockMessages": [],
        }
    dto: AssignmentPreviewDesktopDto = desktop_api.preview_assignment(
        task_id, project_resource_id
    )
    return {
        "ok": True,
        "overallocationPct": dto.overallocation_pct,
        "conflictProjects": list(dto.conflict_projects),
        "skillsMatched": dto.skills_matched,
        "certsValid": dto.certs_valid,
        "hasWarnings": dto.has_warnings,
        "warningMessages": list(dto.warning_messages),
        "isBlocked": dto.is_blocked,
        "blockMessages": list(dto.block_messages),
    }

def validate_assignment(desktop_api, payload: dict[str, Any]) -> dict[str, object]:
    task_id = str(payload.get("taskId") or "").strip()
    project_resource_id = str(payload.get("projectResourceId") or "").strip()
    if not task_id or not project_resource_id:
        return {
            "ok": True,
            "isValid": True,
            "canAssign": True,
            "requiresApproval": False,
            "isBlocked": False,
            "hasWarnings": False,
            "violationMessages": [],
            "warningMessages": [],
            "summary": "valid",
        }
    dto: AssignmentValidationDesktopDto = desktop_api.validate_assignment(
        task_id, project_resource_id
    )
    return {
        "ok": True,
        "isValid": dto.is_valid,
        "canAssign": dto.can_assign,
        "requiresApproval": dto.requires_approval,
        "isBlocked": dto.is_blocked,
        "hasWarnings": dto.has_warnings,
        "violationMessages": list(dto.violation_messages),
        "warningMessages": list(dto.warning_messages),
        "summary": dto.summary,
    }
