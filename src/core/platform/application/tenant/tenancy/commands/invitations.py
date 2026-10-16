from __future__ import annotations

import hmac
import secrets
from datetime import datetime

import src.core.platform.application.tenant.tenancy.mappers.tenant as response_mapper
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    authorization_denied,
)
from src.core.platform.application.tenant.tenancy.dto.responses.tenant import (
    TenantInvitationDto,
)
from src.core.platform.application.tenant.tenancy.invitation_tokens import (
    IssuedTenantInvitation,
    hash_invitation_token,
)
from src.core.platform.application.tenant.tenancy.membership_support import (
    TenantMembershipSupport,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.uow.tenancy.tenant_membership_unit_of_work import (
    TenantMembershipUnitOfWork,
    TenantMembershipUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth import UserSessionContext
from src.core.platform.domain.tenant.tenancy import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_INVITED,
    MEMBERSHIP_STATUS_REMOVED,
    MEMBERSHIP_STATUS_SUSPENDED,
    TenantInvitationChanged,
    TenantMembershipActivated,
    UserTenantMembership,
)
from src.core.shared.time.clock import Clock


class TenantInvitationCommandHandler:
    """Invitation issuance, revocation and self-scoped acceptance in atomic UoWs."""

    def __init__(
        self,
        *,
        uow_factory: TenantMembershipUnitOfWorkFactory,
        support: TenantMembershipSupport,
        clock: Clock,
        user_session: UserSessionContext,
    ) -> None:
        self._uow_factory = uow_factory
        self._support = support
        self._clock = clock
        self._user_session = user_session

    def issue_invitation(
        self,
        target_user_id: str,
        *,
        expires_at: datetime,
    ) -> IssuedTenantInvitation:
        with self._uow_factory.create(context=self._support.new_context()) as uow:
            actor, tenant_id = self._support.require_tenant_administrator(
                uow, operation_label="invite a tenant member"
            )
            target = self._support.require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="invite",
                require_active=True,
                require_invitation_safe_roles=True,
            )
            self._support.require_default_invitation_role(uow.roles, tenant_id)
            now = self._clock.now()
            normalized_expires_at = self._support.validate_invitation_expiry(
                expires_at,
                issued_at=now,
            )
            token = secrets.token_urlsafe(32)
            token_hash = hash_invitation_token(token)
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
            self._support.record_membership_audit(
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
                    "expires_at": normalized_expires_at.isoformat(),
                },
            )
            uow.record_event(
                TenantInvitationChanged(
                    membership_id=membership.id,
                    tenant_id=tenant_id,
                    recipient_user_id=target.id,
                    change_type="issued",
                    occurred_at=now,
                )
            )
            uow.commit()
        return IssuedTenantInvitation(membership=membership, token=token)

    def accept_invitation(self, token: str) -> UserTenantMembership:
        """Accept via the raw one-time token (out-of-band delivery, e.g. a future emailed link)."""
        actor = self._support.require_authenticated_principal()
        token_hash = hash_invitation_token(token)
        with self._uow_factory.create(context=self._support.new_context()) as uow:
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
        return accepted

    def accept_invitation_for_tenant(self, tenant_id: str) -> TenantInvitationDto:
        """Accept the caller's own pending invitation for a tenant, surfaced via
        `list_my_pending_invitations`/in-app notification. No bearer token is involved:
        the caller is already an authenticated principal, and the membership lookup is
        keyed by that principal's own user id, not a shared secret."""
        actor = self._support.require_authenticated_principal()
        normalized_tenant_id = str(tenant_id or "").strip()
        with self._uow_factory.create(context=self._support.new_context()) as uow:
            membership = self._support.require_membership(
                uow.memberships, actor.user_id, normalized_tenant_id
            )
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
        return response_mapper.serialize_invitation(accepted)

    def _accept_membership(
        self,
        uow: TenantMembershipUnitOfWork,
        membership: UserTenantMembership,
        *,
        actor,
    ) -> UserTenantMembership:
        target = self._support.require_active_user(uow.users, membership.user_id)
        self._support.require_invitation_safe_roles(
            uow.role_bindings, uow.roles, target
        )
        self._support.require_active_tenant(uow.tenants, membership.tenant_id)
        accepted = membership.accept_invitation()
        uow.memberships.update(accepted)
        # Recorded before the default-role grant so committed event order matches the
        # real transition order (the UoW publishes only after commit succeeds).
        uow.record_event(
            TenantMembershipActivated(
                membership_id=accepted.id,
                tenant_id=accepted.tenant_id,
                user_id=accepted.user_id,
                occurred_at=self._clock.now(),
            )
        )
        self._support.ensure_default_role_bindings(
            uow,
            target,
            tenant_id=accepted.tenant_id,
            actor=actor,
        )
        self._support.record_membership_audit(
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
        with self._uow_factory.create(context=self._support.new_context()) as uow:
            actor, tenant_id = self._support.require_tenant_administrator(
                uow, operation_label="revoke a tenant invitation"
            )
            target = self._support.require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="revoke an invitation for",
            )
            membership = self._support.require_membership(
                uow.memberships, target.id, tenant_id
            )
            # Invitation revocation is an invitation-lifecycle fact, not a membership-removal
            # fact: the invited principal was never an active member, so no
            # TenantMembershipRemoved (or any other membership event) is emitted here.
            revoked = membership.revoke_invitation()
            uow.memberships.update(revoked)
            self._support.record_membership_audit(
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
            uow.record_event(
                TenantInvitationChanged(
                    membership_id=revoked.id,
                    tenant_id=tenant_id,
                    recipient_user_id=target.id,
                    change_type="revoked",
                    occurred_at=self._clock.now(),
                )
            )
            uow.commit()
        return revoked
