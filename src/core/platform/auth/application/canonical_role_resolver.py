from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from src.core.platform.auth.contracts import (
    PermissionRepository,
    RoleBindingRepository,
    RolePermissionRepository,
    RoleRepository,
)
from src.core.platform.auth.domain import (
    RESOURCE_ROLE_SCOPE_TYPES,
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    Role,
    RoleBinding,
)
from src.core.platform.common.exceptions import BusinessRuleError


ScopeTenantResolver = Callable[[str, str], bool]


@dataclass(frozen=True)
class EffectiveRoleAuthority:
    """Canonical permissions effective in one explicit tenant/org context."""

    role_ids: frozenset[str]
    role_names: frozenset[str]
    permissions: frozenset[str]
    unrestricted_permissions: frozenset[str]
    scoped_access: dict[str, dict[str, frozenset[str]]]


class CanonicalRoleResolver:
    """Resolve canonical bindings without legacy fallback or inferred scope."""

    def __init__(
        self,
        *,
        role_binding_repo: RoleBindingRepository,
        role_repo: RoleRepository,
        role_permission_repo: RolePermissionRepository,
        permission_repo: PermissionRepository,
        scope_tenant_resolvers: Mapping[str, ScopeTenantResolver],
        allow_platform_customer_context: bool = False,
    ) -> None:
        self._role_binding_repo = role_binding_repo
        self._role_repo = role_repo
        self._role_permission_repo = role_permission_repo
        self._permission_repo = permission_repo
        self._scope_tenant_resolvers = {
            str(scope_type or "").strip().lower(): resolver
            for scope_type, resolver in scope_tenant_resolvers.items()
            if str(scope_type or "").strip()
        }
        self._allow_platform_customer_context = bool(
            allow_platform_customer_context
        )

    def register_scope_tenant_resolver(
        self,
        scope_type: str,
        resolver: ScopeTenantResolver,
    ) -> None:
        self._scope_tenant_resolvers[str(scope_type or "").strip().lower()] = resolver

    def resolve(
        self,
        principal_id: str,
        *,
        tenant_id: str | None,
        organization_id: str | None,
    ) -> EffectiveRoleAuthority:
        return self._resolve(
            principal_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            included_scope_types=None,
        )

    def resolve_tenant_authority(
        self,
        principal_id: str,
        *,
        tenant_id: str | None,
    ) -> EffectiveRoleAuthority:
        """Resolve only platform and tenant bindings for tenant-level decisions."""
        return self._resolve(
            principal_id,
            tenant_id=tenant_id,
            organization_id=None,
            included_scope_types=frozenset(
                {ROLE_SCOPE_PLATFORM, ROLE_SCOPE_TENANT}
            ),
        )

    def resolve_organization_authority(
        self,
        principal_id: str,
        *,
        tenant_id: str | None,
        organization_id: str | None,
    ) -> EffectiveRoleAuthority:
        """Resolve platform, tenant, and organization bindings only."""
        return self._resolve(
            principal_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            included_scope_types=frozenset(
                {ROLE_SCOPE_PLATFORM, ROLE_SCOPE_TENANT, "organization"}
            ),
        )

    def resolve_principal_authority(
        self,
        principal_id: str,
        *,
        tenant_id: str | None,
        organization_id: str | None,
        cutover_resource_scope_types: frozenset[str] = frozenset(),
    ) -> EffectiveRoleAuthority:
        """Resolve platform/tenant/organization plus already cut-over resource scopes.

        `cutover_resource_scope_types` grows one entry at a time as each
        resource scope (project, site, storeroom, maintenance) replaces its
        legacy scoped-grant/project-membership decision source.
        """
        return self._resolve(
            principal_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            included_scope_types=frozenset(
                {ROLE_SCOPE_PLATFORM, ROLE_SCOPE_TENANT, "organization"}
                | cutover_resource_scope_types
            ),
        )

    def _resolve(
        self,
        principal_id: str,
        *,
        tenant_id: str | None,
        organization_id: str | None,
        included_scope_types: frozenset[str] | None,
    ) -> EffectiveRoleAuthority:
        normalized_principal_id = str(principal_id or "").strip()
        if not normalized_principal_id:
            raise BusinessRuleError(
                "Canonical authority requires a principal id.",
                code="AUTHORIZATION_PRINCIPAL_REQUIRED",
            )
        normalized_tenant_id = str(tenant_id or "").strip() or None
        normalized_organization_id = str(organization_id or "").strip() or None
        if normalized_organization_id is not None and normalized_tenant_id is None:
            raise BusinessRuleError(
                "Organization authority requires tenant context.",
                code="AUTHORIZATION_CONTEXT_INVALID",
            )

        permission_codes_by_id = {
            permission.id: permission.code
            for permission in self._permission_repo.list_all()
        }
        role_permissions: dict[str, frozenset[str]] = {}
        role_ids: set[str] = set()
        role_names: set[str] = set()
        permissions: set[str] = set()
        unrestricted_permissions: set[str] = set()
        scoped_access: dict[str, dict[str, set[str]]] = {}

        bindings = self._role_binding_repo.list_active_for_principal(
            normalized_principal_id,
            tenant_id=None,
        )
        if normalized_tenant_id is not None:
            bindings.extend(
                self._role_binding_repo.list_active_for_principal(
                    normalized_principal_id,
                    tenant_id=normalized_tenant_id,
                )
            )

        for binding in bindings:
            if (
                included_scope_types is not None
                and binding.actual_scope_type not in included_scope_types
            ):
                continue
            role = self._validate_binding(
                binding,
                requested_tenant_id=normalized_tenant_id,
            )
            if role.status != "active":
                continue
            codes = role_permissions.get(role.id)
            if codes is None:
                codes = self._permission_codes_for_role(
                    role,
                    permission_codes_by_id=permission_codes_by_id,
                )
                role_permissions[role.id] = codes

            if binding.actual_scope_type == ROLE_SCOPE_PLATFORM:
                if (
                    normalized_tenant_id is not None
                    and not self._allow_platform_customer_context
                ):
                    raise BusinessRuleError(
                        "Platform authority cannot enter ordinary customer context.",
                        code="PLATFORM_CUSTOMER_CONTEXT_DENIED",
                    )
                self._add_unrestricted_role(
                    role,
                    codes,
                    role_ids=role_ids,
                    role_names=role_names,
                    permissions=permissions,
                    unrestricted_permissions=unrestricted_permissions,
                )
                continue

            if binding.actual_scope_type == ROLE_SCOPE_TENANT:
                self._add_unrestricted_role(
                    role,
                    codes,
                    role_ids=role_ids,
                    role_names=role_names,
                    permissions=permissions,
                    unrestricted_permissions=unrestricted_permissions,
                )
                continue

            self._require_resource_ownership(binding)
            scope_id = str(binding.actual_scope_id or "").strip()
            scope_rows = scoped_access.setdefault(binding.actual_scope_type, {})
            scope_rows.setdefault(scope_id, set()).update(codes)

            if binding.actual_scope_type == "organization":
                if scope_id == normalized_organization_id:
                    self._add_unrestricted_role(
                        role,
                        codes,
                        role_ids=role_ids,
                        role_names=role_names,
                        permissions=permissions,
                        unrestricted_permissions=unrestricted_permissions,
                    )
                continue

            role_ids.add(role.id)
            role_names.add(role.name)
            permissions.update(codes)

        return EffectiveRoleAuthority(
            role_ids=frozenset(role_ids),
            role_names=frozenset(role_names),
            permissions=frozenset(permissions),
            unrestricted_permissions=frozenset(unrestricted_permissions),
            scoped_access={
                scope_type: {
                    scope_id: frozenset(codes)
                    for scope_id, codes in scope_rows.items()
                }
                for scope_type, scope_rows in scoped_access.items()
            },
        )

    def _validate_binding(
        self,
        binding: RoleBinding,
        *,
        requested_tenant_id: str | None,
    ) -> Role:
        role = self._role_repo.get(binding.role_id)
        if role is None:
            raise BusinessRuleError(
                "A canonical role binding references a missing role.",
                code="AUTH_ROLE_BINDING_ROLE_MISSING",
            )
        if role.allowed_scope_type != binding.actual_scope_type:
            raise BusinessRuleError(
                "A canonical role binding does not match the role scope.",
                code="AUTH_ROLE_BINDING_SCOPE_MISMATCH",
            )
        if binding.actual_scope_type == ROLE_SCOPE_PLATFORM:
            if binding.tenant_id is not None or role.tenant_id is not None:
                raise BusinessRuleError(
                    "Platform role authority cannot be tenant-owned.",
                    code="AUTH_ROLE_BINDING_TENANT_MISMATCH",
                )
            return role
        if binding.tenant_id != requested_tenant_id:
            raise BusinessRuleError(
                "A canonical role binding is outside the requested tenant.",
                code="AUTH_ROLE_BINDING_TENANT_MISMATCH",
            )
        if role.tenant_id not in {None, binding.tenant_id}:
            raise BusinessRuleError(
                "A tenant-owned role is bound outside its tenant.",
                code="AUTH_ROLE_BINDING_TENANT_MISMATCH",
            )
        return role

    def _permission_codes_for_role(
        self,
        role: Role,
        *,
        permission_codes_by_id: Mapping[str, str],
    ) -> frozenset[str]:
        permission_ids = self._role_permission_repo.list_permission_ids(role.id)
        missing_ids = sorted(set(permission_ids).difference(permission_codes_by_id))
        if missing_ids:
            raise BusinessRuleError(
                "A canonical role references a missing permission.",
                code="AUTH_ROLE_PERMISSION_INVALID",
            )
        return frozenset(permission_codes_by_id[item] for item in permission_ids)

    def _require_resource_ownership(self, binding: RoleBinding) -> None:
        if binding.actual_scope_type not in RESOURCE_ROLE_SCOPE_TYPES:
            raise BusinessRuleError(
                "A canonical role binding uses an unsupported resource scope.",
                code="AUTH_ROLE_BINDING_SCOPE_INVALID",
            )
        resolver = self._scope_tenant_resolvers.get(binding.actual_scope_type)
        if resolver is None:
            raise BusinessRuleError(
                "Canonical resource ownership validation is not configured.",
                code="AUTHORIZATION_SCOPE_RESOLVER_REQUIRED",
            )
        tenant_id = str(binding.tenant_id or "").strip()
        scope_id = str(binding.actual_scope_id or "").strip()
        if not resolver(tenant_id, scope_id):
            raise BusinessRuleError(
                "A canonical role binding references a resource outside its tenant.",
                code="AUTH_ROLE_BINDING_SCOPE_OWNERSHIP_INVALID",
            )

    @staticmethod
    def _add_unrestricted_role(
        role: Role,
        codes: frozenset[str],
        *,
        role_ids: set[str],
        role_names: set[str],
        permissions: set[str],
        unrestricted_permissions: set[str],
    ) -> None:
        role_ids.add(role.id)
        role_names.add(role.name)
        permissions.update(codes)
        unrestricted_permissions.update(codes)


__all__ = [
    "CanonicalRoleResolver",
    "EffectiveRoleAuthority",
    "ScopeTenantResolver",
]
