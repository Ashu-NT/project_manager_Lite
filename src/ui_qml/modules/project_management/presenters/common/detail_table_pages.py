from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskAssignmentReadPage,
    TaskDependencyReadPage,
    TaskWorkspaceReadPage,
)


def _date_label(value) -> str:
    if value in (None, ""):
        return "--"
    try:
        parsed = (
            value if hasattr(value, "strftime") else datetime.fromisoformat(str(value))
        )
        return parsed.strftime("%d %b %Y")
    except (TypeError, ValueError):
        return str(value)


def _hours(value) -> str:
    return f"{Decimal(str(value or 0)):,.1f} h"


def project_tasks_page(page: TaskWorkspaceReadPage) -> dict[str, object]:
    rows = [
        {
            "id": item.id,
            "wbsCode": item.wbs_code,
            "taskName": item.name,
            "statusLabel": item.status.replace("_", " ").title(),
            "progressValue": {
                "value": float(item.percent_complete or 0) / 100.0,
                "label": f"{float(item.percent_complete or 0):.0f}%",
            },
            "startDate": _date_label(item.start_date),
            "endDate": _date_label(item.end_date),
            "duration": f"{int(item.duration_days or 0)}d",
            "priority": str(item.priority or 0),
            "state": {"taskId": item.id, "isSummary": item.is_summary},
        }
        for item in page.items
    ]
    return {
        "items": rows,
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort.key,
        "sortDirection": page.sort.direction.value,
    }


def project_resources_page(page) -> dict[str, object]:
    rows = [
        {
            "id": item.project_resource_id,
            "title": item.resource_name,
            "resourceName": item.resource_name,
            "resourceCode": item.resource_code or "--",
            "role": item.role or "Team member",
            "plannedHours": _hours(item.planned_hours),
            "allocatedHours": _hours(item.allocated_hours),
            "actualHours": _hours(item.actual_hours),
            "remainingHours": _hours(item.remaining_hours),
            "statusLabel": "Active" if item.is_active else "Inactive",
            "state": {
                "projectResourceId": item.project_resource_id,
                "resourceId": item.resource_id,
                "plannedHours": str(item.planned_hours),
                "isActive": item.is_active,
                "version": item.version,
            },
        }
        for item in page.items
    ]
    return {
        "items": rows,
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort.key,
        "sortDirection": page.sort.direction.value,
    }


def task_assignments_page(
    page: TaskAssignmentReadPage, *, task_id: str
) -> dict[str, object]:
    rows = [
        {
            "id": item.assignment_id,
            "title": item.resource_name,
            "subtitle": "Resource assignment",
            "statusLabel": item.response_status.title(),
            "resourceName": item.resource_name,
            "resourceCode": item.resource_code or "--",
            "role": item.role or "Team member",
            "allocationPercent": f"{float(item.allocation_percent or 0):.1f}%",
            "plannedHours": _hours(item.planned_hours),
            "actualHours": _hours(item.actual_hours),
            "remainingHours": _hours(
                Decimal(str(item.planned_hours or 0))
                - Decimal(str(item.actual_hours or 0))
            ),
            "responseStatus": item.response_status.title(),
            "state": {
                "assignmentId": item.assignment_id,
                "resourceId": item.resource_id,
                "taskId": task_id,
                "resourceName": item.resource_name,
                "projectResourceId": item.project_resource_id,
                "allocationPercent": float(item.allocation_percent),
                "allocatedPlannedHours": str(item.planned_hours),
                "plannedHours": str(item.planned_hours),
                "hoursLogged": str(item.actual_hours),
                "responseStatus": item.response_status,
                "responseStatusLabel": item.response_status.title(),
                "remainingPlannedLabel": _hours(
                    Decimal(str(item.planned_hours or 0))
                    - Decimal(str(item.actual_hours or 0))
                ),
                "version": item.version,
                "canManage": item.can_manage,
                "canAccept": item.can_accept,
                "canDecline": item.can_decline,
            },
        }
        for item in page.items
    ]
    return {
        "items": rows,
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort.key,
        "sortDirection": page.sort.direction.value,
    }


def task_dependencies_page(page: TaskDependencyReadPage) -> dict[str, object]:
    type_labels = {
        "FS": "Finish to Start",
        "FF": "Finish to Finish",
        "SS": "Start to Start",
        "SF": "Start to Finish",
    }
    rows = [
        {
            "id": item.dependency_id,
            "title": item.linked_task_name,
            "direction": item.direction.title(),
            "taskCode": item.linked_task_code or "--",
            "linkedTask": item.linked_task_name,
            "dependencyType": type_labels.get(
                item.dependency_type, item.dependency_type
            ),
            "lagDays": (
                f"+{item.lag_days}d"
                if item.lag_days > 0
                else f"{abs(item.lag_days)}d lead"
                if item.lag_days < 0
                else "0d"
            ),
            "startDate": _date_label(item.linked_task_start),
            "endDate": _date_label(item.linked_task_end),
            "statusLabel": item.linked_task_status.replace("_", " ").title(),
            "state": {
                "linkedTaskId": item.linked_task_id,
                "direction": item.direction,
                "dependencyType": item.dependency_type,
                "lagDays": item.lag_days,
                "version": item.version,
            },
        }
        for item in page.items
    ]
    return {
        "items": rows,
        "total": page.filtered_total,
        "predecessorTotal": page.predecessor_total,
        "successorTotal": page.successor_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort.key,
        "sortDirection": page.sort.direction.value,
    }


__all__ = [
    "project_resources_page",
    "project_tasks_page",
    "task_assignments_page",
    "task_dependencies_page",
]
