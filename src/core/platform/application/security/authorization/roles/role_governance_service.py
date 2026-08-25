from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    authorization_denied,
    record_authorization_denial,
    require_permission,
)
from src.core.platform.contract.persistence.role_governance_unit_of_work import (
    RoleGovernanceUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth import (
    Role,
    UserSessionContext,
)
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    RoleBinding,
    RoleBindingAssigned,
    RoleBindingPlatformScope,
    RoleBindingResourceScope,
    RoleBindingRevoked,
    RoleBindingScope,
    RoleBindingTenantScope,
    RoleDelegationPolicy,
    normalize_role_scope_type,
)
from src.core.platform.application.security.authorization.roles.role_binding_scope import (
    ResolvedRoleBindingScope,
    ResourceBindingScope,
    TenantBindingScope,
)
from src.core.platform.domain.security.authorization.enforcement.sod import SeparationOfDutiesPolicy
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.time.clock import Clock


ROLE_ASSIGN_PERMISSION = "auth.role.assign"

ScopeExistsResolver = Callable[[Session, str, str], bool]
OrganizationOwnerResolver = Callable[[Session, str, str], "str | None"]


class RoleGovernanceService:
    """Fail-closed canonical role delegation and binding mutations."""

    def __init__(
        self,
        *,
        uow_factory: RoleGovernanceUnitOfWorkFactory,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
        clock: Clock,
        scope_exists_resolvers: dict[str, ScopeExistsResolver] | None = None,
        organization_owner_resolvers: dict[str, OrganizationOwnerResolver] | None = None,
        sod_policy: SeparationOfDutiesPolicy | None = None,
        allow_platform_customer_context: bool = False,
    ) -> None:
        self._uow_factory = uow_factory
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._clock = clock
        self._scope_exists_resolvers = {
            normalize_role_scope_type(scope_type): resolver
            for scope_type, resolver in dict(
                scope_exists_resolvers or {}
            ).items()
        }
        self._organization_owner_resolvers = {
            normalize_role_scope_type(scope_type): resolver
            for scope_type, resolver in dict(
                organization_owner_resolvers or {}
            ).items()
        }
        self._sod_policy = sod_policy or SeparationOfDutiesPolicy()
        self._allow_platform_customer_context = bool(
            allow_platform_customer_context
        )

    def register_scope_exists_resolver(
        self,
        scope_type: str,
        resolver: ScopeExistsResolver,
    ) -> None:
        self._scope_exists_resolvers[
            normalize_role_scope_type(scope_type)
        ] = resolver

    def register_organization_owner_resolver(
        self,
        scope_type: str,
        resolver: OrganizationOwnerResolver,
    ) -> None:
        """P5C-1: resolves a RESOURCE-scoped binding's authoritative organization owner
        (never the ambient active organization) -- so a future P5C-2 `RoleBindingAssigned`/
        `Revoked` event can carry `organization_id` without a post-commit re-query. Returns
        `None` only when the specific resource instance genuinely has no organization owner."""
        self._organization_owner_resolvers[
            normalize_role_scope_type(scope_type)
        ] = resolver

    def _new_context(self) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id())

    def create_delegation_policy(
        self,
        *,
        actor_role_id: str,
        assignable_role_id: str,
        target_scope_type: str,
        tenant_id: str | None = None,
    ) -> RoleDelegationPolicy:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="create role delegation policy",
        )
        actor = self._require_principal()
        normalized_tenant_id = str(tenant_id or "").strip() or None
        normalized_scope_type = normalize_role_scope_type(target_scope_type)

        with self._uow_factory.create(context=self._new_context()) as uow:
            actor_role = self._require_role(uow.roles, actor_role_id)
            assignable_role = self._require_assignable_role(
                uow.roles,
                assignable_role_id,
                tenant_id=normalized_tenant_id,
                target_scope_type=normalized_scope_type,
            )
            self._validate_delegation_namespace(
                actor_role,
                assignable_role,
                tenant_id=normalized_tenant_id,
            )
            if normalized_tenant_id is not None:
                self._require_active_tenant(uow.tenants, normalized_tenant_id)

            permission_hash = self._permission_set_hash(
                uow.permissions, uow.role_permissions, assignable_role.id
            )
            existing = uow.role_delegation_policies.get_active_exact(
                actor_role_id=actor_role.id,
                assignable_role_id=assignable_role.id,
                tenant_id=normalized_tenant_id,
                target_scope_type=normalized_scope_type,
            )
            if existing is not None:
                if (
                    existing.assignable_role_policy_version
                    == assignable_role.policy_version
                    and existing.assignable_permission_set_hash
                    == permission_hash
                ):
                    return existing
                authorization_denied(
                    self._user_session,
                    message=(
                        "The active delegation policy no longer matches the role "
                        "definition and must be explicitly replaced."
                    ),
                    code="ROLE_DELEGATION_POLICY_REVIEW_REQUIRED",
                    operation_label="create role delegation policy",
                    target_scope_type="role",
                    target_scope_id=assignable_role.id,
                    operation="authorization.delegation.denied",
                )

            policy = RoleDelegationPolicy.create(
                tenant_id=normalized_tenant_id,
                actor_role_id=actor_role.id,
                assignable_role_id=assignable_role.id,
                target_scope_type=normalized_scope_type,
                assignable_role_policy_version=assignable_role.policy_version,
                assignable_permission_set_hash=permission_hash,
                created_by=actor.user_id,
            )
            uow.role_delegation_policies.add(policy)
            self._record_audit(
                uow.audit,
                actor=actor,
                tenant_id=normalized_tenant_id,
                operation="create",
                entity_type="role_delegation_policy",
                entity_id=policy.id,
                action="auth.role.delegation.created",
                metadata={
                    "actor_role_id": actor_role.id,
                    "assignable_role_id": assignable_role.id,
                    "target_scope_type": normalized_scope_type,
                    "assignable_role_policy_version": (
                        assignable_role.policy_version
                    ),
                    "assignable_permission_set_hash": permission_hash,
                },
            )
            uow.commit()
        return policy

    def revoke_delegation_policy(
        self,
        policy_id: str,
    ) -> RoleDelegationPolicy:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="revoke role delegation policy",
        )
        actor = self._require_principal()

        with self._uow_factory.create(context=self._new_context()) as uow:
            policy = uow.role_delegation_policies.get(str(policy_id or "").strip())
            if policy is None:
                raise NotFoundError(
                    "Role delegation policy not found.",
                    code="ROLE_DELEGATION_POLICY_NOT_FOUND",
                )
            if policy.revoked_at is not None:
                return policy
            revoked_at = datetime.now(timezone.utc)
            uow.role_delegation_policies.revoke(policy.id, revoked_at=revoked_at)
            self._record_audit(
                uow.audit,
                actor=actor,
                tenant_id=policy.tenant_id,
                operation="delete",
                entity_type="role_delegation_policy",
                entity_id=policy.id,
                action="auth.role.delegation.revoked",
                metadata={
                    "actor_role_id": policy.actor_role_id,
                    "assignable_role_id": policy.assignable_role_id,
                    "target_scope_type": policy.target_scope_type,
                },
            )
            uow.commit()
        return replace(policy, revoked_at=revoked_at)

    def assign_role(
        self,
        *,
        target_user_id: str,
        role_id: str,
        actual_scope_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> RoleBinding:
        with self._uow_factory.create(context=self._new_context()) as uow:
            actor, tenant_id = self._require_tenant_actor(
                uow.tenants, uow.memberships, operation_label="assign a canonical role"
            )
            target = uow.users.get(str(target_user_id or "").strip())
            if target is None:
                raise NotFoundError("User not found.", code="USER_NOT_FOUND")
            if not target.is_active:
                raise BusinessRuleError(
                    "Canonical roles cannot be assigned to an inactive user.",
                    code="ROLE_TARGET_USER_INACTIVE",
                )
            self._require_active_membership(
                uow.memberships,
                target.id,
                tenant_id,
                code="ROLE_TARGET_TENANT_DENIED",
            )

            role = self._require_role(uow.roles, role_id)
            scope_type = role.allowed_scope_type
            if scope_type == ROLE_SCOPE_PLATFORM:
                authorization_denied(
                    self._user_session,
                    message=(
                        "Platform roles cannot be assigned through a customer "
                        "tenant operation."
                    ),
                    code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
                    operation_label="assign a canonical role",
                    target_scope_type="role",
                    target_scope_id=role.id,
                    operation="authorization.permission_ceiling.denied",
                )
            role = self._require_assignable_role(
                uow.roles,
                role.id,
                tenant_id=tenant_id,
                target_scope_type=scope_type,
            )
            normalized_scope_id = str(actual_scope_id or "").strip() or None
            resolved_scope = self._validate_target_scope(
                session=uow.session,
                tenant_id=tenant_id,
                scope_type=scope_type,
                scope_id=normalized_scope_id,
            )
            self._require_delegation(
                uow.role_bindings,
                uow.role_delegation_policies,
                uow.permissions,
                uow.role_permissions,
                actor_user_id=actor.user_id,
                role=role,
                tenant_id=tenant_id,
                scope_type=scope_type,
                scope_id=normalized_scope_id,
                enforce_permission_snapshot=True,
            )
            self._enforce_target_separation_of_duties(
                uow.role_bindings,
                uow.permissions,
                uow.role_permissions,
                target_user_id=target.id,
                tenant_id=tenant_id,
                additional_role_id=role.id,
            )

            now = datetime.now(timezone.utc)
            uow.role_bindings.revoke_expired_for_assignment(
                principal_id=target.id,
                role_id=role.id,
                tenant_id=tenant_id,
                actual_scope_type=scope_type,
                actual_scope_id=normalized_scope_id,
                as_of=now,
            )
            existing = uow.role_bindings.get_active_for_assignment(
                principal_id=target.id,
                role_id=role.id,
                tenant_id=tenant_id,
                actual_scope_type=scope_type,
                actual_scope_id=normalized_scope_id,
            )
            if existing is not None:
                # No-op: an identical active binding already exists -- no write, no audit.
                # P5C-2 rule (already true here): no transition -> no event.
                return existing

            binding = RoleBinding.create(
                principal_id=target.id,
                role_id=role.id,
                tenant_id=tenant_id,
                actual_scope_type=scope_type,
                actual_scope_id=normalized_scope_id,
                assigned_by=actor.user_id,
                expires_at=expires_at,
            )
            try:
                uow.role_bindings.add(binding)
                self._record_audit(
                    uow.audit,
                    actor=actor,
                    tenant_id=tenant_id,
                    operation="permission_change",
                    entity_type="role_binding",
                    entity_id=binding.id,
                    action="auth.role.binding.assigned",
                    metadata={
                        "target_user_id": target.id,
                        "role_id": role.id,
                        "scope_type": scope_type,
                        "scope_id": normalized_scope_id,
                        "organization_id": _resolved_organization_id(resolved_scope),
                        "expires_at": (
                            binding.expires_at.isoformat()
                            if binding.expires_at is not None
                            else None
                        ),
                    },
                )

                uow.record_event(
                    RoleBindingAssigned(
                        binding_id=binding.id,
                        principal_id=target.id,
                        role_id=role.id,
                        scope=self._to_domain_scope(resolved_scope),
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError:
                existing = uow.role_bindings.get_active_for_assignment(
                    principal_id=target.id,
                    role_id=role.id,
                    tenant_id=tenant_id,
                    actual_scope_type=scope_type,
                    actual_scope_id=normalized_scope_id,
                )
                if existing is not None:
                    return existing
                raise BusinessRuleError(
                    "The canonical role was assigned concurrently.",
                    code="ROLE_BINDING_CONCURRENT_ASSIGNMENT",
                )
        # Post-commit, outside the `with` block (the UoW is already closed): the legacy
        # notification and the current-principal runtime-authorization refresh, in that order.
        # Never before commit -- a rolled-back transaction must never be observable here.
        domain_events.auth_changed.emit(target.id)
        return binding

    def revoke_role_binding(self, binding_id: str) -> RoleBinding:
        with self._uow_factory.create(context=self._new_context()) as uow:
            actor, tenant_id = self._require_tenant_actor(
                uow.tenants, uow.memberships, operation_label="revoke a canonical role"
            )
            binding = uow.role_bindings.get(str(binding_id or "").strip())
            if binding is None or binding.tenant_id != tenant_id:
                raise NotFoundError(
                    "Role binding not found.",
                    code="ROLE_BINDING_NOT_FOUND",
                )
            if binding.revoked_at is not None:
                # No-op: already revoked -- no write, no audit. Same P5C-2 rule as above.
                return binding
            role = self._require_role(uow.roles, binding.role_id)
            self._require_delegation(
                uow.role_bindings,
                uow.role_delegation_policies,
                uow.permissions,
                uow.role_permissions,
                actor_user_id=actor.user_id,
                role=role,
                tenant_id=tenant_id,
                scope_type=binding.actual_scope_type,
                scope_id=binding.actual_scope_id,
                enforce_permission_snapshot=False,
            )
            # Captured BEFORE mutation (item 13): the authoritative scope identity for the
            # event must reflect the binding as it was administered, never re-derived from the
            # current desktop UI scope after the fact.
            domain_scope = self._resolve_domain_scope_for_binding(
                session=uow.session,
                tenant_id=tenant_id,
                scope_type=binding.actual_scope_type,
                scope_id=binding.actual_scope_id,
            )
            revoked_at = datetime.now(timezone.utc)
            uow.role_bindings.revoke(
                binding.id,
                revoked_at=revoked_at,
            )
            self._record_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                operation="delete",
                entity_type="role_binding",
                entity_id=binding.id,
                action="auth.role.binding.revoked",
                metadata={
                    "target_user_id": binding.principal_id,
                    "role_id": binding.role_id,
                    "scope_type": binding.actual_scope_type,
                    "scope_id": binding.actual_scope_id,
                },
            )
            # P5C-2: the ONE canonical RoleBinding revocation fact, mirroring `assign_role`'s
            # own recording point exactly.
            uow.record_event(
                RoleBindingRevoked(
                    binding_id=binding.id,
                    principal_id=binding.principal_id,
                    role_id=binding.role_id,
                    scope=domain_scope,
                    occurred_at=self._clock.now(),
                )
            )
            uow.commit()
        domain_events.auth_changed.emit(binding.principal_id)
        return replace(
            binding,
            revoked_at=revoked_at,
            version=binding.version + 1,
        )

    def _require_principal(self):
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required for role governance.",
                code="AUTHENTICATION_REQUIRED",
            )
        return principal

    def _require_tenant_actor(self, tenant_repo, membership_repo, *, operation_label: str):
        require_permission(
            self._user_session,
            ROLE_ASSIGN_PERMISSION,
            operation_label=operation_label,
        )
        actor = self._require_principal()
        if (
            "platform.admin" in actor.permissions
            and not self._allow_platform_customer_context
        ):
            authorization_denied(
                self._user_session,
                message=(
                    "Platform operators cannot perform ordinary customer role "
                    "assignments without a governed support context."
                ),
                code="PLATFORM_CUSTOMER_OPERATION_DENIED",
                operation_label=operation_label,
                target_scope_type="tenant",
                operation="authorization.support_access.denied",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label=operation_label
        )
        self._require_active_tenant(tenant_repo, tenant_id)
        self._require_active_membership(
            membership_repo,
            actor.user_id,
            tenant_id,
            code="TENANT_ACCESS_DENIED",
        )
        return actor, tenant_id

    def _require_active_tenant(self, tenant_repo, tenant_id: str) -> None:
        tenant = tenant_repo.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if not tenant.is_active:
            raise BusinessRuleError(
                "Role governance requires an active tenant.",
                code="TENANT_INACTIVE",
            )

    def _require_active_membership(
        self,
        membership_repo,
        user_id: str,
        tenant_id: str,
        *,
        code: str,
    ) -> None:
        if membership_repo.is_active_member(user_id, tenant_id):
            return
        authorization_denied(
            self._user_session,
            message="The user is not an active member of the selected tenant.",
            code=code,
            operation_label="govern a canonical role binding",
            target_scope_type="user",
            target_scope_id=user_id,
            operation="authorization.membership.denied",
        )

    def _require_role(self, role_repo, role_id: str) -> Role:
        role = role_repo.get(str(role_id or "").strip())
        if role is None:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        return role

    def _require_assignable_role(
        self,
        role_repo,
        role_id: str,
        *,
        tenant_id: str | None,
        target_scope_type: str,
    ) -> Role:
        role = self._require_role(role_repo, role_id)
        if role.status != "active" or not role.is_assignable:
            authorization_denied(
                self._user_session,
                message="The selected role is not assignable.",
                code="ROLE_NOT_ASSIGNABLE",
                operation_label="assign or delegate a canonical role",
                target_scope_type="role",
                target_scope_id=role.id,
                operation="authorization.delegation.denied",
            )
        if role.allowed_scope_type != target_scope_type:
            authorization_denied(
                self._user_session,
                message="The role cannot be assigned at the requested scope.",
                code="ROLE_SCOPE_MISMATCH",
                operation_label="assign or delegate a canonical role",
                target_scope_type=target_scope_type,
                operation="authorization.resource_scope.denied",
            )
        if role.tenant_id is not None and role.tenant_id != tenant_id:
            authorization_denied(
                self._user_session,
                message="A tenant-owned role cannot be used outside its tenant.",
                code="ROLE_CROSS_TENANT_DENIED",
                operation_label="assign or delegate a canonical role",
                target_scope_type="role",
                target_scope_id=role.id,
                operation="authorization.tenant_boundary.denied",
            )
        return role

    def _validate_delegation_namespace(
        self,
        actor_role: Role,
        assignable_role: Role,
        *,
        tenant_id: str | None,
    ) -> None:
        allowed_tenant_ids = {None, tenant_id}
        if (
            actor_role.tenant_id not in allowed_tenant_ids
            or assignable_role.tenant_id not in allowed_tenant_ids
        ):
            authorization_denied(
                self._user_session,
                message="Delegation roles do not belong to the policy tenant.",
                code="ROLE_DELEGATION_CROSS_TENANT_DENIED",
                operation_label="validate role delegation namespace",
                target_scope_type="role",
                target_scope_id=assignable_role.id,
                operation="authorization.delegation.denied",
            )
        if tenant_id is None and (
            actor_role.tenant_id is not None
            or assignable_role.tenant_id is not None
        ):
            authorization_denied(
                self._user_session,
                message="Global delegation policies may reference only system roles.",
                code="ROLE_DELEGATION_NAMESPACE_INVALID",
                operation_label="validate role delegation namespace",
                target_scope_type="role",
                target_scope_id=assignable_role.id,
                operation="authorization.delegation.denied",
            )
        if actor_role.status != "active":
            authorization_denied(
                self._user_session,
                message="The delegating actor role is not active.",
                code="ROLE_DELEGATION_ACTOR_INACTIVE",
                operation_label="validate role delegation namespace",
                target_scope_type="role",
                target_scope_id=actor_role.id,
                operation="authorization.delegation.denied",
            )

    def _validate_target_scope(
        self,
        *,
        session: Session,
        tenant_id: str,
        scope_type: str,
        scope_id: str | None,
    ) -> ResolvedRoleBindingScope:
        if scope_type == ROLE_SCOPE_TENANT:
            if scope_id is not None:
                raise ValidationError(
                    "Tenant role assignments cannot carry a resource id.",
                    code="AUTH_ROLE_BINDING_SCOPE_INVALID",
                )
            return TenantBindingScope(tenant_id=tenant_id)
        if scope_type == ROLE_SCOPE_PLATFORM or scope_id is None:
            raise ValidationError(
                "Resource role assignments require a resource id.",
                code="AUTH_ROLE_BINDING_SCOPE_INVALID",
            )
        resolver = self._scope_exists_resolvers.get(scope_type)
        if resolver is None:
            authorization_denied(
                self._user_session,
                message=(
                    f"Tenant ownership validation is not configured for "
                    f"{scope_type}."
                ),
                code="AUTHORIZATION_SCOPE_RESOLVER_REQUIRED",
                operation_label="validate canonical role target scope",
                target_scope_type=scope_type,
                target_scope_id=scope_id,
                operation="authorization.infrastructure.denied",
            )

        if not resolver(session, tenant_id, scope_id):
            raise NotFoundError(
                f"{scope_type.title()} not found.",
                code=f"{scope_type.upper()}_NOT_FOUND",
            )
        organization_owner_resolver = self._organization_owner_resolvers.get(scope_type)
        organization_id = (
            organization_owner_resolver(session, tenant_id, scope_id)
            if organization_owner_resolver is not None
            else None
        )
        return ResourceBindingScope(
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            organization_id=organization_id,
        )

    @staticmethod
    def _to_domain_scope(resolved: ResolvedRoleBindingScope) -> RoleBindingScope:

        if isinstance(resolved, ResourceBindingScope):
            return RoleBindingResourceScope(
                tenant_id=resolved.tenant_id,
                organization_id=resolved.organization_id,
                scope_type=resolved.scope_type,
                scope_id=resolved.scope_id,
            )
        if isinstance(resolved, TenantBindingScope):
            return RoleBindingTenantScope(tenant_id=resolved.tenant_id)
        return RoleBindingPlatformScope()

    def _resolve_domain_scope_for_binding(
        self,
        *,
        session: Session,
        tenant_id: str,
        scope_type: str,
        scope_id: str | None,
    ) -> RoleBindingScope:

        if scope_type == ROLE_SCOPE_TENANT:
            return RoleBindingTenantScope(tenant_id=tenant_id)
        if scope_type == ROLE_SCOPE_PLATFORM or scope_id is None:
            return RoleBindingPlatformScope()
        organization_owner_resolver = self._organization_owner_resolvers.get(scope_type)
        organization_id = (
            organization_owner_resolver(session, tenant_id, scope_id)
            if organization_owner_resolver is not None
            else None
        )
        return RoleBindingResourceScope(
            tenant_id=tenant_id,
            organization_id=organization_id,
            scope_type=scope_type,
            scope_id=scope_id,
        )

    def _require_delegation(
        self,
        role_binding_repo,
        delegation_repo,
        permission_repo,
        role_permission_repo,
        *,
        actor_user_id: str,
        role: Role,
        tenant_id: str,
        scope_type: str,
        scope_id: str | None,
        enforce_permission_snapshot: bool,
    ) -> RoleDelegationPolicy | None:
        principal = self._require_principal()
        if (
            principal.user_id == actor_user_id
            and "platform.admin" in principal.permissions
            and self._allow_platform_customer_context
        ):
            return None
        actor_bindings = role_binding_repo.list_active_for_principal(
            actor_user_id,
            tenant_id=tenant_id,
        )
        applicable_actor_role_ids = {
            binding.role_id
            for binding in actor_bindings
            if self._binding_administers_scope(
                binding,
                scope_type=scope_type,
                scope_id=scope_id,
            )
        }
        policy = delegation_repo.find_active(
            actor_role_ids=applicable_actor_role_ids,
            assignable_role_id=role.id,
            tenant_id=tenant_id,
            target_scope_type=scope_type,
        )
        if policy is None:
            authorization_denied(
                self._user_session,
                message="No explicit delegation policy permits this role assignment.",
                code="ROLE_DELEGATION_DENIED",
                operation_label="govern a canonical role binding",
                target_scope_type=scope_type,
                target_scope_id=scope_id,
                operation="authorization.delegation.denied",
            )
        if enforce_permission_snapshot and (
            policy.assignable_role_policy_version != role.policy_version
            or policy.assignable_permission_set_hash
            != self._permission_set_hash(permission_repo, role_permission_repo, role.id)
        ):
            authorization_denied(
                self._user_session,
                message="The delegated role changed after policy approval.",
                code="ROLE_DELEGATION_POLICY_STALE",
                operation_label="govern a canonical role binding",
                target_scope_type="role",
                target_scope_id=role.id,
                operation="authorization.delegation.denied",
            )
        return policy

    @staticmethod
    def _binding_administers_scope(
        binding: RoleBinding,
        *,
        scope_type: str,
        scope_id: str | None,
    ) -> bool:
        if binding.actual_scope_type == ROLE_SCOPE_TENANT:
            return True
        return (
            binding.actual_scope_type == scope_type
            and binding.actual_scope_id == scope_id
        )

    def _permission_codes_for_role(self, permission_repo, role_permission_repo, role_id: str) -> set[str]:
        permission_codes_by_id = {
            permission.id: permission.code
            for permission in permission_repo.list_all()
        }
        return {
            permission_codes_by_id[permission_id]
            for permission_id in role_permission_repo.list_permission_ids(
                role_id
            )
            if permission_id in permission_codes_by_id
        }

    def _permission_set_hash(self, permission_repo, role_permission_repo, role_id: str) -> str:
        canonical = json.dumps(
            sorted(self._permission_codes_for_role(permission_repo, role_permission_repo, role_id)),
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _enforce_target_separation_of_duties(
        self,
        role_binding_repo,
        permission_repo,
        role_permission_repo,
        *,
        target_user_id: str,
        tenant_id: str,
        additional_role_id: str,
    ) -> None:
        role_ids = {
            binding.role_id
            for binding in role_binding_repo.list_active_for_principal(
                target_user_id,
                tenant_id=tenant_id,
            )
        }
        role_ids.add(additional_role_id)
        permission_codes = {
            permission_code
            for role_id in role_ids
            for permission_code in self._permission_codes_for_role(
                permission_repo, role_permission_repo, role_id
            )
        }
        conflicts = self._sod_policy.find_conflicts(permission_codes)
        if conflicts:
            record_authorization_denial(
                self._user_session,
                operation_label="validate canonical role separation of duties",
                reason_code="ROLE_CONFLICT",
                required_permissions=permission_codes,
                target_scope_type="user",
                target_scope_id=target_user_id,
                operation="authorization.sod.denied",
            )
            raise ValidationError(
                f"Role assignment violates separation of duties. "
                f"{conflicts[0]}",
                code="ROLE_CONFLICT",
            )

    def _record_audit(
        self,
        audit_repo,
        *,
        actor,
        tenant_id: str | None,
        operation: str,
        entity_type: str,
        entity_id: str,
        action: str,
        metadata: dict[str, object],
    ) -> None:
        entry = AuditEntry.create(
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=tenant_id,
            module="platform",
            actor_id=actor.user_id,
            actor_username=actor.username,
            tenant_id=tenant_id,
            severity="high",
            compliance_tag="SOC2",
            metadata={"action": action, **metadata},
        )
        if tenant_id is None:
            audit_repo.add_platform(entry)
        else:
            audit_repo.add_for_tenant(entry, tenant_id)


def _resolved_organization_id(resolved_scope: ResolvedRoleBindingScope) -> str | None:
    return getattr(resolved_scope, "organization_id", None)


__all__ = [
    "ROLE_ASSIGN_PERMISSION",
    "RoleGovernanceService",
    "ScopeExistsResolver",
    "OrganizationOwnerResolver",
]
