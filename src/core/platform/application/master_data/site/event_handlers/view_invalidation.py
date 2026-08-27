from __future__ import annotations

from src.core.platform.domain.master_data.site.events import (
    SiteCreated,
    SiteDisabled,
    SiteEnabled,
    SiteProfileUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

SITE_CATEGORY = "site"
SITE_LIST_SCOPE_CODE = "site_list"


def build_site_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    def handle_site_list_event(
        event: SiteCreated | SiteProfileUpdated | SiteEnabled | SiteDisabled,
        context: DomainEventContext,
    ) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=SITE_CATEGORY,
                scope_code=SITE_LIST_SCOPE_CODE,
                entity_type="site",
                entity_id=None,
            )
        )

    return handle_site_list_event


__all__ = [
    "build_site_list_view_invalidation_handler",
    "SITE_CATEGORY",
    "SITE_LIST_SCOPE_CODE",
]
