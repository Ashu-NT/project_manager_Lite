from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "", "subtitle": "", "metrics": []}


def default_collection() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


def default_context() -> dict[str, object]:
    return {
        "projectOptions": [],
        "teamOptions": [],
        "periodOptions": [],
        "unreadOptions": [],
    }


def default_selected_item_detail() -> dict[str, object]:
    return {
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "state": {},
        "fields": [],
        "activity": default_collection(),
        "relatedItems": default_collection(),
        "audit": default_collection(),
    }


__all__ = [
    "default_overview",
    "default_collection",
    "default_context",
    "default_selected_item_detail",
]
