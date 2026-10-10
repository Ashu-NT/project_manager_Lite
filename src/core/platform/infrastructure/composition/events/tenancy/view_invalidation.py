"""Platform organization, entitlement, and membership view subscriptions."""

from src.core.platform.application.master_data.org.event_handlers.view_invalidation import (
    build_organization_created_view_invalidation_handler,
    build_organization_profile_view_invalidation_handler,
)
from src.core.platform.application.tenant.modules.event_handlers.view_invalidation import (
    build_module_entitlement_view_invalidation_handler,
)
from src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation import (
    build_tenant_membership_view_invalidation_handler,
)
from src.core.platform.domain.master_data.org.events import (
    OrganizationActivated,
    OrganizationArchived,
    OrganizationCreated,
    OrganizationDeactivated,
    OrganizationProfileUpdated,
)
from src.core.platform.domain.security.auth.events import TenantMembershipProvisioned
from src.core.platform.domain.tenant.modules.events import (
    ModuleDisabled,
    ModuleEnabled,
    ModuleLicensed,
    ModuleLicenseRevoked,
    ModuleLifecycleTransitioned,
)
from src.core.platform.domain.tenant.tenancy.events import (
    TenantMembershipActivated,
    TenantMembershipReactivated,
    TenantMembershipRemoved,
    TenantMembershipSuspended,
)
from src.core.shared.events.domain_event_subscriber import PostCommitEventSubscriber
from src.core.shared.events.view_invalidation import ViewInvalidationChannel


def register_organization_and_entitlement_views(
    bus: PostCommitEventSubscriber,
    channel: ViewInvalidationChannel,
) -> None:
    bus.subscribe(
        OrganizationCreated,
        build_organization_created_view_invalidation_handler(channel),
    )
    profile_handler = build_organization_profile_view_invalidation_handler(channel)
    for organization_event_type in (
        OrganizationProfileUpdated,
        OrganizationActivated,
        OrganizationDeactivated,
        OrganizationArchived,
    ):
        bus.subscribe(organization_event_type, profile_handler)

    entitlement_handler = build_module_entitlement_view_invalidation_handler(channel)
    for entitlement_event_type in (
        ModuleLicensed,
        ModuleLicenseRevoked,
        ModuleEnabled,
        ModuleDisabled,
        ModuleLifecycleTransitioned,
    ):
        bus.subscribe(entitlement_event_type, entitlement_handler)


def register_membership_views(
    bus: PostCommitEventSubscriber,
    channel: ViewInvalidationChannel,
) -> None:
    membership_handler = build_tenant_membership_view_invalidation_handler(channel)
    for membership_event_type in (
        TenantMembershipActivated,
        TenantMembershipSuspended,
        TenantMembershipReactivated,
        TenantMembershipRemoved,
        TenantMembershipProvisioned,
    ):
        bus.subscribe(membership_event_type, membership_handler)


__all__ = ["register_membership_views", "register_organization_and_entitlement_views"]
