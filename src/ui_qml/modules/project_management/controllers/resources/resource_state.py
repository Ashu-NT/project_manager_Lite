from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "", "subtitle": "", "metrics": []}


def default_resources() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


def default_selected_resource() -> dict[str, object]:
    return {
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "",
        "fields": [],
        "state": {},
    }


def default_resource_inspector() -> dict[str, object]:
    return {
        "id": "",
        "title": "",
        "statusLabel": "",
        "fields": [],
        "state": {},
    }


def default_resource_availability() -> dict[str, object]:
    return {
        "resourceId": "",
        "startDate": "",
        "endDate": "",
        "fromDateLabel": "",
        "toDateLabel": "",
        "calendarSourceLabel": "",
        "capacityPercent": 0.0,
        "baseCapacityHours": 0.0,
        "effectiveCapacityHours": 0.0,
        "plannedCommitmentHours": 0.0,
        "allocatedPlannedHours": 0.0,
        "remainingCapacityHours": 0.0,
        "utilizationPercent": None,
        "utilizationLabel": "N/A",
        "overallocated": False,
        "conflictDays": 0,
        "projectCount": 0,
        "assignmentCount": 0,
        "days": [],
    }


def default_resource_context_page() -> dict[str, object]:
    return {"items": [], "total": 0, "page": 1, "pageSize": 25}


__all__ = [
    "default_overview",
    "default_resource_availability",
    "default_resource_context_page",
    "default_resource_inspector",
    "default_resources",
    "default_selected_resource",
]
