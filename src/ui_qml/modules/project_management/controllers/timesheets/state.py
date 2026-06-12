from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "", "subtitle": "", "metrics": []}


def default_assignment_summary() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "fields": [], "state": {}}


def default_entries() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


def default_selected_entry() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "fields": [], "state": {}}


def default_review_queue() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


def default_review_detail() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "fields": [], "state": {}}


__all__ = [
    "default_assignment_summary",
    "default_entries",
    "default_overview",
    "default_review_detail",
    "default_review_queue",
    "default_selected_entry",
]
