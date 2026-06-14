from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectCreateCommand,
    ProjectManagementProjectsDesktopApi,
    ProjectUpdateCommand,
)

from .validation import (
    optional_date,
    optional_float,
    optional_int,
    optional_text,
    require_text,
)

def suggest_code(
    desktop_api: ProjectManagementProjectsDesktopApi,
    payload: dict[str, Any],
) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    existing = {
        str(getattr(row, "code", "") or "").upper()
        for row in desktop_api.list_projects()
    }
    name = optional_text(payload, "name")
    return CodeGenerator().generate(
        "project",
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )

def create_project(
    desktop_api: ProjectManagementProjectsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = ProjectCreateCommand(
        name=require_text(payload, "name", "Project name is required."),
        code=optional_text(payload, "projectCode"),
        description=optional_text(payload, "description"),
        status=optional_text(payload, "status") or "PLANNED",
        client_name=optional_text(payload, "clientName"),
        client_contact=optional_text(payload, "clientContact"),
        planned_budget=optional_float(payload, "plannedBudget"),
        currency=optional_text(payload, "currency"),
        start_date=optional_date(payload, "startDate"),
        end_date=optional_date(payload, "endDate"),
        site_id=optional_text(payload, "siteId"),
    )
    desktop_api.create_project(command)

def update_project(
    desktop_api: ProjectManagementProjectsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = ProjectUpdateCommand(
        project_id=require_text(payload, "projectId", "Project ID is required for updates."),
        name=require_text(payload, "name", "Project name is required."),
        code=optional_text(payload, "projectCode"),
        description=optional_text(payload, "description"),
        status=optional_text(payload, "status") or "PLANNED",
        client_name=optional_text(payload, "clientName"),
        client_contact=optional_text(payload, "clientContact"),
        planned_budget=optional_float(payload, "plannedBudget"),
        currency=optional_text(payload, "currency"),
        start_date=optional_date(payload, "startDate"),
        end_date=optional_date(payload, "endDate"),
        site_id=optional_text(payload, "siteId"),
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.update_project(command)

def set_project_status(
    desktop_api: ProjectManagementProjectsDesktopApi,
    project_id: str,
    status: str,
) -> None:
    normalized_project_id = (project_id or "").strip()
    normalized_status = (status or "").strip()
    if not normalized_project_id:
        raise ValueError("Project ID is required to change status.")
    if not normalized_status:
        raise ValueError("Choose a project status before saving.")
    desktop_api.set_project_status(normalized_project_id, normalized_status)

def delete_project(
    desktop_api: ProjectManagementProjectsDesktopApi,
    project_id: str,
) -> None:
    normalized_id = (project_id or "").strip()
    if not normalized_id:
        raise ValueError("Project ID is required to delete a project.")
    desktop_api.delete_project(normalized_id)
