from __future__ import annotations

from src.core.modules.project_management.application.financials.rate_cards.rate_card_events import (
    RateCardCreated,
    RateCardDeactivated,
    RateCardLineAdded,
    RateCardLineDeactivated,
    RateCardLineUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

RATE_CARD_CATEGORY = "rate_card"
RATE_CARD_LIST_SCOPE_CODE = "rate_card_list"
RATE_CARD_DETAIL_SCOPE_CODE = "rate_card_detail"
RATE_CARD_MODULE_CODE = "project_management"
RATE_CARD_ENTITY_TYPE = "rate_card"
RATE_CARD_PROJECT_ENTITY_TYPE = "project"

_OrgTarget = tuple[str, str, str]
_DetailTarget = tuple[str, str, str, str, str, str]


def _org_scope_target(scope_code: str, scope: OrganizationScope) -> _OrgTarget:
    return (scope_code, scope.tenant_id, scope.organization_id)


def _detail_scope_target(scope_code: str, scope: ResourceScope) -> _DetailTarget:
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def build_rate_card_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_org_targets: set[_OrgTarget] = set()
    notified_detail_targets: set[_DetailTarget] = set()

    def _notify_list(
        *, tenant_id: str, organization_id: str, rate_card_id: str, project_id: str | None
    ) -> None:
        if project_id is None:
            scope: OrganizationScope | ResourceScope = OrganizationScope(tenant_id, organization_id)
            target = _org_scope_target(RATE_CARD_LIST_SCOPE_CODE, scope)
            if target in notified_org_targets:
                return
            notified_org_targets.add(target)
            hint_entity_id = rate_card_id
        else:
            scope = ResourceScope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                module_code=RATE_CARD_MODULE_CODE,
                entity_type=RATE_CARD_PROJECT_ENTITY_TYPE,
                entity_id=project_id,
            )
            target = _detail_scope_target(RATE_CARD_LIST_SCOPE_CODE, scope)
            if target in notified_detail_targets:
                return
            notified_detail_targets.add(target)
            hint_entity_id = project_id
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=RATE_CARD_CATEGORY,
                scope_code=RATE_CARD_LIST_SCOPE_CODE,
                entity_type=(
                    RATE_CARD_ENTITY_TYPE if project_id is None else RATE_CARD_PROJECT_ENTITY_TYPE
                ),
                entity_id=hint_entity_id,
            )
        )

    def _notify_detail(*, tenant_id: str, organization_id: str, rate_card_id: str) -> None:
        scope = ResourceScope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            module_code=RATE_CARD_MODULE_CODE,
            entity_type=RATE_CARD_ENTITY_TYPE,
            entity_id=rate_card_id,
        )
        target = _detail_scope_target(RATE_CARD_DETAIL_SCOPE_CODE, scope)
        if target in notified_detail_targets:
            return
        notified_detail_targets.add(target)
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=RATE_CARD_CATEGORY,
                scope_code=RATE_CARD_DETAIL_SCOPE_CODE,
                entity_type=RATE_CARD_ENTITY_TYPE,
                entity_id=rate_card_id,
            )
        )

    def handle_rate_card_event(
        event: (
            RateCardCreated
            | RateCardDeactivated
            | RateCardLineAdded
            | RateCardLineUpdated
            | RateCardLineDeactivated
        ),
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_org_targets.clear()
            notified_detail_targets.clear()

        if isinstance(event, RateCardCreated):
            _notify_list(
                tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                rate_card_id=event.rate_card_id,
                project_id=event.project_id,
            )
        elif isinstance(event, RateCardDeactivated):
            _notify_list(
                tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                rate_card_id=event.rate_card_id,
                project_id=event.project_id,
            )
            _notify_detail(
                tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                rate_card_id=event.rate_card_id,
            )
        else:
            _notify_detail(
                tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                rate_card_id=event.rate_card_id,
            )

    return handle_rate_card_event


__all__ = [
    "build_rate_card_view_invalidation_handler",
    "RATE_CARD_CATEGORY",
    "RATE_CARD_LIST_SCOPE_CODE",
    "RATE_CARD_DETAIL_SCOPE_CODE",
    "RATE_CARD_MODULE_CODE",
    "RATE_CARD_ENTITY_TYPE",
    "RATE_CARD_PROJECT_ENTITY_TYPE",
]
