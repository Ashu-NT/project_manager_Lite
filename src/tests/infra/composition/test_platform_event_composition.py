from src.core.platform.domain.approval.events import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequested,
)
from src.core.platform.domain.master_data.org.events import (
    OrganizationActivated,
    OrganizationArchived,
    OrganizationCreated,
    OrganizationDeactivated,
    OrganizationProfileUpdated,
)
from src.core.platform.domain.security.auth.events import (
    AccountLocked,
    AccountUnlocked,
    AuthenticationFailureRecorded,
    CustomRoleCreated,
    CustomRoleRetired,
    CustomRoleUpdated,
    FederatedIdentityLinked,
    MfaStatusChanged,
    PasswordChanged,
    RolePolicyReconciled,
    TenantMembershipProvisioned,
    UserAccountCreated,
    UserAccountProfileUpdated,
    UserAccountStatusChanged,
    UserSessionPolicyChanged,
    UserSessionsRevoked,
)
from src.core.platform.domain.security.authorization.roles.events import (
    RoleBindingAssigned,
    RoleBindingRevoked,
)
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


def test_platform_view_event_families_have_one_shared_handler(services):
    bus = services["project_service"]._uow_factory._post_commit_bus
    families = (
        (OrganizationCreated,),
        (
            OrganizationProfileUpdated, OrganizationActivated,
            OrganizationDeactivated, OrganizationArchived,
        ),
        (ModuleLicensed, ModuleLicenseRevoked, ModuleEnabled, ModuleDisabled, ModuleLifecycleTransitioned),
        (RoleBindingAssigned, RoleBindingRevoked),
        (
            TenantMembershipActivated, TenantMembershipSuspended,
            TenantMembershipReactivated, TenantMembershipRemoved, TenantMembershipProvisioned,
        ),
        (
            UserAccountCreated, UserAccountProfileUpdated, UserAccountStatusChanged,
            AccountLocked, AccountUnlocked, AuthenticationFailureRecorded,
            PasswordChanged, MfaStatusChanged, FederatedIdentityLinked,
            UserSessionPolicyChanged, UserSessionsRevoked,
        ),
        (CustomRoleCreated, CustomRoleUpdated, CustomRoleRetired, RolePolicyReconciled),
        (ApprovalRequested, ApprovalApproved, ApprovalRejected),
    )
    for family in families:
        handlers = [
            [
                handler for handler in bus._handlers[event_type]
                if handler.__module__.startswith("src.core.platform.application")
            ]
            for event_type in family
        ]
        assert all(len(entries) == 1 for entries in handlers)
        assert all(entries[0] is handlers[0][0] for entries in handlers)
