from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "", "subtitle": "", "metrics": []}


def default_collection() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "items": []}


def default_summary() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "fields": []}


__all__ = ["default_overview", "default_collection", "default_summary"]
