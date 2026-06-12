from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "", "subtitle": "", "metrics": []}


def default_entries() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


def default_selected_entry() -> dict[str, object]:
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


def default_urgent_entries() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


__all__ = [
    "default_entries",
    "default_overview",
    "default_selected_entry",
    "default_urgent_entries",
]
