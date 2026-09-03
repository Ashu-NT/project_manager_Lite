from __future__ import annotations

from src.core.platform.application.time_management.time.timesheet_events import (
    TimesheetPeriodStatusChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

TIMESHEET_CATEGORY = "timesheet"
TIMESHEET_WORKSPACE_SCOPE_CODE = "timesheet_workspace"
TIMESHEET_RESOURCE_SCOPE_CODE = "timesheet_resource"
TIMESHEET_PROJECT_SCOPE_CODE = "timesheet_project"
TIMESHEET_MODULE_CODE = "project_management"
TIMESHEET_RESOURCE_ENTITY_TYPE = "resource"
TIMESHEET_PROJECT_ENTITY_TYPE = "project"

_OrgTarget = tuple[str, str, str]
_ResourceTarget = tuple[str, str, str, str, str, str]


def _organization_scope_target(scope_code: str, scope: OrganizationScope) -> _OrgTarget:
    return (scope_code, scope.tenant_id, scope.organization_id)


def _resource_scope_target(scope_code: str, scope: ResourceScope) -> _ResourceTarget:
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def build_timesheet_view_invalidation_handler(channel: ViewInvalidationChannel):
    """One `TimesheetPeriodStatusChanged` legitimately produces up to three distinct hints --
    the org-wide review/personal workspace (any reviewer or team-scoped viewer needs to see it),
    the exact resource whose period changed (the resource inspector's assignments tab), and each
    project referenced by the period's own entries (the Task workspace, which blocks editing while
    a period is not OPEN/REJECTED). This is source-preserving, not an invented fan-out: the legacy
    `timesheet_periods_changed` signal reached the exact same three consumer families uniformly,
    just without any scoping at all."""

    current_correlation_id: list[str | None] = [None]
    notified_org_targets: set[_OrgTarget] = set()
    notified_resource_targets: set[_ResourceTarget] = set()

    def handle_timesheet_period_event(
        event: TimesheetPeriodStatusChanged,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_org_targets.clear()
            notified_resource_targets.clear()

        org_scope = OrganizationScope(event.tenant_id, event.organization_id)
        org_target = _organization_scope_target(TIMESHEET_WORKSPACE_SCOPE_CODE, org_scope)
        if org_target not in notified_org_targets:
            notified_org_targets.add(org_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=org_scope,
                    category=TIMESHEET_CATEGORY,
                    scope_code=TIMESHEET_WORKSPACE_SCOPE_CODE,
                    entity_type=TIMESHEET_RESOURCE_ENTITY_TYPE,
                    entity_id=event.resource_id,
                )
            )

        resource_scope = ResourceScope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            module_code=TIMESHEET_MODULE_CODE,
            entity_type=TIMESHEET_RESOURCE_ENTITY_TYPE,
            entity_id=event.resource_id,
        )
        resource_target = _resource_scope_target(TIMESHEET_RESOURCE_SCOPE_CODE, resource_scope)
        if resource_target not in notified_resource_targets:
            notified_resource_targets.add(resource_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=resource_scope,
                    category=TIMESHEET_CATEGORY,
                    scope_code=TIMESHEET_RESOURCE_SCOPE_CODE,
                    entity_type=TIMESHEET_RESOURCE_ENTITY_TYPE,
                    entity_id=event.resource_id,
                )
            )

        for project_id in event.project_ids:
            project_scope = ResourceScope(
                tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                module_code=TIMESHEET_MODULE_CODE,
                entity_type=TIMESHEET_PROJECT_ENTITY_TYPE,
                entity_id=project_id,
            )
            project_target = _resource_scope_target(TIMESHEET_PROJECT_SCOPE_CODE, project_scope)
            if project_target in notified_resource_targets:
                continue
            notified_resource_targets.add(project_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=project_scope,
                    category=TIMESHEET_CATEGORY,
                    scope_code=TIMESHEET_PROJECT_SCOPE_CODE,
                    entity_type=TIMESHEET_PROJECT_ENTITY_TYPE,
                    entity_id=project_id,
                )
            )

    return handle_timesheet_period_event


__all__ = [
    "build_timesheet_view_invalidation_handler",
    "TIMESHEET_CATEGORY",
    "TIMESHEET_WORKSPACE_SCOPE_CODE",
    "TIMESHEET_RESOURCE_SCOPE_CODE",
    "TIMESHEET_PROJECT_SCOPE_CODE",
    "TIMESHEET_MODULE_CODE",
    "TIMESHEET_RESOURCE_ENTITY_TYPE",
    "TIMESHEET_PROJECT_ENTITY_TYPE",
]
