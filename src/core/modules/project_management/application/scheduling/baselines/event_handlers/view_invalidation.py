from __future__ import annotations

from src.core.modules.project_management.application.scheduling.baselines.baseline_events import (
    ProjectBaselineApproved,
    ProjectBaselineCreated,
    ProjectBaselineDeleted,
    ProjectBaselineRejected,
    ProjectBaselineSubmitted,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

BASELINE_CATEGORY = "baseline"
BASELINE_PROJECT_SCOPE_CODE = "project_baseline"
BASELINE_MODULE_CODE = "project_management"
BASELINE_PROJECT_ENTITY_TYPE = "project"

_ProjectTarget = tuple[str, str, str, str, str, str]


def _project_scope_target(scope_code: str, scope: ResourceScope) -> _ProjectTarget:
    """Dedupe identity is the (scope_code, target/scope) identity -- never a raw event field"""
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def _project_scope(*, tenant_id: str, organization_id: str, project_id: str) -> ResourceScope:
    return ResourceScope(
        tenant_id=tenant_id,
        organization_id=organization_id,
        module_code=BASELINE_MODULE_CODE,
        entity_type=BASELINE_PROJECT_ENTITY_TYPE,
        entity_id=project_id,
    )


def build_baseline_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def _notify(*, tenant_id: str, organization_id: str, project_id: str) -> None:
        scope = _project_scope(
            tenant_id=tenant_id, organization_id=organization_id, project_id=project_id
        )
        target = _project_scope_target(BASELINE_PROJECT_SCOPE_CODE, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=BASELINE_CATEGORY,
                scope_code=BASELINE_PROJECT_SCOPE_CODE,
                entity_type=BASELINE_PROJECT_ENTITY_TYPE,
                entity_id=project_id,
            )
        )

    def handle_baseline_event(
        event: (
            ProjectBaselineCreated
            | ProjectBaselineSubmitted
            | ProjectBaselineApproved
            | ProjectBaselineRejected
            | ProjectBaselineDeleted
        ),
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        _notify(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            project_id=event.project_id,
        )

    return handle_baseline_event


__all__ = [
    "build_baseline_view_invalidation_handler",
    "BASELINE_CATEGORY",
    "BASELINE_PROJECT_SCOPE_CODE",
    "BASELINE_MODULE_CODE",
    "BASELINE_PROJECT_ENTITY_TYPE",
]
