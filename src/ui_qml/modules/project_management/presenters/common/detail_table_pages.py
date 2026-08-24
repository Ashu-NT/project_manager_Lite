from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def _date_label(value) -> str:
    if value in (None, ""):
        return "--"
    try:
        parsed = value if hasattr(value, "strftime") else datetime.fromisoformat(str(value))
        return parsed.strftime("%d %b %Y")
    except (TypeError, ValueError):
        return str(value)


def _hours(value) -> str:
    return f"{Decimal(str(value or 0)):,.1f} h"


def activity_page(page) -> dict[str, object]:
    rows = [{
        "id": item.id,
        "occurredAt": _date_label(item.occurred_at),
        "actorLabel": "Authorized user" if item.actor_id else "System",
        "eventLabel": item.action.replace("_", " ").replace(".", " / ").title(),
        "sourceLabel": item.entity_type.replace("_", " ").title(),
        "summary": item.summary,
        "state": {"action": item.action, "details": dict(item.details or {})},
    } for item in page.items]
    return {"items": rows, "total": page.filtered_total, "page": page.page,
            "pageSize": page.page_size, "sortKey": page.sort_key,
            "sortDirection": page.sort_direction}


def project_tasks_page(page) -> dict[str, object]:
    rows = [{
        "id": item.id, "wbsCode": item.wbs_code, "taskName": item.name,
        "statusLabel": item.status_label,
        "progressValue": {"value": float(item.percent_complete or 0) / 100.0,
                          "label": f"{float(item.percent_complete or 0):.0f}%"},
        "startDate": _date_label(item.start_date), "endDate": _date_label(item.end_date),
        "duration": f"{int(item.duration_days or 0)}d",
        "priority": str(item.priority or 0),
        "state": {"taskId": item.id, "isSummary": item.is_summary},
    } for item in page.items]
    return {"items": rows, "total": page.filtered_total, "page": page.page,
            "pageSize": page.page_size, "sortKey": page.sort_key,
            "sortDirection": page.sort_direction}


def project_resources_page(page) -> dict[str, object]:
    rows = [{
        "id": item.id, "resourceName": item.resource_name,
        "resourceCode": item.resource_code or "--", "role": item.role or "Team member",
        "plannedHours": _hours(item.planned_hours), "allocatedHours": _hours(item.allocated_hours),
        "actualHours": _hours(item.actual_hours), "remainingHours": _hours(item.remaining_hours),
        "statusLabel": "Active" if item.is_active else "Inactive",
        "state": {"projectResourceId": item.id, "resourceId": item.resource_id,
                  "plannedHours": item.planned_hours, "isActive": item.is_active,
                  "version": item.version},
    } for item in page.items]
    return {"items": rows, "total": page.filtered_total, "page": page.page,
            "pageSize": page.page_size, "sortKey": page.sort_key,
            "sortDirection": page.sort_direction}


def task_assignments_page(page) -> dict[str, object]:
    rows = [{
        "id": item.id, "resourceName": item.resource_name,
        "resourceCode": item.resource_code or "--", "role": item.role or "Team member",
        "allocationPercent": f"{float(item.allocation_percent or 0):.1f}%",
        "plannedHours": _hours(item.allocated_planned_hours),
        "actualHours": _hours(item.hours_logged),
        "remainingHours": _hours(Decimal(str(item.allocated_planned_hours or 0)) - Decimal(str(item.hours_logged or 0))),
        "responseStatus": item.response_status_label,
        "state": {"assignmentId": item.id, "resourceId": item.resource_id,
                  "projectResourceId": item.project_resource_id,
                  "allocationPercent": item.allocation_percent,
                  "allocatedPlannedHours": item.allocated_planned_hours,
                  "version": item.version, "canManage": item.can_manage,
                  "canAccept": item.can_accept, "canDecline": item.can_decline},
    } for item in page.items]
    return {"items": rows, "total": page.filtered_total, "page": page.page,
            "pageSize": page.page_size, "sortKey": page.sort_key,
            "sortDirection": page.sort_direction}


def task_dependencies_page(page) -> dict[str, object]:
    rows = [{
        "id": item.id, "direction": item.direction_label,
        "taskCode": item.linked_task_code or "--", "linkedTask": item.linked_task_name,
        "dependencyType": item.dependency_type_label,
        "lagDays": (f"+{item.lag_days}d" if item.lag_days > 0 else
                    f"{abs(item.lag_days)}d lead" if item.lag_days < 0 else "0d"),
        "startDate": _date_label(item.linked_task_start), "endDate": _date_label(item.linked_task_end),
        "statusLabel": item.linked_task_status.replace("_", " ").title(),
        "state": {"linkedTaskId": item.linked_task_id, "direction": item.direction,
                  "dependencyType": item.dependency_type, "lagDays": item.lag_days,
                  "version": item.version},
    } for item in page.items]
    return {"items": rows, "total": page.filtered_total,
            "predecessorTotal": page.predecessor_total, "successorTotal": page.successor_total,
            "page": page.page, "pageSize": page.page_size, "sortKey": page.sort_key,
            "sortDirection": page.sort_direction}


__all__ = ["activity_page", "project_resources_page", "project_tasks_page",
           "task_assignments_page", "task_dependencies_page"]
