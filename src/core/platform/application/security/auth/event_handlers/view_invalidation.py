from __future__ import annotations

from src.core.platform.domain.security.auth.events import (
    AccountLocked,
    AccountUnlocked,
    AuthenticationFailureRecorded,
    FederatedIdentityLinked,
    MfaStatusChanged,
    PasswordChanged,
    UserAccountCreated,
    UserAccountProfileUpdated,
    UserAccountStatusChanged,
    UserSessionPolicyChanged,
    UserSessionsRevoked,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    PlatformScope,
    TenantScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

ACCOUNT_SECURITY_CATEGORY = "account_security"
ACCOUNT_SECURITY_SCOPE_CODE = "account_security"

_AccountSecurityEvent = (
    UserAccountCreated
    | UserAccountProfileUpdated
    | UserAccountStatusChanged
    | AccountLocked
    | AccountUnlocked
    | AuthenticationFailureRecorded
    | PasswordChanged
    | MfaStatusChanged
    | FederatedIdentityLinked
    | UserSessionPolicyChanged
    | UserSessionsRevoked
)


def build_account_security_view_invalidation_handler(channel: ViewInvalidationChannel):
    """One `PostCommitEventHandler` bound to `channel`, reused for explicit composition-root
    registration against every `UserAccount`-owned durable fact. `account_security` is per-user
    security posture (locked/active/failed-attempts/MFA-state/password-changed-at/session-policy)
    -- it never carries authorization-context facts (Membership/RoleBinding/Role/RolePolicy),
    which map to the separate `authorization_context` category instead."""

    def handle_account_security_event(
        event: _AccountSecurityEvent,
        context: DomainEventContext,
    ) -> None:
        tenant_id = getattr(event, "tenant_id", None)
        scope = TenantScope(tenant_id) if tenant_id else PlatformScope()
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=ACCOUNT_SECURITY_CATEGORY,
                scope_code=ACCOUNT_SECURITY_SCOPE_CODE,
                entity_type="user",
                entity_id=event.user_id,
            )
        )

    return handle_account_security_event


__all__ = [
    "ACCOUNT_SECURITY_CATEGORY",
    "ACCOUNT_SECURITY_SCOPE_CODE",
    "build_account_security_view_invalidation_handler",
]
