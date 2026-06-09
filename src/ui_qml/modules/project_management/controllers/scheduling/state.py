from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "", "subtitle": "", "metrics": []}


def default_collection() -> dict[str, object]:
    return {"title": "", "subtitle": "", "items": [], "emptyState": ""}


def default_calendar() -> dict[str, object]:
    return {
        "summaryText": "",
        "workingDays": [],
        "hoursPerDay": "8",
        "holidays": [],
        "emptyState": "",
    }


def default_baselines() -> dict[str, object]:
    return {
        "options": [],
        "selectedBaselineAId": "",
        "selectedBaselineBId": "",
        "includeUnchanged": False,
        "summaryText": "",
        "rows": [],
        "emptyState": "",
    }


def default_selected_activity() -> dict[str, object]:
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


def default_schedule_impact() -> dict[str, object]:
    return {
        "taskId": "",
        "affectedCount": 0,
        "maxProjectFinishShiftDays": 0,
        "requiresApproval": False,
        "newlyCriticalCount": 0,
        "noLongerCriticalCount": 0,
        "affectedTasks": [],
        "available": False,
    }


__all__ = [
    "default_overview",
    "default_collection",
    "default_calendar",
    "default_baselines",
    "default_selected_activity",
    "default_schedule_impact",
]
