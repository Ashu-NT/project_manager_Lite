from __future__ import annotations

from src.core.modules.project_management.application.financials.commitments.commitment_events import (
    CommitmentLineChanged,
    CommitmentMatchChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

COMMITMENT_CATEGORY = "commitment"
COMMITMENT_LIST_SCOPE_CODE = "commitment_list"
COMMITMENT_MODULE_CODE = "project_management"
COMMITMENT_PROJECT_ENTITY_TYPE = "project"

_ProjectTarget = tuple[str, str, str, str, str, str]

_CommitmentEvent = CommitmentLineChanged | CommitmentMatchChanged


def _project_scope_target(scope_code: str, scope: ResourceScope) -> _ProjectTarget:
    """Dedupe identity is the (scope_code, target/scope) identity."""
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
        module_code=COMMITMENT_MODULE_CODE,
        entity_type=COMMITMENT_PROJECT_ENTITY_TYPE,
        entity_id=project_id,
    )


def build_commitment_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def handle_commitment_event(
        event: _CommitmentEvent,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        scope = _project_scope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            project_id=event.project_id,
        )
        target = _project_scope_target(COMMITMENT_LIST_SCOPE_CODE, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=COMMITMENT_CATEGORY,
                scope_code=COMMITMENT_LIST_SCOPE_CODE,
                entity_type=COMMITMENT_PROJECT_ENTITY_TYPE,
                entity_id=event.project_id,
            )
        )

    return handle_commitment_event


__all__ = [
    "build_commitment_view_invalidation_handler",
    "COMMITMENT_CATEGORY",
    "COMMITMENT_LIST_SCOPE_CODE",
    "COMMITMENT_MODULE_CODE",
    "COMMITMENT_PROJECT_ENTITY_TYPE",
]
