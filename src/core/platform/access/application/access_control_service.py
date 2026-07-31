from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, NoReturn

from sqlalchemy.orm import Session

from src.core.shared.audit import record_audit_entry
from src.core.platform.common.exceptions import (
    NotFoundError,
    ValidationError,
)
from src.core.shared.events.domain_events import domain_events
from src.core.platform.access.contracts import (
    ProjectMembershipRepository,
    ScopedAccessGrantRepository,
)
from src.core.platform.access.domain import (
    ProjectMembership,
    ScopedAccessGrant,
    ScopedRolePolicy,
    ScopedRolePolicyRegistry,
    normalize_access_scope_id,
    normalize_access_scope_type,
    normalize_access_user_id,
)
from src.core.platform.auth.authorization import (
    authorization_denied,
    require_permission,
)
from src.core.platform.auth.contracts import UserRepository

if TYPE_CHECKING:
    from src.core.platform.audit.application.enterprise_audit_service import EnterpriseAuditService
    from src.core.platform.auth import UserSessionContext
    from src.core.platform.auth.application.auth_service import AuthService
    from src.core.platform.auth.application.role_governance_service import RoleGovernanceService
    from src.core.platform.auth.contracts import RoleBindingRepository, RoleRepository
    from src.core.platform.tenancy.contracts import UserTenantMembershipRepository
    from src.core.platform.tenancy.tenant_context import TenantContextService


ScopeExistsResolver = Callable[[str, str], bool]

# RBAC-TRANSITION-ONLY: scope types in this set write/read canonical
# role_bindings instead of ScopedAccessGrant/ProjectMembership. The
# ScopedAccessGrant-shaped translation below exists only so the legacy
# desktop API/QML contract keeps working; delete it once those adapters
# consume canonical role names directly, one scope type at a time.
_CANONICAL_SCOPE_TYPES = frozenset({"project"})


class AccessControlService:
    def __init__(
        self,
        *,
        session: Session,
        membership_repo: ProjectMembershipRepository,
        user_repo: UserRepository,
        auth_service: "AuthService",
        policy_registry: ScopedRolePolicyRegistry | None = None,
        scoped_access_repo: ScopedAccessGrantRepository | None = None,
        scope_exists_resolvers: dict[str, ScopeExistsResolver] | None = None,
        user_session: "UserSessionContext | None" = None,
        enterprise_audit_service: "EnterpriseAuditService | None" = None,
        user_tenant_repo: "UserTenantMembershipRepository | None" = None,
        tenant_context_service: "TenantContextService | None" = None,
        role_governance_service: "RoleGovernanceService | None" = None,
        role_repo: "RoleRepository | None" = None,
        role_binding_repo: "RoleBindingRepository | None" = None,
    ) -> None:
        self._session = session
        self._membership_repo = membership_repo
        self._user_repo = user_repo
        self._auth_service = auth_service
        self._policy_registry = policy_registry or ScopedRolePolicyRegistry()
        self._scoped_access_repo = scoped_access_repo
        self._scope_exists_resolvers = {
            self._normalize_scope_type(scope_type): resolver
            for scope_type, resolver in dict(scope_exists_resolvers or {}).items()
        }
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._user_tenant_repo = user_tenant_repo
        self._role_governance_service = role_governance_service
        self._role_repo = role_repo
        self._role_binding_repo = role_binding_repo
        self._tenant_context_service = tenant_context_service

    def register_scope_policy(self, policy: ScopedRolePolicy) -> None:
        self._policy_registry.register(policy)

    def register_scope_exists_resolver(
        self,
        scope_type: str,
        resolver: ScopeExistsResolver,
    ) -> None:
        self._scope_exists_resolvers[self._normalize_scope_type(scope_type)] = resolver

    def list_supported_scope_types(self) -> tuple[str, ...]:
        return self._policy_registry.list_scope_types()

    def list_scope_role_choices(self, scope_type: str) -> tuple[str, ...]:
        return self._require_scope_policy(scope_type).role_choices

    def list_scope_grants(self, scope_type: str, scope_id: str) -> list[ScopedAccessGrant]:
        require_permission(self._user_session, "access.manage", operation_label="list scoped access grants")
        tenant_id = self._require_active_tenant_id(
            operation_label="list scoped access grants"
        )
        normalized_scope_type = self._normalize_scope_type(scope_type)
        normalized_scope_id = normalize_access_scope_id(scope_id)
        self._require_scope_policy(normalized_scope_type)
        self._assert_scope_exists(
            normalized_scope_type,
            normalized_scope_id,
            tenant_id=tenant_id,
        )
        if normalized_scope_type in _CANONICAL_SCOPE_TYPES:
            return self._list_canonical_scope_grants_for_scope(
                normalized_scope_type,
                normalized_scope_id,
                tenant_id=tenant_id,
            )
        if self._scoped_access_repo is not None:
            return self._scoped_access_repo.list_by_scope(normalized_scope_type, normalized_scope_id)
        if normalized_scope_type == "project":
            return [
                membership.as_scoped_access_grant()
                for membership in self._membership_repo.list_by_project(normalized_scope_id)
            ]
        self._raise_unsupported_scope_type(normalized_scope_type)

    def list_user_scope_grants(
        self,
        user_id: str,
        *,
        scope_type: str | None = None,
    ) -> list[ScopedAccessGrant]:
        require_permission(self._user_session, "access.manage", operation_label="list user scoped access grants")
        tenant_id = self._require_active_tenant_id(
            operation_label="list user scoped access grants"
        )
        normalized_user_id = normalize_access_user_id(user_id)
        self._require_target_membership(
            normalized_user_id,
            tenant_id=tenant_id,
            active_only=False,
            operation_label="list scoped access grants",
        )
        normalized_scope_type = (
            self._normalize_scope_type(scope_type)
            if scope_type is not None
            else None
        )
        if normalized_scope_type is not None:
            self._require_scope_policy(normalized_scope_type)
            if normalized_scope_type in _CANONICAL_SCOPE_TYPES:
                return self._list_canonical_scope_grants_for_user(
                    normalized_scope_type,
                    normalized_user_id,
                    tenant_id=tenant_id,
                )
        if self._scoped_access_repo is not None:
            legacy_grants = self._scoped_access_repo.list_by_user(normalized_user_id, scope_type=normalized_scope_type)
        elif normalized_scope_type in (None, "project"):
            legacy_grants = [
                membership.as_scoped_access_grant()
                for membership in self._membership_repo.list_by_user(normalized_user_id)
            ]
            if normalized_scope_type is not None:
                legacy_grants = [grant for grant in legacy_grants if grant.scope_type == normalized_scope_type]
        else:
            self._raise_unsupported_scope_type(normalized_scope_type)
        if normalized_scope_type is None:
            legacy_grants = [grant for grant in legacy_grants if grant.scope_type not in _CANONICAL_SCOPE_TYPES]
            for canonical_scope_type in _CANONICAL_SCOPE_TYPES:
                legacy_grants.extend(
                    self._list_canonical_scope_grants_for_user(
                        canonical_scope_type,
                        normalized_user_id,
                        tenant_id=tenant_id,
                    )
                )
        return legacy_grants

    def list_project_memberships(self, project_id: str) -> list[ProjectMembership]:
        return [
            ProjectMembership.from_scoped_access_grant(grant)
            for grant in self.list_scope_grants("project", project_id)
        ]

    def list_user_memberships(self, user_id: str) -> list[ProjectMembership]:
        return [
            ProjectMembership.from_scoped_access_grant(grant)
            for grant in self.list_user_scope_grants(user_id, scope_type="project")
        ]

    def assign_scope_grant(
        self,
        *,
        scope_type: str,
        scope_id: str,
        user_id: str,
        scope_role: str,
    ) -> ScopedAccessGrant:
        require_permission(self._user_session, "access.manage", operation_label="assign scoped access grant")
        tenant_id = self._require_active_tenant_id(
            operation_label="assign scoped access grant"
        )
        normalized_scope_type = self._normalize_scope_type(scope_type)
        normalized_scope_id = normalize_access_scope_id(scope_id)
        normalized_user_id = normalize_access_user_id(user_id)
        user = self._user_repo.get(normalized_user_id)
        if user is None:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        self._require_target_membership(
            normalized_user_id,
            tenant_id=tenant_id,
            active_only=True,
            operation_label="assign scoped access",
        )
        role_name = self._normalize_scope_role(normalized_scope_type, scope_role)
        permissions = sorted(self._resolve_scope_permissions(normalized_scope_type, role_name))
        if not permissions:
            raise ValidationError("Scope role must resolve to at least one permission.")

        self._assert_scope_exists(
            normalized_scope_type,
            normalized_scope_id,
            tenant_id=tenant_id,
        )
        if normalized_scope_type in _CANONICAL_SCOPE_TYPES:
            grant = self._assign_canonical_scope_grant(
                scope_type=normalized_scope_type,
                scope_id=normalized_scope_id,
                user_id=normalized_user_id,
                role_name=role_name,
                permissions=permissions,
            )
            domain_events.access_changed.emit(normalized_scope_id)
            self._refresh_current_session_if_needed(normalized_user_id)
            return grant

        entity_type = (
            "project_membership"
            if normalized_scope_type == "project"
            else f"{normalized_scope_type}_access_grant"
        )

        if self._scoped_access_repo is not None:
            grant = self._scoped_access_repo.get_for_scope_user(
                normalized_scope_type,
                normalized_scope_id,
                normalized_user_id,
            )
            if grant is None:
                grant = ScopedAccessGrant.create(
                    scope_type=normalized_scope_type,
                    scope_id=normalized_scope_id,
                    user_id=normalized_user_id,
                    scope_role=role_name,
                    permission_codes=permissions,
                )
                self._scoped_access_repo.add(grant)
            else:
                grant.scope_role = role_name
                grant.permission_codes = permissions
                self._scoped_access_repo.update(grant)
        elif normalized_scope_type == "project":
            membership = self._membership_repo.get_for_project_user(normalized_scope_id, normalized_user_id)
            if membership is None:
                membership = ProjectMembership.create(
                    project_id=normalized_scope_id,
                    user_id=normalized_user_id,
                    scope_role=role_name,
                    permission_codes=permissions,
                )
                self._membership_repo.add(membership)
            else:
                membership.scope_role = role_name
                membership.permission_codes = permissions
                self._membership_repo.update(membership)
            grant = membership.as_scoped_access_grant()
        else:
            self._raise_unsupported_scope_type(normalized_scope_type)
        self._session.commit()
        record_audit_entry(
            self,
            operation="permission_change",
            entity_type=entity_type,
            entity_id=grant.id,
            module="platform",
            severity="medium",
            metadata={
                "action": "access.membership.upsert",
                "scope_type": normalized_scope_type,
                "scope_id": normalized_scope_id,
                "username": user.username,
                "scope_role": grant.scope_role,
            },
        )
        domain_events.access_changed.emit(normalized_scope_id)
        self._refresh_current_session_if_needed(normalized_user_id)
        return grant

    def assign_project_membership(
        self,
        *,
        project_id: str,
        user_id: str,
        scope_role: str,
    ) -> ProjectMembership:
        return ProjectMembership.from_scoped_access_grant(
            self.assign_scope_grant(
                scope_type="project",
                scope_id=project_id,
                user_id=user_id,
                scope_role=scope_role,
            )
        )

    def remove_scope_grant(self, *, scope_type: str, scope_id: str, user_id: str) -> None:
        require_permission(self._user_session, "access.manage", operation_label="remove scoped access grant")
        tenant_id = self._require_active_tenant_id(
            operation_label="remove scoped access grant"
        )
        normalized_scope_type = self._normalize_scope_type(scope_type)
        self._require_scope_policy(normalized_scope_type)
        normalized_scope_id = normalize_access_scope_id(scope_id)
        normalized_user_id = normalize_access_user_id(user_id)
        self._require_target_membership(
            normalized_user_id,
            tenant_id=tenant_id,
            active_only=False,
            operation_label="remove scoped access",
        )
        self._assert_scope_exists(
            normalized_scope_type,
            normalized_scope_id,
            tenant_id=tenant_id,
        )
        if normalized_scope_type in _CANONICAL_SCOPE_TYPES:
            self._remove_canonical_scope_grant(
                scope_type=normalized_scope_type,
                scope_id=normalized_scope_id,
                user_id=normalized_user_id,
                tenant_id=tenant_id,
            )
            domain_events.access_changed.emit(normalized_scope_id)
            self._refresh_current_session_if_needed(user_id)
            return
        if self._scoped_access_repo is not None:
            grant = self._scoped_access_repo.get_for_scope_user(
                normalized_scope_type,
                normalized_scope_id,
                normalized_user_id,
            )
        elif normalized_scope_type == "project":
            membership = self._membership_repo.get_for_project_user(normalized_scope_id, normalized_user_id)
            grant = membership.as_scoped_access_grant() if membership is not None else None
        else:
            self._raise_unsupported_scope_type(normalized_scope_type)
        if grant is None:
            not_found_code = "PROJECT_MEMBERSHIP_NOT_FOUND" if normalized_scope_type == "project" else "SCOPED_ACCESS_GRANT_NOT_FOUND"
            not_found_label = "Project membership" if normalized_scope_type == "project" else "Scoped access grant"
            raise NotFoundError(f"{not_found_label} not found.", code=not_found_code)
        user = self._user_repo.get(normalized_user_id)
        if self._scoped_access_repo is not None:
            self._scoped_access_repo.delete(grant.id)
        else:
            self._membership_repo.delete(grant.id)
        entity_type = "project_membership" if normalized_scope_type == "project" else f"{normalized_scope_type}_access_grant"
        self._session.commit()
        record_audit_entry(
            self,
            operation="delete",
            entity_type=entity_type,
            entity_id=grant.id,
            module="platform",
            severity="medium",
            metadata={
                "action": "access.membership.remove",
                "scope_type": normalized_scope_type,
                "scope_id": normalized_scope_id,
                "username": user.username if user is not None else normalized_user_id,
                "scope_role": grant.scope_role,
            },
        )
        domain_events.access_changed.emit(normalized_scope_id)
        self._refresh_current_session_if_needed(user_id)

    def remove_project_membership(self, *, project_id: str, user_id: str) -> None:
        self.remove_scope_grant(scope_type="project", scope_id=project_id, user_id=user_id)

    # RBAC-TRANSITION-ONLY: this block routes _CANONICAL_SCOPE_TYPES scopes to
    # role_bindings while translating results back to the legacy
    # ScopedAccessGrant shape. Delete it once the desktop API/QML adapters
    # consume canonical role names directly for every cut-over scope type.
    def _require_canonical_services(self):
        if (
            self._role_governance_service is None
            or self._role_repo is None
            or self._role_binding_repo is None
        ):
            authorization_denied(
                self._user_session,
                message="Canonical role-governance infrastructure is not configured.",
                code="AUTHORIZATION_INFRASTRUCTURE_REQUIRED",
                operation_label="govern a canonical scope-role grant",
                operation="authorization.infrastructure.denied",
            )
        return self._role_governance_service, self._role_repo, self._role_binding_repo

    @staticmethod
    def _canonical_role_name(scope_type: str, scope_role: str) -> str:
        return f"{scope_type}_{scope_role}"

    @staticmethod
    def _scope_role_from_canonical_role_name(scope_type: str, role_name: str) -> str:
        prefix = f"{scope_type}_"
        return role_name[len(prefix):] if role_name.startswith(prefix) else role_name

    def _canonical_role_names_for_scope(self, scope_type: str) -> tuple[str, ...]:
        return tuple(
            self._canonical_role_name(scope_type, scope_role)
            for scope_role in self.list_scope_role_choices(scope_type)
        )

    def _require_canonical_role(self, role_repo, scope_type: str, scope_role: str):
        role = role_repo.get_by_name(self._canonical_role_name(scope_type, scope_role))
        if role is None:
            authorization_denied(
                self._user_session,
                message=(
                    f"No canonical role is defined for {scope_type} scope role "
                    f"'{scope_role}'."
                ),
                code="AUTHORIZATION_SCOPE_ROLE_UNDEFINED",
                operation_label="govern a canonical scope-role grant",
                target_scope_type=scope_type,
                operation="authorization.infrastructure.denied",
            )
        return role

    def _binding_to_scoped_access_grant(self, binding, *, scope_type: str, role) -> ScopedAccessGrant:
        scope_role = self._scope_role_from_canonical_role_name(scope_type, role.name)
        return ScopedAccessGrant(
            id=binding.id,
            scope_type=scope_type,
            scope_id=binding.actual_scope_id or "",
            user_id=binding.principal_id,
            scope_role=scope_role,
            permission_codes=sorted(self._resolve_scope_permissions(scope_type, scope_role)),
            created_at=binding.assigned_at,
        )

    def _assign_canonical_scope_grant(
        self,
        *,
        scope_type: str,
        scope_id: str,
        user_id: str,
        role_name: str,
        permissions: list[str],
    ) -> ScopedAccessGrant:
        role_governance_service, role_repo, _ = self._require_canonical_services()
        role = self._require_canonical_role(role_repo, scope_type, role_name)
        binding = role_governance_service.assign_role(
            target_user_id=user_id,
            role_id=role.id,
            actual_scope_id=scope_id,
        )
        return ScopedAccessGrant(
            id=binding.id,
            scope_type=scope_type,
            scope_id=scope_id,
            user_id=user_id,
            scope_role=role_name,
            permission_codes=permissions,
            created_at=binding.assigned_at,
        )

    def _remove_canonical_scope_grant(
        self,
        *,
        scope_type: str,
        scope_id: str,
        user_id: str,
        tenant_id: str,
    ) -> None:
        role_governance_service, _, role_binding_repo = self._require_canonical_services()
        bindings = [
            binding
            for binding in role_binding_repo.list_active_for_principal(user_id, tenant_id=tenant_id)
            if binding.actual_scope_type == scope_type and binding.actual_scope_id == scope_id
        ]
        if not bindings:
            raise NotFoundError(
                f"{scope_type.title()} membership not found.",
                code=f"{scope_type.upper()}_MEMBERSHIP_NOT_FOUND",
            )
        for binding in bindings:
            role_governance_service.revoke_role_binding(binding.id)

    def _list_canonical_scope_grants_for_scope(
        self,
        scope_type: str,
        scope_id: str,
        *,
        tenant_id: str,
    ) -> list[ScopedAccessGrant]:
        _, role_repo, role_binding_repo = self._require_canonical_services()
        grants: list[ScopedAccessGrant] = []
        for role_name in self._canonical_role_names_for_scope(scope_type):
            role = role_repo.get_by_name(role_name)
            if role is None:
                continue
            for binding in role_binding_repo.list_active_for_role(role.id, tenant_id=tenant_id):
                if binding.actual_scope_type == scope_type and binding.actual_scope_id == scope_id:
                    grants.append(
                        self._binding_to_scoped_access_grant(binding, scope_type=scope_type, role=role)
                    )
        return grants

    def _list_canonical_scope_grants_for_user(
        self,
        scope_type: str,
        user_id: str,
        *,
        tenant_id: str,
    ) -> list[ScopedAccessGrant]:
        _, role_repo, role_binding_repo = self._require_canonical_services()
        grants: list[ScopedAccessGrant] = []
        for binding in role_binding_repo.list_active_for_principal(user_id, tenant_id=tenant_id):
            if binding.actual_scope_type != scope_type:
                continue
            role = role_repo.get(binding.role_id)
            if role is None:
                continue
            grants.append(
                self._binding_to_scoped_access_grant(binding, scope_type=scope_type, role=role)
            )
        return grants

    def _require_scope_policy(self, scope_type: str) -> ScopedRolePolicy:
        return self._policy_registry.get(scope_type)

    def _normalize_scope_role(self, scope_type: str, scope_role: str) -> str:
        policy = self._require_scope_policy(scope_type)
        normalized_role = str(policy.normalize_role(scope_role)).strip().lower()
        if normalized_role not in policy.role_choices:
            raise ValidationError(
                f"Unsupported scope role '{normalized_role}' for {scope_type}.",
                code="UNSUPPORTED_SCOPE_ROLE",
            )
        return normalized_role

    def _resolve_scope_permissions(self, scope_type: str, scope_role: str) -> set[str]:
        policy = self._require_scope_policy(scope_type)
        return {
            str(code).strip()
            for code in policy.resolve_permissions(scope_role)
            if str(code).strip()
        }

    def _normalize_scope_type(self, scope_type: str) -> str:
        return normalize_access_scope_type(scope_type)

    def _assert_scope_exists(
        self,
        scope_type: str,
        scope_id: str,
        *,
        tenant_id: str,
    ) -> None:
        resolver = self._scope_exists_resolvers.get(scope_type)
        if resolver is None:
            authorization_denied(
                self._user_session,
                message=f"Tenant ownership validation is not configured for {scope_type}.",
                code="AUTHORIZATION_SCOPE_RESOLVER_REQUIRED",
                operation_label=f"validate {scope_type} tenant ownership",
                target_scope_type=scope_type,
                target_scope_id=scope_id,
                operation="authorization.infrastructure.denied",
            )
        if resolver(tenant_id, scope_id):
            return
        raise NotFoundError(f"{scope_type.title()} not found.", code=f"{scope_type.upper()}_NOT_FOUND")

    def _require_active_tenant_id(self, *, operation_label: str) -> str:
        if self._tenant_context_service is None:
            authorization_denied(
                self._user_session,
                message="Tenant context authorization is not configured.",
                code="AUTHORIZATION_CONTEXT_REQUIRED",
                operation_label=operation_label,
                operation="authorization.infrastructure.denied",
            )
        return self._tenant_context_service.require_active_tenant_id(
            operation_label=operation_label
        )

    def _require_target_membership(
        self,
        user_id: str,
        *,
        tenant_id: str,
        active_only: bool,
        operation_label: str,
    ) -> None:
        if self._user_tenant_repo is None:
            authorization_denied(
                self._user_session,
                message="Tenant membership authorization is not configured.",
                code="AUTHORIZATION_CONTEXT_REQUIRED",
                operation_label=operation_label,
                target_scope_type="user",
                target_scope_id=user_id,
                operation="authorization.infrastructure.denied",
            )
        membership = self._user_tenant_repo.get(user_id, tenant_id)
        has_membership = membership is not None and (
            not active_only or bool(membership.is_active)
        )
        if has_membership:
            return
        qualifier = "active " if active_only else ""
        authorization_denied(
            self._user_session,
            message=(
                f"Cannot {operation_label} for a user without {qualifier}membership "
                "in the active tenant."
            ),
            code="ACCESS_TARGET_TENANT_DENIED",
            operation_label=operation_label,
            target_scope_type="user",
            target_scope_id=user_id,
            operation="authorization.membership.denied",
        )

    @staticmethod
    def _raise_unsupported_scope_type(scope_type: str) -> NoReturn:
        raise ValidationError(
            f"Unsupported scope type '{scope_type}'.",
            code="UNSUPPORTED_SCOPE_TYPE",
        )

    def _refresh_current_session_if_needed(self, user_id: str) -> None:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None or principal.user_id != user_id:
            return
        user = self._user_repo.get(user_id)
        if user is None:
            self._user_session.clear()
            return
        self._user_session.set_principal(self._auth_service.build_principal(user))


__all__ = ["AccessControlService", "ScopeExistsResolver"]
