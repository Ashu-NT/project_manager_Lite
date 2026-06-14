from __future__ import annotations

from typing import Any


def record_activity(
    owner: object,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    module: str,
    workspace_id: str | None = None,
    message: str = "",
    details: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    parent_entity_id: str | None = None,
    type: str = "info",
    visibility: str = "workspace",
    icon: str | None = None,
    color: str | None = None,
) -> None:
    activity_service = getattr(owner, "_activity_service", None)
    if activity_service is None:
        return
    activity_service.record(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        module=module,
        workspace_id=workspace_id,
        human_message=message or action,
        details=details or {},
        context=context or {},
        parent_entity_id=parent_entity_id,
        type=type,
        visibility=visibility,
        icon=icon,
        color=color,
        commit=True,
    )


__all__ = ["record_activity"]
