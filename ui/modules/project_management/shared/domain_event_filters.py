from __future__ import annotations

from core.platform.notifications.domain_events import DomainChangeEvent


def should_refresh_collaboration_workspace(event: DomainChangeEvent) -> bool:
    return (
        event.scope_code == "project_management"
        and event.entity_type in {"project", "project_tasks", "task_collaboration"}
    ) or (event.category == "platform" and event.entity_type == "approval_request")


def should_refresh_resource_context(event: DomainChangeEvent) -> bool:
    return event.category in {"platform", "shared_master"} and event.entity_type in {"employee", "site", "department"}


__all__ = [
    "should_refresh_collaboration_workspace",
    "should_refresh_resource_context",
]
