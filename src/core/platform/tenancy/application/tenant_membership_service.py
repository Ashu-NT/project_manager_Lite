from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditRepository
from src.core.platform.audit.domain import AuditEntry
from src.core.platform.auth.authorization import (
    authorization_denied,
    require_permission,
)
from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.contracts import (
    AuthSessionRepository,
    RoleBindingRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from src.core.platform.auth.domain import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    RoleBinding,
    UserAccount,
    UserRoleBinding,
    UserSessionContext,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
)
from src.core.platform.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.platform.tenancy.domain import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_INVITED,
    MEMBERSHIP_STATUS_REMOVED,
    MEMBERSHIP_STATUS_SUSPENDED,
    UserTenantMembership,
)
from src.core.platform.tenancy.tenant_context import TenantContextService
from src.core.shared.events.domain_events import domain_events


_DEFAULT_INVITATION_ROLE = "viewer"
_PLATFORM_ROLE_NAMES = frozenset({"admin", "support_admin"})
_MINIMUM_INVITATION_TOKEN_LENGTH = 32
_MAXIMUM_INVITATION_LIFETIME = timedelta(days=30)


@dataclass(frozen=True)
class IssuedTenantInvitation:
    membership: UserTenantMembership
    token: str


class TenantMembershipService:
    """Authorized orchestration for tenant membership lifecycle changes."""

    def __init__(
        self,
        *,
        session: Session,
        tenant_repo: TenantRepository,
        membership_repo: UserTenantMembershipRepository,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        role_binding_repo: RoleBindingRepository,
        user_role_repo: UserRoleRepository,
        auth_session_repo: AuthSessionRepository,
        audit_repo: AuditRepository,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
    ) -> None:
        self._session = session
        self._tenant_repo = tenant_repo
        self._membership_repo = membership_repo
        self._user_repo = user_repo
        self._role_repo = role_repo
        self._role_binding_repo = role_binding_repo
        self._user_role_repo = user_role_repo
        self._auth_session_repo = auth_session_repo
        self._audit_repo = audit_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def issue_invitation(
        self,
        target_user_id: str,
        *,
        expires_at: datetime,
    ) -> IssuedTenantInvitation:
        actor, tenant_id = self._require_tenant_administrator(
            operation_label="invite a tenant member"
        )
        target = self._require_manageable_target(
            target_user_id,
            actor=actor,
            operation_label="invite",
            require_active=True,
            require_invitation_safe_roles=True,
        )
        self._require_default_invitation_role(tenant_id)
        now = datetime.now(timezone.utc)
        normalized_expires_at = self._validate_invitation_expiry(
            expires_at,
            issued_at=now,
        )
        token = secrets.token_urlsafe(32)
        token_hash = self.hash_invitation_token(token)
        existing = self._membership_repo.get(target.id, tenant_id)

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
            persist = self._membership_repo.add
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
            persist = self._membership_repo.update
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

        try:
            persist(membership)
            self._record_membership_audit(
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
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return IssuedTenantInvitation(membership=membership, token=token)

    def accept_invitation(self, token: str) -> UserTenantMembership:
        actor = self._require_authenticated_principal()
        token_hash = self.hash_invitation_token(token)
        membership = self._membership_repo.get_by_invitation_token_hash(token_hash)
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

        target = self._require_active_user(membership.user_id)
        self._require_invitation_safe_roles(target)
        self._require_active_tenant(membership.tenant_id)
        accepted = membership.accept_invitation()
        try:
            self._membership_repo.update(accepted)
            self._ensure_default_role_bindings(
                target,
                tenant_id=accepted.tenant_id,
                assigned_by=actor.user_id,
            )
            self._record_membership_audit(
                actor=actor,
                tenant_id=accepted.tenant_id,
                membership=accepted,
                action="tenant.membership.invitation_accepted",
                operation="update",
                old_status=MEMBERSHIP_STATUS_INVITED,
                new_status=MEMBERSHIP_STATUS_ACTIVE,
                metadata={"target_user_id": target.id},
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        domain_events.auth_changed.emit(target.id)
        return accepted

    def revoke_invitation(self, target_user_id: str) -> UserTenantMembership:
        actor, tenant_id = self._require_tenant_administrator(
            operation_label="revoke a tenant invitation"
        )
        target = self._require_manageable_target(
            target_user_id,
            actor=actor,
            operation_label="revoke an invitation for",
        )
        membership = self._require_membership(target.id, tenant_id)
        revoked = membership.revoke_invitation()
        self._persist_administrative_transition(
            actor=actor,
            membership=revoked,
            action="tenant.membership.invitation_revoked",
            old_status=MEMBERSHIP_STATUS_INVITED,
            metadata={"target_user_id": target.id},
        )
        return revoked

    def suspend_member(self, target_user_id: str) -> UserTenantMembership:
        actor, tenant_id = self._require_tenant_administrator(
            operation_label="suspend a tenant member"
        )
        target = self._require_manageable_target(
            target_user_id,
            actor=actor,
            operation_label="suspend",
        )
        membership = self._require_membership(target.id, tenant_id)
        self._guard_last_tenant_administrator(target.id, tenant_id)
        now = datetime.now(timezone.utc)
        suspended = membership.suspend(suspended_at=now)
        invalidated_sessions = self._revoke_affected_sessions(
            target.id,
            tenant_id,
            revoked_at=now,
        )
        self._persist_administrative_transition(
            actor=actor,
            membership=suspended,
            action="tenant.membership.suspended",
            old_status=MEMBERSHIP_STATUS_ACTIVE,
            metadata={
                "target_user_id": target.id,
                "invalidated_session_count": invalidated_sessions,
            },
        )
        domain_events.auth_changed.emit(target.id)
        return suspended

    def reactivate_member(self, target_user_id: str) -> UserTenantMembership:
        actor, tenant_id = self._require_tenant_administrator(
            operation_label="reactivate a tenant member"
        )
        target = self._require_manageable_target(
            target_user_id,
            actor=actor,
            operation_label="reactivate",
            require_active=True,
        )
        membership = self._require_membership(target.id, tenant_id)
        reactivated = membership.reactivate()
        self._persist_administrative_transition(
            actor=actor,
            membership=reactivated,
            action="tenant.membership.reactivated",
            old_status=MEMBERSHIP_STATUS_SUSPENDED,
            metadata={"target_user_id": target.id},
        )
        domain_events.auth_changed.emit(target.id)
        return reactivated

    def remove_member(self, target_user_id: str) -> UserTenantMembership:
        actor, tenant_id = self._require_tenant_administrator(
            operation_label="remove a tenant member"
        )
        target = self._require_manageable_target(
            target_user_id,
            actor=actor,
            operation_label="remove",
        )
        membership = self._require_membership(target.id, tenant_id)
        self._guard_last_tenant_administrator(target.id, tenant_id)
        now = datetime.now(timezone.utc)
        removed = membership.remove(removed_at=now)
        invalidated_sessions = self._revoke_affected_sessions(
            target.id,
            tenant_id,
            revoked_at=now,
        )
        revoked_bindings = self._role_binding_repo.revoke_active_for_principal_tenant(
            target.id,
            tenant_id,
            revoked_at=now,
        )
        self._persist_administrative_transition(
            actor=actor,
            membership=removed,
            action="tenant.membership.removed",
            old_status=membership.status,
            metadata={
                "target_user_id": target.id,
                "invalidated_session_count": invalidated_sessions,
                "revoked_binding_count": revoked_bindings,
            },
        )
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

    def _require_tenant_administrator(self, *, operation_label: str):
        require_permission(
            self._user_session,
            "auth.manage",
            operation_label=operation_label,
        )
        actor = self._require_authenticated_principal()
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label=operation_label
        )
        self._require_active_tenant(tenant_id)
        if (
            not self._is_platform_operator(actor)
            and not self._membership_repo.is_active_member(
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

    def _require_active_tenant(self, tenant_id: str) -> None:
        tenant = self._tenant_repo.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if not tenant.is_active:
            raise BusinessRuleError(
                "Tenant membership changes require an active tenant.",
                code="TENANT_INACTIVE",
            )

    def _require_user(self, user_id: str) -> UserAccount:
        user = self._user_repo.get(str(user_id or "").strip())
        if user is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user

    def _require_active_user(self, user_id: str) -> UserAccount:
        user = self._require_user(user_id)
        if not user.is_active:
            raise BusinessRuleError(
                "Inactive users cannot enter a tenant.",
                code="TENANT_MEMBERSHIP_USER_INACTIVE",
            )
        return user

    def _require_manageable_target(
        self,
        user_id: str,
        *,
        actor,
        operation_label: str,
        require_active: bool = False,
        require_invitation_safe_roles: bool = False,
    ) -> UserAccount:
        target = (
            self._require_active_user(user_id)
            if require_active
            else self._require_user(user_id)
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
        roles = self._roles_for_user(target.id)
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
            self._require_invitation_safe_roles(target, roles=roles)
        return target

    def _roles_for_user(self, user_id: str):
        return [
            role
            for role_id in self._user_role_repo.list_role_ids(user_id)
            if (role := self._role_repo.get(role_id)) is not None
        ]

    def _require_invitation_safe_roles(
        self,
        user: UserAccount,
        *,
        roles=None,
    ) -> None:
        resolved_roles = roles if roles is not None else self._roles_for_user(user.id)
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
        if any(role.name != _DEFAULT_INVITATION_ROLE for role in resolved_roles):
            authorization_denied(
                self._user_session,
                message=(
                    "The user's legacy roles require canonical migration review "
                    "before invitation."
                ),
                code="TENANT_INVITATION_LEGACY_ROLE_AMBIGUOUS",
                operation_label="validate tenant invitation roles",
                target_scope_type="user",
                target_scope_id=user.id,
                operation="authorization.permission_ceiling.denied",
            )

    def _guard_last_tenant_administrator(
        self,
        target_user_id: str,
        tenant_id: str,
    ) -> None:
        if not self._is_effective_legacy_tenant_administrator(
            target_user_id,
            tenant_id,
        ):
            return
        active_admin_count = sum(
            1
            for membership in self._membership_repo.list_users_for_tenant(
                tenant_id
            )
            if self._is_effective_legacy_tenant_administrator(
                membership.user_id,
                tenant_id,
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

    def _is_effective_legacy_tenant_administrator(
        self,
        user_id: str,
        tenant_id: str,
    ) -> bool:
        if not self._membership_repo.is_active_member(user_id, tenant_id):
            return False
        if self._membership_repo.list_tenant_ids_for_user(user_id) != [tenant_id]:
            return False
        return any(
            role.name == "tenant_admin"
            for role in self._roles_for_user(user_id)
        )

    def _require_membership(
        self,
        user_id: str,
        tenant_id: str,
    ) -> UserTenantMembership:
        membership = self._membership_repo.get(user_id, tenant_id)
        if membership is None:
            raise NotFoundError(
                "Tenant membership not found.",
                code="TENANT_MEMBERSHIP_NOT_FOUND",
            )
        return membership

    def _ensure_default_role_bindings(
        self,
        user: UserAccount,
        *,
        tenant_id: str,
        assigned_by: str,
    ) -> None:
        role = self._require_default_invitation_role(tenant_id)

        active_bindings = self._role_binding_repo.list_active_for_principal(
            user.id,
            tenant_id=tenant_id,
        )
        if not any(
            binding.role_id == role.id
            and binding.actual_scope_type == ROLE_SCOPE_TENANT
            and binding.actual_scope_id is None
            for binding in active_bindings
        ):
            self._role_binding_repo.add(
                RoleBinding.create(
                    principal_id=user.id,
                    role_id=role.id,
                    actual_scope_type=ROLE_SCOPE_TENANT,
                    tenant_id=tenant_id,
                    assigned_by=assigned_by,
                )
            )
        if not self._user_role_repo.exists(user.id, role.id):
            # RBAC-TRANSITION-ONLY: Remove this compatibility write when
            # canonical role bindings become the sole assignment store.
            self._user_role_repo.add(
                UserRoleBinding.create(user_id=user.id, role_id=role.id)
            )

    def _require_default_invitation_role(self, tenant_id: str):
        role = self._role_repo.get_by_name(_DEFAULT_INVITATION_ROLE)
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
        user_id: str,
        tenant_id: str,
        *,
        revoked_at: datetime,
    ) -> int:
        revoked_count = 0
        for auth_session in self._auth_session_repo.list_by_user(user_id):
            if (
                auth_session.revoked_at is not None
                or auth_session.last_active_tenant_id != tenant_id
            ):
                continue
            auth_session.revoked_at = revoked_at
            auth_session.updated_at = revoked_at
            self._auth_session_repo.update(auth_session)
            revoked_count += 1
        return revoked_count

    def _persist_administrative_transition(
        self,
        *,
        actor,
        membership: UserTenantMembership,
        action: str,
        old_status: str,
        metadata: dict[str, object],
    ) -> None:
        try:
            self._membership_repo.update(membership)
            self._record_membership_audit(
                actor=actor,
                tenant_id=membership.tenant_id,
                membership=membership,
                action=action,
                operation="update",
                old_status=old_status,
                new_status=membership.status,
                metadata=metadata,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def _record_membership_audit(
        self,
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
        self._audit_repo.add_for_tenant(entry, tenant_id)


__all__ = ["IssuedTenantInvitation", "TenantMembershipService"]
