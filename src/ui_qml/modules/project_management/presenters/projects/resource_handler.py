from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementProjectsDesktopApi,
    ProjectResourceAssignCommand,
    ProjectResourceUpdateCommand,
)


def assign_resource_to_project(
    desktop_api: ProjectManagementProjectsDesktopApi,
    *,
    project_id: str,
    resource_id: str,
    planned_hours: float,
    hourly_rate: float | None,
) -> None:
    normalized_project_id = (project_id or "").strip()
    normalized_resource_id = (resource_id or "").strip()
    if not normalized_project_id or not normalized_resource_id:
        raise ValueError("Project and resource are required.")
    desktop_api.add_project_resource(
        ProjectResourceAssignCommand(
            project_id=normalized_project_id,
            resource_id=normalized_resource_id,
            planned_hours=max(0.0, planned_hours),
            hourly_rate=hourly_rate if hourly_rate and hourly_rate > 0 else None,
        )
    )


def update_project_resource(
    desktop_api: ProjectManagementProjectsDesktopApi,
    *,
    project_resource_id: str,
    planned_hours: float,
    hourly_rate: float | None,
    is_active: bool,
) -> None:
    normalized_id = (project_resource_id or "").strip()
    if not normalized_id:
        raise ValueError("Project resource ID is required.")
    desktop_api.update_project_resource(
        ProjectResourceUpdateCommand(
            project_resource_id=normalized_id,
            planned_hours=max(0.0, planned_hours),
            hourly_rate=hourly_rate if hourly_rate and hourly_rate > 0 else None,
            is_active=is_active,
        )
    )


def remove_project_resource(
    desktop_api: ProjectManagementProjectsDesktopApi,
    *,
    project_resource_id: str,
) -> None:
    normalized_id = (project_resource_id or "").strip()
    if not normalized_id:
        raise ValueError("Project resource ID is required.")
    desktop_api.remove_project_resource(normalized_id)
