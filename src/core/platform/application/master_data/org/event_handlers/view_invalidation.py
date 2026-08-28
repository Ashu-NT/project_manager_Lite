"""ADR-005 Section 12 (P5A): `OrganizationCreated` -> `ViewInvalidationHint` post-commit reaction.

Maps the `OrganizationCreated` business fact onto the two stale-read targets
`platform_p5_event_discovery.md`'s Event -> Invalidation Matrix (Section 9) documents: the
tenant-wide organization list, and the created organization's own details view. One business
event legitimately produces two hints (ADR-005 Section 3a's multi-hint rule) -- never a single
`TenantScope`-only hint, since the details view is genuinely organization-scoped, not tenant-wide.

Transport-independent: no Qt, no QML. Routing is delegated entirely to `ScopeFilter.matches(...)`
via the P2 `ViewInvalidationChannel` -- this module never reimplements tenant/organization
matching itself. The P6 Qt adapter consumes `ViewInvalidationHint`, never this event directly.
"""

from __future__ import annotations

from src.core.platform.domain.master_data.org.events import (
    OrganizationCreated,
    OrganizationDisabled,
    OrganizationEnabled,
    OrganizationProfileUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    TenantScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

ORGANIZATION_CATEGORY = "organization"
ORGANIZATION_LIST_SCOPE_CODE = "organization_list"
ORGANIZATION_DETAILS_SCOPE_CODE = "organization_details"


def build_organization_created_view_invalidation_handler(channel: ViewInvalidationChannel):
    """Returns a `PostCommitEventHandler[OrganizationCreated]` bound to `channel`, for explicit
    composition-root registration (`post_commit_bus.subscribe(OrganizationCreated, handler)`)."""

    def handle_organization_created(event: OrganizationCreated, context: DomainEventContext) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=TenantScope(event.tenant_id),
                category=ORGANIZATION_CATEGORY,
                scope_code=ORGANIZATION_LIST_SCOPE_CODE,
                entity_type="organization",
                entity_id=None,
            )
        )
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=ORGANIZATION_CATEGORY,
                scope_code=ORGANIZATION_DETAILS_SCOPE_CODE,
                entity_type="organization",
                entity_id=event.organization_id,
            )
        )

    return handle_organization_created


def build_organization_profile_view_invalidation_handler(channel: ViewInvalidationChannel):

    def handle_organization_profile_event(
        event: OrganizationProfileUpdated | OrganizationEnabled | OrganizationDisabled,
        context: DomainEventContext,
    ) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=TenantScope(event.tenant_id),
                category=ORGANIZATION_CATEGORY,
                scope_code=ORGANIZATION_LIST_SCOPE_CODE,
                entity_type="organization",
                entity_id=None,
            )
        )

    return handle_organization_profile_event


__all__ = [
    "build_organization_created_view_invalidation_handler",
    "build_organization_profile_view_invalidation_handler",
    "ORGANIZATION_CATEGORY",
    "ORGANIZATION_LIST_SCOPE_CODE",
    "ORGANIZATION_DETAILS_SCOPE_CODE",
]
