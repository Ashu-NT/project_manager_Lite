from __future__ import annotations

from collections.abc import Iterable

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    authorization_denied,
    record_authorization_denial,
    require_permission,
)
from src.core.platform.application.security.authorization.roles.role_scope_policy import (
    is_platform_role,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.repositories.security.auth import (
    PermissionRepository,
    RoleBindingRepository,
    RolePermissionRepository,
)
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.platform.domain.security.auth import (
    Permission,
    UserSessionContext,
)
from src.core.platform.domain.security.authorization.enforcement.sod import (
    SeparationOfDutiesPolicy,
)
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_TENANT,
)
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_ROLE_PERMISSIONS,
)

ROLE_MANAGE_PERMISSION = "auth.manage"
ROLE_ASSIGN_PERMISSION = "auth.role.assign"
RESERVED_CUSTOM_ROLE_NAMES = frozenset(DEFAULT_ROLE_PERMISSIONS)
CUSTOMER_CUSTOM_ROLE_PERMISSION_CODES = frozenset(
    permission_code
    for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items()
    if not is_platform_role(role_name)
    for permission_code in permission_codes
)


class TenantRoleAuthorization:
    """Fail-closed tenant administration scope, permission ceiling and SoD checks."""

    def __init__(
        self,
        *,
        role_binding_repo: RoleBindingRepository,
        permission_repo: PermissionRepository,
        role_permission_repo: RolePermissionRepository,
        tenant_repo: TenantRepository,
        membership_repo: UserTenantMembershipRepository,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
        sod_policy: SeparationOfDutiesPolicy,
    ) -> None:
        self._role_binding_repo = role_binding_repo
        self._permission_repo = permission_repo
        self._role_permission_repo = role_permission_repo
        self._tenant_repo = tenant_repo
        self._membership_repo = membership_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._sod_policy = sod_policy

    def require_role_administrator(self, *, operation_label: str):
        require_permission(
            self._user_session,
            ROLE_MANAGE_PERMISSION,
            operation_label=operation_label,
        )
        require_permission(
            self._user_session,
            ROLE_ASSIGN_PERMISSION,
            operation_label=operation_label,
        )
        actor = self._user_session.principal
        if actor is None:
            raise BusinessRuleError(
                "Authentication is required for custom-role administration.",
                code="AUTHENTICATION_REQUIRED",
            )
        if "platform.admin" in actor.permissions:
            authorization_denied(
                self._user_session,
                message=(
                    "Platform operators cannot administer customer roles without "
                    "a governed support context."
                ),
                code="PLATFORM_CUSTOMER_OPERATION_DENIED",
                operation_label=operation_label,
                target_scope_type="tenant",
                operation="authorization.support_access.denied",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label=operation_label
        )
        tenant = self._tenant_repo.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if not tenant.is_active:
            raise BusinessRuleError(
                "Custom roles require an active tenant.",
                code="TENANT_INACTIVE",
            )
        if not self._membership_repo.is_active_member(
            actor.user_id,
            tenant_id,
        ):
            authorization_denied(
                self._user_session,
                message=(
                    "Active tenant membership is required for custom-role "
                    "administration."
                ),
                code="TENANT_ACCESS_DENIED",
                operation_label=operation_label,
                target_scope_type="tenant",
                target_scope_id=tenant_id,
                operation="authorization.membership.denied",
            )
        self._require_tenant_administration_scope(
            actor.user_id,
            tenant_id=tenant_id,
        )
        return actor, tenant_id

    def _require_tenant_administration_scope(
        self,
        actor_user_id: str,
        *,
        tenant_id: str,
    ) -> None:
        required_permissions = {
            ROLE_MANAGE_PERMISSION,
            ROLE_ASSIGN_PERMISSION,
        }
        for binding in self._role_binding_repo.list_active_for_principal(
            actor_user_id,
            tenant_id=tenant_id,
        ):
            if (
                binding.actual_scope_type == ROLE_SCOPE_TENANT
                and binding.actual_scope_id is None
                and required_permissions.issubset(
                    self.permission_codes(binding.role_id)
                )
            ):
                return
        authorization_denied(
            self._user_session,
            message=(
                "A canonical tenant-scope administrative role is required for "
                "custom-role administration."
            ),
            code="CUSTOM_ROLE_TENANT_SCOPE_REQUIRED",
            operation_label="administer tenant custom roles",
            required_permissions=required_permissions,
            target_scope_type="tenant",
            target_scope_id=tenant_id,
            operation="authorization.resource_scope.denied",
        )

    def validate_permissions(
        self,
        permission_codes: Iterable[str],
    ) -> dict[str, Permission]:
        normalized_codes = {
            str(permission_code or "").strip().lower()
            for permission_code in (permission_codes or ())
            if str(permission_code or "").strip()
        }
        permission_map = {
            permission.code: permission
            for permission in self._permission_repo.list_all()
        }
        unknown_codes = normalized_codes.difference(permission_map)
        if unknown_codes:
            raise ValidationError(
                "Unknown custom-role permission codes: "
                + ", ".join(sorted(unknown_codes)),
                code="CUSTOM_ROLE_PERMISSION_UNKNOWN",
            )
        denied_codes = normalized_codes.difference(
            CUSTOMER_CUSTOM_ROLE_PERMISSION_CODES
        )
        if denied_codes:
            authorization_denied(
                self._user_session,
                message=(
                    "Custom roles cannot receive platform permission codes: "
                    + ", ".join(sorted(denied_codes))
                ),
                code="CUSTOM_ROLE_PERMISSION_DENIED",
                operation_label="validate custom-role permissions",
                required_permissions=denied_codes,
                target_scope_type="role",
                operation="authorization.permission_ceiling.denied",
            )
        conflicts = self._sod_policy.find_conflicts(normalized_codes)
        if conflicts:
            record_authorization_denial(
                self._user_session,
                operation_label="validate custom-role separation of duties",
                reason_code="CUSTOM_ROLE_PERMISSION_CONFLICT",
                required_permissions=normalized_codes,
                target_scope_type="role",
                operation="authorization.sod.denied",
            )
            raise ValidationError(
                f"Custom role violates separation of duties. {conflicts[0]}",
                code="CUSTOM_ROLE_PERMISSION_CONFLICT",
            )
        return {code: permission_map[code] for code in sorted(normalized_codes)}

    def permission_codes(self, role_id: str) -> set[str]:
        codes_by_id = {
            permission.id: permission.code
            for permission in self._permission_repo.list_all()
        }
        return {
            codes_by_id[permission_id]
            for permission_id in self._role_permission_repo.list_permission_ids(role_id)
            if permission_id in codes_by_id
        }
