from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import logging
import secrets

from src.core.platform.contract.persistence.tenant_membership_unit_of_work import (
    TenantMembershipUnitOfWork,
    TenantMembershipUnitOfWorkFactory,
)
from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    authorization_denied,
    require_permission,
)
from src.core.platform.application.security.authorization.roles.role_binding_mutation_participant import (
    OrganizationOwnerResolver,
    create_role_binding_using,
    resolve_domain_scope_for_binding,
    revoke_role_binding_using,
)
from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    RoleBindingTenantScope,
)
from src.core.platform.domain.security.auth import (
    UserAccount,
    UserSessionContext,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.application.events.notifications.notification_service import NotificationService
from src.core.platform.domain.tenant.tenancy import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_INVITED,
    MEMBERSHIP_STATUS_REMOVED,
    MEMBERSHIP_STATUS_SUSPENDED,
    TenantMembershipActivated,
    TenantMembershipReactivated,
    TenantMembershipRemoved,
    TenantMembershipSuspended,
    UserTenantMembership,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.time.clock import Clock

logger = logging.getLogger(__name__)

_DEFAULT_INVITATION_ROLE = "viewer"
_PLATFORM_ROLE_NAMES = frozenset({"admin", "support_admin"})
_MINIMUM_INVITATION_TOKEN_LENGTH = 32
_MAXIMUM_INVITATION_LIFETIME = timedelta(days=30)


@dataclass(frozen=True)
class IssuedTenantInvitation:
    membership: UserTenantMembership
    token: str


class TenantMembershipService:
    """Authorized orchestration for tenant membership lifecycle changes.

    P5D-1: converged onto a canonical, fresh-session `TenantMembershipUnitOfWork` -- one
    business operation, one transaction owner, no shared process-lifetime Session and no
    inline commit()/rollback(). The two RoleBinding mutations that are genuine membership-
    lifecycle facts (the default-role grant on acceptance, the cascade revoke on removal) reuse
    the SAME canonical identity/no-op/audit/event mechanics `RoleGovernanceService` uses --
    the transaction-agnostic `role_binding_mutation_participant` module -- atomically within
    this service's own UoW. This is never a nested `RoleGovernanceService` call and never a
    second transaction. Deliberately does NOT apply interactive-admin delegation/SoD policy to
    either mutation: a self-service acceptance and a membership-removal cascade are
    system/lifecycle operations, not an admin delegating a role to someone else, so the
    delegation-namespace and permission-snapshot checks `RoleGovernanceService.assign_role`
    enforces for an interactive admin grant do not apply here.

    `suspend_member`/`reactivate_member` never touch RoleBinding rows -- confirmed by the P5D-1
    audit, not assumed: they only transition the membership's own status and (suspend only)
    revoke the target's affected AuthSessions. Neither emits a RoleBinding event.

    P5D-2: each of the four non-trivial aggregate transition methods this service actually
    invokes -- `accept_invitation()`, `suspend()`, `reactivate()`, `remove()` -- now has this
    service record exactly one corresponding fact (`TenantMembershipActivated`/`Suspended`/
    `Reactivated`/`Removed`) via `uow.record_event(...)`, atomically with that same transition,
    inside the SAME outer UoW. `issue_invitation`/`reinvite` (still `invited`) and
    `revoke_invitation` (a distinct invitation-lifecycle fact, not a membership-removal fact --
    see `revoke_invitation`'s own comment for the evidence) deliberately record none. Recording
    is this service's responsibility alone: `UserTenantMembership` stays a plain aggregate that
    owns its own state invariants and does not implement `RecordsDomainEvents` -- one recording
    responsibility, not two.

    P5D-2A: the membership event is recorded immediately after its own aggregate transition
    succeeds -- BEFORE the consequential RoleBinding mutation that follows it in the same
    command (`_ensure_default_role_bindings` on acceptance, the cascade revoke on removal) --
    so the committed event order mirrors actual business-transition order
    (`TenantMembershipActivated` then `RoleBindingAssigned`; `TenantMembershipRemoved` then
    `RoleBindingRevoked`), not merely wherever `record_event()` happened to be convenient near
    `commit()`. This is safe because the canonical UoW never publishes anything until
    `uow.commit()` succeeds, so recording early carries no rollback-safety cost.
    """

    def __init__(
        self,
        *,
        uow_factory: TenantMembershipUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
        notification_service: NotificationService,
        organization_owner_resolvers: dict[str, OrganizationOwnerResolver],
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._notification_service = notification_service
        self._organization_owner_resolvers = organization_owner_resolvers

    def _new_context(self) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id())

    # -- commands --------------------------------------------------------------------------

    def issue_invitation(
        self,
        target_user_id: str,
        *,
        expires_at: datetime,
    ) -> IssuedTenantInvitation:
        with self._uow_factory.create(context=self._new_context()) as uow:
            actor, tenant_id = self._require_tenant_administrator(
                uow, operation_label="invite a tenant member"
            )
            target = self._require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="invite",
                require_active=True,
                require_invitation_safe_roles=True,
            )
            self._require_default_invitation_role(uow.roles, tenant_id)
            now = self._clock.now()
            normalized_expires_at = self._validate_invitation_expiry(
                expires_at,
                issued_at=now,
            )
            token = secrets.token_urlsafe(32)
            token_hash = self.hash_invitation_token(token)
            existing = uow.memberships.get(target.id, tenant_id)

            if existing is None:
                membership = UserTenantMembership.invite(
                    target.id,
                    tenant_id,
                    invited_by_user_id=actor.user_id,
                    expires_at=normalized_expires_at,
                    invitation_token_hash=token_hash,
                    invited_at=now,
                )
                old_status = None
                persist = uow.memberships.add
            elif existing.status in {
                MEMBERSHIP_STATUS_INVITED,
                MEMBERSHIP_STATUS_REMOVED,
            }:
                old_status = existing.status
                membership = existing.reinvite(
                    invited_by_user_id=actor.user_id,
                    expires_at=normalized_expires_at,
                    invitation_token_hash=token_hash,
                    invited_at=now,
                )
                persist = uow.memberships.update
            elif existing.status == MEMBERSHIP_STATUS_SUSPENDED:
                raise BusinessRuleError(
                    "Suspended memberships must be explicitly reactivated.",
                    code="TENANT_MEMBERSHIP_REACTIVATION_REQUIRED",
                )
            else:
                raise BusinessRuleError(
                    "The user is already an active tenant member.",
                    code="TENANT_MEMBERSHIP_ALREADY_ACTIVE",
                )

            persist(membership)
            self._record_membership_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                membership=membership,
                action="tenant.membership.invitation_issued",
                operation="create",
                old_status=old_status,
                new_status=MEMBERSHIP_STATUS_INVITED,
                metadata={
                    "target_user_id": target.id,
                    "expires_at": membership.invitation_expires_at.isoformat(),
                },
            )
            uow.commit()
        self._notify_invitation_issued(target.id, tenant_id=tenant_id, membership=membership)
        return IssuedTenantInvitation(membership=membership, token=token)

    def list_my_pending_invitations(self) -> list[UserTenantMembership]:
        actor = self._require_authenticated_principal()
        with self._uow_factory.create(context=self._new_context()) as uow:
            pending = [
                membership
                for membership in uow.memberships.list_memberships_for_user(actor.user_id)
                if membership.status == MEMBERSHIP_STATUS_INVITED
                and not membership.invitation_is_expired()
            ]
            uow.commit()
        return pending

    def accept_invitation(self, token: str) -> UserTenantMembership:
        """Accept via the raw one-time token (out-of-band delivery, e.g. a future emailed link)."""
        actor = self._require_authenticated_principal()
        token_hash = self.hash_invitation_token(token)
        with self._uow_factory.create(context=self._new_context()) as uow:
            membership = uow.memberships.get_by_invitation_token_hash(token_hash)
            if (
                membership is None
                or membership.status != MEMBERSHIP_STATUS_INVITED
                or not hmac.compare_digest(
                    membership.invitation_token_hash or "",
                    token_hash,
                )
            ):
                authorization_denied(
                    self._user_session,
                    message="The tenant invitation is invalid or no longer available.",
                    code="TENANT_INVITATION_INVALID",
                    operation_label="accept a tenant invitation",
                    operation="authorization.invitation.denied",
                )
            if membership.user_id != actor.user_id:
                authorization_denied(
                    self._user_session,
                    message="The tenant invitation belongs to a different user.",
                    code="TENANT_INVITATION_TARGET_MISMATCH",
                    operation_label="accept a tenant invitation",
                    target_scope_type="user",
                    target_scope_id=membership.user_id,
                    operation="authorization.membership.denied",
                )
            accepted = self._accept_membership(uow, membership, actor=actor)
        domain_events.auth_changed.emit(accepted.user_id)
        return accepted

    def accept_invitation_for_tenant(self, tenant_id: str) -> UserTenantMembership:
        """Accept the caller's own pending invitation for a tenant, surfaced via
        `list_my_pending_invitations`/in-app notification. No bearer token is involved:
        the caller is already an authenticated principal, and the membership lookup is
        keyed by that principal's own user id, not a shared secret."""
        actor = self._require_authenticated_principal()
        normalized_tenant_id = str(tenant_id or "").strip()
        with self._uow_factory.create(context=self._new_context()) as uow:
            membership = self._require_membership(uow.memberships, actor.user_id, normalized_tenant_id)
            if (
                membership.status != MEMBERSHIP_STATUS_INVITED
                or membership.invitation_is_expired()
            ):
                authorization_denied(
                    self._user_session,
                    message="The tenant invitation is invalid or no longer available.",
                    code="TENANT_INVITATION_INVALID",
                    operation_label="accept a tenant invitation",
                    operation="authorization.invitation.denied",
                )
            accepted = self._accept_membership(uow, membership, actor=actor)
        domain_events.auth_changed.emit(accepted.user_id)
        return accepted

    def _accept_membership(
        self,
        uow: TenantMembershipUnitOfWork,
        membership: UserTenantMembership,
        *,
        actor,
    ) -> UserTenantMembership:
        target = self._require_active_user(uow.users, membership.user_id)
        self._require_invitation_safe_roles(uow.role_bindings, uow.roles, target)
        self._require_active_tenant(uow.tenants, membership.tenant_id)
        accepted = membership.accept_invitation()
        uow.memberships.update(accepted)
        # P5D-2A: recorded immediately after the membership transition itself -- the ACTUAL
        # business-fact order is "membership becomes active" first, "a default role is granted
        # as a consequence" second (`_ensure_default_role_bindings` runs strictly after this
        # point in the code, never before). Recording here, before that call, makes the
        # committed event order mirror real transition order rather than merely mirroring
        # where the audit entry happens to be written. Safe because the canonical UoW never
        # publishes anything until `uow.commit()` succeeds -- an early `record_event()` call is
        # observationally identical to a late one for rollback purposes. Never emitted for
        # `reinvite`/`issue_invitation`: `accept_invitation()` (the aggregate method this event
        # anchors to) only ever fires on the invited -> active transition, regardless of how
        # many times this membership was previously removed and reinvited.
        uow.record_event(
            TenantMembershipActivated(
                membership_id=accepted.id,
                tenant_id=accepted.tenant_id,
                user_id=accepted.user_id,
                occurred_at=self._clock.now(),
            )
        )
        self._ensure_default_role_bindings(
            uow,
            target,
            tenant_id=accepted.tenant_id,
            actor=actor,
        )
        self._record_membership_audit(
            uow.audit,
            actor=actor,
            tenant_id=accepted.tenant_id,
            membership=accepted,
            action="tenant.membership.invitation_accepted",
            operation="update",
            old_status=MEMBERSHIP_STATUS_INVITED,
            new_status=MEMBERSHIP_STATUS_ACTIVE,
            metadata={"target_user_id": target.id},
        )
        uow.commit()
        return accepted

    def revoke_invitation(self, target_user_id: str) -> UserTenantMembership:
        with self._uow_factory.create(context=self._new_context()) as uow:
            actor, tenant_id = self._require_tenant_administrator(
                uow, operation_label="revoke a tenant invitation"
            )
            target = self._require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="revoke an invitation for",
            )
            membership = self._require_membership(uow.memberships, target.id, tenant_id)
            # P5D-2 decision (documented, not inferred from `status == "removed""): invitation
            # revocation is a distinct invitation-lifecycle fact, not a membership-removal fact,
            # so it deliberately emits NO `TenantMembershipRemoved` (and no other membership
            # event). Evidence: (1) the invited principal was never an active tenant member --
            # every membership-facing guard (self-lockout, `is_active_member`, the last-admin
            # count) gates on ACTIVE status, never INVITED; (2) the audit vocabulary already
            # distinguishes the two facts ("invitation_revoked" vs "removed"); (3) the aggregate
            # itself marks a different field (`revoked_at`, never set by `remove()`) and this
            # command never calls `_revoke_affected_sessions` or touches RoleBinding rows at
            # all, unlike `remove_member` -- there is nothing to invalidate because acceptance,
            # the only path that ever creates a session/binding footprint, never happened. A
            # separate `TenantInvitationRevoked` fact is deliberately NOT added either, per this
            # phase's own scope: no concrete consumer needs it yet.
            revoked = membership.revoke_invitation()
            uow.memberships.update(revoked)
            self._record_membership_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                membership=revoked,
                action="tenant.membership.invitation_revoked",
                operation="update",
                old_status=MEMBERSHIP_STATUS_INVITED,
                new_status=revoked.status,
                metadata={"target_user_id": target.id},
            )
            uow.commit()
        self._notify_invitation_revoked(target.id, tenant_id=tenant_id, membership=revoked)
        return revoked

    def suspend_member(self, target_user_id: str) -> UserTenantMembership:
        with self._uow_factory.create(context=self._new_context()) as uow:
            actor, tenant_id = self._require_tenant_administrator(
                uow, operation_label="suspend a tenant member"
            )
            target = self._require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="suspend",
            )
            membership = self._require_membership(uow.memberships, target.id, tenant_id)
            self._guard_last_tenant_administrator(
                uow.memberships, uow.role_bindings, uow.roles, target.id, tenant_id
            )
            now = self._clock.now()
            suspended = membership.suspend(suspended_at=now)
            invalidated_sessions = self._revoke_affected_sessions(
                uow.auth_sessions,
                target.id,
                tenant_id,
                revoked_at=now,
            )
            uow.memberships.update(suspended)
            self._record_membership_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                membership=suspended,
                action="tenant.membership.suspended",
                operation="update",
                old_status=MEMBERSHIP_STATUS_ACTIVE,
                new_status=suspended.status,
                metadata={
                    "target_user_id": target.id,
                    "invalidated_session_count": invalidated_sessions,
                },
            )
            # P5D-2: AuthSession invalidation above is a persistence/security side effect, not a
            # separate membership event. Verified (P5D-1): suspension never touches RoleBinding
            # rows, so this transition never emits a RoleBinding event either.
            uow.record_event(
                TenantMembershipSuspended(
                    membership_id=suspended.id,
                    tenant_id=tenant_id,
                    user_id=target.id,
                    occurred_at=now,
                )
            )
            uow.commit()
        domain_events.auth_changed.emit(target.id)
        return suspended

    def reactivate_member(self, target_user_id: str) -> UserTenantMembership:
        with self._uow_factory.create(context=self._new_context()) as uow:
            actor, tenant_id = self._require_tenant_administrator(
                uow, operation_label="reactivate a tenant member"
            )
            target = self._require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="reactivate",
                require_active=True,
            )
            membership = self._require_membership(uow.memberships, target.id, tenant_id)
            now = self._clock.now()
            reactivated = membership.reactivate(reactivated_at=now)
            uow.memberships.update(reactivated)
            self._record_membership_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                membership=reactivated,
                action="tenant.membership.reactivated",
                operation="update",
                old_status=MEMBERSHIP_STATUS_SUSPENDED,
                new_status=reactivated.status,
                metadata={"target_user_id": target.id},
            )
            # P5D-1 verified reactivation never touches RoleBinding rows -- zero RoleBinding
            # events here, by the same evidence as suspend_member above.
            uow.record_event(
                TenantMembershipReactivated(
                    membership_id=reactivated.id,
                    tenant_id=tenant_id,
                    user_id=target.id,
                    occurred_at=now,
                )
            )
            uow.commit()
        domain_events.auth_changed.emit(target.id)
        return reactivated

    def remove_member(self, target_user_id: str) -> UserTenantMembership:
        with self._uow_factory.create(context=self._new_context()) as uow:
            actor, tenant_id = self._require_tenant_administrator(
                uow, operation_label="remove a tenant member"
            )
            target = self._require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="remove",
            )
            membership = self._require_membership(uow.memberships, target.id, tenant_id)
            self._guard_last_tenant_administrator(
                uow.memberships, uow.role_bindings, uow.roles, target.id, tenant_id
            )
            now = self._clock.now()
            removed = membership.remove(removed_at=now)
            uow.memberships.update(removed)
            # P5D-2A: recorded immediately after the membership transition itself -- the ACTUAL
            # business-fact order is "membership is removed" first, "each active RoleBinding is
            # revoked as a cascade consequence" second (the revocation loop runs strictly after
            # this point in the code, never before). Recording here makes the committed event
            # order mirror real transition order. Safe for the same reason as acceptance: the
            # canonical UoW never publishes anything until `uow.commit()` succeeds.
            uow.record_event(
                TenantMembershipRemoved(
                    membership_id=removed.id,
                    tenant_id=tenant_id,
                    user_id=target.id,
                    occurred_at=now,
                )
            )
            invalidated_sessions = self._revoke_affected_sessions(
                uow.auth_sessions,
                target.id,
                tenant_id,
                revoked_at=now,
            )
            revoked_binding_count = self._revoke_active_role_bindings_for_membership_removal(
                uow,
                target.id,
                tenant_id,
                actor=actor,
            )
            self._record_membership_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                membership=removed,
                action="tenant.membership.removed",
                operation="update",
                old_status=membership.status,
                new_status=removed.status,
                metadata={
                    "target_user_id": target.id,
                    "invalidated_session_count": invalidated_sessions,
                    "revoked_binding_count": revoked_binding_count,
                },
            )
            uow.commit()
        domain_events.auth_changed.emit(target.id)
        return removed

    @staticmethod
    def hash_invitation_token(token: str) -> str:
        normalized = str(token or "").strip()
        if len(normalized) < _MINIMUM_INVITATION_TOKEN_LENGTH:
            raise BusinessRuleError(
                "The tenant invitation token is invalid.",
                code="TENANT_INVITATION_INVALID",
            )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_invitation_expiry(
        expires_at: datetime,
        *,
        issued_at: datetime,
    ) -> datetime:
        normalized = ensure_utc_datetime(expires_at)
        if (
            normalized is None
            or normalized <= issued_at
            or normalized > issued_at + _MAXIMUM_INVITATION_LIFETIME
        ):
            raise BusinessRuleError(
                "Tenant invitations must expire within 30 days.",
                code="TENANT_INVITATION_EXPIRY_INVALID",
            )
        return normalized

    def _require_authenticated_principal(self):
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required for tenant membership operations.",
                code="AUTHENTICATION_REQUIRED",
            )
        return principal

    @staticmethod
    def _is_platform_operator(principal) -> bool:
        return (
            "admin" in principal.role_names
            and "platform.admin" in principal.permissions
        )

    def _require_tenant_administrator(self, uow: TenantMembershipUnitOfWork, *, operation_label: str):
        require_permission(
            self._user_session,
            "auth.manage",
            operation_label=operation_label,
        )
        actor = self._require_authenticated_principal()
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label=operation_label
        )
        self._require_active_tenant(uow.tenants, tenant_id)
        if (
            not self._is_platform_operator(actor)
            and not uow.memberships.is_active_member(
                actor.user_id,
                tenant_id,
            )
        ):
            authorization_denied(
                self._user_session,
                message="The authenticated user is not an active member of the selected tenant.",
                code="TENANT_ACCESS_DENIED",
                operation_label=operation_label,
                target_scope_type="tenant",
                target_scope_id=tenant_id,
                operation="authorization.membership.denied",
            )
        return actor, tenant_id

    def _require_active_tenant(self, tenant_repo, tenant_id: str) -> None:
        tenant = tenant_repo.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if not tenant.is_active:
            raise BusinessRuleError(
                "Tenant membership changes require an active tenant.",
                code="TENANT_INACTIVE",
            )

    def _require_user(self, user_repo, user_id: str) -> UserAccount:
        user = user_repo.get(str(user_id or "").strip())
        if user is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user

    def _require_active_user(self, user_repo, user_id: str) -> UserAccount:
        user = self._require_user(user_repo, user_id)
        if not user.is_active:
            raise BusinessRuleError(
                "Inactive users cannot enter a tenant.",
                code="TENANT_MEMBERSHIP_USER_INACTIVE",
            )
        return user

    def _require_manageable_target(
        self,
        uow: TenantMembershipUnitOfWork,
        user_id: str,
        *,
        actor,
        operation_label: str,
        require_active: bool = False,
        require_invitation_safe_roles: bool = False,
    ) -> UserAccount:
        target = (
            self._require_active_user(uow.users, user_id)
            if require_active
            else self._require_user(uow.users, user_id)
        )
        if target.id == actor.user_id:
            authorization_denied(
                self._user_session,
                message=(
                    f"Cannot {operation_label} the authenticated user's own membership."
                ),
                code="TENANT_MEMBERSHIP_SELF_LOCKOUT",
                operation_label=f"{operation_label} tenant membership",
                target_scope_type="user",
                target_scope_id=target.id,
                operation="authorization.membership.denied",
            )
        roles = self._platform_roles_for_user(uow.role_bindings, uow.roles, target.id)
        if any(
            role.name in _PLATFORM_ROLE_NAMES
            or role.allowed_scope_type == ROLE_SCOPE_PLATFORM
            for role in roles
        ):
            authorization_denied(
                self._user_session,
                message=(
                    "Platform operators cannot be managed through a customer "
                    "membership path."
                ),
                code="TENANT_MEMBERSHIP_PLATFORM_TARGET_DENIED",
                operation_label=f"{operation_label} tenant membership",
                target_scope_type="user",
                target_scope_id=target.id,
                operation="authorization.support_access.denied",
            )
        if require_invitation_safe_roles:
            self._require_invitation_safe_roles(uow.role_bindings, uow.roles, target, roles=roles)
        return target

    def _platform_roles_for_user(self, role_bindings_repo, roles_repo, user_id: str):
        return [
            role
            for binding in role_bindings_repo.list_active_for_principal(
                user_id,
                tenant_id=None,
            )
            if (role := roles_repo.get(binding.role_id)) is not None
            and role.allowed_scope_type == ROLE_SCOPE_PLATFORM
        ]

    def _require_invitation_safe_roles(
        self,
        role_bindings_repo,
        roles_repo,
        user: UserAccount,
        *,
        roles=None,
    ) -> None:
        resolved_roles = (
            roles
            if roles is not None
            else self._platform_roles_for_user(role_bindings_repo, roles_repo, user.id)
        )
        if any(
            role.name in _PLATFORM_ROLE_NAMES
            or role.allowed_scope_type == ROLE_SCOPE_PLATFORM
            for role in resolved_roles
        ):
            authorization_denied(
                self._user_session,
                message=(
                    "Platform operators cannot be invited through a customer "
                    "membership path."
                ),
                code="TENANT_MEMBERSHIP_PLATFORM_TARGET_DENIED",
                operation_label="validate tenant invitation roles",
                target_scope_type="user",
                target_scope_id=user.id,
                operation="authorization.support_access.denied",
            )

    def _guard_last_tenant_administrator(
        self,
        memberships_repo,
        role_bindings_repo,
        roles_repo,
        target_user_id: str,
        tenant_id: str,
    ) -> None:
        if not self._is_effective_tenant_administrator(
            memberships_repo, role_bindings_repo, roles_repo, target_user_id, tenant_id,
        ):
            return
        active_admin_count = sum(
            1
            for membership in memberships_repo.list_users_for_tenant(tenant_id)
            if self._is_effective_tenant_administrator(
                memberships_repo, role_bindings_repo, roles_repo, membership.user_id, tenant_id,
            )
        )
        if active_admin_count <= 1:
            authorization_denied(
                self._user_session,
                message=(
                    "Transfer tenant administration before removing the last "
                    "administrator."
                ),
                code="TENANT_LAST_ADMIN_REQUIRED",
                operation_label="remove or suspend a tenant administrator",
                target_scope_type="user",
                target_scope_id=target_user_id,
                operation="authorization.sod.denied",
            )

    def _is_effective_tenant_administrator(
        self,
        memberships_repo,
        role_bindings_repo,
        roles_repo,
        user_id: str,
        tenant_id: str,
    ) -> bool:
        if not memberships_repo.is_active_member(user_id, tenant_id):
            return False
        return any(
            binding.actual_scope_type == ROLE_SCOPE_TENANT
            and binding.actual_scope_id is None
            and (role := roles_repo.get(binding.role_id)) is not None
            and role.name == "tenant_admin"
            for binding in role_bindings_repo.list_active_for_principal(
                user_id,
                tenant_id=tenant_id,
            )
        )

    def _require_membership(
        self,
        memberships_repo,
        user_id: str,
        tenant_id: str,
    ) -> UserTenantMembership:
        membership = memberships_repo.get(user_id, tenant_id)
        if membership is None:
            raise NotFoundError(
                "Tenant membership not found.",
                code="TENANT_MEMBERSHIP_NOT_FOUND",
            )
        return membership

    def _ensure_default_role_bindings(
        self,
        uow: TenantMembershipUnitOfWork,
        user: UserAccount,
        *,
        tenant_id: str,
        actor,
    ) -> None:
        """Membership-driven default grant on self-service acceptance: a real business fact,
        so it reuses the canonical `RoleBindingAssigned`-emitting mechanics (P5C event
        vocabulary, never a new event name) -- but deliberately skips the interactive-admin
        delegation-namespace/permission-snapshot checks `RoleGovernanceService.assign_role`
        enforces, since this is a system-issued default grant, not an admin delegating a role
        to someone else (P5D-1 item 17's explicit policy distinction)."""
        role = self._require_default_invitation_role(uow.roles, tenant_id)
        create_role_binding_using(
            role_bindings_repo=uow.role_bindings,
            audit_repo=uow.audit,
            clock=self._clock,
            record_event=uow.record_event,
            principal_id=user.id,
            role_id=role.id,
            tenant_id=tenant_id,
            scope_type=ROLE_SCOPE_TENANT,
            scope_id=None,
            domain_scope=RoleBindingTenantScope(tenant_id=tenant_id),
            actor=actor,
            audit_action="auth.role.binding.assigned",
            audit_metadata_extra={"origin": "tenant_membership_acceptance"},
        )

    def _revoke_active_role_bindings_for_membership_removal(
        self,
        uow: TenantMembershipUnitOfWork,
        target_user_id: str,
        tenant_id: str,
        *,
        actor,
    ) -> int:
        """Membership-removal cascade: revokes every genuinely active RoleBinding the target
        holds in this tenant, one at a time, through the same canonical revoke mechanics
        `RoleGovernanceService.revoke_role_binding` uses -- one real `RoleBindingRevoked` per
        real transition, never a bulk-generated event for rows that were never truly active.
        Replaces the pre-P5D-1 direct bulk-SQL `revoke_active_for_principal_tenant` bypass,
        which updated rows with no audit/event evidence at all. Deliberately does not apply
        interactive-admin delegation/SoD policy (same P5D-1 item 17 distinction as the default
        grant above): this is a membership-lifecycle cascade, not an admin revoking someone
        else's role by choice."""
        revoked_count = 0
        for binding in uow.role_bindings.list_active_for_principal(target_user_id, tenant_id=tenant_id):
            domain_scope = resolve_domain_scope_for_binding(
                session=uow.session,
                tenant_id=tenant_id,
                scope_type=binding.actual_scope_type,
                scope_id=binding.actual_scope_id,
                organization_owner_resolvers=self._organization_owner_resolvers,
            )
            revoke_role_binding_using(
                role_bindings_repo=uow.role_bindings,
                audit_repo=uow.audit,
                clock=self._clock,
                record_event=uow.record_event,
                binding=binding,
                domain_scope=domain_scope,
                actor=actor,
                audit_action="auth.role.binding.revoked",
                audit_metadata_extra={"origin": "tenant_membership_removal"},
            )
            revoked_count += 1
        return revoked_count

    def _require_default_invitation_role(self, roles_repo, tenant_id: str):
        role = roles_repo.get_by_name(_DEFAULT_INVITATION_ROLE)
        if (
            role is None
            or role.status != "active"
            or not role.is_assignable
            or role.allowed_scope_type != ROLE_SCOPE_TENANT
            or role.tenant_id not in {None, tenant_id}
        ):
            authorization_denied(
                self._user_session,
                message="The default tenant invitation role is not safely assignable.",
                code="TENANT_INVITATION_DEFAULT_ROLE_INVALID",
                operation_label="assign the default tenant invitation role",
                target_scope_type="tenant",
                target_scope_id=tenant_id,
                operation="authorization.infrastructure.denied",
            )
        return role

    def _revoke_affected_sessions(
        self,
        auth_sessions_repo,
        user_id: str,
        tenant_id: str,
        *,
        revoked_at: datetime,
    ) -> int:
        revoked_count = 0
        for auth_session in auth_sessions_repo.list_by_user(user_id):
            if (
                auth_session.revoked_at is not None
                or auth_session.last_active_tenant_id != tenant_id
            ):
                continue
            auth_session.revoked_at = revoked_at
            auth_session.updated_at = revoked_at
            auth_sessions_repo.update(auth_session)
            revoked_count += 1
        return revoked_count

    def _record_membership_audit(
        self,
        audit_repo,
        *,
        actor,
        tenant_id: str,
        membership: UserTenantMembership,
        action: str,
        operation: str,
        old_status: str | None,
        new_status: str,
        metadata: dict[str, object],
    ) -> None:
        entry = AuditEntry.create(
            operation=operation,
            entity_type="tenant_membership",
            entity_id=membership.id,
            entity_parent_id=tenant_id,
            module="platform",
            actor_id=actor.user_id,
            actor_username=actor.username,
            field="status",
            old_value=old_status,
            new_value=new_status,
            tenant_id=tenant_id,
            severity="high",
            compliance_tag="SOC2",
            metadata={"action": action, **metadata},
        )
        audit_repo.add_for_tenant(entry, tenant_id)

    def _notify_invitation_issued(
        self,
        recipient_user_id: str,
        *,
        tenant_id: str,
        membership: UserTenantMembership,
    ) -> None:
        # The raw invitation token is never placed in notification metadata: notifications
        # are a generic, broadly-readable transport. Acceptance from this notification goes
        # through accept_invitation_for_tenant, which needs no bearer token.
        self._safe_dispatch_notification(
            recipient_user_id=recipient_user_id,
            category="tenant.invitation.issued",
            title="You've been invited to join a workspace",
            body="You have a pending workspace invitation, expiring "
            f"{membership.invitation_expires_at.isoformat()}.",
            tenant_id=tenant_id,
            metadata={"membership_id": membership.id},
        )

    def _notify_invitation_revoked(
        self,
        recipient_user_id: str,
        *,
        tenant_id: str,
        membership: UserTenantMembership,
    ) -> None:
        self._safe_dispatch_notification(
            recipient_user_id=recipient_user_id,
            category="tenant.invitation.revoked",
            title="Your workspace invitation was revoked",
            body="A pending invitation to join a workspace was revoked by an administrator.",
            tenant_id=tenant_id,
            metadata={"membership_id": membership.id},
        )

    def _safe_dispatch_notification(
        self,
        *,
        recipient_user_id: str,
        category: str,
        title: str,
        body: str,
        tenant_id: str,
        metadata: dict[str, object],
    ) -> None:
        try:
            self._notification_service.dispatch(
                recipient_user_id=recipient_user_id,
                category=category,
                title=title,
                body=body,
                tenant_id=tenant_id,
                metadata=metadata,
                commit=True,
            )
        except Exception:
            logger.exception(
                "Tenant membership notification dispatch failed category=%s recipient=%s",
                category,
                recipient_user_id,
            )


__all__ = ["IssuedTenantInvitation", "TenantMembershipService"]
