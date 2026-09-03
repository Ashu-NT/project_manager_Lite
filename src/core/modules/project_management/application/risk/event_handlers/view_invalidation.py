from __future__ import annotations

from src.core.modules.project_management.application.risk.register_events import (
    RegisterEntryChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

REGISTER_CATEGORY = "register"
REGISTER_WORKSPACE_SCOPE_CODE = "register_workspace"
REGISTER_PROJECT_SCOPE_CODE = "register_project"
REGISTER_MODULE_CODE = "project_management"
REGISTER_PROJECT_ENTITY_TYPE = "project"

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


def build_register_view_invalidation_handler(channel: ViewInvalidationChannel):
    current_correlation_id: list[str | None] = [None]
    notified_org_targets: set[_OrgTarget] = set()
    notified_project_targets: set[_ProjectTarget] = set()

    def handle_register_entry_event(
        event: RegisterEntryChanged,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_org_targets.clear()
            notified_project_targets.clear()

        org_scope = OrganizationScope(event.tenant_id, event.organization_id)
        org_target = _organization_scope_target(REGISTER_WORKSPACE_SCOPE_CODE, org_scope)
        if org_target not in notified_org_targets:
            notified_org_targets.add(org_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=org_scope,
                    category=REGISTER_CATEGORY,
                    scope_code=REGISTER_WORKSPACE_SCOPE_CODE,
                    entity_type=REGISTER_PROJECT_ENTITY_TYPE,
                    entity_id=event.project_id,
                )
            )

        project_scope = ResourceScope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            module_code=REGISTER_MODULE_CODE,
            entity_type=REGISTER_PROJECT_ENTITY_TYPE,
            entity_id=event.project_id,
        )
        project_target = _project_scope_target(REGISTER_PROJECT_SCOPE_CODE, project_scope)
        if project_target not in notified_project_targets:
            notified_project_targets.add(project_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=project_scope,
                    category=REGISTER_CATEGORY,
                    scope_code=REGISTER_PROJECT_SCOPE_CODE,
                    entity_type=REGISTER_PROJECT_ENTITY_TYPE,
                    entity_id=event.project_id,
                )
            )

    return handle_register_entry_event


__all__ = [
    "build_register_view_invalidation_handler",
    "REGISTER_CATEGORY",
    "REGISTER_WORKSPACE_SCOPE_CODE",
    "REGISTER_PROJECT_SCOPE_CODE",
    "REGISTER_MODULE_CODE",
    "REGISTER_PROJECT_ENTITY_TYPE",
]
