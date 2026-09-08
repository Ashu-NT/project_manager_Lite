from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass(frozen=True, slots=True, kw_only=True)
class UserAccountCreated:
    user_id: str
    tenant_id: str | None
    account_type: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class UserAccountProfileUpdated:
    user_id: str
    tenant_id: str | None
    changed_fields: tuple[str, ...]
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class UserAccountStatusChanged:
    user_id: str
    tenant_id: str | None
    is_active: bool
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountLocked:
    user_id: str
    tenant_id: str | None
    locked_until: datetime
    failed_attempts: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountUnlocked:
    user_id: str
    tenant_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthenticationFailureRecorded:
    user_id: str
    tenant_id: str | None
    failed_attempts: int
    occurred_at: datetime


class PasswordChangeType(str, Enum):
    CHANGED = "changed"
    FORCE_RESET_REQUIRED = "force_reset_required"
    RESET = "reset"


@dataclass(frozen=True, slots=True, kw_only=True)
class PasswordChanged:
    user_id: str
    tenant_id: str | None
    change_type: PasswordChangeType
    occurred_at: datetime


class MfaChangeType(str, Enum):
    PROVISIONED = "provisioned"
    ENABLED = "enabled"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True, kw_only=True)
class MfaStatusChanged:
    user_id: str
    tenant_id: str | None
    change_type: MfaChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedIdentityLinked:
    user_id: str
    tenant_id: str | None
    identity_provider: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class UserSessionPolicyChanged:
    user_id: str
    tenant_id: str | None
    session_timeout_minutes_override: int | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class UserSessionsRevoked:
    user_id: str
    tenant_id: str | None
    scope: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CustomRoleCreated:
    role_id: str
    tenant_id: str
    policy_version: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CustomRoleUpdated:
    role_id: str
    tenant_id: str
    policy_version: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CustomRoleRetired:
    role_id: str
    tenant_id: str
    policy_version: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RolePolicyReconciled:
    policy_name: str
    from_version: int
    to_version: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantMembershipProvisioned:
    """A genuinely different creation path from `TenantMembershipActivated` (which is
    anchored specifically to the invite -> accept aggregate transition, per
    `TenantMembershipService._accept_membership`'s own docstring: "never emitted for
    reinvite/issue_invitation"). Registration/bootstrap create an already-active
    `UserTenantMembership` directly via `UserTenantMembership.create(...)` -- a separate,
    first-class constructor, not an invitation that was ever extended or accepted. Reusing
    `TenantMembershipActivated` here would misrepresent a transition that never happened;
    this event states the true fact instead: system/admin-direct provisioning, no invitation
    flow involved."""

    membership_id: str
    tenant_id: str
    user_id: str
    occurred_at: datetime


__all__ = [
    "AccountLocked",
    "AccountUnlocked",
    "AuthenticationFailureRecorded",
    "CustomRoleCreated",
    "CustomRoleRetired",
    "CustomRoleUpdated",
    "FederatedIdentityLinked",
    "MfaChangeType",
    "MfaStatusChanged",
    "PasswordChangeType",
    "PasswordChanged",
    "RolePolicyReconciled",
    "TenantMembershipProvisioned",
    "UserAccountCreated",
    "UserAccountProfileUpdated",
    "UserAccountStatusChanged",
    "UserSessionPolicyChanged",
    "UserSessionsRevoked",
]
