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


def default_resource_availability() -> dict[str, object]:
    return {
        "resourceId": "",
        "peakLoadPercent": 0.0,
        "averageLoadPercent": 0.0,
        "overloadedDays": 0,
        "availableDays": 0,
        "isAvailable": True,
        "fromDateLabel": "",
        "toDateLabel": "",
        "days": [],
    }


__all__ = [
    "default_overview",
    "default_resource_availability",
    "default_resources",
    "default_selected_resource",
]
