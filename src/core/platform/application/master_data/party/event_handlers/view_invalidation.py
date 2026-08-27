from __future__ import annotations

from src.core.platform.domain.master_data.party.events import (
    PartyCreated,
    PartyProfileUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

PARTY_CATEGORY = "party"
PARTY_LIST_SCOPE_CODE = "party_list"


def build_party_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    def handle_party_list_event(
        event: PartyCreated | PartyProfileUpdated,
        context: DomainEventContext,
    ) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=PARTY_CATEGORY,
                scope_code=PARTY_LIST_SCOPE_CODE,
                entity_type="party",
                entity_id=None,
            )
        )

    return handle_party_list_event


__all__ = [
    "build_party_list_view_invalidation_handler",
    "PARTY_CATEGORY",
    "PARTY_LIST_SCOPE_CODE",
]
