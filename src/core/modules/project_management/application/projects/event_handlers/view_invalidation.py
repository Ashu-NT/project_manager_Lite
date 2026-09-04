from __future__ import annotations

from src.core.modules.project_management.application.projects.project_events import (
    ProjectCreated,
    ProjectProfileUpdated,
    ProjectRemoved,
    ProjectStatusChanged,
)
from src.core.modules.project_management.application.resources.project_resource_events import (
    ProjectResourceAssignmentChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

PROJECT_CATEGORY = "project"
PROJECT_LIST_SCOPE_CODE = "project_list"
PROJECT_DETAIL_SCOPE_CODE = "project_detail"
PROJECT_MODULE_CODE = "project_management"
PROJECT_ENTITY_TYPE = "project"

_ProjectEvent = (
    ProjectCreated
    | ProjectProfileUpdated
    | ProjectStatusChanged
    | ProjectRemoved
    | ProjectResourceAssignmentChanged
)

_OrgTarget = tuple[str, str, str]
_ProjectTarget = tuple[str, str, str, str, str, str]


def _organization_scope_target(scope_code: str, scope: OrganizationScope) -> _OrgTarget:
    return (scope_code, scope.tenant_id, scope.organization_id)


def _project_scope_target(scope_code: str, scope: ResourceScope) -> _ProjectTarget:
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def build_project_view_invalidation_handler(channel: ViewInvalidationChannel):
    """`ProjectCreated`/`ProjectProfileUpdated`/`ProjectStatusChanged`/`ProjectRemoved` all stale
    the organization-wide Project collection/selector target; the latter three additionally stale
    the exact Project's own detail target (a not-yet-created Project has no existing detail view
    to stale -- `ProjectCreated` maps to the list/selector target only, per the brief's own §34).
    `ProjectResourceAssignmentChanged` (a `resources`-module fact, not a Project field change)
    maps to the detail target only -- it never affects the Project list/selector."""

    current_correlation_id: list[str | None] = [None]
    notified_org_targets: set[_OrgTarget] = set()
    notified_project_targets: set[_ProjectTarget] = set()

    def handle_project_event(
        event: _ProjectEvent,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_org_targets.clear()
            notified_project_targets.clear()

        if not isinstance(event, ProjectResourceAssignmentChanged):
            org_scope = OrganizationScope(event.tenant_id, event.organization_id)
            org_target = _organization_scope_target(PROJECT_LIST_SCOPE_CODE, org_scope)
            if org_target not in notified_org_targets:
                notified_org_targets.add(org_target)
                channel.notify(
                    ViewInvalidationHint(
                        scope=org_scope,
                        category=PROJECT_CATEGORY,
                        scope_code=PROJECT_LIST_SCOPE_CODE,
                        entity_type=PROJECT_ENTITY_TYPE,
                        entity_id=event.project_id,
                    )
                )

        if isinstance(event, ProjectCreated):
            return

        project_scope = ResourceScope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            module_code=PROJECT_MODULE_CODE,
            entity_type=PROJECT_ENTITY_TYPE,
            entity_id=event.project_id,
        )
        project_target = _project_scope_target(PROJECT_DETAIL_SCOPE_CODE, project_scope)
        if project_target not in notified_project_targets:
            notified_project_targets.add(project_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=project_scope,
                    category=PROJECT_CATEGORY,
                    scope_code=PROJECT_DETAIL_SCOPE_CODE,
                    entity_type=PROJECT_ENTITY_TYPE,
                    entity_id=event.project_id,
                )
            )

    return handle_project_event


__all__ = [
    "build_project_view_invalidation_handler",
    "PROJECT_CATEGORY",
    "PROJECT_LIST_SCOPE_CODE",
    "PROJECT_DETAIL_SCOPE_CODE",
    "PROJECT_MODULE_CODE",
    "PROJECT_ENTITY_TYPE",
]
