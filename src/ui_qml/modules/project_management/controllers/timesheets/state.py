from __future__ import annotations


def default_overview() -> dict[str, object]:
    return {"title": "Review Queue", "subtitle": "", "metrics": []}


def default_review_queue() -> dict[str, object]:
    return {"title": "Review Queue", "subtitle": "", "emptyState": "", "items": []}


def default_review_detail() -> dict[str, object]:
    return {"title": "", "subtitle": "", "emptyState": "", "fields": [], "state": {}}


__all__ = ["default_overview", "default_review_detail", "default_review_queue"]
