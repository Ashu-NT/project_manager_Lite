from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.platform.api.desktop.master_data.employee.employee import (
    PlatformEmployeeDesktopApi,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.ui_qml.modules.project_management.presenters.common.activity_log_builder import (
    build_actor_lookup,
)
from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    icon_key_for_entity_type,
    serialize_activity_items,
    tone_for_action,
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
    *,
    user_api: PlatformUserDesktopApi | None = None,
    employee_api: PlatformEmployeeDesktopApi | None = None,
    **query,
) -> dict[str, object]:
    page = desktop_api.list_resource_activity_page(resource_id, **query)
    actor_lookup = build_actor_lookup(
        user_api.list_users() if user_api is not None else DesktopApiResult(ok=False),
        employee_api.list_employees() if employee_api is not None else None,
    )
    return {
        "items": serialize_activity_items(
            _to_activity_item(item, actor_lookup) for item in page.items
        ),
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort_key,
        "sortDirection": page.sort_direction,
    }


def _to_activity_item(item, actor_lookup: dict[str, str]) -> ActivityItemViewModel:
    activation_state = None
    if item.can_open_source:
        activation_state = {
            "sourceType": item.source_type,
            "sourceId": item.source_id or "",
            "projectId": item.project_id or "",
            "taskId": item.task_id or "",
        }
    return ActivityItemViewModel(
        id=item.id,
        title=item.summary,
        actor_display=actor_lookup.get(item.actor_id or "", "") or "System",
        occurred_at=item.occurred_at,
        occurred_at_label=item.occurred_at.strftime("%d %b %Y %H:%M") if item.occurred_at else "",
        icon_key=icon_key_for_entity_type(item.source_type),
        tone=tone_for_action(item.event_type),
        subject_display=item.source_type.replace("_", " ").title(),
        badge_label=_label(item.category),
        activation_state=activation_state,
    )


__all__ = [
    "build_resource_activity_page",
    "build_resource_assignments_page",
    "build_resource_projects_page",
]
