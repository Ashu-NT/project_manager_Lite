from __future__ import annotations

from src.core.platform.notifications.domain_events import DomainChangeEvent


def should_refresh_collaboration_workspace(event: DomainChangeEvent) -> bool:
    return (
        event.scope_code == "project_management"
        and event.entity_type in {"project", "project_tasks", "task_collaboration"}
    ) or (event.category == "platform" and event.entity_type == "approval_request")


def should_refresh_resource_context(event: DomainChangeEvent) -> bool:
    return event.category in {"platform", "shared_master"} and event.entity_type in {"employee", "site", "department"}


def is_project_management_domain_event(event: DomainChangeEvent, *entity_types: str) -> bool:
    return event.scope_code == "project_management" and event.entity_type in set(entity_types)


__all__ = [
    "should_refresh_collaboration_workspace",
    "should_refresh_resource_context",
    "is_project_management_domain_event",
]
