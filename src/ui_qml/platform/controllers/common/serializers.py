from __future__ import annotations

from typing import Any


def serialize_workspace_overview(overview) -> dict[str, object]:
    return {
        "title": overview.title,
        "subtitle": overview.subtitle,
        "statusLabel": overview.status_label,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in overview.metrics
        ],
        "sections": [
            {
                "title": section.title,
                "emptyState": section.empty_state,
                "rows": [
                    {
                        "label": row.label,
                        "value": row.value,
                        "supportingText": row.supporting_text,
                    }
                    for row in section.rows
                ],
            }
            for section in overview.sections
        ],
    }


def serialize_action_list(list_view_model) -> dict[str, object]:
    return {
        "title": list_view_model.title,
        "subtitle": list_view_model.subtitle,
        "emptyState": list_view_model.empty_state,
        "items": [serialize_action_item(item) for item in list_view_model.items],
    }


def serialize_action_item(item) -> dict[str, object]:
    return {
        "id": item.id,
        "title": item.title,
        "statusLabel": item.status_label,
        "subtitle": item.subtitle,
        "supportingText": item.supporting_text,
        "metaText": item.meta_text,
        "canPrimaryAction": item.can_primary_action,
        "canSecondaryAction": item.can_secondary_action,
        "canTertiaryAction": item.can_tertiary_action,
        "state": dict(item.state),
    }


def serialize_operation_result(
    result,
    *,
    success_message: str,
) -> dict[str, object]:
    if result is not None and getattr(result, "ok", False):
        return {
            "ok": True,
            "category": "",
            "code": "",
            "message": success_message,
        }
    error = getattr(result, "error", None) if result is not None else None
    return {
        "ok": False,
        "category": getattr(error, "category", "domain"),
        "code": getattr(error, "code", "operation_failed"),
        "message": getattr(error, "message", "The platform QML action did not complete."),
    }


__all__ = [
    "serialize_action_item",
    "serialize_action_list",
    "serialize_operation_result",
    "serialize_workspace_overview",
]
