from __future__ import annotations

from datetime import date, datetime

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
)


def _label(value: object) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _hours(value: object) -> str:
    try:
        return f"{float(str(value or 0)):,.1f} h"
    except (TypeError, ValueError):
        return "0.0 h"


def _percent(value: object) -> str:
    try:
        return f"{float(str(value or 0)):,.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _date_label(value: str) -> str:
    try:
        return date.fromisoformat(value).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return "-"


def _date_range(start: str, end: str) -> str:
    if not start and not end:
        return "Unscheduled"
    return f"{_date_label(start)} - {_date_label(end)}"


def build_resource_projects_page(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    **query,
) -> dict[str, object]:
    page = desktop_api.list_resource_projects_page(resource_id, **query)
    return {
        "items": [
            {
                "id": item.id,
                "projectName": item.project_name,
                "projectCode": item.project_code or "-",
                "statusLabel": _label(item.project_status),
                "plannedHours": _hours(item.planned_hours),
                "activeLabel": "Active" if item.is_active else "Inactive",
                "dateRange": _date_range(item.start_date, item.end_date),
                "state": {
                    "resourceId": item.resource_id,
                    "projectId": item.project_id,
                    "projectResourceId": item.id,
                    "plannedHours": item.planned_hours,
                    "isActive": item.is_active,
                    "version": item.version,
                    "canOpenProject": item.can_open_project,
                },
            }
            for item in page.items
        ],
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort_key,
        "sortDirection": page.sort_direction,
    }


def build_resource_assignments_page(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    **query,
) -> dict[str, object]:
    page = desktop_api.list_resource_assignments_page(resource_id, **query)
    return {
        "items": [
            {
                "id": item.id,
                "taskName": item.task_name,
                "taskCode": item.task_code or "-",
                "projectName": item.project_name,
                "scheduledStart": _date_range(item.scheduled_start, item.scheduled_finish),
                "plannedHours": _hours(item.allocated_planned_hours),
                "allocationPercent": _percent(item.allocation_percent),
                "actualHours": _hours(item.actual_hours),
                "statusLabel": _label(item.task_status),
                "responseStatus": _label(item.response_status),
                "state": {
                    "resourceId": item.resource_id,
                    "projectId": item.project_id,
                    "taskId": item.task_id,
                    "assignmentId": item.id,
                    "projectResourceId": item.project_resource_id or "",
                    "allocatedPlannedHours": item.allocated_planned_hours,
                    "actualHours": item.actual_hours,
                    "actualHoursSource": item.actual_hours_source,
                    "allocationPercent": item.allocation_percent,
                    "version": item.version,
                    "canOpenProject": item.can_open_project,
                    "canOpenTask": item.can_open_task,
                },
            }
            for item in page.items
        ],
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort_key,
        "sortDirection": page.sort_direction,
    }


def build_resource_activity_page(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    **query,
) -> dict[str, object]:
    page = desktop_api.list_resource_activity_page(resource_id, **query)
    rows = []
    for item in page.items:
        try:
            occurred = datetime.fromisoformat(item.occurred_at).strftime("%d %b %Y %H:%M")
        except (TypeError, ValueError):
            occurred = item.occurred_at
        rows.append(
            {
                "id": item.id,
                "title": item.summary,
                "metaText": f"{item.actor_label} | {occurred}",
                "statusLabel": _label(item.category),
                "routeId": item.source_type if item.can_open_source else "",
                "state": {
                    "resourceId": item.resource_id,
                    "eventType": item.event_type,
                    "sourceType": item.source_type,
                    "sourceId": item.source_id or "",
                    "projectId": item.project_id or "",
                    "taskId": item.task_id or "",
                    "canOpenSource": item.can_open_source,
                },
            }
        )
    return {
        "items": rows,
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort_key,
        "sortDirection": page.sort_direction,
    }


__all__ = [
    "build_resource_activity_page",
    "build_resource_assignments_page",
    "build_resource_projects_page",
]
