from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "", "subtitle": "", "metrics": []}


def default_collection() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


def default_detail() -> dict[str, object]:
    return {
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "",
        "fields": [],
        "linkedDocuments": [],
        "state": {},
    }
