from __future__ import annotations

from datetime import datetime, timedelta

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
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.uow.tenancy.tenant_membership_unit_of_work import (
    TenantMembershipUnitOfWork,
)
from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.domain.security.auth import (
    UserAccount,
    UserSessionContext,
)
from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    RoleBindingTenantScope,
)
from src.core.platform.domain.tenant.tenancy import (
    UserTenantMembership,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

_DEFAULT_INVITATION_ROLE = "viewer"
_PLATFORM_ROLE_NAMES = frozenset({"admin", "support_admin"})
_MAXIMUM_INVITATION_LIFETIME = timedelta(days=30)


class TenantMembershipSupport:
    """Shared authorization, audit and in-UoW role/session mutation mechanics."""

    def __init__(
        self,
        *,
        clock: Clock,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
        organization_owner_resolvers: dict[str, OrganizationOwnerResolver],
    ) -> None:
        self._clock = clock
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._organization_owner_resolvers = organization_owner_resolvers

    def new_context(self) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id())

    @staticmethod
    def validate_invitation_expiry(
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

    def require_authenticated_principal(self):
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required for tenant membership operations.",
                code="AUTHENTICATION_REQUIRED",
            )
        return principal

    @staticmethod
    def is_platform_operator(principal) -> bool:
        return (
            "admin" in principal.role_names
            and "platform.admin" in principal.permissions
        )

    def require_tenant_administrator(
        self, uow: TenantMembershipUnitOfWork, *, operation_label: str
    ):
        require_permission(
            self._user_session,
            "auth.manage",
            operation_label=operation_label,
        )
        actor = self.require_authenticated_principal()
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label=operation_label
        )
        self.require_active_tenant(uow.tenants, tenant_id)
        if not self.is_platform_operator(
            actor
        ) and not uow.memberships.is_active_member(
            actor.user_id,
            tenant_id,
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

    def require_active_tenant(self, tenant_repo, tenant_id: str) -> None:
        tenant = tenant_repo.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if not tenant.is_active:
            raise BusinessRuleError(
                "Tenant membership changes require an active tenant.",
                code="TENANT_INACTIVE",
            )

    def require_user(self, user_repo, user_id: str) -> UserAccount:
        user = user_repo.get(str(user_id or "").strip())
        if user is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user

    def require_active_user(self, user_repo, user_id: str) -> UserAccount:
        user = self.require_user(user_repo, user_id)
        if not user.is_active:
            raise BusinessRuleError(
                "Inactive users cannot enter a tenant.",
                code="TENANT_MEMBERSHIP_USER_INACTIVE",
            )
        return user

    def require_manageable_target(
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
            self.require_active_user(uow.users, user_id)
            if require_active
            else self.require_user(uow.users, user_id)
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
        roles = self.platform_roles_for_user(uow.role_bindings, uow.roles, target.id)
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
            self.require_invitation_safe_roles(
                uow.role_bindings, uow.roles, target, roles=roles
            )
        return target

    def platform_roles_for_user(self, role_bindings_repo, roles_repo, user_id: str):
        return [
            role
            for binding in role_bindings_repo.list_active_for_principal(
                user_id,
                tenant_id=None,
            )
            if (role := roles_repo.get(binding.role_id)) is not None
            and role.allowed_scope_type == ROLE_SCOPE_PLATFORM
        ]

    def require_invitation_safe_roles(
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
            else self.platform_roles_for_user(role_bindings_repo, roles_repo, user.id)
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

    def guard_last_tenant_administrator(
        self,
        memberships_repo,
        role_bindings_repo,
        roles_repo,
        target_user_id: str,
        tenant_id: str,
    ) -> None:
        if not self.is_effective_tenant_administrator(
            memberships_repo,
            role_bindings_repo,
            roles_repo,
            target_user_id,
            tenant_id,
        ):
            return
        active_admin_count = sum(
            1
            for membership in memberships_repo.list_users_for_tenant(tenant_id)
            if self.is_effective_tenant_administrator(
                memberships_repo,
                role_bindings_repo,
                roles_repo,
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

    def is_effective_tenant_administrator(
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

    def require_membership(
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

    def ensure_default_role_bindings(
        self,
        uow: TenantMembershipUnitOfWork,
        user: UserAccount,
        *,
        tenant_id: str,
        actor,
    ) -> None:
        """Grants the default role on self-service acceptance, skipping the interactive-admin
        delegation/SoD checks `RoleGovernanceService.assign_role` enforces -- this is a
        system-issued grant, not an admin delegating a role to someone else."""
        role = self.require_default_invitation_role(uow.roles, tenant_id)
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

    def revoke_active_role_bindings_for_membership_removal(
        self,
        uow: TenantMembershipUnitOfWork,
        target_user_id: str,
        tenant_id: str,
        *,
        actor,
    ) -> int:
        """Revokes every active RoleBinding the target holds in this tenant, through the
        same canonical revoke mechanics `RoleGovernanceService.revoke_role_binding` uses,
        emitting one `RoleBindingRevoked` per binding. Skips interactive-admin delegation/SoD
        policy: this is a membership-lifecycle cascade, not an admin revoking someone else's
        role by choice."""
        revoked_count = 0
        for binding in uow.role_bindings.list_active_for_principal(
            target_user_id, tenant_id=tenant_id
        ):
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

    def require_default_invitation_role(self, roles_repo, tenant_id: str):
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

    def revoke_affected_sessions(
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

    def record_membership_audit(
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
            changed_fields={"status": {"before": old_status, "after": new_status}},
            tenant_id=tenant_id,
            severity="high",
            category="SECURITY",
            metadata={"action": action, **metadata},
        )
        audit_repo.add_for_tenant(entry, tenant_id)
