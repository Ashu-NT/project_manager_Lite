"""Platform authorization and account-security view subscriptions."""

from src.core.platform.application.security.auth.event_handlers.view_invalidation import (
    build_account_security_view_invalidation_handler,
)
from src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation import (
    build_authorization_context_view_invalidation_handler,
    build_role_binding_view_invalidation_handler,
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
from src.core.shared.events.domain_event_subscriber import PostCommitEventSubscriber
from src.core.shared.events.view_invalidation import ViewInvalidationChannel


def register_role_binding_views(
    bus: PostCommitEventSubscriber,
    channel: ViewInvalidationChannel,
) -> None:
    handler = build_role_binding_view_invalidation_handler(channel)
    for role_binding_event_type in (RoleBindingAssigned, RoleBindingRevoked):
        bus.subscribe(role_binding_event_type, handler)


def register_account_and_authorization_views(
    bus: PostCommitEventSubscriber,
    channel: ViewInvalidationChannel,
) -> None:
    account_handler = build_account_security_view_invalidation_handler(channel)
    for account_event_type in (
        UserAccountCreated,
        UserAccountProfileUpdated,
        UserAccountStatusChanged,
        AccountLocked,
        AccountUnlocked,
        AuthenticationFailureRecorded,
        PasswordChanged,
        MfaStatusChanged,
        FederatedIdentityLinked,
        UserSessionPolicyChanged,
        UserSessionsRevoked,
    ):
        bus.subscribe(account_event_type, account_handler)

    authorization_handler = build_authorization_context_view_invalidation_handler(channel)
    for authorization_event_type in (
        CustomRoleCreated,
        CustomRoleUpdated,
        CustomRoleRetired,
        RolePolicyReconciled,
    ):
        bus.subscribe(authorization_event_type, authorization_handler)


__all__ = ["register_account_and_authorization_views", "register_role_binding_views"]
