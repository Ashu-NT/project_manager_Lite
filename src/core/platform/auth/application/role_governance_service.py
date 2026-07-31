from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditRepository
from src.core.platform.audit.domain import AuditEntry
from src.core.platform.auth.authorization import (
    authorization_denied,
    record_authorization_denial,
    require_permission,
)
from src.core.platform.auth.contracts import (
    PermissionRepository,
    RoleBindingRepository,
    RoleDelegationPolicyRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.auth.domain import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    Role,
    RoleBinding,
    RoleDelegationPolicy,
    UserSessionContext,
    normalize_role_scope_type,
)
from src.core.platform.auth.sod import SeparationOfDutiesPolicy
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.platform.tenancy.tenant_context import TenantContextService
from src.core.shared.events.domain_events import domain_events


ScopeExistsResolver = Callable[[str, str], bool]
ROLE_ASSIGN_PERMISSION = "auth.role.assign"


class RoleGovernanceService:
    """Fail-closed canonical role delegation and binding mutations."""

    def __init__(
        self,
        *,
        session: Session,
        role_repo: RoleRepository,
        role_binding_repo: RoleBindingRepository,
        delegation_repo: RoleDelegationPolicyRepository,
        role_permission_repo: RolePermissionRepository,
        permission_repo: PermissionRepository,
        user_repo: UserRepository,
        tenant_repo: TenantRepository,
        membership_repo: UserTenantMembershipRepository,
        audit_repo: AuditRepository,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
        scope_exists_resolvers: dict[str, ScopeExistsResolver] | None = None,
        sod_policy: SeparationOfDutiesPolicy | None = None,
        allow_platform_customer_context: bool = False,
    ) -> None:
        self._session = session
        self._role_repo = role_repo
        self._role_binding_repo = role_binding_repo
        self._delegation_repo = delegation_repo
        self._role_permission_repo = role_permission_repo
        self._permission_repo = permission_repo
        self._user_repo = user_repo
        self._tenant_repo = tenant_repo
        self._membership_repo = membership_repo
        self._audit_repo = audit_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._scope_exists_resolvers = {
            normalize_role_scope_type(scope_type): resolver
            for scope_type, resolver in dict(
                scope_exists_resolvers or {}
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
        actor_role = self._require_role(actor_role_id)
        assignable_role = self._require_assignable_role(
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
            self._require_active_tenant(normalized_tenant_id)

        permission_hash = self._permission_set_hash(assignable_role.id)
        existing = self._delegation_repo.get_active_exact(
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
        try:
            self._delegation_repo.add(policy)
            self._record_audit(
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
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
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
        policy = self._delegation_repo.get(str(policy_id or "").strip())
        if policy is None:
            raise NotFoundError(
                "Role delegation policy not found.",
                code="ROLE_DELEGATION_POLICY_NOT_FOUND",
            )
        if policy.revoked_at is not None:
            return policy
        revoked_at = datetime.now(timezone.utc)
        try:
            self._delegation_repo.revoke(policy.id, revoked_at=revoked_at)
            self._record_audit(
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
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return replace(policy, revoked_at=revoked_at)

    def assign_role(
        self,
        *,
        target_user_id: str,
        role_id: str,
        actual_scope_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> RoleBinding:
        actor, tenant_id = self._require_tenant_actor(
            operation_label="assign a canonical role"
        )
        target = self._user_repo.get(str(target_user_id or "").strip())
        if target is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        if not target.is_active:
            raise BusinessRuleError(
                "Canonical roles cannot be assigned to an inactive user.",
                code="ROLE_TARGET_USER_INACTIVE",
            )
        self._require_active_membership(
            target.id,
            tenant_id,
            code="ROLE_TARGET_TENANT_DENIED",
        )

        role = self._require_role(role_id)
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
            role.id,
            tenant_id=tenant_id,
            target_scope_type=scope_type,
        )
        normalized_scope_id = str(actual_scope_id or "").strip() or None
        self._validate_target_scope(
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=normalized_scope_id,
        )
        self._require_delegation(
            actor_user_id=actor.user_id,
            role=role,
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=normalized_scope_id,
            enforce_permission_snapshot=True,
        )
        self._enforce_target_separation_of_duties(
            target.id,
            tenant_id=tenant_id,
            additional_role_id=role.id,
        )

        now = datetime.now(timezone.utc)
        self._role_binding_repo.revoke_expired_for_assignment(
            principal_id=target.id,
            role_id=role.id,
            tenant_id=tenant_id,
            actual_scope_type=scope_type,
            actual_scope_id=normalized_scope_id,
            as_of=now,
        )
        existing = self._role_binding_repo.get_active_for_assignment(
            principal_id=target.id,
            role_id=role.id,
            tenant_id=tenant_id,
            actual_scope_type=scope_type,
            actual_scope_id=normalized_scope_id,
        )
        if existing is not None:
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
            self._role_binding_repo.add(binding)
            self._record_audit(
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
                    "expires_at": (
                        binding.expires_at.isoformat()
                        if binding.expires_at is not None
                        else None
                    ),
                },
            )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            existing = self._role_binding_repo.get_active_for_assignment(
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
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        domain_events.auth_changed.emit(target.id)
        return binding

    def revoke_role_binding(self, binding_id: str) -> RoleBinding:
        actor, tenant_id = self._require_tenant_actor(
            operation_label="revoke a canonical role"
        )
        binding = self._role_binding_repo.get(str(binding_id or "").strip())
        if binding is None or binding.tenant_id != tenant_id:
            raise NotFoundError(
                "Role binding not found.",
                code="ROLE_BINDING_NOT_FOUND",
            )
        if binding.revoked_at is not None:
            return binding
        role = self._require_role(binding.role_id)
        self._require_delegation(
            actor_user_id=actor.user_id,
            role=role,
            tenant_id=tenant_id,
            scope_type=binding.actual_scope_type,
            scope_id=binding.actual_scope_id,
            enforce_permission_snapshot=False,
        )
        revoked_at = datetime.now(timezone.utc)
        try:
            self._role_binding_repo.revoke(
                binding.id,
                revoked_at=revoked_at,
            )
            self._record_audit(
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
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
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

    def _require_tenant_actor(self, *, operation_label: str):
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
        self._require_active_tenant(tenant_id)
        self._require_active_membership(
            actor.user_id,
            tenant_id,
            code="TENANT_ACCESS_DENIED",
        )
        return actor, tenant_id

    def _require_active_tenant(self, tenant_id: str) -> None:
        tenant = self._tenant_repo.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if not tenant.is_active:
            raise BusinessRuleError(
                "Role governance requires an active tenant.",
                code="TENANT_INACTIVE",
            )

    def _require_active_membership(
        self,
        user_id: str,
        tenant_id: str,
        *,
        code: str,
    ) -> None:
        if self._membership_repo.is_active_member(user_id, tenant_id):
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

    def _require_role(self, role_id: str) -> Role:
        role = self._role_repo.get(str(role_id or "").strip())
        if role is None:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        return role

    def _require_assignable_role(
        self,
        role_id: str,
        *,
        tenant_id: str | None,
        target_scope_type: str,
    ) -> Role:
        role = self._require_role(role_id)
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
        tenant_id: str,
        scope_type: str,
        scope_id: str | None,
    ) -> None:
        if scope_type == ROLE_SCOPE_TENANT:
            if scope_id is not None:
                raise ValidationError(
                    "Tenant role assignments cannot carry a resource id.",
                    code="AUTH_ROLE_BINDING_SCOPE_INVALID",
                )
            return
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
        if not resolver(tenant_id, scope_id):
            raise NotFoundError(
                f"{scope_type.title()} not found.",
                code=f"{scope_type.upper()}_NOT_FOUND",
            )

    def _require_delegation(
        self,
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
        actor_bindings = self._role_binding_repo.list_active_for_principal(
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
        policy = self._delegation_repo.find_active(
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
            != self._permission_set_hash(role.id)
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

    def _permission_codes_for_role(self, role_id: str) -> set[str]:
        permission_codes_by_id = {
            permission.id: permission.code
            for permission in self._permission_repo.list_all()
        }
        return {
            permission_codes_by_id[permission_id]
            for permission_id in self._role_permission_repo.list_permission_ids(
                role_id
            )
            if permission_id in permission_codes_by_id
        }

    def _permission_set_hash(self, role_id: str) -> str:
        canonical = json.dumps(
            sorted(self._permission_codes_for_role(role_id)),
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _enforce_target_separation_of_duties(
        self,
        target_user_id: str,
        *,
        tenant_id: str,
        additional_role_id: str,
    ) -> None:
        role_ids = {
            binding.role_id
            for binding in self._role_binding_repo.list_active_for_principal(
                target_user_id,
                tenant_id=tenant_id,
            )
        }
        role_ids.add(additional_role_id)
        permission_codes = {
            permission_code
            for role_id in role_ids
            for permission_code in self._permission_codes_for_role(role_id)
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
            self._audit_repo.add_platform(entry)
        else:
            self._audit_repo.add_for_tenant(entry, tenant_id)


__all__ = [
    "ROLE_ASSIGN_PERMISSION",
    "RoleGovernanceService",
    "ScopeExistsResolver",
]
