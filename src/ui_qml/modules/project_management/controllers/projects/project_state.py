from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "", "subtitle": "", "metrics": []}


def default_projects() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


def default_selected_project() -> dict[str, object]:
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


def default_lazy_section(title: str, label: str) -> dict[str, object]:
    return {
        "title": title,
        "subtitle": "",
        "emptyState": f"Open this section to load project {label}.",
        "items": [],
    }


__all__ = [
    "default_lazy_section",
    "default_overview",
    "default_projects",
    "default_selected_project",
]
